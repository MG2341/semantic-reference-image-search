from app.db.local_vector import TABLE_NAME, insert_embedding, search_embeddings
from qdrant_client import QdrantClient


def test_insert_embedding_creates_local_table(tmp_path):
    insert_embedding(
        url="https://example.com/image.jpg",
        label="test image",
        embedding=[1.0, 2.5, 3.0],
        path=tmp_path,
    )

    db = QdrantClient(path=str(tmp_path))
    records, _ = db.scroll(collection_name=TABLE_NAME, limit=10, with_payload=True)

    assert len(records) == 1
    assert records[0].payload["label"] == "test image"


def test_search_embeddings_returns_best_matches_first(tmp_path):
    insert_embedding("red", "red image", [1.0, 0.0], path=tmp_path)
    insert_embedding("blue", "blue image", [0.0, 1.0], path=tmp_path)

    results = search_embeddings([0.9, 0.1], limit=1, path=tmp_path)

    assert len(results) == 1
    assert results[0]["url"] == "red"
