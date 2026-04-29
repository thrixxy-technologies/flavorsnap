import requests
import time
import os
import json
from threading import Thread

BASE_URL = "http://127.0.0.1:5000"

# Test API keys for different tiers
FREE_API_KEY = os.environ.get('FREE_API_KEY', 'free_dev-api-key-1234567890123456789012345678')
PREMIUM_API_KEY = os.environ.get('PREMIUM_API_KEY', 'prem_dev-api-key-1234567890123456789012345678')
ENTERPRISE_API_KEY = os.environ.get('ENTERPRISE_API_KEY', 'ent_dev-api-key-1234567890123456789012345678')

def generate_test_api_keys():
    """Generate test API keys for different tiers"""
    print("\n--- Generating Test API Keys ---")
    
    # Generate free tier key
    try:
        response = requests.post(f"{BASE_URL}/admin/api-key/generate", 
                               json={'tier': 'free'})
        if response.status_code == 200:
            free_key = response.json()['api_key']
            print(f"✅ Free tier key generated: {free_key[:20]}...")
        else:
            print(f"❌ Failed to generate free key: {response.status_code}")
    except Exception as e:
        print(f"❌ Error generating free key: {e}")
    
    # Generate premium tier key
    try:
        response = requests.post(f"{BASE_URL}/admin/api-key/generate", 
                               json={'tier': 'premium'})
        if response.status_code == 200:
            premium_key = response.json()['api_key']
            print(f"✅ Premium tier key generated: {premium_key[:20]}...")
        else:
            print(f"❌ Failed to generate premium key: {response.status_code}")
    except Exception as e:
        print(f"❌ Error generating premium key: {e}")
    
    # Generate enterprise tier key
    try:
        response = requests.post(f"{BASE_URL}/admin/api-key/generate", 
                               json={'tier': 'enterprise'})
        if response.status_code == 200:
            enterprise_key = response.json()['api_key']
            print(f"✅ Enterprise tier key generated: {enterprise_key[:20]}...")
        else:
            print(f"❌ Failed to generate enterprise key: {response.status_code}")
    except Exception as e:
        print(f"❌ Error generating enterprise key: {e}")

def test_tiered_rate_limits():
    """Test rate limiting for different API tiers"""
    print("\n--- Testing Tiered Rate Limits ---")
    
    test_cases = [
        ("Free Tier", FREE_API_KEY, 12, 10),  # 12 requests, should hit 10/min limit
        ("Premium Tier", PREMIUM_API_KEY, 105, 100),  # 105 requests, should hit 100/min limit
        ("Enterprise Tier", ENTERPRISE_API_KEY, 505, 500)  # 505 requests, should hit 500/min limit
    ]
    
    for tier_name, api_key, request_count, expected_limit in test_cases:
        print(f"\n--- Testing {tier_name} ({expected_limit} requests/min expected) ---")
        
        success_count = 0
        ratelimited_count = 0
        auth_errors = 0
        
        with open(__file__, 'rb') as f:
            for i in range(request_count):
                try:
                    files = {'image': ('test.jpg', f, 'image/jpeg')}
                    headers = {'X-API-Key': api_key}
                    r = requests.post(f"{BASE_URL}/predict", files=files, headers=headers)
                    
                    if i == 0 or i % 20 == 0 or r.status_code != 200:
                        print(f"  Request #{i+1}: {r.status_code}")
                    
                    if r.status_code == 200:
                        success_count += 1
                    elif r.status_code == 429:
                        ratelimited_count += 1
                        if ratelimited_count == 1:  # Show first rate limit error details
                            error_data = r.json()
                            print(f"    Rate limited: {error_data.get('limit', 'unknown')}")
                            print(f"    Tier: {error_data.get('tier', 'unknown')}")
                    elif r.status_code == 401:
                        auth_errors += 1
                        
                except Exception as e:
                    print(f"  Error: {e}")
        
        print(f"  Results: {success_count} successful, {ratelimited_count} rate limited, {auth_errors} auth errors")
        
        if ratelimited_count > 0:
            print(f"  ✅ {tier_name} rate limiting working")
        else:
            print(f"  ❌ {tier_name} rate limiting failed - expected some requests to be limited")

def test_health_check_exempt():
    print("\n--- Testing Health Check (Exempt/1000 per hour) ---")
    for i in range(12):
        r = requests.get(f"{BASE_URL}/health")
        print(f"Health #{i+1}: {r.status_code}")
        # Health check should not be rate limited for small number of requests
        if r.status_code == 429:
            print("Failed: Health check was rate limited too early!")
            print("Headers:", r.headers)
            break
        
        # Check security headers
        if i == 0:  # Check headers on first request
            security_headers = ['X-Content-Type-Options', 'X-Frame-Options', 'X-XSS-Protection']
            missing_headers = [h for h in security_headers if h not in r.headers]
            if missing_headers:
                print(f"⚠️  Missing security headers: {missing_headers}")
            else:
                print("✅ Security headers present")

def test_api_info_rate_limit():
    print("\n--- Testing API Info Endpoint (30 per minute) ---")
    success_count = 0
    ratelimited_count = 0
    
    for i in range(35):  # Try 35 requests, should hit 30/min limit
        try:
            r = requests.get(f"{BASE_URL}/api/info")
            
            if i == 0 or r.status_code != 200:
                print(f"API Info #{i+1}: {r.status_code}")
            
            if r.status_code == 200:
                success_count += 1
            elif r.status_code == 429:
                ratelimited_count += 1
                error_data = r.json()
                print(f"  Rate limited: {error_data.get('limit', 'unknown')}")
                
        except Exception as e:
            print(f"Error: {e}")
    
    print(f"Results: {success_count} successful, {ratelimited_count} rate limited")
    if ratelimited_count > 0:
        print("✅ API info rate limiting working")
    else:
        print("❌ API info rate limiting failed")

def test_api_key_authentication():
    print("\n--- Testing API Key Authentication ---")
    
    # Test without API key
    print("Testing without API key...")
    with open(__file__, 'rb') as f:
        files = {'image': ('test.jpg', f, 'image/jpeg')}
        r = requests.post(f"{BASE_URL}/predict", files=files)
        print(f"No API Key: {r.status_code} - {r.json().get('error', 'success')}")
        if r.status_code == 401:
            print("✅ API key authentication working")
        else:
            print("❌ API key authentication failed")
    
    # Test with invalid API key
    print("Testing with invalid API key...")
    with open(__file__, 'rb') as f:
        files = {'image': ('test.jpg', f, 'image/jpeg')}
        headers = {'X-API-Key': 'invalid-key-123'}
        r = requests.post(f"{BASE_URL}/predict", files=files, headers=headers)
        print(f"Invalid API Key: {r.status_code} - {r.json().get('error', 'success')}")
        if r.status_code == 401:
            print("✅ Invalid API key rejected")
        else:
            print("❌ Invalid API key accepted")

def test_input_validation():
    print("\n--- Testing Input Validation ---")
    
    # Test no file
    print("Testing no file upload...")
    headers = {'X-API-Key': FREE_API_KEY}
    r = requests.post(f"{BASE_URL}/predict", headers=headers)
    print(f"No file: {r.status_code} - {r.json().get('error', 'success')}")
    if r.status_code == 400 and 'No image provided' in r.json().get('error', ''):
        print("✅ No file validation working")
    else:
        print("❌ No file validation failed")
    
    # Test invalid file type
    print("Testing invalid file type...")
    files = {'image': ('test.txt', b'fake content', 'text/plain')}
    headers = {'X-API-Key': FREE_API_KEY}
    r = requests.post(f"{BASE_URL}/predict", files=files, headers=headers)
    print(f"Invalid file type: {r.status_code} - {r.json().get('error', 'success')}")
    if r.status_code == 400 and ('Unsupported' in r.json().get('error', '') or 'file type' in r.json().get('error', '').lower()):
        print("✅ File type validation working")
    else:
        print("❌ File type validation failed")

def test_security_headers():
    print("\n--- Testing Security Headers ---")
    r = requests.get(f"{BASE_URL}/health")
    
    security_headers = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Content-Security-Policy': None,  # Just check presence
        'Referrer-Policy': None  # Just check presence
    }
    
    missing_headers = []
    for header, expected_value in security_headers.items():
        if header not in r.headers:
            missing_headers.append(header)
        elif expected_value and r.headers[header] != expected_value:
            print(f"⚠️  {header}: expected '{expected_value}', got '{r.headers[header]}'")
    
    if missing_headers:
        print(f"❌ Missing security headers: {missing_headers}")
    else:
        print("✅ All security headers present")

def test_dashboard_rate_limits():
    """Test rate limiting for dashboard endpoint"""
    print("\n--- Testing Dashboard Rate Limits ---")
    
    test_cases = [
        ("Free Dashboard", FREE_API_KEY, 25, 20),  # 25 requests, should hit 20/min limit
        ("Premium Dashboard", PREMIUM_API_KEY, 105, 100),  # 105 requests, should hit 100/min limit
    ]
    
    for tier_name, api_key, request_count, expected_limit in test_cases:
        print(f"\n--- Testing {tier_name} ({expected_limit} requests/min expected) ---")
        
        success_count = 0
        ratelimited_count = 0
        
        for i in range(request_count):
            try:
                headers = {'X-API-Key': api_key}
                r = requests.get(f"{BASE_URL}/dashboard", headers=headers)
                
                if i == 0 or r.status_code != 200:
                    print(f"  Request #{i+1}: {r.status_code}")
                
                if r.status_code == 200:
                    success_count += 1
                elif r.status_code == 429:
                    ratelimited_count += 1
                    error_data = r.json()
                    print(f"  Rate limited: {error_data.get('limit', 'unknown')}")
                elif r.status_code == 503:  # Dashboard not available
                    print(f"  Dashboard not available, skipping test")
                    break
                    
            except Exception as e:
                print(f"  Error: {e}")
        
        print(f"  Results: {success_count} successful, {ratelimited_count} rate limited")
        
        if ratelimited_count > 0:
            print(f"  ✅ {tier_name} dashboard rate limiting working")
        else:
            print(f"  ❌ {tier_name} dashboard rate limiting failed")

if __name__ == "__main__":
    # Wait for the server to spin up
    print("Waiting 2 seconds for server to start...")
    time.sleep(2)
    
    # Generate test API keys first
    generate_test_api_keys()
    
    # Run comprehensive tests
    test_health_check_exempt()
    test_api_info_rate_limit()
    test_tiered_rate_limits()
    test_dashboard_rate_limits()
    test_api_key_authentication()
    test_input_validation()
    test_security_headers()
    
    print("\n" + "="*50)
    print("Comprehensive rate limiting tests completed!")
    print("Check the output above for any ❌ marks indicating issues.")
    print("\nTier-based rate limiting summary:")
    print("- Free tier: 10 requests/min for predict")
    print("- Premium tier: 100 requests/min for predict") 
    print("- Enterprise tier: 500 requests/min for predict")
    print("- Health check: 1000 requests/hour (exempt from tier limits)")
    print("- API info: 30 requests/min (fixed limit)")
    print("- Dashboard: Tier-based limits (20/100/500 per minute)")
