from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScrapedImage:
    image_url: str
    source_page_url: str
    title: str | None = None
