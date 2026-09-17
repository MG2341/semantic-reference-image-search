from __future__ import annotations

import torch

from app.config import MODEL_NAME
from app.db.local_vector import init_db, search_embeddings
from app.services.embedding_service import (
    cosine_similarity,
    download_image,
    get_image_embedding,
    get_text_embedding,
)
from app.services.storage_service import save_image_embedding


def load_model():
    from transformers import CLIPModel, CLIPProcessor

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained(MODEL_NAME).to(device)
    processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    return model, processor


def search_images(query: str, k: int = 5) -> list[dict[str, object]]:
    """Search stored images using a natural-language query."""
    if not query.strip():
        raise ValueError("query must not be empty")
    if k < 1:
        raise ValueError("k must be at least 1")

    model, processor = load_model()
    text_embedding = get_text_embedding(model, processor, query)
    return search_embeddings(text_embedding[0].tolist(), limit=k)


def run_demo(image_url: str) -> None:
    init_db()

    model, processor = load_model()

    image = download_image(image_url)
    image_embedding = get_image_embedding(model, processor, image)

    save_image_embedding(
        url=image_url,
        label="demo flower image",
        embedding=image_embedding[0].tolist(),
    )

    candidate_queries = [
        "a flower in bloom",
        "a close-up portrait of a person",
        "a red flower on a green background",
        "a dramatic warrior scene",
        "a red flower with a white background",
    ]

    similarities = []
    for query in candidate_queries:
        text_embedding = get_text_embedding(model, processor, query)
        score = cosine_similarity(image_embedding, text_embedding)
        similarities.append((query, score))

    similarities.sort(key=lambda item: item[1], reverse=True)

    print("Image query pipeline demo")
    print("Best match:")
    for query, score in similarities[:3]:
        print(f"- {query}: {score:.4f}")
