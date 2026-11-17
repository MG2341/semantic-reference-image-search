from __future__ import annotations

import argparse
import re
import time
from collections.abc import Mapping
from typing import Any

import requests

from app.bootstrap import initialize_database
from app.db.sqlite import get_connection, update_image_metadata
from app.scraping.met import extract_met_metadata, get_met_object


OBJECT_ID_PATTERNS = (
    re.compile(r"/objects/(\d+)$"),
    re.compile(r"/search/(\d+)$"),
)


def _object_id_from_url(url: str) -> int | None:
    for pattern in OBJECT_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return int(match.group(1))
    return None


def _met_rows(max_images: int | None) -> list[Mapping[str, Any]]:
    query = """
        SELECT id, source_page_url
        FROM images
        WHERE source_page_url LIKE '%collectionapi.metmuseum.org%'
           OR source_page_url LIKE 'https://www.metmuseum.org/art/collection/search/%'
        ORDER BY id
    """
    if max_images is not None:
        query += " LIMIT ?"

    with get_connection() as connection:
        if max_images is None:
            rows = connection.execute(query).fetchall()
        else:
            rows = connection.execute(query, (max_images,)).fetchall()
    return rows


def backfill_metadata(
    max_images: int | None,
    delay_seconds: float,
    retries: int,
) -> tuple[int, int]:
    updated = 0
    skipped = 0
    rows = _met_rows(max_images)

    for index, row in enumerate(rows, start=1):
        object_id = _object_id_from_url(row["source_page_url"])
        if object_id is None:
            skipped += 1
            print(f"Skipping image {row['id']}: cannot determine Met object ID")
            continue

        print(f"Fetching Met object {object_id} ({index}/{len(rows)})", flush=True)
        try:
            record = get_met_object(object_id, retries=retries)
            metadata = extract_met_metadata(record, object_id)
            update_image_metadata(
                row["id"],
                **{key: value for key, value in metadata.items() if key != "image_url"},
            )
            updated += 1
        except (requests.RequestException, ValueError) as error:
            skipped += 1
            print(f"Skipping object {object_id}: {error}", flush=True)

        if index < len(rows):
            time.sleep(delay_seconds)

    return updated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill Met thumbnails and metadata for existing records."
    )
    parser.add_argument("--max-images", type=int)
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()

    if args.max_images is not None and args.max_images < 1:
        parser.error("--max-images must be at least 1")
    if args.delay < 0:
        parser.error("--delay cannot be negative")
    if args.retries < 0:
        parser.error("--retries cannot be negative")

    initialize_database()
    updated, skipped = backfill_metadata(args.max_images, args.delay, args.retries)
    print(f"Updated {updated} records; skipped {skipped}.")


if __name__ == "__main__":
    main()
