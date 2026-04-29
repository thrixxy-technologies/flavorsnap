from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from PIL import Image


@pytest.fixture(scope="session")
def sample_image_bytes_png() -> bytes:
    """
    Deterministic small PNG payload for tests.
    We generate it on the fly to avoid storing binary fixtures in git.
    """

    img = Image.new("RGB", (64, 64), (123, 45, 67))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="session")
def corrupted_image_bytes() -> bytes:
    return b"this is not an image"


def _create_resnet18_state_dict(tmp_path: Path, num_classes: int) -> Path:
    """
    Create a dummy (random weights) ResNet18 checkpoint with the right `fc` size.
    This keeps `PyTorchFoodClassifier.load()` realistic without needing the real model.
    """

    import torch
    import torch.nn as nn
    from torchvision import models as torchvision_models

    model = torchvision_models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    model.eval()

    state_dict = model.state_dict()
    out_path = tmp_path / "dummy_model.pth"
    torch.save(state_dict, out_path)
    return out_path


@pytest.fixture
def dummy_pytorch_checkpoint(tmp_path: Path) -> dict[str, Any]:
    """
    Returns:
      - model_path: Path to a dummy checkpoint
      - classes_path: Path to a `food_classes.txt` file
      - class_names: List of class labels
    """

    # Keep these aligned with the API tests' expectations style.
    class_names = ["Akara", "Bread", "Egusi", "Moi Moi", "Rice and Stew", "Yam"]
    classes_path = tmp_path / "food_classes.txt"
    classes_path.write_text("\n".join(class_names) + "\n", encoding="utf-8")

    model_path = _create_resnet18_state_dict(tmp_path, num_classes=len(class_names))

    return {
        "model_path": model_path,
        "classes_path": classes_path,
        "class_names": class_names,
    }

