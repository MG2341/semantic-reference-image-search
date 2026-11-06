from __future__ import annotations

from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def discover_image_urls(page_url: str) -> list[str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(page_url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    image_urls: list[str] = []
    seen: set[str] = set()

    for image in soup.find_all("img"):
        candidates = [image.get("src"), image.get("data-src")]
        srcset = image.get("srcset")
        if srcset:
            candidates.extend(item.strip().split(" ", 1)[0] for item in srcset.split(","))

        for candidate in candidates:
            if not candidate:
                continue
            image_url = urljoin(page_url, candidate)
            if image_url not in seen:
                seen.add(image_url)
                image_urls.append(image_url)

    return image_urls
