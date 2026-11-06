import json
import sqlite3
from contextlib import closing

from app.db import sqlite


def test_insert_embedding_stores_json_vector(tmp_path, monkeypatch):
    database_path = tmp_path / "reference_images.db"
    monkeypatch.setattr(sqlite, "DB_PATH", database_path)

    sqlite.init_db()
    sqlite.insert_embedding("https://example.com/image.jpg", "example", [1.0, 2.5])

    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            "SELECT url, label, embedding FROM image_embeddings"
        ).fetchone()

    assert row == (
        "https://example.com/image.jpg",
        "example",
        json.dumps([1.0, 2.5]),
    )
