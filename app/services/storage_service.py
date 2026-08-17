from __future__ import annotations

from app.db.postgres import insert_embedding


def save_image_embedding(url: str, label: str | None, embedding: list[float]) -> None:
    insert_embedding(url=url, label=label, embedding=embedding)
