from __future__ import annotations

from pathlib import Path

import pytest
import torch

from src.core import ModelManager


@pytest.mark.unit
def test_model_manager_get_model_info_not_loaded() -> None:
    mm = ModelManager(model_path="does-not-matter.pth")
    info = mm.get_model_info()
    assert info == {"status": "not_loaded"}


@pytest.mark.unit
def test_model_manager_load_model_reads_classes_and_loads_checkpoint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # ModelManager checks file existence before loading.
    model_path = tmp_path / "model.pth"
    model_path.write_bytes(b"dummy-checkpoint-bytes")

    # _load_classes reads a CWD-local `food_classes.txt`.
    food_classes_path = tmp_path / "food_classes.txt"
    food_classes_path.write_text("Akara\nBread\nEgusi\nMoi Moi\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    class DummyModel(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.loaded_state_dict: object | None = None

        def load_state_dict(self, state_dict: object) -> None:  # noqa: D401
            self.loaded_state_dict = state_dict

        def to(self, device: torch.device) -> "DummyModel":  # noqa: ANN001
            return self

        def eval(self) -> "DummyModel":
            return self

    def fake_hub_load(*args, **kwargs) -> DummyModel:  # noqa: ANN001, ARG001
        return DummyModel()

    def fake_torch_load(*args, **kwargs) -> dict[str, object]:  # noqa: ANN001, ARG001
        return {"some_weight": torch.zeros(1)}

    monkeypatch.setattr(torch.hub, "load", fake_hub_load)
    monkeypatch.setattr(torch, "load", fake_torch_load)

    mm = ModelManager(model_path=str(model_path))
    mm.load_model()

    assert isinstance(mm.model, DummyModel)
    assert mm.classes == ["Akara", "Bread", "Egusi", "Moi Moi"]
    assert mm.get_model_info()["status"] == "loaded"
    assert mm.get_model_info()["num_classes"] == 4


@pytest.mark.unit
def test_model_manager_load_classes_fallback_to_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    mm = ModelManager(model_path=str(tmp_path / "model.pth"))
    mm._load_classes()

    assert mm.classes == ["Akara", "Bread", "Egusi", "Moi Moi", "Rice and Stew", "Yam"]

