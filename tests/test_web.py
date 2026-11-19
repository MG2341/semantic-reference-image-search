from io import BytesIO

from PIL import Image
from fastapi.testclient import TestClient

import web
from app.web_search import SearchDocument


class _Embedding:
    def __getitem__(self, index):
        assert index == 0
        return self

    def tolist(self):
        return [1.0, 0.0]


def test_search_endpoint_loads_resources_at_startup(monkeypatch):
    calls = {"model": 0, "documents": 0}
    document = SearchDocument(
        id=7,
        title="A painting",
        artist="An artist",
        date="1900",
        thumbnail_url="https://example.com/thumb.jpg",
        met_page_url="https://example.com/met/7",
        credit_line="Gift",
        vector=(1.0, 0.0),
    )

    monkeypatch.setattr(web, "initialize_database", lambda: None)

    def load_model():
        calls["model"] += 1
        return "model", "processor"

    def load_documents():
        calls["documents"] += 1
        return [document]

    monkeypatch.setattr(web, "load_clip_model", load_model)
    monkeypatch.setattr(web, "load_search_documents", load_documents)
    monkeypatch.setattr(web, "get_text_embedding", lambda *args: _Embedding())
    monkeypatch.setattr(web, "get_image_embedding", lambda *args: _Embedding())

    image_bytes = BytesIO()
    Image.new("RGB", (1, 1), color="white").save(image_bytes, format="PNG")

    with TestClient(web.app) as client:
        page_response = client.get("/")
        response = client.get("/search?q=painting&k=1")
        second_response = client.get("/search?q=painting&k=1")
        image_response = client.post(
            "/search/image?k=1",
            files={"file": ("reference.png", image_bytes.getvalue(), "image/png")},
        )

    assert page_response.status_code == 200
    assert "Semantic Reference Image Search" in page_response.text
    assert "Search by image" in page_response.text
    assert response.status_code == 200
    assert response.json()[0] == {
        "id": 7,
        "title": "A painting",
        "artist": "An artist",
        "date": "1900",
        "thumbnail_url": "https://example.com/thumb.jpg",
        "met_page_url": "https://example.com/met/7",
        "credit_line": "Gift",
        "museum": None,
        "object_name": None,
        "medium": None,
        "dimensions": None,
        "height": None,
        "width": None,
        "department": None,
        "classification": None,
        "culture": None,
        "period": None,
        "dynasty": None,
        "reign": None,
        "country": None,
        "accession_number": None,
        "is_public_domain": None,
        "score": 1.0,
    }
    assert second_response.status_code == 200
    assert image_response.status_code == 200
    assert image_response.json()[0]["id"] == 7
    assert calls == {"model": 1, "documents": 1}


def test_image_search_rejects_non_image_upload(monkeypatch):
    monkeypatch.setattr(web, "initialize_database", lambda: None)
    monkeypatch.setattr(web, "load_clip_model", lambda: ("model", "processor"))
    monkeypatch.setattr(web, "load_search_documents", lambda: [])
    monkeypatch.setattr(web, "get_text_embedding", lambda *args: _Embedding())
    monkeypatch.setattr(web, "get_image_embedding", lambda *args: _Embedding())

    with TestClient(web.app) as client:
        response = client.post(
            "/search/image",
            files={"file": ("reference.txt", b"not an image", "text/plain")},
        )

    assert response.status_code == 415
