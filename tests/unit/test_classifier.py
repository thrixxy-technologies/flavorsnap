from __future__ import annotations

from pathlib import Path

import pytest
import torch

from src.api.classifier import PyTorchFoodClassifier
from src.api.models import PreprocessingOptions
from src.core import FoodClassifier, ImageProcessor, ModelManager


@pytest.mark.unit
def test_pytorch_food_classifier_ready_and_class_names(dummy_pytorch_checkpoint: dict, tmp_path: Path) -> None:
    model_path: Path = dummy_pytorch_checkpoint["model_path"]
    classes_path: Path = dummy_pytorch_checkpoint["classes_path"]
    expected_class_names: list[str] = dummy_pytorch_checkpoint["class_names"]

    classifier = PyTorchFoodClassifier(model_path=model_path, classes_path=classes_path)
    assert classifier.ready is False
    assert classifier.class_names == expected_class_names

    classifier.load()
    assert classifier.ready is True


@pytest.mark.unit
def test_pytorch_food_classifier_load_missing_checkpoint_raises(tmp_path: Path) -> None:
    model_path = tmp_path / "missing-model.pth"
    classes_path = tmp_path / "food_classes.txt"
    classes_path.write_text("Akara\nBread\n", encoding="utf-8")

    classifier = PyTorchFoodClassifier(model_path=model_path, classes_path=classes_path)
    with pytest.raises(FileNotFoundError):
        classifier.load()


@pytest.mark.unit
def test_pytorch_food_classifier_classify_returns_ranked_predictions(
    dummy_pytorch_checkpoint: dict, sample_image_bytes_png: bytes
) -> None:
    model_path: Path = dummy_pytorch_checkpoint["model_path"]
    classes_path: Path = dummy_pytorch_checkpoint["classes_path"]
    expected_class_names: list[str] = dummy_pytorch_checkpoint["class_names"]

    classifier = PyTorchFoodClassifier(model_path=model_path, classes_path=classes_path)
    classifier.load()

    options = PreprocessingOptions(resize=224, center_crop=True, normalize=True, top_k=2)
    results = classifier.classify(sample_image_bytes_png, options)

    assert len(results) == 2
    for pred in results:
        assert pred.label in expected_class_names
        assert 0.0 <= pred.confidence <= 1.0


@pytest.mark.unit
def test_food_classifier_classify_image_returns_expected_shape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class_names = ["Akara", "Bread", "Egusi", "Moi Moi"]
    logits = torch.tensor([0.1, 0.2, 1.0, 0.3], dtype=torch.float32)

    class DummyModel(torch.nn.Module):
        def forward(self, x: torch.Tensor) -> torch.Tensor:  # noqa: ANN001
            # Output logits for a single batch element.
            batch_size = x.shape[0]
            return logits.unsqueeze(0).expand(batch_size, logits.shape[0])

    def fake_load_model(self: ModelManager, force_reload: bool = False) -> torch.nn.Module:  # noqa: ARG001
        self.device = torch.device("cpu")
        self.classes = class_names
        self.model = DummyModel()
        return self.model

    monkeypatch.setattr(ModelManager, "load_model", fake_load_model)
    monkeypatch.setattr(
        ImageProcessor,
        "preprocess_image",
        lambda self, image_path: torch.zeros((1, 3, 224, 224), dtype=torch.float32),
    )

    # Use a valid image file so `get_image_info()` can extract metadata.
    from PIL import Image as PILImage

    image_path = tmp_path / "food.png"
    PILImage.new("RGB", (32, 32), (10, 20, 30)).save(image_path)

    # validate_image() already checks extension + verify(); leave it as-is.
    clf = FoodClassifier(model_path=str(tmp_path / "irrelevant.pth"), confidence_threshold=0.6)
    result = clf.classify_image(str(image_path))

    assert result["success"] is True
    assert isinstance(result["prediction"], dict)
    assert result["prediction"]["label"] == "Egusi"
    assert 0.0 <= result["prediction"]["confidence"] <= 100.0

    assert len(result["all_predictions"]) == len(class_names)
    assert result["all_predictions"][0]["rank"] == 1

    # Ensure we included info from image processing.
    image_info = result["image_info"]
    assert image_info["format"] in {"PNG", "png", "Png"}
    assert "mode" in image_info
    assert "size" in image_info
    assert "file_size" in image_info


@pytest.mark.unit
def test_food_classifier_update_confidence_threshold_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_load_model(self: ModelManager, force_reload: bool = False) -> torch.nn.Module:  # noqa: ARG001
        self.device = torch.device("cpu")
        self.classes = ["Akara"]
        self.model = torch.nn.Identity()
        return self.model

    monkeypatch.setattr(ModelManager, "load_model", fake_load_model)
    clf = FoodClassifier(model_path="irrelevant.pth", confidence_threshold=0.6)

    with pytest.raises(ValueError):
        clf.update_confidence_threshold(-0.01)
    with pytest.raises(ValueError):
        clf.update_confidence_threshold(1.01)

    clf.update_confidence_threshold(1.0)
    assert clf.confidence_threshold == 1.0


@pytest.mark.unit
def test_food_classifier_get_classifier_info(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class_names = ["Akara", "Bread"]

    def fake_load_model(self: ModelManager, force_reload: bool = False) -> torch.nn.Module:  # noqa: ARG001
        self.device = torch.device("cpu")
        self.classes = class_names
        self.model = torch.nn.Identity()
        return self.model

    monkeypatch.setattr(ModelManager, "load_model", fake_load_model)
    clf = FoodClassifier(model_path=str(tmp_path / "irrelevant.pth"), confidence_threshold=0.6)

    info = clf.get_classifier_info()
    assert set(info.keys()) == {"model_info", "confidence_threshold", "supported_classes", "input_size"}
    assert info["supported_classes"] == class_names

