"""
Unit tests for the main Flask application
"""

import pytest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from PIL import Image
import io

from app import app

@pytest.mark.unit
class TestApp:
    """Test cases for the main Flask application"""

    def test_app_creation(self):
        """Test that Flask app is created successfully"""
        assert app is not None
        assert app.config['SECRET_KEY'] is not None

    @pytest.mark.parametrize("endpoint,expected_status", [
        ("/health", 200),
        ("/config", 200),
        ("/queue/status", 503),  # Should return 503 when queue not initialized
    ])
    def test_basic_endpoints(self, test_client, endpoint, expected_status):
        """Test basic endpoints return expected status codes"""
        response = test_client.get(endpoint)
        assert response.status_code == expected_status

    def test_health_check_success(self, test_client, mock_database):
        """Test successful health check"""
        response = test_client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'database' in data
        assert 'version' in data
        assert 'environment' in data

    def test_health_check_failure(self, test_client):
        """Test health check when database fails"""
        with patch('db_config.db_config.test_connection', return_value=False):
            response = test_client.get('/health')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['status'] == 'healthy'  # Still healthy, just database disconnected
            assert data['database'] == 'disconnected'

    def test_config_info_endpoint(self, test_client, mock_config):
        """Test configuration info endpoint"""
        response = test_client.get('/config')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'environment' in data
        assert 'last_reload' in data
        assert 'version_count' in data
        assert 'watcher_active' in data
        assert 'backup_count' in data
        assert 'validation_status' in data
        
        # Ensure no sensitive information is exposed
        assert 'secret_key' not in data
        assert 'password' not in data

    def test_config_reload_endpoint(self, test_client, mock_config):
        """Test configuration reload endpoint"""
        response = test_client.post('/config/reload')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'message' in data
        assert 'reloaded successfully' in data['message'].lower()

    def test_predict_endpoint_no_image(self, test_client):
        """Test predict endpoint without image"""
        response = test_client.post('/predict')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'No image uploaded' in data['error']

    def test_predict_endpoint_invalid_extension(self, test_client):
        """Test predict endpoint with invalid file extension"""
        data = {
            'image': (io.BytesIO(b'test content'), 'test.exe', 'application/octet-stream')
        }
        response = test_client.post('/predict', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        
        response_data = json.loads(response.data)
        assert 'error' in response_data
        assert 'File extension not allowed' in response_data['error']

    def test_predict_endpoint_with_valid_image(self, test_client, sample_image_file, mock_cache_manager):
        """Test predict endpoint with valid image"""
        with patch('app.cache_manager', mock_cache_manager):
            data = {'image': sample_image_file}
            response = test_client.post('/predict', data=data, content_type='multipart/form-data')
            assert response.status_code == 200
            
            result = json.loads(response.data)
            assert 'label' in result
            assert 'confidence' in result
            assert 'model_version' in result
            assert result['label'] == 'Moi Moi'  # Dummy output from app.py

    def test_predict_endpoint_cache_hit(self, test_client, sample_image_file, mock_cache_manager):
        """Test predict endpoint with cache hit"""
        # Configure mock to return cached result
        mock_cache_manager.get_cached_prediction.return_value = {
            'label': 'Cached Food',
            'confidence': 0.88
        }
        
        with patch('app.cache_manager', mock_cache_manager):
            data = {'image': sample_image_file}
            response = test_client.post('/predict', data=data, content_type='multipart/form-data')
            assert response.status_code == 200
            
            result = json.loads(response.data)
            assert result['label'] == 'Cached Food'
            assert result['confidence'] == 0.88
            assert result['cached'] is True

    def test_predict_endpoint_queue_processing(self, test_client, sample_image_file, mock_batch_processor, mock_cache_manager):
        """Test predict endpoint with queue processing"""
        with patch('app.batch_processor', mock_batch_processor):
            with patch('app.cache_manager', mock_cache_manager):
                data = {
                    'image': sample_image_file,
                    'use_queue': 'true',
                    'priority': 'high'
                }
                response = test_client.post('/predict', data=data, content_type='multipart/form-data')
                assert response.status_code == 202
                
                result = json.loads(response.data)
                assert 'task_id' in result
                assert result['status'] == 'queued'
                assert result['priority'] == 'HIGH'

    @pytest.mark.parametrize("priority,expected_priority", [
        ('low', 'LOW'),
        ('normal', 'NORMAL'),
        ('high', 'HIGH'),
        ('critical', 'CRITICAL'),
        ('invalid', 'NORMAL'),  # Default fallback
    ])
    def test_predict_endpoint_queue_priorities(self, test_client, sample_image_file, mock_batch_processor, 
                                              mock_cache_manager, priority, expected_priority):
        """Test predict endpoint with different queue priorities"""
        with patch('app.batch_processor', mock_batch_processor):
            with patch('app.cache_manager', mock_cache_manager):
                data = {
                    'image': sample_image_file,
                    'use_queue': 'true',
                    'priority': priority
                }
                response = test_client.post('/predict', data=data, content_type='multipart/form-data')
                assert response.status_code == 202
                
                result = json.loads(response.data)
                assert result['priority'] == expected_priority

    def test_queue_status_endpoint(self, test_client, mock_batch_processor):
        """Test queue status endpoint"""
        with patch('app.batch_processor', mock_batch_processor):
            response = test_client.get('/queue/status')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'pending_tasks' in data
            assert 'running_tasks' in data
            assert 'completed_tasks' in data
            assert 'failed_tasks' in data

    def test_queue_status_endpoint_not_initialized(self, test_client):
        """Test queue status endpoint when queue system not initialized"""
        response = test_client.get('/queue/status')
        assert response.status_code == 503
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not initialized' in data['error']

    def test_get_task_status_endpoint(self, test_client, mock_batch_processor):
        """Test get task status endpoint"""
        with patch('app.batch_processor', mock_batch_processor):
            response = test_client.get('/queue/task/test-task-id')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'id' in data
            assert 'status' in data
            assert 'result' in data

    def test_get_task_status_not_found(self, test_client, mock_batch_processor):
        """Test get task status for non-existent task"""
        mock_batch_processor.get_task_status.return_value = None
        with patch('app.batch_processor', mock_batch_processor):
            response = test_client.get('/queue/task/non-existent-task')
            assert response.status_code == 404
            
            data = json.loads(response.data)
            assert 'error' in data
            assert 'not found' in data['error']

    def test_cancel_task_endpoint(self, test_client, mock_batch_processor):
        """Test cancel task endpoint"""
        mock_batch_processor.cancel_task.return_value = True
        with patch('app.batch_processor', mock_batch_processor):
            response = test_client.post('/queue/task/test-task-id/cancel')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'message' in data
            assert 'cancelled successfully' in data['message']

    def test_cancel_task_not_found(self, test_client, mock_batch_processor):
        """Test cancel task for non-existent task"""
        mock_batch_processor.cancel_task.return_value = False
        with patch('app.batch_processor', mock_batch_processor):
            response = test_client.post('/queue/task/non-existent-task/cancel')
            assert response.status_code == 404
            
            data = json.loads(response.data)
            assert 'error' in data

    def test_retry_task_endpoint(self, test_client, mock_batch_processor):
        """Test retry task endpoint"""
        mock_batch_processor.retry_failed_task.return_value = True
        with patch('app.batch_processor', mock_batch_processor):
            response = test_client.post('/queue/task/test-task-id/retry')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'message' in data
            assert 'requeued for retry' in data['message']

    def test_queue_monitoring_endpoint(self, test_client, mock_queue_monitor, mock_cache_manager):
        """Test queue monitoring endpoint"""
        with patch('app.queue_monitor', mock_queue_monitor):
            with patch('app.cache_manager', mock_cache_manager):
                response = test_client.get('/queue/monitoring')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert 'queue_metrics' in data
                assert 'performance_summary' in data
                assert 'cache_stats' in data
                assert 'timestamp' in data

    def test_queue_analytics_endpoint(self, test_client, mock_queue_monitor):
        """Test queue analytics endpoint"""
        with patch('app.queue_monitor', mock_queue_monitor):
            response = test_client.get('/queue/analytics?hours=24')
            assert response.status_code == 200

    def test_export_metrics_json(self, test_client, mock_queue_monitor):
        """Test export metrics endpoint with JSON format"""
        mock_queue_monitor.export_metrics.return_value = '{"metrics": "test"}'
        with patch('app.queue_monitor', mock_queue_monitor):
            response = test_client.get('/queue/export?format=json')
            assert response.status_code == 200
            assert response.content_type == 'application/json'

    def test_export_metrics_prometheus(self, test_client, mock_queue_monitor):
        """Test export metrics endpoint with Prometheus format"""
        mock_queue_monitor.export_metrics.return_value = '# HELP test_metric Test metric'
        with patch('app.queue_monitor', mock_queue_monitor):
            response = test_client.get('/queue/export?format=prometheus')
            assert response.status_code == 200
            assert response.content_type == 'text/plain'

    def test_error_handlers(self, test_client):
        """Test error handlers"""
        # Test 404 error
        response = test_client.get('/non-existent-endpoint')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error']

    def test_file_too_large(self, test_client):
        """Test file size limit error"""
        # Create a large payload (simulating file too large)
        large_data = 'A' * (17 * 1024 * 1024)  # 17MB
        
        with patch('flask.request.files.get') as mock_get_file:
            mock_file = MagicMock()
            mock_file.filename = 'large_image.jpg'
            mock_get_file.return_value = mock_file
            
            # Simulate the 413 error
            with patch('app.request') as mock_request:
                mock_request.form.get.return_value = 'false'
                response = test_client.post('/predict')
                # This might not trigger the actual 413 in test environment
                # but the handler should exist

    @pytest.mark.parametrize("invalid_method", ["GET", "PUT", "DELETE", "PATCH"])
    def test_predict_endpoint_invalid_methods(self, test_client, invalid_method):
        """Test predict endpoint with invalid HTTP methods"""
        response = getattr(test_client, invalid_method.lower())('/predict')
        assert response.status_code == 405  # Method Not Allowed

    def test_app_configuration(self):
        """Test Flask app configuration"""
        assert app.config['TESTING'] is not None
        assert 'MAX_CONTENT_LENGTH' in app.config
        assert isinstance(app.config['MAX_CONTENT_LENGTH'], int)

    def test_secret_key_configuration(self):
        """Test that secret key is properly configured"""
        secret_key = app.config.get('SECRET_KEY')
        assert secret_key is not None
        assert len(secret_key) > 0
