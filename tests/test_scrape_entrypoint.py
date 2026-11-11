import scrape


def test_scrape_api_passes_pagination_options(monkeypatch):
    observed = {}

    monkeypatch.setattr(scrape, "initialize_database", lambda: None)
    monkeypatch.setattr(
        scrape,
        "discover_images",
        lambda *args, **kwargs: observed.update(kwargs) or [],
    )
    monkeypatch.setattr(scrape, "process_images", lambda images, delay: 0)

    assert (
        scrape.scrape_api(
            "https://api.example.com/images",
            max_images=10,
            delay_seconds=0,
            source_type="photo",
            image_field="url",
            title_field=None,
            records_path=None,
            max_pages=4,
            next_url_field="next",
        )
        == 0
    )
    assert observed == {"max_pages": 4, "next_url_field": "next"}
