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
            "SELECT url, label, source_institution, embedding FROM image_embeddings"
        ).fetchone()

    assert row == (
        "https://example.com/image.jpg",
        "example",
        "The Metropolitan Museum of Art",
        json.dumps([1.0, 2.5]),
    )


def test_init_db_adds_source_institution_to_existing_images(tmp_path, monkeypatch):
    database_path = tmp_path / "existing.db"
    monkeypatch.setattr(sqlite, "DB_PATH", database_path)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE images (
                id INTEGER PRIMARY KEY,
                image_url TEXT NOT NULL UNIQUE,
                source_page_url TEXT NOT NULL,
                title TEXT,
                source_type TEXT NOT NULL DEFAULT 'unknown',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_checked_at TEXT
            )
            """
        )
        connection.execute(
            "INSERT INTO images (image_url, source_page_url) VALUES (?, ?)",
            ("https://example.com/existing.jpg", "https://example.com"),
        )
        connection.commit()

    sqlite.init_db()

    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            "SELECT source_institution FROM images"
        ).fetchone()

    assert row == ("The Metropolitan Museum of Art",)


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


def test_insert_embedding_stores_model_metadata(tmp_path, monkeypatch):
    database_path = tmp_path / "reference_images.db"
    monkeypatch.setattr(sqlite, "DB_PATH", database_path)

    sqlite.init_db()
    sqlite.insert_embedding(
        "https://example.com/image.jpg",
        "example",
        [1.0, 2.0, 3.0],
        model_name="test-model",
        model_revision="test-revision",
    )

    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            "SELECT model_name, model_revision, dimensions "
            "FROM embeddings"
        ).fetchone()

    assert row == ("test-model", "test-revision", 3)


def test_init_db_migrates_legacy_embeddings(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy.db"
    monkeypatch.setattr(sqlite, "DB_PATH", database_path)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE image_embeddings (
                url TEXT UNIQUE,
                label TEXT,
                source_type TEXT,
                embedding TEXT
            )
            """
        )
        connection.execute(
            "INSERT INTO image_embeddings VALUES (?, ?, ?, ?)",
            (
                "https://example.com/legacy.jpg",
                "Legacy",
                "photo",
                "[1.0, 0.0]",
            ),
        )
        connection.commit()

    sqlite.init_db()

    with closing(sqlite3.connect(database_path)) as connection:
        image = connection.execute(
            "SELECT image_url, title, source_type FROM images"
        ).fetchone()
        embedding = connection.execute(
            "SELECT dimensions, vector FROM embeddings"
        ).fetchone()
        legacy_object = connection.execute(
            "SELECT type FROM sqlite_master WHERE name = 'image_embeddings'"
        ).fetchone()

    assert image == ("https://example.com/legacy.jpg", "Legacy", "photo")
    assert embedding == (2, "[1.0, 0.0]")
    assert legacy_object == ("view",)


def test_search_embeddings_rejects_dimension_mismatch(tmp_path, monkeypatch):
    database_path = tmp_path / "reference_images.db"
    monkeypatch.setattr(sqlite, "DB_PATH", database_path)

    sqlite.init_db()
    sqlite.insert_embedding("https://example.com/image.jpg", "example", [1.0, 0.0])

    try:
        sqlite.search_embeddings([1.0], top_k=1)
    except ValueError as error:
        assert "Embedding dimension mismatch" in str(error)
    else:
        raise AssertionError("Expected a dimension mismatch to raise ValueError")
