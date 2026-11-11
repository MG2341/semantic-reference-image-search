from __future__ import annotations

import argparse
import time

from app.bootstrap import initialize_database, load_clip_model
from app.scraping.models import ScrapedImage, SourceType
from app.scraping.api import discover_images
from app.services.embedding_service import download_image, get_image_embedding
from app.services.storage_service import save_image_embedding


def scrape_api(
    api_url: str,
    max_images: int,
    delay_seconds: float,
    source_type: SourceType,
    image_field: str,
    title_field: str | None,
    records_path: str | None,
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
        )[:max_images]
    ]
    return process_images(images, delay_seconds)


def process_images(images: list[ScrapedImage], delay_seconds: float) -> int:
    model, processor = load_clip_model()

    saved_count = 0
    for index, image in enumerate(images):
        print(f"Processing {image.image_url}", flush=True)
        try:
            downloaded_image = download_image(image.image_url)
            embedding = get_image_embedding(model, processor, downloaded_image)
            saved = save_image_embedding(
                url=image.image_url,
                label=image.title or f"Scraped from {image.source_page_url}",
                embedding=embedding[0].tolist(),
                source_type=image.source_type,
            )
        except (OSError, ValueError):
            print(f"Skipping unsupported image: {image.image_url}", flush=True)
            continue
        if saved:
            saved_count += 1
        if index < len(images) - 1:
            time.sleep(delay_seconds)

    return saved_count


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
