from __future__ import annotations

from app.config import MODEL_NAME
from app.db.sqlite import init_db


def initialize_database() -> None:
    print("Opening SQLite database...", flush=True)
    try:
        init_db()
    except Exception as error:
        raise RuntimeError(
            "Could not initialize the SQLite database. Check SQLITE_DB_PATH "
            "and its parent directory."
        ) from error


def load_clip_model():
    import torch
    from transformers import CLIPModel, CLIPProcessor

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading CLIP model on {device}; the first run downloads it...", flush=True)
    model = CLIPModel.from_pretrained(MODEL_NAME).to(device)
    model.eval()
    processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    return model, processor
