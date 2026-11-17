from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence

from app.config import MODEL_NAME, MODEL_REVISION
from app.db.sqlite import get_connection
from app.services.search_service import (
    cosine_similarity,
    embedding_norm,
    normalize_embedding,
)


@dataclass(frozen=True)
class SearchDocument:
    id: int
    title: str | None
    artist: str | None
    date: str | None
    thumbnail_url: str | None
    met_page_url: str | None
    credit_line: str | None
    vector: tuple[float, ...]


@dataclass(frozen=True)
class SearchMatch:
    id: int
    title: str | None
    artist: str | None
    date: str | None
    thumbnail_url: str | None
    met_page_url: str | None
    credit_line: str | None
    score: float


def load_search_documents() -> list[SearchDocument]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT images.id, images.title, images.artist, images.date,
                   images.thumbnail_url, images.source_page_url, images.credit_line,
                   embeddings.dimensions, embeddings.vector
            FROM images
            JOIN embeddings ON embeddings.image_id = images.id
            WHERE embeddings.model_name = ?
              AND embeddings.model_revision = ?
            """,
            (MODEL_NAME, MODEL_REVISION),
        ).fetchall()

    documents: list[SearchDocument] = []
    for row in rows:
        vector = tuple(float(value) for value in json.loads(row["vector"]))
        if row["dimensions"] != len(vector):
            raise ValueError(f"Stored dimension mismatch for image {row['id']}")
        if embedding_norm(vector) == 0:
            continue
        normalized_vector = normalize_embedding(vector)
        documents.append(
            SearchDocument(
                id=row["id"],
                title=row["title"],
                artist=row["artist"],
                date=row["date"],
                thumbnail_url=row["thumbnail_url"],
                met_page_url=row["source_page_url"],
                credit_line=row["credit_line"],
                vector=normalized_vector,
            )
        )
    return documents


def search_documents(
    query_embedding: Sequence[float],
    documents: Sequence[SearchDocument],
    k: int,
) -> list[SearchMatch]:
    if k < 1:
        raise ValueError("k must be at least 1")

    normalized_query = normalize_embedding(query_embedding, "query_embedding")

    matches: list[SearchMatch] = []
    for document in documents:
        if len(document.vector) != len(normalized_query):
            raise ValueError(f"Embedding dimension mismatch for image {document.id}")
        score = cosine_similarity(normalized_query, document.vector)
        matches.append(
            SearchMatch(
                id=document.id,
                title=document.title,
                artist=document.artist,
                date=document.date,
                thumbnail_url=document.thumbnail_url,
                met_page_url=document.met_page_url,
                credit_line=document.credit_line,
                score=score,
            )
        )

    matches.sort(key=lambda match: match.score, reverse=True)
    return matches[:k]
