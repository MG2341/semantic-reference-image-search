from app.scraping import api


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_discover_images_maps_nested_api_records(monkeypatch):
    monkeypatch.setattr(
        api.requests,
        "get",
        lambda *args, **kwargs: _Response(
            {
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
        ),
    )

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


def test_discover_images_follows_next_urls_and_deduplicates(monkeypatch):
    responses = iter(
        [
            _Response(
                {
                    "items": [{"url": "https://example.com/one.jpg"}],
                    "next": "https://api.example.com/page-2",
                }
            ),
            _Response(
                {
                    "items": [
                        {"url": "https://example.com/one.jpg"},
                        {"url": "https://example.com/two.jpg"},
                    ],
                    "next": None,
                }
            ),
        ]
    )
    requested_urls = []
    monkeypatch.setattr(
        api.requests,
        "get",
        lambda url, **kwargs: (
            requested_urls.append(url) or next(responses)
        ),
    )

    images = api.discover_images(
        "https://api.example.com/page-1",
        image_field="url",
        title_field=None,
        records_path="items",
        source_type="photo",
        max_pages=3,
        next_url_field="next",
    )

    assert requested_urls == [
        "https://api.example.com/page-1",
        "https://api.example.com/page-2",
    ]
    assert [image.image_url for image in images] == [
        "https://example.com/one.jpg",
        "https://example.com/two.jpg",
    ]


def test_discover_images_retries_request_failures(monkeypatch):
    attempts = 0

    def request(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise api.requests.Timeout()
        return _Response([{"url": "https://example.com/recovered.jpg"}])

    monkeypatch.setattr(api.requests, "get", request)
    monkeypatch.setattr(api.time, "sleep", lambda seconds: None)

    images = api.discover_images(
        "https://api.example.com/images",
        image_field="url",
        title_field=None,
        records_path=None,
        source_type="photo",
    )

    assert attempts == 3
    assert images[0].image_url == "https://example.com/recovered.jpg"


def test_discover_images_rejects_non_object_records(monkeypatch):
    monkeypatch.setattr(
        api.requests,
        "get",
        lambda *args, **kwargs: _Response({"items": ["not an object"]}),
    )

    try:
        api.discover_images(
            "https://api.example.com/images",
            image_field="url",
            title_field=None,
            records_path="items",
            source_type="photo",
        )
    except ValueError as error:
        assert str(error) == "The selected API response value must be a list of objects"
    else:
        raise AssertionError("Expected invalid API records to raise ValueError")
