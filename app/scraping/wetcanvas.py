from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from app.scraping.generic import fetch_soup
from app.scraping.models import ScrapedImage


def _wetcanvas_url(page_url: str, **parameters: str) -> str:
    parsed = urlparse(page_url)
    query = parse_qs(parsed.query)
    query.update(parameters)
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def discover_category_urls(index_url: str) -> list[str]:
    soup = fetch_soup(index_url)
    category_urls: list[str] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        category_url = urljoin(index_url, link["href"])
        parsed = urlparse(category_url)
        if parsed.netloc not in {"www.wetcanvas.com", "wetcanvas.com"}:
            continue
        if "cat" not in parse_qs(parsed.query):
            continue
        category_url = _wetcanvas_url(category_url, pg="1")
        if category_url not in seen:
            seen.add(category_url)
            category_urls.append(category_url)
    return category_urls


def discover_photo_pages(category_url: str) -> list[str]:
    soup = fetch_soup(category_url)
    photo_pages: list[str] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        photo_url = urljoin(category_url, link["href"])
        if "photo" not in parse_qs(urlparse(photo_url).query):
            continue
        if photo_url not in seen:
            seen.add(photo_url)
            photo_pages.append(photo_url)
    return photo_pages


def get_image_from_photo_page(photo_url: str) -> ScrapedImage:
    soup = fetch_soup(photo_url)
    for image in soup.find_all("img", src=True):
        image_url = urljoin(photo_url, image["src"])
        if "/medium/" in image_url:
            return ScrapedImage(
                image_url=image_url,
                source_page_url=photo_url,
                title=image.get("alt"),
                source_type="photo",
            )
    raise ValueError(f"No medium image found on {photo_url}")


def discover_images(
    index_url: str, max_pages: int, max_images: int
) -> list[ScrapedImage]:
    if max_pages < 1 or max_images < 1:
        raise ValueError("max_pages and max_images must be at least 1")

    category_urls = discover_category_urls(index_url)
    if not category_urls:
        category_urls = [_wetcanvas_url(index_url, pg="1")]

    images: list[ScrapedImage] = []
    seen_images: set[str] = set()
    visited_pages = 0
    for category_url in category_urls:
        page_number = 1
        while visited_pages < max_pages and len(images) < max_images:
            page_url = _wetcanvas_url(category_url, pg=str(page_number))
            photo_pages = discover_photo_pages(page_url)
            visited_pages += 1
            if not photo_pages:
                break

            for photo_page in photo_pages:
                image = get_image_from_photo_page(photo_page)
                if image.image_url not in seen_images:
                    seen_images.add(image.image_url)
                    images.append(image)
                    if len(images) >= max_images:
                        break
            page_number += 1

    return images
