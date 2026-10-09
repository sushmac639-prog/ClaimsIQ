import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.config import settings
from app.db.models import AuditLog, Document, DocumentStatus, Policy, User, UserRole
from app.db.session import get_db
from app.rag.ingestion import ingest_document
from app.rag.vector_store import get_vector_store
from app.schemas.ai import DocumentRead, DocumentStatusUpdate

router = APIRouter(prefix="/documents", tags=["Documents"])
admin_only = require_roles(UserRole.ADMIN)

ALLOWED_CONTENT_TYPES = {"application/pdf"}


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.replace(" ", "_")
    return "".join(ch for ch in name if ch.isalnum() or ch in "._-")[:220] or "document.pdf"


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    policy_id: int | None = Query(default=None, ge=1),
    region: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Only PDF documents are supported")

    if policy_id is not None:
        policy = db.get(Policy, policy_id)
        if policy is None:
            raise HTTPException(status_code=404, detail="Policy not found")
        region = region or policy.region

    content = file.file.read(settings.max_document_size_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_document_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Document exceeds {settings.max_document_size_mb} MB")
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded document is empty")

    checksum = hashlib.sha256(content).hexdigest()
    existing = db.scalar(select(Document).where(Document.checksum_sha256 == checksum))
    if existing:
        raise HTTPException(status_code=409, detail="A document with the same content already exists")

    settings.document_storage_directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{_safe_filename(file.filename or 'document.pdf')}"
    path = settings.document_storage_directory / stored_name
    path.write_bytes(content)

    document = Document(
        filename=file.filename or stored_name,
        storage_path=str(path),
        checksum_sha256=checksum,
        content_type=file.content_type,
        file_size_bytes=len(content),
        region=region,
        policy_id=policy_id,
        status=DocumentStatus.PROCESSING,
        uploaded_by=actor.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        ingest_document(db, document)
    except Exception as exc:
        db.refresh(document)
        raise HTTPException(status_code=502, detail=f"Document indexing failed: {document.failure_reason or str(exc)}") from exc

    db.add(
        AuditLog(
            user_id=actor.id,
            action="DOCUMENT_UPLOADED",
            entity_type="Document",
            entity_id=str(document.id),
            details=f"filename={document.filename}; policy_id={document.policy_id}",
        )
    )
    db.commit()
    db.refresh(document)
    return document


@router.get("", response_model=list[DocumentRead])
def list_documents(
    status_filter: DocumentStatus | None = Query(default=None, alias="status"),
    policy_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Document).order_by(Document.id.desc())
    if status_filter:
        stmt = stmt.where(Document.status == status_filter)
    if policy_id:
        stmt = stmt.where(Document.policy_id == policy_id)
    if user.role not in {UserRole.ADMIN, UserRole.CLAIMS_MANAGER}:
        stmt = stmt.where((Document.region == user.region) | (Document.region.is_(None)) | (Document.region == "GLOBAL"))
    return list(db.scalars(stmt).all())


@router.patch("/{document_id}/status", response_model=DocumentRead)
def update_document_status(
    document_id: int,
    body: DocumentStatusUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if body.active:
        try:
            document.status = DocumentStatus.PROCESSING
            document.failure_reason = None
            db.commit()
            db.refresh(document)
            ingest_document(db, document)
        except Exception as exc:
            db.refresh(document)
            raise HTTPException(status_code=502, detail=f"Document re-indexing failed: {document.failure_reason or str(exc)}") from exc
        action = "DOCUMENT_ACTIVATED"
    else:
        get_vector_store().delete_document(document.id)
        document.status = DocumentStatus.INACTIVE
        db.commit()
        action = "DOCUMENT_DEACTIVATED"

    db.add(AuditLog(user_id=actor.id, action=action, entity_type="Document", entity_id=str(document.id)))
    db.commit()
    db.refresh(document)
    return document
