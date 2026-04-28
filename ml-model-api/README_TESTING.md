# FlavorSnap ML API Testing Framework

This document provides comprehensive information about the testing framework implemented for the FlavorSnap ML API project.

## Overview

The testing framework includes:
- **Unit Tests** (>90% coverage requirement)
- **Integration Tests** for API endpoints
- **Performance Testing** with benchmarks
- **Load Testing** with Locust
- **Security Testing** for vulnerability detection
- **Automated Test Reporting** with HTML and JSON outputs

## Test Structure

```
ml-model-api/
├── tests/
│   ├── __init__.py
│   ├── test_app.py              # Unit tests for main Flask app
│   ├── test_batch_processor.py  # Unit tests for batch processor
│   ├── test_cache_manager.py    # Unit tests for cache manager
│   ├── test_integration.py      # Integration tests
│   ├── test_performance.py      # Performance benchmarks
│   ├── test_security.py         # Security vulnerability tests
│   └── test_load.py             # Load testing with Locust
├── conftest.py                  # Pytest configuration and fixtures
├── pytest.ini                  # Pytest settings
├── requirements-dev.txt         # Testing dependencies
└── run_tests.py                 # Test runner script
```

## Installation

Install testing dependencies:

```bash
pip install -r requirements-dev.txt
```

## Running Tests

### Using the Test Runner Script

The `run_tests.py` script provides a convenient interface to run different test suites:

```bash
# Setup test environment
python run_tests.py --setup

# Run all tests
python run_tests.py all

# Run specific test suites
python run_tests.py unit
python run_tests.py integration
python run_tests.py performance
python run_tests.py security
python run_tests.py smoke

# Run load tests (requires target host)
python run_tests.py load --host http://localhost:5000 --users 100 --spawn-rate 10
```

### Using Pytest Directly

```bash
# Run all tests with coverage
pytest --cov=. --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m performance
pytest -m security

# Run with verbose output
pytest -v -vv

# Generate HTML report
pytest --html=reports/test_report.html --self-contained-html
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)

Unit tests focus on individual components:

- **Flask App Tests**: Endpoint functionality, error handling, request validation
- **Batch Processor Tests**: Task submission, priority handling, worker management
- **Cache Manager Tests**: Caching logic, eviction policies, distributed cache

**Coverage Requirement**: >90%

### Integration Tests (`@pytest.mark.integration`)

Integration tests verify component interactions:

- Complete prediction workflows
- Cache integration
- Queue monitoring integration
- Configuration management
- Error recovery scenarios

### Performance Tests (`@pytest.mark.performance`)

Performance tests ensure system responsiveness:

- Response time benchmarks
- Concurrent request handling
- Memory usage stability
- Cache performance impact
- Throughput measurements

### Security Tests (`@pytest.mark.security`)

Security tests identify vulnerabilities:

- Input validation (SQL injection, XSS, path traversal)
- File upload security
- Authentication and authorization
- Rate limiting
- Data exfiltration prevention
- Security headers validation

### Load Tests (`@pytest.mark.load`)

Load tests simulate real-world usage patterns:

- **Light Load**: 10 users, 5 minutes
- **Medium Load**: 50 users, 10 minutes  
- **Heavy Load**: 200 users, 15 minutes
- **Stress Test**: 500 users, 5 minutes
- **Spike Test**: 1000 users, 2 minutes
- **Soak Test**: 100 users, 1 hour

## Configuration

### Pytest Configuration (`pytest.ini`)

Key settings:
- Coverage threshold: 90%
- HTML reports enabled
- Benchmarking enabled
- Timeout: 300 seconds
- Async mode: auto

### Test Fixtures (`conftest.py`)

Available fixtures:
- `test_client`: Flask test client
- `sample_image`: Test image data
- `mock_*`: Various mock objects
- `temp_*`: Temporary directories and files

## Reports

Test reports are generated in the `reports/` directory:

- `unit_test_report.html`: Unit test results
- `integration_test_report.html`: Integration test results
- `performance_test_report.html`: Performance benchmarks
- `security_test_report.html`: Security test results
- `load_test_report.html`: Load test results
- `coverage/`: HTML coverage report
- `test_summary.json`: Overall test summary

## Performance Benchmarks

### Response Time Targets
- **Health Check**: < 100ms (average), < 200ms (95th percentile)
- **Prediction**: < 1.0s (average), < 2.0s (95th percentile)
- **Queue Status**: < 500ms (average)

### Throughput Targets
- **Minimum**: 100 requests/second
- **Target**: 500 requests/second
- **Peak**: 1000+ requests/second

### Success Rate Targets
- **Normal Load**: > 99%
- **Heavy Load**: > 95%
- **Stress Test**: > 80%

## Security Test Coverage

### Input Validation
- SQL injection attempts
- XSS payload detection
- Path traversal attacks
- Command injection attempts
- Unicode-based attacks

### File Upload Security
- Malicious file detection
- File size validation
- MIME type spoofing prevention
- Filename sanitization

### Authentication & Authorization
- Token validation
- Session hijacking prevention
- Missing authentication handling

### Rate Limiting
- Brute force protection
- DoS attack simulation

## Load Testing with Locust

### User Types

1. **FlavorSnapUser**: Standard user behavior
2. **HighVolumeUser**: High-frequency requests
3. **QueueUser**: Queue-focused operations
4. **CacheUser**: Cache performance testing

### Running Locust Tests

```bash
# Web UI mode
locust -f tests/test_load.py --host http://localhost:5000

# Headless mode
locust -f tests/test_load.py --headless --users 100 --spawn-rate 10 --run-time 10m --host http://localhost:5000

# Generate HTML report
locust -f tests/test_load.py --headless --users 100 --spawn-rate 10 --run-time 10m --host http://localhost:5000 --html reports/load_test_report.html
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    - name: Run tests
      run: python run_tests.py all
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

## Best Practices

### Writing Tests

1. **Use descriptive test names** that explain what is being tested
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **Use fixtures** for common setup code
4. **Mock external dependencies** to isolate units
5. **Test edge cases** and error conditions
6. **Use parameterized tests** for multiple scenarios

### Test Data Management

1. **Use factories** for test data generation
2. **Clean up test data** after each test
3. **Use deterministic data** for reproducible tests
4. **Avoid hardcoding values** in tests

### Performance Testing

1. **Establish baselines** before optimization
2. **Test realistic scenarios** based on usage patterns
3. **Monitor system resources** during tests
4. **Use appropriate sample sizes** for statistical significance

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Database Connection**: Check test database configuration
3. **Port Conflicts**: Use different ports for parallel tests
4. **Memory Issues**: Increase test timeout or reduce test data size
5. **Coverage Failures**: Check for untested code paths

### Debugging Tests

```bash
# Run with debugging
pytest -s -v --pdb

# Stop on first failure
pytest -x

# Run specific test
pytest tests/test_app.py::TestApp::test_health_check_success

# Show local variables on failure
pytest -l
```

## Contributing

When adding new tests:

1. **Follow existing patterns** and conventions
2. **Add appropriate markers** (unit, integration, etc.)
3. **Update documentation** for new test types
4. **Ensure coverage >90%** for new code
5. **Add performance benchmarks** for critical paths

## Future Enhancements

Planned improvements to the testing framework:

1. **Visual Regression Testing** for UI components
2. **Contract Testing** for API compatibility
3. **Chaos Engineering** for resilience testing
4. **A/B Testing Framework** for feature testing
5. **Automated Performance Regression Detection**

## Support

For questions or issues with the testing framework:

1. Check existing test documentation
2. Review test output logs
3. Consult pytest documentation
4. Create an issue with detailed information

---

This testing framework provides comprehensive coverage for the FlavorSnap ML API, ensuring reliability, performance, and security of the application.
