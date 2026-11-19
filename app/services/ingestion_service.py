from __future__ import annotations

import time
from collections.abc import Callable, Sequence

import requests

from app.db.sqlite import existing_image_urls
from app.scraping.models import ScrapedImage
from app.services.embedding_service import download_image, get_image_embedding
from app.services.storage_service import save_image_embedding


ProgressCallback = Callable[[int, int, int], None]
PROGRESS_INTERVAL_SECONDS = 60.0


def process_images(
    images: Sequence[ScrapedImage],
    delay_seconds: float,
    progress_callback: ProgressCallback | None = None,
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
    last_progress_at = time.monotonic()
    for index, image in enumerate(pending):
        print(
            f"Processing image {index + 1}/{len(pending)}: {image.image_url}",
            flush=True,
        )
        try:
            downloaded_image = download_image(image.image_url)
            embedding = get_image_embedding(model, processor, downloaded_image)
            saved = save_image_embedding(
                url=image.image_url,
                label=image.title or f"Scraped from {image.source_page_url}",
                embedding=embedding[0].tolist(),
                source_type=image.source_type,
                source_page_url=image.source_page_url,
                source_institution=image.source_institution,
                artist=image.artist,
                date=image.date,
                thumbnail_url=image.thumbnail_url,
                credit_line=image.credit_line,
                object_name=image.object_name,
                medium=image.medium,
                dimensions=image.dimensions,
                height=image.height,
                width=image.width,
                department=image.department,
                classification=image.classification,
                culture=image.culture,
                period=image.period,
                dynasty=image.dynasty,
                reign=image.reign,
                country=image.country,
                accession_number=image.accession_number,
                is_public_domain=image.is_public_domain,
            )
            if saved:
                saved_count += 1
        except (OSError, ValueError, requests.RequestException) as error:
            print(f"Skipping {image.image_url}: {error}", flush=True)
        finally:
            processed_count = index + 1
            now = time.monotonic()
            if progress_callback and (
                now - last_progress_at >= PROGRESS_INTERVAL_SECONDS
                or processed_count == len(pending)
            ):
                progress_callback(processed_count, len(pending), saved_count)
                last_progress_at = now
            if index < len(pending) - 1:
                time.sleep(delay_seconds)
    return saved_count
