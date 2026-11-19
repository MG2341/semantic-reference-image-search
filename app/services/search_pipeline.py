from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Generic, TypeVar


InputT = TypeVar("InputT")
ResultT = TypeVar("ResultT")

EmbeddingEncoder = Callable[[InputT], Sequence[float]]
EmbeddingSearcher = Callable[[Sequence[float], int], list[ResultT]]


class EmbeddingSearchPipeline(Generic[InputT, ResultT]):
    """Combine an input modality encoder with an embedding search backend."""

    def __init__(
        self,
        encoder: EmbeddingEncoder[InputT],
        searcher: EmbeddingSearcher[ResultT],
    ) -> None:
        self._encoder = encoder
        self._searcher = searcher

    def search(self, value: InputT, top_k: int) -> list[ResultT]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        embedding = self._encoder(value)
        return self._searcher(embedding, top_k)
