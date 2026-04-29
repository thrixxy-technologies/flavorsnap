"""
Advanced Load Balancer for Distributed Computing
Implements intelligent load balancing for distributed task processing and API requests
"""
import os
import time
import json
import hashlib
import threading
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import logging
import requests
import redis
from distributed_processor import Node, Task, NodeStatus, TaskStatus


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    RESOURCE_BASED = "resource_based"
    ADAPTIVE = "adaptive"
    CONSISTENT_HASH = "consistent_hash"


class HealthCheckType(Enum):
    """Health check types"""
    HTTP = "http"
    TCP = "tcp"
    TASK = "task"
    CUSTOM = "custom"


@dataclass
class LoadBalancerMetrics:
    """Load balancer metrics"""
    timestamp: datetime
    total_requests: int
    requests_per_second: float
    active_connections: int
    avg_response_time: float
    error_rate: float
    backend_distribution: Dict[str, int]
    health_check_results: Dict[str, bool]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class Backend:
    """Backend server/node information"""
    backend_id: str
    host: str
    port: int
    weight: int
    max_connections: int
    current_connections: int
    response_times: deque
    success_rate: float
    last_health_check: datetime
    health_status: str
    cpu_usage: float
    memory_usage: float
    active_tasks: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['last_health_check'] = self.last_health_check.isoformat()
        data['response_times'] = list(self.response_times)
        return data


class LoadBalancerConfig:
    """Load balancer configuration"""
    
    # Load balancing
    DEFAULT_STRATEGY = LoadBalancingStrategy.ADAPTIVE
    MAX_RESPONSE_TIME_SAMPLES = 100
    HEALTH_CHECK_INTERVAL = 30  # seconds
    HEALTH_CHECK_TIMEOUT = 5   # seconds
    
    # Circuit breaker
    CIRCUIT_BREAKER_THRESHOLD = 5
    CIRCUIT_BREAKER_TIMEOUT = 60  # seconds
    
    # Connection limits
    MAX_CONNECTIONS_PER_BACKEND = 1000
    CONNECTION_TIMEOUT = 30  # seconds
    
    # Metrics
    METRICS_COLLECTION_INTERVAL = 10  # seconds
    METRICS_HISTORY_SIZE = 1440  # 24 hours at 1-minute intervals


class HealthChecker:
    """Health checking for backends"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.health_check_functions = {
            HealthCheckType.HTTP: self._check_http_health,
            HealthCheckType.TCP: self._check_tcp_health,
            HealthCheckType.TASK: self._check_task_health,
            HealthCheckType.CUSTOM: self._check_custom_health
        }
    
    def check_health(self, backend: Backend, check_type: HealthCheckType = HealthCheckType.HTTP) -> bool:
        """Check backend health"""
        check_function = self.health_check_functions.get(check_type)
        if not check_function:
            self.logger.error(f"Unknown health check type: {check_type}")
            return False
        
        try:
            return check_function(backend)
        except Exception as e:
            self.logger.error(f"Health check failed for {backend.backend_id}: {str(e)}")
            return False
    
    def _check_http_health(self, backend: Backend) -> bool:
        """Check HTTP health endpoint"""
        try:
            url = f"http://{backend.host}:{backend.port}/health"
            response = requests.get(url, timeout=LoadBalancerConfig.HEALTH_CHECK_TIMEOUT)
            return response.status_code == 200
        except:
            return False
    
    def _check_tcp_health(self, backend: Backend) -> bool:
        """Check TCP connectivity"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(LoadBalancerConfig.HEALTH_CHECK_TIMEOUT)
            result = sock.connect_ex((backend.host, backend.port))
            sock.close()
            return result == 0
        except:
            return False
    
    def _check_task_health(self, backend: Backend) -> bool:
        """Check task processing health"""
        try:
            # Submit a simple health check task
            url = f"http://{backend.host}:{backend.port}/api/task/health"
            response = requests.post(url, timeout=LoadBalancerConfig.HEALTH_CHECK_TIMEOUT)
            return response.status_code == 200
        except:
            return False
    
    def _check_custom_health(self, backend: Backend) -> bool:
        """Custom health check (can be overridden)"""
        # Default implementation checks if backend is responsive
        return self._check_tcp_health(backend)


class LoadBalancingAlgorithms:
    """Load balancing algorithm implementations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.round_robin_index = 0
        self.backend_stats = defaultdict(lambda: {
            'requests': 0,
            'response_times': deque(maxlen=LoadBalancerConfig.MAX_RESPONSE_TIME_SAMPLES),
            'success_rate': 1.0
        })
    
    def select_backend(self, backends: List[Backend], strategy: LoadBalancingStrategy, 
                       client_ip: str = None, request_path: str = None) -> Optional[Backend]:
        """Select backend based on strategy"""
        # Filter healthy backends
        healthy_backends = [b for b in backends if b.health_status == "healthy"]
        
        if not healthy_backends:
            return None
        
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin(healthy_backends)
        elif strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin(healthy_backends)
        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections(healthy_backends)
        elif strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            return self._least_response_time(healthy_backends)
        elif strategy == LoadBalancingStrategy.RESOURCE_BASED:
            return self._resource_based(healthy_backends)
        elif strategy == LoadBalancingStrategy.CONSISTENT_HASH:
            return self._consistent_hash(healthy_backends, client_ip, request_path)
        elif strategy == LoadBalancingStrategy.ADAPTIVE:
            return self._adaptive(healthy_backends)
        else:
            return self._round_robin(healthy_backends)
    
    def _round_robin(self, backends: List[Backend]) -> Backend:
        """Round robin selection"""
        backend = backends[self.round_robin_index % len(backends)]
        self.round_robin_index += 1
        return backend
    
    def _weighted_round_robin(self, backends: List[Backend]) -> Backend:
        """Weighted round robin selection"""
        total_weight = sum(b.weight for b in backends)
        if total_weight == 0:
            return backends[0]
        
        # Create weighted list
        weighted_backends = []
        for backend in backends:
            weighted_backends.extend([backend] * backend.weight)
        
        return self._round_robin(weighted_backends)
    
    def _least_connections(self, backends: List[Backend]) -> Backend:
        """Least connections selection"""
        return min(backends, key=lambda b: b.current_connections)
    
    def _least_response_time(self, backends: List[Backend]) -> Backend:
        """Least response time selection"""
        # Calculate average response time for each backend
        backend_times = []
        for backend in backends:
            if backend.response_times:
                avg_time = statistics.mean(backend.response_times)
                backend_times.append((backend, avg_time))
            else:
                backend_times.append((backend, float('inf')))
        
        # Return backend with lowest average response time
        return min(backend_times, key=lambda x: x[1])[0]
    
    def _resource_based(self, backends: List[Backend]) -> Backend:
        """Resource-based selection"""
        # Calculate resource score (lower is better)
        def resource_score(backend):
            # Normalize CPU and memory usage (0-1)
            cpu_score = backend.cpu_usage / 100.0
            memory_score = backend.memory_usage / 100.0
            
            # Factor in active tasks
            task_score = backend.active_tasks / max(backend.max_connections, 1)
            
            # Combined score
            return (cpu_score * 0.4 + memory_score * 0.3 + task_score * 0.3)
        
        return min(backends, key=resource_score)
    
    def _consistent_hash(self, backends: List[Backend], client_ip: str, request_path: str) -> Backend:
        """Consistent hash selection"""
        if not client_ip and not request_path:
            return backends[0]
        
        # Create hash key
        hash_key = f"{client_ip}:{request_path}" if client_ip else request_path
        
        # Hash to backend
        hash_value = int(hashlib.md5(hash_key.encode()).hexdigest(), 16)
        return backends[hash_value % len(backends)]
    
    def _adaptive(self, backends: List[Backend]) -> Backend:
        """Adaptive selection based on performance metrics"""
        # Calculate performance score for each backend
        def performance_score(backend):
            # Response time component (lower is better)
            if backend.response_times:
                avg_response_time = statistics.mean(backend.response_times)
                response_score = 1.0 / (1.0 + avg_response_time)
            else:
                response_score = 0.5
            
            # Success rate component
            success_score = backend.success_rate
            
            # Connection utilization component
            connection_utilization = backend.current_connections / max(backend.max_connections, 1)
            connection_score = 1.0 - connection_utilization
            
            # Weighted combination
            return (response_score * 0.4 + success_score * 0.3 + connection_score * 0.3)
        
        # Select backend with highest performance score
        return max(backends, key=performance_score)
    
    def update_backend_stats(self, backend_id: str, response_time: float, success: bool):
        """Update backend statistics"""
        stats = self.backend_stats[backend_id]
        stats['requests'] += 1
        stats['response_times'].append(response_time)
        
        # Update success rate (exponential moving average)
        if success:
            stats['success_rate'] = stats['success_rate'] * 0.9 + 0.1
        else:
            stats['success_rate'] = stats['success_rate'] * 0.9


class CircuitBreaker:
    """Circuit breaker for fault tolerance"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.circuit_states = {}  # backend_id -> state
        self.failure_counts = defaultdict(int)
        self.last_failure_time = {}
    
    def is_available(self, backend_id: str) -> bool:
        """Check if backend is available (circuit is closed)"""
        state = self.circuit_states.get(backend_id, "closed")
        
        if state == "closed":
            return True
        elif state == "open":
            # Check if timeout has passed
            last_failure = self.last_failure_time.get(backend_id, 0)
            if time.time() - last_failure > LoadBalancerConfig.CIRCUIT_BREAKER_TIMEOUT:
                # Try half-open state
                self.circuit_states[backend_id] = "half_open"
                return True
            return False
        elif state == "half_open":
            return True
        
        return False
    
    def record_success(self, backend_id: str):
        """Record successful request"""
        if self.circuit_states.get(backend_id) == "half_open":
            # Close circuit on success
            self.circuit_states[backend_id] = "closed"
            self.failure_counts[backend_id] = 0
        
    def record_failure(self, backend_id: str):
        """Record failed request"""
        self.failure_counts[backend_id] += 1
        self.last_failure_time[backend_id] = time.time()
        
        # Check if threshold reached
        if self.failure_counts[backend_id] >= LoadBalancerConfig.CIRCUIT_BREAKER_THRESHOLD:
            self.circuit_states[backend_id] = "open"
            self.logger.warning(f"Circuit opened for backend {backend_id}")


class AdvancedLoadBalancer:
    """Advanced load balancer for distributed computing"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.backends: Dict[str, Backend] = {}
        self.health_checker = HealthChecker()
        self.algorithms = LoadBalancingAlgorithms()
        self.circuit_breaker = CircuitBreaker()
        
        self.current_strategy = LoadBalancerConfig.DEFAULT_STRATEGY
        self.metrics_history: deque = deque(maxlen=LoadBalancerConfig.METRICS_HISTORY_SIZE)
        
        self.monitoring_active = False
        self.health_check_thread = None
        self.metrics_thread = None
        
        # Statistics
        self.total_requests = 0
        self.request_times = deque(maxlen=1000)
        self.error_count = 0
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize load balancer with Flask app"""
        self.app = app
        
        # Load configuration
        self._load_configuration()
        
        # Start monitoring
        self.start_monitoring()
        
        self.logger.info("Advanced load balancer initialized")
    
    def _load_configuration(self):
        """Load configuration from app config"""
        # Load backends from configuration
        backends_config = self.app.config.get('LOAD_BALANCER_BACKENDS', [])
        
        for backend_config in backends_config:
            self.add_backend(
                backend_id=backend_config['id'],
                host=backend_config['host'],
                port=backend_config['port'],
                weight=backend_config.get('weight', 1),
                max_connections=backend_config.get('max_connections', 1000)
            )
        
        # Load strategy
        strategy_name = self.app.config.get('LOAD_BALANCING_STRATEGY', 'adaptive')
        self.current_strategy = LoadBalancingStrategy(strategy_name)
    
    def start_monitoring(self):
        """Start monitoring threads"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()
        
        # Start metrics collection thread
        self.metrics_thread = threading.Thread(target=self._metrics_loop, daemon=True)
        self.metrics_thread.start()
        
        self.logger.info("Load balancer monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring threads"""
        self.monitoring_active = False
        
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
        if self.metrics_thread:
            self.metrics_thread.join(timeout=5)
        
        self.logger.info("Load balancer monitoring stopped")
    
    def add_backend(self, backend_id: str, host: str, port: int, weight: int = 1, 
                   max_connections: int = 1000):
        """Add a backend server"""
        backend = Backend(
            backend_id=backend_id,
            host=host,
            port=port,
            weight=weight,
            max_connections=max_connections,
            current_connections=0,
            response_times=deque(maxlen=LoadBalancerConfig.MAX_RESPONSE_TIME_SAMPLES),
            success_rate=1.0,
            last_health_check=datetime.now(),
            health_status="unknown",
            cpu_usage=0.0,
            memory_usage=0.0,
            active_tasks=0,
            metadata={}
        )
        
        self.backends[backend_id] = backend
        self.logger.info(f"Added backend {backend_id} at {host}:{port}")
    
    def remove_backend(self, backend_id: str) -> bool:
        """Remove a backend server"""
        if backend_id in self.backends:
            del self.backends[backend_id]
            self.logger.info(f"Removed backend {backend_id}")
            return True
        return False
    
    def select_backend(self, client_ip: str = None, request_path: str = None) -> Optional[Backend]:
        """Select best backend for request"""
        # Filter available backends
        available_backends = [
            backend for backend in self.backends.values()
            if (backend.health_status == "healthy" and 
                self.circuit_breaker.is_available(backend.backend_id) and
                backend.current_connections < backend.max_connections)
        ]
        
        if not available_backends:
            self.logger.warning("No available backends")
            return None
        
        # Select backend using algorithm
        selected_backend = self.algorithms.select_backend(
            available_backends, self.current_strategy, client_ip, request_path
        )
        
        if selected_backend:
            selected_backend.current_connections += 1
            self.total_requests += 1
        
        return selected_backend
    
    def release_backend(self, backend_id: str, response_time: float, success: bool):
        """Release backend after request completion"""
        if backend_id in self.backends:
            backend = self.backends[backend_id]
            backend.current_connections = max(0, backend.current_connections - 1)
            backend.response_times.append(response_time)
            
            # Update success rate
            if success:
                backend.success_rate = backend.success_rate * 0.9 + 0.1
            else:
                backend.success_rate = backend.success_rate * 0.9
            
            # Update algorithm stats
            self.algorithms.update_backend_stats(backend_id, response_time, success)
            
            # Update circuit breaker
            if success:
                self.circuit_breaker.record_success(backend_id)
            else:
                self.circuit_breaker.record_failure(backend_id)
                self.error_count += 1
            
            # Record request time
            self.request_times.append(response_time)
    
    def _health_check_loop(self):
        """Health check loop"""
        while self.monitoring_active:
            try:
                for backend in self.backends.values():
                    # Perform health check
                    is_healthy = self.health_checker.check_health(backend)
                    
                    # Update health status
                    backend.health_status = "healthy" if is_healthy else "unhealthy"
                    backend.last_health_check = datetime.now()
                    
                    # Log status changes
                    if not is_healthy:
                        self.logger.warning(f"Backend {backend.backend_id} is unhealthy")
                
                # Sleep until next check
                time.sleep(LoadBalancerConfig.HEALTH_CHECK_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Health check loop error: {str(e)}")
                time.sleep(LoadBalancerConfig.HEALTH_CHECK_INTERVAL)
    
    def _metrics_loop(self):
        """Metrics collection loop"""
        while self.monitoring_active:
            try:
                # Calculate current metrics
                now = datetime.now()
                
                # Requests per second
                recent_requests = len([t for t in self.request_times 
                                    if (now - timedelta(seconds=LoadBalancerConfig.METRICS_COLLECTION_INTERVAL)).timestamp() < time.time()])
                requests_per_second = recent_requests / LoadBalancerConfig.METRICS_COLLECTION_INTERVAL
                
                # Average response time
                avg_response_time = statistics.mean(self.request_times) if self.request_times else 0
                
                # Error rate
                error_rate = self.error_count / max(self.total_requests, 1)
                
                # Backend distribution
                backend_distribution = {}
                for backend_id, backend in self.backends.items():
                    backend_distribution[backend_id] = backend.current_connections
                
                # Health check results
                health_results = {backend_id: backend.health_status == "healthy" 
                               for backend_id, backend in self.backends.items()}
                
                metrics = LoadBalancerMetrics(
                    timestamp=now,
                    total_requests=self.total_requests,
                    requests_per_second=requests_per_second,
                    active_connections=sum(b.current_connections for b in self.backends.values()),
                    avg_response_time=avg_response_time,
                    error_rate=error_rate,
                    backend_distribution=backend_distribution,
                    health_check_results=health_results
                )
                
                self.metrics_history.append(metrics)
                
                # Sleep until next collection
                time.sleep(LoadBalancerConfig.METRICS_COLLECTION_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Metrics collection error: {str(e)}")
                time.sleep(LoadBalancerConfig.METRICS_COLLECTION_INTERVAL)
    
    def get_load_balancer_status(self) -> Dict[str, Any]:
        """Get current load balancer status"""
        return {
            'strategy': self.current_strategy.value,
            'total_backends': len(self.backends),
            'healthy_backends': len([b for b in self.backends.values() if b.health_status == "healthy"]),
            'total_requests': self.total_requests,
            'active_connections': sum(b.current_connections for b in self.backends.values()),
            'error_rate': self.error_count / max(self.total_requests, 1),
            'monitoring_active': self.monitoring_active,
            'backends': {backend_id: backend.to_dict() for backend_id, backend in self.backends.items()}
        }
    
    def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics history"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            metrics.to_dict() for metrics in self.metrics_history
            if metrics.timestamp >= cutoff_time
        ]
    
    def set_strategy(self, strategy: LoadBalancingStrategy):
        """Set load balancing strategy"""
        self.current_strategy = strategy
        self.logger.info(f"Load balancing strategy changed to {strategy.value}")


# Initialize global advanced load balancer
advanced_load_balancer = AdvancedLoadBalancer()
