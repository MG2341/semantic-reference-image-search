from __future__ import annotations

import io
from typing import TYPE_CHECKING

import torch
import requests
from PIL import Image

if TYPE_CHECKING:
    from transformers import CLIPModel, CLIPProcessor


def download_image(url: str) -> Image.Image:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    image = Image.open(io.BytesIO(response.content))
    return image.convert("RGB")


def unwrap_embedding(output) -> torch.Tensor:
    if hasattr(output, "pooler_output") and output.pooler_output is not None:
        return output.pooler_output
    if hasattr(output, "image_embeds"):
        return output.image_embeds
    if hasattr(output, "text_embeds"):
        return output.text_embeds
    if hasattr(output, "last_hidden_state"):
        return output.last_hidden_state[:, 0]
    if isinstance(output, torch.Tensor):
        return output
    raise TypeError(f"Unsupported model output type: {type(output)!r}")


def normalize(vector: torch.Tensor) -> torch.Tensor:
    return vector / vector.norm(p=2, dim=-1, keepdim=True)


def get_image_embedding(model: CLIPModel, processor: CLIPProcessor, image: Image.Image) -> torch.Tensor:
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        embedding = model.get_image_features(**inputs)
    embedding = unwrap_embedding(embedding)
    return normalize(embedding)


def get_text_embedding(model: CLIPModel, processor: CLIPProcessor, text: str) -> torch.Tensor:
    inputs = processor(text=[text], return_tensors="pt", padding=True)
    with torch.no_grad():
        embedding = model.get_text_features(**inputs)
    embedding = unwrap_embedding(embedding)
    return normalize(embedding)


def cosine_similarity(a: torch.Tensor, b: torch.Tensor) -> float:
    return torch.nn.functional.cosine_similarity(a, b).item()
