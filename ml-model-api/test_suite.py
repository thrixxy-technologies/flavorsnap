"""
Advanced Testing and Quality Assurance Suite for FlavorSnap
Comprehensive automated testing with quality gates and reporting
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
import pytest
import requests
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import numpy as np
import pandas as pd
from jinja2 import Template

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Individual test result"""
    name: str
    suite: str
    status: str  # passed, failed, skipped, error
    duration: float
    message: str = ""
    traceback: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TestSuite:
    """Test suite configuration and results"""
    name: str
    description: str
    tests: List[TestResult] = field(default_factory=list)
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    total_duration: float = 0.0
    coverage: float = 0.0
    quality_score: float = 0.0
    
    def calculate_summary(self):
        """Calculate test suite summary"""
        self.total_tests = len(self.tests)
        self.passed_tests = len([t for t in self.tests if t.status == 'passed'])
        self.failed_tests = len([t for t in self.tests if t.status == 'failed'])
        self.skipped_tests = len([t for t in self.tests if t.status == 'skipped'])
        self.error_tests = len([t for t in self.tests if t.status == 'error'])
        self.total_duration = sum(t.duration for t in self.tests)
        
        # Calculate quality score
        if self.total_tests > 0:
            pass_rate = self.passed_tests / self.total_tests
            self.quality_score = (pass_rate * 0.7 + self.coverage * 0.3) * 100


@dataclass
class QualityGate:
    """Quality gate configuration"""
    name: str
    description: str
    conditions: List[Dict[str, Any]]
    enabled: bool = True
    blocking: bool = True  # Whether to block deployment on failure


@dataclass
class QualityGateResult:
    """Quality gate evaluation result"""
    gate_name: str
    passed: bool
    score: float
    conditions_met: List[str]
    conditions_failed: List[str]
    details: Dict[str, Any] = field(default_factory=dict)


class AutomatedTestRunner:
    """Advanced automated test runner"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.test_suites = {}
        self.quality_gates = {}
        self.test_results = []
        self.coverage_data = {}
        
        # Test execution configuration
        self.parallel_execution = config.get('parallel_execution', True)
        self.max_workers = config.get('max_workers', 4)
        self.timeout = config.get('timeout', 300)  # 5 minutes
        
        # Initialize quality gates
        self._setup_quality_gates()
    
    def _setup_quality_gates(self):
        """Setup default quality gates"""
        default_gates = [
            QualityGate(
                name="code_coverage",
                description="Minimum code coverage of 80%",
                conditions=[
                    {"metric": "coverage", "operator": "gte", "value": 80.0}
                ]
            ),
            QualityGate(
                name="test_success_rate",
                description="Test success rate of 95%",
                conditions=[
                    {"metric": "success_rate", "operator": "gte", "value": 95.0}
                ]
            ),
            QualityGate(
                name="performance_tests",
                description="Performance tests must pass",
                conditions=[
                    {"metric": "performance_passed", "operator": "eq", "value": True}
                ]
            ),
            QualityGate(
                name="security_tests",
                description="Security tests must pass",
                conditions=[
                    {"metric": "security_passed", "operator": "eq", "value": True}
                ]
            ),
            QualityGate(
                name="integration_tests",
                description="Integration tests must pass",
                conditions=[
                    {"metric": "integration_passed", "operator": "eq", "value": True}
                ]
            )
        ]
        
        for gate in default_gates:
            self.quality_gates[gate.name] = gate
    
    async def run_all_tests(self) -> Dict[str, TestSuite]:
        """Run all test suites"""
        logger.info("Starting comprehensive test execution...")
        
        # Define test suites
        test_suites_config = [
            {
                "name": "unit_tests",
                "description": "Unit tests for individual components",
                "test_path": "tests/unit",
                "pytest_args": ["-v", "--tb=short"]
            },
            {
                "name": "integration_tests", 
                "description": "Integration tests for component interactions",
                "test_path": "tests/integration",
                "pytest_args": ["-v", "--tb=short"]
            },
            {
                "name": "performance_tests",
                "description": "Performance and load tests",
                "test_path": "tests/performance",
                "pytest_args": ["-v", "--tb=short"]
            },
            {
                "name": "security_tests",
                "description": "Security vulnerability tests",
                "test_path": "tests/security",
                "pytest_args": ["-v", "--tb=short"]
            },
            {
                "name": "api_tests",
                "description": "API endpoint tests",
                "test_path": "tests/api",
                "pytest_args": ["-v", "--tb=short"]
            }
        ]
        
        results = {}
        
        if self.parallel_execution:
            # Run test suites in parallel
            tasks = []
            for suite_config in test_suites_config:
                task = asyncio.create_task(
                    self._run_test_suite(suite_config)
                )
                tasks.append(task)
            
            suite_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(suite_results):
                if isinstance(result, Exception):
                    logger.error(f"Test suite {test_suites_config[i]['name']} failed: {result}")
                    # Create failed suite
                    suite = TestSuite(
                        name=test_suites_config[i]['name'],
                        description=test_suites_config[i]['description']
                    )
                    suite.tests.append(TestResult(
                        name="suite_execution",
                        suite=suite.name,
                        status="error",
                        duration=0.0,
                        message=str(result)
                    ))
                    results[suite.name] = suite
                else:
                    results[result.name] = result
        else:
            # Run test suites sequentially
            for suite_config in test_suites_config:
                suite = await self._run_test_suite(suite_config)
                results[suite.name] = suite
        
        # Store results
        self.test_suites = results
        
        # Generate coverage report
        await self._generate_coverage_report()
        
        logger.info("Test execution completed")
        return results
    
    async def _run_test_suite(self, suite_config: Dict[str, Any]) -> TestSuite:
        """Run individual test suite"""
        suite_name = suite_config['name']
        test_path = suite_config['test_path']
        pytest_args = suite_config.get('pytest_args', [])
        
        logger.info(f"Running test suite: {suite_name}")
        
        suite = TestSuite(
            name=suite_name,
            description=suite_config['description']
        )
        
        start_time = time.time()
        
        try:
            # Check if test path exists
            if not Path(test_path).exists():
                logger.warning(f"Test path {test_path} does not exist, skipping suite")
                suite.tests.append(TestResult(
                    name="suite_not_found",
                    suite=suite_name,
                    status="skipped",
                    duration=0.0,
                    message=f"Test path {test_path} not found"
                ))
                return suite
            
            # Run pytest
            cmd = [
                sys.executable, "-m", "pytest",
                test_path,
                "--json-report",
                f"--json-report-file=reports/{suite_name}_report.json",
                "--cov=ml_model_api",
                f"--cov-report=json:reports/{suite_name}_coverage.json",
                "--cov-report=html:reports/{suite_name}_coverage_html",
                "--cov-report=term",
                *pytest_args
            ]
            
            # Create reports directory
            Path("reports").mkdir(exist_ok=True)
            
            # Execute pytest
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=Path.cwd()
            )
            
            # Parse pytest JSON report
            report_file = Path(f"reports/{suite_name}_report.json")
            if report_file.exists():
                try:
                    with open(report_file) as f:
                        pytest_data = json.load(f)
                    
                    # Convert pytest results to TestResult objects
                    for test_info in pytest_data.get('tests', []):
                        test_result = TestResult(
                            name=test_info.get('name', ''),
                            suite=suite_name,
                            status=test_info.get('outcome', 'unknown'),
                            duration=test_info.get('duration', 0.0),
                            message=test_info.get('message', ''),
                            traceback=test_info.get('call', {}).get('longrepr', ''),
                            metrics={
                                'setup_duration': test_info.get('setup', {}).get('duration', 0.0),
                                'teardown_duration': test_info.get('teardown', {}).get('duration', 0.0)
                            }
                        )
                        suite.tests.append(test_result)
                        
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to parse pytest report for {suite_name}: {e}")
            
            # Parse coverage report
            coverage_file = Path(f"reports/{suite_name}_coverage.json")
            if coverage_file.exists():
                try:
                    with open(coverage_file) as f:
                        coverage_data = json.load(f)
                    
                    suite.coverage = coverage_data.get('totals', {}).get('percent_covered', 0.0)
                    self.coverage_data[suite_name] = coverage_data
                    
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to parse coverage report for {suite_name}: {e}")
            
            # Add suite-level result if no individual tests found
            if not suite.tests:
                status = "passed" if result.returncode == 0 else "failed"
                suite.tests.append(TestResult(
                    name="suite_execution",
                    suite=suite_name,
                    status=status,
                    duration=time.time() - start_time,
                    message=result.stdout or result.stderr
                ))
            
        except subprocess.TimeoutExpired:
            logger.error(f"Test suite {suite_name} timed out")
            suite.tests.append(TestResult(
                name="timeout",
                suite=suite_name,
                status="error",
                duration=self.timeout,
                message=f"Test suite timed out after {self.timeout} seconds"
            ))
            
        except Exception as e:
            logger.error(f"Error running test suite {suite_name}: {e}")
            suite.tests.append(TestResult(
                name="execution_error",
                suite=suite_name,
                status="error",
                duration=time.time() - start_time,
                message=str(e)
            ))
        
        # Calculate summary
        suite.calculate_summary()
        
        logger.info(f"Test suite {suite_name} completed: {suite.passed_tests}/{suite.total_tests} passed")
        return suite
    
    async def _generate_coverage_report(self):
        """Generate combined coverage report"""
        try:
            # Combine coverage from all suites
            total_coverage = 0.0
            suite_count = 0
            
            for suite_name, coverage_data in self.coverage_data.items():
                coverage_percent = coverage_data.get('totals', {}).get('percent_covered', 0.0)
                total_coverage += coverage_percent
                suite_count += 1
            
            if suite_count > 0:
                average_coverage = total_coverage / suite_count
                logger.info(f"Average test coverage: {average_coverage:.2f}%")
                
                # Save combined coverage report
                combined_report = {
                    "timestamp": datetime.now().isoformat(),
                    "average_coverage": average_coverage,
                    "suite_coverage": {
                        name: data.get('totals', {}).get('percent_covered', 0.0)
                        for name, data in self.coverage_data.items()
                    }
                }
                
                with open("reports/combined_coverage.json", "w") as f:
                    json.dump(combined_report, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to generate coverage report: {e}")
    
    def evaluate_quality_gates(self) -> List[QualityGateResult]:
        """Evaluate all quality gates"""
        results = []
        
        # Calculate overall metrics
        total_tests = sum(suite.total_tests for suite in self.test_suites.values())
        total_passed = sum(suite.passed_tests for suite in self.test_suites.values())
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0.0
        
        # Calculate average coverage
        total_coverage = sum(suite.coverage for suite in self.test_suites.values())
        average_coverage = total_coverage / len(self.test_suites) if self.test_suites else 0.0
        
        # Check specific suite results
        performance_passed = self.test_suites.get('performance_tests', TestSuite()).passed_tests > 0
        security_passed = self.test_suites.get('security_tests', TestSuite()).passed_tests > 0
        integration_passed = self.test_suites.get('integration_tests', TestSuite()).passed_tests > 0
        
        metrics = {
            'success_rate': success_rate,
            'coverage': average_coverage,
            'performance_passed': performance_passed,
            'security_passed': security_passed,
            'integration_passed': integration_passed,
            'total_tests': total_tests,
            'total_passed': total_passed
        }
        
        for gate_name, gate in self.quality_gates.items():
            if not gate.enabled:
                continue
            
            conditions_met = []
            conditions_failed = []
            gate_passed = True
            
            for condition in gate.conditions:
                metric_name = condition['metric']
                operator = condition['operator']
                expected_value = condition['value']
                
                if metric_name in metrics:
                    actual_value = metrics[metric_name]
                    
                    if self._evaluate_condition(actual_value, operator, expected_value):
                        conditions_met.append(
                            f"{metric_name} {operator} {expected_value} (actual: {actual_value})"
                        )
                    else:
                        conditions_failed.append(
                            f"{metric_name} {operator} {expected_value} (actual: {actual_value})"
                        )
                        gate_passed = False
            
            # Calculate gate score
            total_conditions = len(conditions_met) + len(conditions_failed)
            gate_score = (len(conditions_met) / total_conditions * 100) if total_conditions > 0 else 0.0
            
            result = QualityGateResult(
                gate_name=gate_name,
                passed=gate_passed,
                score=gate_score,
                conditions_met=conditions_met,
                conditions_failed=conditions_failed,
                details=metrics
            )
            
            results.append(result)
            
            # Log result
            status = "PASSED" if gate_passed else "FAILED"
            logger.info(f"Quality gate {gate_name}: {status} (Score: {gate_score:.1f}%)")
            
            if conditions_failed:
                for condition in conditions_failed:
                    logger.warning(f"  Failed: {condition}")
        
        return results
    
    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        """Evaluate quality gate condition"""
        try:
            if operator == 'eq':
                return actual == expected
            elif operator == 'ne':
                return actual != expected
            elif operator == 'gt':
                return actual > expected
            elif operator == 'gte':
                return actual >= expected
            elif operator == 'lt':
                return actual < expected
            elif operator == 'lte':
                return actual <= expected
            elif operator == 'in':
                return actual in expected
            elif operator == 'contains':
                return expected in actual
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    async def run_performance_tests(self) -> TestSuite:
        """Run specialized performance tests"""
        suite = TestSuite(
            name="performance_benchmarks",
            description="Performance benchmark tests"
        )
        
        start_time = time.time()
        
        # Define performance benchmarks
        benchmarks = [
            {
                "name": "api_response_time",
                "url": "http://localhost:8000/api/predict",
                "method": "POST",
                "expected_max_time": 1.0,  # 1 second
                "concurrent_requests": 10
            },
            {
                "name": "model_inference_time",
                "url": "http://localhost:8000/api/classify",
                "method": "POST", 
                "expected_max_time": 2.0,  # 2 seconds
                "concurrent_requests": 5
            },
            {
                "name": "file_upload_time",
                "url": "http://localhost:8000/api/upload",
                "method": "POST",
                "expected_max_time": 5.0,  # 5 seconds
                "concurrent_requests": 3
            }
        ]
        
        for benchmark in benchmarks:
            try:
                result = await self._run_benchmark(benchmark)
                suite.tests.append(result)
                
            except Exception as e:
                suite.tests.append(TestResult(
                    name=benchmark['name'],
                    suite="performance_benchmarks",
                    status="error",
                    duration=0.0,
                    message=str(e)
                ))
        
        suite.calculate_summary()
        return suite
    
    async def _run_benchmark(self, benchmark: Dict[str, Any]) -> TestResult:
        """Run individual performance benchmark"""
        name = benchmark['name']
        url = benchmark['url']
        method = benchmark['method']
        expected_max_time = benchmark['expected_max_time']
        concurrent_requests = benchmark['concurrent_requests']
        
        logger.info(f"Running performance benchmark: {name}")
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Create concurrent requests
                tasks = []
                for i in range(concurrent_requests):
                    if method == 'POST':
                        # Create test data
                        test_data = self._create_test_data(url)
                        task = session.post(url, json=test_data)
                    else:
                        task = session.get(url)
                    tasks.append(task)
                
                # Execute requests concurrently
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Calculate metrics
                response_times = []
                successful_requests = 0
                
                for response in responses:
                    if isinstance(response, Exception):
                        logger.warning(f"Request failed: {response}")
                        continue
                    
                    if response.status == 200:
                        successful_requests += 1
                        # Response time would need to be measured more accurately
                        # For now, use total time / number of requests as approximation
                        response_times.append(time.time() - start_time)
                
                # Calculate average response time
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
                
                # Determine test status
                status = "passed" if avg_response_time <= expected_max_time else "failed"
                message = f"Average response time: {avg_response_time:.3f}s (max: {expected_max_time}s)"
                
                return TestResult(
                    name=name,
                    suite="performance_benchmarks",
                    status=status,
                    duration=time.time() - start_time,
                    message=message,
                    metrics={
                        'avg_response_time': avg_response_time,
                        'successful_requests': successful_requests,
                        'total_requests': concurrent_requests,
                        'success_rate': (successful_requests / concurrent_requests * 100)
                    }
                )
                
        except Exception as e:
            return TestResult(
                name=name,
                suite="performance_benchmarks",
                status="error",
                duration=time.time() - start_time,
                message=str(e)
            )
    
    def _create_test_data(self, url: str) -> Dict[str, Any]:
        """Create test data for different endpoints"""
        if 'predict' in url:
            return {
                'image_data': 'base64_encoded_test_image_data',
                'model_version': 'v1.0'
            }
        elif 'classify' in url:
            return {
                'features': [0.1, 0.2, 0.3, 0.4, 0.5],
                'threshold': 0.5
            }
        elif 'upload' in url:
            return {
                'file_name': 'test_image.jpg',
                'file_data': 'base64_encoded_file_data'
            }
        else:
            return {}
    
    def generate_test_report(self, output_dir: str = "reports") -> str:
        """Generate comprehensive test report"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Calculate overall statistics
        total_tests = sum(suite.total_tests for suite in self.test_suites.values())
        total_passed = sum(suite.passed_tests for suite in self.test_suites.values())
        total_failed = sum(suite.failed_tests for suite in self.test_suites.values())
        total_skipped = sum(suite.skipped_tests for suite in self.test_suites.values())
        total_errors = sum(suite.error_tests for suite in self.test_suites.values())
        total_duration = sum(suite.total_duration for suite in self.test_suites.values())
        
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0.0
        average_coverage = sum(suite.coverage for suite in self.test_suites.values()) / len(self.test_suites) if self.test_suites else 0.0
        
        # Evaluate quality gates
        quality_gate_results = self.evaluate_quality_gates()
        quality_gates_passed = all(result.passed for result in quality_gate_results)
        
        # Prepare report data
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': total_tests,
                'passed': total_passed,
                'failed': total_failed,
                'skipped': total_skipped,
                'errors': total_errors,
                'success_rate': overall_success_rate,
                'duration': total_duration,
                'coverage': average_coverage
            },
            'test_suites': {
                name: asdict(suite) for name, suite in self.test_suites.items()
            },
            'quality_gates': {
                name: asdict(result) for name, result in zip(
                    [r.gate_name for r in quality_gate_results],
                    quality_gate_results
                )
            },
            'quality_gates_passed': quality_gates_passed,
            'recommendations': self._generate_recommendations()
        }
        
        # Save JSON report
        json_file = output_path / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Generate HTML report
        html_file = output_path / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        html_content = self._generate_html_report(report_data)
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Test report generated: {html_file}")
        return str(html_file)
    
    def _generate_recommendations(self) -> List[str]:
        """Generate improvement recommendations based on test results"""
        recommendations = []
        
        # Analyze test results
        for suite_name, suite in self.test_suites.items():
            if suite.total_tests > 0:
                success_rate = suite.passed_tests / suite.total_tests * 100
                
                if success_rate < 90:
                    recommendations.append(
                        f"Improve test suite '{suite_name}' - success rate is {success_rate:.1f}%"
                    )
                
                if suite.coverage < 80:
                    recommendations.append(
                        f"Increase code coverage for '{suite_name}' - current coverage is {suite.coverage:.1f}%"
                    )
        
        # Analyze quality gates
        quality_gate_results = self.evaluate_quality_gates()
        for result in quality_gate_results:
            if not result.passed:
                recommendations.append(
                    f"Fix quality gate '{result.gate_name}' - {len(result.conditions_failed)} conditions failed"
                )
        
        # General recommendations
        total_tests = sum(suite.total_tests for suite in self.test_suites.values())
        if total_tests < 50:
            recommendations.append("Consider adding more tests to improve code coverage and confidence")
        
        if len(self.test_suites) < 5:
            recommendations.append("Add more test suites (e.g., E2E, contract testing)")
        
        return recommendations
    
    def _generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML test report"""
        template_str = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FlavorSnap Test Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 8px; margin-bottom: 2rem; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .metric-card { background: white; padding: 1.5rem; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2.5rem; font-weight: bold; color: #667eea; }
        .metric-label { font-size: 0.875rem; color: #6c757d; margin-top: 0.5rem; }
        .section { background: white; padding: 1.5rem; margin-bottom: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-passed { color: #28a745; }
        .status-failed { color: #dc3545; }
        .status-skipped { color: #ffc107; }
        .status-error { color: #fd7e14; }
        .test-item { padding: 0.75rem; margin: 0.5rem 0; border-left: 4px solid #e9ecef; background: #f8f9fa; border-radius: 4px; }
        .test-passed { border-left-color: #28a745; }
        .test-failed { border-left-color: #dc3545; }
        .test-skipped { border-left-color: #ffc107; }
        .test-error { border-left-color: #fd7e14; }
        .quality-gate { padding: 1rem; margin: 0.5rem 0; border-radius: 6px; }
        .gate-passed { background: #d4edda; border: 1px solid #c3e6cb; }
        .gate-failed { background: #f8d7da; border: 1px solid #f5c6cb; }
        .chart { height: 400px; margin: 1rem 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>FlavorSnap Test Report</h1>
        <p>Generated on: {{ timestamp }}</p>
        <p>Status: {% if quality_gates_passed %}✅ All Quality Gates Passed{% else %}❌ Quality Gates Failed{% endif %}</p>
    </div>
    
    <div class="summary">
        <div class="metric-card">
            <div class="metric-value">{{ summary.total_tests }}</div>
            <div class="metric-label">Total Tests</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{{ "%.1f"|format(summary.success_rate) }}%</div>
            <div class="metric-label">Success Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{{ "%.1f"|format(summary.coverage) }}%</div>
            <div class="metric-label">Code Coverage</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{{ "%.2f"|format(summary.duration) }}s</div>
            <div class="metric-label">Total Duration</div>
        </div>
    </div>
    
    <div class="section">
        <h2>Test Results Summary</h2>
        <div class="summary">
            <div class="metric-card">
                <div class="metric-value status-passed">{{ summary.passed }}</div>
                <div class="metric-label">Passed</div>
            </div>
            <div class="metric-card">
                <div class="metric-value status-failed">{{ summary.failed }}</div>
                <div class="metric-label">Failed</div>
            </div>
            <div class="metric-card">
                <div class="metric-value status-skipped">{{ summary.skipped }}</div>
                <div class="metric-label">Skipped</div>
            </div>
            <div class="metric-card">
                <div class="metric-value status-error">{{ summary.errors }}</div>
                <div class="metric-label">Errors</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>Quality Gates</h2>
        {% for gate_name, gate_result in quality_gates.items() %}
        <div class="quality-gate {% if gate_result.passed %}gate-passed{% else %}gate-failed{% endif %}">
            <h3>{{ gate_name }} - {% if gate_result.passed %}PASSED{% else %}FAILED{% endif %}</h3>
            <p>Score: {{ "%.1f"|format(gate_result.score) }}%</p>
            {% if gate_result.conditions_failed %}
            <p><strong>Failed Conditions:</strong></p>
            <ul>
                {% for condition in gate_result.conditions_failed %}
                <li>{{ condition }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    <div class="section">
        <h2>Test Suites</h2>
        {% for suite_name, suite_data in test_suites.items() %}
        <div class="section">
            <h3>{{ suite_name }}</h3>
            <p>{{ suite_data.description }}</p>
            <p>Tests: {{ suite_data.passed_tests }}/{{ suite_data.total_tests }} passed</p>
            <p>Coverage: {{ "%.1f"|format(suite_data.coverage) }}%</p>
            <p>Duration: {{ "%.2f"|format(suite_data.total_duration) }}s</p>
        </div>
        {% endfor %}
    </div>
    
    {% if recommendations %}
    <div class="section">
        <h2>Recommendations</h2>
        <ul>
            {% for recommendation in recommendations %}
            <li>{{ recommendation }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}
</body>
</html>
        '''
        
        template = Template(template_str)
        return template.render(**report_data)


# Global test runner instance
test_runner = None


def initialize_test_runner(config: Dict[str, Any]) -> AutomatedTestRunner:
    """Initialize global test runner"""
    global test_runner
    test_runner = AutomatedTestRunner(config)
    return test_runner


def get_test_runner() -> Optional[AutomatedTestRunner]:
    """Get global test runner instance"""
    return test_runner
