"""
Advanced Load Balancer for ML Model API
Implements intelligent traffic distribution, health checks, and failover mechanisms
"""

import asyncio
import aiohttp
import time
import hashlib
import logging
import json
import statistics
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import socket
import ssl
from urllib.parse import urlparse
import psutil
import prometheus_client as prom

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoadBalancingAlgorithm(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    IP_HASH = "ip_hash"
    LEAST_RESPONSE_TIME = "least_response_time"
    ADAPTIVE = "adaptive"

class HealthStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    UNKNOWN = "unknown"

@dataclass
class BackendServer:
    id: str
    host: str
    port: int
    weight: int = 1
    max_connections: int = 100
    current_connections: int = 0
    response_times: List[float] = None
    health_status: HealthStatus = HealthStatus.UNKNOWN
    last_health_check: float = 0
    consecutive_failures: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    @property
    def avg_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return statistics.mean(self.response_times[-100:])  # Last 100 requests
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return (self.total_requests - self.failed_requests) / self.total_requests
    
    @property
    def load_score(self) -> float:
        """Calculate load score for adaptive load balancing"""
        connection_ratio = self.current_connections / self.max_connections
        response_time_score = min(self.avg_response_time / 5.0, 1.0)  # Normalize to 5s
        success_rate_score = 1.0 - self.success_rate
        
        return (connection_ratio * 0.4 + response_time_score * 0.3 + success_rate_score * 0.3)

class PrometheusMetrics:
    """Prometheus metrics for load balancer monitoring"""
    
    def __init__(self):
        self.requests_total = prom.Counter(
            'load_balancer_requests_total',
            'Total requests processed',
            ['backend', 'status']
        )
        
        self.request_duration = prom.Histogram(
            'load_balancer_request_duration_seconds',
            'Request duration in seconds',
            ['backend']
        )
        
        self.backend_connections = prom.Gauge(
            'load_balancer_backend_connections',
            'Current connections per backend',
            ['backend']
        )
        
        self.backend_health = prom.Gauge(
            'load_balancer_backend_health',
            'Backend health status (1=healthy, 0=unhealthy)',
            ['backend']
        )
        
        self.backend_response_time = prom.Gauge(
            'load_balancer_backend_response_time',
            'Average response time per backend',
            ['backend']
        )
        
        self.backend_load_score = prom.Gauge(
            'load_balancer_backend_load_score',
            'Load score per backend',
            ['backend']
        )
        
        self.active_backends = prom.Gauge(
            'load_balancer_active_backends',
            'Number of active backends'
        )

class AdvancedLoadBalancer:
    """Advanced load balancer with multiple algorithms and health checking"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backends: List[BackendServer] = []
        self.algorithm = LoadBalancingAlgorithm(config.get('algorithm', 'least_connections'))
        self.health_check_interval = config.get('health_check_interval', 30)
        self.health_check_timeout = config.get('health_check_timeout', 5)
        self.health_check_retries = config.get('health_check_retries', 3)
        self.failover_timeout = config.get('failover_timeout', 10)
        self.connection_draining_timeout = config.get('connection_draining_timeout', 30)
        self.ssl_verify = config.get('ssl_verify', True)
        
        # Round-robin state
        self.current_index = 0
        
        # Metrics
        self.metrics = PrometheusMetrics()
        
        # Health check task
        self.health_check_task = None
        
        # Session affinity (IP hash)
        self.session_affinity_enabled = config.get('session_affinity', False)
        
        # Initialize backends
        self._initialize_backends()
        
        # Start health checking
        self._start_health_checking()
    
    def _initialize_backends(self):
        """Initialize backend servers from configuration"""
        backend_configs = self.config.get('backends', [])
        for i, backend_config in enumerate(backend_configs):
            backend = BackendServer(
                id=f"backend_{i}",
                host=backend_config['host'],
                port=backend_config['port'],
                weight=backend_config.get('weight', 1),
                max_connections=backend_config.get('max_connections', 100)
            )
            self.backends.append(backend)
    
    def _start_health_checking(self):
        """Start the health checking background task"""
        if self.health_check_task is None:
            self.health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def _health_check_loop(self):
        """Background health checking loop"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(5)
    
    async def _perform_health_checks(self):
        """Perform health checks on all backends"""
        for backend in self.backends:
            try:
                is_healthy = await self._check_backend_health(backend)
                if is_healthy:
                    if backend.health_status != HealthStatus.HEALTHY:
                        logger.info(f"Backend {backend.id} is now healthy")
                        backend.health_status = HealthStatus.HEALTHY
                        backend.consecutive_failures = 0
                    self.metrics.backend_health.labels(backend=backend.id).set(1)
                else:
                    backend.consecutive_failures += 1
                    if backend.consecutive_failures >= self.health_check_retries:
                        if backend.health_status != HealthStatus.UNHEALTHY:
                            logger.warning(f"Backend {backend.id} is now unhealthy")
                            backend.health_status = HealthStatus.UNHEALTHY
                        self.metrics.backend_health.labels(backend=backend.id).set(0)
                
                backend.last_health_check = time.time()
                
            except Exception as e:
                logger.error(f"Health check failed for {backend.id}: {e}")
                backend.consecutive_failures += 1
                if backend.consecutive_failures >= self.health_check_retries:
                    backend.health_status = HealthStatus.UNHEALTHY
                    self.metrics.backend_health.labels(backend=backend.id).set(0)
        
        # Update active backends metric
        active_count = sum(1 for b in self.backends if b.health_status == HealthStatus.HEALTHY)
        self.metrics.active_backends.set(active_count)
    
    async def _check_backend_health(self, backend: BackendServer) -> bool:
        """Check health of a specific backend"""
        try:
            timeout = aiohttp.ClientTimeout(total=self.health_check_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{backend.url}/health", ssl=self.ssl_verify) as response:
                    if response.status == 200:
                        # Check response content if available
                        content = await response.text()
                        return "healthy" in content.lower()
                    return False
        except Exception as e:
            logger.debug(f"Health check failed for {backend.id}: {e}")
            return False
    
    def get_healthy_backends(self) -> List[BackendServer]:
        """Get list of healthy backends"""
        return [b for b in self.backends if b.health_status == HealthStatus.HEALTHY]
    
    def select_backend(self, client_ip: str = None) -> Optional[BackendServer]:
        """Select backend based on configured algorithm"""
        healthy_backends = self.get_healthy_backends()
        
        if not healthy_backends:
            logger.error("No healthy backends available")
            return None
        
        if self.algorithm == LoadBalancingAlgorithm.ROUND_ROBIN:
            return self._select_round_robin(healthy_backends)
        elif self.algorithm == LoadBalancingAlgorithm.LEAST_CONNECTIONS:
            return self._select_least_connections(healthy_backends)
        elif self.algorithm == LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN:
            return self._select_weighted_round_robin(healthy_backends)
        elif self.algorithm == LoadBalancingAlgorithm.IP_HASH:
            return self._select_ip_hash(healthy_backends, client_ip)
        elif self.algorithm == LoadBalancingAlgorithm.LEAST_RESPONSE_TIME:
            return self._select_least_response_time(healthy_backends)
        elif self.algorithm == LoadBalancingAlgorithm.ADAPTIVE:
            return self._select_adaptive(healthy_backends)
        else:
            # Default to least connections
            return self._select_least_connections(healthy_backends)
    
    def _select_round_robin(self, backends: List[BackendServer]) -> BackendServer:
        """Round-robin selection"""
        backend = backends[self.current_index % len(backends)]
        self.current_index += 1
        return backend
    
    def _select_least_connections(self, backends: List[BackendServer]) -> BackendServer:
        """Select backend with least connections"""
        return min(backends, key=lambda b: b.current_connections)
    
    def _select_weighted_round_robin(self, backends: List[BackendServer]) -> BackendServer:
        """Weighted round-robin selection"""
        total_weight = sum(b.weight for b in backends)
        if total_weight == 0:
            return self._select_round_robin(backends)
        
        # Create weighted list
        weighted_backends = []
        for backend in backends:
            weighted_backends.extend([backend] * backend.weight)
        
        backend = weighted_backends[self.current_index % len(weighted_backends)]
        self.current_index += 1
        return backend
    
    def _select_ip_hash(self, backends: List[BackendServer], client_ip: str) -> BackendServer:
        """IP hash selection for session affinity"""
        if not client_ip:
            return self._select_round_robin(backends)
        
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        index = hash_value % len(backends)
        return backends[index]
    
    def _select_least_response_time(self, backends: List[BackendServer]) -> BackendServer:
        """Select backend with lowest average response time"""
        return min(backends, key=lambda b: b.avg_response_time)
    
    def _select_adaptive(self, backends: List[BackendServer]) -> BackendServer:
        """Adaptive selection based on multiple factors"""
        return min(backends, key=lambda b: b.load_score)
    
    async def forward_request(self, method: str, path: str, headers: Dict[str, str], 
                            body: bytes = None, client_ip: str = None) -> Tuple[int, Dict[str, str], bytes]:
        """Forward request to selected backend"""
        backend = self.select_backend(client_ip)
        
        if not backend:
            return 503, {"Content-Type": "application/json"}, json.dumps({
                "error": "Service Unavailable",
                "message": "No healthy backends available"
            }).encode()
        
        start_time = time.time()
        backend.current_connections += 1
        backend.total_requests += 1
        
        try:
            # Update metrics
            self.metrics.backend_connections.labels(backend=backend.id).set(backend.current_connections)
            
            timeout = aiohttp.ClientTimeout(total=self.config.get('request_timeout', 300))
            
            # Prepare headers
            forward_headers = headers.copy()
            forward_headers['X-Forwarded-For'] = client_ip or 'unknown'
            forward_headers['X-Forwarded-Proto'] = 'https'
            forward_headers['X-Forwarded-Host'] = headers.get('Host', 'unknown')
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=method,
                    url=f"{backend.url}{path}",
                    headers=forward_headers,
                    data=body
                ) as response:
                    response_body = await response.read()
                    response_headers = dict(response.headers)
                    
                    # Remove hop-by-hop headers
                    hop_by_hop = {'connection', 'keep-alive', 'proxy-authenticate', 
                                'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 
                                'upgrade', 'proxy-connection'}
                    response_headers = {k: v for k, v in response_headers.items() 
                                     if k.lower() not in hop_by_hop}
                    
                    # Update backend metrics
                    response_time = time.time() - start_time
                    backend.response_times.append(response_time)
                    if len(backend.response_times) > 1000:
                        backend.response_times = backend.response_times[-1000:]
                    
                    # Update Prometheus metrics
                    self.metrics.requests_total.labels(
                        backend=backend.id, 
                        status=str(response.status)
                    ).inc()
                    self.metrics.request_duration.labels(backend=backend.id).observe(response_time)
                    self.metrics.backend_response_time.labels(backend=backend.id).set(backend.avg_response_time)
                    self.metrics.backend_load_score.labels(backend=backend.id).set(backend.load_score)
                    
                    return response.status, response_headers, response_body
                    
        except Exception as e:
            backend.failed_requests += 1
            logger.error(f"Request failed for backend {backend.id}: {e}")
            
            # Try failover to another backend
            if self.config.get('failover_enabled', True):
                return await self._attempt_failover(method, path, headers, body, client_ip, [backend])
            
            return 502, {"Content-Type": "application/json"}, json.dumps({
                "error": "Bad Gateway",
                "message": "Backend server error"
            }).encode()
            
        finally:
            backend.current_connections -= 1
            self.metrics.backend_connections.labels(backend=backend.id).set(backend.current_connections)
    
    async def _attempt_failover(self, method: str, path: str, headers: Dict[str, str], 
                               body: bytes, client_ip: str, tried_backends: List[BackendServer]) -> Tuple[int, Dict[str, str], bytes]:
        """Attempt failover to another backend"""
        healthy_backends = self.get_healthy_backends()
        available_backends = [b for b in healthy_backends if b not in tried_backends]
        
        if not available_backends:
            return 503, {"Content-Type": "application/json"}, json.dumps({
                "error": "Service Unavailable",
                "message": "All backends failed"
            }).encode()
        
        backend = self.select_backend(client_ip)
        if backend in tried_backends:
            # Try next available backend
            for b in available_backends:
                if b not in tried_backends:
                    backend = b
                    break
        
        tried_backends.append(backend)
        
        try:
            return await self.forward_request(method, path, headers, body, client_ip)
        except Exception as e:
            logger.warning(f"Failover attempt failed for backend {backend.id}: {e}")
            return await self._attempt_failover(method, path, headers, body, client_ip, tried_backends)
    
    def get_backend_stats(self) -> Dict[str, Any]:
        """Get statistics for all backends"""
        stats = {
            'total_backends': len(self.backends),
            'healthy_backends': len(self.get_healthy_backends()),
            'algorithm': self.algorithm.value,
            'backends': []
        }
        
        for backend in self.backends:
            backend_stats = {
                'id': backend.id,
                'host': backend.host,
                'port': backend.port,
                'health_status': backend.health_status.value,
                'current_connections': backend.current_connections,
                'max_connections': backend.max_connections,
                'total_requests': backend.total_requests,
                'failed_requests': backend.failed_requests,
                'success_rate': backend.success_rate,
                'avg_response_time': backend.avg_response_time,
                'load_score': backend.load_score,
                'last_health_check': backend.last_health_check
            }
            stats['backends'].append(backend_stats)
        
        return stats
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update load balancer configuration"""
        self.config.update(new_config)
        
        # Update algorithm if changed
        if 'algorithm' in new_config:
            self.algorithm = LoadBalancingAlgorithm(new_config['algorithm'])
        
        # Update health check parameters
        if 'health_check_interval' in new_config:
            self.health_check_interval = new_config['health_check_interval']
        if 'health_check_timeout' in new_config:
            self.health_check_timeout = new_config['health_check_timeout']
        if 'health_check_retries' in new_config:
            self.health_check_retries = new_config['health_check_retries']
        
        logger.info("Load balancer configuration updated")
    
    async def shutdown(self):
        """Graceful shutdown"""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Load balancer shutdown complete")

# Example usage and configuration
if __name__ == "__main__":
    # Example configuration
    config = {
        'algorithm': 'least_connections',
        'health_check_interval': 30,
        'health_check_timeout': 5,
        'health_check_retries': 3,
        'failover_enabled': True,
        'session_affinity': False,
        'request_timeout': 300,
        'ssl_verify': True,
        'backends': [
            {'host': 'backend-1', 'port': 5000, 'weight': 1, 'max_connections': 100},
            {'host': 'backend-2', 'port': 5000, 'weight': 2, 'max_connections': 150},
            {'host': 'backend-3', 'port': 5000, 'weight': 1, 'max_connections': 100},
        ]
    }
    
    # Create load balancer
    lb = AdvancedLoadBalancer(config)
    
    # Example request forwarding
    async def handle_request():
        status, headers, body = await lb.forward_request(
            method='GET',
            path='/api/health',
            headers={'Host': 'flavorsnap.com'},
            client_ip='192.168.1.100'
        )
        print(f"Status: {status}")
        print(f"Body: {body.decode()}")
    
    # Run example
    asyncio.run(handle_request())
