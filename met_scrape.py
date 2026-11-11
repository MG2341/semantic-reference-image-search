from __future__ import annotations

import argparse

from app.bootstrap import initialize_database
from app.scraping.met import discover_met_images
from app.services.ingestion_service import process_images


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch artwork images from the Metropolitan Museum API."
    )
    parser.add_argument("query", help="Text searched in the Met collection")
    parser.add_argument("--max-images", type=int, default=20)
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
    if args.delay < 0:
        parser.error("--delay cannot be negative")

    initialize_database()
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
