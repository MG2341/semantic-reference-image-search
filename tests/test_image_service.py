from io import BytesIO

from PIL import Image
import pytest

from app.services.image_service import prepare_image_for_search


def test_prepare_image_for_search_resizes_large_images():
    source = BytesIO()
    Image.new("RGB", (4000, 1000), color="white").save(source, format="PNG")
    source.seek(0)

    prepared = prepare_image_for_search(source)

    assert prepared.size == (2048, 512)
    assert prepared.mode == "RGB"


def test_prepare_image_for_search_keeps_small_images_at_original_size():
    source = BytesIO()
    Image.new("RGB", (800, 600), color="white").save(source, format="PNG")
    source.seek(0)

    prepared = prepare_image_for_search(source)

    assert prepared.size == (800, 600)
    assert prepared.mode == "RGB"


def test_prepare_image_for_search_rejects_invalid_dimension():
    with pytest.raises(ValueError, match="max_dimension must be at least 1"):
        prepare_image_for_search(BytesIO(), max_dimension=0)
