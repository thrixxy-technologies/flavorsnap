import os
import sqlite3
import pytest
from pathlib import Path
from datetime import datetime

# Assuming PYTHONPATH includes ml-model-api
from model_registry import ModelRegistry, ModelMetadata

@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_model_registry.db")

@pytest.fixture
def temp_models_dir(tmp_path):
    models_dir = tmp_path / "models"
    models_dir.mkdir(exist_ok=True)
    return models_dir

@pytest.fixture
def temp_model_file(temp_models_dir):
    model_path = temp_models_dir / "dummy_model.pth"
    model_path.write_bytes(b"dummy_model_data_for_hash")
    return str(model_path)

@pytest.fixture
def registry(temp_db_path, temp_models_dir, monkeypatch):
    # Monkeypatch the Path("models") in ModelRegistry to point to our temp dir
    class PatchedModelRegistry(ModelRegistry):
        def __init__(self, registry_path):
            self.registry_path = registry_path
            self.models_dir = temp_models_dir
            self._init_database()
            
    return PatchedModelRegistry(registry_path=temp_db_path)

@pytest.mark.unit
def test_init_database_creates_tables(temp_db_path, registry):
    assert os.path.exists(temp_db_path)
    with sqlite3.connect(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        assert "models" in tables
        assert "ab_tests" in tables
        assert "predictions" in tables

@pytest.mark.unit
def test_register_model_success(registry, temp_model_file):
    success = registry.register_model(
        version="v1.0",
        model_path=temp_model_file,
        created_by="test_user",
        description="Test model",
        accuracy=0.95,
        loss=0.05,
        epochs_trained=10,
        tags=["test", "initial"],
        hyperparameters={"lr": 0.001}
    )
    assert success is True
    
    model = registry.get_model("v1.0")
    assert model is not None
    assert model.version == "v1.0"
    assert model.created_by == "test_user"
    assert model.accuracy == 0.95
    assert "test" in model.tags
    assert model.hyperparameters.get("lr") == 0.001

@pytest.mark.unit
def test_register_model_file_not_found(registry):
    success = registry.register_model(
        version="v1.0",
        model_path="nonexistent_file.pth",
        created_by="test_user",
        description="Test model"
    )
    assert success is False
    assert registry.get_model("v1.0") is None

@pytest.mark.unit
def test_get_model_not_found(registry):
    assert registry.get_model("nonexistent") is None

@pytest.mark.unit
def test_list_models(registry, temp_models_dir):
    model1_path = temp_models_dir / "m1.pth"
    model1_path.write_bytes(b"m1")
    model2_path = temp_models_dir / "m2.pth"
    model2_path.write_bytes(b"m2")
    
    registry.register_model("v1", str(model1_path), "u1", "d1")
    registry.register_model("v2", str(model2_path), "u2", "d2")
    
    models = registry.list_models()
    assert len(models) == 2
    # list_models orders by created_at DESC
    assert models[0].version == "v2"
    assert models[1].version == "v1"

@pytest.mark.unit
def test_activate_model(registry, temp_models_dir):
    model1_path = temp_models_dir / "m1.pth"
    model1_path.write_bytes(b"m1")
    model2_path = temp_models_dir / "m2.pth"
    model2_path.write_bytes(b"m2")
    
    registry.register_model("v1", str(model1_path), "u1", "d1")
    registry.register_model("v2", str(model2_path), "u2", "d2")
    
    # Activate v1
    assert registry.activate_model("v1") is True
    active = registry.get_active_model()
    assert active is not None
    assert active.version == "v1"
    
    # Activate v2
    assert registry.activate_model("v2") is True
    active = registry.get_active_model()
    assert active is not None
    assert active.version == "v2"
    
    # Check v1 is not active anymore
    v1_model = registry.get_model("v1")
    assert v1_model.is_active is False

@pytest.mark.unit
def test_delete_model(registry, temp_model_file):
    registry.register_model("v1", temp_model_file, "u1", "d1")
    
    # Should be able to delete non-active model
    assert registry.delete_model("v1") is True
    assert registry.get_model("v1") is None

@pytest.mark.unit
def test_delete_active_model_fails(registry, temp_model_file):
    registry.register_model("v1", temp_model_file, "u1", "d1")
    registry.activate_model("v1")
    
    # Active model should not be deleted
    assert registry.delete_model("v1") is False
    assert registry.get_model("v1") is not None

@pytest.mark.unit
def test_mark_stable(registry, temp_model_file):
    registry.register_model("v1", temp_model_file, "u1", "d1")
    
    assert registry.mark_stable("v1", True) is True
    model = registry.get_model("v1")
    assert model.is_stable is True
    
    assert registry.mark_stable("v1", False) is True
    model = registry.get_model("v1")
    assert model.is_stable is False
