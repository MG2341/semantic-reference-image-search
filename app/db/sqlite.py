from __future__ import annotations

import json
import os
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Sequence

from app.config import MODEL_NAME, MODEL_REVISION
from app.domain.models import (
    DEFAULT_SOURCE_INSTITUTION,
    SearchResult,
)
from app.services.search_service import (
    cosine_similarity,
    embedding_norm,
    normalize_embedding,
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
                artist TEXT,
                date TEXT,
                thumbnail_url TEXT,
                credit_line TEXT,
                object_name TEXT,
                medium TEXT,
                dimensions TEXT,
                height TEXT,
                width TEXT,
                department TEXT,
                classification TEXT,
                culture TEXT,
                period TEXT,
                dynasty TEXT,
                reign TEXT,
                country TEXT,
                accession_number TEXT,
                is_public_domain INTEGER,
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

            CREATE TABLE IF NOT EXISTS scrape_progress (
                source TEXT PRIMARY KEY,
                next_index INTEGER NOT NULL DEFAULT 0,
                random_seed INTEGER
            );

            """
        )
        _ensure_image_columns(conn)
        _ensure_progress_columns(conn)
        _migrate_met_source_urls(conn)
        _repair_embedding_dimensions(conn)
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


def get_scrape_progress(source: str) -> int:
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT next_index FROM scrape_progress WHERE source = ?",
            (source,),
        ).fetchone()
    return int(row["next_index"]) if row else 0


def get_or_create_scrape_seed(source: str) -> int:
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT random_seed FROM scrape_progress WHERE source = ?",
            (source,),
        ).fetchone()
        if row and row["random_seed"] is not None:
            return int(row["random_seed"])

        seed = secrets.randbits(63)
        conn.execute(
            """
            INSERT INTO scrape_progress (source, next_index, random_seed)
            VALUES (?, 0, ?)
            ON CONFLICT(source) DO UPDATE SET random_seed = excluded.random_seed
            """,
            (source, seed),
        )
        conn.commit()
        return seed


def set_scrape_progress(source: str, next_index: int) -> None:
    if next_index < 0:
        raise ValueError("next_index cannot be negative")
    with closing(get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO scrape_progress (source, next_index)
            VALUES (?, ?)
            ON CONFLICT(source) DO UPDATE SET next_index = excluded.next_index
            """,
            (source, next_index),
        )
        conn.commit()


def _ensure_progress_columns(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(scrape_progress)").fetchall()
    }
    if "random_seed" not in columns:
        conn.execute("ALTER TABLE scrape_progress ADD COLUMN random_seed INTEGER")


def _ensure_image_columns(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(images)").fetchall()
    }
    if "source_institution" not in columns:
        conn.execute(
            "ALTER TABLE images ADD COLUMN source_institution TEXT NOT NULL "
            "DEFAULT 'The Metropolitan Museum of Art'"
        )
    for column in (
        "artist",
        "date",
        "thumbnail_url",
        "credit_line",
        "object_name",
        "medium",
        "dimensions",
        "height",
        "width",
        "department",
        "classification",
        "culture",
        "period",
        "dynasty",
        "reign",
        "country",
        "accession_number",
        "is_public_domain",
    ):
        if column not in columns:
            column_type = "INTEGER" if column == "is_public_domain" else "TEXT"
            conn.execute(f"ALTER TABLE images ADD COLUMN {column} {column_type}")


def _migrate_met_source_urls(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE images
        SET source_page_url =
            'https://www.metmuseum.org/art/collection/search/' ||
            substr(source_page_url, instr(source_page_url, '/objects/') + 9)
        WHERE source_page_url LIKE
            'https://collectionapi.metmuseum.org/public/collection/v1/objects/%'
        """
    )


def _repair_embedding_dimensions(conn: sqlite3.Connection) -> int:
    repaired = 0
    rows = conn.execute(
        "SELECT id, dimensions, vector FROM embeddings"
    ).fetchall()
    for row in rows:
        try:
            actual_dimensions = len(json.loads(row["vector"]))
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        if row["dimensions"] != actual_dimensions:
            conn.execute(
                "UPDATE embeddings SET dimensions = ? WHERE id = ?",
                (actual_dimensions, row["id"]),
            )
            repaired += 1
    if repaired:
        conn.commit()
    return repaired


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
    artist: str | None = None,
    date: str | None = None,
    thumbnail_url: str | None = None,
    credit_line: str | None = None,
    object_name: str | None = None,
    medium: str | None = None,
    dimensions: str | None = None,
    height: str | None = None,
    width: str | None = None,
    department: str | None = None,
    classification: str | None = None,
    culture: str | None = None,
    period: str | None = None,
    dynasty: str | None = None,
    reign: str | None = None,
    country: str | None = None,
    accession_number: str | None = None,
    is_public_domain: bool | None = None,
) -> bool:
    vector = list(embedding)
    with closing(get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO images (
                image_url, source_page_url, title, artist, date, thumbnail_url,
                credit_line, object_name, medium, dimensions, height, width,
                department, classification, culture, period, dynasty, reign,
                country, accession_number, is_public_domain, source_type,
                source_institution
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(image_url) DO UPDATE SET
                title = COALESCE(images.title, excluded.title),
                source_page_url = COALESCE(images.source_page_url, excluded.source_page_url),
                artist = COALESCE(images.artist, excluded.artist),
                date = COALESCE(images.date, excluded.date),
                thumbnail_url = COALESCE(images.thumbnail_url, excluded.thumbnail_url),
                credit_line = COALESCE(images.credit_line, excluded.credit_line),
                object_name = COALESCE(images.object_name, excluded.object_name),
                medium = COALESCE(images.medium, excluded.medium),
                dimensions = COALESCE(images.dimensions, excluded.dimensions),
                height = COALESCE(images.height, excluded.height),
                width = COALESCE(images.width, excluded.width),
                department = COALESCE(images.department, excluded.department),
                classification = COALESCE(images.classification, excluded.classification),
                culture = COALESCE(images.culture, excluded.culture),
                period = COALESCE(images.period, excluded.period),
                dynasty = COALESCE(images.dynasty, excluded.dynasty),
                reign = COALESCE(images.reign, excluded.reign),
                country = COALESCE(images.country, excluded.country),
                accession_number = COALESCE(
                    images.accession_number, excluded.accession_number
                ),
                is_public_domain = COALESCE(
                    images.is_public_domain, excluded.is_public_domain
                ),
                source_institution = COALESCE(
                    images.source_institution, excluded.source_institution
                )
            """,
            (
                url,
                source_page_url or url,
                label,
                artist,
                date,
                thumbnail_url or url,
                credit_line,
                object_name,
                medium,
                dimensions,
                height,
                width,
                department,
                classification,
                culture,
                period,
                dynasty,
                reign,
                country,
                accession_number,
                is_public_domain,
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


def update_image_metadata(
    image_id: int,
    *,
    source_page_url: str,
    title: str | None,
    artist: str | None,
    date: str | None,
    thumbnail_url: str | None,
    credit_line: str | None,
    object_name: str | None,
    medium: str | None,
    dimensions: str | None,
    height: str | None,
    width: str | None,
    department: str | None,
    classification: str | None,
    culture: str | None,
    period: str | None,
    dynasty: str | None,
    reign: str | None,
    country: str | None,
    accession_number: str | None,
    is_public_domain: bool | None,
) -> None:
    with closing(get_connection()) as conn:
        conn.execute(
            """
            UPDATE images
            SET source_page_url = ?,
                title = ?,
                artist = ?,
                date = ?,
                thumbnail_url = ?,
                credit_line = ?,
                object_name = ?,
                medium = ?,
                dimensions = ?,
                height = ?,
                width = ?,
                department = ?,
                classification = ?,
                culture = ?,
                period = ?,
                dynasty = ?,
                reign = ?,
                country = ?,
                accession_number = ?,
                is_public_domain = ?
            WHERE id = ?
            """,
            (
                source_page_url,
                title,
                artist,
                date,
                thumbnail_url,
                credit_line,
                object_name,
                medium,
                dimensions,
                height,
                width,
                department,
                classification,
                culture,
                period,
                dynasty,
                reign,
                country,
                accession_number,
                is_public_domain,
                image_id,
            ),
        )
        conn.commit()


def search_embeddings(
    query_embedding: Sequence[float],
    top_k: int,
    source_types: Sequence[str] | None = None,
    model_name: str = MODEL_NAME,
    model_revision: str = MODEL_REVISION,
) -> list[SearchResult]:
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    query = normalize_embedding(query_embedding, "query_embedding")

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
        if embedding_norm(embedding) == 0:
            continue
        score = cosine_similarity(query, embedding)
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
