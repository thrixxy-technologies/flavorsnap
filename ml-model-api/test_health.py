#!/usr/bin/env python3
"""Test script for health check endpoints"""

import app
import urllib.request
import urllib.error
import json
import threading
import time
import sys

def run_app():
    """Run Flask app in background"""
    app.app.run(host='127.0.0.1', port=5001, debug=False)

def test_endpoint(url, name):
    """Test a specific endpoint"""
    try:
        print(f'\nTesting {name}: {url}')
        response = urllib.request.urlopen(url, timeout=10)
        data = json.loads(response.read().decode())
        print(f'Status: {response.getcode()}')
        print(f'Overall status: {data.get("status", "N/A")}')
        
        # Print key information
        if 'checks' in data:
            print(f'Checks: {data["checks"]}')
        if 'endpoints' in data:
            print(f'Available endpoints: {list(data["endpoints"].keys())}')
        if 'database' in data:
            print(f'Database connected: {data["database"].get("connected", "N/A")}')
        if 'redis' in data:
            print(f'Redis status: {data["redis"].get("status", "N/A")}')
        if 'model' in data:
            print(f'Model loaded: {data["model"].get("loaded", "N/A")}')
        if 'system' in data:
            print(f'CPU percent: {data["system"].get("cpu", {}).get("percent", "N/A")}%')
            print(f'Memory percent: {data["system"].get("memory", {}).get("percent", "N/A")}%')
        
        return True
    except Exception as e:
        print(f'Error testing {name}: {e}')
        return False

def main():
    print("Starting Flask app for testing...")
    
    # Start app in background thread
    server_thread = threading.Thread(target=run_app, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(5)
    
    # Test endpoints
    endpoints = [
        ('http://127.0.0.1:5001/health', 'Basic Health Check'),
        ('http://127.0.0.1:5001/health/detailed', 'Detailed Health Check'),
        ('http://127.0.0.1:5001/health/database', 'Database Health Check'),
        ('http://127.0.0.1:5001/health/redis', 'Redis Health Check'),
        ('http://127.0.0.1:5001/health/model', 'Model Health Check'),
        ('http://127.0.0.1:5001/health/system', 'System Health Check'),
        ('http://127.0.0.1:5001/health/dependencies', 'Dependencies Health Check'),
        ('http://127.0.0.1:5001/api/info', 'API Info'),
    ]
    
    results = []
    for url, name in endpoints:
        success = test_endpoint(url, name)
        results.append((name, success))
    
    # Summary
    print('\n' + '='*50)
    print('TEST SUMMARY')
    print('='*50)
    for name, success in results:
        status = 'PASS' if success else 'FAIL'
        print(f'{name}: {status}')
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f'\nTotal: {passed}/{total} endpoints working')
    
    if passed == total:
        print('All health check endpoints are working correctly!')
        return 0
    else:
        print('Some endpoints failed. Check the errors above.')
        return 1

if __name__ == '__main__':
    sys.exit(main())
