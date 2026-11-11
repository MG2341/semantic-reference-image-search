from app.domain.models import ImageRecord
from app import bootstrap
from app.services import ingestion_service


def test_process_images_skips_known_and_duplicate_urls(monkeypatch):
    images = [
        ImageRecord("https://example.com/known.jpg", "https://api.example.com"),
        ImageRecord("https://example.com/new.jpg", "https://api.example.com"),
        ImageRecord("https://example.com/new.jpg", "https://api.example.com"),
    ]
    downloaded_urls = []

    monkeypatch.setattr(
        ingestion_service,
        "existing_image_urls",
        lambda urls: {"https://example.com/known.jpg"},
    )
    monkeypatch.setattr(
        bootstrap, "load_clip_model", lambda: ("model", "processor")
    )
    monkeypatch.setattr(
        ingestion_service,
        "download_image",
        lambda url: downloaded_urls.append(url) or "image",
    )
    monkeypatch.setattr(
        ingestion_service,
        "get_image_embedding",
        lambda model, processor, image: _Embedding(),
    )
    monkeypatch.setattr(
        ingestion_service,
        "save_image_embedding",
        lambda **kwargs: True,
    )

    assert ingestion_service.process_images(images, delay_seconds=0) == 1
    assert downloaded_urls == ["https://example.com/new.jpg"]


class _Embedding:
    def __getitem__(self, index):
        assert index == 0
        return self

    def tolist(self):
        return [1.0]
