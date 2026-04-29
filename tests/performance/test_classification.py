from __future__ import annotations

from pathlib import Path

import pytest

from src.api.classifier import PyTorchFoodClassifier
from src.api.models import PreprocessingOptions


def _run_classification(
    classifier: PyTorchFoodClassifier,
    image_bytes: bytes,
    options: PreprocessingOptions,
) -> list:
    return classifier.classify(image_bytes, options)


@pytest.mark.performance_smoke
def test_classification_performance_smoke(
    benchmark,
    dummy_pytorch_checkpoint: dict,
    sample_image_bytes_png: bytes,
) -> None:
    model_path: Path = dummy_pytorch_checkpoint["model_path"]
    classes_path: Path = dummy_pytorch_checkpoint["classes_path"]

    classifier = PyTorchFoodClassifier(model_path=model_path, classes_path=classes_path)
    classifier.load()

    options = PreprocessingOptions(resize=224, center_crop=True, normalize=True, top_k=3)

    benchmark(_run_classification, classifier, sample_image_bytes_png, options)


@pytest.mark.performance_full
def test_classification_performance_full(
    benchmark,
    dummy_pytorch_checkpoint: dict,
    sample_image_bytes_png: bytes,
) -> None:
    model_path: Path = dummy_pytorch_checkpoint["model_path"]
    classes_path: Path = dummy_pytorch_checkpoint["classes_path"]

    classifier = PyTorchFoodClassifier(model_path=model_path, classes_path=classes_path)
    classifier.load()

    options = PreprocessingOptions(resize=224, center_crop=True, normalize=True, top_k=3)

    # Measure more samples for more stable numbers (intentionally heavier than smoke).
    benchmark.pedantic(
        _run_classification,
        args=(classifier, sample_image_bytes_png, options),
        rounds=3,
        iterations=5,
    )

