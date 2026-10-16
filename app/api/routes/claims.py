from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.redaction import redact_sensitive_text
from app.db.models import (
    AuditLog, Claim, ClaimNote, ClaimStatus, ClaimStatusHistory,
    Policy, PolicyStatus, User, UserRole,
)
from app.db.session import get_db
from app.schemas.claim import ClaimCreate, ClaimRead, ClaimStatusUpdate, ClaimUpdate, NoteCreate, NoteRead

router = APIRouter(prefix="/claims", tags=["Claims"])
manager_or_admin = require_roles(UserRole.ADMIN, UserRole.CLAIMS_MANAGER)
adjuster_or_manager = require_roles(UserRole.ADMIN, UserRole.CLAIMS_MANAGER, UserRole.CLAIMS_ADJUSTER)
VALID_TRANSITIONS = {
    ClaimStatus.SUBMITTED: {ClaimStatus.UNDER_REVIEW},
    ClaimStatus.UNDER_REVIEW: {ClaimStatus.APPROVED, ClaimStatus.REJECTED},
    ClaimStatus.APPROVED: {ClaimStatus.CLOSED},
    ClaimStatus.REJECTED: {ClaimStatus.CLOSED},
    ClaimStatus.CLOSED: set(),
}


def visible_claims_stmt(user: User):
    """Apply row-level visibility in SQL before any claim is returned or mutated."""
    stmt = select(Claim).where(Claim.archived_at.is_(None))
    if user.role == UserRole.CLAIMS_ADJUSTER:
        stmt = stmt.where((Claim.assigned_user_id == user.id) | (func.lower(Claim.region) == (user.region or "").casefold()))
    elif user.role == UserRole.SUPPORT_AGENT:
        # Support users may only look up claims within their own region.
        stmt = stmt.where(func.lower(Claim.region) == (user.region or "").casefold())
    return stmt


def _validate_assignee(db: Session, assigned_user_id: int | None, region: str) -> None:
    if assigned_user_id is None:
        return
    assignee = db.get(User, assigned_user_id)
    if (assignee is None or not assignee.is_active or assignee.role != UserRole.CLAIMS_ADJUSTER):
        raise HTTPException(status_code=422, detail="Assigned user must be an active claims adjuster")
    if assignee.region and assignee.region.casefold() != region.casefold():
        raise HTTPException(status_code=422, detail="Assigned adjuster must belong to the claim region")


@router.post("", response_model=ClaimRead, status_code=status.HTTP_201_CREATED)
def create_claim(body: ClaimCreate, db: Session = Depends(get_db), actor: User = Depends(adjuster_or_manager)):
    if db.scalar(select(Claim.id).where(Claim.claim_number == body.claim_number)):
        raise HTTPException(status_code=409, detail="Claim number already exists")
    policy = db.get(Policy, body.policy_id)
    if policy is None or policy.status != PolicyStatus.ACTIVE:
        raise HTTPException(status_code=422, detail="Claim must be linked to an active policy")
    today = date.today()
    if not policy.effective_date <= today <= policy.expiry_date:
        raise HTTPException(status_code=422, detail="Policy is not within its effective coverage dates")
    if policy.region.casefold() != body.region.strip().casefold():
        raise HTTPException(status_code=422, detail="Claim region must match the policy region")
    if actor.role == UserRole.CLAIMS_ADJUSTER:
        if not actor.region or actor.region.casefold() != body.region.strip().casefold():
            raise HTTPException(status_code=403, detail="You can only create claims in your region")
        if body.assigned_user_id not in (None, actor.id):
            raise HTTPException(status_code=403, detail="Adjusters cannot assign claims to another user")
    _validate_assignee(db, body.assigned_user_id, body.region.strip())

    claim_values = body.model_dump()
    claim_values["region"] = policy.region  # persist the canonical policy region
    claim = Claim(**claim_values, status=ClaimStatus.SUBMITTED)
    db.add(claim)
    db.flush()
    db.add(ClaimStatusHistory(claim_id=claim.id, old_status=None, new_status=ClaimStatus.SUBMITTED, changed_by=actor.id))
    db.add(AuditLog(user_id=actor.id, action="CLAIM_CREATED", entity_type="Claim", entity_id=str(claim.id)))
    db.commit()
    db.refresh(claim)
    return claim


@router.get("", response_model=list[ClaimRead])
def list_claims(
    claim_status: ClaimStatus | None = None,
    claim_number: str | None = Query(default=None, min_length=1, max_length=80),
    claimant: str | None = Query(default=None, min_length=1, max_length=150),
    policy_number: str | None = Query(default=None, min_length=1, max_length=80),
    region: str | None = Query(default=None, max_length=100),
    skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db), actor: User = Depends(get_current_user),
):
    stmt = visible_claims_stmt(actor).order_by(Claim.id)
    if claim_status:
        stmt = stmt.where(Claim.status == claim_status)
    if claim_number:
        stmt = stmt.where(Claim.claim_number.ilike(f"%{claim_number.strip()}%"))
    if claimant:
        stmt = stmt.where(Claim.claimant_name.ilike(f"%{claimant.strip()}%"))
    if policy_number:
        stmt = stmt.join(Claim.policy).where(Policy.policy_number.ilike(f"%{policy_number.strip()}%"))
    if region:
        # A caller-provided filter can narrow visibility, never broaden it.
        stmt = stmt.where(Claim.region == region.strip())
    return list(db.scalars(stmt.offset(skip).limit(limit)).all())


@router.get("/{claim_id}", response_model=ClaimRead)
def get_claim(claim_id: int, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    claim = db.scalar(visible_claims_stmt(actor).where(Claim.id == claim_id))
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.patch("/{claim_id}", response_model=ClaimRead)
def update_claim(claim_id: int, body: ClaimUpdate, db: Session = Depends(get_db), actor: User = Depends(adjuster_or_manager)):
    claim = db.scalar(visible_claims_stmt(actor).where(Claim.id == claim_id))
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    values = body.model_dump(exclude_unset=True)
    if not values:
        return claim
    privileged_fields = {"assigned_user_id", "claim_amount", "region"}
    if actor.role == UserRole.CLAIMS_ADJUSTER and privileged_fields.intersection(values):
        raise HTTPException(status_code=403, detail="Adjusters cannot change claim assignment, amount, or region")
    if "region" in values:
        policy = db.get(Policy, claim.policy_id)
        if policy is None or policy.region.casefold() != values["region"].strip().casefold():
            raise HTTPException(status_code=422, detail="Claim region must match the linked policy region")
        values["region"] = policy.region  # persist canonical casing for row-level checks
    target_region = values.get("region", claim.region)
    if "assigned_user_id" in values or "region" in values:
        _validate_assignee(db, values.get("assigned_user_id", claim.assigned_user_id), target_region)
    for field, value in values.items():
        setattr(claim, field, value.strip() if isinstance(value, str) and field in {"claimant_name", "claim_type", "region"} else value)
    db.add(AuditLog(user_id=actor.id, action="CLAIM_UPDATED", entity_type="Claim", entity_id=str(claim.id)))
    db.commit()
    db.refresh(claim)
    return claim


@router.patch("/{claim_id}/status", response_model=ClaimRead)
def update_claim_status(claim_id: int, body: ClaimStatusUpdate, db: Session = Depends(get_db), actor: User = Depends(adjuster_or_manager)):
    claim = db.scalar(visible_claims_stmt(actor).where(Claim.id == claim_id))
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    is_manager = actor.role in {UserRole.ADMIN, UserRole.CLAIMS_MANAGER}
    justification = body.justification.strip() if body.justification else ""
    override_needed = body.new_status not in VALID_TRANSITIONS[claim.status]
    if override_needed and (not is_manager or not justification):
        raise HTTPException(status_code=409, detail=f"Invalid transition from {claim.status.value} to {body.new_status.value}; manager override with justification is required")
    if override_needed and len(justification) < 10:
        raise HTTPException(status_code=422, detail="Manager override justification must contain at least 10 non-whitespace characters")
    old_status = claim.status
    claim.status = body.new_status
    if body.new_status == ClaimStatus.CLOSED:
        claim.closed_at = datetime.now(timezone.utc)
    db.add(ClaimStatusHistory(claim_id=claim.id, old_status=old_status, new_status=body.new_status, changed_by=actor.id, justification=redact_sensitive_text(justification) if justification else None))
    db.add(AuditLog(user_id=actor.id, action="CLAIM_STATUS_CHANGED", entity_type="Claim", entity_id=str(claim.id), details=f"{old_status.value} -> {body.new_status.value}; override={override_needed}"))
    db.commit()
    db.refresh(claim)
    return claim


@router.post("/{claim_id}/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def add_note(claim_id: int, body: NoteCreate, db: Session = Depends(get_db), actor: User = Depends(adjuster_or_manager)):
    claim = db.scalar(visible_claims_stmt(actor).where(Claim.id == claim_id))
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    note = ClaimNote(claim_id=claim.id, created_by=actor.id, note=body.note.strip())
    db.add(note)
    db.flush()
    db.add(AuditLog(user_id=actor.id, action="CLAIM_NOTE_ADDED", entity_type="Claim", entity_id=str(claim.id)))
    db.commit()
    db.refresh(note)
    return note


@router.get("/{claim_id}/notes", response_model=list[NoteRead])
def list_notes(claim_id: int, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    claim = db.scalar(visible_claims_stmt(actor).where(Claim.id == claim_id))
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return list(db.scalars(select(ClaimNote).where(ClaimNote.claim_id == claim_id).order_by(ClaimNote.created_at)).all())


@router.delete("/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_claim(claim_id: int, db: Session = Depends(get_db), actor: User = Depends(manager_or_admin)):
    claim = db.scalar(select(Claim).where(Claim.id == claim_id, Claim.archived_at.is_(None)))
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status != ClaimStatus.SUBMITTED:
        raise HTTPException(status_code=409, detail="Only submitted claims can be archived")
    # Soft-delete only: status history and notes remain available for audit retention.
    claim.archived_at = datetime.now(timezone.utc)
    db.add(AuditLog(user_id=actor.id, action="CLAIM_ARCHIVED", entity_type="Claim", entity_id=str(claim.id)))
    db.commit()
    return None
