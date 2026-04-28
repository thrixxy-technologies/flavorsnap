#!/usr/bin/env python3
"""
Test script for comprehensive file validation
"""

import os
import io
import requests
from PIL import Image
import numpy as np
from datetime import datetime

# Test data creation functions
def create_test_image(filename, size=(224, 224), format='JPEG'):
    """Create a test image"""
    img = Image.new('RGB', size, color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format=format)
    img_bytes.seek(0)
    return img_bytes, filename

def create_malicious_file(filename):
    """Create a file with malicious signature"""
    # PE executable signature
    malicious_content = b'\x4D\x5A' + b'A' * 100
    return io.BytesIO(malicious_content), filename

def create_script_in_image(filename):
    """Create an image file with embedded script"""
    img = Image.new('RGB', (100, 100), color='blue')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    
    # Add script content at the end
    script_content = b'<script>alert("xss")</script>'
    malicious_bytes = img_bytes.getvalue() + script_content
    
    return io.BytesIO(malicious_bytes), filename

def test_validation_endpoint(file_obj, filename, api_key=None):
    """Test the validation endpoint"""
    url = "http://localhost:5000/validate-file"
    
    files = {'file': (filename, file_obj, 'application/octet-stream')}
    headers = {}
    
    if api_key:
        headers['X-API-Key'] = api_key
    
    try:
        response = requests.post(url, files=files, headers=headers)
        return response.status_code, response.json()
    except requests.exceptions.ConnectionError:
        return None, {"error": "Connection failed - make sure the API is running"}
    except Exception as e:
        return None, {"error": f"Request failed: {str(e)}"}

def main():
    """Main test function"""
    print("=== File Validation Test Suite ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Test cases
    test_cases = [
        ("Valid JPEG", lambda: create_test_image("test.jpg", format='JPEG')),
        ("Valid PNG", lambda: create_test_image("test.png", format='PNG')),
        ("Valid GIF", lambda: create_test_image("test.gif", format='GIF')),
        ("Oversized image", lambda: create_test_image("huge.jpg", size=(10000, 10000))),
        ("Tiny image", lambda: create_test_image("tiny.jpg", size=(10, 10))),
        ("PE executable", lambda: create_malicious_file("malware.exe")),
        ("Script in image", lambda: create_script_in_image("fake.png")),
        ("Empty file", lambda: (io.BytesIO(b""), "empty.txt")),
        ("Wrong extension", lambda: create_test_image("test.txt", format='JPEG')),
    ]
    
    # Generate a test API key (for development)
    from security_config import APIKeyManager
    test_api_key = APIKeyManager.generate_api_key('free')
    print(f"Using test API key: {test_api_key}")
    print()
    
    results = []
    
    for test_name, file_generator in test_cases:
        print(f"Testing: {test_name}")
        print("-" * 40)
        
        try:
            file_obj, filename = file_generator()
            
            # Test without API key (should fail in production)
            print("1. Testing without API key:")
            status, response = test_validation_endpoint(file_obj, filename)
            print(f"   Status: {status}")
            print(f"   Response: {response}")
            
            # Reset file pointer
            file_obj.seek(0)
            
            # Test with API key
            print("2. Testing with API key:")
            status, response = test_validation_endpoint(file_obj, filename, test_api_key)
            print(f"   Status: {status}")
            print(f"   Response: {response}")
            
            results.append({
                'test': test_name,
                'filename': filename,
                'status_no_key': status,
                'status_with_key': status,
                'response': response
            })
            
        except Exception as e:
            print(f"   Error: {str(e)}")
            results.append({
                'test': test_name,
                'error': str(e)
            })
        
        print()
    
    # Summary
    print("=== Test Summary ===")
    for result in results:
        if 'error' in result:
            print(f"X {result['test']}: ERROR - {result['error']}")
        else:
            print(f"OK {result['test']}: Status {result['status_with_key']}")
    
    print(f"\nTotal tests: {len(results)}")
    print("Test completed!")

if __name__ == "__main__":
    main()
