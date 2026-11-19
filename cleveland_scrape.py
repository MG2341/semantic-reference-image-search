from __future__ import annotations

import argparse
from datetime import datetime

from app.bootstrap import initialize_database
from app.db.sqlite import get_scrape_progress, set_scrape_progress
from app.scraping.cleveland import discover_cleveland_images
from app.services.ingestion_service import process_images


CLEVELAND_PROGRESS_SOURCE = "cleveland-all"


def _print_progress(processed: int, total: int, saved: int) -> None:
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    print(
        f"[{timestamp}] Covered {processed}/{total} images; "
        f"saved {saved} embeddings.",
        flush=True,
    )


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
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continue --all scraping from persisted Cleveland progress",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        help="Start --all scraping at this API listing offset",
    )
    args = parser.parse_args()

    if args.max_images < 1:
        parser.error("--max-images must be at least 1")
    if args.batch_size < 1 or args.batch_size > 1000:
        parser.error("--batch-size must be between 1 and 1000")
    if args.delay < 0:
        parser.error("--delay cannot be negative")
    if args.resume and args.start_index is not None:
        parser.error("--resume and --start-index cannot be used together")
    if (args.resume or args.start_index is not None) and not args.all:
        parser.error("--resume and --start-index require --all")
    if args.start_index is not None and args.start_index < 0:
        parser.error("--start-index cannot be negative")

    initialize_database()
    start_index = 0
    if args.resume:
        start_index = get_scrape_progress(CLEVELAND_PROGRESS_SOURCE)
    elif args.start_index is not None:
        start_index = args.start_index

    images = discover_cleveland_images(
        max_images=None if args.all else args.max_images,
        query=args.query,
        all_records=args.all,
        batch_size=args.batch_size,
        start_index=start_index,
    )
    print(
        f"Discovered {len(images)} Cleveland image records"
        f"{f' starting at API index {start_index}' if args.all else ''}.",
        flush=True,
    )

    if args.dry_run:
        for index, image in enumerate(images, start=1):
            print(
                f"{index}. {image.title or 'Untitled'} | "
                f"{image.image_url} | {image.source_page_url}"
            )
        print("Dry run complete; no embeddings were downloaded or stored.")
        return

    print("Starting image download and embedding process.", flush=True)
    def progress_callback(processed: int, total: int, saved: int) -> None:
        _print_progress(processed, total, saved)
        if args.all:
            set_scrape_progress(
                CLEVELAND_PROGRESS_SOURCE,
                start_index + processed,
            )

    saved_count = process_images(
        images,
        args.delay,
        progress_callback=progress_callback,
    )
    if args.all:
        set_scrape_progress(
            CLEVELAND_PROGRESS_SOURCE,
            start_index + len(images),
        )
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    print(
        f"[{timestamp}] Completed. Saved {saved_count} image embeddings.",
        flush=True,
    )


if __name__ == "__main__":
    main()
