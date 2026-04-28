#!/usr/bin/env python3
"""
Advanced Network Optimizer for FlavorSnap ML Model API
Implements network optimization with connection pooling, compression, and protocol optimization
"""

import os
import time
import logging
import threading
import asyncio
import gzip
import zlib
import brotli
import lz4.frame
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import socket
import ssl
from urllib.parse import urlparse
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
        logging.FileHandler('logs/network_optimizer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CompressionType(Enum):
    """Compression algorithms"""
    NONE = "none"
    GZIP = "gzip"
    DEFLATE = "deflate"
    BROTLI = "brotli"
    LZ4 = "lz4"

class ProtocolType(Enum):
    """Network protocols"""
    HTTP_1_1 = "http/1.1"
    HTTP_2 = "http/2"
    HTTPS = "https"
    WEBSOCKET = "websocket"

@dataclass
class NetworkConfig:
    """Network optimization configuration"""
    enable_connection_pooling: bool = True
    pool_size: int = 20
    max_retries: int = 3
    backoff_factor: float = 0.3
    timeout_seconds: float = 30.0
    enable_compression: bool = True
    compression_type: CompressionType = CompressionType.GZIP
    compression_level: int = 6
    enable_protocol_optimization: bool = True
    preferred_protocol: ProtocolType = ProtocolType.HTTP_2
    enable_keepalive: bool = True
    keepalive_timeout: int = 30
    enable_bandwidth_optimization: bool = True
    max_bandwidth_mbps: float = 100.0
    enable_latency_optimization: bool = True
    target_latency_ms: float = 100.0
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    enable_monitoring: bool = True

@dataclass
class NetworkMetrics:
    """Network performance metrics"""
    timestamp: datetime
    endpoint: str
    protocol: str
    response_time_ms: float
    bandwidth_mbps: float
    compression_ratio: float
    connection_pool_size: int
    active_connections: int
    request_count: int
    error_count: int
    cache_hit_rate: float

class NetworkOptimizer:
    """Advanced network optimization system"""
    
    def __init__(self, config: NetworkConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.connection_pool = {}
        self.cache = {}
        self.metrics_history = []
        self.compression_stats = {}
        self.protocol_stats = {}
        self.bandwidth_tracker = {}
        self.latency_tracker = {}
        
        # Initialize network components
        self._init_session()
        self._init_connection_pool()
        self._init_compression()
        self._init_protocol_optimization()
        
        logger.info("NetworkOptimizer initialized")
    
    def _init_session(self):
        """Initialize HTTP session with optimizations"""
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        
        # Create custom adapter
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.config.pool_size,
            pool_maxsize=self.config.pool_size
        )
        
        # Mount adapters for different protocols
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Configure session defaults
        self.session.headers.update({
            'User-Agent': 'FlavorSnap-NetworkOptimizer/1.0',
            'Accept-Encoding': self._get_accept_encoding(),
            'Connection': 'keep-alive' if self.config.enable_keepalive else 'close'
        })
        
        logger.info("HTTP session initialized with optimizations")
    
    def _init_connection_pool(self):
        """Initialize connection pool management"""
        if not self.config.enable_connection_pooling:
            return
        
        # Configure connection pool parameters
        self.connection_pool_config = {
            'pool_size': self.config.pool_size,
            'max_retries': self.config.max_retries,
            'timeout': self.config.timeout_seconds,
            'keepalive': self.config.enable_keepalive
        }
        
        logger.info(f"Connection pool initialized with size: {self.config.pool_size}")
    
    def _init_compression(self):
        """Initialize compression settings"""
        if not self.config.enable_compression:
            return
        
        self.compression_stats = {
            'total_requests': 0,
            'compressed_requests': 0,
            'total_bytes_original': 0,
            'total_bytes_compressed': 0,
            'compression_ratio': 0.0
        }
        
        logger.info(f"Compression enabled: {self.config.compression_type.value}")
    
    def _init_protocol_optimization(self):
        """Initialize protocol optimization"""
        if not self.config.enable_protocol_optimization:
            return
        
        self.protocol_stats = {
            'http_1_1': {'count': 0, 'avg_response_time': 0.0},
            'http_2': {'count': 0, 'avg_response_time': 0.0},
            'https': {'count': 0, 'avg_response_time': 0.0}
        }
        
        logger.info(f"Protocol optimization enabled: {self.config.preferred_protocol.value}")
    
    def _get_accept_encoding(self) -> str:
        """Get Accept-Encoding header based on available compression"""
        encodings = []
        
        if self.config.enable_compression:
            if self.config.compression_type in [CompressionType.GZIP, CompressionType.DEFLATE]:
                encodings.extend(['gzip', 'deflate'])
            if self.config.compression_type == CompressionType.BROTLI:
                encodings.append('br')
            if self.config.compression_type == CompressionType.LZ4:
                encodings.append('lz4')
        
        return ', '.join(encodings) if encodings else 'identity'
    
    def make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make optimized HTTP request"""
        start_time = time.time()
        
        try:
            # Apply optimizations
            self._apply_request_optimizations(kwargs)
            
            # Make request
            response = self.session.request(method, url, **kwargs)
            
            # Record metrics
            response_time = (time.time() - start_time) * 1000
            self._record_request_metrics(url, response_time, response)
            
            return response
            
        except Exception as e:
            self._record_error_metrics(url, str(e))
            raise
    
    def _apply_request_optimizations(self, kwargs: Dict[str, Any]):
        """Apply network optimizations to request"""
        # Set timeout
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.config.timeout_seconds
        
        # Apply compression to request data if applicable
        if self.config.enable_compression and 'data' in kwargs:
            kwargs['data'] = self._compress_data(kwargs['data'])
        
        # Apply caching headers
        if self.config.enable_caching:
            headers = kwargs.get('headers', {})
            if 'Cache-Control' not in headers:
                headers['Cache-Control'] = f'max-age={self.config.cache_ttl_seconds}'
            kwargs['headers'] = headers
    
    def _compress_data(self, data: Any) -> Any:
        """Compress request data"""
        if not data or not isinstance(data, (str, bytes)):
            return data
        
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            if self.config.compression_type == CompressionType.GZIP:
                compressed = gzip.compress(data, compresslevel=self.config.compression_level)
            elif self.config.compression_type == CompressionType.DEFLATE:
                compressed = zlib.compress(data, level=self.config.compression_level)
            elif self.config.compression_type == CompressionType.BROTLI:
                compressed = brotli.compress(data, quality=self.config.compression_level)
            elif self.config.compression_type == CompressionType.LZ4:
                compressed = lz4.frame.compress(data, compression_level=self.config.compression_level)
            else:
                return data
            
            # Update compression stats
            self.compression_stats['compressed_requests'] += 1
            self.compression_stats['total_bytes_original'] += len(data)
            self.compression_stats['total_bytes_compressed'] += len(compressed)
            
            return compressed
            
        except Exception as e:
            logger.warning(f"Compression failed: {str(e)}")
            return data
    
    def _decompress_data(self, data: bytes, encoding: str) -> bytes:
        """Decompress response data"""
        try:
            if encoding == 'gzip':
                return gzip.decompress(data)
            elif encoding == 'deflate':
                return zlib.decompress(data)
            elif encoding == 'br':
                return brotli.decompress(data)
            elif encoding == 'lz4':
                return lz4.frame.decompress(data)
            else:
                return data
        except Exception as e:
            logger.warning(f"Decompression failed: {str(e)}")
            return data
    
    def _record_request_metrics(self, url: str, response_time: float, response: requests.Response):
        """Record request metrics"""
        try:
            # Parse URL to get protocol
            parsed_url = urlparse(url)
            protocol = parsed_url.scheme
            
            # Calculate bandwidth
            content_length = len(response.content) if response.content else 0
            bandwidth_mbps = (content_length * 8) / (response_time / 1000) / (1024 * 1024)
            
            # Calculate compression ratio
            compression_ratio = 1.0
            if response.headers.get('content-encoding'):
                original_size = int(response.headers.get('content-length', 0))
                compressed_size = len(response.content)
                if original_size > 0:
                    compression_ratio = compressed_size / original_size
            
            # Create metrics
            metrics = NetworkMetrics(
                timestamp=datetime.now(pytz.UTC),
                endpoint=url,
                protocol=protocol,
                response_time_ms=response_time,
                bandwidth_mbps=bandwidth_mbps,
                compression_ratio=compression_ratio,
                connection_pool_size=self.config.pool_size,
                active_connections=self._get_active_connections(),
                request_count=1,
                error_count=0,
                cache_hit_rate=self._get_cache_hit_rate()
            )
            
            # Store metrics
            self.metrics_history.append(metrics)
            
            # Keep only last 1000 metrics
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
            
            # Update protocol stats
            if protocol in self.protocol_stats:
                self.protocol_stats[protocol]['count'] += 1
                current_avg = self.protocol_stats[protocol]['avg_response_time']
                count = self.protocol_stats[protocol]['count']
                self.protocol_stats[protocol]['avg_response_time'] = (
                    (current_avg * (count - 1) + response_time) / count
                )
            
            # Update bandwidth tracker
            self.bandwidth_tracker[url] = bandwidth_mbps
            
            # Update latency tracker
            self.latency_tracker[url] = response_time
            
            # Check for optimization opportunities
            self._check_optimization_opportunities(metrics)
            
        except Exception as e:
            logger.error(f"Failed to record metrics: {str(e)}")
    
    def _record_error_metrics(self, url: str, error: str):
        """Record error metrics"""
        try:
            metrics = NetworkMetrics(
                timestamp=datetime.now(pytz.UTC),
                endpoint=url,
                protocol="unknown",
                response_time_ms=0,
                bandwidth_mbps=0,
                compression_ratio=1.0,
                connection_pool_size=self.config.pool_size,
                active_connections=self._get_active_connections(),
                request_count=0,
                error_count=1,
                cache_hit_rate=self._get_cache_hit_rate()
            )
            
            self.metrics_history.append(metrics)
            
        except Exception as e:
            logger.error(f"Failed to record error metrics: {str(e)}")
    
    def _get_active_connections(self) -> int:
        """Get number of active connections"""
        try:
            # Get network connection count
            connections = psutil.net_connections()
            return len([c for c in connections if c.status == 'ESTABLISHED'])
        except Exception:
            return 0
    
    def _get_cache_hit_rate(self) -> float:
        """Get cache hit rate"""
        if not self.cache:
            return 0.0
        
        # Simplified cache hit rate calculation
        total_requests = len(self.metrics_history)
        if total_requests == 0:
            return 0.0
        
        # Count cache hits (simplified)
        cache_hits = sum(1 for m in self.metrics_history[-100:] if m.response_time_ms < 50)
        return cache_hits / min(total_requests, 100)
    
    def _check_optimization_opportunities(self, metrics: NetworkMetrics):
        """Check for optimization opportunities"""
        # Check latency
        if self.config.enable_latency_optimization:
            if metrics.response_time_ms > self.config.target_latency_ms:
                self._suggest_latency_optimization(metrics)
        
        # Check bandwidth
        if self.config.enable_bandwidth_optimization:
            if metrics.bandwidth_mbps > self.config.max_bandwidth_mbps:
                self._suggest_bandwidth_optimization(metrics)
        
        # Check compression
        if self.config.enable_compression:
            if metrics.compression_ratio > 0.8:  # Low compression
                self._suggest_compression_optimization(metrics)
    
    def _suggest_latency_optimization(self, metrics: NetworkMetrics):
        """Suggest latency optimizations"""
        suggestions = []
        
        if metrics.response_time_ms > 500:
            suggestions.append("Consider enabling HTTP/2 for multiplexing")
            suggestions.append("Implement request batching")
            suggestions.append("Use CDN for static content")
        
        if suggestions:
            logger.info(f"Latency optimization suggestions for {metrics.endpoint}: {suggestions}")
    
    def _suggest_bandwidth_optimization(self, metrics: NetworkMetrics):
        """Suggest bandwidth optimizations"""
        suggestions = []
        
        if metrics.compression_ratio > 0.8:
            suggestions.append("Enable data compression")
            suggestions.append("Use more efficient compression algorithm")
        
        if metrics.bandwidth_mbps > self.config.max_bandwidth_mbps:
            suggestions.append("Implement request throttling")
            suggestions.append("Use data streaming for large payloads")
        
        if suggestions:
            logger.info(f"Bandwidth optimization suggestions for {metrics.endpoint}: {suggestions}")
    
    def _suggest_compression_optimization(self, metrics: NetworkMetrics):
        """Suggest compression optimizations"""
        suggestions = []
        
        if self.config.compression_type == CompressionType.GZIP:
            suggestions.append("Try Brotli compression for better ratios")
        elif self.config.compression_type == CompressionType.NONE:
            suggestions.append("Enable compression to reduce bandwidth")
        
        if self.config.compression_level < 6:
            suggestions.append("Increase compression level")
        
        if suggestions:
            logger.info(f"Compression optimization suggestions for {metrics.endpoint}: {suggestions}")
    
    def get_network_metrics(self, hours: int = 1) -> Dict[str, Any]:
        """Get network performance metrics"""
        try:
            cutoff_time = datetime.now(pytz.UTC) - timedelta(hours=hours)
            recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
            
            if not recent_metrics:
                return {}
            
            # Calculate aggregates
            total_requests = len(recent_metrics)
            total_errors = sum(m.error_count for m in recent_metrics)
            avg_response_time = sum(m.response_time_ms for m in recent_metrics) / total_requests
            avg_bandwidth = sum(m.bandwidth_mbps for m in recent_metrics) / total_requests
            avg_compression_ratio = sum(m.compression_ratio for m in recent_metrics) / total_requests
            avg_cache_hit_rate = sum(m.cache_hit_rate for m in recent_metrics) / total_requests
            
            return {
                'time_range_hours': hours,
                'total_requests': total_requests,
                'total_errors': total_errors,
                'error_rate': total_errors / total_requests if total_requests > 0 else 0,
                'avg_response_time_ms': avg_response_time,
                'avg_bandwidth_mbps': avg_bandwidth,
                'avg_compression_ratio': avg_compression_ratio,
                'avg_cache_hit_rate': avg_cache_hit_rate,
                'protocol_stats': self.protocol_stats,
                'compression_stats': self.compression_stats,
                'connection_pool_size': self.config.pool_size,
                'active_connections': self._get_active_connections()
            }
            
        except Exception as e:
            logger.error(f"Failed to get network metrics: {str(e)}")
            return {}
    
    def optimize_connection_pool(self, target_response_time_ms: float = 100.0) -> Dict[str, Any]:
        """Optimize connection pool size based on performance"""
        try:
            current_metrics = self.get_network_metrics(hours=1)
            
            if not current_metrics:
                return {'status': 'no_data', 'message': 'No metrics available'}
            
            avg_response_time = current_metrics.get('avg_response_time_ms', 0)
            current_pool_size = self.config.pool_size
            
            suggestions = []
            new_pool_size = current_pool_size
            
            # Analyze response time vs pool size
            if avg_response_time > target_response_time_ms:
                if current_pool_size < 50:
                    new_pool_size = min(current_pool_size + 10, 50)
                    suggestions.append(f"Increase pool size to {new_pool_size}")
                else:
                    suggestions.append("Pool size at maximum, consider other optimizations")
            elif avg_response_time < target_response_time_ms / 2:
                if current_pool_size > 5:
                    new_pool_size = max(current_pool_size - 5, 5)
                    suggestions.append(f"Decrease pool size to {new_pool_size} to save resources")
            
            # Apply new pool size if changed
            if new_pool_size != current_pool_size:
                self.config.pool_size = new_pool_size
                self._init_session()  # Reinitialize with new pool size
            
            return {
                'status': 'optimized',
                'current_pool_size': current_pool_size,
                'new_pool_size': new_pool_size,
                'avg_response_time_ms': avg_response_time,
                'target_response_time_ms': target_response_time_ms,
                'suggestions': suggestions
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize connection pool: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def optimize_compression(self, target_compression_ratio: float = 0.5) -> Dict[str, Any]:
        """Optimize compression settings"""
        try:
            current_metrics = self.get_network_metrics(hours=1)
            
            if not current_metrics:
                return {'status': 'no_data', 'message': 'No metrics available'}
            
            avg_compression_ratio = current_metrics.get('avg_compression_ratio', 1.0)
            current_compression_type = self.config.compression_type
            current_compression_level = self.config.compression_level
            
            suggestions = []
            new_compression_type = current_compression_type
            new_compression_level = current_compression_level
            
            # Analyze compression ratio
            if avg_compression_ratio > target_compression_ratio:
                # Need better compression
                if current_compression_type == CompressionType.NONE:
                    new_compression_type = CompressionType.GZIP
                    suggestions.append("Enable GZIP compression")
                elif current_compression_type == CompressionType.GZIP:
                    new_compression_type = CompressionType.BROTLI
                    suggestions.append("Switch to Brotli compression for better ratio")
                
                if current_compression_level < 9:
                    new_compression_level = min(current_compression_level + 2, 9)
                    suggestions.append(f"Increase compression level to {new_compression_level}")
            
            # Apply new compression settings if changed
            if new_compression_type != current_compression_type or new_compression_level != current_compression_level:
                self.config.compression_type = new_compression_type
                self.config.compression_level = new_compression_level
                self._init_session()  # Reinitialize with new compression
            
            return {
                'status': 'optimized',
                'current_compression_type': current_compression_type.value,
                'new_compression_type': new_compression_type.value,
                'current_compression_level': current_compression_level,
                'new_compression_level': new_compression_level,
                'avg_compression_ratio': avg_compression_ratio,
                'target_compression_ratio': target_compression_ratio,
                'suggestions': suggestions
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize compression: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def optimize_protocol(self, target_response_time_ms: float = 100.0) -> Dict[str, Any]:
        """Optimize network protocol"""
        try:
            current_metrics = self.get_network_metrics(hours=1)
            
            if not current_metrics:
                return {'status': 'no_data', 'message': 'No metrics available'}
            
            protocol_stats = current_metrics.get('protocol_stats', {})
            avg_response_time = current_metrics.get('avg_response_time_ms', 0)
            current_protocol = self.config.preferred_protocol
            
            suggestions = []
            new_protocol = current_protocol
            
            # Analyze protocol performance
            if avg_response_time > target_response_time_ms:
                if current_protocol == ProtocolType.HTTP_1_1:
                    new_protocol = ProtocolType.HTTP_2
                    suggestions.append("Switch to HTTP/2 for better performance")
                elif current_protocol == ProtocolType.HTTP_2:
                    suggestions.append("Consider HTTP/3 when available")
            
            # Apply new protocol if changed
            if new_protocol != current_protocol:
                self.config.preferred_protocol = new_protocol
                self._init_session()  # Reinitialize with new protocol
            
            return {
                'status': 'optimized',
                'current_protocol': current_protocol.value,
                'new_protocol': new_protocol.value,
                'avg_response_time_ms': avg_response_time,
                'target_response_time_ms': target_response_time_ms,
                'protocol_stats': protocol_stats,
                'suggestions': suggestions
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize protocol: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def run_network_analysis(self) -> Dict[str, Any]:
        """Run comprehensive network analysis"""
        try:
            # Get current metrics
            metrics_1h = self.get_network_metrics(hours=1)
            metrics_24h = self.get_network_metrics(hours=24)
            
            # Run optimizations
            pool_optimization = self.optimize_connection_pool()
            compression_optimization = self.optimize_compression()
            protocol_optimization = self.optimize_protocol()
            
            # Generate recommendations
            recommendations = []
            
            if metrics_1h.get('error_rate', 0) > 0.05:
                recommendations.append("High error rate detected - check network connectivity")
            
            if metrics_1h.get('avg_response_time_ms', 0) > 200:
                recommendations.append("High response time - consider protocol optimization")
            
            if metrics_1h.get('avg_compression_ratio', 1.0) > 0.8:
                recommendations.append("Low compression efficiency - review compression settings")
            
            if metrics_1h.get('avg_cache_hit_rate', 0) < 0.5:
                recommendations.append("Low cache hit rate - review caching strategy")
            
            return {
                'timestamp': datetime.now(pytz.UTC).isoformat(),
                'metrics_1h': metrics_1h,
                'metrics_24h': metrics_24h,
                'optimizations': {
                    'connection_pool': pool_optimization,
                    'compression': compression_optimization,
                    'protocol': protocol_optimization
                },
                'recommendations': recommendations,
                'config': asdict(self.config)
            }
            
        except Exception as e:
            logger.error(f"Failed to run network analysis: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def close(self):
        """Close network optimizer and cleanup resources"""
        try:
            if self.session:
                self.session.close()
            
            logger.info("NetworkOptimizer closed")
            
        except Exception as e:
            logger.error(f"Failed to close NetworkOptimizer: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Example configuration
    config = NetworkConfig(
        enable_connection_pooling=True,
        pool_size=20,
        enable_compression=True,
        compression_type=CompressionType.GZIP,
        enable_protocol_optimization=True,
        preferred_protocol=ProtocolType.HTTP_2,
        enable_bandwidth_optimization=True,
        enable_latency_optimization=True
    )
    
    # Initialize network optimizer
    optimizer = NetworkOptimizer(config)
    
    try:
        # Example request
        response = optimizer.make_request('GET', 'https://httpbin.org/get')
        print(f"Request completed: {response.status_code}")
        
        # Get metrics
        metrics = optimizer.get_network_metrics()
        print(f"Network metrics: {metrics}")
        
        # Run analysis
        analysis = optimizer.run_network_analysis()
        print(f"Network analysis: {analysis}")
        
    finally:
        optimizer.close()
