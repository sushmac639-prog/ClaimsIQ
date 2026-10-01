from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_roles
from app.db.models import AuditLog, Claim, ClaimNote, ClaimStatus, ClaimStatusHistory, Policy, PolicyStatus, User, UserRole
from app.db.session import get_db
from app.schemas.claim import ClaimCreate, ClaimRead, ClaimStatusUpdate, ClaimUpdate, NoteCreate, NoteRead
router = APIRouter(prefix="/claims", tags=["Claims"])
manager_or_admin = require_roles(UserRole.ADMIN, UserRole.CLAIMS_MANAGER)
adjuster_or_manager = require_roles(UserRole.ADMIN, UserRole.CLAIMS_MANAGER, UserRole.CLAIMS_ADJUSTER)
VALID_TRANSITIONS = {ClaimStatus.SUBMITTED:{ClaimStatus.UNDER_REVIEW}, ClaimStatus.UNDER_REVIEW:{ClaimStatus.APPROVED,ClaimStatus.REJECTED}, ClaimStatus.APPROVED:{ClaimStatus.CLOSED}, ClaimStatus.REJECTED:{ClaimStatus.CLOSED}, ClaimStatus.CLOSED:set()}
def visible_claims_stmt(user: User):
    stmt = select(Claim)
    if user.role == UserRole.CLAIMS_ADJUSTER:
        stmt = stmt.where((Claim.assigned_user_id == user.id) | (Claim.region == user.region))
    return stmt
@router.post("", response_model=ClaimRead, status_code=status.HTTP_201_CREATED)
def create_claim(body: ClaimCreate, db: Session = Depends(get_db), actor: User = Depends(adjuster_or_manager)):
    if db.scalar(select(Claim).where(Claim.claim_number == body.claim_number)): raise HTTPException(status_code=409, detail="Claim number already exists")
    policy = db.get(Policy, body.policy_id)
    if policy is None or policy.status != PolicyStatus.ACTIVE: raise HTTPException(status_code=422, detail="Claim must be linked to an active policy")
    if body.assigned_user_id:
        assignee = db.get(User, body.assigned_user_id)
        if assignee is None or assignee.role != UserRole.CLAIMS_ADJUSTER or not assignee.is_active: raise HTTPException(status_code=422, detail="Assigned user must be an active claims adjuster")
    claim = Claim(**body.model_dump(), status=ClaimStatus.SUBMITTED); db.add(claim); db.flush()
    db.add(ClaimStatusHistory(claim_id=claim.id, old_status=None, new_status=ClaimStatus.SUBMITTED, changed_by=actor.id))
    db.add(AuditLog(user_id=actor.id, action="CLAIM_CREATED", entity_type="Claim", entity_id=str(claim.id)))
    db.commit(); db.refresh(claim); return claim
@router.get("", response_model=list[ClaimRead])
def list_claims(claim_status: ClaimStatus | None = None, region: str | None = None, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    stmt = visible_claims_stmt(actor).order_by(Claim.id)
    if claim_status: stmt = stmt.where(Claim.status == claim_status)
    if region: stmt = stmt.where(Claim.region == region)
    return list(db.scalars(stmt.offset(skip).limit(limit)).all())
@router.get("/{claim_id}", response_model=ClaimRead)
def get_claim(claim_id: int, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    claim = db.scalar(visible_claims_stmt(actor).where(Claim.id == claim_id))
    if claim is None: raise HTTPException(status_code=404, detail="Claim not found")
    return claim
@router.patch("/{claim_id}", response_model=ClaimRead)
def update_claim(claim_id: int, body: ClaimUpdate, db: Session = Depends(get_db), actor: User = Depends(adjuster_or_manager)):
    claim = db.scalar(visible_claims_stmt(actor).where(Claim.id == claim_id))
    if claim is None: raise HTTPException(status_code=404, detail="Claim not found")
    for field, value in body.model_dump(exclude_unset=True).items(): setattr(claim, field, value)
    db.add(AuditLog(user_id=actor.id, action="CLAIM_UPDATED", entity_type="Claim", entity_id=str(claim.id))); db.commit(); db.refresh(claim); return claim
@router.patch("/{claim_id}/status", response_model=ClaimRead)
def update_claim_status(claim_id: int, body: ClaimStatusUpdate, db: Session = Depends(get_db), actor: User = Depends(adjuster_or_manager)):
    claim = db.scalar(visible_claims_stmt(actor).where(Claim.id == claim_id))
    if claim is None: raise HTTPException(status_code=404, detail="Claim not found")
    allowed = VALID_TRANSITIONS[claim.status]; manager_override = actor.role in {UserRole.ADMIN, UserRole.CLAIMS_MANAGER} and bool(body.justification)
    if body.new_status not in allowed and not manager_override: raise HTTPException(status_code=409, detail=f"Invalid transition from {claim.status.value} to {body.new_status.value}")
    old_status = claim.status; claim.status = body.new_status
    if body.new_status == ClaimStatus.CLOSED: claim.closed_at = datetime.now(timezone.utc)
    db.add(ClaimStatusHistory(claim_id=claim.id, old_status=old_status, new_status=body.new_status, changed_by=actor.id, justification=body.justification))
    db.add(AuditLog(user_id=actor.id, action="CLAIM_STATUS_CHANGED", entity_type="Claim", entity_id=str(claim.id), details=f"{old_status.value} -> {body.new_status.value}")); db.commit(); db.refresh(claim); return claim
@router.post("/{claim_id}/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def add_note(claim_id: int, body: NoteCreate, db: Session = Depends(get_db), actor: User = Depends(adjuster_or_manager)):
    claim = db.scalar(visible_claims_stmt(actor).where(Claim.id == claim_id))
    if claim is None: raise HTTPException(status_code=404, detail="Claim not found")
    note = ClaimNote(claim_id=claim.id, created_by=actor.id, note=body.note); db.add(note); db.flush()
    db.add(AuditLog(user_id=actor.id, action="CLAIM_NOTE_ADDED", entity_type="Claim", entity_id=str(claim.id))); db.commit(); db.refresh(note); return note
@router.get("/{claim_id}/notes", response_model=list[NoteRead])
def list_notes(claim_id: int, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    claim = db.scalar(visible_claims_stmt(actor).where(Claim.id == claim_id))
    if claim is None: raise HTTPException(status_code=404, detail="Claim not found")
    return list(db.scalars(select(ClaimNote).where(ClaimNote.claim_id == claim_id).order_by(ClaimNote.created_at)).all())
@router.delete("/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_claim(claim_id: int, db: Session = Depends(get_db), actor: User = Depends(manager_or_admin)):
    claim = db.get(Claim, claim_id)
    if claim is None: raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status != ClaimStatus.SUBMITTED: raise HTTPException(status_code=409, detail="Only submitted claims can be deleted")
    db.add(AuditLog(user_id=actor.id, action="CLAIM_DELETED", entity_type="Claim", entity_id=str(claim.id))); db.delete(claim); db.commit(); return None
