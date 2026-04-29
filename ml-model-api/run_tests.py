#!/usr/bin/env python3
"""
Test runner script for FlavorSnap ML API testing framework
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    success = result.returncode == 0
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'} (exit code: {result.returncode})")
    
    return success, result

def run_unit_tests(args):
    """Run unit tests with coverage"""
    cmd = [
        'python', '-m', 'pytest',
        'tests/test_app.py',
        'tests/test_batch_processor.py',
        'tests/test_cache_manager.py',
        '-v',
        '--cov=.',
        '--cov-report=html:reports/coverage',
        '--cov-report=term-missing',
        '--cov-report=xml:reports/coverage.xml',
        '--cov-fail-under=90',
        '--html=reports/unit_test_report.html',
        '--self-contained-html',
        '-m', 'unit'
    ]
    
    if args.verbose:
        cmd.append('-vv')
    
    return run_command(cmd, "Unit Tests with Coverage")

def run_integration_tests(args):
    """Run integration tests"""
    cmd = [
        'python', '-m', 'pytest',
        'tests/test_integration.py',
        '-v',
        '--html=reports/integration_test_report.html',
        '--self-contained-html',
        '-m', 'integration'
    ]
    
    if args.verbose:
        cmd.append('-vv')
    
    return run_command(cmd, "Integration Tests")

def run_performance_tests(args):
    """Run performance tests"""
    cmd = [
        'python', '-m', 'pytest',
        'tests/test_performance.py',
        '-v',
        '--html=reports/performance_test_report.html',
        '--self-contained-html',
        '--benchmark-only',
        '--benchmark-sort=mean',
        '--benchmark-json=reports/benchmark_results.json',
        '-m', 'performance'
    ]
    
    if args.verbose:
        cmd.append('-vv')
    
    return run_command(cmd, "Performance Tests")

def run_security_tests(args):
    """Run security tests"""
    cmd = [
        'python', '-m', 'pytest',
        'tests/test_security.py',
        '-v',
        '--html=reports/security_test_report.html',
        '--self-contained-html',
        '-m', 'security'
    ]
    
    if args.verbose:
        cmd.append('-vv')
    
    return run_command(cmd, "Security Tests")

def run_load_tests(args):
    """Run load tests using Locust"""
    if args.host is None:
        print("Error: --host is required for load tests")
        return False, None
    
    cmd = [
        'locust',
        '-f', 'tests/test_load.py',
        '--host', args.host,
        '--users', str(args.users) if args.users else '100',
        '--spawn-rate', str(args.spawn_rate) if args.spawn_rate else '10',
        '--run-time', args.run_time if args.run_time else '10m',
        '--html', 'reports/load_test_report.html'
    ]
    
    if args.headless:
        cmd.append('--headless')
    
    return run_command(cmd, "Load Tests")

def run_all_tests(args):
    """Run all test suites"""
    results = {}
    
    # Create reports directory
    os.makedirs('reports', exist_ok=True)
    
    # Run unit tests
    success, result = run_unit_tests(args)
    results['unit'] = success
    
    # Run integration tests
    success, result = run_integration_tests(args)
    results['integration'] = success
    
    # Run performance tests
    success, result = run_performance_tests(args)
    results['performance'] = success
    
    # Run security tests
    success, result = run_security_tests(args)
    results['security'] = success
    
    return results

def run_smoke_tests(args):
    """Run quick smoke tests"""
    cmd = [
        'python', '-m', 'pytest',
        'tests/test_app.py::TestApp::test_app_creation',
        'tests/test_app.py::TestApp::test_health_check_success',
        'tests/test_app.py::TestApp::test_predict_endpoint_no_image',
        'tests/test_integration.py::TestAPIIntegration::test_full_prediction_workflow',
        '-v',
        '-m', 'smoke'
    ]
    
    return run_command(cmd, "Smoke Tests")

def generate_test_report(results):
    """Generate comprehensive test report"""
    report = {
        'test_run': {
            'timestamp': str(subprocess.check_output(['date'], text=True).strip()),
            'total_suites': len(results),
            'passed_suites': sum(1 for success in results.values() if success),
            'failed_suites': sum(1 for success in results.values() if not success)
        },
        'suites': {}
    }
    
    for suite_name, success in results.items():
        report['suites'][suite_name] = {
            'status': 'PASSED' if success else 'FAILED',
            'report_file': f'reports/{suite_name}_test_report.html'
        }
    
    # Save report
    with open('reports/test_summary.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    print(f"Total Suites: {report['test_run']['total_suites']}")
    print(f"Passed: {report['test_run']['passed_suites']}")
    print(f"Failed: {report['test_run']['failed_suites']}")
    print(f"\nDetailed report saved to: reports/test_summary.json")
    
    for suite_name, suite_info in report['suites'].items():
        status_symbol = "✓" if suite_info['status'] == 'PASSED' else "✗"
        print(f"{status_symbol} {suite_name.title()}: {suite_info['status']}")
    
    return all(results.values())

def setup_test_environment():
    """Setup test environment"""
    print("Setting up test environment...")
    
    # Create necessary directories
    os.makedirs('reports', exist_ok=True)
    os.makedirs('test_uploads', exist_ok=True)
    
    # Install test dependencies if needed
    try:
        import pytest
        print("✓ pytest is installed")
    except ImportError:
        print("Installing pytest...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pytest'], check=True)
    
    try:
        import pytest_cov
        print("✓ pytest-cov is installed")
    except ImportError:
        print("Installing pytest-cov...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pytest-cov'], check=True)
    
    print("Test environment setup complete!")

def main():
    parser = argparse.ArgumentParser(description='FlavorSnap ML API Test Runner')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--setup', action='store_true', help='Setup test environment')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Unit tests
    unit_parser = subparsers.add_parser('unit', help='Run unit tests')
    
    # Integration tests
    integration_parser = subparsers.add_parser('integration', help='Run integration tests')
    
    # Performance tests
    perf_parser = subparsers.add_parser('performance', help='Run performance tests')
    
    # Security tests
    security_parser = subparsers.add_parser('security', help='Run security tests')
    
    # Load tests
    load_parser = subparsers.add_parser('load', help='Run load tests')
    load_parser.add_argument('--host', required=True, help='Target host for load testing')
    load_parser.add_argument('--users', type=int, help='Number of users')
    load_parser.add_argument('--spawn-rate', type=int, help='Spawn rate')
    load_parser.add_argument('--run-time', help='Run time (e.g., 10m, 1h)')
    load_parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    # All tests
    all_parser = subparsers.add_parser('all', help='Run all tests')
    
    # Smoke tests
    smoke_parser = subparsers.add_parser('smoke', help='Run smoke tests')
    
    args = parser.parse_args()
    
    if args.setup:
        setup_test_environment()
        return
    
    if not args.command:
        parser.print_help()
        return
    
    # Setup environment
    setup_test_environment()
    
    # Run tests based on command
    if args.command == 'unit':
        success, _ = run_unit_tests(args)
        sys.exit(0 if success else 1)
    
    elif args.command == 'integration':
        success, _ = run_integration_tests(args)
        sys.exit(0 if success else 1)
    
    elif args.command == 'performance':
        success, _ = run_performance_tests(args)
        sys.exit(0 if success else 1)
    
    elif args.command == 'security':
        success, _ = run_security_tests(args)
        sys.exit(0 if success else 1)
    
    elif args.command == 'load':
        success, _ = run_load_tests(args)
        sys.exit(0 if success else 1)
    
    elif args.command == 'all':
        results = run_all_tests(args)
        overall_success = generate_test_report(results)
        sys.exit(0 if overall_success else 1)
    
    elif args.command == 'smoke':
        success, _ = run_smoke_tests(args)
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
