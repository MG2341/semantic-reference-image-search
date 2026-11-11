from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import requests

from app.scraping.models import ScrapedImage, SourceType


USER_AGENT = "reference-image-searcher/0.1"


def _read_field(record: Mapping[str, Any], field_path: str) -> Any:
    value: Any = record
    for part in field_path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def _read_records(payload: Any, records_path: str | None) -> list[Mapping[str, Any]]:
    records: Any = payload
    if records_path:
        for part in records_path.split("."):
            if not isinstance(records, Mapping) or part not in records:
                raise ValueError(f"API response does not contain '{records_path}'")
            records = records[part]

    if not isinstance(records, list) or not all(
        isinstance(record, Mapping) for record in records
    ):
        raise ValueError("The selected API response value must be a list of objects")
    return list(records)


def discover_images(
    api_url: str,
    image_field: str,
    title_field: str | None,
    records_path: str | None,
    source_type: SourceType,
) -> list[ScrapedImage]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    token = os.getenv("API_BEARER_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(api_url, headers=headers, timeout=30)
    response.raise_for_status()
    records = _read_records(response.json(), records_path)

    images: list[ScrapedImage] = []
    seen: set[str] = set()
    for record in records:
        image_url = _read_field(record, image_field)
        if not isinstance(image_url, str):
            continue
        if urlparse(image_url).scheme not in {"http", "https"}:
            continue
        if image_url in seen:
            continue
        seen.add(image_url)

        title = _read_field(record, title_field) if title_field else None
        images.append(
            ScrapedImage(
                image_url=image_url,
                source_page_url=api_url,
                title=title if isinstance(title, str) else None,
                source_type=source_type,
            )
        )
    return images
