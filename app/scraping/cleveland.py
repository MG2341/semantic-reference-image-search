from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import requests

from app.scraping.models import ScrapedImage


CLEVELAND_API_URL = "https://openaccess-api.clevelandart.org/api/artworks/"
CLEVELAND_SOURCE_INSTITUTION = "Cleveland Museum of Art"
USER_AGENT = "reference-image-searcher/0.1"
MAX_API_PAGE_SIZE = 1000

_FIELDS = ",".join(
    (
        "id",
        "accession_number",
        "title",
        "creation_date",
        "creators",
        "culture",
        "technique",
        "department",
        "type",
        "measurements",
        "dimensions",
        "creditline",
        "url",
        "images",
        "share_license_status",
    )
)


def extract_cleveland_metadata(record: Mapping[str, Any]) -> dict[str, Any]:
    images = record.get("images")
    web_image = images.get("web") if isinstance(images, Mapping) else None
    image_url = _string_value(web_image, "url")
    if image_url is None or urlparse(image_url).scheme not in {"http", "https"}:
        raise ValueError("Cleveland artwork has no valid web image URL")

    artwork_id = record.get("id")
    accession_number = _string_value(record, "accession_number")
    source_page_url = _string_value(record, "url")
    if source_page_url is None:
        page_id = accession_number or str(artwork_id)
        source_page_url = f"https://www.clevelandart.org/art/{page_id}"

    return {
        "image_url": image_url,
        "source_page_url": source_page_url,
        "title": _string_value(record, "title"),
        "artist": _artist_value(record.get("creators")),
        "date": _string_value(record, "creation_date"),
        "thumbnail_url": image_url,
        "credit_line": _string_value(record, "creditline"),
        "object_name": _string_value(record, "type"),
        "medium": _string_value(record, "technique"),
        "dimensions": _string_value(record, "measurements"),
        "height": _dimension_value(record.get("dimensions"), "height"),
        "width": _dimension_value(record.get("dimensions"), "width"),
        "department": _string_value(record, "department"),
        "classification": _string_value(record, "classification_type"),
        "culture": _culture_value(record.get("culture")),
        "accession_number": accession_number,
        "is_public_domain": record.get("share_license_status") == "CC0",
        "source_institution": CLEVELAND_SOURCE_INSTITUTION,
    }


def discover_cleveland_images(
    max_images: int | None = 20,
    *,
    query: str | None = None,
    all_records: bool = False,
    batch_size: int = MAX_API_PAGE_SIZE,
    retries: int = 3,
) -> list[ScrapedImage]:
    if max_images is not None and max_images < 1:
        raise ValueError("max_images must be at least 1")
    if not all_records and max_images is None:
        raise ValueError("max_images is required unless all_records is true")
    if batch_size < 1 or batch_size > MAX_API_PAGE_SIZE:
        raise ValueError(
            f"batch_size must be between 1 and {MAX_API_PAGE_SIZE}"
        )
    if retries < 0:
        raise ValueError("retries cannot be negative")

    images: list[ScrapedImage] = []
    seen_urls: set[str] = set()
    skip = 0

    while True:
        params: dict[str, Any] = {
            "has_image": 1,
            "limit": batch_size if all_records else min(batch_size, max_images),
            "skip": skip,
            "fields": _FIELDS,
        }
        if query and query.strip():
            params["q"] = query.strip()

        payload = _get_json(params, retries)
        records = payload.get("data")
        if not isinstance(records, list):
            raise ValueError("Cleveland API response has invalid data")

        for record in records:
            if not isinstance(record, Mapping):
                continue
            try:
                metadata = extract_cleveland_metadata(record)
            except ValueError:
                continue
            if metadata["image_url"] in seen_urls:
                continue
            seen_urls.add(metadata["image_url"])
            images.append(ScrapedImage(source_type="master_artwork", **metadata))
            if max_images is not None and len(images) >= max_images:
                return images

        info = payload.get("info")
        total = info.get("total") if isinstance(info, Mapping) else None
        skip += len(records)
        if (
            not all_records
            or len(records) < params["limit"]
            or (isinstance(total, int) and skip >= total)
        ):
            break

    return images


def _get_json(params: Mapping[str, Any], retries: int) -> dict[str, Any]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    for attempt in range(retries + 1):
        try:
            response = requests.get(
                CLEVELAND_API_URL,
                headers=headers,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Cleveland API response must be an object")
            return payload
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")


def _string_value(record: Any, field: str) -> str | None:
    if not isinstance(record, Mapping):
        return None
    value = record.get(field)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _artist_value(creators: Any) -> str | None:
    if not isinstance(creators, list):
        return None
    artists = [
        creator.get("description")
        for creator in creators
        if isinstance(creator, Mapping)
        and creator.get("role") == "artist"
        and isinstance(creator.get("description"), str)
        and creator["description"].strip()
    ]
    return "; ".join(artists) if artists else None


def _culture_value(culture: Any) -> str | None:
    if not isinstance(culture, list):
        return None
    values = [value.strip() for value in culture if isinstance(value, str) and value.strip()]
    return "; ".join(values) if values else None


def _dimension_value(dimensions: Any, name: str) -> str | None:
    if not isinstance(dimensions, Mapping):
        return None
    for value in dimensions.values():
        if not isinstance(value, Mapping):
            continue
        dimension = value.get(name)
        if isinstance(dimension, (int, float)):
            return str(dimension)
    return None
