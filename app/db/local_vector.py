from __future__ import annotations

import os
import hashlib
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


DB_PATH = Path(os.getenv("VECTOR_DB_PATH", "data"))
TABLE_NAME = "image_embeddings"


def init_db(path: str | Path = DB_PATH) -> None:
    """Create the local database directory when the application starts."""
    Path(path).mkdir(parents=True, exist_ok=True)
    QdrantClient(path=str(path))


def insert_embedding(
    url: str,
    label: str | None,
    embedding: list[float],
    path: str | Path = DB_PATH,
) -> None:
    db = QdrantClient(path=str(path))

    if not db.collection_exists(TABLE_NAME):
        db.create_collection(
            collection_name=TABLE_NAME,
            vectors_config=VectorParams(size=len(embedding), distance=Distance.COSINE),
        )

    db.upsert(
        collection_name=TABLE_NAME,
        points=[
            PointStruct(
                id=uuid5(
                    NAMESPACE_URL,
                    hashlib.sha256(
                        f"{url}\0{label}\0{','.join(map(str, embedding))}".encode()
                    ).hexdigest(),
                ),
                vector=embedding,
                payload={"url": url, "label": label},
            )
        ],
    )