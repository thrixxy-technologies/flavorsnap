"""
API Gateway Handlers
Main gateway implementation with routing, middleware management, and request handling
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from urllib.parse import urlparse, parse_qs
import re
from functools import wraps
from collections import defaultdict
import psutil

from flask import Flask, request, jsonify, Response
from load_balancer import AdvancedLoadBalancer
from middleware import MiddlewareManager, MiddlewareContext

logger = logging.getLogger(__name__)

class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

class RouteMatchType(Enum):
    EXACT = "exact"
    PREFIX = "prefix"
    REGEX = "regex"
    WILDCARD = "wildcard"

@dataclass
class Route:
    """API route configuration"""
    path: str
    method: HTTPMethod
    backend_service: str
    match_type: RouteMatchType = RouteMatchType.EXACT
    version: Optional[str] = None
    middleware_chain: List[str] = None
    rate_limit: Optional[Dict[str, Any]] = None
    auth_required: bool = False
    timeout: int = 30
    retries: int = 3
    load_balancing_algorithm: str = "least_connections"
    deprecated: bool = False
    deprecation_date: Optional[str] = None
    sunset_date: Optional[str] = None
    
    def __post_init__(self):
        if self.middleware_chain is None:
            self.middleware_chain = []

@dataclass
class ServiceEndpoint:
    """Backend service endpoint configuration"""
    name: str
    hosts: List[str]
    port: int
    protocol: str = "http"
    health_check_path: str = "/health"
    weight: int = 1
    max_connections: int = 100
    timeout: int = 30

@dataclass
class GatewayConfig:
    """Gateway configuration"""
    name: str
    version: str = "1.0.0"
    debug: bool = False
    request_timeout: int = 30
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    enable_cors: bool = True
    enable_metrics: bool = True
    enable_tracing: bool = False
    cors_origins: List[str] = None
    rate_limiting: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]
        if self.rate_limiting is None:
            self.rate_limiting = {}

class APIGateway:
    """Main API Gateway implementation"""
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.routes: Dict[str, Route] = {}
        self.services: Dict[str, ServiceEndpoint] = {}
        self.load_balancers: Dict[str, AdvancedLoadBalancer] = {}
        self.middleware_manager = MiddlewareManager()
        
        # Request tracking
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        
        # Metrics
        self.request_count = 0
        self.error_count = 0
        self.start_time = time.time()
        
        # Enhanced monitoring
        self.request_metrics: Dict[str, List[float]] = defaultdict(list)  # response times by route
        self.error_metrics: Dict[str, int] = defaultdict(int)  # error counts by type
        self.service_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)  # per-service metrics
        self.alerts: List[Dict[str, Any]] = []
        self.performance_thresholds = {
            'response_time_warning': 1.0,  # seconds
            'response_time_critical': 5.0,  # seconds
            'error_rate_warning': 0.05,  # 5%
            'error_rate_critical': 0.10,  # 10%
            'memory_usage_warning': 0.80,  # 80%
            'memory_usage_critical': 0.90   # 90%
        }
        
        # Initialize Flask app
        self.app = Flask(__name__)
        self.app.config.update(asdict(config))
        
        # Setup routes
        self._setup_gateway_routes()
        self._setup_cors()
        
        logger.info(f"API Gateway '{config.name}' initialized")
    
    def _setup_gateway_routes(self):
        """Setup gateway management routes"""
        
        @self.app.route('/gateway/health', methods=['GET'])
        def health_check():
            """Gateway health check"""
            uptime = time.time() - self.start_time
            return jsonify({
                'status': 'healthy',
                'gateway': self.config.name,
                'version': self.config.version,
                'uptime': uptime,
                'active_requests': len(self.active_requests),
                'total_requests': self.request_count,
                'error_count': self.error_count,
                'services': list(self.services.keys()),
                'routes': len(self.routes)
            })
        
        @self.app.route('/gateway/routes', methods=['GET'])
        def list_routes():
            """List all configured routes"""
            routes_data = []
            for route_id, route in self.routes.items():
                route_data = asdict(route)
                route_data['id'] = route_id
                routes_data.append(route_data)
            
            return jsonify({
                'routes': routes_data,
                'total': len(routes_data)
            })
        
        @self.app.route('/gateway/services', methods=['GET'])
        def list_services():
            """List all backend services"""
            services_data = []
            for name, service in self.services.items():
                service_data = asdict(service)
                # Add load balancer stats
                if name in self.load_balancers:
                    service_data['load_balancer_stats'] = self.load_balancers[name].get_backend_stats()
                services_data.append(service_data)
            
            return jsonify({
                'services': services_data,
                'total': len(services_data)
            })
        
        @self.app.route('/gateway/metrics', methods=['GET'])
        def get_metrics():
            """Get gateway metrics"""
            uptime = time.time() - self.start_time
            return jsonify({
                'uptime': uptime,
                'total_requests': self.request_count,
                'error_count': self.error_count,
                'error_rate': self.error_count / max(self.request_count, 1),
                'active_requests': len(self.active_requests),
                'services': len(self.services),
                'routes': len(self.routes),
                'middleware_count': len(self.middleware_manager.middleware_registry)
            })
        
        @self.app.route('/gateway/config', methods=['GET'])
        def get_config():
            """Get gateway configuration (sans sensitive data)"""
            return jsonify(asdict(self.config))
        
        @self.app.route('/gateway/versions', methods=['GET'])
        def list_api_versions():
            """List all available API versions"""
            versions = {}
            for route_id, route in self.routes.items():
                if route.version:
                    if route.version not in versions:
                        versions[route.version] = {
                            'routes': [],
                            'deprecated': False,
                            'deprecation_date': None,
                            'sunset_date': None
                        }
                    
                    versions[route.version]['routes'].append({
                        'id': route_id,
                        'method': route.method.value,
                        'path': route.path,
                        'service': route.backend_service,
                        'deprecated': route.deprecated,
                        'deprecation_date': route.deprecation_date,
                        'sunset_date': route.sunset_date
                    })
                    
                    if route.deprecated:
                        versions[route.version]['deprecated'] = True
                        if route.deprecation_date:
                            versions[route.version]['deprecation_date'] = route.deprecation_date
                        if route.sunset_date:
                            versions[route.version]['sunset_date'] = route.sunset_date
            
            return jsonify({
                'versions': versions,
                'current_version': self.config.version,
                'total_versions': len(versions)
            })
        
        @self.app.route('/gateway/monitoring/health', methods=['GET'])
        def detailed_health_check():
            """Detailed health check with monitoring data"""
            uptime = time.time() - self.start_time
            memory_percent = psutil.virtual_memory().percent
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Calculate error rate
            error_rate = self.error_count / max(self.request_count, 1)
            
            # Get average response times
            avg_response_times = {}
            for route_id, times in self.request_metrics.items():
                if times:
                    avg_response_times[route_id] = sum(times) / len(times)
            
            health_status = "healthy"
            issues = []
            
            # Check thresholds
            if error_rate > self.performance_thresholds['error_rate_critical']:
                health_status = "critical"
                issues.append(f"High error rate: {error_rate:.2%}")
            elif error_rate > self.performance_thresholds['error_rate_warning']:
                health_status = "warning"
                issues.append(f"Elevated error rate: {error_rate:.2%}")
            
            if memory_percent > self.performance_thresholds['memory_usage_critical']:
                health_status = "critical"
                issues.append(f"High memory usage: {memory_percent:.1f}%")
            elif memory_percent > self.performance_thresholds['memory_usage_warning']:
                health_status = "warning"
                issues.append(f"Elevated memory usage: {memory_percent:.1f}%")
            
            return jsonify({
                'status': health_status,
                'uptime': uptime,
                'system': {
                    'memory_usage_percent': memory_percent,
                    'cpu_usage_percent': cpu_percent,
                    'active_connections': len(self.active_requests)
                },
                'performance': {
                    'total_requests': self.request_count,
                    'error_count': self.error_count,
                    'error_rate': error_rate,
                    'avg_response_times': avg_response_times
                },
                'services': {
                    'total_services': len(self.services),
                    'healthy_services': sum(1 for lb in self.load_balancers.values() 
                                           if len(lb.get_healthy_backends()) > 0)
                },
                'issues': issues,
                'alerts': self.alerts[-10:] if self.alerts else []  # Last 10 alerts
            })
        
        @self.app.route('/gateway/monitoring/metrics', methods=['GET'])
        def detailed_metrics():
            """Get detailed performance metrics"""
            uptime = time.time() - self.start_time
            
            # Request metrics by route
            route_metrics = {}
            for route_id, times in self.request_metrics.items():
                if times:
                    route_metrics[route_id] = {
                        'request_count': len(times),
                        'avg_response_time': sum(times) / len(times),
                        'min_response_time': min(times),
                        'max_response_time': max(times),
                        'p95_response_time': sorted(times)[int(len(times) * 0.95)] if len(times) > 20 else max(times)
                    }
            
            # Error metrics
            total_errors = sum(self.error_metrics.values())
            error_breakdown = dict(self.error_metrics)
            
            # Service metrics
            service_metrics = {}
            for service_name, lb in self.load_balancers.items():
                service_metrics[service_name] = lb.get_backend_stats()
            
            # Performance trends (last 100 requests)
            recent_response_times = []
            for times in self.request_metrics.values():
                recent_response_times.extend(times[-100:])
            
            if recent_response_times:
                recent_response_times.sort()
                performance_trends = {
                    'recent_avg': sum(recent_response_times) / len(recent_response_times),
                    'recent_p95': recent_response_times[int(len(recent_response_times) * 0.95)],
                    'recent_p99': recent_response_times[int(len(recent_response_times) * 0.99)]
                }
            else:
                performance_trends = {}
            
            return jsonify({
                'gateway': {
                    'uptime': uptime,
                    'version': self.config.version,
                    'total_requests': self.request_count,
                    'total_errors': total_errors,
                    'error_rate': total_errors / max(self.request_count, 1),
                    'requests_per_second': self.request_count / max(uptime, 1)
                },
                'routes': route_metrics,
                'errors': error_breakdown,
                'services': service_metrics,
                'performance_trends': performance_trends,
                'system': {
                    'memory_usage_percent': psutil.virtual_memory().percent,
                    'cpu_usage_percent': psutil.cpu_percent(interval=1),
                    'disk_usage_percent': psutil.disk_usage('/').percent
                }
            })
        
        @self.app.route('/gateway/monitoring/alerts', methods=['GET'])
        def get_alerts():
            """Get monitoring alerts"""
            return jsonify({
                'alerts': self.alerts,
                'total_alerts': len(self.alerts),
                'active_alerts': len([a for a in self.alerts if not a.get('resolved', False)])
            })
        
        @self.app.route('/gateway/monitoring/alerts', methods=['POST'])
        def create_alert():
            """Create a manual alert"""
            alert_data = request.get_json()
            if not alert_data:
                return jsonify({'error': 'Invalid JSON'}), 400
            
            alert = {
                'id': str(uuid.uuid4()),
                'timestamp': time.time(),
                'type': alert_data.get('type', 'manual'),
                'severity': alert_data.get('severity', 'warning'),
                'message': alert_data.get('message', ''),
                'source': alert_data.get('source', 'manual'),
                'resolved': False
            }
            
            self.alerts.append(alert)
            logger.warning(f"Manual alert created: {alert['message']}")
            
            return jsonify(alert), 201
        
        @self.app.route('/gateway/monitoring/alerts/<alert_id>/resolve', methods=['POST'])
        def resolve_alert(alert_id):
            """Resolve an alert"""
            for alert in self.alerts:
                if alert['id'] == alert_id:
                    alert['resolved'] = True
                    alert['resolved_at'] = time.time()
                    logger.info(f"Alert resolved: {alert_id}")
                    return jsonify(alert)
            
            return jsonify({'error': 'Alert not found'}), 404
        
        # Catch-all route for API requests
        @self.app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
        def handle_request(path):
            """Main request handler"""
            return self._handle_flask_request(path)
    
    def _setup_cors(self):
        """Setup CORS headers"""
        if not self.config.enable_cors:
            return
        
        @self.app.after_request
        def add_cors_headers(response):
            origin = request.headers.get('Origin')
            if origin in self.config.cors_origins or '*' in self.config.cors_origins:
                response.headers['Access-Control-Allow-Origin'] = origin or '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
                response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response
        
        @self.app.route('/<path:path>', methods=['OPTIONS'])
        def handle_options(path):
            """Handle OPTIONS requests for CORS"""
            response = Response()
            origin = request.headers.get('Origin')
            if origin in self.config.cors_origins or '*' in self.config.cors_origins:
                response.headers['Access-Control-Allow-Origin'] = origin or '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
                response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response
    
    def _handle_flask_request(self, path: str):
        """Handle Flask request and route through gateway"""
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Get client IP
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
            
            # Create request context
            context = MiddlewareContext(
                request_id=request_id,
                method=request.method,
                path=path,
                headers=dict(request.headers),
                query_params=dict(request.args),
                client_ip=client_ip,
                start_time=start_time
            )
            
            # Track active request
            self.active_requests[request_id] = {
                'method': request.method,
                'path': path,
                'client_ip': client_ip,
                'start_time': start_time
            }
            
            # Find matching route
            route = self._find_route(request.method, path)
            if not route:
                self.error_count += 1
                return jsonify({
                    'error': 'Not Found',
                    'message': f'No route found for {request.method} {path}',
                    'request_id': request_id
                }), 404
            
            # Apply pre-request middleware
            middleware_result = self.middleware_manager.apply_pre_request(context, route.middleware_chain)
            if middleware_result:
                self.error_count += 1
                return middleware_result
            
            # Get load balancer for the service
            load_balancer = self.load_balancers.get(route.backend_service)
            if not load_balancer:
                self.error_count += 1
                return jsonify({
                    'error': 'Service Unavailable',
                    'message': f'Backend service {route.backend_service} not found',
                    'request_id': request_id
                }), 503
            
            # Forward request to backend
            try:
                # Prepare request body
                body = request.get_data() if request.method in ['POST', 'PUT', 'PATCH'] else None
                
                # Forward request
                status, headers, body = asyncio.run(load_balancer.forward_request(
                    method=request.method,
                    path=path,
                    headers=dict(request.headers),
                    body=body,
                    client_ip=client_ip
                ))
                
                # Apply post-request middleware
                context.response_status = status
                context.response_headers = headers
                context.response_body = body
                
                post_middleware_result = self.middleware_manager.apply_post_request(context, route.middleware_chain)
                if post_middleware_result:
                    self.error_count += 1
                    return post_middleware_result
                
                # Create Flask response
                response = Response(
                    response=body,
                    status=status,
                    headers=headers
                )
                
                # Add gateway headers
                response.headers['X-Gateway-Request-ID'] = request_id
                response.headers['X-Gateway-Service'] = route.backend_service
                response.headers['X-Gateway-Version'] = self.config.version
                
                # Add version-specific headers
                if route.version:
                    response.headers['X-API-Version'] = route.version
                    
                    # Add deprecation warnings if applicable
                    if route.deprecated:
                        response.headers['X-API-Deprecated'] = 'true'
                        if route.deprecation_date:
                            response.headers['X-API-Deprecation-Date'] = route.deprecation_date
                        if route.sunset_date:
                            response.headers['X-API-Sunset-Date'] = route.sunset_date
                    
                    # Add API version support information
                    response.headers['X-API-Supported-Versions'] = self._get_supported_versions()
                
                return response
                
            except Exception as e:
                logger.error(f"Error forwarding request: {e}")
                self.error_count += 1
                return jsonify({
                    'error': 'Bad Gateway',
                    'message': 'Error forwarding request to backend',
                    'request_id': request_id
                }), 502
                
        except Exception as e:
            logger.error(f"Gateway error: {e}")
            self.error_count += 1
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Gateway internal error',
                'request_id': request_id
            }), 500
            
        finally:
            # Clean up request tracking
            if request_id in self.active_requests:
                del self.active_requests[request_id]
            
            # Update metrics
            self.request_count += 1
            duration = time.time() - start_time
            logger.info(f"Request {request_id} completed in {duration:.3f}s")
            
            # Collect detailed metrics
            route_key = f"{route.method.value} {route.path}"
            self.request_metrics[route_key].append(duration)
            
            # Keep only last 1000 response times per route
            if len(self.request_metrics[route_key]) > 1000:
                self.request_metrics[route_key] = self.request_metrics[route_key][-1000:]
            
            # Update service metrics
            if route.backend_service not in self.service_metrics:
                self.service_metrics[route.backend_service] = {
                    'request_count': 0,
                    'error_count': 0,
                    'response_times': []
                }
            
            self.service_metrics[route.backend_service]['request_count'] += 1
            self.service_metrics[route.backend_service]['response_times'].append(duration)
            
            # Keep only last 1000 response times per service
            if len(self.service_metrics[route.backend_service]['response_times']) > 1000:
                self.service_metrics[route.backend_service]['response_times'] = \
                    self.service_metrics[route.backend_service]['response_times'][-1000:]
            
            # Check for performance alerts
            self._check_performance_alerts(duration, route_key, route.backend_service)
            
            # Update error metrics if this was an error response
            if context.response_status and context.response_status >= 400:
                error_type = f"{context.response_status}"
                self.error_metrics[error_type] += 1
                self.service_metrics[route.backend_service]['error_count'] += 1
    
    def _find_route(self, method: str, path: str) -> Optional[Route]:
        """Find matching route for request with version support"""
        # Extract version from path or headers
        version = self._extract_version_from_request(path)
        
        # Find matching routes
        matching_routes = []
        for route in self.routes.values():
            if route.method.value != method:
                continue
            
            # Check version compatibility
            if route.version and version and route.version != version:
                continue
            
            # Check path matching
            if route.match_type == RouteMatchType.EXACT:
                if route.path == path:
                    matching_routes.append(route)
            elif route.match_type == RouteMatchType.PREFIX:
                if path.startswith(route.path):
                    matching_routes.append(route)
            elif route.match_type == RouteMatchType.REGEX:
                if re.match(route.path, path):
                    matching_routes.append(route)
            elif route.match_type == RouteMatchType.WILDCARD:
                # Simple wildcard matching
                pattern = route.path.replace('*', '.*')
                if re.match(f"^{pattern}$", path):
                    matching_routes.append(route)
        
        # Prefer versioned routes over unversioned ones
        versioned_routes = [r for r in matching_routes if r.version]
        if versioned_routes:
            return versioned_routes[0]
        
        # Return any matching route
        return matching_routes[0] if matching_routes else None
    
    def _extract_version_from_request(self, path: str) -> Optional[str]:
        """Extract API version from path or headers"""
        # Try to extract from URL path: /api/v1/users -> v1
        version_pattern = r'/v(\d+(?:\.\d+)?)'
        match = re.search(version_pattern, path)
        if match:
            return match.group(1)
        
        # Could also check Accept-Version header or other version indicators
        return None
    
    def _get_supported_versions(self) -> str:
        """Get comma-separated list of supported API versions"""
        versions = set()
        for route in self.routes.values():
            if route.version:
                versions.add(route.version)
        return ','.join(sorted(versions))
    
    def _check_performance_alerts(self, duration: float, route_key: str, service_name: str):
        """Check for performance issues and create alerts"""
        # Check response time alerts
        if duration > self.performance_thresholds['response_time_critical']:
            self._create_alert(
                'performance',
                'critical',
                f'Critical response time: {duration:.3f}s for {route_key}',
                'system'
            )
        elif duration > self.performance_thresholds['response_time_warning']:
            self._create_alert(
                'performance',
                'warning',
                f'High response time: {duration:.3f}s for {route_key}',
                'system'
            )
        
        # Check error rate alerts
        if service_name in self.service_metrics:
            service_stats = self.service_metrics[service_name]
            if service_stats['request_count'] > 0:
                error_rate = service_stats['error_count'] / service_stats['request_count']
                if error_rate > self.performance_thresholds['error_rate_critical']:
                    self._create_alert(
                        'error_rate',
                        'critical',
                        f'Critical error rate: {error_rate:.2%} for service {service_name}',
                        'system'
                    )
                elif error_rate > self.performance_thresholds['error_rate_warning']:
                    self._create_alert(
                        'error_rate',
                        'warning',
                        f'Elevated error rate: {error_rate:.2%} for service {service_name}',
                        'system'
                    )
        
        # Check system resource alerts
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > self.performance_thresholds['memory_usage_critical']:
            self._create_alert(
                'system',
                'critical',
                f'Critical memory usage: {memory_percent:.1f}%',
                'system'
            )
        elif memory_percent > self.performance_thresholds['memory_usage_warning']:
            self._create_alert(
                'system',
                'warning',
                f'Elevated memory usage: {memory_percent:.1f}%',
                'system'
            )
    
    def _create_alert(self, alert_type: str, severity: str, message: str, source: str):
        """Create an alert (avoiding duplicates)"""
        # Check if similar alert already exists and is not resolved
        for alert in self.alerts:
            if (alert.get('type') == alert_type and 
                alert.get('severity') == severity and 
                alert.get('message') == message and 
                not alert.get('resolved', False)):
                # Update timestamp instead of creating duplicate
                alert['last_seen'] = time.time()
                return
        
        # Create new alert
        alert = {
            'id': str(uuid.uuid4()),
            'timestamp': time.time(),
            'type': alert_type,
            'severity': severity,
            'message': message,
            'source': source,
            'resolved': False
        }
        
        self.alerts.append(alert)
        logger.warning(f"Alert created: {message}")
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
    
    def add_route(self, route_id: str, route: Route):
        """Add a new route"""
        self.routes[route_id] = route
        logger.info(f"Added route {route_id}: {route.method.value} {route.path} -> {route.backend_service}")
    
    def remove_route(self, route_id: str):
        """Remove a route"""
        if route_id in self.routes:
            del self.routes[route_id]
            logger.info(f"Removed route {route_id}")
    
    def add_service(self, service: ServiceEndpoint):
        """Add a backend service"""
        self.services[service.name] = service
        
        # Create load balancer for the service
        load_balancer_config = {
            'algorithm': service.name,  # Will be overridden per route
            'backends': [
                {
                    'host': host,
                    'port': service.port,
                    'weight': service.weight,
                    'max_connections': service.max_connections
                }
                for host in service.hosts
            ],
            'health_check_interval': 30,
            'health_check_timeout': 5,
            'health_check_retries': 3,
            'request_timeout': service.timeout
        }
        
        self.load_balancers[service.name] = AdvancedLoadBalancer(load_balancer_config)
        logger.info(f"Added service {service.name} with {len(service.hosts)} backends")
    
    def remove_service(self, service_name: str):
        """Remove a backend service"""
        if service_name in self.services:
            del self.services[service_name]
        
        if service_name in self.load_balancers:
            # Shutdown load balancer
            asyncio.run(self.load_balancers[service_name].shutdown())
            del self.load_balancers[service_name]
        
        logger.info(f"Removed service {service_name}")
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update gateway configuration"""
        for key, value in new_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        logger.info("Gateway configuration updated")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get gateway statistics"""
        uptime = time.time() - self.start_time
        return {
            'uptime': uptime,
            'total_requests': self.request_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(self.request_count, 1),
            'active_requests': len(self.active_requests),
            'services': len(self.services),
            'routes': len(self.routes),
            'middleware_count': len(self.middleware_manager.middleware_registry)
        }
    
    def run(self, host: str = '0.0.0.0', port: int = 8080, debug: bool = None):
        """Run the gateway"""
        if debug is None:
            debug = self.config.debug
        
        logger.info(f"Starting API Gateway on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

# Gateway factory function
def create_gateway(config: Dict[str, Any]) -> APIGateway:
    """Create and configure an API Gateway instance"""
    gateway_config = GatewayConfig(**config)
    gateway = APIGateway(gateway_config)
    
    # Add default middleware
    from middleware import LoggingMiddleware, RateLimitMiddleware, SecurityMiddleware
    
    gateway.middleware_manager.register_middleware('logging', LoggingMiddleware())
    gateway.middleware_manager.register_middleware('rate_limit', RateLimitMiddleware())
    gateway.middleware_manager.register_middleware('security', SecurityMiddleware())
    
    return gateway

# Example usage
if __name__ == "__main__":
    # Example configuration
    config = {
        'name': 'FlavorSnap Gateway',
        'version': '1.0.0',
        'debug': True,
        'enable_cors': True,
        'cors_origins': ['*']
    }
    
    # Create gateway
    gateway = create_gateway(config)
    
    # Add example service
    from dataclasses import dataclass
    
    service = ServiceEndpoint(
        name='ml-model-api',
        hosts=['localhost'],
        port=5000,
        health_check_path='/health'
    )
    gateway.add_service(service)
    
    # Add example route
    route = Route(
        path='/api/*',
        method=HTTPMethod.GET,
        backend_service='ml-model-api',
        match_type=RouteMatchType.WILDCARD,
        middleware_chain=['logging', 'security']
    )
    gateway.add_route('api-route', route)
    
    # Run gateway
    gateway.run(host='0.0.0.0', port=8080)
