from __future__ import annotations

from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


USER_AGENT = "reference-image-searcher/0.1"


def ensure_allowed_by_robots(page_url: str) -> None:
    parsed_url = urlparse(page_url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    response = requests.get(
        robots_url,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    if getattr(response, "status_code", 200) == 404:
        return
    response.raise_for_status()

    robots = RobotFileParser()
    robots.set_url(robots_url)
    robots.parse(response.text.splitlines())
    if not robots.can_fetch(USER_AGENT, page_url):
        raise RuntimeError(f"robots.txt disallows scraping {page_url}")


def discover_image_urls(page_url: str) -> list[str]:
    ensure_allowed_by_robots(page_url)
    headers = {
        "User-Agent": USER_AGENT
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
