from app.rag.service import NO_MATCH, build_context
from app.rag.vector_store import RetrievedChunk


def test_rag_no_match_message_is_explicit():
    assert NO_MATCH == "No relevant information was found in the approved documents."


def test_rag_context_contains_source_reference():
    chunk = RetrievedChunk(
        document_id=1,
        filename="policy.pdf",
        page_number=3,
        section_reference="Page 3",
        chunk_index=0,
        text="Hospitalization coverage is available subject to the policy terms.",
        similarity=0.91,
    )
    context, sources = build_context([chunk])
    assert "[S1]" in context
    assert sources[0].filename == "policy.pdf"
    assert sources[0].page_number == 3
