from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Document, DocumentStatus, User, UserRole
from app.rag.vector_store import RetrievedChunk, get_vector_store


def retrieve_chunks(
    db: Session,
    user: User,
    question: str,
    top_k: int | None = None,
    policy_id: int | None = None,
) -> list[RetrievedChunk]:
    requested = top_k or settings.rag_top_k
    requested = max(1, min(requested, 10))
    candidate_count = min(max(requested * 4, requested), 40)

    where = {"status": "active"}
    if policy_id is not None:
        where["policy_id"] = policy_id

    candidates = get_vector_store().search(question, candidate_count, where)
    if not candidates:
        return []

    document_ids = [item.document_id for item in candidates]
    documents = list(
        db.scalars(
            select(Document).where(
                Document.id.in_(document_ids),
                Document.status == DocumentStatus.ACTIVE,
            )
        ).all()
    )
    accessible = {doc.id: doc for doc in documents}

    is_privileged = user.role in {UserRole.ADMIN, UserRole.CLAIMS_MANAGER}
    filtered: list[RetrievedChunk] = []
    for item in candidates:
        document = accessible.get(item.document_id)
        if document is None:
            continue
        if policy_id is not None and document.policy_id != policy_id:
            continue
        if not is_privileged:
            allowed_region = document.region in {None, "GLOBAL", user.region}
            if not allowed_region:
                continue
        if item.similarity < settings.rag_min_similarity:
            continue
        filtered.append(item)
        if len(filtered) >= requested:
            break
    return filtered
