from dataclasses import dataclass
from typing import Any

from langchain_chroma import Chroma

from app.core.config import settings
from app.llm.openai_client import get_openai_client


@dataclass(frozen=True)
class RetrievedChunk:
    vector_id: str
    document_id: int
    filename: str
    chunk_index: int
    page_number: int | None
    section_reference: str | None
    region: str | None
    policy_id: int | None
    text: str
    distance: float
    similarity: float


class VectorStore:
    def __init__(self) -> None:
        settings.chroma_persist_directory.mkdir(parents=True, exist_ok=True)
        self.store = Chroma(
            collection_name=settings.chroma_collection,
            persist_directory=str(settings.chroma_persist_directory),
            embedding_function=get_openai_client().embeddings,
        )

    def add_chunks(self, ids: list[str], texts: list[str], metadatas: list[dict[str, Any]]) -> None:
        if not (len(ids) == len(texts) == len(metadatas)):
            raise ValueError("Vector fields must have equal lengths")
        if ids:
            self.store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    def delete_document(self, document_id: int) -> None:
        result = self.store.get(where={"document_id": document_id})
        ids = result.get("ids", [])
        if ids:
            self.store.delete(ids=ids)

    def search(self, query: str, top_k: int, where: dict[str, Any] | None = None) -> list[RetrievedChunk]:
        print(f"Chroma query: {query}")
        print(f"Chroma filter: {where}")
        print(f"Chroma collection count: {self.store._collection.count()}")
        collection = self.store._collection

        print("Chroma collection count:", collection.count())

        print(
            "Chroma stored records:",
            collection.get(
                include=["metadatas", "documents"]
            )
        )
        results = self.store.similarity_search_with_score(query, k=top_k, filter=where)

        items: list[RetrievedChunk] = []
        for document, distance in results:
            metadata = document.metadata
            distance_value = float(distance or 0.0)
            similarity = max(0.0, min(1.0, 1.0 - distance_value))
            raw_policy_id = metadata.get("policy_id")
            policy_id = None if raw_policy_id in (None, -1, "-1") else int(raw_policy_id)
            items.append(
                RetrievedChunk(
                    vector_id=str(metadata.get("vector_id", "")),
                    document_id=int(metadata["document_id"]),
                    filename=str(metadata.get("filename", "")),
                    chunk_index=int(metadata.get("chunk_index", 0)),
                    page_number=int(metadata["page_number"]) if metadata.get("page_number") is not None else None,
                    section_reference=metadata.get("section_reference"),
                    region=metadata.get("region"),
                    policy_id=policy_id,
                    text=document.page_content,
                    distance=distance_value,
                    similarity=similarity,
                )
            )
        return items


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
