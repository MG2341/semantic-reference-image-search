from __future__ import annotations

import argparse
import time

from app.bootstrap import initialize_database, load_clip_model
from app.scraping.models import ScrapedImage
from app.scraping import generic, wetcanvas
from app.services.embedding_service import download_image, get_image_embedding
from app.services.storage_service import save_image_embedding


def scrape_page(page_url: str, max_images: int, delay_seconds: float) -> int:
    initialize_database()

    images = [
        ScrapedImage(image_url=url, source_page_url=page_url)
        for url in generic.discover_image_urls(page_url)[:max_images]
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
            )
        except (OSError, ValueError):
            print(f"Skipping unsupported image: {image.image_url}", flush=True)
            continue
        if saved:
            saved_count += 1
        if index < len(images) - 1:
            time.sleep(delay_seconds)

    return saved_count


def scrape_wetcanvas(
    index_url: str, max_pages: int, max_images: int, delay_seconds: float
) -> int:
    initialize_database()
    return process_images(
        wetcanvas.discover_images(index_url, max_pages, max_images),
        delay_seconds,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape image embeddings from a web page")
    parser.add_argument("url", help="Web page URL to scrape")
    parser.add_argument(
        "--wetcanvas",
        action="store_true",
        help="Use the WetCanvas category and photo-page scraper",
    )
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument(
        "--max-images",
        type=int,
        default=20,
        help="Maximum number of images to process (default: 20)",
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

    print(f"Discovering images on {args.url}...", flush=True)
    if args.wetcanvas:
        saved_count = scrape_wetcanvas(
            args.url, args.max_pages, args.max_images, args.delay
        )
    else:
        saved_count = scrape_page(args.url, args.max_images, args.delay)
    print(f"Saved {saved_count} image embeddings.", flush=True)


if __name__ == "__main__":
    main()
