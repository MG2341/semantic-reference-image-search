from __future__ import annotations

import time
from collections.abc import Sequence

import requests

from app.db.sqlite import existing_image_urls
from app.scraping.models import ScrapedImage
from app.services.embedding_service import download_image, get_image_embedding
from app.services.storage_service import save_image_embedding


def process_images(
    images: Sequence[ScrapedImage],
    delay_seconds: float,
) -> int:
    known_urls = existing_image_urls([image.image_url for image in images])
    pending: list[ScrapedImage] = []
    queued_urls: set[str] = set()
    for image in images:
        if image.image_url not in known_urls and image.image_url not in queued_urls:
            pending.append(image)
            queued_urls.add(image.image_url)
    if not pending:
        return 0

    from app.bootstrap import load_clip_model

    model, processor = load_clip_model()
    saved_count = 0
    for index, image in enumerate(pending):
        print(f"Processing {image.image_url}", flush=True)
        try:
            downloaded_image = download_image(image.image_url)
            embedding = get_image_embedding(model, processor, downloaded_image)
            saved = save_image_embedding(
                url=image.image_url,
                label=image.title or f"Scraped from {image.source_page_url}",
                embedding=embedding[0].tolist(),
                source_type=image.source_type,
                source_page_url=image.source_page_url,
            )
            if saved:
                saved_count += 1
        except (OSError, ValueError, requests.RequestException) as error:
            print(f"Skipping {image.image_url}: {error}", flush=True)
        finally:
            if index < len(pending) - 1:
                time.sleep(delay_seconds)
    return saved_count
