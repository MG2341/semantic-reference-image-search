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

The API adapter does not assume a particular provider, pagination scheme, or
response shape beyond the explicit field mapping. Provider-specific pagination
or authentication can be added as a separate adapter when needed.

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
API adapter -> ScrapedImage -> image download -> CLIP embedding -> SQLite
                                                     |
                                                     v
                                               filtered search
```

The project intentionally does not include generic HTML scraping or the
WetCanvas-specific scraper. Sources should be added only through APIs with
clear, documented response and usage policies.
