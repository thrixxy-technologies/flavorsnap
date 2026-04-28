#!/usr/bin/env python3
"""
Advanced Connection Pool for FlavorSnap ML Model API
Implements sophisticated connection pooling with health monitoring and auto-scaling
"""

import os
import time
import logging
import threading
import queue
import socket
import ssl
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.poolmanager import PoolManager
import psutil
import json
import pytz
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/connection_pool.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConnectionStatus(Enum):
    """Connection status states"""
    IDLE = "idle"
    ACTIVE = "active"
    ERROR = "error"
    CLOSING = "closing"
    CLOSED = "closed"

class PoolStrategy(Enum):
    """Connection pool strategies"""
    FIXED_SIZE = "fixed_size"
    DYNAMIC = "dynamic"
    ADAPTIVE = "adaptive"
    LOAD_BALANCED = "load_balanced"

@dataclass
class ConnectionConfig:
    """Connection configuration"""
    host: str
    port: int
    protocol: str = "https"
    timeout: float = 30.0
    max_retries: int = 3
    backoff_factor: float = 0.3
    keepalive: bool = True
    keepalive_timeout: int = 30
    ssl_verify: bool = True
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    custom_headers: Optional[Dict[str, str]] = None

@dataclass
class PoolConfig:
    """Connection pool configuration"""
    min_size: int = 5
    max_size: int = 50
    strategy: PoolStrategy = PoolStrategy.DYNAMIC
    health_check_interval: int = 30
    health_check_timeout: float = 5.0
    idle_timeout: int = 300
    max_lifetime: int = 3600
    enable_metrics: bool = True
    enable_auto_scaling: bool = True
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.3
    scale_up_step: int = 5
    scale_down_step: int = 3

@dataclass
class ConnectionMetrics:
    """Connection performance metrics"""
    connection_id: str
    created_at: datetime
    last_used: datetime
    usage_count: int
    error_count: int
    avg_response_time: float
    total_bytes_sent: int
    total_bytes_received: int
    status: ConnectionStatus
    health_score: float

class PooledConnection:
    """Individual pooled connection wrapper"""
    
    def __init__(self, connection_id: str, config: ConnectionConfig):
        self.connection_id = connection_id
        self.config = config
        self.status = ConnectionStatus.IDLE
        self.created_at = datetime.now(pytz.UTC)
        self.last_used = self.created_at
        self.usage_count = 0
        self.error_count = 0
        self.response_times = []
        self.bytes_sent = 0
        self.bytes_received = 0
        self.health_score = 1.0
        self.lock = threading.Lock()
        
        # Initialize actual connection
        self.connection = None
        self.session = None
        self._init_connection()
    
    def _init_connection(self):
        """Initialize the actual connection"""
        try:
            # Create requests session for this connection
            self.session = requests.Session()
            
            # Configure retry strategy
            retry_strategy = Retry(
                total=self.config.max_retries,
                backoff_factor=self.config.backoff_factor,
                status_forcelist=[429, 500, 502, 503, 504]
            )
            
            # Create adapter
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount(f"{self.config.protocol}://", adapter)
            
            # Configure session
            self.session.timeout = self.config.timeout
            
            # Add custom headers
            if self.config.custom_headers:
                self.session.headers.update(self.config.custom_headers)
            
            # Configure SSL
            if self.config.protocol == "https":
                if not self.config.ssl_verify:
                    self.session.verify = False
                elif self.config.ssl_cert_path and self.config.ssl_key_path:
                    self.session.cert = (self.config.ssl_cert_path, self.config.ssl_key_path)
            
            self.status = ConnectionStatus.IDLE
            logger.debug(f"Connection {self.connection_id} initialized")
            
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.error_count += 1
            logger.error(f"Failed to initialize connection {self.connection_id}: {str(e)}")
    
    def execute_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Execute request through this connection"""
        with self.lock:
            if self.status != ConnectionStatus.IDLE:
                raise Exception(f"Connection {self.connection_id} not available: {self.status}")
            
            start_time = time.time()
            self.status = ConnectionStatus.ACTIVE
            self.usage_count += 1
            
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Update metrics
                response_time = (time.time() - start_time) * 1000
                self.response_times.append(response_time)
                self.last_used = datetime.now(pytz.UTC)
                
                # Track bytes
                if response.request.body:
                    self.bytes_sent += len(response.request.body)
                if response.content:
                    self.bytes_received += len(response.content)
                
                # Update health score
                self._update_health_score(response_time, response.status_code)
                
                return response
                
            except Exception as e:
                self.error_count += 1
                self._update_health_score(0, 0)  # Penalize for errors
                raise
            finally:
                self.status = ConnectionStatus.IDLE
    
    def _update_health_score(self, response_time: float, status_code: int):
        """Update connection health score"""
        try:
            # Base score calculation
            score = 1.0
            
            # Penalize slow responses
            if response_time > 1000:  # 1 second
                score -= 0.1
            elif response_time > 500:  # 500ms
                score -= 0.05
            
            # Penalize error status codes
            if status_code >= 400:
                score -= 0.2
            
            # Penalize errors
            if self.error_count > 0:
                score -= min(self.error_count * 0.1, 0.5)
            
            # Update health score with smoothing
            self.health_score = (self.health_score * 0.7) + (score * 0.3)
            self.health_score = max(0.0, min(1.0, self.health_score))
            
        except Exception as e:
            logger.error(f"Failed to update health score: {str(e)}")
    
    def health_check(self) -> bool:
        """Perform health check on connection"""
        try:
            # Simple health check - make a lightweight request
            test_url = f"{self.config.protocol}://{self.config.host}:{self.config.port}/health"
            response = self.session.get(test_url, timeout=5)
            
            if response.status_code == 200:
                self._update_health_score(200, 200)  # Good response
                return True
            else:
                self._update_health_score(200, response.status_code)
                return False
                
        except Exception as e:
            self.error_count += 1
            self._update_health_score(0, 0)
            logger.warning(f"Health check failed for connection {self.connection_id}: {str(e)}")
            return False
    
    def is_expired(self, max_lifetime: int, idle_timeout: int) -> bool:
        """Check if connection is expired"""
        now = datetime.now(pytz.UTC)
        
        # Check max lifetime
        if (now - self.created_at).total_seconds() > max_lifetime:
            return True
        
        # Check idle timeout
        if (now - self.last_used).total_seconds() > idle_timeout:
            return True
        
        return False
    
    def is_healthy(self, min_health_score: float = 0.5) -> bool:
        """Check if connection is healthy"""
        return self.health_score >= min_health_score and self.status != ConnectionStatus.ERROR
    
    def get_metrics(self) -> ConnectionMetrics:
        """Get connection metrics"""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        return ConnectionMetrics(
            connection_id=self.connection_id,
            created_at=self.created_at,
            last_used=self.last_used,
            usage_count=self.usage_count,
            error_count=self.error_count,
            avg_response_time=avg_response_time,
            total_bytes_sent=self.bytes_sent,
            total_bytes_received=self.bytes_received,
            status=self.status,
            health_score=self.health_score
        )
    
    def close(self):
        """Close connection"""
        with self.lock:
            self.status = ConnectionStatus.CLOSING
            
            if self.session:
                self.session.close()
                self.session = None
            
            self.status = ConnectionStatus.CLOSED
            logger.debug(f"Connection {self.connection_id} closed")

class AdvancedConnectionPool:
    """Advanced connection pool with auto-scaling and health monitoring"""
    
    def __init__(self, connection_config: ConnectionConfig, pool_config: PoolConfig):
        self.connection_config = connection_config
        self.pool_config = pool_config
        self.logger = logging.getLogger(__name__)
        
        # Pool state
        self.connections = {}
        self.available_connections = queue.Queue()
        self.active_connections = set()
        self.pool_lock = threading.Lock()
        
        # Metrics
        self.metrics_history = []
        self.total_requests = 0
        self.total_errors = 0
        self.pool_resizes = 0
        
        # Background tasks
        self.health_check_thread = None
        self.scaling_thread = None
        self.cleanup_thread = None
        self.running = False
        
        # Initialize pool
        self._init_pool()
        
        logger.info(f"AdvancedConnectionPool initialized with strategy: {pool_config.strategy.value}")
    
    def _init_pool(self):
        """Initialize connection pool"""
        try:
            # Create initial connections
            initial_size = self.pool_config.min_size
            for i in range(initial_size):
                self._create_connection()
            
            # Start background tasks
            self._start_background_tasks()
            
            logger.info(f"Connection pool initialized with {initial_size} connections")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {str(e)}")
            raise
    
    def _create_connection(self) -> str:
        """Create a new connection"""
        connection_id = f"conn_{int(time.time())}_{len(self.connections)}"
        
        try:
            connection = PooledConnection(connection_id, self.connection_config)
            
            with self.pool_lock:
                self.connections[connection_id] = connection
                self.available_connections.put(connection_id)
            
            logger.debug(f"Created connection: {connection_id}")
            return connection_id
            
        except Exception as e:
            logger.error(f"Failed to create connection {connection_id}: {str(e)}")
            raise
    
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        self.running = True
        
        # Health check thread
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop, daemon=True
        )
        self.health_check_thread.start()
        
        # Auto-scaling thread
        if self.pool_config.enable_auto_scaling:
            self.scaling_thread = threading.Thread(
                target=self._auto_scaling_loop, daemon=True
            )
            self.scaling_thread.start()
        
        # Cleanup thread
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_loop, daemon=True
        )
        self.cleanup_thread.start()
        
        logger.info("Background tasks started")
    
    def _health_check_loop(self):
        """Background health check loop"""
        while self.running:
            try:
                self._perform_health_checks()
                time.sleep(self.pool_config.health_check_interval)
            except Exception as e:
                logger.error(f"Health check loop error: {str(e)}")
                time.sleep(10)
    
    def _auto_scaling_loop(self):
        """Background auto-scaling loop"""
        while self.running:
            try:
                self._check_scaling_needs()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Auto-scaling loop error: {str(e)}")
                time.sleep(10)
    
    def _cleanup_loop(self):
        """Background cleanup loop"""
        while self.running:
            try:
                self._cleanup_expired_connections()
                time.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Cleanup loop error: {str(e)}")
                time.sleep(60)
    
    def _perform_health_checks(self):
        """Perform health checks on all connections"""
        unhealthy_connections = []
        
        with self.pool_lock:
            for connection_id, connection in self.connections.items():
                if connection.is_healthy():
                    continue
                
                # Perform health check
                if not connection.health_check():
                    unhealthy_connections.append(connection_id)
        
        # Remove unhealthy connections
        for connection_id in unhealthy_connections:
            self._remove_connection(connection_id, "unhealthy")
        
        if unhealthy_connections:
            logger.info(f"Removed {len(unhealthy_connections)} unhealthy connections")
    
    def _check_scaling_needs(self):
        """Check if pool needs to be scaled"""
        with self.pool_lock:
            current_size = len(self.connections)
            active_count = len(self.active_connections)
            available_count = self.available_connections.qsize()
            
            # Calculate utilization
            utilization = active_count / current_size if current_size > 0 else 0
            
            # Scale up if needed
            if utilization > self.pool_config.scale_up_threshold and current_size < self.pool_config.max_size:
                scale_up_count = min(self.pool_config.scale_up_step, 
                                   self.pool_config.max_size - current_size)
                
                for _ in range(scale_up_count):
                    try:
                        self._create_connection()
                    except Exception as e:
                        logger.error(f"Failed to scale up: {str(e)}")
                        break
                
                self.pool_resizes += 1
                logger.info(f"Scaled up pool by {scale_up_count} connections")
            
            # Scale down if needed
            elif utilization < self.pool_config.scale_down_threshold and current_size > self.pool_config.min_size:
                scale_down_count = min(self.pool_config.scale_down_step,
                                     current_size - self.pool_config.min_size)
                
                # Remove idle connections
                removed_count = 0
                for _ in range(scale_down_count):
                    try:
                        connection_id = self.available_connections.get_nowait()
                        if self._remove_connection(connection_id, "scale_down"):
                            removed_count += 1
                    except queue.Empty:
                        break
                
                if removed_count > 0:
                    self.pool_resizes += 1
                    logger.info(f"Scaled down pool by {removed_count} connections")
    
    def _cleanup_expired_connections(self):
        """Clean up expired connections"""
        expired_connections = []
        
        with self.pool_lock:
            for connection_id, connection in self.connections.items():
                if connection.is_expired(self.pool_config.max_lifetime, self.pool_config.idle_timeout):
                    expired_connections.append(connection_id)
        
        for connection_id in expired_connections:
            self._remove_connection(connection_id, "expired")
        
        if expired_connections:
            logger.info(f"Cleaned up {len(expired_connections)} expired connections")
    
    def _remove_connection(self, connection_id: str, reason: str) -> bool:
        """Remove a connection from the pool"""
        with self.pool_lock:
            if connection_id not in self.connections:
                return False
            
            connection = self.connections[connection_id]
            
            # Close connection
            connection.close()
            
            # Remove from pool
            del self.connections[connection_id]
            
            # Remove from active set if present
            self.active_connections.discard(connection_id)
            
            logger.debug(f"Removed connection {connection_id} ({reason})")
            return True
    
    def get_connection(self, timeout: float = 30.0) -> PooledConnection:
        """Get a connection from the pool"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try to get available connection
                connection_id = self.available_connections.get_nowait()
                
                with self.pool_lock:
                    if connection_id in self.connections:
                        connection = self.connections[connection_id]
                        if connection.is_healthy():
                            self.active_connections.add(connection_id)
                            return connection
                        else:
                            # Remove unhealthy connection
                            self._remove_connection(connection_id, "unhealthy")
                
            except queue.Empty:
                # No available connections, try to create new one
                with self.pool_lock:
                    if len(self.connections) < self.pool_config.max_size:
                        try:
                            connection_id = self._create_connection()
                            connection = self.connections[connection_id]
                            self.active_connections.add(connection_id)
                            return connection
                        except Exception:
                            pass
                
                # Wait and retry
                time.sleep(0.1)
        
        raise TimeoutError("Failed to get connection from pool")
    
    def return_connection(self, connection: PooledConnection):
        """Return a connection to the pool"""
        with self.pool_lock:
            if connection.connection_id in self.connections:
                self.active_connections.discard(connection.connection_id)
                self.available_connections.put(connection.connection_id)
    
    def execute_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Execute request using pooled connection"""
        connection = None
        try:
            # Get connection from pool
            connection = self.get_connection()
            
            # Execute request
            response = connection.execute_request(method, url, **kwargs)
            
            # Update metrics
            self.total_requests += 1
            if response.status_code >= 400:
                self.total_errors += 1
            
            return response
            
        except Exception as e:
            self.total_errors += 1
            raise
        finally:
            # Return connection to pool
            if connection:
                self.return_connection(connection)
    
    def get_pool_metrics(self) -> Dict[str, Any]:
        """Get pool performance metrics"""
        with self.pool_lock:
            total_connections = len(self.connections)
            active_connections = len(self.active_connections)
            available_connections = self.available_connections.qsize()
            
            # Calculate connection health
            healthy_connections = sum(1 for conn in self.connections.values() if conn.is_healthy())
            avg_health_score = sum(conn.health_score for conn in self.connections.values()) / total_connections if total_connections > 0 else 0
            
            # Calculate utilization
            utilization = active_connections / total_connections if total_connections > 0 else 0
            
            # Calculate error rate
            error_rate = self.total_errors / self.total_requests if self.total_requests > 0 else 0
            
            return {
                'timestamp': datetime.now(pytz.UTC).isoformat(),
                'total_connections': total_connections,
                'active_connections': active_connections,
                'available_connections': available_connections,
                'healthy_connections': healthy_connections,
                'avg_health_score': avg_health_score,
                'utilization': utilization,
                'total_requests': self.total_requests,
                'total_errors': self.total_errors,
                'error_rate': error_rate,
                'pool_resizes': self.pool_resizes,
                'min_size': self.pool_config.min_size,
                'max_size': self.pool_config.max_size,
                'strategy': self.pool_config.strategy.value
            }
    
    def get_connection_metrics(self) -> List[ConnectionMetrics]:
        """Get detailed metrics for all connections"""
        with self.pool_lock:
            return [conn.get_metrics() for conn in self.connections.values()]
    
    def optimize_pool(self) -> Dict[str, Any]:
        """Optimize pool configuration based on metrics"""
        try:
            metrics = self.get_pool_metrics()
            
            recommendations = []
            changes_made = []
            
            # Analyze utilization
            utilization = metrics['utilization']
            if utilization > 0.9:
                recommendations.append("High utilization - consider increasing max_size")
                if self.pool_config.max_size < 100:
                    self.pool_config.max_size = min(self.pool_config.max_size + 10, 100)
                    changes_made.append(f"Increased max_size to {self.pool_config.max_size}")
            
            elif utilization < 0.2 and metrics['total_connections'] > self.pool_config.min_size:
                recommendations.append("Low utilization - consider decreasing min_size")
                if self.pool_config.min_size > 2:
                    self.pool_config.min_size = max(self.pool_config.min_size - 2, 2)
                    changes_made.append(f"Decreased min_size to {self.pool_config.min_size}")
            
            # Analyze health
            avg_health_score = metrics['avg_health_score']
            if avg_health_score < 0.7:
                recommendations.append("Low average health score - check network connectivity")
                recommendations.append("Consider decreasing health check interval")
                if self.pool_config.health_check_interval > 15:
                    self.pool_config.health_check_interval = max(self.pool_config.health_check_interval - 5, 15)
                    changes_made.append(f"Decreased health check interval to {self.pool_config.health_check_interval}s")
            
            # Analyze error rate
            error_rate = metrics['error_rate']
            if error_rate > 0.1:
                recommendations.append("High error rate - check connection configuration")
                recommendations.append("Consider increasing timeout values")
                if self.connection_config.timeout < 60:
                    self.connection_config.timeout = min(self.connection_config.timeout + 10, 60)
                    changes_made.append(f"Increased timeout to {self.connection_config.timeout}s")
            
            return {
                'status': 'optimized',
                'current_metrics': metrics,
                'recommendations': recommendations,
                'changes_made': changes_made,
                'new_config': {
                    'pool_config': asdict(self.pool_config),
                    'connection_config': asdict(self.connection_config)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize pool: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def close(self):
        """Close connection pool and all connections"""
        self.running = False
        
        # Wait for background threads to finish
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
        if self.scaling_thread:
            self.scaling_thread.join(timeout=5)
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        
        # Close all connections
        with self.pool_lock:
            for connection in self.connections.values():
                connection.close()
            
            self.connections.clear()
            self.active_connections.clear()
            
            # Clear queue
            while not self.available_connections.empty():
                try:
                    self.available_connections.get_nowait()
                except queue.Empty:
                    break
        
        logger.info("Connection pool closed")

# Example usage
if __name__ == "__main__":
    # Example configuration
    connection_config = ConnectionConfig(
        host="httpbin.org",
        port=443,
        protocol="https",
        timeout=30.0,
        max_retries=3
    )
    
    pool_config = PoolConfig(
        min_size=5,
        max_size=20,
        strategy=PoolStrategy.DYNAMIC,
        enable_auto_scaling=True,
        health_check_interval=30
    )
    
    # Create connection pool
    pool = AdvancedConnectionPool(connection_config, pool_config)
    
    try:
        # Example request
        response = pool.execute_request('GET', 'https://httpbin.org/get')
        print(f"Request completed: {response.status_code}")
        
        # Get pool metrics
        metrics = pool.get_pool_metrics()
        print(f"Pool metrics: {metrics}")
        
        # Optimize pool
        optimization = pool.optimize_pool()
        print(f"Pool optimization: {optimization}")
        
    finally:
        pool.close()
