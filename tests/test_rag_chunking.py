from app.rag.chunking import split_pages


def test_split_pages_preserves_page_numbers():
    chunks = split_pages([(1, "A " * 1000), (2, "B " * 1000)])
    assert chunks
    assert chunks[0].page_number == 1
    assert any(chunk.page_number == 2 for chunk in chunks)
