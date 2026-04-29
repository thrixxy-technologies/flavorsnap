from __future__ import annotations

from pathlib import Path

import pytest
import torch
from PIL import Image as PILImage

from src.core import ImageProcessor


@pytest.mark.unit
def test_image_processor_validate_image_rejects_wrong_extension(tmp_path: Path) -> None:
    image_path = tmp_path / "not_an_image.txt"
    PILImage.new("RGB", (16, 16), (1, 2, 3)).save(image_path, format="PNG")

    processor = ImageProcessor()
    assert processor.validate_image(str(image_path)) is False


@pytest.mark.unit
def test_image_processor_validate_image_rejects_corrupted_bytes(tmp_path: Path) -> None:
    image_path = tmp_path / "corrupted.png"
    image_path.write_bytes(b"definitely-not-an-image")

    processor = ImageProcessor()
    assert processor.validate_image(str(image_path)) is False


@pytest.mark.unit
def test_image_processor_preprocess_image_returns_tensor_with_expected_shape(tmp_path: Path) -> None:
    image_path = tmp_path / "food.png"
    PILImage.new("RGB", (32, 32), (10, 20, 30)).save(image_path)

    processor = ImageProcessor(input_size=(64, 64))
    tensor = processor.preprocess_image(str(image_path))

    assert isinstance(tensor, torch.Tensor)
    assert tensor.shape == (1, 3, 64, 64)


@pytest.mark.unit
def test_image_processor_get_image_info_returns_metadata(tmp_path: Path) -> None:
    image_path = tmp_path / "food.png"
    PILImage.new("RGB", (10, 12), (10, 20, 30)).save(image_path)

    processor = ImageProcessor()
    info = processor.get_image_info(str(image_path))

    assert info["format"] is not None
    assert info["mode"] == "RGB"
    assert "size" in info
    assert "file_size" in info

