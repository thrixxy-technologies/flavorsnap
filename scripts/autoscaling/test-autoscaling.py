#!/usr/bin/env python3
"""
Comprehensive Auto-Scaling Testing Suite
Tests all aspects of intelligent auto-scaling system
"""

import asyncio
import aiohttp
import time
import json
import logging
import statistics
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    name: str
    passed: bool
    duration: float
    details: Dict[str, Any]
    error: str = ""

class AutoScalingTester:
    """Comprehensive auto-scaling testing suite"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
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
        """Run all auto-scaling tests"""
        logger.info("Starting comprehensive auto-scaling tests...")
        
        # Basic functionality tests
        await self.test_autoscaler_health()
        await self.test_policy_management()
        await self.test_metrics_collection()
        await self.test_cost_optimization()
        
        # Scaling behavior tests
        await self.test_threshold_based_scaling()
        await self.test_predictive_scaling()
        await self.test_scheduled_scaling()
        await self.test_custom_scaling_rules()
        
        # Performance tests
        await self.test_scaling_latency()
        await self.test_resource_optimization()
        await self.test_cost_savings()
        
        # Integration tests
        await self.test_kubernetes_integration()
        await self.test_prometheus_integration()
        await self.test_alerting_system()
        
        return self.generate_report()
    
    async def test_autoscaler_health(self):
        """Test autoscaler health endpoints"""
        start_time = time.time()
        details = {}
        
        try:
            # Test main health endpoint
            async with self.session.get(f"{self.base_url}/health") as response:
                details['health_status'] = response.status
                details['health_response'] = await response.text()
                
                if response.status == 200:
                    passed = True
                    details['message'] = "Autoscaler health endpoint working"
                else:
                    passed = False
                    details['message'] = f"Health endpoint returned {response.status}"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Autoscaler Health Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Autoscaler health test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_policy_management(self):
        """Test policy management functionality"""
        start_time = time.time()
        details = {}
        
        try:
            # Test getting all policies
            async with self.session.get(f"{self.base_url}/policies") as response:
                details['get_policies_status'] = response.status
                if response.status == 200:
                    policies = await response.json()
                    details['policy_count'] = len(policies.get('policies', {}))
            
            # Test creating a test policy
            test_policy = {
                'name': 'test-policy',
                'component': 'test-component',
                'policy_type': 'threshold_based',
                'min_replicas': 1,
                'max_replicas': 5,
                'default_replicas': 2,
                'thresholds': [
                    {
                        'metric': 'cpu_utilization',
                        'operator': '>',
                        'value': 80.0,
                        'duration': 60,
                        'cooldown': 120
                    }
                ]
            }
            
            async with self.session.post(
                f"{self.base_url}/policies",
                json=test_policy
            ) as response:
                details['create_policy_status'] = response.status
                if response.status in [200, 201]:
                    details['create_policy_response'] = await response.json()
            
            # Test updating the policy
            update_data = {'enabled': False}
            async with self.session.patch(
                f"{self.base_url}/policies/test-policy",
                json=update_data
            ) as response:
                details['update_policy_status'] = response.status
                if response.status == 200:
                    details['update_policy_response'] = await response.json()
            
            # Test deleting the test policy
            async with self.session.delete(f"{self.base_url}/policies/test-policy") as response:
                details['delete_policy_status'] = response.status
            
            passed = (
                details['get_policies_status'] == 200 and
                details['create_policy_status'] in [200, 201] and
                details['update_policy_status'] == 200 and
                details['delete_policy_status'] in [200, 204]
            )
            
            details['message'] = "Policy management working correctly"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Policy Management Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Policy management test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_metrics_collection(self):
        """Test metrics collection and analysis"""
        start_time = time.time()
        details = {}
        
        try:
            # Test metrics endpoint
            async with self.session.get(f"{self.base_url}/metrics") as response:
                details['metrics_status'] = response.status
                if response.status == 200:
                    metrics_text = await response.text()
                    details['metrics_count'] = len([line for line in metrics_text.split('\n') if line and not line.startswith('#')])
            
            # Test cost metrics endpoint
            async with self.session.get(f"{self.base_url}/cost-metrics") as response:
                details['cost_metrics_status'] = response.status
                if response.status == 200:
                    cost_metrics = await response.json()
                    details['cost_metrics_components'] = len(cost_metrics.get('components', {}))
            
            # Test scaling status endpoint
            async with self.session.get(f"{self.base_url}/status") as response:
                details['status_status'] = response.status
                if response.status == 200:
                    status_data = await response.json()
                    details['status_components'] = len(status_data.get('components', {}))
            
            passed = (
                details['metrics_status'] == 200 and
                details['cost_metrics_status'] == 200 and
                details['status_status'] == 200
            )
            
            details['message'] = "Metrics collection working correctly"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Metrics Collection Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Metrics collection test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_cost_optimization(self):
        """Test cost optimization functionality"""
        start_time = time.time()
        details = {}
        
        try:
            # Test cost optimization endpoint
            async with self.session.get(f"{self.base_url}/cost-optimization") as response:
                details['cost_optimization_status'] = response.status
                if response.status == 200:
                    optimization_data = await response.json()
                    details['opportunities_count'] = len(optimization_data.get('opportunities', []))
                    details['total_savings'] = optimization_data.get('summary', {}).get('total_savings_per_hour', 0)
            
            # Test applying cost optimization
            test_optimization = {
                'component': 'test-component',
                'recommended_replicas': 3,
                'recommended_instance_type': 'spot',
                'savings_per_hour': 5.0
            }
            
            async with self.session.post(
                f"{self.base_url}/cost-optimization/apply",
                json=test_optimization
            ) as response:
                details['apply_optimization_status'] = response.status
                if response.status == 200:
                    apply_result = await response.json()
                    details['optimization_applied'] = apply_result.get('success', False)
            
            passed = (
                details['cost_optimization_status'] == 200 and
                details['apply_optimization_status'] == 200
            )
            
            details['message'] = "Cost optimization working correctly"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Cost Optimization Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Cost optimization test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_threshold_based_scaling(self):
        """Test threshold-based scaling behavior"""
        start_time = time.time()
        details = {}
        
        try:
            # Simulate high CPU usage to trigger scale-up
            high_cpu_metrics = {
                'component': 'test-component',
                'cpu_utilization': 85.0,
                'memory_utilization': 60.0,
                'request_rate': 500.0,
                'current_replicas': 2
            }
            
            async with self.session.post(
                f"{self.base_url}/evaluate-policies",
                json=high_cpu_metrics
            ) as response:
                details['high_cpu_evaluation_status'] = response.status
                if response.status == 200:
                    evaluation = await response.json()
                    details['high_cpu_actions'] = len(evaluation.get('actions', []))
            
            # Simulate low CPU usage to test scale-down
            low_cpu_metrics = {
                'component': 'test-component',
                'cpu_utilization': 30.0,
                'memory_utilization': 40.0,
                'request_rate': 100.0,
                'current_replicas': 4
            }
            
            async with self.session.post(
                f"{self.base_url}/evaluate-policies",
                json=low_cpu_metrics
            ) as response:
                details['low_cpu_evaluation_status'] = response.status
                if response.status == 200:
                    evaluation = await response.json()
                    details['low_cpu_actions'] = len(evaluation.get('actions', []))
            
            passed = (
                details['high_cpu_evaluation_status'] == 200 and
                details['low_cpu_evaluation_status'] == 200
            )
            
            details['message'] = "Threshold-based scaling working correctly"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Threshold-Based Scaling Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Threshold-based scaling test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_predictive_scaling(self):
        """Test predictive scaling functionality"""
        start_time = time.time()
        details = {}
        
        try:
            # Test predictive model training
            training_data = [
                {
                    'cpu_utilization': 60.0 + random.uniform(-10, 10),
                    'memory_utilization': 50.0 + random.uniform(-5, 5),
                    'request_rate': 200.0 + random.uniform(-50, 50),
                    'timestamp': time.time() - i * 60
                }
                for i in range(100)
            ]
            
            async with self.session.post(
                f"{self.base_url}/train-model",
                json={'training_data': training_data}
            ) as response:
                details['training_status'] = response.status
                if response.status == 200:
                    training_result = await response.json()
                    details['model_trained'] = training_result.get('success', False)
            
            # Test prediction
            test_metrics = {
                'component': 'test-component',
                'cpu_utilization': 70.0,
                'memory_utilization': 60.0,
                'request_rate': 300.0,
                'current_replicas': 3
            }
            
            async with self.session.post(
                f"{self.base_url}/predict",
                json=test_metrics
            ) as response:
                details['prediction_status'] = response.status
                if response.status == 200:
                    prediction = await response.json()
                    details['prediction_made'] = 'predicted_value' in prediction
                    details['prediction_confidence'] = prediction.get('confidence', 0)
            
            passed = (
                details['training_status'] == 200 and
                details['prediction_status'] == 200
            )
            
            details['message'] = "Predictive scaling working correctly"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Predictive Scaling Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Predictive scaling test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_scheduled_scaling(self):
        """Test scheduled scaling functionality"""
        start_time = time.time()
        details = {}
        
        try:
            # Create a test schedule
            test_schedule = {
                'name': 'test-schedule',
                'component': 'test-component',
                'policy_type': 'schedule_based',
                'schedules': [
                    {
                        'name': 'business_hours',
                        'timezone': 'UTC',
                        'schedules': [
                            {
                                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
                                'start_time': '09:00',
                                'end_time': '18:00',
                                'replicas': 5
                            }
                        ]
                    }
                ]
            }
            
            async with self.session.post(
                f"{self.base_url}/policies",
                json=test_schedule
            ) as response:
                details['schedule_creation_status'] = response.status
                if response.status in [200, 201]:
                    details['schedule_created'] = True
            
            # Test schedule evaluation
            current_time = time.time()
            test_datetime = time.strftime('%A %H:%M', time.gmtime(current_time))
            
            async with self.session.get(f"{self.base_url}/evaluate-schedule") as response:
                details['schedule_evaluation_status'] = response.status
                if response.status == 200:
                    evaluation = await response.json()
                    details['schedule_active'] = evaluation.get('active', False)
            
            passed = (
                details['schedule_creation_status'] in [200, 201] and
                details['schedule_evaluation_status'] == 200
            )
            
            details['message'] = "Scheduled scaling working correctly"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Scheduled Scaling Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Scheduled scaling test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_custom_scaling_rules(self):
        """Test custom scaling rules functionality"""
        start_time = time.time()
        details = {}
        
        try:
            # Create policy with custom rules
            custom_policy = {
                'name': 'test-custom-policy',
                'component': 'test-component',
                'policy_type': 'custom',
                'custom_rules': [
                    {
                        'type': 'ml_model_load',
                        'condition': 'high_prediction_volume',
                        'action': 'scale_up',
                        'multiplier': 1.5
                    },
                    {
                        'type': 'cost_optimization',
                        'condition': 'low_traffic_period',
                        'action': 'scale_down',
                        'min_replicas': 1
                    }
                ]
            }
            
            async with self.session.post(
                f"{self.base_url}/policies",
                json=custom_policy
            ) as response:
                details['custom_policy_status'] = response.status
                if response.status in [200, 201]:
                    details['custom_policy_created'] = True
            
            # Test custom rule evaluation
            test_metrics = {
                'component': 'test-component',
                'cpu_utilization': 75.0,
                'memory_utilization': 60.0,
                'request_rate': 400.0,
                'ml_prediction_volume': 1000.0,  # High volume
                'current_replicas': 3
            }
            
            async with self.session.post(
                f"{self.base_url}/evaluate-policies",
                json=test_metrics
            ) as response:
                details['custom_evaluation_status'] = response.status
                if response.status == 200:
                    evaluation = await response.json()
                    details['custom_actions'] = len(evaluation.get('actions', []))
            
            passed = (
                details['custom_policy_status'] in [200, 201] and
                details['custom_evaluation_status'] == 200
            )
            
            details['message'] = "Custom scaling rules working correctly"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Custom Scaling Rules Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Custom scaling rules test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_scaling_latency(self):
        """Test scaling decision latency"""
        start_time = time.time()
        details = {}
        
        try:
            # Measure scaling decision time
            latencies = []
            
            for i in range(10):
                decision_start = time.time()
                
                test_metrics = {
                    'component': 'test-component',
                    'cpu_utilization': 85.0,
                    'memory_utilization': 70.0,
                    'request_rate': 500.0,
                    'current_replicas': 2
                }
                
                async with self.session.post(
                    f"{self.base_url}/evaluate-policies",
                    json=test_metrics
                ) as response:
                    if response.status == 200:
                        decision_time = time.time() - decision_start
                        latencies.append(decision_time)
                
                await asyncio.sleep(0.1)  # Small delay between requests
            
            if latencies:
                details['avg_latency'] = statistics.mean(latencies)
                details['max_latency'] = max(latencies)
                details['min_latency'] = min(latencies)
                details['p95_latency'] = sorted(latencies)[int(len(latencies) * 0.95)]
                
                # Check if latency is acceptable (< 1 second)
                passed = details['avg_latency'] < 1.0
                details['message'] = f"Average scaling latency: {details['avg_latency']:.3f}s"
            else:
                passed = False
                details['message'] = "No latency measurements collected"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Scaling Latency Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Scaling latency test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_resource_optimization(self):
        """Test resource optimization functionality"""
        start_time = time.time()
        details = {}
        
        try:
            # Test resource optimization recommendations
            current_resources = {
                'component': 'test-component',
                'current_replicas': 5,
                'cpu_request': 0.5,
                'memory_request_mb': 1024,
                'utilization_score': 60.0
            }
            
            async with self.session.post(
                f"{self.base_url}/optimize-resources",
                json=current_resources
            ) as response:
                details['optimization_status'] = response.status
                if response.status == 200:
                    optimization = await response.json()
                    details['recommendations'] = len(optimization.get('recommendations', []))
                    details['potential_savings'] = optimization.get('potential_savings', 0)
            
            # Test applying optimization
            optimization_action = {
                'component': 'test-component',
                'action': 'optimize_resources',
                'target_replicas': 3,
                'target_cpu': 0.3,
                'target_memory_mb': 512
            }
            
            async with self.session.post(
                f"{self.base_url}/apply-optimization",
                json=optimization_action
            ) as response:
                details['apply_optimization_status'] = response.status
                if response.status == 200:
                    apply_result = await response.json()
                    details['optimization_applied'] = apply_result.get('success', False)
            
            passed = (
                details['optimization_status'] == 200 and
                details['apply_optimization_status'] == 200
            )
            
            details['message'] = "Resource optimization working correctly"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Resource Optimization Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Resource optimization test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_cost_savings(self):
        """Test cost savings calculation and tracking"""
        start_time = time.time()
        details = {}
        
        try:
            # Test cost analysis
            cost_data = {
                'components': [
                    {
                        'name': 'frontend',
                        'current_replicas': 4,
                        'cpu_request': 0.5,
                        'memory_request_mb': 512,
                        'instance_type': 'on_demand',
                        'cost_per_hour': 0.20
                    },
                    {
                        'name': 'backend',
                        'current_replicas': 3,
                        'cpu_request': 1.0,
                        'memory_request_mb': 1024,
                        'instance_type': 'on_demand',
                        'cost_per_hour': 0.30
                    }
                ]
            }
            
            async with self.session.post(
                f"{self.base_url}/analyze-costs",
                json=cost_data
            ) as response:
                details['cost_analysis_status'] = response.status
                if response.status == 200:
                    analysis = await response.json()
                    details['total_cost'] = analysis.get('total_current_cost', 0)
                    details['potential_savings'] = analysis.get('total_savings', 0)
                    details['savings_percentage'] = analysis.get('total_savings_percentage', 0)
            
            # Test cost optimization recommendations
            async with self.session.get(f"{self.base_url}/cost-recommendations") as response:
                details['recommendations_status'] = response.status
                if response.status == 200:
                    recommendations = await response.json()
                    details['recommendations_count'] = len(recommendations.get('recommendations', []))
            
            passed = (
                details['cost_analysis_status'] == 200 and
                details['recommendations_status'] == 200
            )
            
            details['message'] = "Cost savings analysis working correctly"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Cost Savings Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Cost savings test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_kubernetes_integration(self):
        """Test Kubernetes integration"""
        start_time = time.time()
        details = {}
        
        try:
            # Test Kubernetes API access
            async with self.session.get(f"{self.base_url}/k8s-status") as response:
                details['k8s_status'] = response.status
                if response.status == 200:
                    k8s_info = await response.json()
                    details['cluster_accessible'] = k8s_info.get('accessible', False)
                    details['namespace_accessible'] = k8s_info.get('namespace_accessible', False)
            
            # Test deployment scaling
            scale_request = {
                'component': 'test-component',
                'target_replicas': 5,
                'reason': 'test scaling'
            }
            
            async with self.session.post(
                f"{self.base_url}/scale-deployment",
                json=scale_request
            ) as response:
                details['scale_deployment_status'] = response.status
                if response.status == 200:
                    scale_result = await response.json()
                    details['scaling_applied'] = scale_result.get('success', False)
            
            passed = (
                details['k8s_status'] == 200 and
                details['scale_deployment_status'] == 200
            )
            
            details['message'] = "Kubernetes integration working correctly"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Kubernetes Integration Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Kubernetes integration test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_prometheus_integration(self):
        """Test Prometheus metrics integration"""
        start_time = time.time()
        details = {}
        
        try:
            # Test Prometheus metrics endpoint
            async with self.session.get(f"{self.base_url}/prometheus-metrics") as response:
                details['prometheus_metrics_status'] = response.status
                if response.status == 200:
                    metrics_text = await response.text()
                    details['metrics_lines'] = len([line for line in metrics_text.split('\n') if line and not line.startswith('#')])
            
            # Test custom metrics creation
            custom_metric = {
                'name': 'test_scaling_event',
                'type': 'counter',
                'help': 'Test scaling event counter'
            }
            
            async with self.session.post(
                f"{self.base_url}/create-metric",
                json=custom_metric
            ) as response:
                details['create_metric_status'] = response.status
                if response.status in [200, 201]:
                    details['metric_created'] = True
            
            # Test metric recording
            metric_record = {
                'metric_name': 'test_scaling_event',
                'value': 1,
                'labels': {
                    'component': 'test',
                    'action': 'scale_up'
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/record-metric",
                json=metric_record
            ) as response:
                details['record_metric_status'] = response.status
                if response.status == 200:
                    details['metric_recorded'] = True
            
            passed = (
                details['prometheus_metrics_status'] == 200 and
                details['create_metric_status'] in [200, 201] and
                details['record_metric_status'] == 200
            )
            
            details['message'] = "Prometheus integration working correctly"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Prometheus Integration Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Prometheus integration test: {'PASSED' if passed else 'FAILED'}")
    
    async def test_alerting_system(self):
        """Test alerting system functionality"""
        start_time = time.time()
        details = {}
        
        try:
            # Test alert rules
            async with self.session.get(f"{self.base_url}/alert-rules") as response:
                details['alert_rules_status'] = response.status
                if response.status == 200:
                    rules = await response.json()
                    details['alert_rules_count'] = len(rules.get('rules', []))
            
            # Test alert triggering
            alert_event = {
                'alert_name': 'test_high_cpu',
                'severity': 'warning',
                'component': 'test-component',
                'message': 'Test alert for high CPU utilization',
                'labels': {
                    'component': 'test',
                    'metric': 'cpu'
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/trigger-alert",
                json=alert_event
            ) as response:
                details['trigger_alert_status'] = response.status
                if response.status == 200:
                    alert_result = await response.json()
                    details['alert_triggered'] = alert_result.get('success', False)
            
            # Test alert history
            async with self.session.get(f"{self.base_url}/alert-history") as response:
                details['alert_history_status'] = response.status
                if response.status == 200:
                    history = await response.json()
                    details['alert_history_count'] = len(history.get('alerts', []))
            
            passed = (
                details['alert_rules_status'] == 200 and
                details['trigger_alert_status'] == 200 and
                details['alert_history_status'] == 200
            )
            
            details['message'] = "Alerting system working correctly"
        
        except Exception as e:
            passed = False
            details['error'] = str(e)
        
        duration = time.time() - start_time
        result = TestResult("Alerting System Test", passed, duration, details)
        self.results.append(result)
        logger.info(f"Alerting system test: {'PASSED' if passed else 'FAILED'}")
    
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
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    async with AutoScalingTester(base_url) as tester:
        report = await tester.run_all_tests()
        
        print("\n" + "="*60)
        print("INTELLIGENT AUTO-SCALING TEST REPORT")
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
        with open('auto-scaling-test-report.json', 'w') as f:
            json.dump(report, f, indent=2)
        print("Detailed report saved to: auto-scaling-test-report.json")
        
        return summary['success_rate'] >= 0.8  # Return True if 80%+ tests pass

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
