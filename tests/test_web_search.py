from app.web_search import SearchDocument, search_documents


def test_search_documents_ranks_normalized_vectors_by_dot_product():
    documents = [
        SearchDocument(
            id=1,
            title="Close",
            artist=None,
            date=None,
            thumbnail_url="https://example.com/close-small.jpg",
            met_page_url="https://example.com/close",
            credit_line=None,
            vector=(1.0, 0.0),
        ),
        SearchDocument(
            id=2,
            title="Far",
            artist=None,
            date=None,
            thumbnail_url="https://example.com/far-small.jpg",
            met_page_url="https://example.com/far",
            credit_line=None,
            vector=(0.0, 1.0),
        ),
    ]

    results = search_documents((3.0, 0.0), documents, k=1)

    assert results[0].id == 1
    assert results[0].score == 1.0


def test_search_documents_rejects_dimension_mismatch():
    document = SearchDocument(
        id=1,
        title=None,
        artist=None,
        date=None,
        thumbnail_url=None,
        met_page_url=None,
        credit_line=None,
        vector=(1.0, 0.0),
    )

    try:
        search_documents((1.0,), [document], k=1)
    except ValueError as error:
        assert "Embedding dimension mismatch" in str(error)
    else:
        raise AssertionError("Expected a dimension mismatch to raise ValueError")
