import time
import psutil
import torch
import json
import logging
import asyncio
import aiohttp
from functools import wraps
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, Info
from flask import Flask, Response, request, make_response
try:
    from persistence import log_prediction_history
except Exception:
    log_prediction_history = None

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'flask_http_request_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'flask_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

REQUEST_EXCEPTIONS = Counter(
    'flask_http_request_exceptions_total',
    'Total HTTP request exceptions',
    ['method', 'endpoint']
)

MODEL_INFERENCE_COUNT = Counter(
    'model_inference_total',
    'Total model inferences',
    ['label', 'status']
)

MODEL_INFERENCE_DURATION = Histogram(
    'model_inference_duration_seconds',
    'Model inference duration in seconds',
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)

MODEL_INFERENCE_FAILURES = Counter(
    'model_inference_failures_total',
    'Total model inference failures'
)

MODEL_ACCURACY = Gauge(
    'model_accuracy',
    'Current model accuracy'
)

MEMORY_USAGE = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
)

CPU_USAGE = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage'
)

GPU_MEMORY_USAGE = Gauge(
    'gpu_memory_usage_bytes',
    'GPU memory usage in bytes'
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Number of active connections'
)

# Additional infrastructure monitoring metrics
DISK_USAGE = Gauge(
    'disk_usage_bytes',
    'Disk usage in bytes',
    ['mount_point']
)

NETWORK_IO = Gauge(
    'network_io_bytes',
    'Network I/O bytes',
    ['direction']
)

PROCESS_COUNT = Gauge(
    'process_count',
    'Number of running processes'
)

SYSTEM_LOAD = Gauge(
    'system_load_average',
    'System load average',
    ['period']
)

CONTAINER_STATUS = Info(
    'container_status',
    'Container status information'
)

DATABASE_CONNECTIONS = Gauge(
    'database_connections',
    'Active database connections'
)

DATABASE_QUERY_DURATION = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type']
)

CACHE_HIT_RATE = Gauge(
    'cache_hit_rate',
    'Cache hit rate percentage'
)

ORACLE_REQUEST_COUNT = Counter(
    'oracle_requests_total',
    'Total oracle requests',
    ['oracle_type', 'status']
)

ZK_PROOF_COUNT = Counter(
    'zk_proofs_total',
    'Total ZK proofs generated/verified',
    ['circuit_type', 'operation', 'status']
)

DEPLOYMENT_STATUS = Info(
    'deployment_status',
    'Current deployment status'
)

ALERT_COUNT = Counter(
    'alerts_total',
    'Total alerts triggered',
    ['severity', 'type']
)

# Storage and CDN metrics
STORAGE_OPERATIONS = Counter(
    'storage_operations_total',
    'Total storage operations',
    ['operation', 'status']
)

STORAGE_BANDWIDTH = Counter(
    'storage_bandwidth_bytes_total',
    'Total storage bandwidth',
    ['direction']
)

CDN_REQUESTS = Counter(
    'cdn_requests_total',
    'Total CDN requests',
    ['status', 'cache_hit']
)

CDN_BANDWIDTH_SAVED = Counter(
    'cdn_bandwidth_saved_bytes_total',
    'Total CDN bandwidth saved'
)

STORAGE_COST = Gauge(
    'storage_cost_usd',
    'Current storage cost in USD'
)

CDN_COST_SAVINGS = Gauge(
    'cdn_cost_savings_usd',
    'CDN cost savings in USD'
)

class MonitoringMiddleware:
    def __init__(self, app: Flask = None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_request(self._teardown_request)
        
        # Add metrics endpoint
        @app.route('/metrics')
        def metrics():
            # Update system metrics
            self._update_system_metrics()
            return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
        
        # Add health check with detailed metrics
        @app.route('/health/detailed')
        def detailed_health():
            return self._get_detailed_health()
    
    def _before_request(self):
        request.start_time = time.time()
    
    def _after_request(self, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Record request metrics
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown',
                status=response.status_code
            ).inc()
            
            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown'
            ).observe(duration)
        
        return response
    
    def _teardown_request(self, exception):
        if exception:
            REQUEST_EXCEPTIONS.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown'
            ).inc()
    
    def _update_system_metrics(self):
        # Update memory usage
        memory = psutil.virtual_memory()
        MEMORY_USAGE.set(memory.used)
        
        # Update CPU usage
        CPU_USAGE.set(psutil.cpu_percent())
        
        # Update GPU memory if available
        if torch.cuda.is_available():
            GPU_MEMORY_USAGE.set(torch.cuda.memory_allocated())
        
        # Update active connections (placeholder)
        ACTIVE_CONNECTIONS.set(1)  # This would need actual connection tracking
    
    def _get_detailed_health(self) -> Dict[str, Any]:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health_data = {
            'status': 'healthy',
            'timestamp': time.time(),
            'system': {
                'cpu_percent': psutil.cpu_percent(),
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                }
            },
            'gpu': {
                'available': torch.cuda.is_available(),
                'device_count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
                'memory_allocated': torch.cuda.memory_allocated() if torch.cuda.is_available() else 0,
                'memory_cached': torch.cuda.memory_reserved() if torch.cuda.is_available() else 0
            },
            'model': {
                'loaded': True,  # This would be set based on actual model state
                'accuracy': MODEL_ACCURACY._value.get() if MODEL_ACCURACY._value else 0.0
            }
        }
        
        return health_data

def track_inference(func):
    """Decorator to track model inference metrics"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        status = 'success'
        resp_obj = None
        try:
            result = func(*args, **kwargs)
            try:
                resp_obj = make_response(result)
            except Exception:
                resp_obj = None
            return result
        except Exception as e:
            status = 'failure'
            MODEL_INFERENCE_FAILURES.inc()
            raise
        finally:
            duration = time.time() - start_time
            MODEL_INFERENCE_DURATION.observe(duration)
            
            # Extract label from result if available
            label = 'unknown'
            payload = None
            try:
                if resp_obj is not None:
                    payload = resp_obj.get_json(silent=True)
                    if isinstance(payload, dict):
                        label = payload.get('label', 'unknown')
            except Exception:
                payload = None
            
            MODEL_INFERENCE_COUNT.labels(label=label, status=status).inc()
            try:
                if log_prediction_history and isinstance(payload, dict):
                    meta = {
                        "request_id": request.headers.get("X-Request-Id"),
                        "user_id": request.headers.get("X-User-Id"),
                        "error_message": None if status == 'success' else 'inference_failed'
                    }
                    log_prediction_history(payload, duration, status, meta)
            except Exception:
                pass
    
    return wrapper

def update_model_accuracy(accuracy: float):
    """Update model accuracy metric"""
    MODEL_ACCURACY.set(accuracy)

@dataclass
class Alert:
    """Alert data structure"""
    timestamp: datetime
    severity: str  # critical, warning, info
    type: str
    message: str
    source: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None

@dataclass
class HealthCheck:
    """Health check data structure"""
    service_name: str
    status: str  # healthy, unhealthy, degraded
    timestamp: datetime
    response_time: float
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = None

class InfrastructureMonitor:
    """Comprehensive infrastructure monitoring system"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.logger = logging.getLogger('InfrastructureMonitor')
        self.alerts: List[Alert] = []
        self.health_checks: Dict[str, HealthCheck] = {}
        self.metrics_history: List[Dict[str, Any]] = []
        self.alert_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'response_time': 5.0,
            'error_rate': 5.0
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize monitoring with Flask app"""
        self.app = app
        
        # Add additional monitoring endpoints
        @app.route('/monitoring/health')
        def monitoring_health():
            return self.get_overall_health()
        
        @app.route('/monitoring/alerts')
        def get_alerts():
            return self.get_active_alerts()
        
        @app.route('/monitoring/metrics/history')
        def metrics_history():
            return self.get_metrics_history()
        
        @app.route('/monitoring/status')
        def infrastructure_status():
            return self.get_infrastructure_status()
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk_partitions = psutil.disk_partitions()
            disk_usage = {}
            for partition in disk_partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage[partition.mountpoint] = {
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': usage.percent
                    }
                except PermissionError:
                    continue
            
            # Network metrics
            network_io = psutil.net_io_counters()
            network_interfaces = psutil.net_if_addrs()
            
            # Process metrics
            process_count = len(psutil.pids())
            
            # GPU metrics
            gpu_metrics = {}
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    gpu_metrics[f'gpu_{i}'] = {
                        'memory_allocated': torch.cuda.memory_allocated(i),
                        'memory_cached': torch.cuda.memory_reserved(i),
                        'memory_total': torch.cuda.get_device_properties(i).total_memory
                    }
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'load_average': {
                        '1min': load_avg[0],
                        '5min': load_avg[1],
                        '15min': load_avg[2]
                    }
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'cached': getattr(memory, 'cached', 0)
                },
                'swap': {
                    'total': swap.total,
                    'used': swap.used,
                    'free': swap.free,
                    'percent': swap.percent
                },
                'disk': disk_usage,
                'network': {
                    'bytes_sent': network_io.bytes_sent,
                    'bytes_recv': network_io.bytes_recv,
                    'packets_sent': network_io.packets_sent,
                    'packets_recv': network_io.packets_recv,
                    'interfaces': list(network_interfaces.keys())
                },
                'processes': {
                    'count': process_count,
                    'running': len([p for p in psutil.process_iter() if p.status() == 'running'])
                },
                'gpu': gpu_metrics
            }
            
            # Update Prometheus metrics
            self._update_prometheus_metrics(metrics)
            
            # Store in history
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > 1000:  # Keep only last 1000 entries
                self.metrics_history.pop(0)
            
            # Check for alerts
            self._check_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return {}
    
    def _update_prometheus_metrics(self, metrics: Dict[str, Any]):
        """Update Prometheus metrics with collected data"""
        try:
            # Update existing metrics
            CPU_USAGE.set(metrics['cpu']['percent'])
            MEMORY_USAGE.set(metrics['memory']['used'])
            
            # Update new metrics
            PROCESS_COUNT.set(metrics['processes']['count'])
            
            # System load
            for period, value in [('1min', metrics['cpu']['load_average']['1min']),
                                 ('5min', metrics['cpu']['load_average']['5min']),
                                 ('15min', metrics['cpu']['load_average']['15min'])]:
                SYSTEM_LOAD.labels(period=period).set(value)
            
            # Disk usage
            for mount_point, usage in metrics['disk'].items():
                DISK_USAGE.labels(mount_point=mount_point).set(usage['used'])
            
            # Network I/O
            NETWORK_IO.labels(direction='sent').set(metrics['network']['bytes_sent'])
            NETWORK_IO.labels(direction='recv').set(metrics['network']['bytes_recv'])
            
            # GPU metrics
            for gpu_name, gpu_data in metrics['gpu'].items():
                GPU_MEMORY_USAGE.set(gpu_data['memory_allocated'])
            
        except Exception as e:
            self.logger.error(f"Error updating Prometheus metrics: {e}")
    
    def _check_alerts(self, metrics: Dict[str, Any]):
        """Check metrics against thresholds and generate alerts"""
        try:
            # CPU usage alert
            if metrics['cpu']['percent'] > self.alert_thresholds['cpu_usage']:
                self.create_alert(
                    severity='warning',
                    alert_type='cpu_usage',
                    message=f"CPU usage is {metrics['cpu']['percent']:.1f}%",
                    source='system_monitor'
                )
            
            # Memory usage alert
            if metrics['memory']['percent'] > self.alert_thresholds['memory_usage']:
                self.create_alert(
                    severity='warning',
                    alert_type='memory_usage',
                    message=f"Memory usage is {metrics['memory']['percent']:.1f}%",
                    source='system_monitor'
                )
            
            # Disk usage alert
            for mount_point, usage in metrics['disk'].items():
                if usage['percent'] > self.alert_thresholds['disk_usage']:
                    self.create_alert(
                        severity='critical',
                        alert_type='disk_usage',
                        message=f"Disk usage for {mount_point} is {usage['percent']:.1f}%",
                        source='system_monitor'
                    )
            
            # System load alert
            if metrics['cpu']['load_average']['1min'] > metrics['cpu']['count']:
                self.create_alert(
                    severity='warning',
                    alert_type='system_load',
                    message=f"System load ({metrics['cpu']['load_average']['1min']:.2f}) exceeds CPU count ({metrics['cpu']['count']})",
                    source='system_monitor'
                )
            
        except Exception as e:
            self.logger.error(f"Error checking alerts: {e}")
    
    def create_alert(self, severity: str, alert_type: str, message: str, source: str):
        """Create a new alert"""
        alert = Alert(
            timestamp=datetime.now(),
            severity=severity,
            type=alert_type,
            message=message,
            source=source
        )
        
        self.alerts.append(alert)
        
        # Update alert counter
        ALERT_COUNT.labels(severity=severity, type=alert_type).inc()
        
        # Log alert
        self.logger.warning(f"ALERT [{severity.upper()}] {alert_type}: {message}")
        
        # Keep only last 1000 alerts
        if len(self.alerts) > 1000:
            self.alerts.pop(0)
    
    def perform_health_check(self, service_name: str, check_url: str = None) -> HealthCheck:
        """Perform health check for a service"""
        start_time = time.time()
        status = 'healthy'
        error_message = None
        metrics = {}
        
        try:
            if check_url:
                # Perform HTTP health check
                import requests
                response = requests.get(check_url, timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code != 200:
                    status = 'unhealthy'
                    error_message = f"HTTP {response.status_code}"
                
                if response_time > self.alert_thresholds['response_time']:
                    status = 'degraded'
                    error_message = f"Response time: {response_time:.2f}s"
                
                metrics = {
                    'response_time': response_time,
                    'status_code': response.status_code
                }
            else:
                # Internal service health check
                metrics = self.collect_system_metrics()
                response_time = time.time() - start_time
                
                # Check system health
                if (metrics['cpu']['percent'] > 90 or 
                    metrics['memory']['percent'] > 95):
                    status = 'degraded'
                    error_message = "High resource usage"
                
        except Exception as e:
            status = 'unhealthy'
            error_message = str(e)
            response_time = time.time() - start_time
        
        health_check = HealthCheck(
            service_name=service_name,
            status=status,
            timestamp=datetime.now(),
            response_time=response_time,
            error_message=error_message,
            metrics=metrics
        )
        
        self.health_checks[service_name] = health_check
        
        # Create alert if unhealthy
        if status == 'unhealthy':
            self.create_alert(
                severity='critical',
                alert_type='service_health',
                message=f"Service {service_name} is unhealthy: {error_message}",
                source='health_check'
            )
        elif status == 'degraded':
            self.create_alert(
                severity='warning',
                alert_type='service_health',
                message=f"Service {service_name} is degraded: {error_message}",
                source='health_check'
            )
        
        return health_check
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        try:
            # Collect current metrics
            metrics = self.collect_system_metrics()
            
            # Perform health checks
            services = ['api', 'database', 'cache', 'oracle', 'zk_proofs']
            for service in services:
                self.perform_health_check(service)
            
            # Calculate overall status
            total_checks = len(self.health_checks)
            healthy_checks = sum(1 for check in self.health_checks.values() if check.status == 'healthy')
            degraded_checks = sum(1 for check in self.health_checks.values() if check.status == 'degraded')
            
            if healthy_checks == total_checks:
                overall_status = 'healthy'
            elif degraded_checks > 0:
                overall_status = 'degraded'
            else:
                overall_status = 'unhealthy'
            
            return {
                'status': overall_status,
                'timestamp': datetime.now().isoformat(),
                'services': {name: asdict(check) for name, check in self.health_checks.items()},
                'metrics': metrics,
                'summary': {
                    'total_services': total_checks,
                    'healthy': healthy_checks,
                    'degraded': degraded_checks,
                    'unhealthy': total_checks - healthy_checks - degraded_checks
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting overall health: {e}")
            return {
                'status': 'error',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def get_active_alerts(self) -> Dict[str, Any]:
        """Get active alerts"""
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        
        # Group alerts by severity
        alerts_by_severity = {
            'critical': [],
            'warning': [],
            'info': []
        }
        
        for alert in active_alerts:
            alerts_by_severity[alert.severity].append(asdict(alert))
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_alerts': len(active_alerts),
            'alerts_by_severity': alerts_by_severity,
            'recent_alerts': [asdict(alert) for alert in active_alerts[-10:]]
        }
    
    def get_metrics_history(self, limit: int = 100) -> Dict[str, Any]:
        """Get metrics history"""
        return {
            'timestamp': datetime.now().isoformat(),
            'limit': limit,
            'count': len(self.metrics_history),
            'data': self.metrics_history[-limit:] if self.metrics_history else []
        }
    
    def get_infrastructure_status(self) -> Dict[str, Any]:
        """Get comprehensive infrastructure status"""
        try:
            metrics = self.collect_system_metrics()
            
            # Get container information
            container_info = {}
            try:
                import docker
                client = docker.from_env()
                containers = client.containers.list(all=True)
                
                for container in containers:
                    container_info[container.name] = {
                        'status': container.status,
                        'image': container.image.tags[0] if container.image.tags else 'unknown',
                        'created': container.attrs['Created'],
                        'ports': container.ports
                    }
                
                CONTAINER_STATUS.info(container_info)
            except ImportError:
                container_info = {'error': 'Docker SDK not available'}
            except Exception as e:
                container_info = {'error': str(e)}
            
            return {
                'timestamp': datetime.now().isoformat(),
                'system_metrics': metrics,
                'containers': container_info,
                'alerts': {
                    'active': len([a for a in self.alerts if not a.resolved]),
                    'total': len(self.alerts)
                },
                'health_checks': {name: asdict(check) for name, check in self.health_checks.items()}
            }
            
        except Exception as e:
            self.logger.error(f"Error getting infrastructure status: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def track_oracle_request(self, oracle_type: str, status: str, response_time: float = None):
        """Track oracle request metrics"""
        ORACLE_REQUEST_COUNT.labels(oracle_type=oracle_type, status=status).inc()
        
        if response_time:
            # Track response time as a histogram
            pass  # Would need to create oracle response time histogram
    
    def track_zk_proof(self, circuit_type: str, operation: str, status: str, verification_time: float = None):
        """Track ZK proof metrics"""
        ZK_PROOF_COUNT.labels(circuit_type=circuit_type, operation=operation, status=status).inc()
        
        if verification_time:
            # Track verification time as a histogram
            pass  # Would need to create ZK verification time histogram
    
    def track_database_query(self, query_type: str, duration: float):
        """Track database query metrics"""
        DATABASE_QUERY_DURATION.labels(query_type=query_type).observe(duration)
    
    def update_cache_hit_rate(self, hit_rate: float):
        """Update cache hit rate metric"""
        CACHE_HIT_RATE.set(hit_rate)
    
    def update_database_connections(self, connection_count: int):
        """Update database connection count"""
        DATABASE_CONNECTIONS.set(connection_count)
    
    def update_deployment_status(self, version: str, environment: str, status: str):
        """Update deployment status"""
        DEPLOYMENT_STATUS.info({
            'version': version,
            'environment': environment,
            'status': status,
            'timestamp': datetime.now().isoformat()
        })
    
    def track_storage_operation(self, operation: str, status: str, size_bytes: int = 0):
        """Track storage operation metrics"""
        STORAGE_OPERATIONS.labels(operation=operation, status=status).inc()
        
        if operation in ['upload', 'download'] and size_bytes > 0:
            direction = 'upload' if operation == 'upload' else 'download'
            STORAGE_BANDWIDTH.labels(direction=direction).inc(size_bytes)
    
    def track_cdn_request(self, status: str, cache_hit: bool, bandwidth_saved: int = 0):
        """Track CDN request metrics"""
        cache_status = 'hit' if cache_hit else 'miss'
        CDN_REQUESTS.labels(status=status, cache_hit=cache_status).inc()
        
        if bandwidth_saved > 0:
            CDN_BANDWIDTH_SAVED.inc(bandwidth_saved)
    
    def update_storage_cost(self, cost_usd: float):
        """Update storage cost metric"""
        STORAGE_COST.set(cost_usd)
    
    def update_cdn_cost_savings(self, savings_usd: float):
        """Update CDN cost savings metric"""
        CDN_COST_SAVINGS.set(savings_usd)
    
    def resolve_alert(self, alert_index: int):
        """Resolve an alert"""
        if 0 <= alert_index < len(self.alerts):
            self.alerts[alert_index].resolved = True
            self.alerts[alert_index].resolved_at = datetime.now()

# Global infrastructure monitor instance
infrastructure_monitor = InfrastructureMonitor()
