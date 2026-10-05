import hashlib
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Document, DocumentChunk, DocumentStatus
from app.rag.chunking import split_pages
from app.rag.vector_store import get_vector_store


class DocumentIngestionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_pdf_pages(path: Path) -> list[tuple[int, str]]:
    try:
        reader = PdfReader(str(path))
        pages: list[tuple[int, str]] = []
        for page_number, page in enumerate(reader.pages, start=1):
            pages.append((page_number, page.extract_text() or ""))
        return pages
    except Exception as exc:
        raise DocumentIngestionError("Unable to extract text from the PDF") from exc


def ingest_document(db: Session, document: Document) -> int:
    path = Path(document.storage_path)
    try:
        pages = extract_pdf_pages(path)
        chunks = split_pages(pages)
        if not chunks:
            raise DocumentIngestionError("No extractable text was found in the PDF")

        vector_ids: list[str] = []
        vector_texts: list[str] = []
        vector_metadatas: list[dict] = []
        db_chunks: list[DocumentChunk] = []
        for chunk in chunks:
            vector_id = f"document-{document.id}-chunk-{chunk.chunk_index}"
            metadata = {
                "document_id": document.id,
                "filename": document.filename,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "section_reference": f"Page {chunk.page_number}",
                "region": document.region or "GLOBAL",
                "policy_id": document.policy_id if document.policy_id is not None else -1,
                "vector_id": vector_id,
                "status": "active",
            }
            vector_ids.append(vector_id)
            vector_texts.append(chunk.text)
            vector_metadatas.append(metadata)
            db_chunks.append(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    section_reference=f"Page {chunk.page_number}",
                    chunk_text=chunk.text,
                    vector_id=vector_id,
                    character_count=len(chunk.text),
                )
            )

        get_vector_store().add_chunks(vector_ids, vector_texts, vector_metadatas)
        db.add_all(db_chunks)
        document.status = DocumentStatus.ACTIVE
        document.failure_reason = None
        db.commit()
        return len(db_chunks)
    except Exception as exc:
        db.rollback()
        document.status = DocumentStatus.FAILED
        document.failure_reason = str(exc)[:500]
        db.commit()
        raise
