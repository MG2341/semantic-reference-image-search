# Reference Image Searcher

This is a small semantic search pipeline using CLIP and a local Qdrant vector store.

## What this repo does

- downloads one sample image
- creates an image embedding with CLIP
- creates text embeddings for search queries
- stores the image embedding locally
- searches stored images using natural-language queries
- returns the `k` images whose embeddings best match the query

## Main files

- `main.py` – starts the demo
- `app/pipeline.py` – coordinates model loading, embedding, storage, and comparison
- `app/services/embedding_service.py` – downloads images and creates embeddings
- `app/db/local_vector.py` – stores embeddings in the local `data/` directory

## Running locally

This project does not require Docker or PostgreSQL. Install the Python dependencies and run:

```powershell
pip install -r requirements.txt
python main.py
```

After adding images to the local database, search them with:

```powershell
python -c "from app.pipeline import search_images; print(search_images('a red flower', k=5))"
```

Qdrant runs in local persistent mode and creates its database in `data/`. No Docker,
PostgreSQL, or separate database server is required.

## Why this is the starting point

This keeps the project focused on the core idea before we add:

- batch ingestion
- API endpoints
- production error handling
