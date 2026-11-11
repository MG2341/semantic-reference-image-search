from __future__ import annotations

import argparse
from app.bootstrap import initialize_database
from app.scraping.models import ScrapedImage, SourceType
from app.scraping.api import discover_images
from app.services.ingestion_service import process_images as ingest_images


def scrape_api(
    api_url: str,
    max_images: int,
    delay_seconds: float,
    source_type: SourceType,
    image_field: str,
    title_field: str | None,
    records_path: str | None,
    max_pages: int = 1,
    next_url_field: str | None = None,
) -> int:
    initialize_database()

    images = [
        image
        for image in discover_images(
            api_url,
            image_field,
            title_field,
            records_path,
            source_type,
            max_pages=max_pages,
            next_url_field=next_url_field,
        )[:max_images]
    ]
    return process_images(images, delay_seconds)


def process_images(images: list[ScrapedImage], delay_seconds: float) -> int:
    return ingest_images(images, delay_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch image records from a JSON API and create embeddings."
    )
    parser.add_argument("url", help="JSON API endpoint")
    parser.add_argument(
        "--source-type",
        choices=["photo", "movie_screencap", "master_artwork", "other", "unknown"],
        default="photo",
        help="Provenance label for images (default: photo)",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=20,
        help="Maximum number of images to process (default: 20)",
    )
    parser.add_argument(
        "--records-path",
        help="Dot-separated path to the list of records, e.g. data.results",
    )
    parser.add_argument(
        "--image-field",
        default="image_url",
        help="Dot-separated image URL field in each record (default: image_url)",
    )
    parser.add_argument("--title-field", help="Optional title field in each record")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1,
        help="Maximum API pages to fetch (default: 1)",
    )
    parser.add_argument(
        "--next-url-field",
        help="Dot-separated response field containing the next page URL",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between image requests (default: 1)",
    )
    args = parser.parse_args()

    if args.max_images < 1:
        parser.error("--max-images must be at least 1")
    if args.delay < 0:
        parser.error("--delay cannot be negative")
    if args.max_pages < 1:
        parser.error("--max-pages must be at least 1")
    print(f"Fetching image records from {args.url}...", flush=True)
    saved_count = scrape_api(
        args.url,
        args.max_images,
        args.delay,
        args.source_type,
        args.image_field,
        args.title_field,
        args.records_path,
    )
    print(f"Saved {saved_count} image embeddings.", flush=True)


if __name__ == "__main__":
    main()
