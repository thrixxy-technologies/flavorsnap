"""
Performance tests for FlavorSnap ML API
"""

import pytest
import time
import threading
import queue
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock
from PIL import Image
import io

from app import app

@pytest.mark.performance
class TestAPIPerformance:
    """Performance tests for API endpoints"""

    @pytest.fixture
    def performance_image(self):
        """Create a performance test image"""
        img = Image.new('RGB', (224, 224), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes.getvalue()

    def test_predict_endpoint_response_time(self, test_client, performance_image):
        """Test predict endpoint response time under load"""
        response_times = []
        
        for _ in range(10):
            start_time = time.time()
            
            data = {'image': ('perf_test.jpg', performance_image, 'image/jpeg')}
            response = test_client.post('/predict', data=data, content_type='multipart/form-data')
            
            end_time = time.time()
            response_times.append(end_time - start_time)
            
            assert response.status_code == 200
        
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        # Performance assertions
        assert avg_response_time < 1.0, f"Average response time {avg_response_time:.3f}s exceeds 1.0s"
        assert max_response_time < 2.0, f"Max response time {max_response_time:.3f}s exceeds 2.0s"

    def test_concurrent_predictions_performance(self, test_client, performance_image):
        """Test concurrent prediction performance"""
        num_threads = 5
        requests_per_thread = 10
        results = queue.Queue()
        
        def make_predictions():
            thread_times = []
            for _ in range(requests_per_thread):
                start_time = time.time()
                
                data = {'image': ('concurrent_test.jpg', performance_image, 'image/jpeg')}
                response = test_client.post('/predict', data=data, content_type='multipart/form-data')
                
                end_time = time.time()
                thread_times.append(end_time - start_time)
                results.put((response.status_code, end_time - start_time))
        
        # Start concurrent threads
        threads = []
        start_time = time.time()
        
        for _ in range(num_threads):
            thread = threading.Thread(target=make_predictions)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Collect results
        response_times = []
        success_count = 0
        
        while not results.empty():
            status_code, response_time = results.get()
            response_times.append(response_time)
            if status_code == 200:
                success_count += 1
        
        # Performance assertions
        total_requests = num_threads * requests_per_thread
        success_rate = success_count / total_requests
        avg_response_time = statistics.mean(response_times)
        throughput = total_requests / total_time
        
        assert success_rate >= 0.95, f"Success rate {success_rate:.2f} below 95%"
        assert avg_response_time < 2.0, f"Average response time {avg_response_time:.3f}s exceeds 2.0s"
        assert throughput >= 5.0, f"Throughput {throughput:.2f} req/s below 5 req/s"

    def test_health_check_performance(self, test_client):
        """Test health check endpoint performance"""
        response_times = []
        
        for _ in range(100):
            start_time = time.time()
            response = test_client.get('/health')
            end_time = time.time()
            
            response_times.append(end_time - start_time)
            assert response.status_code == 200
        
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        
        assert avg_response_time < 0.1, f"Health check avg time {avg_response_time:.3f}s exceeds 0.1s"
        assert p95_response_time < 0.2, f"Health check 95th percentile {p95_response_time:.3f}s exceeds 0.2s"

    def test_queue_status_performance(self, test_client, mock_batch_processor):
        """Test queue status endpoint performance"""
        with patch('app.batch_processor', mock_batch_processor):
            response_times = []
            
            for _ in range(50):
                start_time = time.time()
                response = test_client.get('/queue/status')
                end_time = time.time()
                
                response_times.append(end_time - start_time)
                assert response.status_code == 200
            
            avg_response_time = statistics.mean(response_times)
            assert avg_response_time < 0.5, f"Queue status avg time {avg_response_time:.3f}s exceeds 0.5s"

    def test_memory_usage_stability(self, test_client, performance_image):
        """Test memory usage stability under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make many requests
        for i in range(100):
            data = {'image': (f'test_{i}.jpg', performance_image, 'image/jpeg')}
            response = test_client.post('/predict', data=data, content_type='multipart/form-data')
            assert response.status_code == 200
            
            # Check memory every 20 requests
            if i % 20 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                
                # Memory shouldn't increase too much
                assert memory_increase < 100, f"Memory increased by {memory_increase:.1f}MB"

    def test_cache_performance(self, test_client, performance_image, mock_cache_manager):
        """Test cache performance impact"""
        with patch('app.cache_manager', mock_cache_manager):
            # Test without cache hit
            mock_cache_manager.get_cached_prediction.return_value = None
            response_times = []
            
            for _ in range(20):
                start_time = time.time()
                data = {'image': ('cache_test.jpg', performance_image, 'image/jpeg')}
                response = test_client.post('/predict', data=data, content_type='multipart/form-data')
                end_time = time.time()
                
                response_times.append(end_time - start_time)
                assert response.status_code == 200
            
            no_cache_avg = statistics.mean(response_times)
            
            # Test with cache hit
            mock_cache_manager.get_cached_prediction.return_value = {
                'label': 'Cached Food',
                'confidence': 0.88
            }
            
            cache_response_times = []
            for _ in range(20):
                start_time = time.time()
                data = {'image': ('cache_test.jpg', performance_image, 'image/jpeg')}
                response = test_client.post('/predict', data=data, content_type='multipart/form-data')
                end_time = time.time()
                
                cache_response_times.append(end_time - start_time)
                assert response.status_code == 200
            
            cache_avg = statistics.mean(cache_response_times)
            
            # Cache should improve performance
            performance_improvement = (no_cache_avg - cache_avg) / no_cache_avg
            assert performance_improvement > 0.1, f"Cache performance improvement {performance_improvement:.2f} below 10%"

@pytest.mark.performance
class TestBatchProcessorPerformance:
    """Performance tests for batch processor"""

    def test_batch_processor_throughput(self):
        """Test batch processor throughput"""
        from batch_processor import MLBatchProcessor, TaskPriority
        
        processor = MLBatchProcessor(None, max_workers=4, queue_size=1000)
        
        # Submit many tasks
        num_tasks = 100
        start_time = time.time()
        
        task_ids = []
        for i in range(num_tasks):
            task_id = processor.submit_task({"data": f"task_{i}"}, TaskPriority.NORMAL)
            task_ids.append(task_id)
        
        submission_time = time.time() - start_time
        
        # Check queue stats
        stats = processor.get_queue_stats()
        
        # Performance assertions
        assert stats['pending_tasks'] == num_tasks
        assert submission_time < 1.0, f"Task submission took {submission_time:.3f}s for {num_tasks} tasks"
        assert stats['pending_tasks'] / submission_time > 50, f"Submission rate {stats['pending_tasks']/submission_time:.1f} tasks/s below 50"
        
        processor.shutdown()

    def test_priority_processing_performance(self):
        """Test priority processing performance"""
        from batch_processor import MLBatchProcessor, TaskPriority
        
        processor = MLBatchProcessor(None, max_workers=2, queue_size=100)
        
        # Submit tasks with different priorities
        priorities = [TaskPriority.LOW, TaskPriority.NORMAL, TaskPriority.HIGH, TaskPriority.CRITICAL]
        task_ids = []
        
        start_time = time.time()
        
        for priority in priorities:
            for i in range(25):
                task_id = processor.submit_task({"data": f"{priority.name}_{i}"}, priority)
                task_ids.append(task_id)
        
        submission_time = time.time() - start_time
        
        # Verify priority ordering
        queued_tasks = []
        while not processor.task_queue.empty():
            queued_tasks.append(processor.task_queue.get())
        
        # Check that tasks are ordered by priority
        priority_values = [task.priority.value for task in queued_tasks]
        assert priority_values == sorted(priority_values), "Tasks not properly ordered by priority"
        
        processor.shutdown()

    def test_concurrent_task_submission(self):
        """Test concurrent task submission performance"""
        from batch_processor import MLBatchProcessor
        
        processor = MLBatchProcessor(None, max_workers=4, queue_size=1000)
        
        def submit_tasks(thread_id):
            task_ids = []
            for i in range(25):
                task_id = processor.submit_task({"thread": thread_id, "data": i})
                task_ids.append(task_id)
            return task_ids
        
        # Submit tasks concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(submit_tasks, i) for i in range(4)]
            results = [future.result() for future in as_completed(futures)]
        
        # Verify all tasks were submitted
        total_tasks = sum(len(task_ids) for task_ids in results)
        assert total_tasks == 100
        
        stats = processor.get_queue_stats()
        assert stats['pending_tasks'] == 100
        
        processor.shutdown()

@pytest.mark.performance
class TestCachePerformance:
    """Performance tests for cache manager"""

    def test_cache_set_performance(self):
        """Test cache set performance"""
        from cache_manager import CacheManager
        
        config = {'max_size': 10000, 'ttl_seconds': 3600}
        cache = CacheManager(config)
        
        # Test cache set performance
        num_operations = 1000
        start_time = time.time()
        
        for i in range(num_operations):
            cache.set(f"key_{i}", f"value_{i}")
        
        set_time = time.time() - start_time
        ops_per_second = num_operations / set_time
        
        assert ops_per_second > 1000, f"Cache set rate {ops_per_second:.1f} ops/s below 1000"

    def test_cache_get_performance(self):
        """Test cache get performance"""
        from cache_manager import CacheManager
        
        config = {'max_size': 10000, 'ttl_seconds': 3600}
        cache = CacheManager(config)
        
        # Pre-populate cache
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")
        
        # Test cache get performance
        num_operations = 1000
        start_time = time.time()
        
        for i in range(num_operations):
            result = cache.get(f"key_{i}")
            assert result == f"value_{i}"
        
        get_time = time.time() - start_time
        ops_per_second = num_operations / get_time
        
        assert ops_per_second > 5000, f"Cache get rate {ops_per_second:.1f} ops/s below 5000"

    def test_cache_eviction_performance(self):
        """Test cache eviction performance"""
        from cache_manager import CacheManager
        
        config = {'max_size': 100, 'ttl_seconds': 3600}
        cache = CacheManager(config)
        
        # Fill cache beyond capacity to trigger evictions
        start_time = time.time()
        
        for i in range(200):
            cache.set(f"key_{i}", f"value_{i}")
        
        eviction_time = time.time() - start_time
        
        # Should maintain size limit
        assert len(cache.cache) <= 100
        assert eviction_time < 1.0, f"Cache eviction took {eviction_time:.3f}s for 200 operations"

@pytest.mark.performance
class TestLoadTesting:
    """Load testing scenarios"""

    def test_sustained_load(self, test_client, performance_image):
        """Test sustained load over time"""
        duration = 30  # seconds
        target_rps = 10  # requests per second
        results = queue.Queue()
        
        def generate_load():
            start_time = time.time()
            while time.time() - start_time < duration:
                request_start = time.time()
                
                data = {'image': ('load_test.jpg', performance_image, 'image/jpeg')}
                response = test_client.post('/predict', data=data, content_type='multipart/form-data')
                
                request_end = time.time()
                results.put({
                    'status_code': response.status_code,
                    'response_time': request_end - request_start,
                    'timestamp': request_end
                })
                
                # Rate limiting
                time.sleep(1.0 / target_rps)
        
        # Start load generation
        load_thread = threading.Thread(target=generate_load)
        load_thread.start()
        load_thread.join()
        
        # Analyze results
        response_times = []
        success_count = 0
        
        while not results.empty():
            result = results.get()
            response_times.append(result['response_time'])
            if result['status_code'] == 200:
                success_count += 1
        
        total_requests = len(response_times)
        success_rate = success_count / total_requests
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]
        
        # Load testing assertions
        assert success_rate >= 0.95, f"Success rate {success_rate:.2f} below 95% under sustained load"
        assert avg_response_time < 2.0, f"Average response time {avg_response_time:.3f}s exceeds 2.0s under load"
        assert p95_response_time < 5.0, f"95th percentile {p95_response_time:.3f}s exceeds 5.0s under load"

    def test_spike_load(self, test_client, performance_image):
        """Test handling of load spikes"""
        spike_duration = 10  # seconds
        spike_rps = 50  # high requests per second during spike
        results = queue.Queue()
        
        def generate_spike():
            start_time = time.time()
            while time.time() - start_time < spike_duration:
                request_start = time.time()
                
                data = {'image': ('spike_test.jpg', performance_image, 'image/jpeg')}
                response = test_client.post('/predict', data=data, content_type='multipart/form-data')
                
                request_end = time.time()
                results.put({
                    'status_code': response.status_code,
                    'response_time': request_end - request_start
                })
                
                time.sleep(1.0 / spike_rps)
        
        # Generate spike
        spike_thread = threading.Thread(target=generate_spike)
        spike_thread.start()
        spike_thread.join()
        
        # Analyze spike results
        response_times = []
        success_count = 0
        
        while not results.empty():
            result = results.get()
            response_times.append(result['response_time'])
            if result['status_code'] == 200:
                success_count += 1
        
        total_requests = len(response_times)
        success_rate = success_count / total_requests
        max_response_time = max(response_times)
        
        # Spike testing assertions
        assert success_rate >= 0.80, f"Success rate {success_rate:.2f} below 80% during spike"
        assert max_response_time < 10.0, f"Max response time {max_response_time:.3f}s exceeds 10s during spike"

    def test_gradual_ramp_up(self, test_client, performance_image):
        """Test gradual ramp-up of load"""
        max_rps = 20
        ramp_duration = 60  # seconds
        results = queue.Queue()
        
        def gradual_ramp():
            start_time = time.time()
            while time.time() - start_time < ramp_duration:
                elapsed = time.time() - start_time
                current_rps = (elapsed / ramp_duration) * max_rps
                
                request_start = time.time()
                
                data = {'image': ('ramp_test.jpg', performance_image, 'image/jpeg')}
                response = test_client.post('/predict', data=data, content_type='multipart/form-data')
                
                request_end = time.time()
                results.put({
                    'status_code': response.status_code,
                    'response_time': request_end - request_start,
                    'rps': current_rps
                })
                
                if current_rps > 0:
                    time.sleep(1.0 / current_rps)
        
        # Start gradual ramp-up
        ramp_thread = threading.Thread(target=gradual_ramp)
        ramp_thread.start()
        ramp_thread.join()
        
        # Analyze ramp-up results
        response_times = []
        success_count = 0
        
        while not results.empty():
            result = results.get()
            response_times.append(result['response_time'])
            if result['status_code'] == 200:
                success_count += 1
        
        total_requests = len(response_times)
        success_rate = success_count / total_requests
        avg_response_time = statistics.mean(response_times)
        
        # Ramp-up testing assertions
        assert success_rate >= 0.90, f"Success rate {success_rate:.2f} below 90% during ramp-up"
        assert avg_response_time < 3.0, f"Average response time {avg_response_time:.3f}s exceeds 3.0s during ramp-up"

@pytest.mark.performance
@pytest.mark.slow
class TestEnduranceTesting:
    """Endurance testing for long-running stability"""

    def test_long_running_stability(self, test_client, performance_image):
        """Test stability over extended period"""
        test_duration = 300  # 5 minutes
        requests_per_minute = 30
        results = queue.Queue()
        
        def endurance_test():
            start_time = time.time()
            request_count = 0
            
            while time.time() - start_time < test_duration:
                request_start = time.time()
                
                data = {'image': ('endurance_test.jpg', performance_image, 'image/jpeg')}
                response = test_client.post('/predict', data=data, content_type='multipart/form-data')
                
                request_end = time.time()
                results.put({
                    'status_code': response.status_code,
                    'response_time': request_end - request_start,
                    'timestamp': request_end
                })
                
                request_count += 1
                
                # Rate limiting
                if request_count % (requests_per_minute // 60) == 0:
                    time.sleep(1)
        
        # Run endurance test
        endurance_thread = threading.Thread(target=endurance_test)
        endurance_thread.start()
        endurance_thread.join()
        
        # Analyze endurance results
        response_times = []
        timestamps = []
        success_count = 0
        
        while not results.empty():
            result = results.get()
            response_times.append(result['response_time'])
            timestamps.append(result['timestamp'])
            if result['status_code'] == 200:
                success_count += 1
        
        total_requests = len(response_times)
        success_rate = success_count / total_requests
        
        # Check for performance degradation over time
        first_half = response_times[:len(response_times)//2]
        second_half = response_times[len(response_times)//2:]
        
        first_half_avg = statistics.mean(first_half)
        second_half_avg = statistics.mean(second_half)
        
        performance_degradation = (second_half_avg - first_half_avg) / first_half_avg
        
        # Endurance testing assertions
        assert success_rate >= 0.95, f"Success rate {success_rate:.2f} below 95% over extended period"
        assert performance_degradation < 0.5, f"Performance degradation {performance_degradation:.2f} exceeds 50%"
