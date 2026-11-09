from __future__ import annotations

import json
import math
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Sequence


DB_PATH = Path(os.getenv("SQLITE_DB_PATH", "data/reference_images.db"))
DEFAULT_SOURCE_TYPE = "unknown"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with closing(get_connection()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS image_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                label TEXT,
                source_type TEXT NOT NULL DEFAULT 'unknown',
                embedding TEXT NOT NULL
            )
            """
        )
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(image_embeddings)").fetchall()
        }
        if "source_type" not in columns:
            conn.execute(
                "ALTER TABLE image_embeddings ADD COLUMN "
                "source_type TEXT NOT NULL DEFAULT 'unknown'"
            )
        conn.execute(
            """
            DELETE FROM image_embeddings
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM image_embeddings
                GROUP BY url
            )
            """
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_image_embeddings_url "
            "ON image_embeddings (url)"
        )
        conn.commit()


def insert_embedding(
    url: str,
    label: str | None,
    embedding: Sequence[float],
    source_type: str = DEFAULT_SOURCE_TYPE,
) -> bool:
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO image_embeddings (url, label, source_type, embedding)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url) DO NOTHING
            """,
            (url, label, source_type, json.dumps(list(embedding))),
        )
        conn.commit()
        return cursor.rowcount == 1


def search_embeddings(
    query_embedding: Sequence[float],
    top_k: int,
    source_types: Sequence[str] | None = None,
) -> list[tuple[str, str | None, str, float]]:
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    query = list(query_embedding)
    query_norm = math.sqrt(sum(value * value for value in query))
    if query_norm == 0:
        raise ValueError("query_embedding must not be a zero vector")

    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT url, label, source_type, embedding FROM image_embeddings"
        ).fetchall()

    allowed_types = set(source_types) if source_types else None
    results: list[tuple[str, str | None, str, float]] = []
    for url, label, source_type, serialized_embedding in rows:
        if allowed_types is not None and source_type not in allowed_types:
            continue
        embedding = json.loads(serialized_embedding)
        if len(embedding) != len(query):
            raise ValueError(
                f"Embedding dimension mismatch for {url}: "
                f"expected {len(query)}, got {len(embedding)}"
            )
        embedding_norm = math.sqrt(sum(value * value for value in embedding))
        if embedding_norm == 0:
            continue
        score = sum(
            query_value * image_value
            for query_value, image_value in zip(query, embedding)
        ) / (query_norm * embedding_norm)
        results.append((url, label, source_type, score))

    results.sort(key=lambda result: result[2], reverse=True)
    return results[:top_k]
