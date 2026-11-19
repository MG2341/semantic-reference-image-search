from __future__ import annotations

import math
from typing import Sequence


def normalize_embedding(
    vector: Sequence[float], name: str = "embedding"
) -> tuple[float, ...]:
    values = tuple(float(value) for value in vector)
    norm = embedding_norm(values)
    if norm == 0:
        raise ValueError(f"{name} must not be a zero vector")
    return tuple(value / norm for value in values)


def embedding_norm(vector: Sequence[float]) -> float:
    return math.sqrt(sum(float(value) * float(value) for value in vector))


def cosine_similarity(
    query_embedding: Sequence[float],
    document_embedding: Sequence[float],
) -> float:
    query = normalize_embedding(query_embedding, "query_embedding")
    document = normalize_embedding(document_embedding, "document_embedding")
    if len(query) != len(document):
        raise ValueError(
            "Embedding dimension mismatch: "
            f"query has {len(query)} values, document has {len(document)}"
        )
    return normalized_dot_product(query, document)


def normalized_dot_product(
    first: Sequence[float],
    second: Sequence[float],
) -> float:
    if len(first) != len(second):
        raise ValueError(
            "Embedding dimension mismatch: "
            f"first has {len(first)} values, second has {len(second)}"
        )
    return sum(
        query_value * document_value
        for query_value, document_value in zip(first, second)
    )
