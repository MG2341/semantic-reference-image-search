# Reference Image Searcher

This is the minimal version of the project: a simple semantic search pipeline using CLIP.

## What this repo does

- downloads one sample image
- creates an image embedding with CLIP
- creates text embeddings for search queries
- compares them using cosine similarity
- prints the closest matching text description

## Run it

The demo uses SQLite, which is included with Python. No database server or
Docker is required. The database is created at
`data/reference_images.db` on first run. You can override that location with
the `SQLITE_DB_PATH` environment variable.

Then run:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

The first run also downloads the CLIP model and can take several minutes.
Subsequent runs use the local model cache.

## Scrape a page

The separate scraper entry point discovers images from one HTML page, embeds
them, and saves their URLs and embeddings to SQLite:

```powershell
python scrape.py https://example.com --max-images 20
```

This is intentionally limited to one page and a maximum image count. Before
scraping a real site, check its terms, `robots.txt`, copyright requirements,
and rate limits. The scraper does not execute JavaScript, crawl links, or
download original image files yet.

## Main file

- `main.py` – the executable entry point
- `scrape.py` – the image ingestion entry point

## Why this is the starting point

This keeps the project focused on the core idea before we add:

- batch ingestion
- scalable persistence
- a vector database
- API endpoints
- production error handling
