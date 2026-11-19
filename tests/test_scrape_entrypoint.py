import scrape
import met_scrape


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


def test_met_all_uses_max_images_for_results_and_batch_size_for_scan(
    monkeypatch,
):
    observed = {}

    monkeypatch.setattr(met_scrape, "initialize_database", lambda: None)
    monkeypatch.setattr(
        met_scrape,
        "get_scrape_progress",
        lambda source: 10,
    )
    monkeypatch.setattr(
        met_scrape,
        "get_or_create_scrape_seed",
        lambda source: 123,
    )
    monkeypatch.setattr(
        met_scrape,
        "discover_all_met_images",
        lambda **kwargs: observed.update(kwargs) or [],
    )
    monkeypatch.setattr(met_scrape, "process_images", lambda images, delay: 0)
    monkeypatch.setattr(
        met_scrape,
        "set_scrape_progress",
        lambda source, index: None,
    )
    monkeypatch.setattr(
        "sys.argv",
        ["met_scrape.py", "--all", "--max-images", "3", "--batch-size", "7"],
    )

    met_scrape.main()

    assert observed["max_images"] == 3
    assert observed["object_batch_size"] == 7
