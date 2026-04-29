# FlavorSnap API Gateway

A comprehensive API gateway implementation with routing, load balancing, middleware management, monitoring, and security features for the FlavorSnap ML Model API.

## Features

### Core Gateway Features
- **API Routing**: Intelligent request routing with support for exact, prefix, regex, and wildcard matching
- **Load Balancing**: Advanced load balancing with multiple algorithms (round-robin, least connections, weighted, adaptive)
- **Middleware Management**: Configurable middleware chains for request/response processing
- **API Versioning**: Built-in support for API versioning with deprecation warnings
- **Monitoring**: Comprehensive metrics, health checks, and alerting system
- **Security Policies**: Integrated security middleware with rate limiting and attack detection

### Advanced Features
- **Request Transformation**: Automatic request/response transformation and enrichment
- **Health Checking**: Continuous backend health monitoring with automatic failover
- **Metrics Collection**: Prometheus-compatible metrics and detailed performance analytics
- **CORS Support**: Configurable Cross-Origin Resource Sharing
- **Session Affinity**: IP-based session affinity for stateful applications

## Architecture

### Components

1. **gateway_handlers.py**: Main gateway implementation with routing logic and Flask integration
2. **middleware.py**: Middleware management system with built-in middleware components
3. **load_balancer.py**: Advanced load balancer with health checking and failover
4. **api_endpoints.py**: Gateway management API endpoints

### Data Flow

```
Client Request → Gateway → Middleware Chain → Load Balancer → Backend Service
                    ↓
                 Metrics & Monitoring
```

## Quick Start

### Basic Setup

```python
from gateway_handlers import create_gateway, Route, HTTPMethod, ServiceEndpoint

# Create gateway configuration
config = {
    'name': 'FlavorSnap Gateway',
    'version': '1.0.0',
    'debug': True,
    'enable_cors': True,
    'cors_origins': ['*']
}

# Create gateway
gateway = create_gateway(config)

# Add backend service
service = ServiceEndpoint(
    name='ml-model-api',
    hosts=['localhost'],
    port=5000,
    health_check_path='/health'
)
gateway.add_service(service)

# Add routes
gateway.add_route('models', Route(
    path='/api/models',
    method=HTTPMethod.GET,
    backend_service='ml-model-api'
))

# Start gateway
gateway.run(host='0.0.0.0', port=8080)
```

### Running the Demo

```bash
# Run all demos
python gateway_demo.py

# Start gateway server
python gateway_demo.py --server
```

## Configuration

### Gateway Configuration

```python
config = {
    'name': 'My Gateway',                    # Gateway name
    'version': '1.0.0',                      # Gateway version
    'debug': False,                          # Debug mode
    'request_timeout': 30,                   # Request timeout in seconds
    'max_request_size': 10485760,            # Max request size (10MB)
    'enable_cors': True,                     # Enable CORS
    'cors_origins': ['*'],                   # Allowed origins
    'enable_metrics': True,                  # Enable metrics collection
    'enable_tracing': False                  # Enable request tracing
}
```

### Service Configuration

```python
service = ServiceEndpoint(
    name='my-service',                       # Service name
    hosts=['host1', 'host2'],                # Backend hosts
    port=8080,                               # Backend port
    protocol='http',                         # Protocol (http/https)
    health_check_path='/health',              # Health check endpoint
    weight=1,                                # Load balancer weight
    max_connections=100,                     # Max connections per backend
    timeout=30                               # Request timeout
)
```

### Route Configuration

```python
route = Route(
    path='/api/users/*',                     # Route path
    method=HTTPMethod.GET,                   # HTTP method
    backend_service='user-service',          # Target service
    match_type=RouteMatchType.WILDCARD,      # Path matching type
    version='1.0',                            # API version
    middleware_chain=['logging', 'auth'],    # Middleware chain
    rate_limit={'requests': 100, 'window': 60}, # Rate limiting
    auth_required=True,                       # Authentication required
    timeout=30,                              # Request timeout
    retries=3,                               # Retry attempts
    deprecated=False,                         # Deprecation status
    deprecation_date=None,                    # Deprecation date
    sunset_date=None                          # Sunset date
)
```

## Middleware

### Built-in Middleware

1. **LoggingMiddleware**: Request/response logging
2. **RateLimitMiddleware**: Token bucket rate limiting
3. **SecurityMiddleware**: Attack detection and prevention
4. **AuthenticationMiddleware**: JWT-based authentication
5. **RequestTransformationMiddleware**: Request/response transformation

### Custom Middleware

```python
from middleware import Middleware, MiddlewareContext

class CustomMiddleware(Middleware):
    def __init__(self):
        super().__init__("custom", MiddlewareType.CUSTOM, priority=50)
    
    def process_request(self, context: MiddlewareContext):
        # Process incoming request
        # Return error response if needed, None otherwise
        return None
    
    def process_response(self, context: MiddlewareContext):
        # Process outgoing response
        # Return modified response if needed, None otherwise
        return None

# Register custom middleware
gateway.middleware_manager.register_middleware('custom', CustomMiddleware())
```

### Middleware Chains

```python
# Create middleware chains
gateway.middleware_manager.create_chain('public', ['logging', 'security', 'rate_limit'])
gateway.middleware_manager.create_chain('authenticated', ['logging', 'security', 'auth', 'rate_limit'])
gateway.middleware_manager.create_chain('admin', ['logging', 'security', 'auth', 'rate_limit', 'admin_check'])

# Set global middleware chain
gateway.middleware_manager.set_global_chain(['logging', 'security'])
```

## Load Balancing

### Algorithms

1. **Round Robin**: Simple round-robin distribution
2. **Least Connections**: Route to backend with fewest active connections
3. **Weighted Round Robin**: Weighted distribution based on backend capacity
4. **IP Hash**: Session affinity based on client IP
5. **Least Response Time**: Route to fastest responding backend
6. **Adaptive**: Intelligent routing based on multiple factors

### Load Balancer Configuration

```python
load_balancer_config = {
    'algorithm': 'least_connections',         # Load balancing algorithm
    'health_check_interval': 30,              # Health check interval (seconds)
    'health_check_timeout': 5,                # Health check timeout (seconds)
    'health_check_retries': 3,                # Health check retry attempts
    'failover_enabled': True,                 # Enable automatic failover
    'session_affinity': False,                # Enable session affinity
    'request_timeout': 300,                   # Request timeout (seconds)
    'ssl_verify': True,                       # SSL certificate verification
    'backends': [                             # Backend servers
        {
            'host': 'backend-1',
            'port': 8080,
            'weight': 1,
            'max_connections': 100
        },
        {
            'host': 'backend-2',
            'port': 8080,
            'weight': 2,
            'max_connections': 150
        }
    ]
}
```

## API Versioning

### Version Support

The gateway supports multiple API versions simultaneously:

```python
# Add versioned routes
gateway.add_route('v1-users', Route('/api/v1/users', HTTPMethod.GET, 'user-service', version='1.0'))
gateway.add_route('v2-users', Route('/api/v2/users', HTTPMethod.GET, 'user-service', version='2.0'))

# Deprecated route
gateway.add_route('old-users', Route(
    path='/api/users',
    method=HTTPMethod.GET,
    backend_service='user-service',
    version='1.0',
    deprecated=True,
    deprecation_date='2024-01-01',
    sunset_date='2024-06-01'
))
```

### Version Headers

The gateway automatically adds version information to responses:

```
X-API-Version: 1.0
X-API-Supported-Versions: 1.0,2.0
X-API-Deprecated: true
X-API-Deprecation-Date: 2024-01-01
X-API-Sunset-Date: 2024-06-01
```

## Monitoring

### Health Checks

```bash
# Basic health check
GET /gateway/health

# Detailed health check with metrics
GET /gateway/monitoring/health
```

### Metrics

```bash
# Basic metrics
GET /gateway/metrics

# Detailed metrics
GET /gateway/monitoring/metrics
```

### Alerts

```bash
# List alerts
GET /gateway/monitoring/alerts

# Create manual alert
POST /gateway/monitoring/alerts
{
    "type": "manual",
    "severity": "warning",
    "message": "Custom alert message",
    "source": "admin"
}

# Resolve alert
POST /gateway/monitoring/alerts/{alert_id}/resolve
```

### Performance Thresholds

```python
gateway.performance_thresholds = {
    'response_time_warning': 1.0,          # Response time warning (seconds)
    'response_time_critical': 5.0,          # Response time critical (seconds)
    'error_rate_warning': 0.05,             # Error rate warning (5%)
    'error_rate_critical': 0.10,            # Error rate critical (10%)
    'memory_usage_warning': 0.80,           # Memory usage warning (80%)
    'memory_usage_critical': 0.90            # Memory usage critical (90%)
}
```

## Security

### Rate Limiting

```python
# Global rate limiting
rate_limit_middleware = RateLimitMiddleware(
    default_limit=100,                       # Requests per window
    default_window=60                        # Window size in seconds
)

# Per-route rate limiting
route = Route(
    path='/api/sensitive',
    method=HTTPMethod.POST,
    backend_service='api-service',
    rate_limit={'requests': 10, 'window': 60}  # 10 requests per minute
)
```

### Security Policies

The SecurityMiddleware provides protection against:

- SQL Injection attacks
- Cross-Site Scripting (XSS)
- Path Traversal attacks
- Malicious headers

```python
security_middleware = SecurityMiddleware()
gateway.middleware_manager.register_middleware('security', security_middleware)
```

### Authentication

```python
# JWT authentication
auth_middleware = AuthenticationMiddleware(
    jwt_secret='your-secret-key',
    required_paths=['/api/admin/*', '/api/protected/*']
)
gateway.middleware_manager.register_middleware('auth', auth_middleware)
```

## Management API

### Gateway Management

```bash
# Get gateway configuration
GET /gateway/config

# List routes
GET /gateway/routes

# Add route
POST /gateway/routes
{
    "path": "/api/new-endpoint",
    "method": "GET",
    "backend_service": "api-service",
    "version": "1.0",
    "middleware_chain": ["logging", "security"]
}

# Remove route
DELETE /gateway/routes/{route_id}
```

### Service Management

```bash
# List services
GET /gateway/services

# Add service
POST /gateway/services
{
    "name": "new-service",
    "hosts": ["host1", "host2"],
    "port": 8080,
    "protocol": "http",
    "health_check_path": "/health"
}

# Remove service
DELETE /gateway/services/{service_name}
```

## Integration with Flask Apps

### Easy Integration

```python
from flask import Flask
from api_endpoints import create_gateway_integration

app = Flask(__name__)

# Create gateway integration
gateway = create_gateway_integration(app)

# Register all endpoints (including gateway endpoints)
from api_endpoints import register_all_endpoints
register_all_endpoints(app, model_registry, ab_test_manager, deployment_manager, model_validator)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### Gateway-First Architecture

For gateway-first architecture, run the gateway separately:

```python
# gateway_server.py
from gateway_demo import start_gateway_server

if __name__ == '__main__':
    start_gateway_server()
```

Then route all traffic through the gateway at port 8080.

## Performance Considerations

### Optimization Tips

1. **Connection Pooling**: Enable connection pooling for backend services
2. **Health Check Tuning**: Adjust health check intervals based on backend requirements
3. **Middleware Order**: Place lightweight middleware first in the chain
4. **Rate Limiting**: Use appropriate rate limits to prevent abuse
5. **Monitoring**: Monitor key metrics to identify bottlenecks

### Scaling

- **Horizontal Scaling**: Deploy multiple gateway instances behind a load balancer
- **Vertical Scaling**: Increase memory and CPU resources for high-throughput scenarios
- **Backend Scaling**: Add more backend services to handle increased load

## Troubleshooting

### Common Issues

1. **Backend Health Failures**: Check backend service health endpoints
2. **High Response Times**: Monitor backend performance and network latency
3. **Rate Limiting**: Adjust rate limits based on traffic patterns
4. **Memory Usage**: Monitor request metrics and adjust connection limits

### Debug Mode

Enable debug mode for detailed logging:

```python
config = {
    'name': 'Debug Gateway',
    'version': '1.0.0',
    'debug': True
}
```

### Logs

Monitor gateway logs for troubleshooting:

```bash
# View gateway logs
tail -f /var/log/gateway.log

# View error logs
grep ERROR /var/log/gateway.log
```

## Contributing

### Development Setup

```bash
# Clone repository
git clone https://github.com/gbengaeben/flavorsnap.git
cd flavorsnap/ml-model-api

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Run gateway demo
python gateway_demo.py
```

### Code Style

- Follow PEP 8 style guidelines
- Add type hints for all functions
- Include comprehensive docstrings
- Write unit tests for new features

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Create an issue on GitHub
- Check the documentation
- Review the demo examples
- Monitor gateway health endpoints
