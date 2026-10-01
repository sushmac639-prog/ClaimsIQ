import enum
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CLAIMS_MANAGER = "claims_manager"
    CLAIMS_ADJUSTER = "claims_adjuster"
    SUPPORT_AGENT = "support_agent"

class PolicyStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"

class ClaimStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLOSED = "closed"

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
    nullable=False,)
    region: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assigned_claims: Mapped[list["Claim"]] = relationship(back_populates="assigned_adjuster", foreign_keys="Claim.assigned_user_id")
    claim_notes: Mapped[list["ClaimNote"]] = relationship(back_populates="author")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")

class Policy(TimestampMixin, Base):
    __tablename__ = "policies"
    id: Mapped[int] = mapped_column(primary_key=True)
    policy_number: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    policy_type: Mapped[str] = mapped_column(String(80), nullable=False)
    coverage_description: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PolicyStatus] = mapped_column(Enum(PolicyStatus, name="policy_status",values_callable=lambda enum_cls: [item.value for item in enum_cls]))
    claims: Mapped[list["Claim"]] = relationship(back_populates="policy")

class Claim(TimestampMixin, Base):
    __tablename__ = "claims"
    __table_args__ = (Index("ix_claims_status_region", "status", "region"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    claim_number: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id", ondelete="RESTRICT"), nullable=False)
    assigned_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    claimant_name: Mapped[str] = mapped_column(String(150), nullable=False)
    claim_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    claim_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    region: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    status: Mapped[ClaimStatus] = mapped_column(Enum(ClaimStatus, name="claim_status", values_callable=lambda enum_cls: [item.value for item in enum_cls]))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    policy: Mapped["Policy"] = relationship(back_populates="claims")
    assigned_adjuster: Mapped["User | None"] = relationship(back_populates="assigned_claims", foreign_keys=[assigned_user_id])
    notes: Mapped[list["ClaimNote"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    status_history: Mapped[list["ClaimStatusHistory"]] = relationship(back_populates="claim", cascade="all, delete-orphan")

class ClaimNote(TimestampMixin, Base):
    __tablename__ = "claim_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    claim: Mapped["Claim"] = relationship(back_populates="notes")
    author: Mapped["User"] = relationship(back_populates="claim_notes")

class ClaimStatusHistory(Base):
    __tablename__ = "claim_status_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    old_status: Mapped[ClaimStatus | None] = mapped_column(Enum(ClaimStatus, name="history_old_status"))
    new_status: Mapped[ClaimStatus] = mapped_column(Enum(ClaimStatus, name="history_new_status"), nullable=False)
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    justification: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    claim: Mapped["Claim"] = relationship(back_populates="status_history")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(100))
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user: Mapped["User | None"] = relationship(back_populates="audit_logs")
