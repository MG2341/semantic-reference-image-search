from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

import requests

from app.scraping.models import ScrapedImage


MET_API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1.1"
MET_OBJECT_API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
USER_AGENT = "reference-image-searcher/0.1"


def discover_met_images(
    query: str,
    max_images: int,
    source_type: str = "master_artwork",
    delay_seconds: float = 0.1,
    retries: int = 3,
) -> list[ScrapedImage]:
    if not query.strip():
        raise ValueError("query cannot be empty")
    if max_images < 1:
        raise ValueError("max_images must be at least 1")
    if delay_seconds < 0:
        raise ValueError("delay_seconds cannot be negative")
    if retries < 0:
        raise ValueError("retries cannot be negative")

    search_url = f"{MET_API_BASE}/search"
    search_limit = min(500, max(100, max_images * 5))
    search_payload = _get_json(
        search_url,
        params={"q": query, "hasImages": "true", "limit": search_limit},
        retries=retries,
    )
    object_ids = search_payload.get("objectIDs", [])
    if not isinstance(object_ids, list):
        raise ValueError("Met API search response has invalid objectIDs")

    images: list[ScrapedImage] = []
    seen_urls: set[str] = set()
    object_ids_to_check = object_ids[:search_limit]
    for index, object_id in enumerate(object_ids_to_check):
        if not isinstance(object_id, int):
            continue
        object_url = f"{MET_OBJECT_API_BASE}/objects/{object_id}"
        try:
            record = _get_json(object_url, retries=retries)
        except requests.RequestException as error:
            print(f"Skipping Met object {object_id}: {error}", flush=True)
        else:
            image_url = record.get("primaryImage")
            if isinstance(image_url, str) and image_url and image_url not in seen_urls:
                seen_urls.add(image_url)
                title = record.get("title")
                artist = record.get("artistDisplayName")
                label = title if isinstance(title, str) else None
                if isinstance(artist, str) and artist:
                    label = f"{label} - {artist}" if label else artist
                images.append(
                    ScrapedImage(
                        image_url=image_url,
                        source_page_url=object_url,
                        title=label,
                        source_type=source_type,
                    )
                )
        if len(images) >= max_images:
            break
        if index < len(object_ids_to_check) - 1:
            time.sleep(delay_seconds)

    return images


def _get_json(
    url: str,
    params: Mapping[str, Any] | None = None,
    retries: int = 3,
) -> dict[str, Any]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError(f"Met API response from {url} must be an object")
            return payload
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")
