import pytest
from flask import Flask
from unittest.mock import MagicMock, patch
import json
from api_endpoints import (
    register_management_endpoints, 
    register_ab_testing_endpoints, 
    register_utility_endpoints
)

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app, mock_registry, mock_ab_manager, mock_deployment_manager, mock_validator):
    register_management_endpoints(app, mock_registry, mock_ab_manager, mock_deployment_manager, mock_validator)
    register_ab_testing_endpoints(app, mock_ab_manager)
    register_utility_endpoints(app)
    return app.test_client()

@pytest.fixture
def mock_registry():
    return MagicMock()

@pytest.fixture
def mock_ab_manager():
    return MagicMock()

@pytest.fixture
def mock_deployment_manager():
    return MagicMock()

@pytest.fixture
def mock_validator():
    return MagicMock()

@pytest.mark.unit
def test_list_models_endpoint(client, mock_registry):
    mock_model = MagicMock()
    mock_model.version = "v1.0"
    mock_model.created_at = "2023-01-01"
    mock_model.created_by = "admin"
    mock_model.description = "test"
    mock_model.accuracy = 0.9
    mock_model.loss = 0.1
    mock_model.epochs_trained = 10
    mock_model.is_active = True
    mock_model.is_stable = True
    mock_model.tags = ["test"]
    mock_model.model_path = "/path"
    
    mock_registry.list_models.return_value = [mock_model]
    
    response = client.get('/api/models')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['models']) == 1
    assert data['models'][0]['version'] == "v1.0"

@pytest.mark.unit
def test_register_model_endpoint(client, mock_registry):
    mock_registry.register_model.return_value = True
    
    payload = {
        "version": "v1.1",
        "model_path": "/some/path.pth",
        "created_by": "tester",
        "description": "New model"
    }
    
    response = client.post('/api/models/register', 
                           data=json.dumps(payload),
                           content_type='application/json')
    
    assert response.status_code == 201
    assert "registered successfully" in response.get_json()['message']

@pytest.mark.unit
def test_register_model_missing_fields(client):
    payload = {"version": "v1.1"} # Missing other required fields
    response = client.post('/api/models/register', 
                           data=json.dumps(payload),
                           content_type='application/json')
    assert response.status_code == 400
    assert "Missing required field" in response.get_json()['error']

@pytest.mark.unit
def test_activate_model_endpoint(client, mock_registry):
    mock_registry.activate_model.return_value = True
    response = client.post('/api/models/v1.1/activate')
    assert response.status_code == 200
    assert "activated successfully" in response.get_json()['message']

@pytest.mark.unit
def test_validate_model_endpoint(client, mock_validator):
    mock_result = MagicMock()
    mock_result.model_version = "v1.1"
    mock_result.passed = True
    mock_result.overall_score = 0.95
    mock_validator.validate_model.return_value = mock_result
    
    response = client.post('/api/models/v1.1/validate')
    assert response.status_code == 200
    data = response.get_json()
    assert data['model_version'] == "v1.1"
    assert data['passed'] is True

@pytest.mark.unit
def test_create_ab_test_endpoint(client, mock_ab_manager):
    mock_ab_manager.create_test.return_value = "test_uuid_123"
    payload = {
        "model_a_version": "v1.0",
        "model_b_version": "v1.1",
        "traffic_split": 0.5
    }
    response = client.post('/api/ab-tests', 
                           data=json.dumps(payload),
                           content_type='application/json')
    assert response.status_code == 201
    assert response.get_json()['test_id'] == "test_uuid_123"

@pytest.mark.unit
def test_health_check_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'healthy'

@pytest.mark.unit
def test_get_classes_endpoint(client):
    response = client.get('/api/classes')
    assert response.status_code == 200
    assert 'Akara' in response.get_json()['classes']
