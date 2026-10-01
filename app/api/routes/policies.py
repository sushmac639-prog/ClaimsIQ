from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_roles
from app.db.models import AuditLog, Policy, PolicyStatus, User, UserRole
from app.db.session import get_db
from app.schemas.policy import PolicyCreate, PolicyRead, PolicyUpdate
router = APIRouter(prefix="/policies", tags=["Policies"])
write_roles = require_roles(UserRole.ADMIN, UserRole.CLAIMS_MANAGER)
@router.post("", response_model=PolicyRead, status_code=status.HTTP_201_CREATED)
def create_policy(body: PolicyCreate, db: Session = Depends(get_db), actor: User = Depends(write_roles)):
    if db.scalar(select(Policy).where(Policy.policy_number == body.policy_number)):
        raise HTTPException(status_code=409, detail="Policy number already exists")
    policy = Policy(**body.model_dump()); db.add(policy); db.flush()
    db.add(AuditLog(user_id=actor.id, action="POLICY_CREATED", entity_type="Policy", entity_id=str(policy.id)))
    db.commit(); db.refresh(policy); return policy
@router.get("", response_model=list[PolicyRead])
def list_policies(region: str | None = None, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(Policy).order_by(Policy.id)
    if region: stmt = stmt.where(Policy.region == region)
    return list(db.scalars(stmt.offset(skip).limit(limit)).all())
@router.get("/{policy_id}", response_model=PolicyRead)
def get_policy(policy_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    policy = db.get(Policy, policy_id)
    if policy is None: raise HTTPException(status_code=404, detail="Policy not found")
    return policy
@router.patch("/{policy_id}", response_model=PolicyRead)
def update_policy(policy_id: int, body: PolicyUpdate, db: Session = Depends(get_db), actor: User = Depends(write_roles)):
    policy = db.get(Policy, policy_id)
    if policy is None: raise HTTPException(status_code=404, detail="Policy not found")
    values = body.model_dump(exclude_unset=True)
    effective = values.get("effective_date", policy.effective_date); expiry = values.get("expiry_date", policy.expiry_date)
    if expiry <= effective: raise HTTPException(status_code=422, detail="expiry_date must be after effective_date")
    for field, value in values.items(): setattr(policy, field, value)
    db.add(AuditLog(user_id=actor.id, action="POLICY_UPDATED", entity_type="Policy", entity_id=str(policy.id)))
    db.commit(); db.refresh(policy); return policy
@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_policy(policy_id: int, db: Session = Depends(get_db), actor: User = Depends(write_roles)):
    policy = db.get(Policy, policy_id)
    if policy is None: raise HTTPException(status_code=404, detail="Policy not found")
    policy.status = PolicyStatus.INACTIVE
    db.add(AuditLog(user_id=actor.id, action="POLICY_DEACTIVATED", entity_type="Policy", entity_id=str(policy.id)))
    db.commit(); return None
