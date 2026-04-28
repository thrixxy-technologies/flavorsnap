#!/usr/bin/env python3
"""
Performance Optimizer for Load Balancer
Implements intelligent caching, connection pooling, and performance tuning
"""

import asyncio
import time
import json
import logging
import hashlib
import pickle
import gzip
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, OrderedDict
import aiohttp
import aioredis
import aiomcache
import prometheus_client as prom

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheStrategy(Enum):
    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    ADAPTIVE = "adaptive"

class CompressionType(Enum):
    NONE = "none"
    GZIP = "gzip"
    BROTLI = "brotli"
    ADAPTIVE = "adaptive"

@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: Optional[float] = None
    size: int = 0
    compressed: bool = False
    content_type: str = ""
    
    @property
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    @property
    def age(self) -> float:
        return time.time() - self.created_at
    
    @property
    def time_since_access(self) -> float:
        return time.time() - self.last_accessed

@dataclass
class PerformanceConfig:
    cache_enabled: bool = True
    cache_strategy: CacheStrategy = CacheStrategy.LRU
    cache_size: int = 1000
    cache_ttl: int = 300
    compression_enabled: bool = True
    compression_type: CompressionType = CompressionType.GZIP
    compression_threshold: int = 1024
    connection_pooling: bool = True
    max_connections: int = 100
    connection_timeout: int = 30
    keepalive_timeout: int = 60
    request_buffering: bool = True
    response_buffering: bool = True
    buffer_size: int = 8192
    prefetch_enabled: bool = True
    prefetch_threshold: float = 0.8
    adaptive_optimization: bool = True
    optimization_interval: int = 60

class LRUCache:
    """LRU Cache implementation"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.total_size = 0
    
    def get(self, key: str) -> Optional[CacheEntry]:
        if key in self.cache:
            entry = self.cache[key]
            entry.last_accessed = time.time()
            entry.access_count += 1
            self.cache.move_to_end(key)
            return entry
        return None
    
    def put(self, entry: CacheEntry):
        if entry.key in self.cache:
            # Update existing entry
            old_entry = self.cache[entry.key]
            self.total_size -= old_entry.size
            del self.cache[entry.key]
        
        self.cache[entry.key] = entry
        self.total_size += entry.size
        
        # Evict if necessary
        while len(self.cache) > self.max_size:
            oldest_key, oldest_entry = self.cache.popitem(last=False)
            self.total_size -= oldest_entry.size
    
    def remove(self, key: str) -> bool:
        if key in self.cache:
            entry = self.cache.pop(key)
            self.total_size -= entry.size
            return True
        return False
    
    def clear(self):
        self.cache.clear()
        self.total_size = 0
    
    def cleanup_expired(self):
        """Remove expired entries"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired
        ]
        
        for key in expired_keys:
            entry = self.cache.pop(key)
            self.total_size -= entry.size
        
        return len(expired_keys)

class LFUCache:
    """LFU Cache implementation"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = {}
        self.frequencies = defaultdict(int)
        self.total_size = 0
    
    def get(self, key: str) -> Optional[CacheEntry]:
        if key in self.cache:
            entry = self.cache[key]
            entry.last_accessed = time.time()
            entry.access_count += 1
            self.frequencies[key] = entry.access_count
            return entry
        return None
    
    def put(self, entry: CacheEntry):
        if entry.key in self.cache:
            old_entry = self.cache[entry.key]
            self.total_size -= old_entry.size
        elif len(self.cache) >= self.max_size:
            # Evict least frequently used
            lfu_key = min(self.frequencies.keys(), key=lambda k: self.frequencies[k])
            lfu_entry = self.cache.pop(lfu_key)
            del self.frequencies[lfu_key]
            self.total_size -= lfu_entry.size
        
        self.cache[entry.key] = entry
        self.frequencies[entry.key] = entry.access_count
        self.total_size += entry.size
    
    def remove(self, key: str) -> bool:
        if key in self.cache:
            entry = self.cache.pop(key)
            del self.frequencies[key]
            self.total_size -= entry.size
            return True
        return False
    
    def clear(self):
        self.cache.clear()
        self.frequencies.clear()
        self.total_size = 0
    
    def cleanup_expired(self):
        """Remove expired entries"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired
        ]
        
        for key in expired_keys:
            entry = self.cache.pop(key)
            del self.frequencies[key]
            self.total_size -= entry.size
        
        return len(expired_keys)

class PrometheusMetrics:
    """Prometheus metrics for performance optimization"""
    
    def __init__(self):
        self.cache_hits = prom.Counter(
            'performance_optimizer_cache_hits_total',
            'Total cache hits',
            ['cache_type', 'content_type']
        )
        
        self.cache_misses = prom.Counter(
            'performance_optimizer_cache_misses_total',
            'Total cache misses',
            ['cache_type', 'content_type']
        )
        
        self.cache_size = prom.Gauge(
            'performance_optimizer_cache_size',
            'Current cache size',
            ['cache_type']
        )
        
        self.compression_ratio = prom.Histogram(
            'performance_optimizer_compression_ratio',
            'Compression ratio achieved',
            ['compression_type', 'content_type']
        )
        
        self.connection_pool_active = prom.Gauge(
            'performance_optimizer_connection_pool_active',
            'Active connections in pool',
            ['pool_name']
        )
        
        self.connection_pool_idle = prom.Gauge(
            'performance_optimizer_connection_pool_idle',
            'Idle connections in pool',
            ['pool_name']
        )
        
        self.optimization_score = prom.Gauge(
            'performance_optimizer_score',
            'Overall optimization score',
            ['metric']
        )

class AdvancedPerformanceOptimizer:
    """Advanced performance optimizer with intelligent caching and optimization"""
    
    def __init__(self, config: PerformanceConfig):
        self.config = config
        self.cache = self._create_cache()
        self.connection_pools: Dict[str, aiohttp.TCPConnector] = {}
        self.redis_client: Optional[aioredis.Redis] = None
        self.memcached_client: Optional[aiomcache.Client] = None
        
        # Performance metrics
        self.response_times = defaultdict(list)
        self.cache_hit_rates = defaultdict(float)
        self.compression_stats = defaultdict(dict)
        
        # Metrics
        self.metrics = PrometheusMetrics()
        
        # Background tasks
        self.optimization_task = None
        self.cleanup_task = None
        
        # Initialize components
        self._initialize_components()
    
    def _create_cache(self):
        """Create cache based on strategy"""
        if self.config.cache_strategy == CacheStrategy.LRU:
            return LRUCache(self.config.cache_size)
        elif self.config.cache_strategy == CacheStrategy.LFU:
            return LFUCache(self.config.cache_size)
        else:
            return LRUCache(self.config.cache_size)  # Default to LRU
    
    def _initialize_components(self):
        """Initialize performance components"""
        # Initialize Redis if configured
        if self.config.cache_enabled:
            asyncio.create_task(self._initialize_cache_backends())
        
        # Initialize connection pools
        if self.config.connection_pooling:
            self._initialize_connection_pools()
    
    async def _initialize_cache_backends(self):
        """Initialize cache backends (Redis, Memcached)"""
        try:
            # Initialize Redis
            self.redis_client = await aioredis.from_url(
                'redis://localhost:6379',
                encoding='utf-8'
            )
            logger.info("Redis cache backend initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis: {e}")
        
        try:
            # Initialize Memcached
            self.memcached_client = aiomcache.Client("127.0.0.1", 11211)
            logger.info("Memcached cache backend initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Memcached: {e}")
    
    def _initialize_connection_pools(self):
        """Initialize connection pools"""
        # Default connection pool
        self.connection_pools['default'] = aiohttp.TCPConnector(
            limit=self.config.max_connections,
            limit_per_host=20,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=self.config.keepalive_timeout,
            enable_cleanup_closed=True
        )
        
        logger.info("Connection pools initialized")
    
    async def start(self):
        """Start performance optimizer"""
        if self.optimization_task is None:
            self.optimization_task = asyncio.create_task(self._optimization_loop())
        
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Performance optimizer started")
    
    async def stop(self):
        """Stop performance optimizer"""
        if self.optimization_task:
            self.optimization_task.cancel()
            try:
                await self.optimization_task
            except asyncio.CancelledError:
                pass
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close connection pools
        for pool in self.connection_pools.values():
            await pool.close()
        
        # Close cache clients
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Performance optimizer stopped")
    
    async def get_cached_response(self, cache_key: str) -> Optional[bytes]:
        """Get cached response"""
        if not self.config.cache_enabled:
            return None
        
        start_time = time.time()
        
        try:
            # Try local cache first
            entry = self.cache.get(cache_key)
            if entry and not entry.is_expired:
                self.metrics.cache_hits.labels(
                    cache_type='local',
                    content_type=entry.content_type
                ).inc()
                return entry.value
            
            # Try Redis cache
            if self.redis_client:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    # Decompress if needed
                    if self.config.compression_enabled:
                        cached_data = await self._decompress_data(cached_data)
                    
                    # Update local cache
                    entry = CacheEntry(
                        key=cache_key,
                        value=cached_data,
                        created_at=time.time(),
                        last_accessed=time.time(),
                        ttl=self.config.cache_ttl,
                        size=len(cached_data)
                    )
                    self.cache.put(entry)
                    
                    self.metrics.cache_hits.labels(
                        cache_type='redis',
                        content_type='unknown'
                    ).inc()
                    return cached_data
            
            # Try Memcached
            if self.memcached_client:
                cached_data = await self.memcached_client.get(cache_key.encode())
                if cached_data:
                    if self.config.compression_enabled:
                        cached_data = await self._decompress_data(cached_data)
                    
                    entry = CacheEntry(
                        key=cache_key,
                        value=cached_data,
                        created_at=time.time(),
                        last_accessed=time.time(),
                        ttl=self.config.cache_ttl,
                        size=len(cached_data)
                    )
                    self.cache.put(entry)
                    
                    self.metrics.cache_hits.labels(
                        cache_type='memcached',
                        content_type='unknown'
                    ).inc()
                    return cached_data
            
            self.metrics.cache_misses.labels(
                cache_type='all',
                content_type='unknown'
            ).inc()
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.metrics.cache_misses.labels(
                cache_type='error',
                content_type='unknown'
            ).inc()
            return None
    
    async def cache_response(self, cache_key: str, response_data: bytes, 
                          content_type: str = "", ttl: Optional[int] = None) -> bool:
        """Cache response data"""
        if not self.config.cache_enabled:
            return False
        
        try:
            # Compress if enabled and data is large enough
            compressed_data = response_data
            compression_used = False
            
            if (self.config.compression_enabled and 
                len(response_data) > self.config.compression_threshold):
                
                compressed_data = await self._compress_data(response_data)
                compression_used = True
                
                # Record compression ratio
                ratio = len(compressed_data) / len(response_data)
                self.metrics.compression_ratio.labels(
                    compression_type=self.config.compression_type.value,
                    content_type=content_type
                ).observe(ratio)
            
            # Cache locally
            entry = CacheEntry(
                key=cache_key,
                value=compressed_data,
                created_at=time.time(),
                last_accessed=time.time(),
                ttl=ttl or self.config.cache_ttl,
                size=len(compressed_data),
                compressed=compression_used,
                content_type=content_type
            )
            self.cache.put(entry)
            
            # Cache in Redis
            if self.redis_client:
                await self.redis_client.setex(
                    cache_key,
                    ttl or self.config.cache_ttl,
                    compressed_data
                )
            
            # Cache in Memcached
            if self.memcached_client:
                await self.memcached_client.set(
                    cache_key.encode(),
                    compressed_data,
                    exptime=ttl or self.config.cache_ttl
                )
            
            # Update metrics
            self.metrics.cache_size.labels(cache_type='local').set(len(self.cache.cache))
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def _compress_data(self, data: bytes) -> bytes:
        """Compress data based on configuration"""
        if self.config.compression_type == CompressionType.GZIP:
            return gzip.compress(data)
        elif self.config.compression_type == CompressionType.BROTLI:
            try:
                import brotli
                return brotli.compress(data)
            except ImportError:
                logger.warning("Brotli not available, falling back to gzip")
                return gzip.compress(data)
        else:
            return data
    
    async def _decompress_data(self, data: bytes) -> bytes:
        """Decompress data"""
        try:
            # Try gzip first
            return gzip.decompress(data)
        except:
            # Try brotli
            try:
                import brotli
                return brotli.decompress(data)
            except:
                return data
    
    def generate_cache_key(self, request_info: Dict[str, Any]) -> str:
        """Generate cache key from request"""
        key_parts = [
            request_info.get('method', 'GET'),
            request_info.get('path', '/'),
            str(sorted(request_info.get('headers', {}).items())),
            str(sorted(request_info.get('params', {}).items()))
        ]
        
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def get_connection_pool(self, pool_name: str = 'default') -> aiohttp.TCPConnector:
        """Get connection pool"""
        if pool_name not in self.connection_pools:
            self.connection_pools[pool_name] = aiohttp.TCPConnector(
                limit=self.config.max_connections,
                limit_per_host=20,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=self.config.keepalive_timeout,
                enable_cleanup_closed=True
            )
        
        return self.connection_pools[pool_name]
    
    async def optimize_request(self, request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize request before processing"""
        optimized_request = request_info.copy()
        
        # Add caching headers
        if self.config.cache_enabled:
            optimized_request['headers'] = optimized_request.get('headers', {})
            optimized_request['headers']['Cache-Control'] = 'max-age=300'
        
        # Add compression headers
        if self.config.compression_enabled:
            optimized_request['headers'] = optimized_request.get('headers', {})
            optimized_request['headers']['Accept-Encoding'] = 'gzip, deflate, br'
        
        return optimized_request
    
    async def optimize_response(self, response_data: bytes, content_type: str = "") -> bytes:
        """Optimize response data"""
        optimized_data = response_data
        
        # Compress if enabled and beneficial
        if (self.config.compression_enabled and 
            len(response_data) > self.config.compression_threshold):
            
            compressed_data = await self._compress_data(response_data)
            
            # Only use compression if it actually reduces size
            if len(compressed_data) < len(response_data):
                optimized_data = compressed_data
                
                # Record compression ratio
                ratio = len(compressed_data) / len(response_data)
                self.metrics.compression_ratio.labels(
                    compression_type=self.config.compression_type.value,
                    content_type=content_type
                ).observe(ratio)
        
        return optimized_data
    
    async def _optimization_loop(self):
        """Background optimization loop"""
        while True:
            try:
                if self.config.adaptive_optimization:
                    await self._adaptive_optimization()
                
                await asyncio.sleep(self.config.optimization_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Optimization loop error: {e}")
                await asyncio.sleep(30)
    
    async def _adaptive_optimization(self):
        """Perform adaptive optimization based on metrics"""
        # Analyze cache hit rates
        for cache_type in ['local', 'redis', 'memcached']:
            hit_rate = self._calculate_cache_hit_rate(cache_type)
            self.cache_hit_rates[cache_type] = hit_rate
            
            # Adjust cache size if needed
            if hit_rate < 0.7 and self.config.cache_size < 10000:
                self.config.cache_size = int(self.config.cache_size * 1.2)
                logger.info(f"Increased cache size to {self.config.cache_size}")
            elif hit_rate > 0.95 and self.config.cache_size > 100:
                self.config.cache_size = int(self.config.cache_size * 0.9)
                logger.info(f"Decreased cache size to {self.config.cache_size}")
        
        # Update optimization score metrics
        self.metrics.optimization_score.labels(metric='cache_hit_rate').set(
            max(self.cache_hit_rates.values()) if self.cache_hit_rates else 0
        )
        
        # Update connection pool metrics
        for name, pool in self.connection_pools.items():
            self.metrics.connection_pool_active.labels(pool_name=name).set(
                len(pool._conns) if hasattr(pool, '_conns') else 0
            )
            self.metrics.connection_pool_idle.labels(pool_name=name).set(
                len(pool._conns) if hasattr(pool, '_conns') else 0
            )
    
    def _calculate_cache_hit_rate(self, cache_type: str) -> float:
        """Calculate cache hit rate for a cache type"""
        hits = self.metrics.cache_hits.labels(cache_type=cache_type, content_type='')._value._value
        misses = self.metrics.cache_misses.labels(cache_type=cache_type, content_type='')._value._value
        
        total = hits + misses
        return hits / total if total > 0 else 0.0
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                # Clean up expired cache entries
                expired_count = self.cache.cleanup_expired()
                if expired_count > 0:
                    logger.debug(f"Cleaned up {expired_count} expired cache entries")
                
                # Update metrics
                self.metrics.cache_size.labels(cache_type='local').set(len(self.cache.cache))
                
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(60)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'cache_enabled': self.config.cache_enabled,
            'cache_strategy': self.config.cache_strategy.value,
            'cache_size': self.config.cache_size,
            'current_cache_entries': len(self.cache.cache),
            'compression_enabled': self.config.compression_enabled,
            'compression_type': self.config.compression_type.value,
            'connection_pooling': self.config.connection_pooling,
            'active_connection_pools': len(self.connection_pools),
            'cache_hit_rates': dict(self.cache_hit_rates),
            'metrics': {
                'cache_hits': self.metrics.cache_hits._value._value,
                'cache_misses': self.metrics.cache_misses._value._value,
                'cache_size': self.metrics.cache_size._value._value,
                'connection_pool_active': self.metrics.connection_pool_active._value._value,
                'connection_pool_idle': self.metrics.connection_pool_idle._value._value
            }
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update performance configuration"""
        for key, value in new_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Recreate cache if strategy changed
        if 'cache_strategy' in new_config:
            self.cache = self._create_cache()
        
        logger.info("Performance configuration updated")

# Example usage
if __name__ == "__main__":
    async def main():
        config = PerformanceConfig(
            cache_enabled=True,
            cache_strategy=CacheStrategy.LRU,
            cache_size=1000,
            compression_enabled=True,
            connection_pooling=True,
            adaptive_optimization=True
        )
        
        optimizer = AdvancedPerformanceOptimizer(config)
        await optimizer.start()
        
        # Example caching
        request_info = {
            'method': 'GET',
            'path': '/api/data',
            'headers': {'Accept': 'application/json'}
        }
        
        cache_key = optimizer.generate_cache_key(request_info)
        
        # Cache some data
        test_data = b'{"message": "Hello, World!"}' * 100
        await optimizer.cache_response(cache_key, test_data, 'application/json')
        
        # Retrieve cached data
        cached_data = await optimizer.get_cached_response(cache_key)
        print(f"Cached data retrieved: {len(cached_data) if cached_data else 0} bytes")
        
        # Get performance stats
        stats = optimizer.get_performance_stats()
        print(f"Performance stats: {json.dumps(stats, indent=2, default=str)}")
        
        await asyncio.sleep(60)
        await optimizer.stop()
    
    asyncio.run(main())
