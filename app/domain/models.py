from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from typing import NamedTuple


SourceType = Literal[
    "photo",
    "movie_screencap",
    "master_artwork",
    "other",
    "unknown",
]


@dataclass(frozen=True)
class ImageRecord:
    image_url: str
    source_page_url: str
    title: str | None = None
    source_type: SourceType = "unknown"


class SearchResult(NamedTuple):
    image_url: str
    title: str | None
    source_type: str
    score: float
