"""
Advanced Response Caching with ETags, Conditional Requests, and Cache Invalidation
"""

import hashlib
import json
import time
import gzip
import logging
from typing import Dict, Any, Optional, Tuple, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import redis
from flask import Flask, request, Response, make_response, jsonify, current_app
import pickle
import zlib
from functools import wraps

logger = logging.getLogger(__name__)

class CacheStrategy(Enum):
    """Cache strategies for different types of responses"""
    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    ADAPTIVE = "adaptive"

class CacheLevel(Enum):
    """Cache levels for hierarchical caching"""
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"
    DISTRIBUTED = "distributed"

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    etag: str
    content_type: str
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int
    last_accessed: datetime
    size_bytes: int
    compressed: bool
    tags: List[str]
    metadata: Dict[str, Any]

@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int
    misses: int
    sets: int
    deletes: int
    evictions: int
    size_bytes: int
    entry_count: int
    hit_rate: float
    avg_access_time: float

class CacheManager:
    """Advanced cache manager with ETags and conditional requests"""
    
    def __init__(self, app: Flask = None, redis_url: str = None):
        self.app = app
        self.redis_url = redis_url or "redis://localhost:6379/0"
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.cache_stats = CacheStats(0, 0, 0, 0, 0, 0, 0, 0.0, 0.0)
        self.max_memory_size = 100 * 1024 * 1024  # 100MB
        self.default_ttl = timedelta(hours=1)
        self.compression_threshold = 1024  # 1KB
        self.redis_client = None
        
        # Cache configuration
        self.cache_config = {
            'enabled': True,
            'default_ttl': 3600,  # 1 hour
            'max_entries': 10000,
            'compression_enabled': True,
            'compression_level': 6,
            'etag_enabled': True,
            'conditional_requests': True
        }
        
        # Cache warming configuration
        self.warmup_config = {
            'enabled': True,
            'endpoints': ['/api/classes', '/api/models', '/health'],
            'interval': 300,  # 5 minutes
            'concurrent_requests': 5
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize cache manager with Flask app"""
        self.app = app
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.from_url(self.redis_url)
            self.redis_client.ping()
            logger.info("Redis cache backend connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, using memory cache only")
        
        # Add caching middleware
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        # Add cache management endpoints
        self._register_cache_endpoints(app)
        
        # Start cache warming
        if self.warmup_config['enabled']:
            self._start_cache_warming()
    
    def _register_cache_endpoints(self, app: Flask):
        """Register cache management endpoints"""
        
        @app.route('/cache/stats', methods=['GET'])
        def cache_stats():
            """Get cache statistics"""
            return jsonify(asdict(self.get_cache_stats()))
        
        @app.route('/cache/clear', methods=['POST'])
        def cache_clear():
            """Clear cache"""
            pattern = request.json.get('pattern', '*') if request.json else '*'
            cleared = self.clear_cache(pattern)
            return jsonify({'cleared_entries': cleared})
        
        @app.route('/cache/invalidate', methods=['POST'])
        def cache_invalidate():
            """Invalidate cache entries by tags"""
            tags = request.json.get('tags', []) if request.json else []
            invalidated = self.invalidate_by_tags(tags)
            return jsonify({'invalidated_entries': invalidated})
        
        @app.route('/cache/warmup', methods=['POST'])
        def manual_warmup():
            """Manually trigger cache warming"""
            endpoints = request.json.get('endpoints', self.warmup_config['endpoints'])
            warmed = self.warm_cache(endpoints)
            return jsonify({'warmed_endpoints': warmed})
        
        @app.route('/cache/config', methods=['GET', 'PUT'])
        def cache_config():
            """Get or update cache configuration"""
            if request.method == 'GET':
                return jsonify(self.cache_config)
            else:
                new_config = request.get_json()
                self.cache_config.update(new_config)
                return jsonify({'message': 'Configuration updated'})
    
    def _before_request(self):
        """Handle cache lookup and conditional requests"""
        if not self.cache_config['enabled']:
            return
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Check for conditional requests
        if self.cache_config['conditional_requests']:
            if_none_match = request.headers.get('If-None-Match')
            if_modified_since = request.headers.get('If-Modified-Since')
            
            entry = self.get(cache_key)
            if entry:
                # ETag match
                if if_none_match and entry.etag == if_none_match:
                    return Response('', status=304, headers={
                        'ETag': entry.etag,
                        'Cache-Control': self._get_cache_control_headers(entry)
                    })
                
                # Modified-Since check
                if if_modified_since:
                    try:
                        if_modified_since_dt = datetime.fromisoformat(if_modified_since.replace('Z', '+00:00'))
                        if entry.created_at <= if_modified_since_dt:
                            return Response('', status=304, headers={
                                'ETag': entry.etag,
                                'Cache-Control': self._get_cache_control_headers(entry)
                            })
                    except ValueError:
                        pass
        
        # Store cache key for later use
        request.cache_key = cache_key
    
    def _after_request(self, response: Response) -> Response:
        """Handle cache storage for responses"""
        if not self.cache_config['enabled']:
            return response
        
        # Don't cache error responses
        if response.status_code >= 400:
            return response
        
        # Check if response should be cached
        if not self._should_cache_response(request, response):
            return response
        
        cache_key = getattr(request, 'cache_key', None)
        if not cache_key:
            cache_key = self._generate_cache_key(request)
        
        # Extract response data
        try:
            content_type = response.headers.get('Content-Type', 'application/json')
            
            # Get response data
            if hasattr(response, 'json'):
                data = response.json
            else:
                data = response.get_data(as_text=True)
            
            # Store in cache
            ttl = self._get_cache_ttl(request, response)
            self.set(cache_key, data, content_type, ttl)
            
            # Add cache headers to response
            entry = self.get(cache_key)
            if entry:
                response.headers['ETag'] = entry.etag
                response.headers['Cache-Control'] = self._get_cache_control_headers(entry)
                response.headers['Last-Modified'] = entry.created_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        except Exception as e:
            logger.error(f"Cache storage failed: {e}")
        
        return response
    
    def _generate_cache_key(self, request) -> str:
        """Generate cache key from request"""
        key_parts = [
            request.method,
            request.path,
            str(sorted(request.args.items())),
            str(sorted(request.form.items())) if request.form else '',
            request.headers.get('Accept', ''),
            request.headers.get('Accept-Language', ''),
            request.headers.get('X-User-ID', '')
        ]
        
        key_string = '|'.join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _should_cache_response(self, request, response) -> bool:
        """Determine if response should be cached"""
        # Don't cache if explicitly disabled
        cache_control = response.headers.get('Cache-Control', '')
        if 'no-cache' in cache_control or 'private' in cache_control:
            return False
        
        # Don't cache large responses
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
            return False
        
        # Cache GET requests by default
        if request.method == 'GET':
            return True
        
        # Cache specific POST requests (e.g., search results)
        if request.method == 'POST' and request.path in ['/api/search', '/api/predict']:
            return True
        
        return False
    
    def _get_cache_ttl(self, request, response) -> timedelta:
        """Get cache TTL based on response and request"""
        cache_control = response.headers.get('Cache-Control', '')
        
        # Extract max-age from Cache-Control
        if 'max-age=' in cache_control:
            try:
                max_age = int(cache_control.split('max-age=')[1].split(',')[0])
                return timedelta(seconds=max_age)
            except ValueError:
                pass
        
        # Default TTL based on endpoint
        path = request.path
        if path.startswith('/api/models'):
            return timedelta(hours=24)  # Model data changes rarely
        elif path.startswith('/api/classes'):
            return timedelta(days=7)   # Classes rarely change
        elif path.startswith('/api/predict'):
            return timedelta(minutes=15)  # Predictions change frequently
        else:
            return self.default_ttl
    
    def _get_cache_control_headers(self, entry: CacheEntry) -> str:
        """Generate Cache-Control headers"""
        directives = ['public']
        
        if entry.expires_at:
            max_age = int((entry.expires_at - datetime.now()).total_seconds())
            directives.append(f'max-age={max_age}')
        
        if entry.compressed:
            directives.append('must-revalidate')
        
        return ', '.join(directives)
    
    def set(self, key: str, value: Any, content_type: str = 'application/json', 
            ttl: timedelta = None, tags: List[str] = None) -> bool:
        """Store value in cache"""
        try:
            now = datetime.now()
            expires_at = now + (ttl or self.default_ttl)
            
            # Serialize and compress if needed
            serialized_value = self._serialize_value(value)
            compressed = False
            
            if (self.cache_config['compression_enabled'] and 
                len(serialized_value) > self.compression_threshold):
                serialized_value = self._compress_value(serialized_value)
                compressed = True
            
            # Generate ETag
            etag = self._generate_etag(serialized_value)
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                etag=etag,
                content_type=content_type,
                created_at=now,
                expires_at=expires_at,
                access_count=0,
                last_accessed=now,
                size_bytes=len(serialized_value),
                compressed=compressed,
                tags=tags or [],
                metadata={}
            )
            
            # Store in memory cache
            self.memory_cache[key] = entry
            
            # Store in Redis if available
            if self.redis_client:
                self._store_in_redis(entry)
            
            # Update statistics
            self.cache_stats.sets += 1
            self._update_cache_stats()
            
            # Check memory usage and evict if needed
            self._check_memory_usage()
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set failed: {e}")
            return False
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from cache"""
        try:
            # Check memory cache first
            entry = self.memory_cache.get(key)
            if entry:
                # Check expiration
                if entry.expires_at and datetime.now() > entry.expires_at:
                    self.delete(key)
                    self.cache_stats.misses += 1
                    return None
                
                # Update access statistics
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                
                self.cache_stats.hits += 1
                return entry
            
            # Check Redis cache
            if self.redis_client:
                entry = self._get_from_redis(key)
                if entry:
                    # Store in memory cache
                    self.memory_cache[key] = entry
                    self.cache_stats.hits += 1
                    return entry
            
            self.cache_stats.misses += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get failed: {e}")
            self.cache_stats.misses += 1
            return None
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        try:
            # Delete from memory cache
            if key in self.memory_cache:
                del self.memory_cache[key]
            
            # Delete from Redis
            if self.redis_client:
                self.redis_client.delete(f"cache:{key}")
            
            self.cache_stats.deletes += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache delete failed: {e}")
            return False
    
    def clear_cache(self, pattern: str = '*') -> int:
        """Clear cache entries matching pattern"""
        cleared = 0
        
        try:
            # Clear memory cache
            if pattern == '*':
                cleared += len(self.memory_cache)
                self.memory_cache.clear()
            else:
                import fnmatch
                keys_to_delete = [k for k in self.memory_cache.keys() if fnmatch.fnmatch(k, pattern)]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                    cleared += 1
            
            # Clear Redis cache
            if self.redis_client:
                redis_keys = self.redis_client.keys(f"cache:{pattern}")
                if redis_keys:
                    cleared += len(redis_keys)
                    self.redis_client.delete(*redis_keys)
            
            return cleared
            
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return cleared
    
    def invalidate_by_tags(self, tags: List[str]) -> int:
        """Invalidate cache entries by tags"""
        invalidated = 0
        
        try:
            # Find entries with matching tags
            entries_to_delete = []
            for key, entry in self.memory_cache.items():
                if any(tag in entry.tags for tag in tags):
                    entries_to_delete.append(key)
            
            # Delete entries
            for key in entries_to_delete:
                del self.memory_cache[key]
                invalidated += 1
            
            # Invalidate in Redis
            if self.redis_client:
                # This would require a more sophisticated Redis setup with tag indexing
                pass
            
            return invalidated
            
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            return invalidated
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            if isinstance(value, (dict, list, str, int, float, bool)):
                return json.dumps(value).encode('utf-8')
            else:
                return pickle.dumps(value)
        except Exception:
            return str(value).encode('utf-8')
    
    def _compress_value(self, data: bytes) -> bytes:
        """Compress serialized data"""
        return zlib.compress(data, level=self.cache_config['compression_level'])
    
    def _decompress_value(self, data: bytes) -> bytes:
        """Decompress data"""
        return zlib.decompress(data)
    
    def _generate_etag(self, data: bytes) -> str:
        """Generate ETag for data"""
        return f'"{hashlib.md5(data).hexdigest()}"'
    
    def _store_in_redis(self, entry: CacheEntry):
        """Store entry in Redis"""
        try:
            key = f"cache:{entry.key}"
            
            # Serialize entry
            entry_data = pickle.dumps(entry)
            
            # Store with TTL
            if entry.expires_at:
                ttl = int((entry.expires_at - datetime.now()).total_seconds())
                self.redis_client.setex(key, ttl, entry_data)
            else:
                self.redis_client.set(key, entry_data)
            
            # Store tag mappings for invalidation
            for tag in entry.tags:
                self.redis_client.sadd(f"tags:{tag}", entry.key)
            
        except Exception as e:
            logger.error(f"Redis storage failed: {e}")
    
    def _get_from_redis(self, key: str) -> Optional[CacheEntry]:
        """Get entry from Redis"""
        try:
            redis_key = f"cache:{key}"
            data = self.redis_client.get(redis_key)
            
            if data:
                entry = pickle.loads(data)
                
                # Check expiration
                if entry.expires_at and datetime.now() > entry.expires_at:
                    self.redis_client.delete(redis_key)
                    return None
                
                return entry
            
        except Exception as e:
            logger.error(f"Redis retrieval failed: {e}")
        
        return None
    
    def _check_memory_usage(self):
        """Check memory usage and evict entries if needed"""
        total_size = sum(entry.size_bytes for entry in self.memory_cache.values())
        
        if total_size > self.max_memory_size:
            # Evict least recently used entries
            entries_by_access = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1].last_accessed
            )
            
            entries_to_evict = int(len(entries_by_access) * 0.2)  # Evict 20%
            for key, _ in entries_by_access[:entries_to_evict]:
                del self.memory_cache[key]
                self.cache_stats.evictions += 1
    
    def _update_cache_stats(self):
        """Update cache statistics"""
        self.cache_stats.entry_count = len(self.memory_cache)
        self.cache_stats.size_bytes = sum(entry.size_bytes for entry in self.memory_cache.values())
        
        if self.cache_stats.hits + self.cache_stats.misses > 0:
            self.cache_stats.hit_rate = self.cache_stats.hits / (self.cache_stats.hits + self.cache_stats.misses)
    
    def get_cache_stats(self) -> CacheStats:
        """Get current cache statistics"""
        self._update_cache_stats()
        return self.cache_stats
    
    def warm_cache(self, endpoints: List[str] = None) -> List[str]:
        """Warm cache for specified endpoints"""
        warmed = []
        endpoints = endpoints or self.warmup_config['endpoints']
        
        for endpoint in endpoints:
            try:
                # Make a request to warm the cache
                with self.app.test_request_context(endpoint):
                    response = self.app.full_dispatch_request(request)
                    if response.status_code == 200:
                        warmed.append(endpoint)
                        logger.info(f"Warmed cache for {endpoint}")
            except Exception as e:
                logger.error(f"Cache warming failed for {endpoint}: {e}")
        
        return warmed
    
    def _start_cache_warming(self):
        """Start background cache warming"""
        import threading
        import time
        
        def warmup_worker():
            while True:
                try:
                    self.warm_cache()
                    time.sleep(self.warmup_config['interval'])
                except Exception as e:
                    logger.error(f"Cache warming error: {e}")
        
        thread = threading.Thread(target=warmup_worker, daemon=True)
        thread.start()

# Decorators for caching
def cached(ttl: timedelta = None, tags: List[str] = None, key_prefix: str = ''):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cache_manager = current_app.extensions.get('cache_manager')
            if cache_manager:
                entry = cache_manager.get(cache_key)
                if entry:
                    return entry.value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            if cache_manager:
                cache_manager.set(cache_key, result, ttl=ttl, tags=tags)
            
            return result
        
        return wrapper
    return decorator

def conditional_cache(ttl: timedelta = None, tags: List[str] = None):
    """Decorator for conditional caching based on request"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if request should be cached
            if not getattr(request, 'cache_enabled', True):
                return func(*args, **kwargs)
            
            return cached(ttl, tags)(func)(*args, **kwargs)
        
        return wrapper
    return decorator

# Global cache manager instance
cache_manager = CacheManager()
