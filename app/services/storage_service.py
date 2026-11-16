from __future__ import annotations

from app.db.sqlite import insert_embedding
from app.domain.models import DEFAULT_SOURCE_INSTITUTION


def save_image_embedding(
    url: str,
    label: str | None,
    embedding: list[float],
    source_type: str = "unknown",
    source_page_url: str | None = None,
    source_institution: str = DEFAULT_SOURCE_INSTITUTION,
    artist: str | None = None,
    date: str | None = None,
    thumbnail_url: str | None = None,
    credit_line: str | None = None,
) -> bool:
    return insert_embedding(
        url=url,
        label=label,
        embedding=embedding,
        source_type=source_type,
        source_page_url=source_page_url,
        source_institution=source_institution,
        artist=artist,
        date=date,
        thumbnail_url=thumbnail_url,
        credit_line=credit_line,
    )
