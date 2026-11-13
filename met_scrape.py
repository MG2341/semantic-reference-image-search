from __future__ import annotations

import argparse

from app.bootstrap import initialize_database
from app.db.sqlite import (
    get_or_create_scrape_seed,
    get_scrape_progress,
    set_scrape_progress,
)
from app.scraping.met import discover_all_met_images, discover_met_images
from app.services.ingestion_service import process_images


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch artwork images from the Metropolitan Museum API."
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Text searched in the Met collection (omit when using --all)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Walk the Met's complete object-ID listing instead of text search",
    )
    parser.add_argument("--max-images", type=int, default=20)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of Met object IDs to inspect per --all run (default: 1000)",
    )
    parser.add_argument(
        "--source-type",
        choices=["master_artwork", "photo", "movie_screencap", "other", "unknown"],
        default="master_artwork",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Seconds between Met object requests (default: 0.1)",
    )
    args = parser.parse_args()

    if args.max_images < 1:
        parser.error("--max-images must be at least 1")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    if args.delay < 0:
        parser.error("--delay cannot be negative")
    if args.all == (args.query is not None):
        parser.error("provide either a query or --all, but not both")

    initialize_database()
    if args.all:
        progress_source = "met-paintings-random"
        start_index = get_scrape_progress(progress_source)
        random_seed = get_or_create_scrape_seed(progress_source)
        print("Walking the Met collection in random order", flush=True)
        print(
            f"Starting at object index {start_index}; "
            f"batch size {args.batch_size}",
            flush=True,
        )
        images = discover_all_met_images(
            max_images=args.batch_size,
            start_index=start_index,
            object_batch_size=args.batch_size,
            random_seed=random_seed,
            source_type=args.source_type,
            delay_seconds=args.delay,
        )
    else:
        print(f"Searching the Met collection for: {args.query}", flush=True)
        images = discover_met_images(
            query=args.query,
            max_images=args.max_images,
            source_type=args.source_type,
            delay_seconds=args.delay,
        )
    saved_count = process_images(images, args.delay)
    if args.all:
        set_scrape_progress(progress_source, start_index + args.batch_size)
    print(f"Saved {saved_count} image embeddings.", flush=True)


if __name__ == "__main__":
    main()
