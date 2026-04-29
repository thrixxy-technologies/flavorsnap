import os
import pytest
import torch
import torch.nn as nn
from unittest.mock import MagicMock, patch
from pathlib import Path
from model_validator import ModelValidator, ValidationConfig, ValidationResult
from model_registry import ModelRegistry

@pytest.fixture
def mock_registry():
    return MagicMock(spec=ModelRegistry)

@pytest.fixture
def validator(mock_registry, tmp_path):
    # Use a temp DB and temp directories
    registry_db = str(tmp_path / "test_validator.db")
    config = ValidationConfig(
        test_dataset_path=str(tmp_path / "dataset/test"),
        validation_dataset_path=str(tmp_path / "dataset/val")
    )
    return ModelValidator(mock_registry, config, registry_path=registry_db)

@pytest.mark.unit
def test_validation_config_defaults():
    config = ValidationConfig()
    assert config.min_accuracy_threshold == 0.80
    assert config.max_inference_time_threshold == 2.0
    assert config.test_dataset_path == "dataset/test"

@pytest.mark.unit
def test_load_model(validator):
    with patch('torch.load') as mock_torch_load, \
         patch('torchvision.models.resnet18') as mock_resnet:
        
        mock_model = MagicMock(spec=nn.Module)
        mock_resnet.return_value = mock_model
        mock_torch_load.return_value = {"state": "dict"}
        
        loaded_model = validator.load_model("dummy_path.pth")
        
        assert loaded_model == mock_model
        mock_torch_load.assert_called_once()
        mock_model.load_state_dict.assert_called_once_with({"state": "dict"})
        mock_model.eval.assert_called_once()

@pytest.mark.unit
def test_check_model_integrity_success(validator, tmp_path):
    model_path = tmp_path / "model.pth"
    model_path.write_bytes(b"dummy data" * 100) # Ensure > 1000 bytes
    
    with patch.object(validator, 'load_model') as mock_load:
        mock_model = MagicMock(spec=nn.Module)
        mock_model.fc = MagicMock()
        mock_model.fc.out_features = 6
        mock_load.return_value = mock_model
        
        # Mock forward pass
        mock_model.return_value = torch.randn(1, 6)
        
        passed, errors = validator.check_model_integrity(str(model_path))
        
        assert passed is True
        assert len(errors) == 0

@pytest.mark.unit
def test_check_model_integrity_file_not_found(validator):
    passed, errors = validator.check_model_integrity("nonexistent.pth")
    assert passed is False
    assert "Model file not found" in errors[0]

@pytest.mark.unit
def test_load_test_dataset(validator, tmp_path):
    dataset_path = tmp_path / "test_data"
    dataset_path.mkdir()
    
    # Create class directories and dummy images
    for cls in validator.class_names:
        class_dir = dataset_path / cls
        class_dir.mkdir()
        (class_dir / "img1.jpg").write_text("dummy")
        (class_dir / "img2.png").write_text("dummy")
        
    test_data, size = validator.load_test_dataset(str(dataset_path))
    
    assert size == 12 # 6 classes * 2 images
    assert len(test_data) == 12
    assert test_data[0][1] in validator.class_names

@pytest.mark.unit
def test_calculate_metrics(validator):
    inference_results = {
        'predictions': ['Akara', 'Bread', 'Akara', 'Yam'],
        'ground_truths': ['Akara', 'Bread', 'Yam', 'Yam'],
        'confidences': [0.9, 0.8, 0.7, 0.9],
        'inference_times': [0.1, 0.2, 0.1, 0.3],
        'error_count': 0
    }
    
    metrics = validator.calculate_metrics(inference_results)
    
    assert metrics['accuracy'] == 0.75 # 3 out of 4 correct
    assert metrics['avg_confidence'] == pytest.approx(0.825)
    assert metrics['total_predictions'] == 4

@pytest.mark.unit
def test_check_performance_regression_no_baseline(validator):
    passed, msgs = validator.check_performance_regression({}, None)
    assert passed is False
    assert msgs == []

@pytest.mark.unit
@patch('matplotlib.pyplot.savefig')
def test_generate_confusion_matrix(mock_savefig, validator, tmp_path):
    ground_truths = ['Akara', 'Bread']
    predictions = ['Akara', 'Egusi']
    
    path = validator.generate_confusion_matrix(ground_truths, predictions, "v1.0")
    
    assert path is not None
    assert "confusion_matrix_v1.0.png" in path
    mock_savefig.assert_called_once()

@pytest.mark.unit
def test_validate_model_full_flow(validator, mock_registry, tmp_path):
    model_version = "v1.0.1"
    model_path = tmp_path / "prod_model.pth"
    model_path.write_bytes(b"dummy data" * 200)
    
    # Setup mock registry
    mock_metadata = MagicMock()
    mock_metadata.model_path = str(model_path)
    mock_registry.get_model.return_value = mock_metadata
    
    # Mock internal methods to avoid heavy lifting
    with patch.object(validator, 'check_model_integrity', return_value=(True, [])), \
         patch.object(validator, 'load_model'), \
         patch.object(validator, 'load_test_dataset', return_value=([("p1", "Akara")], 1)), \
         patch.object(validator, 'run_inference_test', return_value={
             'predictions': ['Akara'], 'ground_truths': ['Akara'], 
             'confidences': [0.95], 'inference_times': [0.05], 'error_count': 0
         }), \
         patch.object(validator, 'generate_confusion_matrix', return_value="cm.png"):
        
        result = validator.validate_model(model_version)
        
        assert isinstance(result, ValidationResult)
        assert result.passed is True
        assert result.accuracy == 1.0
        assert result.model_version == model_version
