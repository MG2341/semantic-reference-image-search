from __future__ import annotations

import argparse
import time

import torch
from transformers import CLIPModel, CLIPProcessor

from app.config import MODEL_NAME
from app.db.sqlite import init_db
from app.services.embedding_service import download_image, get_image_embedding
from app.services.scraper_service import discover_image_urls
from app.services.storage_service import save_image_embedding


def scrape_page(page_url: str, max_images: int, delay_seconds: float) -> int:
    init_db()

    image_urls = discover_image_urls(page_url)[:max_images]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading CLIP model on {device}; the first run downloads it...", flush=True)
    model = CLIPModel.from_pretrained(MODEL_NAME).to(device)
    processor = CLIPProcessor.from_pretrained(MODEL_NAME)

    saved_count = 0
    for index, image_url in enumerate(image_urls):
        print(f"Processing {image_url}", flush=True)
        try:
            image = download_image(image_url)
            embedding = get_image_embedding(model, processor, image)
            save_image_embedding(
                url=image_url,
                label=f"Scraped from {page_url}",
                embedding=embedding[0].tolist(),
            )
        except (OSError, ValueError):
            print(f"Skipping unsupported image: {image_url}", flush=True)
            continue
        saved_count += 1
        if index < len(image_urls) - 1:
            time.sleep(delay_seconds)

    return saved_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape image embeddings from a web page")
    parser.add_argument("url", help="Web page URL to scrape")
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

    print(f"Discovering images on {args.url}...", flush=True)
    saved_count = scrape_page(args.url, args.max_images, args.delay)
    print(f"Saved {saved_count} image embeddings.", flush=True)


if __name__ == "__main__":
    main()
