from __future__ import annotations

from app.bootstrap import initialize_database, load_clip_model


def run_demo(image_url: str) -> None:
    initialize_database()
    from app.services.embedding_service import (
        cosine_similarity,
        download_image,
        get_image_embedding,
        get_text_embedding,
    )
    from app.services.storage_service import save_image_embedding

    model, processor = load_clip_model()

    print("Downloading sample image...", flush=True)
    image = download_image(image_url)
    image_embedding = get_image_embedding(model, processor, image)

    save_image_embedding(
        url=image_url,
        label="demo flower image",
        embedding=image_embedding[0].tolist(),
        source_type="other",
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
    for query, score in similarities[:]:
        print(f"- {query}: {score:.4f}")
