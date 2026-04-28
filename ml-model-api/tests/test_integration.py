"""
Integration tests for FlavorSnap ML API
"""

import pytest
import json
import time
from unittest.mock import patch, MagicMock
from PIL import Image
import io

from app import app

@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints"""

    def test_full_prediction_workflow(self, test_client, sample_image_file, mock_database):
        """Test complete prediction workflow from upload to result"""
        with patch('app.batch_processor') as mock_processor:
            with patch('app.cache_manager') as mock_cache:
                # Configure mocks
                mock_processor.submit_task.return_value = 'test-task-id'
                mock_cache.get_cached_prediction.return_value = None
                
                # Step 1: Submit image for prediction
                data = {
                    'image': sample_image_file,
                    'use_queue': 'true',
                    'priority': 'high'
                }
                
                response = test_client.post('/predict', data=data, content_type='multipart/form-data')
                assert response.status_code == 202
                
                result = json.loads(response.data)
                task_id = result['task_id']
                assert task_id is not None
                
                # Step 2: Check task status
                mock_processor.get_task_status.return_value = {
                    'id': task_id,
                    'status': 'completed',
                    'result': {'label': 'Jollof Rice', 'confidence': 0.95}
                }
                
                response = test_client.get(f'/queue/task/{task_id}')
                assert response.status_code == 200
                
                status = json.loads(response.data)
                assert status['status'] == 'completed'
                assert 'result' in status

    def test_cache_integration_workflow(self, test_client, sample_image_file, mock_cache_manager):
        """Test cache integration in prediction workflow"""
        # Configure cache to return cached result
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
            assert result['cached'] is True
            assert result['confidence'] == 0.88

    def test_queue_monitoring_integration(self, test_client, mock_queue_monitor, mock_cache_manager):
        """Test queue monitoring integration"""
        with patch('app.queue_monitor', mock_queue_monitor):
            with patch('app.cache_manager', mock_cache_manager):
                response = test_client.get('/queue/monitoring')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert 'queue_metrics' in data
                assert 'performance_summary' in data
                assert 'cache_stats' in data
                assert 'timestamp' in data

    def test_config_reload_integration(self, test_client, mock_config):
        """Test configuration reload integration"""
        response = test_client.post('/config/reload')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'message' in data
        assert 'reloaded successfully' in data['message'].lower()

    def test_health_check_integration(self, test_client, mock_database):
        """Test health check integration with all components"""
        response = test_client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'database' in data
        assert 'version' in data
        assert 'environment' in data

    def test_error_handling_integration(self, test_client):
        """Test error handling across the application"""
        # Test 404 error
        response = test_client.get('/non-existent-endpoint')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data

    def test_file_validation_integration(self, test_client):
        """Test file validation integration"""
        # Test with invalid file type
        invalid_file = ('test.exe', b'MZ\x90\x00', 'application/octet-stream')
        data = {'image': invalid_file}
        
        response = test_client.post('/predict', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        
        result = json.loads(response.data)
        assert 'error' in result
        assert 'File extension not allowed' in result['error']

    @pytest.mark.parametrize("priority", ['low', 'normal', 'high', 'critical'])
    def test_priority_queue_integration(self, test_client, sample_image_file, priority):
        """Test priority queue integration with different priorities"""
        with patch('app.batch_processor') as mock_processor:
            mock_processor.submit_task.return_value = f'task-{priority}'
            
            data = {
                'image': sample_image_file,
                'use_queue': 'true',
                'priority': priority
            }
            
            response = test_client.post('/predict', data=data, content_type='multipart/form-data')
            assert response.status_code == 202
            
            result = json.loads(response.data)
            assert result['priority'] == priority.upper()

    def test_metrics_export_integration(self, test_client, mock_queue_monitor):
        """Test metrics export integration"""
        mock_queue_monitor.export_metrics.return_value = '{"metrics": "test_data"}'
        
        with patch('app.queue_monitor', mock_queue_monitor):
            # Test JSON export
            response = test_client.get('/queue/export?format=json')
            assert response.status_code == 200
            assert response.content_type == 'application/json'
            
            # Test Prometheus export
            mock_queue_monitor.export_metrics.return_value = '# HELP test_metric Test metric\ntest_metric 1'
            response = test_client.get('/queue/export?format=prometheus')
            assert response.status_code == 200
            assert response.content_type == 'text/plain'

@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database components"""

    def test_database_connection_integration(self, test_client, mock_database):
        """Test database connection integration"""
        response = test_client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['database'] == 'connected'

    def test_database_failure_handling(self, test_client):
        """Test handling of database failures"""
        with patch('db_config.db_config.test_connection', return_value=False):
            response = test_client.get('/health')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['database'] == 'disconnected'

@pytest.mark.integration
class TestPersistenceIntegration:
    """Integration tests for persistence layer"""

    def test_queue_persistence_integration(self, test_client, sample_image_file):
        """Test queue persistence integration"""
        with patch('app.queue_persistence') as mock_persistence:
            with patch('app.batch_processor') as mock_processor:
                mock_processor.submit_task.return_value = 'persisted-task-id'
                
                data = {
                    'image': sample_image_file,
                    'use_queue': 'true'
                }
                
                response = test_client.post('/predict', data=data, content_type='multipart/form-data')
                assert response.status_code == 202
                
                # Verify persistence was called
                mock_persistence.save_task.assert_called_once()

@pytest.mark.integration
class TestLoggingIntegration:
    """Integration tests for logging components"""

    def test_logging_integration(self, test_client, sample_image_file):
        """Test logging integration across endpoints"""
        with patch('app.logger') as mock_logger:
            data = {'image': sample_image_file}
            response = test_client.post('/predict', data=data, content_type='multipart/form-data')
            
            # Verify logging calls were made
            assert mock_logger.info.called or mock_logger.error.called

    def test_error_logging_integration(self, test_client):
        """Test error logging integration"""
        with patch('app.logger') as mock_logger:
            # Trigger an error
            response = test_client.post('/predict')  # No image provided
            
            assert response.status_code == 400
            mock_logger.error.assert_called()

@pytest.mark.integration
class TestSecurityIntegration:
    """Integration tests for security components"""

    def test_file_upload_security(self, test_client):
        """Test file upload security integration"""
        # Test with potentially malicious file
        malicious_files = [
            ('test.php', b'<?php system($_GET["cmd"]); ?>', 'application/x-php'),
            ('test.html', b'<script>alert("xss")</script>', 'text/html'),
        ]
        
        for filename, content, content_type in malicious_files:
            data = {'image': (filename, content, content_type)}
            response = test_client.post('/predict', data=data, content_type='multipart/form-data')
            
            # Should be rejected due to file extension validation
            assert response.status_code == 400

    def test_request_size_limits(self, test_client):
        """Test request size limits integration"""
        # This test would normally require a very large file
        # For testing purposes, we'll mock the file size check
        with patch('app.request') as mock_request:
            mock_request.files.get.return_value = None
            
            response = test_client.post('/predict')
            # The exact behavior depends on Flask configuration

@pytest.mark.integration
class TestPerformanceIntegration:
    """Integration tests for performance components"""

    def test_response_time_integration(self, test_client, sample_image_file):
        """Test response time monitoring integration"""
        start_time = time.time()
        
        data = {'image': sample_image_file}
        response = test_client.post('/predict', data=data, content_type='multipart/form-data')
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        # Response time should be reasonable (adjust threshold as needed)
        assert response_time < 5.0

    def test_concurrent_requests_integration(self, test_client, sample_image_file):
        """Test handling of concurrent requests"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            data = {'image': sample_image_file}
            response = test_client.post('/predict', data=data, content_type='multipart/form-data')
            results.put(response.status_code)
        
        # Create multiple concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        success_count = 0
        while not results.empty():
            status_code = results.get()
            if status_code == 200:
                success_count += 1
        
        # Most requests should succeed
        assert success_count >= 4

@pytest.mark.integration
class TestConfigurationIntegration:
    """Integration tests for configuration management"""

    def test_configuration_changes_integration(self, test_client, mock_config):
        """Test configuration changes integration"""
        # Test getting current config
        response = test_client.get('/config')
        assert response.status_code == 200
        
        # Test reloading config
        response = test_client.post('/config/reload')
        assert response.status_code == 200
        
        # Verify config was reloaded
        data = json.loads(response.data)
        assert 'message' in data

    def test_environment_specific_configuration(self, test_client, mock_config):
        """Test environment-specific configuration"""
        response = test_client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'environment' in data

@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end workflow tests"""

    def test_complete_ml_workflow(self, test_client, sample_image_file):
        """Test complete ML workflow from upload to caching"""
        with patch('app.batch_processor') as mock_processor:
            with patch('app.cache_manager') as mock_cache:
                # Configure mocks for complete workflow
                task_id = 'end-to-end-task'
                mock_processor.submit_task.return_value = task_id
                mock_cache.get_cached_prediction.return_value = None
                
                # Step 1: Upload and queue image
                data = {
                    'image': sample_image_file,
                    'use_queue': 'true',
                    'priority': 'normal'
                }
                
                response = test_client.post('/predict', data=data, content_type='multipart/form-data')
                assert response.status_code == 202
                
                result = json.loads(response.data)
                assert result['task_id'] == task_id
                
                # Step 2: Check processing status
                mock_processor.get_task_status.return_value = {
                    'id': task_id,
                    'status': 'running'
                }
                
                response = test_client.get(f'/queue/task/{task_id}')
                assert response.status_code == 200
                
                # Step 3: Simulate completion
                mock_processor.get_task_status.return_value = {
                    'id': task_id,
                    'status': 'completed',
                    'result': {'label': 'Egusi Soup', 'confidence': 0.94}
                }
                
                response = test_client.get(f'/queue/task/{task_id}')
                assert response.status_code == 200
                
                status = json.loads(response.data)
                assert status['status'] == 'completed'
                assert status['result']['label'] == 'Egusi Soup'
                
                # Step 4: Verify cache would be updated
                assert mock_cache.cache_prediction_result.called

    def test_error_recovery_workflow(self, test_client, sample_image_file):
        """Test error recovery in the workflow"""
        with patch('app.batch_processor') as mock_processor:
            # Simulate task failure
            task_id = 'failed-task'
            mock_processor.submit_task.return_value = task_id
            mock_processor.get_task_status.return_value = {
                'id': task_id,
                'status': 'failed',
                'error_message': 'Processing failed'
            }
            
            data = {
                'image': sample_image_file,
                'use_queue': 'true'
            }
            
            response = test_client.post('/predict', data=data, content_type='multipart/form-data')
            assert response.status_code == 202
            
            # Check failed status
            response = test_client.get(f'/queue/task/{task_id}')
            assert response.status_code == 200
            
            status = json.loads(response.data)
            assert status['status'] == 'failed'
            assert 'error_message' in status
            
            # Test retry functionality
            mock_processor.retry_failed_task.return_value = True
            response = test_client.post(f'/queue/retry/{task_id}')
            assert response.status_code == 200

    def test_monitoring_dashboard_integration(self, test_client, mock_queue_monitor, mock_cache_manager):
        """Test monitoring dashboard data integration"""
        with patch('app.queue_monitor', mock_queue_monitor):
            with patch('app.cache_manager', mock_cache_manager):
                # Get monitoring data
                response = test_client.get('/queue/monitoring')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                
                # Verify all monitoring components are present
                assert 'queue_metrics' in data
                assert 'performance_summary' in data
                assert 'cache_stats' in data
                assert 'timestamp' in data
                
                # Get queue analytics
                response = test_client.get('/queue/analytics?hours=24')
                assert response.status_code == 200
                
                # Get queue status
                response = test_client.get('/queue/status')
                assert response.status_code in [200, 503]  # 503 if not initialized
