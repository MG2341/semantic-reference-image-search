from app.scraping import generic, wetcanvas


def test_wetcanvas_image_discovery_follows_category_and_photo_pages(monkeypatch):
    pages = {
        "https://www.wetcanvas.com/reflib-archive/?cat=15": """
            <a href="?cat=20">Horses</a>
        """,
        "https://www.wetcanvas.com/reflib-archive/?cat=15&pg=1": """
            <a href="?cat=20">Horses</a>
        """,
        "https://www.wetcanvas.com/reflib-archive/?cat=20&pg=1": """
            <a href="?photo=123">Horse</a>
        """,
        "https://www.wetcanvas.com/reflib-archive/?photo=123": """
            <img src="https://s3.amazonaws.com/wetcanvas-hdc/RefLib/data2/20/medium/horse.jpg"
                 alt="Horse">
        """,
        "https://www.wetcanvas.com/reflib-archive/?cat=20&pg=2": "",
    }

    class Response:
        status_code = 200

        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            pass

    def fake_get(url, **kwargs):
        if url.endswith("/robots.txt"):
            return Response("")
        return Response(pages[url])

    monkeypatch.setattr(generic.requests, "get", fake_get)

    assert wetcanvas.discover_images(
        "https://www.wetcanvas.com/reflib-archive/?cat=15",
        max_pages=2,
        max_images=1,
    ) == [
        wetcanvas.ScrapedImage(
            image_url=(
                "https://s3.amazonaws.com/wetcanvas-hdc/RefLib/data2/20/medium/"
                "horse.jpg"
            ),
            source_page_url="https://www.wetcanvas.com/reflib-archive/?photo=123",
            title="Horse",
            source_type="photo",
        )
    ]
