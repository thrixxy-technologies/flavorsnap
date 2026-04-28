"""
Advanced Cache Manager with Queue Support for FlavorSnap
Handles caching for batch processing results, queue states, and performance optimization
"""

import json
import pickle
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass
from collections import OrderedDict
import hashlib
import logging

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    metadata: Dict[str, Any] = None

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl_seconds is None:
            return False
        return datetime.now() > (self.created_at + timedelta(seconds=self.ttl_seconds))
    
    def update_access(self):
        """Update access information"""
        self.last_accessed = datetime.now()
        self.access_count += 1

class CacheEvictionPolicy(ABC):
    """Abstract base class for cache eviction policies"""
    
    @abstractmethod
    def should_evict(self, cache_entries: Dict[str, CacheEntry], new_entry_size: int, max_size: int) -> Optional[str]:
        """Determine which key to evict, or None if no eviction needed"""
        pass

class LRUEvictionPolicy(CacheEvictionPolicy):
    """Least Recently Used eviction policy"""
    
    def should_evict(self, cache_entries: Dict[str, CacheEntry], new_entry_size: int, max_size: int) -> Optional[str]:
        """Evict least recently used entry"""
        if not cache_entries:
            return None
        
        # Calculate current size
        current_size = sum(entry.size_bytes for entry in cache_entries.values())
        if current_size + new_entry_size <= max_size:
            return None
        
        # Find LRU entry
        lru_key = min(cache_entries.keys(), 
                     key=lambda k: cache_entries[k].last_accessed)
        return lru_key

class LFUEvictionPolicy(CacheEvictionPolicy):
    """Least Frequently Used eviction policy"""
    
    def should_evict(self, cache_entries: Dict[str, CacheEntry], new_entry_size: int, max_size: int) -> Optional[str]:
        """Evict least frequently used entry"""
        if not cache_entries:
            return None
        
        current_size = sum(entry.size_bytes for entry in cache_entries.values())
        if current_size + new_entry_size <= max_size:
            return None
        
        # Find LFU entry (use access count, then last accessed as tiebreaker)
        lfu_key = min(cache_entries.keys(),
                     key=lambda k: (cache_entries[k].access_count, cache_entries[k].last_accessed))
        return lfu_key

class TTLEvictionPolicy(CacheEvictionPolicy):
    """Time-based eviction policy"""
    
    def should_evict(self, cache_entries: Dict[str, CacheEntry], new_entry_size: int, max_size: int) -> Optional[str]:
        """Evict expired entries first, then LRU if needed"""
        # First, remove expired entries
        expired_keys = [k for k, entry in cache_entries.items() if entry.is_expired()]
        if expired_keys:
            return expired_keys[0]
        
        # If no expired entries, use LRU
        lru_policy = LRUEvictionPolicy()
        return lru_policy.should_evict(cache_entries, new_entry_size, max_size)

class QueueCache:
    """Specialized cache for queue operations and batch processing"""
    
    def __init__(self, max_size: int = 1000, eviction_policy: CacheEvictionPolicy = None):
        self.max_size = max_size
        self.eviction_policy = eviction_policy or LRUEvictionPolicy()
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size_bytes': 0,
            'entry_count': 0
        }
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate size of cached value in bytes"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, (dict, list, tuple)):
                return len(json.dumps(value).encode('utf-8'))
            else:
                return len(pickle.dumps(value))
        except Exception:
            return 1024  # Fallback size estimate
    
    def _generate_key(self, prefix: str, data: Any) -> str:
        """Generate cache key from data"""
        try:
            if isinstance(data, (str, int, float, bool)):
                key_data = str(data)
            elif isinstance(data, dict):
                # Sort dict keys for consistent key generation
                sorted_items = sorted(data.items())
                key_data = json.dumps(sorted_items, sort_keys=True)
            else:
                key_data = pickle.dumps(data)
            
            hash_obj = hashlib.md5(key_data.encode('utf-8') if isinstance(key_data, str) else key_data)
            return f"{prefix}:{hash_obj.hexdigest()}"
        except Exception as e:
            logger.error(f"Error generating cache key: {e}")
            return f"{prefix}:{hash(data)}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats['misses'] += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._stats['misses'] += 1
                self._stats['evictions'] += 1
                self._update_stats()
                return None
            
            entry.update_access()
            self._stats['hits'] += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None):
        """Set value in cache"""
        with self._lock:
            now = datetime.now()
            size_bytes = self._calculate_size(value)
            
            # Check if we need to evict entries
            eviction_key = self.eviction_policy.should_evict(self._cache, size_bytes, self.max_size)
            if eviction_key:
                del self._cache[eviction_key]
                self._stats['evictions'] += 1
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                last_accessed=now,
                ttl_seconds=ttl_seconds,
                size_bytes=size_bytes,
                metadata=metadata or {}
            )
            
            self._cache[key] = entry
            self._update_stats()
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._update_stats()
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._update_stats()
    
    def _update_stats(self):
        """Update cache statistics"""
        self._stats['size_bytes'] = sum(entry.size_bytes for entry in self._cache.values())
        self._stats['entry_count'] = len(self._cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': hit_rate,
                'evictions': self._stats['evictions'],
                'size_bytes': self._stats['size_bytes'],
                'entry_count': self._stats['entry_count'],
                'max_size': self.max_size,
                'utilization': self._stats['size_bytes'] / self.max_size if self.max_size > 0 else 0
            }
    
    def get_expired_keys(self) -> List[str]:
        """Get list of expired keys"""
        with self._lock:
            return [key for key, entry in self._cache.items() if entry.is_expired()]
    
    def cleanup_expired(self):
        """Remove expired entries"""
        expired_keys = self.get_expired_keys()
        for key in expired_keys:
            self.delete(key)
        return len(expired_keys)

class CacheManager:
    """Advanced cache manager with multiple cache types and queue support"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize different cache types
        self._init_caches()
        
        # Background cleanup thread
        self._cleanup_thread = threading.Thread(target=self._background_cleanup, daemon=True)
        self._cleanup_stop_event = threading.Event()
        self._cleanup_thread.start()
    
    def _init_caches(self):
        """Initialize different cache instances"""
        default_size = self.config.get('default_cache_size', 1000)
        result_cache_size = self.config.get('result_cache_size', 500)
        queue_cache_size = self.config.get('queue_cache_size', 2000)
        
        # Results cache - for ML model predictions
        self.results_cache = QueueCache(
            max_size=result_cache_size * 1024 * 1024,  # Convert MB to bytes
            eviction_policy=TTLEvictionPolicy()
        )
        
        # Queue state cache - for queue statistics and metadata
        self.queue_cache = QueueCache(
            max_size=queue_cache_size * 1024 * 1024,
            eviction_policy=LRUEvictionPolicy()
        )
        
        # General purpose cache
        self.general_cache = QueueCache(
            max_size=default_size * 1024 * 1024,
            eviction_policy=LRUEvictionPolicy()
        )
    
    def cache_prediction_result(self, image_hash: str, result: Dict[str, Any], ttl_seconds: int = 3600):
        """Cache ML prediction result"""
        key = f"prediction:{image_hash}"
        self.results_cache.set(key, result, ttl_seconds, {'type': 'prediction'})
    
    def get_cached_prediction(self, image_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached prediction result"""
        key = f"prediction:{image_hash}"
        return self.results_cache.get(key)
    
    def cache_queue_stats(self, queue_id: str, stats: Dict[str, Any], ttl_seconds: int = 60):
        """Cache queue statistics"""
        key = f"queue_stats:{queue_id}"
        self.queue_cache.set(key, stats, ttl_seconds, {'type': 'queue_stats'})
    
    def get_cached_queue_stats(self, queue_id: str) -> Optional[Dict[str, Any]]:
        """Get cached queue statistics"""
        key = f"queue_stats:{queue_id}"
        return self.queue_cache.get(key)
    
    def cache_batch_result(self, batch_id: str, results: List[Dict[str, Any]], ttl_seconds: int = 7200):
        """Cache batch processing results"""
        key = f"batch:{batch_id}"
        self.general_cache.set(key, results, ttl_seconds, {'type': 'batch_result'})
    
    def get_cached_batch_result(self, batch_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached batch processing results"""
        key = f"batch:{batch_id}"
        return self.general_cache.get(key)
    
    def cache_worker_performance(self, worker_id: str, performance_data: Dict[str, Any], ttl_seconds: int = 300):
        """Cache worker performance metrics"""
        key = f"worker_perf:{worker_id}"
        self.queue_cache.set(key, performance_data, ttl_seconds, {'type': 'worker_performance'})
    
    def get_cached_worker_performance(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get cached worker performance metrics"""
        key = f"worker_perf:{worker_id}"
        return self.queue_cache.get(key)
    
    def invalidate_queue_cache(self, queue_id: str = None):
        """Invalidate queue-related cache entries"""
        if queue_id:
            # Invalidate specific queue
            pattern = f"queue_stats:{queue_id}"
            self.queue_cache.delete(pattern)
        else:
            # Invalidate all queue stats
            keys_to_delete = [key for key in self.queue_cache._cache.keys() 
                            if key.startswith("queue_stats:")]
            for key in keys_to_delete:
                self.queue_cache.delete(key)
    
    def invalidate_prediction_cache(self, image_hash: str = None):
        """Invalidate prediction cache entries"""
        if image_hash:
            key = f"prediction:{image_hash}"
            self.results_cache.delete(key)
        else:
            # Clear all prediction cache
            keys_to_delete = [key for key in self.results_cache._cache.keys()
                            if key.startswith("prediction:")]
            for key in keys_to_delete:
                self.results_cache.delete(key)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        return {
            'results_cache': self.results_cache.get_stats(),
            'queue_cache': self.queue_cache.get_stats(),
            'general_cache': self.general_cache.get_stats(),
            'total_memory_mb': (
                self.results_cache.get_stats()['size_bytes'] +
                self.queue_cache.get_stats()['size_bytes'] +
                self.general_cache.get_stats()['size_bytes']
            ) / (1024 * 1024)
        }
    
    def _background_cleanup(self):
        """Background thread for cache cleanup"""
        cleanup_interval = self.config.get('cleanup_interval', 300)  # 5 minutes
        
        while not self._cleanup_stop_event.is_set():
            try:
                # Cleanup expired entries
                expired_count = 0
                expired_count += self.results_cache.cleanup_expired()
                expired_count += self.queue_cache.cleanup_expired()
                expired_count += self.general_cache.cleanup_expired()
                
                if expired_count > 0:
                    logger.info(f"Cleaned up {expired_count} expired cache entries")
                
                # Sleep until next cleanup
                self._cleanup_stop_event.wait(cleanup_interval)
                
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                self._cleanup_stop_event.wait(60)  # Wait 1 minute on error
    
    def shutdown(self):
        """Shutdown cache manager"""
        logger.info("Shutting down cache manager")
        self._cleanup_stop_event.set()
        self._cleanup_thread.join(timeout=5)
        
        # Clear all caches
        self.results_cache.clear()
        self.queue_cache.clear()
        self.general_cache.clear()
        
        logger.info("Cache manager shutdown complete")

class DistributedCacheManager(CacheManager):
    """Distributed cache manager with Redis backend"""
    
    def __init__(self, redis_config: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.redis_config = redis_config
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            import redis
            self.redis_client = redis.Redis(
                host=self.redis_config.get('host', 'localhost'),
                port=self.redis_config.get('port', 6379),
                db=self.redis_config.get('db', 0),
                password=self.redis_config.get('password'),
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
        except ImportError:
            logger.error("Redis not installed. Install with: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            raise
    
    def cache_prediction_result(self, image_hash: str, result: Dict[str, Any], ttl_seconds: int = 3600):
        """Cache prediction result in Redis"""
        key = f"prediction:{image_hash}"
        try:
            self.redis_client.setex(key, ttl_seconds, json.dumps(result))
        except Exception as e:
            logger.error(f"Redis cache error: {e}")
            # Fallback to local cache
            super().cache_prediction_result(image_hash, result, ttl_seconds)
    
    def get_cached_prediction(self, image_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached prediction from Redis"""
        key = f"prediction:{image_hash}"
        try:
            result = self.redis_client.get(key)
            if result:
                return json.loads(result)
            return None
        except Exception as e:
            logger.error(f"Redis cache error: {e}")
            # Fallback to local cache
            return super().get_cached_prediction(image_hash)
    
    def get_redis_stats(self) -> Dict[str, Any]:
        """Get Redis statistics"""
        try:
            info = self.redis_client.info()
            return {
                'connected_clients': info.get('connected_clients'),
                'used_memory': info.get('used_memory'),
                'used_memory_human': info.get('used_memory_human'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits'),
                'keyspace_misses': info.get('keyspace_misses')
            }
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
            return {}
    
    def shutdown(self):
        """Shutdown distributed cache manager"""
        if hasattr(self, 'redis_client'):
            try:
                self.redis_client.close()
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
        
        super().shutdown()
