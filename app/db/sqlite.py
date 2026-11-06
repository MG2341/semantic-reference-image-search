from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Sequence


DB_PATH = Path(os.getenv("SQLITE_DB_PATH", "data/reference_images.db"))


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
                embedding TEXT NOT NULL
            )
            """
        )
        conn.commit()


def insert_embedding(
    url: str, label: str | None, embedding: Sequence[float]
) -> None:
    with closing(get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO image_embeddings (url, label, embedding)
            VALUES (?, ?, ?)
            """,
            (url, label, json.dumps(list(embedding))),
        )
        conn.commit()
