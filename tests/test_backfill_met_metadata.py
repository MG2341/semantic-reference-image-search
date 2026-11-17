import backfill_met_metadata as backfill


def test_backfill_metadata_updates_existing_met_record(monkeypatch):
    rows = [{"id": 7, "source_page_url": "https://www.metmuseum.org/art/collection/search/123"}]
    updates = []

    monkeypatch.setattr(backfill, "_met_rows", lambda max_images: rows)
    monkeypatch.setattr(
        backfill,
        "get_met_object",
        lambda object_id, retries: {
            "primaryImage": "https://images.example.com/full.jpg",
            "primaryImageSmall": "https://images.example.com/small.jpg",
            "objectURL": "https://www.metmuseum.org/art/collection/search/123",
            "title": "A painting",
            "artistDisplayName": "An artist",
            "objectDate": "1900",
            "creditLine": "Gift",
        },
    )
    monkeypatch.setattr(
        backfill,
        "update_image_metadata",
        lambda image_id, **metadata: updates.append((image_id, metadata)),
    )
    monkeypatch.setattr(backfill.time, "sleep", lambda seconds: None)

    assert backfill.backfill_metadata(None, 0, 3) == (1, 0)
    assert updates == [
        (
            7,
            {
                "source_page_url": "https://www.metmuseum.org/art/collection/search/123",
                "title": "A painting",
                "artist": "An artist",
                "date": "1900",
                "thumbnail_url": "https://images.example.com/small.jpg",
                "credit_line": "Gift",
            },
        )
    ]
