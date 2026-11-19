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

DEFAULT_SOURCE_INSTITUTION = "Unknown"
MET_SOURCE_INSTITUTION = "The Metropolitan Museum of Art"


@dataclass(frozen=True)
class ImageRecord:
    image_url: str
    source_page_url: str
    title: str | None = None
    source_type: SourceType = "unknown"
    source_institution: str = DEFAULT_SOURCE_INSTITUTION
    artist: str | None = None
    date: str | None = None
    thumbnail_url: str | None = None
    credit_line: str | None = None
    object_name: str | None = None
    medium: str | None = None
    dimensions: str | None = None
    height: str | None = None
    width: str | None = None
    department: str | None = None
    classification: str | None = None
    culture: str | None = None
    period: str | None = None
    dynasty: str | None = None
    reign: str | None = None
    country: str | None = None
    accession_number: str | None = None
    is_public_domain: bool | None = None


class SearchResult(NamedTuple):
    image_url: str
    title: str | None
    source_type: str
    score: float
