#!/usr/bin/env python3
"""
Comprehensive API testing scenarios for FlavorSnap
"""

import requests
import json
import time
import os
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

class FlavorSnapAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
    
    def test_health_check(self) -> Dict[str, Any]:
        """Test basic health check endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return {
                "test": "health_check",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "success": response.status_code == 200,
                "data": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            return {
                "test": "health_check",
                "success": False,
                "error": str(e)
            }
    
    def test_detailed_health_check(self) -> Dict[str, Any]:
        """Test detailed health check endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health/detailed")
            return {
                "test": "detailed_health_check",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "success": response.status_code == 200,
                "data": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            return {
                "test": "detailed_health_check",
                "success": False,
                "error": str(e)
            }
    
    def test_classification_with_image(self, image_path: str) -> Dict[str, Any]:
        """Test classification with a valid image"""
        if not os.path.exists(image_path):
            return {
                "test": "classification_with_image",
                "success": False,
                "error": f"Test image not found: {image_path}"
            }
        
        try:
            with open(image_path, 'rb') as f:
                files = {'image': f}
                response = self.session.post(f"{self.base_url}/predict", files=files)
            
            success = response.status_code == 200
            data = response.json() if success else None
            
            # Validate response structure
            if success and data:
                required_fields = ['id', 'label', 'confidence', 'all_predictions', 'processing_time', 'created_at', 'request_id']
                missing_fields = [field for field in required_fields if field not in data]
                
                return {
                    "test": "classification_with_image",
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "success": success and len(missing_fields) == 0,
                    "data": data,
                    "missing_fields": missing_fields,
                    "confidence_valid": 0 <= data.get('confidence', -1) <= 1,
                    "processing_time_reasonable": data.get('processing_time', float('inf')) < 5.0
                }
            else:
                return {
                    "test": "classification_with_image",
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "success": False,
                    "error": response.text
                }
                
        except Exception as e:
            return {
                "test": "classification_with_image",
                "success": False,
                "error": str(e)
            }
    
    def test_classification_without_image(self) -> Dict[str, Any]:
        """Test classification without providing an image"""
        try:
            response = self.session.post(f"{self.base_url}/predict", files={})
            success = response.status_code == 400
            data = response.json() if response.status_code == 400 else None
            
            return {
                "test": "classification_without_image",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "success": success and data and 'error' in data,
                "data": data
            }
        except Exception as e:
            return {
                "test": "classification_without_image",
                "success": False,
                "error": str(e)
            }
    
    def test_rate_limiting(self, requests_count: int = 15) -> Dict[str, Any]:
        """Test rate limiting by sending multiple requests quickly"""
        results = []
        
        def make_request():
            try:
                response = self.session.post(f"{self.base_url}/predict", files={})
                return {
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
            except Exception as e:
                return {
                    "status_code": 0,
                    "error": str(e)
                }
        
        # Send requests concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(requests_count)]
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze results
        rate_limited_requests = sum(1 for r in results if r.get('status_code') == 429)
        bad_requests = sum(1 for r in results if r.get('status_code') == 400)
        successful_requests = sum(1 for r in results if r.get('status_code') == 200)
        
        return {
            "test": "rate_limiting",
            "total_requests": requests_count,
            "successful_requests": successful_requests,
            "rate_limited_requests": rate_limited_requests,
            "bad_requests": bad_requests,
            "rate_limiting_working": rate_limited_requests > 0,
            "results": results
        }
    
    def test_load_performance(self, concurrent_users: int = 10, requests_per_user: int = 5) -> Dict[str, Any]:
        """Test load performance with concurrent users"""
        results = []
        
        def user_simulation(user_id: int):
            user_results = []
            for i in range(requests_per_user):
                start_time = time.time()
                try:
                    # Simulate a basic request (this would normally include an image)
                    response = self.session.post(f"{self.base_url}/predict", files={})
                    end_time = time.time()
                    user_results.append({
                        "user_id": user_id,
                        "request_id": i,
                        "status_code": response.status_code,
                        "response_time": end_time - start_time,
                        "success": response.status_code in [200, 400, 429]  # Accept expected responses
                    })
                except Exception as e:
                    end_time = time.time()
                    user_results.append({
                        "user_id": user_id,
                        "request_id": i,
                        "error": str(e),
                        "response_time": end_time - start_time,
                        "success": False
                    })
                
                # Small delay between requests
                time.sleep(0.1)
            
            return user_results
        
        # Run concurrent users
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(user_simulation, i) for i in range(concurrent_users)]
            for future in as_completed(futures):
                results.extend(future.result())
        
        # Calculate performance metrics
        successful_requests = [r for r in results if r.get('success', False)]
        response_times = [r['response_time'] for r in successful_requests]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
        else:
            avg_response_time = median_response_time = p95_response_time = 0
        
        return {
            "test": "load_performance",
            "concurrent_users": concurrent_users,
            "requests_per_user": requests_per_user,
            "total_requests": len(results),
            "successful_requests": len(successful_requests),
            "success_rate": len(successful_requests) / len(results) * 100 if results else 0,
            "avg_response_time": avg_response_time,
            "median_response_time": median_response_time,
            "p95_response_time": p95_response_time,
            "results": results
        }
    
    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all test scenarios"""
        print("🧪 Running FlavorSnap API Comprehensive Tests...")
        
        test_results = []
        
        # Basic functionality tests
        print("\n📋 Running basic functionality tests...")
        test_results.append(self.test_health_check())
        test_results.append(self.test_detailed_health_check())
        test_results.append(self.test_classification_without_image())
        
        # Classification test (if test image exists)
        test_image_path = "../test-food.jpg"
        if os.path.exists(test_image_path):
            test_results.append(self.test_classification_with_image(test_image_path))
        else:
            print(f"⚠️  Test image not found at {test_image_path}, skipping classification test")
        
        # Rate limiting test
        print("\n⏱️  Testing rate limiting...")
        test_results.append(self.test_rate_limiting())
        
        # Load performance test
        print("\n🚀 Running load performance test...")
        test_results.append(self.test_load_performance())
        
        # Generate summary
        successful_tests = sum(1 for result in test_results if result.get('success', False))
        total_tests = len(test_results)
        
        summary = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests / total_tests * 100 if total_tests > 0 else 0,
            "test_results": test_results,
            "timestamp": time.time()
        }
        
        print(f"\n📊 Test Summary: {successful_tests}/{total_tests} tests passed ({summary['success_rate']:.1f}%)")
        
        return summary
    
    def generate_report(self, results: Dict[str, Any], output_file: str = "test_report.json"):
        """Generate a detailed test report"""
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"📄 Detailed report saved to {output_file}")

if __name__ == "__main__":
    # Run tests
    tester = FlavorSnapAPITester()
    results = tester.run_comprehensive_tests()
    tester.generate_report(results)
    
    # Print summary
    print("\n" + "="*50)
    print("FLAVORSNAP API TEST SUMMARY")
    print("="*50)
    
    for result in results['test_results']:
        test_name = result['test'].replace('_', ' ').title()
        status = "✅ PASS" if result.get('success', False) else "❌ FAIL"
        print(f"{status} {test_name}")
        
        if not result.get('success', False) and 'error' in result:
            print(f"    Error: {result['error']}")
    
    print(f"\nOverall Success Rate: {results['success_rate']:.1f}%")
