import pytest

from app.services.search_pipeline import EmbeddingSearchPipeline


def test_pipeline_encodes_input_before_searching():
    calls = []
    pipeline = EmbeddingSearchPipeline(
        encoder=lambda value: [len(value), 0.0],
        searcher=lambda embedding, top_k: calls.append((embedding, top_k)) or ["match"],
    )

    assert pipeline.search("reference image", 3) == ["match"]
    assert calls == [([15, 0.0], 3)]


def test_pipeline_rejects_invalid_top_k_before_encoding():
    encoded = []
    pipeline = EmbeddingSearchPipeline(
        encoder=lambda value: encoded.append(value) or [1.0],
        searcher=lambda embedding, top_k: [],
    )

    with pytest.raises(ValueError, match="top_k must be at least 1"):
        pipeline.search(object(), 0)

    assert encoded == []
