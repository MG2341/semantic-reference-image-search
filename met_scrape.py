from __future__ import annotations

import argparse

from app.bootstrap import initialize_database
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
        "--skip-images",
        type=int,
        default=0,
        help="Skip this many images in ordered --all mode (default: 0)",
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
    if args.skip_images < 0:
        parser.error("--skip-images cannot be negative")
    if args.delay < 0:
        parser.error("--delay cannot be negative")
    if args.all == (args.query is not None):
        parser.error("provide either a query or --all, but not both")

    initialize_database()
    if args.all:
        print("Walking the Met collection in object-ID order", flush=True)
        images = discover_all_met_images(
            max_images=args.max_images,
            skip_images=args.skip_images,
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
    print(f"Saved {saved_count} image embeddings.", flush=True)


if __name__ == "__main__":
    main()
