#!/usr/bin/env python3
"""
Test script to demonstrate the performance monitoring integration
"""

import requests
import json
import time
import sys

def test_monitoring_endpoints():
    """Test all monitoring endpoints"""
    base_url = "http://localhost:5000"
    
    print("🍲 FlavorSnap Performance Monitoring Integration Test")
    print("=" * 60)
    
    # Test endpoints
    endpoints = [
        ("/health", "Basic Health Check"),
        ("/health/detailed", "Detailed Health Metrics"),
        ("/metrics", "Prometheus Metrics"),
        ("/dashboard", "Performance Dashboard"),
        ("/api/info", "API Information")
    ]
    
    results = {}
    
    for endpoint, description in endpoints:
        try:
            url = base_url + endpoint
            print(f"\n📊 Testing {description}: {url}")
            
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print(f"✅ SUCCESS - Status: {response.status_code}")
                
                if endpoint == "/metrics":
                    # Check for Prometheus metrics format
                    lines = response.text.split('\n')
                    metric_lines = [line for line in lines if line and not line.startswith('#')]
                    print(f"   📈 Found {len(metric_lines)} metrics")
                    
                elif endpoint == "/health":
                    data = response.json()
                    print(f"   🏥 Status: {data.get('status')}")
                    print(f"   📊 Monitoring: {data.get('monitoring', {}).get('enabled', False)}")
                    
                elif endpoint == "/health/detailed":
                    data = response.json()
                    system = data.get('system', {})
                    print(f"   💻 CPU: {system.get('cpu_percent', 'N/A')}%")
                    print(f"   🧠 Memory: {system.get('memory', {}).get('percent', 'N/A')}%")
                    
                elif endpoint == "/api/info":
                    data = response.json()
                    endpoints_list = data.get('endpoints', {})
                    print(f"   🔗 Available endpoints: {len(endpoints_list)}")
                    monitoring = data.get('monitoring', {})
                    print(f"   📊 Prometheus metrics: {monitoring.get('prometheus_metrics', False)}")
                    
                elif endpoint == "/dashboard":
                    content_type = response.headers.get('content-type', '')
                    if 'text/html' in content_type:
                        print(f"   🖥️ HTML Dashboard (Limited Mode)")
                    else:
                        print(f"   📊 Full Dashboard")
                        
                results[endpoint] = True
                
            else:
                print(f"❌ FAILED - Status: {response.status_code}")
                results[endpoint] = False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ FAILED - Connection refused. Is the app running?")
            results[endpoint] = False
        except Exception as e:
            print(f"❌ FAILED - Error: {e}")
            results[endpoint] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    for endpoint, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {endpoint}")
    
    print(f"\n🎯 Results: {success_count}/{total_count} endpoints working")
    
    if success_count == total_count:
        print("🎉 All monitoring endpoints are working correctly!")
        return True
    else:
        print("⚠️  Some endpoints are not available. Check if the app is running.")
        return False

def main():
    """Main test function"""
    print("Starting monitoring integration test...")
    print("Make sure the app is running with: python app.py")
    print()
    
    # Wait a moment for user to read
    time.sleep(2)
    
    success = test_monitoring_endpoints()
    
    if success:
        print("\n🚀 Performance monitoring integration is complete!")
        print("\nNext steps:")
        print("1. Install full dashboard dependencies: pip install -r requirements-monitoring.txt")
        print("2. Set up Prometheus to scrape /metrics endpoint")
        print("3. Configure Grafana dashboards for visualization")
        print("4. Monitor the application in production")
    else:
        print("\n❌ Some issues detected. Check the application logs.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
