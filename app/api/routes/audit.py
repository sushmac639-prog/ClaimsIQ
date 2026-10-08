from fastapi import APIRouter, Depends, Query 
from sqlalchemy import select 
from sqlalchemy.orm import Session 
 
from app.api.deps import require_roles 
from app.db.models import AuditLog, User, UserRole 
from app.db.session import get_db 
from app.schemas.audit import AuditLogRead 
 
router = APIRouter(prefix="/audit-logs", tags=["Audit"]) 
admin_only = require_roles(UserRole.ADMIN) 
 
 
@router.get("", response_model=list[AuditLogRead]) 
def list_audit_logs( 
    action: str | None = Query(default=None, max_length=100), 
    entity_type: str | None = Query(default=None, max_length=100), 
    user_id: int | None = Query(default=None, ge=1), 
    skip: int = Query(0, ge=0), 
    limit: int = Query(100, ge=1, le=200), 
    db: Session = Depends(get_db), 
    _: User = Depends(admin_only), 
): 
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()) 
    if action: 
        stmt = stmt.where(AuditLog.action == action.strip()) 
    if entity_type: 
        stmt = stmt.where(AuditLog.entity_type == entity_type.strip()) 
    if user_id: 
        stmt = stmt.where(AuditLog.user_id == user_id) 
    return list(db.scalars(stmt.offset(skip).limit(limit)).all()) 