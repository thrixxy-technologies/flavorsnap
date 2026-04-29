"""
Comprehensive security test suite for FlavorSnap API
"""
import pytest
import requests
import time
import os
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
import json

BASE_URL = "http://127.0.0.1:5000"
API_KEY = os.environ.get('TEST_API_KEY', 'test-api-key-for-development')

class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_health_check_rate_limit(self):
        """Test that health check has appropriate rate limiting"""
        responses = []
        for i in range(5):
            r = requests.get(f"{BASE_URL}/health")
            responses.append(r.status_code)
            time.sleep(0.1)
        
        # Health check should not be rate limited for small number of requests
        assert all(status == 200 for status in responses)
    
    def test_predict_rate_limit(self):
        """Test rate limiting on predict endpoint"""
        success_count = 0
        rate_limited_count = 0
        
        with open(__file__, 'rb') as f:
            for i in range(105):  # Exceed the 100 per minute limit
                try:
                    files = {'image': ('test.jpg', f, 'image/jpeg')}
                    headers = {'X-API-Key': API_KEY}
                    r = requests.post(f"{BASE_URL}/predict", files=files, headers=headers)
                    
                    if r.status_code == 200:
                        success_count += 1
                    elif r.status_code == 429:
                        rate_limited_count += 1
                    else:
                        # 400 is expected for invalid image, but not rate limited
                        if r.status_code != 400:
                            print(f"Unexpected status: {r.status_code}")
                    
                    # Check rate limit headers
                    if 'X-RateLimit-Limit' in r.headers:
                        print(f"Request {i+1}: Limit={r.headers['X-RateLimit-Limit']}, Remaining={r.headers.get('X-RateLimit-Remaining', 'N/A')}")
                
                except Exception as e:
                    print(f"Request {i+1} failed: {e}")
        
        print(f"Results: {success_count} successful, {rate_limited_count} rate limited")
        assert rate_limited_count > 0, "Expected some requests to be rate limited"
    
    def test_concurrent_requests(self):
        """Test rate limiting under concurrent load"""
        def make_request():
            try:
                r = requests.get(f"{BASE_URL}/health")
                return r.status_code
            except:
                return None
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            responses = [f.result() for f in futures]
        
        # Most requests should succeed
        success_count = sum(1 for r in responses if r == 200)
        assert success_count > 90, f"Too many failed requests: {success_count}/100"

class TestAPIKeyAuthentication:
    """Test API key authentication"""
    
    def test_missing_api_key(self):
        """Test request without API key"""
        with open(__file__, 'rb') as f:
            files = {'image': ('test.jpg', f, 'image/jpeg')}
            r = requests.post(f"{BASE_URL}/predict", files=files)
        
        assert r.status_code == 401
        assert 'API key required' in r.json()['error']
    
    def test_invalid_api_key(self):
        """Test request with invalid API key"""
        with open(__file__, 'rb') as f:
            files = {'image': ('test.jpg', f, 'image/jpeg')}
            headers = {'X-API-Key': 'invalid-key-123'}
            r = requests.post(f"{BASE_URL}/predict", files=files, headers=headers)
        
        assert r.status_code == 401
        assert 'Invalid API key' in r.json()['error']
    
    def test_valid_api_key(self):
        """Test request with valid API key"""
        with open(__file__, 'rb') as f:
            files = {'image': ('test.jpg', f, 'image/jpeg')}
            headers = {'X-API-Key': API_KEY}
            r = requests.post(f"{BASE_URL}/predict", files=files, headers=headers)
        
        # Should not be 401 (may be 400 for invalid image, but not auth error)
        assert r.status_code != 401

class TestInputValidation:
    """Test input validation and sanitization"""
    
    def test_no_file_upload(self):
        """Test request without file"""
        headers = {'X-API-Key': API_KEY}
        r = requests.post(f"{BASE_URL}/predict", headers=headers)
        
        assert r.status_code == 400
        assert 'No image provided' in r.json()['error']
    
    def test_empty_filename(self):
        """Test upload with empty filename"""
        files = {'image': ('', b'', 'image/jpeg')}
        headers = {'X-API-Key': API_KEY}
        r = requests.post(f"{BASE_URL}/predict", files=files, headers=headers)
        
        assert r.status_code == 400
        assert 'No file selected' in r.json()['error']
    
    def test_invalid_file_extension(self):
        """Test upload with invalid file extension"""
        files = {'image': ('test.txt', b'fake content', 'text/plain')}
        headers = {'X-API-Key': API_KEY}
        r = requests.post(f"{BASE_URL}/predict", files=files, headers=headers)
        
        assert r.status_code == 400
        assert 'Unsupported file type' in r.json()['error']
    
    def test_malicious_filename(self):
        """Test upload with malicious filename"""
        malicious_names = [
            '../../../etc/passwd',
            '<script>alert("xss")</script>.jpg',
            'CON.jpg',  # Windows reserved name
            'file with spaces.jpg'
        ]
        
        for filename in malicious_names:
            files = {'image': (filename, b'fake content', 'image/jpeg')}
            headers = {'X-API-Key': API_KEY}
            r = requests.post(f"{BASE_URL}/predict", files=files, headers=headers)
            
            # Should be rejected for filename issues or processed safely
            assert r.status_code in [400, 422]

class TestSecurityHeaders:
    """Test security headers"""
    
    def test_security_headers_present(self):
        """Test that security headers are present"""
        r = requests.get(f"{BASE_URL}/health")
        
        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Content-Security-Policy',
            'Referrer-Policy'
        ]
        
        for header in security_headers:
            assert header in r.headers, f"Missing security header: {header}"
    
    def test_cors_headers(self):
        """Test CORS configuration"""
        r = requests.options(f"{BASE_URL}/predict")
        
        # Should have CORS headers
        assert 'Access-Control-Allow-Origin' in r.headers
        assert 'Access-Control-Allow-Methods' in r.headers
        assert 'Access-Control-Allow-Headers' in r.headers

class TestErrorHandling:
    """Test error handling"""
    
    def test_404_error(self):
        """Test 404 error handling"""
        r = requests.get(f"{BASE_URL}/nonexistent")
        
        assert r.status_code == 404
        assert 'error' in r.json()
    
    def test_large_file_upload(self):
        """Test large file upload handling"""
        # Create a large fake file (20MB)
        large_content = b'x' * (20 * 1024 * 1024)
        
        files = {'image': ('large.jpg', large_content, 'image/jpeg')}
        headers = {'X-API-Key': API_KEY}
        
        try:
            r = requests.post(f"{BASE_URL}/predict", files=files, headers=headers)
            assert r.status_code == 413
            assert 'Request too large' in r.json()['error']
        except requests.exceptions.RequestException:
            # Request might be rejected by server before reaching Flask
            pass

class TestAPIEndpoints:
    """Test API endpoints functionality"""
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        r = requests.get(f"{BASE_URL}/health")
        
        assert r.status_code == 200
        data = r.json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'version' in data
        assert 'security' in data
    
    def test_api_info_endpoint(self):
        """Test API info endpoint"""
        r = requests.get(f"{BASE_URL}/api/info")
        
        assert r.status_code == 200
        data = r.json()
        assert 'name' in data
        assert 'version' in data
        assert 'endpoints' in data
        assert 'security' in data
        
        # Check security info
        security = data['security']
        assert 'rate_limiting' in security
        assert 'api_key_auth' in security
        assert 'cors_enabled' in security
        assert 'security_headers' in security
    
    def test_api_key_generation(self):
        """Test API key generation endpoint"""
        r = requests.post(f"{BASE_URL}/admin/api-key/generate")
        
        assert r.status_code == 200
        data = r.json()
        assert 'api_key' in data
        assert 'message' in data
        
        # API key should be long enough
        assert len(data['api_key']) >= 32

def run_security_tests():
    """Run all security tests"""
    print("Starting FlavorSnap API Security Tests")
    print("=" * 50)
    
    test_classes = [
        TestRateLimiting,
        TestAPIKeyAuthentication,
        TestInputValidation,
        TestSecurityHeaders,
        TestErrorHandling,
        TestAPIEndpoints
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\nRunning {test_class.__name__}")
        print("-" * 30)
        
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                test_instance = test_class()
                method = getattr(test_instance, method_name)
                method()
                print(f"✅ {method_name}")
                passed_tests += 1
            except Exception as e:
                print(f"❌ {method_name}: {str(e)}")
    
    print(f"\n" + "=" * 50)
    print(f"Test Results: {passed_tests}/{total_tests} passed")
    
    if passed_tests == total_tests:
        print("🎉 All security tests passed!")
    else:
        print(f"⚠️  {total_tests - passed_tests} tests failed")

if __name__ == "__main__":
    run_security_tests()
