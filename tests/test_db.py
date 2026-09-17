from app.db.local_vector import TABLE_NAME, insert_embedding
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
