"""
API Gateway Demo and Examples
Demonstrates how to use the FlavorSnap API Gateway with routing, load balancing, and middleware
"""

import asyncio
import json
import time
import requests
from typing import Dict, Any

# Import gateway components
from gateway_handlers import APIGateway, Route, HTTPMethod, ServiceEndpoint, create_gateway
from middleware import MiddlewareManager, LoggingMiddleware, RateLimitMiddleware, SecurityMiddleware
from load_balancer import AdvancedLoadBalancer

def demo_basic_gateway():
    """Demo basic gateway setup and usage"""
    print("=== Basic Gateway Demo ===")
    
    # Create gateway configuration
    config = {
        'name': 'FlavorSnap Demo Gateway',
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
    routes = [
        ('models-list', Route('/api/models', HTTPMethod.GET, 'ml-model-api')),
        ('predict', Route('/api/predict', HTTPMethod.POST, 'ml-model-api')),
        ('classes', Route('/api/classes', HTTPMethod.GET, 'ml-model-api')),
    ]
    
    for route_id, route in routes:
        gateway.add_route(route_id, route)
    
    print(f"Gateway created: {gateway.config.name}")
    print(f"Services: {list(gateway.services.keys())}")
    print(f"Routes: {list(gateway.routes.keys())}")
    
    return gateway

def demo_advanced_routing():
    """Demo advanced routing with versioning and middleware"""
    print("\n=== Advanced Routing Demo ===")
    
    config = {
        'name': 'Advanced FlavorSnap Gateway',
        'version': '2.0.0',
        'debug': True,
        'enable_cors': True
    }
    
    gateway = create_gateway(config)
    
    # Add multiple backend services
    services = [
        ServiceEndpoint(
            name='ml-model-api-v1',
            hosts=['localhost'],
            port=5000,
            health_check_path='/health'
        ),
        ServiceEndpoint(
            name='ml-model-api-v2',
            hosts=['localhost'],
            port=5001,
            health_check_path='/health'
        )
    ]
    
    for service in services:
        gateway.add_service(service)
    
    # Add versioned routes
    versioned_routes = [
        ('v1-models', Route('/api/v1/models', HTTPMethod.GET, 'ml-model-api-v1', version='1.0')),
        ('v2-models', Route('/api/v2/models', HTTPMethod.GET, 'ml-model-api-v2', version='2.0')),
        ('v1-predict', Route('/api/v1/predict', HTTPMethod.POST, 'ml-model-api-v1', version='1.0')),
        ('v2-predict', Route('/api/v2/predict', HTTPMethod.POST, 'ml-model-api-v2', version='2.0')),
        # Deprecated route
        ('old-predict', Route('/api/predict', HTTPMethod.POST, 'ml-model-api-v1', 
                             version='1.0', deprecated=True, 
                             deprecation_date='2024-01-01', sunset_date='2024-06-01')),
    ]
    
    for route_id, route in versioned_routes:
        gateway.add_route(route_id, route)
    
    print(f"Advanced gateway with {len(gateway.services)} services and {len(gateway.routes)} routes")
    
    return gateway

def demo_middleware_chains():
    """Demo middleware chains and custom middleware"""
    print("\n=== Middleware Chains Demo ===")
    
    config = {
        'name': 'Middleware Demo Gateway',
        'version': '1.0.0',
        'debug': True
    }
    
    gateway = create_gateway(config)
    
    # Add service
    service = ServiceEndpoint(
        name='ml-model-api',
        hosts=['localhost'],
        port=5000,
        health_check_path='/health'
    )
    gateway.add_service(service)
    
    # Create middleware chains
    gateway.middleware_manager.create_chain('public', ['logging', 'security', 'rate_limit'])
    gateway.middleware_manager.create_chain('authenticated', ['logging', 'security', 'auth', 'rate_limit'])
    gateway.middleware_manager.create_chain('admin', ['logging', 'security', 'auth', 'rate_limit', 'admin_check'])
    
    # Add routes with different middleware chains
    routes = [
        ('public-endpoint', Route('/api/public', HTTPMethod.GET, 'ml-model-api', 
                                 middleware_chain=['public'])),
        ('protected-endpoint', Route('/api/protected', HTTPMethod.GET, 'ml-model-api', 
                                    middleware_chain=['authenticated'], auth_required=True)),
        ('admin-endpoint', Route('/api/admin', HTTPMethod.GET, 'ml-model-api', 
                               middleware_chain=['admin'], auth_required=True)),
    ]
    
    for route_id, route in routes:
        gateway.add_route(route_id, route)
    
    print(f"Middleware chains: {list(gateway.middleware_manager.middleware_chains.keys())}")
    print(f"Middleware registry: {list(gateway.middleware_manager.middleware_registry.keys())}")
    
    return gateway

def demo_load_balancing():
    """Demo load balancing across multiple backends"""
    print("\n=== Load Balancing Demo ===")
    
    config = {
        'name': 'Load Balanced Gateway',
        'version': '1.0.0',
        'debug': True
    }
    
    gateway = create_gateway(config)
    
    # Add service with multiple backends
    service = ServiceEndpoint(
        name='ml-model-cluster',
        hosts=['backend-1', 'backend-2', 'backend-3'],
        port=5000,
        health_check_path='/health',
        weight=1,
        max_connections=150
    )
    gateway.add_service(service)
    
    # Add routes
    routes = [
        ('predict-cluster', Route('/api/predict', HTTPMethod.POST, 'ml-model-cluster')),
        ('models-cluster', Route('/api/models', HTTPMethod.GET, 'ml-model-cluster')),
    ]
    
    for route_id, route in routes:
        gateway.add_route(route_id, route)
    
    # Show load balancer stats
    if 'ml-model-cluster' in gateway.load_balancers:
        lb = gateway.load_balancers['ml-model-cluster']
        stats = lb.get_backend_stats()
        print(f"Load balancer stats: {json.dumps(stats, indent=2)}")
    
    return gateway

def demo_monitoring():
    """Demo gateway monitoring and metrics"""
    print("\n=== Monitoring Demo ===")
    
    config = {
        'name': 'Monitored Gateway',
        'version': '1.0.0',
        'debug': True
    }
    
    gateway = create_gateway(config)
    
    # Add service and routes
    service = ServiceEndpoint(
        name='monitored-api',
        hosts=['localhost'],
        port=5000,
        health_check_path='/health'
    )
    gateway.add_service(service)
    
    routes = [
        ('monitored-predict', Route('/api/predict', HTTPMethod.POST, 'monitored-api')),
        ('monitored-models', Route('/api/models', HTTPMethod.GET, 'monitored-api')),
    ]
    
    for route_id, route in routes:
        gateway.add_route(route_id, route)
    
    # Simulate some requests to generate metrics
    print("Simulating requests for monitoring...")
    for i in range(10):
        # Simulate request processing
        start_time = time.time()
        time.sleep(0.1)  # Simulate processing time
        duration = time.time() - start_time
        
        # Add to metrics
        route_key = "POST /api/predict"
        gateway.request_metrics[route_key].append(duration)
        
        if i % 3 == 0:  # Simulate some errors
            gateway.error_count += 1
            gateway.error_metrics["500"] += 1
    
    # Show metrics
    stats = gateway.get_stats()
    print(f"Gateway stats: {json.dumps(stats, indent=2)}")
    
    return gateway

def demo_gateway_api():
    """Demo gateway management API endpoints"""
    print("\n=== Gateway API Demo ===")
    
    config = {
        'name': 'API Demo Gateway',
        'version': '1.0.0',
        'debug': True
    }
    
    gateway = create_gateway(config)
    
    # Add service and routes
    service = ServiceEndpoint(
        name='demo-api',
        hosts=['localhost'],
        port=5000,
        health_check_path='/health'
    )
    gateway.add_service(service)
    
    routes = [
        ('demo-predict', Route('/api/predict', HTTPMethod.POST, 'demo-api')),
        ('demo-models', Route('/api/models', HTTPMethod.GET, 'demo-api')),
    ]
    
    for route_id, route in routes:
        gateway.add_route(route_id, route)
    
    print("Gateway management API endpoints:")
    print("GET  /gateway/health - Gateway health check")
    print("GET  /gateway/config - Gateway configuration")
    print("GET  /gateway/routes - List all routes")
    print("POST /gateway/routes - Add new route")
    print("DELETE /gateway/routes/<id> - Remove route")
    print("GET  /gateway/services - List all services")
    print("POST /gateway/services - Add new service")
    print("DELETE /gateway/services/<name> - Remove service")
    print("GET  /gateway/metrics - Gateway metrics")
    print("GET  /gateway/versions - API version information")
    print("GET  /gateway/monitoring/health - Detailed health check")
    print("GET  /gateway/monitoring/metrics - Detailed metrics")
    print("GET  /gateway/monitoring/alerts - Monitoring alerts")
    
    return gateway

def run_all_demos():
    """Run all gateway demos"""
    print("FlavorSnap API Gateway Demo Suite")
    print("=" * 50)
    
    try:
        # Run all demos
        demo_basic_gateway()
        demo_advanced_routing()
        demo_middleware_chains()
        demo_load_balancing()
        demo_monitoring()
        demo_gateway_api()
        
        print("\n" + "=" * 50)
        print("All demos completed successfully!")
        print("To start the gateway server, use:")
        print("python gateway_demo.py --server")
        
    except Exception as e:
        print(f"Demo error: {e}")
        import traceback
        traceback.print_exc()

def start_gateway_server():
    """Start the gateway server for testing"""
    print("Starting FlavorSnap API Gateway Server...")
    
    config = {
        'name': 'FlavorSnap Production Gateway',
        'version': '1.0.0',
        'debug': False,
        'enable_cors': True,
        'cors_origins': ['http://localhost:3000', 'https://flavorsnap.com']
    }
    
    gateway = create_gateway(config)
    
    # Add ML model API service
    service = ServiceEndpoint(
        name='ml-model-api',
        hosts=['localhost'],
        port=5000,
        health_check_path='/health',
        max_connections=200
    )
    gateway.add_service(service)
    
    # Add comprehensive routes
    routes = [
        # Model management
        ('models-list', Route('/api/models', HTTPMethod.GET, 'ml-model-api')),
        ('models-detail', Route('/api/models/<version>', HTTPMethod.GET, 'ml-model-api')),
        ('models-register', Route('/api/models/register', HTTPMethod.POST, 'ml-model-api')),
        ('models-activate', Route('/api/models/<version>/activate', HTTPMethod.POST, 'ml-model-api')),
        
        # Prediction endpoints
        ('predict', Route('/api/predict', HTTPMethod.POST, 'ml-model-api')),
        ('predict-v1', Route('/api/v1/predict', HTTPMethod.POST, 'ml-model-api', version='1.0')),
        ('predict-v2', Route('/api/v2/predict', HTTPMethod.POST, 'ml-model-api', version='2.0')),
        
        # Utility endpoints
        ('classes', Route('/api/classes', HTTPMethod.GET, 'ml-model-api')),
        ('history', Route('/api/history', HTTPMethod.GET, 'ml-model-api')),
        ('health', Route('/health', HTTPMethod.GET, 'ml-model-api')),
        
        # Admin endpoints (with authentication)
        ('admin-metrics', Route('/api/admin/metrics', HTTPMethod.GET, 'ml-model-api', 
                              auth_required=True, middleware_chain=['authenticated'])),
    ]
    
    for route_id, route in routes:
        gateway.add_route(route_id, route)
    
    print(f"Gateway server starting with {len(gateway.services)} services and {len(gateway.routes)} routes")
    print("Available endpoints:")
    print("- Gateway Management: /gateway/*")
    print("- ML Model API: /api/*")
    print("- Health Check: /health")
    print("\nStarting server on http://localhost:8080")
    
    # Start the gateway server
    gateway.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        start_gateway_server()
    else:
        run_all_demos()
