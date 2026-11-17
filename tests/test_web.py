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

    with TestClient(web.app) as client:
        page_response = client.get("/")
        response = client.get("/search?q=painting&k=1")
        second_response = client.get("/search?q=painting&k=1")

    assert page_response.status_code == 200
    assert "Semantic Reference Image Search" in page_response.text
    assert response.status_code == 200
    assert response.json()[0] == {
        "id": 7,
        "title": "A painting",
        "artist": "An artist",
        "date": "1900",
        "thumbnail_url": "https://example.com/thumb.jpg",
        "met_page_url": "https://example.com/met/7",
        "credit_line": "Gift",
        "score": 1.0,
    }
    assert second_response.status_code == 200
    assert calls == {"model": 1, "documents": 1}
