from __future__ import annotations

import argparse

import torch
from transformers import CLIPModel, CLIPProcessor

from app.config import MODEL_NAME
from app.db.sqlite import init_db, search_embeddings
from app.services.embedding_service import get_text_embedding


def search_images(query: str, top_k: int) -> list[tuple[str, str | None, float]]:
    init_db()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading CLIP model on {device}; the first run downloads it...", flush=True)
    model = CLIPModel.from_pretrained(MODEL_NAME).to(device)
    model.eval()
    processor = CLIPProcessor.from_pretrained(MODEL_NAME)

    query_embedding = get_text_embedding(model, processor, query)
    return search_embeddings(query_embedding[0].tolist(), top_k)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find the best matching scraped image links."
    )
    parser.add_argument("query", help="Description of the images to find")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if not args.query.strip():
        parser.error("query cannot be empty")
    if args.top_k < 1:
        parser.error("--top-k must be at least 1")

    results = search_images(args.query, args.top_k)
    if not results:
        print("No images are stored yet. Run scrape.py first.")
        return

    print(f"Best matches for: {args.query}")
    for url, label, score in results:
        print(f"- {url} (score: {score:.4f})")


if __name__ == "__main__":
    main()
