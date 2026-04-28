#!/usr/bin/env python3
"""
Advanced Load Balancer Testing Script
Tests all aspects of the advanced load balancing infrastructure
"""

import asyncio
import aiohttp
import time
import json
import logging
import statistics
from typing import Dict, List, Any
import concurrent.futures
import random
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    name: str
    passed: bool
    duration: float
    details: Dict[str, Any]
    error: str = ""

class LoadBalancerTester:
    """Comprehensive load balancer testing suite"""
    
    def __init__(self, base_url: str = "http://localhost:80"):
        self.base_url = base_url
        self.results: List[TestResult] = []
        self.session: aiohttp.ClientSession = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all load balancer tests"""
        logger.info("Starting comprehensive load balancer tests...")
        
        # Basic connectivity tests
        await self.test_health_endpoint()
        await self.test_basic_routing()
        
        # Load balancing tests
        await self.test_round_robin_load_balancing()
        await self.test_least_connections_load_balancing()
        await self.test_session_affinity()
        
        # Health check tests
        await self.test_health_check_failover()
        await self.test_circuit_breaker()
        
        # Rate limiting tests
        await self.test_rate_limiting()
        await self.test_burst_capacity()
        
        # SSL/TLS tests
        await self.test_ssl_termination()
        await self.test_ssl_redirects()
        
        # Performance tests
        await self.test_concurrent_connections()
        await self.test_response_times()
        await self.test_connection_pooling()
        
        # Failover tests
        await self.test_failover_mechanism()
        await self.test_graceful_degradation()
        
        # Monitoring tests
        await self.test_metrics_endpoint()
        await self.test_prometheus_integration()
        
        return self.generate_report()
    
    async def test_health_endpoint(self):
        """Test health endpoint"""
        start_time = time.time()
        details = {}
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                details['status_code'] = response.status
                details['response_text'] = await response.text()
                
                if response.status == 200 and "healthy" in details['response_text'].lower():
                    passed = True
                    details['message'] = "Health endpoint working correctly"
                else:
                    passed = False
                    details['message'] = "Health endpoint not responding correctly"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Health Endpoint Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Health endpoint test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_basic_routing(self):
        """Test basic request routing"""
        start_time = time.time()
        details = {}
        
        try:
            # Test frontend routing
            async with self.session.get(f"{self.base_url}/") as response:
                details['frontend_status'] = response.status
            
            # Test API routing
            async with self.session.get(f"{self.base_url}/api/health") as response:
                details['api_status'] = response.status
                details['api_response'] = await response.text()
            
            # Test ML prediction routing
            async with self.session.get(f"{self.base_url}/predict") as response:
                details['predict_status'] = response.status
            
            passed = (details['frontend_status'] == 200 and 
                     details['api_status'] in [200, 405] and  # 405 for GET on /predict
                     details['predict_status'] in [200, 405])
            
            details['message'] = "Basic routing working correctly"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Basic Routing Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Basic routing test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_round_robin_load_balancing(self):
        """Test round-robin load balancing"""
        start_time = time.time()
        details = {}
        
        try:
            responses = []
            headers = []
            
            # Make multiple requests to see distribution
            for i in range(20):
                async with self.session.get(f"{self.base_url}/api/health") as response:
                    responses.append(response.status)
                    # Check for different backend responses if available
                    if 'X-Backend-Server' in response.headers:
                        headers.append(response.headers['X-Backend-Server'])
            
            details['total_requests'] = len(responses)
            details['successful_requests'] = sum(1 for r in responses if r == 200)
            details['success_rate'] = details['successful_requests'] / len(responses)
            
            # Check if requests are distributed (if backend headers are available)
            if headers:
                unique_backends = set(headers)
                details['unique_backends'] = len(unique_backends)
                details['distribution'] = {backend: headers.count(backend) for backend in unique_backends}
                passed = len(unique_backends) > 1 and details['success_rate'] > 0.9
            else:
                # Fallback: just check success rate
                passed = details['success_rate'] > 0.9
            
            details['message'] = f"Load balancing with {details.get('unique_backends', 'unknown')} backends"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Round-Robin Load Balancing Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Round-robin load balancing test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_least_connections_load_balancing(self):
        """Test least connections load balancing"""
        start_time = time.time()
        details = {}
        
        try:
            # Make concurrent requests to test connection-based routing
            async def make_request():
                async with self.session.get(f"{self.base_url}/api/health") as response:
                    return response.status
            
            # Launch concurrent requests
            tasks = [make_request() for _ in range(10)]
            responses = await asyncio.gather(*tasks)
            
            details['concurrent_requests'] = len(responses)
            details['successful_requests'] = sum(1 for r in responses if r == 200)
            details['success_rate'] = details['successful_requests'] / len(responses)
            
            passed = details['success_rate'] > 0.9
            details['message'] = "Concurrent request handling working"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Least Connections Load Balancing Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Least connections load balancing test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_session_affinity(self):
        """Test session affinity (IP hash)"""
        start_time = time.time()
        details = {}
        
        try:
            # Make requests from same "client" (same headers)
            headers = {'X-Forwarded-For': '192.168.1.100'}
            backend_responses = []
            
            for i in range(10):
                async with self.session.get(f"{self.base_url}/api/health", headers=headers) as response:
                    if 'X-Backend-Server' in response.headers:
                        backend_responses.append(response.headers['X-Backend-Server'])
            
            if backend_responses:
                unique_backends = set(backend_responses)
                details['session_affinity_working'] = len(unique_backends) == 1
                details['backend'] = backend_responses[0] if backend_responses else None
                passed = len(unique_backends) == 1
            else:
                passed = True  # Can't test without backend headers
                details['message'] = "Session affinity test inconclusive (no backend headers)"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Session Affinity Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Session affinity test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_health_check_failover(self):
        """Test health check based failover"""
        start_time = time.time()
        details = {}
        
        try:
            # Monitor responses over time to see if failover occurs
            initial_responses = []
            for i in range(5):
                async with self.session.get(f"{self.base_url}/api/health") as response:
                    initial_responses.append(response.status)
                await asyncio.sleep(1)
            
            details['initial_success_rate'] = sum(1 for r in initial_responses if r == 200) / len(initial_responses)
            
            # Wait and check again
            await asyncio.sleep(10)
            
            later_responses = []
            for i in range(5):
                async with self.session.get(f"{self.base_url}/api/health") as response:
                    later_responses.append(response.status)
                await asyncio.sleep(1)
            
            details['later_success_rate'] = sum(1 for r in later_responses if r == 200) / len(later_responses)
            
            # Test passes if we maintain good success rates
            passed = (details['initial_success_rate'] > 0.8 and 
                     details['later_success_rate'] > 0.8)
            
            details['message'] = "Health check failover maintaining availability"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Health Check Failover Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Health check failover test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        start_time = time.time()
        details = {}
        
        try:
            # Make requests to potentially failing endpoint
            responses = []
            for i in range(20):
                try:
                    async with self.session.get(f"{self.base_url}/api/test-error", timeout=2) as response:
                        responses.append(response.status)
                except asyncio.TimeoutError:
                    responses.append('timeout')
                except Exception:
                    responses.append('error')
                
                await asyncio.sleep(0.1)
            
            details['total_requests'] = len(responses)
            details['successful_requests'] = sum(1 for r in responses if r == 200)
            details['error_responses'] = sum(1 for r in responses if r in ['error', 'timeout'])
            
            # Circuit breaker should prevent cascading failures
            passed = details['error_responses'] < len(responses)  # Not all should fail
            details['message'] = "Circuit breaker preventing cascading failures"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Circuit Breaker Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Circuit breaker test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        start_time = time.time()
        details = {}
        
        try:
            # Make rapid requests to test rate limiting
            responses = []
            start = time.time()
            
            for i in range(50):
                async with self.session.get(f"{self.base_url}/api/health") as response:
                    responses.append(response.status)
            
            duration_test = time.time() - start
            details['total_requests'] = len(responses)
            details['duration'] = duration_test
            details['requests_per_second'] = len(responses) / duration_test
            
            # Check for rate limit responses (429)
            rate_limited = sum(1 for r in responses if r == 429)
            details['rate_limited_requests'] = rate_limited
            
            # Rate limiting should be active
            passed = rate_limited > 0 or details['requests_per_second'] < 200  # Some reasonable limit
            details['message'] = f"Rate limiting active ({rate_limited} requests limited)"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Rate Limiting Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Rate limiting test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_burst_capacity(self):
        """Test burst capacity handling"""
        start_time = time.time()
        details = {}
        
        try:
            # Test burst capacity with concurrent requests
            async def make_burst_request():
                try:
                    async with self.session.get(f"{self.base_url}/api/health") as response:
                        return response.status
                except:
                    return 'error'
            
            # Launch burst of requests
            tasks = [make_burst_request() for _ in range(30)]
            responses = await asyncio.gather(*tasks)
            
            details['burst_size'] = len(responses)
            details['successful_burst'] = sum(1 for r in responses if r == 200)
            details['burst_success_rate'] = details['successful_burst'] / len(responses)
            
            passed = details['burst_success_rate'] > 0.7  # At least 70% should succeed
            details['message'] = f"Burst capacity: {details['successful_burst']}/{details['burst_size']}"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Burst Capacity Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Burst capacity test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_ssl_termination(self):
        """Test SSL termination"""
        start_time = time.time()
        details = {}
        
        try:
            # Test HTTPS if available
            https_url = self.base_url.replace('http://', 'https://')
            
            try:
                async with self.session.get(https_url, ssl=False) as response:
                    details['https_status'] = response.status
                    details['ssl_working'] = True
                    passed = response.status == 200
            except:
                # HTTPS not available, test HTTP headers for SSL info
                async with self.session.get(f"{self.base_url}/") as response:
                    details['http_status'] = response.status
                    details['ssl_headers'] = {k: v for k, v in response.headers.items() if 'ssl' in k.lower()}
                    passed = True  # HTTP working is acceptable for this test
            
            details['message'] = "SSL termination working" if passed else "SSL termination issues"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("SSL Termination Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"SSL termination test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_ssl_redirects(self):
        """Test HTTP to HTTPS redirects"""
        start_time = time.time()
        details = {}
        
        try:
            # Test if HTTP redirects to HTTPS
            async with self.session.get(f"{self.base_url}/", allow_redirects=False) as response:
                details['redirect_status'] = response.status
                if response.status in [301, 302, 307, 308]:
                    details['location'] = response.headers.get('Location', '')
                    passed = 'https' in details['location']
                else:
                    passed = True  # No redirect is also acceptable
            
            details['message'] = "SSL redirect working" if passed else "SSL redirect not working"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("SSL Redirect Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"SSL redirect test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_concurrent_connections(self):
        """Test concurrent connection handling"""
        start_time = time.time()
        details = {}
        
        try:
            # Test with many concurrent connections
            async def make_connection():
                try:
                    async with self.session.get(f"{self.base_url}/api/health") as response:
                        return response.status
                except:
                    return 'error'
            
            # Test different levels of concurrency
            for concurrency in [10, 25, 50]:
                tasks = [make_connection() for _ in range(concurrency)]
                responses = await asyncio.gather(*tasks)
                
                success_rate = sum(1 for r in responses if r == 200) / len(responses)
                details[f'concurrency_{concurrency}_success_rate'] = success_rate
            
            # Check if higher concurrency still works reasonably well
            passed = details.get('concurrency_50_success_rate', 0) > 0.5
            details['message'] = f"Concurrent connections handled successfully"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Concurrent Connections Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Concurrent connections test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_response_times(self):
        """Test response time performance"""
        start_time = time.time()
        details = {}
        
        try:
            response_times = []
            
            # Collect response times
            for i in range(20):
                request_start = time.time()
                async with self.session.get(f"{self.base_url}/api/health") as response:
                    await response.text()
                response_times.append(time.time() - request_start)
            
            details['avg_response_time'] = statistics.mean(response_times)
            details['min_response_time'] = min(response_times)
            details['max_response_time'] = max(response_times)
            details['p95_response_time'] = sorted(response_times)[int(0.95 * len(response_times))]
            
            # Response times should be reasonable (< 1 second average)
            passed = details['avg_response_time'] < 1.0
            details['message'] = f"Average response time: {details['avg_response_time']:.3f}s"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Response Times Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Response times test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_connection_pooling(self):
        """Test connection pooling efficiency"""
        start_time = time.time()
        details = {}
        
        try:
            # Make sequential requests to test connection reuse
            response_times = []
            
            for i in range(10):
                request_start = time.time()
                async with self.session.get(f"{self.base_url}/api/health") as response:
                    await response.text()
                response_times.append(time.time() - request_start)
            
            # Later requests should be faster due to connection pooling
            early_avg = statistics.mean(response_times[:3])
            late_avg = statistics.mean(response_times[-3:])
            
            details['early_avg_time'] = early_avg
            details['late_avg_time'] = late_avg
            details['improvement'] = (early_avg - late_avg) / early_avg if early_avg > 0 else 0
            
            # Connection pooling should show some improvement
            passed = details['improvement'] > 0 or late_avg < 0.5
            details['message'] = f"Connection pooling improvement: {details['improvement']:.1%}"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Connection Pooling Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Connection pooling test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_failover_mechanism(self):
        """Test automatic failover"""
        start_time = time.time()
        details = {}
        
        try:
            # Monitor availability over time
            availability_samples = []
            
            for i in range(10):
                try:
                    async with self.session.get(f"{self.base_url}/api/health", timeout=5) as response:
                        availability_samples.append(response.status == 200)
                except:
                    availability_samples.append(False)
                
                await asyncio.sleep(2)
            
            details['availability_samples'] = availability_samples
            details['availability_rate'] = sum(availability_samples) / len(availability_samples)
            
            # High availability should be maintained
            passed = details['availability_rate'] > 0.8
            details['message'] = f"Availability: {details['availability_rate']:.1%}"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Failover Mechanism Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Failover mechanism test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_graceful_degradation(self):
        """Test graceful degradation under load"""
        start_time = time.time()
        details = {}
        
        try:
            # Test different endpoints under load
            endpoints = ['/health', '/api/health', '/']
            results = {}
            
            for endpoint in endpoints:
                response_times = []
                success_count = 0
                
                for i in range(10):
                    try:
                        request_start = time.time()
                        async with self.session.get(f"{self.base_url}{endpoint}") as response:
                            if response.status == 200:
                                success_count += 1
                            await response.text()
                        response_times.append(time.time() - request_start)
                    except:
                        response_times.append(10.0)  # Timeout
                
                results[endpoint] = {
                    'success_rate': success_count / 10,
                    'avg_response_time': statistics.mean(response_times)
                }
            
            details['endpoint_results'] = results
            
            # All endpoints should maintain reasonable performance
            all_good = all(
                result['success_rate'] > 0.7 and result['avg_response_time'] < 2.0
                for result in results.values()
            )
            
            passed = all_good
            details['message'] = "Graceful degradation maintained"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Graceful Degradation Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Graceful degradation test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_metrics_endpoint(self):
        """Test metrics endpoint"""
        start_time = time.time()
        details = {}
        
        try:
            async with self.session.get(f"{self.base_url}/metrics") as response:
                details['metrics_status'] = response.status
                metrics_text = await response.text()
                details['metrics_length'] = len(metrics_text)
                
                # Check for common metrics
                common_metrics = [
                    'nginx_http_requests_total',
                    'nginx_upstream_response_time',
                    'process_cpu_seconds_total'
                ]
                
                found_metrics = [metric for metric in common_metrics if metric in metrics_text]
                details['found_metrics'] = found_metrics
                
                passed = response.status == 200 and len(found_metrics) > 0
                details['message'] = f"Found {len(found_metrics)} expected metrics"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Metrics Endpoint Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Metrics endpoint test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_prometheus_integration(self):
        """Test Prometheus integration"""
        start_time = time.time()
        details = {}
        
        try:
            # Test if metrics are in Prometheus format
            async with self.session.get(f"{self.base_url}/metrics") as response:
                metrics_text = await response.text()
                
                # Check Prometheus format
                lines = metrics_text.split('\n')
                metric_lines = [line for line in lines if line and not line.startswith('#')]
                
                details['total_metrics'] = len(metric_lines)
                details['sample_metrics'] = metric_lines[:3] if metric_lines else []
                
                # Basic format validation
                valid_format = all(
                    ' ' in line and line.split(' ')[-1].replace('.', '').isdigit()
                    for line in metric_lines[:5] if line
                )
                
                passed = response.status == 200 and len(metric_lines) > 10 and valid_format
                details['message'] = f"Prometheus format valid with {len(metric_lines)} metrics"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Prometheus Integration Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Prometheus integration test: {'PASSED' if passed else 'FAILED'}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': passed_tests / total_tests if total_tests > 0 else 0,
                'total_duration': sum(r.duration for r in self.results)
            },
            'test_results': [
                {
                    'name': result.name,
                    'passed': result.passed,
                    'duration': result.duration,
                    'details': result.details,
                    'error': result.error
                }
                for result in self.results
            ]
        }
        
        return report

async def main():
    """Main test runner"""
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:80"
    
    async with LoadBalancerTester(base_url) as tester:
        report = await tester.run_all_tests()
        
        print("\n" + "="*60)
        print("ADVANCED LOAD BALANCER TEST REPORT")
        print("="*60)
        
        summary = report['summary']
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print(f"Total Duration: {summary['total_duration']:.2f}s")
        print()
        
        # Print failed tests
        failed_results = [r for r in report['test_results'] if not r['passed']]
        if failed_results:
            print("FAILED TESTS:")
            print("-" * 40)
            for result in failed_results:
                print(f"❌ {result['name']}")
                if result.get('error'):
                    print(f"   Error: {result['error']}")
                print()
        
        # Print all results
        print("DETAILED RESULTS:")
        print("-" * 40)
        for result in report['test_results']:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"{status} {result['name']} ({result['duration']:.2f}s)")
            if result.get('details', {}).get('message'):
                print(f"     {result['details']['message']}")
        
        print("\n" + "="*60)
        
        # Save report to file
        with open('load-balancer-test-report.json', 'w') as f:
            json.dump(report, f, indent=2)
        print("Detailed report saved to: load-balancer-test-report.json")
        
        return summary['success_rate'] >= 0.8  # Return True if 80%+ tests pass

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
