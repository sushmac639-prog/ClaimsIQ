from sqlalchemy import select

from app.db.models import Document, DocumentStatus
from app.db.session import SessionLocal
from app.rag.ingestion import ingest_document
from app.rag.vector_store import get_vector_store


def main() -> None:
    with SessionLocal() as db:
        documents = list(db.scalars(select(Document).where(Document.status == DocumentStatus.ACTIVE)).all())
        for document in documents:
            get_vector_store().delete_document(document.id)
            document.status = DocumentStatus.PROCESSING
            db.commit()
            count = ingest_document(db, document)
            print(f"Reindexed document {document.id}: {count} chunks")


if __name__ == "__main__":
    main()
