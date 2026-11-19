import pytest

from app.services.search_service import cosine_similarity, normalize_embedding


def test_cosine_similarity_normalizes_vectors():
    assert cosine_similarity((3.0, 0.0), (2.0, 0.0)) == 1.0


def test_normalize_embedding_rejects_zero_vector():
    with pytest.raises(ValueError, match="zero vector"):
        normalize_embedding((0.0, 0.0))


def test_cosine_similarity_rejects_dimension_mismatch():
    with pytest.raises(ValueError, match="Embedding dimension mismatch"):
        cosine_similarity((1.0, 0.0), (1.0,))
