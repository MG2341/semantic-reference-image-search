from __future__ import annotations

import argparse

from app.bootstrap import initialize_database, load_clip_model
from app.db.sqlite import search_embeddings
from app.domain.models import SearchResult
from app.services.embedding_service import get_text_embedding


def search_images(
    query: str, top_k: int, source_types: list[str] | None = None
) -> list[SearchResult]:
    initialize_database()
    model, processor = load_clip_model()

    query_embedding = get_text_embedding(model, processor, query)
    return search_embeddings(query_embedding[0].tolist(), top_k, source_types)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find the best matching scraped image links."
    )
    parser.add_argument("query", help="Description of the images to find")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--source-type",
        dest="source_types",
        action="append",
        choices=["photo", "movie_screencap", "master_artwork", "other", "unknown"],
        help="Limit results; repeat for an OR combination",
    )
    args = parser.parse_args()

    if not args.query.strip():
        parser.error("query cannot be empty")
    if args.top_k < 1:
        parser.error("--top-k must be at least 1")

    results = search_images(args.query, args.top_k, args.source_types)
    if not results:
        print("No images are stored yet. Run scrape.py first.")
        return

    print(f"Best matches for: {args.query}")
    for result in results:
        print(
            f"- {result.image_url} [{result.source_type}] "
            f"(score: {result.score:.4f})"
        )


if __name__ == "__main__":
    main()
