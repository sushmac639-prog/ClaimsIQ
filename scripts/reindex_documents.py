from sqlalchemy import select 
 
from app.db.models import Document, DocumentStatus 
from app.db.session import SessionLocal 
from app.rag.ingestion import ingest_document 
 
 
def main() -> None: 
    with SessionLocal() as db: 
        documents = list( 
            db.scalars( 
                select(Document).where( 
                    Document.status == DocumentStatus.ACTIVE 
                ) 
            ).all() 
        ) 
        for document in documents: 
            document.status = DocumentStatus.PROCESSING 
            db.commit() 
            count = ingest_document(db, document) 
            print(f"Reindexed document {document.id}: {count} chunks") 
 
 
if __name__ == "__main__": 
    main()