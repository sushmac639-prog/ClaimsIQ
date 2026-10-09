import enum
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def enum_values(enum_cls):
    return [member.value for member in enum_cls]


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


class DocumentStatus(str, enum.Enum):
    PROCESSING = "processing"
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"


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
        Enum(UserRole, name="user_role", values_callable=enum_values), nullable=False
    )
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
    status: Mapped[PolicyStatus] = mapped_column(
        Enum(PolicyStatus, name="policy_status", values_callable=enum_values),
        default=PolicyStatus.ACTIVE,
        nullable=False,
    )
    claims: Mapped[list["Claim"]] = relationship(back_populates="policy")
    documents: Mapped[list["Document"]] = relationship(back_populates="policy")


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
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, name="claim_status", values_callable=enum_values),
        default=ClaimStatus.SUBMITTED,
        nullable=False,
    )
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
    old_status: Mapped[ClaimStatus | None] = mapped_column(
        Enum(ClaimStatus, name="history_old_status", values_callable=enum_values)
    )
    new_status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, name="history_new_status", values_callable=enum_values), nullable=False
    )
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


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(nullable=False)
    region: Mapped[str | None] = mapped_column(String(100), index=True)
    policy_id: Mapped[int | None] = mapped_column(ForeignKey("policies.id", ondelete="SET NULL"), index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", values_callable=enum_values),
        default=DocumentStatus.PROCESSING,
        nullable=False,
    )
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(500))
    policy: Mapped["Policy | None"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    page_number: Mapped[int | None] = mapped_column()
    section_reference: Mapped[str | None] = mapped_column(String(255))
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    vector_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    character_count: Mapped[int] = mapped_column(nullable=False)
    document: Mapped["Document"] = relationship(back_populates="chunks")


class ChatQueryLog(Base):
    __tablename__ = "chat_query_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(150), nullable=False)
    source_references: Mapped[str | None] = mapped_column(Text)
    retrieved_chunk_count: Mapped[int] = mapped_column(default=0, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column()
    no_match: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    token_type: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

