from app.scraping import met


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_discover_met_images_searches_ids_then_fetches_objects(monkeypatch):
    responses = {
        "search": _Response({"objectIDs": [123, 456]}),
        "objects/123": _Response(
            {
                "primaryImage": "https://images.example.com/one.jpg",
                "primaryImageSmall": "https://images.example.com/one-small.jpg",
                "objectURL": "https://www.metmuseum.org/art/collection/search/123",
                "objectName": "Painting",
                "title": "One",
                "artistDisplayName": "Artist One",
                "objectDate": "1900",
                "creditLine": "Gift of Example",
            }
        ),
        "objects/456": _Response(
            {
                "primaryImage": "https://images.example.com/two.jpg",
                "objectName": "Painting",
                "title": "Two",
                "artistDisplayName": "",
            }
        ),
    }

    def request(url, **kwargs):
        key = "search" if url.endswith("/search") else "objects/" + url.rsplit("/", 1)[-1]
        return responses[key]

    monkeypatch.setattr(met.requests, "get", request)
    monkeypatch.setattr(met.time, "sleep", lambda seconds: None)

    images = met.discover_met_images("flowers", max_images=2)

    assert images[0].title == "One"
    assert images[0].artist == "Artist One"
    assert images[0].date == "1900"
    assert images[0].thumbnail_url == "https://images.example.com/one-small.jpg"
    assert images[0].credit_line == "Gift of Example"
    assert images[0].source_type == "master_artwork"
    assert images[0].source_page_url.endswith("/search/123")
    assert images[1].title == "Two"


def test_discover_met_images_skips_objects_without_images(monkeypatch):
    monkeypatch.setattr(
        met.requests,
        "get",
        lambda url, **kwargs: (
            _Response({"objectIDs": [123]})
            if url.endswith("/search")
            else _Response(
                {"primaryImage": "", "title": "No image", "objectName": "Painting"}
            )
        ),
    )

    assert met.discover_met_images("anything", max_images=1) == []


def test_discover_all_met_images_walks_object_ids(monkeypatch):
    responses = {
        "objects": _Response({"total": 2, "objectIDs": [123, 456]}),
        "objects/123": _Response(
            {"primaryImage": "https://images.example.com/one.jpg", "objectName": "Painting"}
        ),
        "objects/456": _Response(
            {"primaryImage": "https://images.example.com/two.jpg", "objectName": "Painting"}
        ),
    }

    def request(url, **kwargs):
        key = "objects" if url.endswith("/objects") else "objects/" + url.rsplit("/", 1)[-1]
        return responses[key]

    monkeypatch.setattr(met.requests, "get", request)
    monkeypatch.setattr(met.time, "sleep", lambda seconds: None)

    images = met.discover_all_met_images(max_images=2)

    assert [image.source_page_url.rsplit("/", 1)[-1] for image in images] == [
        "123",
        "456",
    ]


def test_discover_all_met_images_uses_random_seed(monkeypatch):
    responses = {
        "objects": _Response({"total": 3, "objectIDs": [123, 456, 789]}),
        "objects/123": _Response({"primaryImage": "https://images.example.com/one.jpg"}),
        "objects/456": _Response(
            {"primaryImage": "https://images.example.com/two.jpg", "objectName": "Painting"}
        ),
        "objects/789": _Response(
            {"primaryImage": "https://images.example.com/three.jpg", "objectName": "Painting"}
        ),
    }

    def request(url, **kwargs):
        key = "objects" if url.endswith("/objects") else "objects/" + url.rsplit("/", 1)[-1]
        return responses[key]

    monkeypatch.setattr(met.requests, "get", request)
    monkeypatch.setattr(met.time, "sleep", lambda seconds: None)

    images = met.discover_all_met_images(
        max_images=1,
        object_batch_size=1,
        random_seed=1,
    )

    assert images[0].source_page_url.endswith("/456")


def test_discover_all_met_images_can_skip_ordered_images(monkeypatch):
    responses = {
        "objects": _Response({"total": 3, "objectIDs": [123, 456, 789]}),
        "objects/123": _Response(
            {"primaryImage": "https://images.example.com/one.jpg", "objectName": "Painting"}
        ),
        "objects/456": _Response(
            {"primaryImage": "https://images.example.com/two.jpg", "objectName": "Painting"}
        ),
        "objects/789": _Response(
            {"primaryImage": "https://images.example.com/three.jpg", "objectName": "Painting"}
        ),
    }

    def request(url, **kwargs):
        key = "objects" if url.endswith("/objects") else "objects/" + url.rsplit("/", 1)[-1]
        return responses[key]

    monkeypatch.setattr(met.requests, "get", request)
    monkeypatch.setattr(met.time, "sleep", lambda seconds: None)

    images = met.discover_all_met_images(
        max_images=1,
        start_index=1,
        object_batch_size=1,
    )

    assert images[0].source_page_url.endswith("/456")
