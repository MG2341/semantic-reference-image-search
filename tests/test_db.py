import json
import sqlite3
from contextlib import closing

from app.db import sqlite


def test_insert_embedding_stores_json_vector(tmp_path, monkeypatch):
    database_path = tmp_path / "reference_images.db"
    monkeypatch.setattr(sqlite, "DB_PATH", database_path)

    sqlite.init_db()
    assert sqlite.insert_embedding(
        "https://example.com/image.jpg", "example", [1.0, 2.5]
    )

    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            "SELECT url, label, embedding FROM image_embeddings"
        ).fetchone()

    assert row == (
        "https://example.com/image.jpg",
        "example",
        json.dumps([1.0, 2.5]),
    )


def test_search_embeddings_returns_highest_similarity_first(tmp_path, monkeypatch):
    database_path = tmp_path / "reference_images.db"
    monkeypatch.setattr(sqlite, "DB_PATH", database_path)

    sqlite.init_db()
    sqlite.insert_embedding("https://example.com/close.jpg", "close", [1.0, 0.0])
    sqlite.insert_embedding("https://example.com/far.jpg", "far", [0.0, 1.0])

    results = sqlite.search_embeddings([1.0, 0.0], top_k=1)

    assert results == [("https://example.com/close.jpg", "close", "unknown", 1.0)]


def test_search_embeddings_filters_source_types(tmp_path, monkeypatch):
    database_path = tmp_path / "reference_images.db"
    monkeypatch.setattr(sqlite, "DB_PATH", database_path)

    sqlite.init_db()
    sqlite.insert_embedding(
        "https://example.com/photo.jpg", "photo", [1.0, 0.0], "photo"
    )
    sqlite.insert_embedding(
        "https://example.com/movie.jpg",
        "movie",
        [1.0, 0.0],
        "movie_screencap",
    )

    results = sqlite.search_embeddings(
        [1.0, 0.0], top_k=5, source_types=["movie_screencap"]
    )

    assert results == [
        ("https://example.com/movie.jpg", "movie", "movie_screencap", 1.0)
    ]


def test_insert_embedding_skips_duplicate_url(tmp_path, monkeypatch):
    database_path = tmp_path / "reference_images.db"
    monkeypatch.setattr(sqlite, "DB_PATH", database_path)

    sqlite.init_db()

    assert sqlite.insert_embedding("https://example.com/image.jpg", "first", [1.0])
    assert not sqlite.insert_embedding("https://example.com/image.jpg", "second", [0.0])

    with closing(sqlite3.connect(database_path)) as connection:
        rows = connection.execute(
            "SELECT url, label, source_type, embedding FROM image_embeddings"
        ).fetchall()

    assert rows == [
        ("https://example.com/image.jpg", "first", "unknown", "[1.0]")
    ]
