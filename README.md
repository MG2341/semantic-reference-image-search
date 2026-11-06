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

## Search scraped images

After scraping images, search them with a text description:

```powershell
python search.py "a red flower in a garden" --top-k 5
```

The command embeds the description with the same CLIP model, compares it with
the stored image embeddings, and prints the best matching image URLs.

## Scrape a page

The separate scraper entry point extracts image URLs from one page and stores
their CLIP embeddings in SQLite:

```powershell
python scrape.py https://example.com/gallery --max-images 20
```

The scraper:

- checks the page's `robots.txt`
- extracts regular, lazy-loaded, and `srcset` image URLs
- limits the number of images
- waits between image requests
- skips individual download or decoding failures
- does not insert the same image URL more than once

This is intentionally a single-page ingestion command. Respect each site's
terms, copyright, and rate limits before scraping. It does not execute
JavaScript, crawl links, download original image files, or provide resumable
job tracking.

## Main file

- `main.py` – the executable entry point
- `scrape.py` – the image ingestion entry point
- `search.py` – the image search entry point

## Why this is the starting point

This keeps the project focused on the core idea before we add:

- batch ingestion
- scalable persistence
- a vector database
- API endpoints
- production error handling

The SQLite layer enforces unique image URLs. Re-running a scrape skips URLs
already stored in the database; it does not yet detect the same image served
under different URLs.
