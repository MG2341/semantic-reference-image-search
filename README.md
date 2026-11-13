# Reference Image Searcher

This project collects image links from JSON APIs, creates CLIP embeddings, and
supports semantic search over the stored images.

## Setup

SQLite is included with Python; no database server or Docker is required.
Install dependencies into the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The database is created at `data/reference_images.db`. Override it with
`SQLITE_DB_PATH`.

## API ingestion

The ingestion command expects an API returning either a JSON list of records or
an object containing a list at `--records-path`. Map the API's fields explicitly:

```powershell
python scrape.py "https://api.example.com/images" `
    --records-path data.results `
    --image-field image.url `
    --title-field title `
    --source-type photo `
    --max-images 100
```

Supported source types are `photo`, `movie_screencap`, `master_artwork`,
`other`, and `unknown`. If the API requires a bearer token, set
`API_BEARER_TOKEN` in the environment rather than putting the secret in the
command line.

The API adapter supports bounded cursor-style pagination when the response
contains a next-page URL:

```powershell
python scrape.py "https://api.example.com/images" `
    --records-path data.results `
    --next-url-field data.next `
    --max-pages 10
```

Requests are retried with exponential backoff. Provider-specific pagination
or authentication can still be added as a separate adapter when an API does
not expose next URLs.

## Met Museum ingestion

The Met uses two API calls: a collection search returns object IDs, and an
object-detail request provides the artwork image URL. Use the dedicated Met
entry point:

```powershell
python met_scrape.py "impressionism" --max-images 20
python met_scrape.py "landscape" --max-images 50 --delay 0.2
```

Met results are labeled `master_artwork` by default. Artworks without a
`primaryImage` are skipped. The Met API does not require an API key; the
adapter uses the documented paginated `v1.1/search` endpoint and stays well
below the documented request-rate limit.

To walk the complete Met object listing in object-ID order rather than relying
on a semantic/text query, use:

```powershell
python met_scrape.py --all --max-images 1000 --skip-images 0 --delay 0.2
```

The object listing includes works without images, so those are skipped. The
database deduplicates image URLs, which means rerunning the command is safe;
if a request fails, rerun it to retry the affected portion. To fetch the next
batch of 1000 ordered images, use `--skip-images 1000 --max-images 1000`.
The offset counts objects with a primary image, not objects without images.

## Search

```powershell
python search.py "a red flower in a garden" --top-k 5
python search.py "a dramatic scene" `
    --source-type movie_screencap --source-type master_artwork
```

Source types are assigned during ingestion and are never inferred from CLIP.
Repeated source-type flags are combined with OR logic.

## Demo

The original CLIP demonstration remains available:

```powershell
python main.py
```

## Architecture

```text
API adapter -> ImageRecord -> ingestion service -> CLIP embedding
                                      |                  |
                                      v                  v
                              duplicate URL check   SQLite repository
                                                         |
                                                         v
                                                   filtered search
```

SQLite separates image metadata from embeddings. Embeddings are tagged with
the model name and revision, so changing models does not silently mix
incompatible vectors. Existing databases using the old `image_embeddings`
table are migrated on initialization.
Image metadata includes `source_institution` (currently defaulting to `The
Metropolitan Museum of Art`) separately from `source_type`. Future metadata can
be added with a schema migration and backfilled by requesting each row's
`source_page_url`; embeddings do not need to be regenerated.

The project intentionally does not include generic HTML scraping or the
WetCanvas-specific scraper. Sources should be added only through APIs with
clear, documented response and usage policies. SQLite is appropriate for a
small prototype; move vector search to pgvector or a vector database when
the dataset no longer fits comfortably in an in-process Python scan.
