from __future__ import annotations

import json
import math
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Sequence

from app.config import MODEL_NAME, MODEL_REVISION
from app.domain.models import (
    DEFAULT_SOURCE_INSTITUTION,
    ImageRecord,
    SearchResult,
)


DB_PATH = Path(os.getenv("SQLITE_DB_PATH", "data/reference_images.db"))
DEFAULT_SOURCE_TYPE = "unknown"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with closing(get_connection()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_url TEXT NOT NULL UNIQUE,
                source_page_url TEXT NOT NULL,
                title TEXT,
                source_type TEXT NOT NULL DEFAULT 'unknown',
                source_institution TEXT NOT NULL DEFAULT 'The Metropolitan Museum of Art',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_checked_at TEXT
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
                model_name TEXT NOT NULL,
                model_revision TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                vector TEXT NOT NULL,
                UNIQUE(image_id, model_name, model_revision)
            );

            """
        )
        _ensure_image_columns(conn)
        _migrate_legacy_embeddings(conn)
        conn.execute("DROP VIEW IF EXISTS image_embeddings")
        conn.execute(
            """
            CREATE VIEW IF NOT EXISTS image_embeddings AS
            SELECT images.image_url AS url,
                   images.title AS label,
                   images.source_type,
                   images.source_institution,
                   embeddings.vector AS embedding
            FROM images
            JOIN embeddings ON embeddings.image_id = images.id
            """
        )
        conn.commit()


def _ensure_image_columns(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(images)").fetchall()
    }
    if "source_institution" not in columns:
        conn.execute(
            "ALTER TABLE images ADD COLUMN source_institution TEXT NOT NULL "
            "DEFAULT 'The Metropolitan Museum of Art'"
        )


def _migrate_legacy_embeddings(conn: sqlite3.Connection) -> None:
    legacy = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name = 'image_embeddings'"
    ).fetchone()
    if legacy is None:
        return

    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(image_embeddings)").fetchall()
    }
    source_type_expression = (
        "source_type" if "source_type" in columns else "'unknown'"
    )
    rows = conn.execute(
        f"SELECT url, label, {source_type_expression} AS source_type, embedding "
        "FROM image_embeddings"
    ).fetchall()
    for row in rows:
        conn.execute(
            """
            INSERT INTO images (image_url, source_page_url, title, source_type)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(image_url) DO NOTHING
            """,
            (
                row["url"],
                row["url"],
                row["label"],
                row["source_type"],
            ),
        )
        image = conn.execute(
            "SELECT id FROM images WHERE image_url = ?", (row["url"],)
        ).fetchone()
        vector = json.loads(row["embedding"])
        conn.execute(
            """
            INSERT INTO embeddings (
                image_id, model_name, model_revision, dimensions, vector
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(image_id, model_name, model_revision) DO NOTHING
            """,
            (
                image["id"],
                MODEL_NAME,
                MODEL_REVISION,
                len(vector),
                row["embedding"],
            ),
        )
    conn.execute("DROP TABLE image_embeddings")


def insert_embedding(
    url: str,
    label: str | None,
    embedding: Sequence[float],
    source_type: str = DEFAULT_SOURCE_TYPE,
    source_page_url: str | None = None,
    source_institution: str = DEFAULT_SOURCE_INSTITUTION,
    model_name: str = MODEL_NAME,
    model_revision: str = MODEL_REVISION,
) -> bool:
    vector = list(embedding)
    with closing(get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO images (
                image_url, source_page_url, title, source_type, source_institution
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(image_url) DO UPDATE SET
                title = COALESCE(images.title, excluded.title),
                source_page_url = COALESCE(images.source_page_url, excluded.source_page_url),
                source_institution = COALESCE(
                    images.source_institution, excluded.source_institution
                )
            """,
            (
                url,
                source_page_url or url,
                label,
                source_type,
                source_institution,
            ),
        )
        image = conn.execute(
            "SELECT id FROM images WHERE image_url = ?", (url,)
        ).fetchone()
        cursor = conn.execute(
            """
            INSERT INTO embeddings (
                image_id, model_name, model_revision, dimensions, vector
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(image_id, model_name, model_revision) DO NOTHING
            """,
            (
                image["id"],
                model_name,
                model_revision,
                len(vector),
                json.dumps(vector),
            ),
        )
        conn.commit()
        return cursor.rowcount == 1


def existing_image_urls(urls: Sequence[str]) -> set[str]:
    if not urls:
        return set()
    placeholders = ",".join("?" for _ in urls)
    with closing(get_connection()) as conn:
        rows = conn.execute(
            f"SELECT image_url FROM images WHERE image_url IN ({placeholders})",
            tuple(urls),
        ).fetchall()
    return {row["image_url"] for row in rows}


def search_embeddings(
    query_embedding: Sequence[float],
    top_k: int,
    source_types: Sequence[str] | None = None,
    model_name: str = MODEL_NAME,
    model_revision: str = MODEL_REVISION,
) -> list[SearchResult]:
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    query = list(query_embedding)
    query_norm = math.sqrt(sum(value * value for value in query))
    if query_norm == 0:
        raise ValueError("query_embedding must not be a zero vector")

    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT images.image_url, images.title, images.source_type,
                   embeddings.dimensions, embeddings.vector
            FROM images
            JOIN embeddings ON embeddings.image_id = images.id
            WHERE embeddings.model_name = ?
              AND embeddings.model_revision = ?
            """,
            (model_name, model_revision),
        ).fetchall()

    allowed_types = set(source_types) if source_types else None
    results: list[SearchResult] = []
    for row in rows:
        if allowed_types is not None and row["source_type"] not in allowed_types:
            continue
        if row["dimensions"] != len(query):
            raise ValueError(
                f"Embedding dimension mismatch for {row['image_url']}: "
                f"expected {len(query)}, got {row['dimensions']}"
            )
        embedding = json.loads(row["vector"])
        embedding_norm = math.sqrt(sum(value * value for value in embedding))
        if embedding_norm == 0:
            continue
        score = sum(
            query_value * image_value
            for query_value, image_value in zip(query, embedding)
        ) / (query_norm * embedding_norm)
        results.append(
            SearchResult(
                image_url=row["image_url"],
                title=row["title"],
                source_type=row["source_type"],
                score=score,
            )
        )

    results.sort(key=lambda result: result.score, reverse=True)
    return results[:top_k]
