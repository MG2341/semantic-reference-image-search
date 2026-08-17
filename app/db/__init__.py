from __future__ import annotations

from typing import Sequence


def embedding_to_pgvector(values: Sequence[float]) -> str:
    """Convert a list of floats to the PostgreSQL pgvector literal format."""
    return str(list(values)).replace(" ", "")
