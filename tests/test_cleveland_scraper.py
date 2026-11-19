from app.scraping import cleveland


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def _record(image_url="https://images.example.com/one.jpg"):
    return {
        "id": 123,
        "accession_number": "2020.1",
        "title": "A landscape",
        "creation_date": "1900",
        "creators": [{"role": "artist", "description": "An artist"}],
        "culture": ["France"],
        "technique": "oil on canvas",
        "department": "European Art",
        "classification_type": "Painting",
        "type": "Painting",
        "measurements": "10 x 20 cm",
        "dimensions": {"unframed": {"height": 0.1, "width": 0.2}},
        "creditline": "Gift",
        "url": "https://clevelandart.org/art/2020.1",
        "images": {"web": {"url": image_url}},
        "share_license_status": "CC0",
    }


def test_extract_cleveland_metadata_maps_artwork_record():
    image = cleveland.extract_cleveland_metadata(_record())

    assert image["image_url"] == "https://images.example.com/one.jpg"
    assert image["title"] == "A landscape"
    assert image["artist"] == "An artist"
    assert image["height"] == "0.1"
    assert image["width"] == "0.2"
    assert image["source_institution"] == "Cleveland Museum of Art"
    assert image["is_public_domain"] is True


def test_discover_cleveland_images_paginates_full_listing(monkeypatch):
    responses = iter(
        [
            _Response({"data": [_record()], "info": {"total": 2}}),
            _Response(
                {
                    "data": [
                        _record("https://images.example.com/two.jpg"),
                    ],
                    "info": {"total": 2},
                }
            ),
        ]
    )
    requested = []

    def request(url, **kwargs):
        requested.append(kwargs["params"])
        return next(responses)

    monkeypatch.setattr(cleveland.requests, "get", request)

    images = cleveland.discover_cleveland_images(
        max_images=None,
        all_records=True,
        batch_size=1,
    )

    assert [image.image_url for image in images] == [
        "https://images.example.com/one.jpg",
        "https://images.example.com/two.jpg",
    ]
    assert [params["skip"] for params in requested] == [0, 1]


def test_discover_cleveland_images_small_run_stops_at_limit(monkeypatch):
    monkeypatch.setattr(
        cleveland.requests,
        "get",
        lambda *args, **kwargs: _Response(
            {"data": [_record(), _record("https://images.example.com/two.jpg")]}
        ),
    )

    images = cleveland.discover_cleveland_images(max_images=1)

    assert len(images) == 1


def test_discover_cleveland_images_starts_at_requested_index(monkeypatch):
    requested = []

    def request(url, **kwargs):
        requested.append(kwargs["params"]["skip"])
        return _Response({"data": [_record()], "info": {"total": 17462}})

    monkeypatch.setattr(cleveland.requests, "get", request)

    cleveland.discover_cleveland_images(
        max_images=1,
        all_records=False,
        start_index=17461,
    )

    assert requested == [17461]
