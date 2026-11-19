from __future__ import annotations

from typing import BinaryIO

from PIL import Image


MAX_SEARCH_IMAGE_DIMENSION = 2048


def prepare_image_for_search(
    file: BinaryIO,
    max_dimension: int = MAX_SEARCH_IMAGE_DIMENSION,
) -> Image.Image:
    if max_dimension < 1:
        raise ValueError("max_dimension must be at least 1")

    with Image.open(file) as image:
        if max(image.size) > max_dimension:
            image.thumbnail(
                (max_dimension, max_dimension),
                resample=Image.Resampling.LANCZOS,
            )
        return image.convert("RGB")
