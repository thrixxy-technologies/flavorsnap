import pytest
import requests
import time
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor

@pytest.fixture
def api_url():
    # Default to localhost for testing, can be overridden via environment variable
    import os
    return os.getenv("FLAVORSNAP_URL", "http://localhost:3000/api/classify")

@pytest.fixture
def sample_image_path(tmp_path):
    # Create a small dummy image for testing
    from PIL import Image
    import io
    
    path = tmp_path / "test_load.jpg"
    img = Image.new('RGB', (224, 224), color = (73, 109, 137))
    img.save(path)
    return path

@pytest.mark.performance_api
def test_api_latency_baseline(api_url, sample_image_path):
    """Measure baseline latency of a single API request."""
    latencies = []
    
    # Warmup
    try:
        with open(sample_image_path, 'rb') as f:
            requests.post(api_url, files={'image': f}, timeout=10)
    except requests.exceptions.ConnectionError:
        pytest.skip("API server not reachable at " + api_url)

    for _ in range(5):
        start = time.perf_counter()
        with open(sample_image_path, 'rb') as f:
            resp = requests.post(api_url, files={'image': f}, timeout=10)
        end = time.perf_counter()
        
        assert resp.status_code == 200
        latencies.append(end - start)
    
    avg_latency = statistics.mean(latencies)
    print(f"\nAverage API Latency: {avg_latency*1000:.2f}ms")
    
    # Assert acceptable latency (adjust threshold as needed)
    # 5 seconds is very generous but reasonable for a cold start/ML model
    assert avg_latency < 5.0

@pytest.mark.performance_load
def test_api_concurrency(api_url, sample_image_path):
    """Measure API performance under moderate load (10 concurrent requests)."""
    concurrency = 10
    total_requests = 30
    
    results = []
    
    def single_req():
        try:
            with open(sample_image_path, 'rb') as f:
                start = time.perf_counter()
                resp = requests.post(api_url, files={'image': f}, timeout=10)
                end = time.perf_counter()
                return {
                    "success": resp.status_code == 200,
                    "latency": end - start
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Check connectivity first
    try:
        with open(sample_image_path, 'rb') as f:
            requests.post(api_url, files={'image': f}, timeout=5)
    except Exception:
        pytest.skip("API server not reachable at " + api_url)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(single_req) for _ in range(total_requests)]
        results = [f.result() for f in futures]
    
    successes = [r for r in results if r.get("success")]
    latencies = [r["latency"] for r in successes]
    
    failure_rate = (total_requests - len(successes)) / total_requests
    
    print(f"\nLoad Test Result ({concurrency} concurrent, {total_requests} total):")
    print(f"Successes: {len(successes)}/{total_requests}")
    print(f"Failure Rate: {failure_rate*100:.1f}%")
    
    if latencies:
        print(f"Avg Latency: {statistics.mean(latencies)*1000:.2f}ms")
        print(f"P95 Latency: {statistics.quantiles(latencies, n=20)[18]*1000:.2f}ms")

    assert failure_rate < 0.1  # Allow up to 10% failure under load (simulated errors)
    if latencies:
        assert statistics.mean(latencies) < 10.0  # Reasonable average latency under load
