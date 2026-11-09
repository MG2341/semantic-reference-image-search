from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


SourceType = Literal[
    "photo",
    "movie_screencap",
    "master_artwork",
    "other",
    "unknown",
]


@dataclass(frozen=True)
class ScrapedImage:
    image_url: str
    source_page_url: str
    title: str | None = None
    source_type: SourceType = "unknown"
