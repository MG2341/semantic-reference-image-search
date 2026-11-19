from __future__ import annotations

import argparse

from app.bootstrap import initialize_database
from app.scraping.cleveland import discover_cleveland_images
from app.services.ingestion_service import process_images


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch artwork images from the Cleveland Museum of Art API."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Walk the complete CMA image-bearing artwork listing",
    )
    parser.add_argument(
        "--query",
        help="Optional CMA search term, such as 'landscape' or 'Picasso'",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=20,
        help="Maximum images for a small run (default: 20)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="API page size for --all (1-1000, default: 1000)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds between image downloads (default: 1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover and print records without downloading or storing images",
    )
    args = parser.parse_args()

    if args.max_images < 1:
        parser.error("--max-images must be at least 1")
    if args.batch_size < 1 or args.batch_size > 1000:
        parser.error("--batch-size must be between 1 and 1000")
    if args.delay < 0:
        parser.error("--delay cannot be negative")

    images = discover_cleveland_images(
        max_images=None if args.all else args.max_images,
        query=args.query,
        all_records=args.all,
        batch_size=args.batch_size,
    )
    print(f"Discovered {len(images)} Cleveland image records.", flush=True)

    if args.dry_run:
        for index, image in enumerate(images, start=1):
            print(
                f"{index}. {image.title or 'Untitled'} | "
                f"{image.image_url} | {image.source_page_url}"
            )
        print("Dry run complete; no embeddings were downloaded or stored.")
        return

    initialize_database()
    saved_count = process_images(images, args.delay)
    print(f"Saved {saved_count} image embeddings.", flush=True)


if __name__ == "__main__":
    main()
