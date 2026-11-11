from __future__ import annotations

import os
import time
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
    max_pages: int = 1,
    next_url_field: str | None = None,
    retries: int = 3,
) -> list[ScrapedImage]:
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")
    if retries < 0:
        raise ValueError("retries cannot be negative")

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    token = os.getenv("API_BEARER_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token

    images: list[ScrapedImage] = []
    seen: set[str] = set()
    next_url: str | None = api_url
    for _ in range(max_pages):
        if not next_url:
            break
        payload = _fetch_json(next_url, headers, retries)
        records = _read_records(payload, records_path)
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
                    source_page_url=next_url,
                    title=title if isinstance(title, str) else None,
                    source_type=source_type,
                )
            )
        next_value = _read_field(payload, next_url_field) if next_url_field else None
        next_url = next_value if isinstance(next_value, str) else None
    return images


def _fetch_json(url: str, headers: dict[str, str], retries: int) -> Any:
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")
