"""
Load testing with Locust for FlavorSnap ML API
"""

from locust import HttpUser, task, between
import io
from PIL import Image
import random
import json

class FlavorSnapUser(HttpUser):
    """Simulated user for load testing FlavorSnap ML API"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a user starts"""
        # Create a test image for the user
        self.test_image = self.create_test_image()
        
    def create_test_image(self):
        """Create a test image for upload"""
        img = Image.new('RGB', (224, 224), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes.getvalue()
    
    @task(3)
    def predict_image(self):
        """Main task: Predict image classification"""
        files = {
            'image': ('test_image.jpg', self.test_image, 'image/jpeg')
        }
        
        # Randomly choose between direct processing and queue processing
        use_queue = random.choice([True, False])
        
        if use_queue:
            data = {
                'use_queue': 'true',
                'priority': random.choice(['low', 'normal', 'high', 'critical'])
            }
        else:
            data = {}
        
        with self.client.post(
            '/predict',
            files=files,
            data=data,
            catch_response=True
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(2)
    def check_health(self):
        """Check application health"""
        self.client.get('/health')
    
    @task(1)
    def get_queue_status(self):
        """Get queue status"""
        with self.client.get('/queue/status', catch_response=True) as response:
            if response.status_code in [200, 503]:  # 503 if not initialized
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(1)
    def get_config(self):
        """Get configuration info"""
        self.client.get('/config')
    
    @task(0.5)
    def get_monitoring_data(self):
        """Get monitoring data"""
        with self.client.get('/queue/monitoring', catch_response=True) as response:
            if response.status_code in [200, 503]:  # 503 if not initialized
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

class HighVolumeUser(FlavorSnapUser):
    """High volume user for stress testing"""
    
    wait_time = between(0.1, 0.5)  # Very short wait time
    
    @task(5)
    def predict_image_high_volume(self):
        """High volume image predictions"""
        files = {
            'image': ('test_image.jpg', self.test_image, 'image/jpeg')
        }
        
        data = {
            'use_queue': 'true',
            'priority': 'high'  # Use high priority for stress testing
        }
        
        with self.client.post(
            '/predict',
            files=files,
            data=data,
            catch_response=True
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

class QueueUser(HttpUser):
    """User focused on queue operations"""
    
    wait_time = between(2, 4)
    
    def on_start(self):
        """Initialize queue user"""
        self.test_image = self.create_test_image()
        self.task_ids = []
    
    def create_test_image(self):
        """Create a test image"""
        img = Image.new('RGB', (224, 224), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes.getvalue()
    
    @task(3)
    def submit_queued_task(self):
        """Submit task to queue"""
        files = {
            'image': ('queue_test.jpg', self.test_image, 'image/jpeg')
        }
        
        data = {
            'use_queue': 'true',
            'priority': random.choice(['low', 'normal', 'high', 'critical'])
        }
        
        with self.client.post(
            '/predict',
            files=files,
            data=data,
            catch_response=True
        ) as response:
            if response.status_code == 202:
                response.success()
                # Store task ID for checking status
                try:
                    result = response.json()
                    if 'task_id' in result:
                        self.task_ids.append(result['task_id'])
                        # Keep only recent task IDs
                        if len(self.task_ids) > 10:
                            self.task_ids.pop(0)
                except:
                    pass
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(2)
    def check_task_status(self):
        """Check status of submitted tasks"""
        if self.task_ids:
            task_id = random.choice(self.task_ids)
            with self.client.get(
                f'/queue/task/{task_id}',
                catch_response=True
            ) as response:
                if response.status_code in [200, 404]:  # 404 if task not found
                    response.success()
                else:
                    response.failure(f"Got status code {response.status_code}")
    
    @task(1)
    def get_queue_analytics(self):
        """Get queue analytics"""
        with self.client.get('/queue/analytics', catch_response=True) as response:
            if response.status_code in [200, 503]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

class CacheUser(HttpUser):
    """User focused on cache performance testing"""
    
    wait_time = between(0.5, 1.5)
    
    def on_start(self):
        """Initialize cache user"""
        self.test_images = []
        # Create multiple test images to test cache variety
        for i in range(5):
            img = Image.new('RGB', (224, 224), color=(random.randint(0,255), random.randint(0,255), random.randint(0,255)))
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            img_bytes.seek(0)
            self.test_images.append(img_bytes.getvalue())
    
    @task(4)
    def predict_with_cache(self):
        """Test prediction with caching"""
        # Use existing images to test cache hits
        image_data = random.choice(self.test_images)
        files = {
            'image': ('cached_test.jpg', image_data, 'image/jpeg')
        }
        
        with self.client.post(
            '/predict',
            files=files,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(1)
    def get_monitoring_for_cache_stats(self):
        """Get monitoring data to check cache statistics"""
        with self.client.get('/queue/monitoring', catch_response=True) as response:
            if response.status_code in [200, 503]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

# Locust configuration for different test scenarios
class LoadTestConfig:
    """Configuration for different load test scenarios"""
    
    # Light load test
    LIGHT_LOAD = {
        'user_classes': [FlavorSnapUser],
        'users': 10,
        'spawn_rate': 2,
        'run_time': '5m'
    }
    
    # Medium load test
    MEDIUM_LOAD = {
        'user_classes': [FlavorSnapUser, QueueUser],
        'users': 50,
        'spawn_rate': 5,
        'run_time': '10m'
    }
    
    # Heavy load test
    HEAVY_LOAD = {
        'user_classes': [FlavorSnapUser, HighVolumeUser, QueueUser, CacheUser],
        'users': 200,
        'spawn_rate': 20,
        'run_time': '15m'
    }
    
    # Stress test
    STRESS_TEST = {
        'user_classes': [HighVolumeUser],
        'users': 500,
        'spawn_rate': 50,
        'run_time': '5m'
    }
    
    # Spike test
    SPIKE_TEST = {
        'user_classes': [FlavorSnapUser, HighVolumeUser],
        'users': 1000,
        'spawn_rate': 100,
        'run_time': '2m'
    }
    
    # Soak test (long duration)
    SOAK_TEST = {
        'user_classes': [FlavorSnapUser, QueueUser, CacheUser],
        'users': 100,
        'spawn_rate': 10,
        'run_time': '1h'
    }

# Custom events and monitoring
from locust import events
import time

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Custom request event listener"""
    if exception:
        print(f"Request failed: {request_type} {name} - Exception: {exception}")
    elif response_time > 5000:  # Log slow requests
        print(f"Slow request: {request_type} {name} - Response time: {response_time}ms")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Test start event"""
    print("Load test started")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Test stop event"""
    print("Load test completed")

# Performance thresholds and reporting
class PerformanceThresholds:
    """Performance thresholds for load testing"""
    
    RESPONSE_TIME_P95 = 2000  # 95th percentile should be under 2 seconds
    RESPONSE_TIME_P99 = 5000  # 99th percentile should be under 5 seconds
    SUCCESS_RATE = 95.0      # Success rate should be above 95%
    THROUGHPUT_MIN = 100     # Minimum requests per second
    
    @classmethod
    def check_performance(cls, stats):
        """Check if performance meets thresholds"""
        issues = []
        
        # Check response times
        if stats.get('response_time_percentile_95', 0) > cls.RESPONSE_TIME_P95:
            issues.append(f"95th percentile response time ({stats.get('response_time_percentile_95')}ms) exceeds threshold ({cls.RESPONSE_TIME_P95}ms)")
        
        if stats.get('response_time_percentile_99', 0) > cls.RESPONSE_TIME_P99:
            issues.append(f"99th percentile response time ({stats.get('response_time_percentile_99')}ms) exceeds threshold ({cls.RESPONSE_TIME_P99}ms)")
        
        # Check success rate
        success_rate = stats.get('success_rate', 0)
        if success_rate < cls.SUCCESS_RATE:
            issues.append(f"Success rate ({success_rate}%) below threshold ({cls.SUCCESS_RATE}%)")
        
        # Check throughput
        if stats.get('total_rps', 0) < cls.THROUGHPUT_MIN:
            issues.append(f"Throughput ({stats.get('total_rps')} RPS) below minimum ({cls.THROUGHPUT_MIN} RPS)")
        
        return issues

# Command line usage examples:
"""
# Light load test
locust -f test_load.py FlavorSnapUser --users 10 --spawn-rate 2 --run-time 5m --host http://localhost:5000

# Medium load test with multiple user types
locust -f test_load.py --users 50 --spawn-rate 5 --run-time 10m --host http://localhost:5000

# Stress test
locust -f test_load.py HighVolumeUser --users 500 --spawn-rate 50 --run-time 5m --host http://localhost:5000

# Web UI mode
locust -f test_load.py --host http://localhost:5000

# Headless mode with specific configuration
locust -f test_load.py --headless --users 100 --spawn-rate 10 --run-time 15m --host http://localhost:5000 --html reports/load_test_report.html
"""
