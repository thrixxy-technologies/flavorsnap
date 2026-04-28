import asyncio
import time
import argparse
import sys
from typing import List, Dict, Any
import statistics

try:
    import aiohttp
    import aiofiles
except ImportError:
    print("Warning: aiohttp and aiofiles not found. Please install them for best results:")
    print("pip install aiohttp aiofiles")
    # For now, we will exit if aiohttp is missing as this is a load test script
    sys.exit(1)

async def send_request(session: aiohttp.ClientSession, url: str, image_path: str) -> Dict[str, Any]:
    start_time = time.perf_counter()
    try:
        data = aiohttp.FormData()
        with open(image_path, 'rb') as f:
            data.add_field('image', f, filename='test.jpg', content_type='image/jpeg')
        
        async with session.post(url, data=data) as response:
            status = response.status
            # We don't necessarily need the body, but reading it ensures the request is fully handled
            await response.read()
            end_time = time.perf_counter()
            return {
                "success": 200 <= status < 300,
                "latency": end_time - start_time,
                "status": status
            }
    except Exception as e:
        end_time = time.perf_counter()
        return {
            "success": False,
            "latency": end_time - start_time,
            "error": str(e)
        }

async def run_load_test(url: str, image_path: str, num_requests: int, concurrency: int):
    print(f"Starting load test on {url}")
    print(f"Total requests: {num_requests}, Concurrency: {concurrency}")
    
    start_time = time.perf_counter()
    results = []
    
    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i in range(num_requests):
            tasks.append(send_request(session, url, image_path))
            
            # Simple rate limiting/concurrency control
            if len(tasks) >= concurrency:
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                tasks = []
                print(f"Completed {len(results)}/{num_requests} requests...")
        
        if tasks:
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
    end_time = time.perf_counter()
    total_duration = end_time - start_time
    
    # Process results
    latencies = [r["latency"] for r in results if r["success"]]
    errors = [r for r in results if not r["success"]]
    
    print("\n" + "="*40)
    print("LOAD TEST RESULTS")
    print("="*40)
    print(f"Total time: {total_duration:.2f}s")
    print(f"Requests per second: {len(results) / total_duration:.2f}")
    print(f"Successful requests: {len(latencies)}")
    print(f"Failed requests: {len(errors)}")
    
    if latencies:
        print(f"Min latency: {min(latencies)*1000:.2f}ms")
        print(f"Max latency: {max(latencies)*1000:.2f}ms")
        print(f"Avg latency: {statistics.mean(latencies)*1000:.2f}ms")
        print(f"Median latency: {statistics.median(latencies)*1000:.2f}ms")
        if len(latencies) >= 2:
            print(f"P95 latency: {statistics.quantiles(latencies, n=20)[18]*1000:.2f}ms")
            print(f"P99 latency: {statistics.quantiles(latencies, n=100)[98]*1000:.2f}ms")
    
    if errors:
        print("\nTop errors:")
        error_counts = {}
        for e in errors:
            err_msg = e.get("error") or f"HTTP {e.get('status')}"
            error_counts[err_msg] = error_counts.get(err_msg, 0) + 1
        for msg, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f" - {msg}: {count}")

def main():
    parser = argparse.ArgumentParser(description="FlavorSnap Load Test Script")
    parser.add_argument("--url", default="http://localhost:3000/api/classify", help="URL to test")
    parser.add_argument("--image", default="test-food.jpg", help="Path to test image")
    parser.add_argument("--n", type=int, default=100, help="Number of requests")
    parser.add_argument("--c", type=int, default=10, help="Concurrency level")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_load_test(args.url, args.image, args.n, args.c))
    except KeyboardInterrupt:
        print("\nTest cancelled by user.")

if __name__ == "__main__":
    main()
