from app.db import embedding_to_pgvector


def test_embedding_to_pgvector_formats_float_list():
    result = embedding_to_pgvector([1.0, 2.5, 3.0])
    assert result == "[1.0,2.5,3.0]"
