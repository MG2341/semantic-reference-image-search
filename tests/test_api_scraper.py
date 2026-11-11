from app.scraping import api


def test_discover_images_maps_nested_api_records(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "data": {
                    "results": [
                        {
                            "image": {"url": "https://example.com/one.jpg"},
                            "title": "One",
                        },
                        {
                            "image": {"url": "https://example.com/one.jpg"},
                            "title": "Duplicate",
                        },
                        {"image": {"url": "not-a-url"}},
                    ]
                }
            }

    monkeypatch.setattr(api.requests, "get", lambda *args, **kwargs: Response())

    assert api.discover_images(
        "https://api.example.com/images",
        image_field="image.url",
        title_field="title",
        records_path="data.results",
        source_type="photo",
    ) == [
        api.ScrapedImage(
            image_url="https://example.com/one.jpg",
            source_page_url="https://api.example.com/images",
            title="One",
            source_type="photo",
        )
    ]
