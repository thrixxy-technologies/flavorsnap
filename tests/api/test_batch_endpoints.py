import pytest
from flask import Flask
from unittest.mock import MagicMock, patch
import io
import json
from batch_endpoints import register_batch_endpoints

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def mock_processor():
    return MagicMock()

@pytest.fixture
def client(app, mock_processor):
    register_batch_endpoints(app, mock_processor)
    return app.test_client()

@pytest.mark.unit
def test_create_batch_job_success(client, mock_processor):
    mock_processor.create_batch_job.return_value = "batch_123"
    
    data = {
        'files': (io.BytesIO(b"dummy image data"), 'test.jpg')
    }
    
    response = client.post('/api/batch/upload', 
                           data=data, 
                           content_type='multipart/form-data')
    
    assert response.status_code == 201
    assert response.get_json()['job_id'] == "batch_123"
    assert response.get_json()['total_files'] == 1

@pytest.mark.unit
def test_create_batch_job_no_files(client):
    response = client.post('/api/batch/upload', data={}, content_type='multipart/form-data')
    assert response.status_code == 400
    assert "No files provided" in response.get_json()['error']

@pytest.mark.unit
def test_get_batch_status_success(client, mock_processor):
    mock_job = MagicMock()
    mock_job.job_id = "batch_123"
    mock_job.status = "processing"
    import datetime
    mock_job.created_at = datetime.datetime.now()
    mock_job.started_at = None
    mock_job.completed_at = None
    mock_job.total_files = 10
    mock_job.processed_files = 5
    mock_job.failed_files = 0
    mock_job.progress_percentage = 50.0
    mock_job.errors = []
    
    mock_processor.get_job_status.return_value = mock_job
    
    response = client.get('/api/batch/status/batch_123')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == "processing"
    assert data['progress_percentage'] == 50.0

@pytest.mark.unit
def test_get_batch_status_not_found(client, mock_processor):
    mock_processor.get_job_status.return_value = None
    response = client.get('/api/batch/status/nonexistent')
    assert response.status_code == 404

@pytest.mark.unit
def test_cancel_batch_job_success(client, mock_processor):
    mock_processor.cancel_job.return_value = True
    response = client.post('/api/batch/cancel/batch_123')
    assert response.status_code == 200
    assert response.get_json()['status'] == "cancelled"

@pytest.mark.unit
def test_batch_health_check(client, mock_processor):
    mock_processor.current_job_id = "job_1"
    mock_processor.processing_queue.qsize.return_value = 2
    mock_processor.jobs = {}
    mock_processor.processing_thread.is_alive.return_value = True
    
    response = client.get('/api/batch/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['queue_size'] == 2
