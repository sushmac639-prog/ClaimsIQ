from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    page_number: int
    text: str


def split_pages(pages: list[tuple[int, str]]) -> list[TextChunk]:
    if settings.rag_chunk_size <= 0:
        raise ValueError("RAG_CHUNK_SIZE must be positive")
    if settings.rag_chunk_overlap < 0 or settings.rag_chunk_overlap >= settings.rag_chunk_size:
        raise ValueError("RAG_CHUNK_OVERLAP must be between 0 and RAG_CHUNK_SIZE - 1")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
    )

    chunks: list[TextChunk] = []
    index = 0
    for page_number, text in pages:
        text = text.replace("\x00", " ").replace("\r\n", "\n").strip()
        if not text:
            continue
        for piece in splitter.split_text(text):
            piece = piece.strip()
            if piece:
                chunks.append(TextChunk(index, page_number, piece))
                index += 1
    return chunks
