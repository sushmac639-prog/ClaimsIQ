from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.core.security import hash_password
from app.db.models import AuditLog, User, UserRole
from app.db.session import get_db
from app.schemas.user import UserCreate, UserRead, UserUpdate
router = APIRouter(prefix="/users", tags=["Users"])
admin_only = require_roles(UserRole.ADMIN)
@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: Session = Depends(get_db), actor: User = Depends(admin_only)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already exists")
    user = User(full_name=body.full_name, email=email, password_hash=hash_password(body.password), role=body.role, region=body.region)
    db.add(user); db.flush()
    db.add(AuditLog(user_id=actor.id, action="USER_CREATED", entity_type="User", entity_id=str(user.id)))
    db.commit(); db.refresh(user); return user
@router.get("", response_model=list[UserRead])
def list_users(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return list(db.scalars(select(User).order_by(User.id).offset(skip).limit(limit)).all())
@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    user = db.get(User, user_id)
    if user is None: raise HTTPException(status_code=404, detail="User not found")
    return user
@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db), actor: User = Depends(admin_only)):
    user = db.get(User, user_id)
    if user is None: raise HTTPException(status_code=404, detail="User not found")
    for field, value in body.model_dump(exclude_unset=True).items(): setattr(user, field, value)
    db.add(AuditLog(user_id=actor.id, action="USER_UPDATED", entity_type="User", entity_id=str(user.id)))
    db.commit(); db.refresh(user); return user
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(user_id: int, db: Session = Depends(get_db), actor: User = Depends(admin_only)):
    user = db.get(User, user_id)
    if user is None: raise HTTPException(status_code=404, detail="User not found")
    if user.id == actor.id: raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    user.is_active = False
    db.add(AuditLog(user_id=actor.id, action="USER_DEACTIVATED", entity_type="User", entity_id=str(user.id)))
    db.commit(); return None
