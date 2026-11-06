from app.scraping import generic


def test_discover_image_urls(monkeypatch):
    class Response:
        text = """
        <img src="/first.jpg">
        <img data-src="second.jpg">
        <img srcset="third-small.jpg 400w, /third-large.jpg 800w">
        <img src="/first.jpg">
        """

        def raise_for_status(self):
            pass

    monkeypatch.setattr(generic.requests, "get", lambda *args, **kwargs: Response())

    assert generic.discover_image_urls("https://example.com/gallery/") == [
        "https://example.com/first.jpg",
        "https://example.com/gallery/second.jpg",
        "https://example.com/gallery/third-small.jpg",
        "https://example.com/third-large.jpg",
    ]
