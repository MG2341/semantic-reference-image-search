# Reference Image Searcher

This is the minimal version of the project: a simple semantic search pipeline using CLIP.

## What this repo does

- downloads one sample image
- creates an image embedding with CLIP
- creates text embeddings for search queries
- compares them using cosine similarity
- prints the closest matching text description

## Main file

- `image_embed.py` – the complete basic pipeline

## Why this is the starting point

This keeps the project focused on the core idea before we add:

- batch ingestion
- persistence
- a vector database
- API endpoints
- production error handling
