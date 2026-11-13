from __future__ import annotations

import time
import random
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

    return _discover_met_images_from_ids(
        object_ids[:search_limit],
        max_images=max_images,
        source_type=source_type,
        delay_seconds=delay_seconds,
        retries=retries,
        paintings_only=False,
    )


def discover_all_met_images(
    max_images: int,
    start_index: int = 0,
    object_batch_size: int | None = None,
    random_seed: int | None = None,
    paintings_only: bool = True,
    source_type: str = "master_artwork",
    delay_seconds: float = 0.1,
    retries: int = 3,
) -> list[ScrapedImage]:
    if max_images < 1:
        raise ValueError("max_images must be at least 1")
    if start_index < 0:
        raise ValueError("start_index cannot be negative")
    if object_batch_size is not None and object_batch_size < 1:
        raise ValueError("object_batch_size must be at least 1")
    if delay_seconds < 0:
        raise ValueError("delay_seconds cannot be negative")
    if retries < 0:
        raise ValueError("retries cannot be negative")
    if random_seed is not None and random_seed < 0:
        raise ValueError("random_seed cannot be negative")

    print("Downloading the Met object-ID list...", flush=True)
    objects_payload = _get_json(
        f"{MET_OBJECT_API_BASE}/objects",
        retries=retries,
    )
    object_ids = objects_payload.get("objectIDs", [])
    if not isinstance(object_ids, list):
        raise ValueError("Met API objects response has invalid objectIDs")
    if random_seed is not None:
        random.Random(random_seed).shuffle(object_ids)
        print("Using the persisted random object order.", flush=True)
    print(f"Found {len(object_ids)} object IDs; checking object details...", flush=True)

    end_index = (
        start_index + object_batch_size
        if object_batch_size is not None
        else len(object_ids)
    )
    object_ids_to_check = object_ids[start_index:end_index]
    print(
        f"Checking object IDs {start_index}-{start_index + len(object_ids_to_check) - 1}",
        flush=True,
    )
    return _discover_met_images_from_ids(
        object_ids_to_check,
        max_images=max_images,
        source_type=source_type,
        delay_seconds=delay_seconds,
        retries=retries,
        paintings_only=paintings_only,
    )


def _discover_met_images_from_ids(
    object_ids: list[Any],
    max_images: int,
    source_type: str,
    delay_seconds: float,
    retries: int,
    paintings_only: bool = False,
) -> list[ScrapedImage]:
    images: list[ScrapedImage] = []
    seen_urls: set[str] = set()
    object_ids_to_check = object_ids
    for index, object_id in enumerate(object_ids_to_check):
        if not isinstance(object_id, int):
            continue
        print(
            f"Checking object {index + 1}/{len(object_ids_to_check)} "
            f"(Met object ID: {object_id})",
            flush=True,
        )
        object_url = f"{MET_OBJECT_API_BASE}/objects/{object_id}"
        try:
            record = _get_json(object_url, retries=retries)
        except requests.RequestException as error:
            print(f"Skipping Met object {object_id}: {error}", flush=True)
        else:
            if paintings_only and (
                not isinstance(record.get("objectName"), str)
                or record["objectName"].strip().casefold() != "painting"
            ):
                continue
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
        if (index + 1) % 100 == 0:
            print(
                f"Checked {index + 1}/{len(object_ids_to_check)} objects; "
                f"found {len(images)} with images",
                flush=True,
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
