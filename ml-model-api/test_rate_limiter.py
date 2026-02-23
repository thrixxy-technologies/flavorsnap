import requests
import time
from threading import Thread

BASE_URL = "http://127.0.0.1:5000"

def test_health_check_exempt():
    print("\\n--- Testing Health Check (Exempt/60 per min) ---")
    for i in range(12):
        r = requests.get(f"{BASE_URL}/health")
        print(f"Health #{i+1}: {r.status_code}")
        # Assuming health is exempt or has 60/min limit, we shouldn't hit 429 easily
        if r.status_code == 429:
            print("Failed: Health check was rate limited too early!")
            print("Headers:", r.headers)
            break

def test_predict_rate_limit():
    print("\\n--- Testing Predict Endpoint (10 per min limit) ---")
    # We will send 12 requests. The 11th and 12th should be 429
    success_count = 0
    ratelimited_count = 0
    with open(__file__, 'rb') as f:
        for i in range(12):
            try:
                # We do a mock file upload just to pass the first layer of validation
                files = {'image': ('test.jpg', f, 'image/jpeg')}
                r = requests.post(f"{BASE_URL}/predict", files=files)
                print(f"Predict #{i+1}: {r.status_code} - {r.json().get('error', 'success')}")
                
                # Check for rate limit headers
                if 'X-RateLimit-Limit' in r.headers:
                    limit_header = r.headers['X-RateLimit-Limit']
                    remaining_header = r.headers.get('X-RateLimit-Remaining', 'N/A')
                    print(f"   Limits: {limit_header}, Remaining: {remaining_header}")
                
                if r.status_code == 200 or r.status_code == 400:
                    success_count += 1
                elif r.status_code == 429:
                    ratelimited_count += 1
                    
            except Exception as e:
                print(f"Error: {e}")
                
    print(f"\\nResults: {success_count} non-429s, {ratelimited_count} ratelimited (429s)")
    if ratelimited_count > 0:
        print("✅ Rate limiting logic is working as expected.")
    else:
        print("❌ Rate limiting failed. Expected some requests to be limited.")

if __name__ == "__main__":
    # Wait for the server to spin up
    print("Waiting 2 seconds for server to start...")
    time.sleep(2)
    test_health_check_exempt()
    test_predict_rate_limit()
