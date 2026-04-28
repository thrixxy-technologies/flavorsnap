"""
Unit tests for the cache manager module
"""

import pytest
import time
import pickle
import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from cache_manager import (
    CacheManager, DistributedCacheManager, CacheEntry, CacheEvictionPolicy,
    LRUEvictionPolicy, LFUEvictionPolicy, TTLEvictionPolicy
)

@pytest.mark.unit
class TestCacheEntry:
    """Test cases for CacheEntry class"""

    def test_cache_entry_creation(self):
        """Test CacheEntry creation"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.now(),
            last_accessed=datetime.now()
        )
        
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.access_count == 0
        assert entry.ttl_seconds is None
        assert entry.size_bytes == 0
        assert entry.metadata is None

    def test_cache_entry_expiration(self):
        """Test cache entry expiration"""
        # Entry with TTL
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.now() - timedelta(seconds=10),
            last_accessed=datetime.now(),
            ttl_seconds=5  # 5 seconds TTL
        )
        
        assert entry.is_expired() is True
        
        # Entry without TTL
        entry_no_ttl = CacheEntry(
            key="test_key2",
            value="test_value2",
            created_at=datetime.now() - timedelta(hours=1),
            last_accessed=datetime.now()
        )
        
        assert entry_no_ttl.is_expired() is False

    def test_update_access(self):
        """Test updating access information"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.now(),
            last_accessed=datetime.now()
        )
        
        initial_count = entry.access_count
        initial_time = entry.last_accessed
        
        time.sleep(0.01)  # Small delay
        entry.update_access()
        
        assert entry.access_count == initial_count + 1
        assert entry.last_accessed > initial_time

@pytest.mark.unit
class TestLRUEvictionPolicy:
    """Test cases for LRU eviction policy"""

    def test_lru_eviction_needed(self):
        """Test LRU eviction when needed"""
        policy = LRUEvictionPolicy()
        
        # Create cache entries with different access times
        old_time = datetime.now() - timedelta(minutes=5)
        recent_time = datetime.now()
        
        entries = {
            "old_key": CacheEntry("old_key", "old_value", old_time, old_time),
            "new_key": CacheEntry("new_key", "new_value", recent_time, recent_time)
        }
        
        # Should evict the least recently used (oldest)
        evicted_key = policy.should_evict(entries, 100, 150)  # Need to evict
        assert evicted_key == "old_key"

    def test_lru_no_eviction_needed(self):
        """Test LRU when no eviction needed"""
        policy = LRUEvictionPolicy()
        
        entries = {
            "key1": CacheEntry("key1", "value1", datetime.now(), datetime.now())
        }
        
        # No eviction needed
        evicted_key = policy.should_evict(entries, 50, 150)
        assert evicted_key is None

    def test_lru_empty_cache(self):
        """Test LRU eviction on empty cache"""
        policy = LRUEvictionPolicy()
        
        evicted_key = policy.should_evict({}, 100, 150)
        assert evicted_key is None

@pytest.mark.unit
class TestLFUEvictionPolicy:
    """Test cases for LFU eviction policy"""

    def test_lfu_eviction_needed(self):
        """Test LFU eviction when needed"""
        policy = LFUEvictionPolicy()
        
        entries = {
            "frequent_key": CacheEntry("frequent_key", "value1", datetime.now(), datetime.now()),
            "rare_key": CacheEntry("rare_key", "value2", datetime.now(), datetime.now())
        }
        
        # Set different access counts
        entries["frequent_key"].access_count = 10
        entries["rare_key"].access_count = 1
        
        # Should evict the least frequently used
        evicted_key = policy.should_evict(entries, 100, 150)
        assert evicted_key == "rare_key"

    def test_lfu_tie_breaker(self):
        """Test LFU eviction with tie-breaking"""
        policy = LFUEvictionPolicy()
        
        old_time = datetime.now() - timedelta(minutes=5)
        recent_time = datetime.now()
        
        entries = {
            "old_key": CacheEntry("old_key", "value1", old_time, old_time),
            "new_key": CacheEntry("new_key", "value2", recent_time, recent_time)
        }
        
        # Same access count, different times
        entries["old_key"].access_count = 5
        entries["new_key"].access_count = 5
        
        # Should evict the older one (LRU tie-breaker)
        evicted_key = policy.should_evict(entries, 100, 150)
        assert evicted_key == "old_key"

@pytest.mark.unit
class TestTTLEvictionPolicy:
    """Test cases for TTL eviction policy"""

    def test_ttl_eviction_expired(self):
        """Test TTL eviction of expired entries"""
        policy = TTLEvictionPolicy()
        
        expired_time = datetime.now() - timedelta(minutes=5)
        valid_time = datetime.now()
        
        entries = {
            "expired_key": CacheEntry("expired_key", "value1", expired_time, expired_time, ttl_seconds=60),
            "valid_key": CacheEntry("valid_key", "value2", valid_time, valid_time, ttl_seconds=3600)
        }
        
        # Should evict expired entry
        evicted_key = policy.should_evict(entries, 100, 150)
        assert evicted_key == "expired_key"

    def test_ttl_no_expired_entries(self):
        """Test TTL eviction when no entries are expired"""
        policy = TTLEvictionPolicy()
        
        entries = {
            "valid_key": CacheEntry("valid_key", "value1", datetime.now(), datetime.now(), ttl_seconds=3600)
        }
        
        # No expired entries, should fall back to LRU
        evicted_key = policy.should_evict(entries, 100, 150)
        assert evicted_key == "valid_key"

@pytest.mark.unit
class TestCacheManager:
    """Test cases for CacheManager class"""

    @pytest.fixture
    def cache_config(self):
        """Cache configuration for testing"""
        return {
            'max_size': 100,
            'ttl_seconds': 3600,
            'eviction_policy': 'lru'
        }

    @pytest.fixture
    def cache_manager(self, cache_config):
        """Create a cache manager instance"""
        return CacheManager(cache_config)

    def test_cache_manager_initialization(self, cache_manager, cache_config):
        """Test cache manager initialization"""
        assert cache_manager.max_size == cache_config['max_size']
        assert cache_manager.default_ttl == cache_config['ttl_seconds']
        assert isinstance(cache_manager.eviction_policy, LRUEvictionPolicy)

    def test_cache_manager_set_and_get(self, cache_manager):
        """Test setting and getting cache values"""
        key = "test_key"
        value = {"label": "test", "confidence": 0.95}
        
        cache_manager.set(key, value)
        
        retrieved_value = cache_manager.get(key)
        assert retrieved_value == value

    def test_cache_manager_get_nonexistent(self, cache_manager):
        """Test getting non-existent key"""
        result = cache_manager.get("nonexistent_key")
        assert result is None

    def test_cache_manager_get_expired(self, cache_manager):
        """Test getting expired entry"""
        key = "test_key"
        value = "test_value"
        
        # Set with very short TTL
        cache_manager.set(key, value, ttl_seconds=1)
        
        # Wait for expiration
        time.sleep(1.1)
        
        result = cache_manager.get(key)
        assert result is None

    def test_cache_manager_set_with_custom_ttl(self, cache_manager):
        """Test setting value with custom TTL"""
        key = "test_key"
        value = "test_value"
        
        cache_manager.set(key, value, ttl_seconds=10)
        
        entry = cache_manager.cache.get(key)
        assert entry is not None
        assert entry.ttl_seconds == 10

    def test_cache_manager_delete(self, cache_manager):
        """Test deleting cache entries"""
        key = "test_key"
        value = "test_value"
        
        cache_manager.set(key, value)
        assert cache_manager.get(key) == value
        
        cache_manager.delete(key)
        assert cache_manager.get(key) is None

    def test_cache_manager_clear(self, cache_manager):
        """Test clearing cache"""
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")
        
        assert len(cache_manager.cache) == 2
        
        cache_manager.clear()
        
        assert len(cache_manager.cache) == 0

    def test_cache_manager_eviction(self, cache_config):
        """Test cache eviction when size limit is reached"""
        # Create small cache
        small_config = cache_config.copy()
        small_config['max_size'] = 2
        cache = CacheManager(small_config)
        
        # Fill cache beyond capacity
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should trigger eviction
        
        # Should only have 2 entries
        assert len(cache.cache) <= 2
        
        # Least recently used should be evicted
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None

    def test_cache_prediction_result(self, cache_manager):
        """Test caching prediction results"""
        image_hash = "test_hash_123"
        result = {"label": "Jollof Rice", "confidence": 0.92}
        
        cache_manager.cache_prediction_result(image_hash, result)
        
        cached_result = cache_manager.get_cached_prediction(image_hash)
        assert cached_result == result

    def test_cache_prediction_result_not_found(self, cache_manager):
        """Test getting non-existent cached prediction"""
        result = cache_manager.get_cached_prediction("nonexistent_hash")
        assert result is None

    def test_cache_stats(self, cache_manager):
        """Test cache statistics"""
        # Add some entries
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")
        
        # Access some entries to generate stats
        cache_manager.get("key1")
        cache_manager.get("key2")
        cache_manager.get("nonexistent")  # Miss
        
        stats = cache_manager.get_comprehensive_stats()
        
        assert 'hit_rate' in stats
        assert 'miss_rate' in stats
        assert 'total_requests' in stats
        assert 'cache_size' in stats
        assert 'max_size' in stats

    def test_cache_size_calculation(self, cache_manager):
        """Test cache size calculation"""
        large_value = "x" * 1000
        cache_manager.set("large_key", large_value)
        
        entry = cache_manager.cache.get("large_key")
        assert entry.size_bytes > 0

    def test_cache_metadata(self, cache_manager):
        """Test cache entry metadata"""
        key = "test_key"
        value = "test_value"
        metadata = {"source": "test", "version": "1.0"}
        
        cache_manager.set(key, value, metadata=metadata)
        
        entry = cache_manager.cache.get(key)
        assert entry.metadata == metadata

    def test_cache_touch_updates_access(self, cache_manager):
        """Test that touching an entry updates access info"""
        key = "test_key"
        value = "test_value"
        
        cache_manager.set(key, value)
        
        initial_count = cache_manager.cache[key].access_count
        initial_time = cache_manager.cache[key].last_accessed
        
        time.sleep(0.01)
        cache_manager.touch(key)
        
        assert cache_manager.cache[key].access_count == initial_count + 1
        assert cache_manager.cache[key].last_accessed > initial_time

    def test_cache_cleanup_expired(self, cache_manager):
        """Test cleanup of expired entries"""
        # Add entries with different TTLs
        cache_manager.set("expired_key", "value1", ttl_seconds=1)
        cache_manager.set("valid_key", "value2", ttl_seconds=3600)
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Cleanup
        cache_manager.cleanup_expired()
        
        # Should only have valid entry
        assert cache_manager.get("expired_key") is None
        assert cache_manager.get("valid_key") is not None

    def test_cache_different_eviction_policies(self, cache_config):
        """Test different eviction policies"""
        # Test LFU policy
        lfu_config = cache_config.copy()
        lfu_config['eviction_policy'] = 'lfu'
        lfu_cache = CacheManager(lfu_config)
        assert isinstance(lfu_cache.eviction_policy, LFUEvictionPolicy)
        
        # Test TTL policy
        ttl_config = cache_config.copy()
        ttl_config['eviction_policy'] = 'ttl'
        ttl_cache = CacheManager(ttl_config)
        assert isinstance(ttl_cache.eviction_policy, TTLEvictionPolicy)

@pytest.mark.unit
class TestDistributedCacheManager:
    """Test cases for DistributedCacheManager class"""

    @pytest.fixture
    def redis_config(self):
        """Redis configuration for testing"""
        return {
            'type': 'redis',
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'ttl_seconds': 3600,
            'key_prefix': 'flavorsnap:'
        }

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        redis_mock = MagicMock()
        redis_mock.ping.return_value = True
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.delete.return_value = 1
        redis_mock.exists.return_value = 1
        return redis_mock

    def test_distributed_cache_initialization(self, redis_config, mock_redis):
        """Test distributed cache initialization"""
        with patch('cache_manager.redis.Redis', return_value=mock_redis):
            cache = DistributedCacheManager(redis_config)
            
            assert cache.redis_client is not None
            assert cache.key_prefix == redis_config['key_prefix']
            assert cache.default_ttl == redis_config['ttl_seconds']

    def test_distributed_cache_set_and_get(self, redis_config, mock_redis):
        """Test distributed cache set and get"""
        with patch('cache_manager.redis.Redis', return_value=mock_redis):
            cache = DistributedCacheManager(redis_config)
            
            key = "test_key"
            value = {"label": "test", "confidence": 0.95}
            
            # Mock Redis operations
            mock_redis.get.return_value = pickle.dumps(value)
            
            cache.set(key, value)
            result = cache.get(key)
            
            assert result == value
            mock_redis.set.assert_called_once()
            mock_redis.get.assert_called_once()

    def test_distributed_cache_delete(self, redis_config, mock_redis):
        """Test distributed cache delete"""
        with patch('cache_manager.redis.Redis', return_value=mock_redis):
            cache = DistributedCacheManager(redis_config)
            
            key = "test_key"
            cache.delete(key)
            
            mock_redis.delete.assert_called_once_with(f"{redis_config['key_prefix']}{key}")

    def test_distributed_cache_clear(self, redis_config, mock_redis):
        """Test distributed cache clear"""
        with patch('cache_manager.redis.Redis', return_value=mock_redis):
            cache = DistributedCacheManager(redis_config)
            
            # Mock keys command
            mock_redis.keys.return_value = [f"{redis_config['key_prefix']}key1", f"{redis_config['key_prefix']}key2"]
            
            cache.clear()
            
            mock_redis.keys.assert_called_once_with(f"{redis_config['key_prefix']}*")
            assert mock_redis.delete.call_count == 2

    def test_distributed_cache_connection_failure(self, redis_config):
        """Test distributed cache with connection failure"""
        with patch('cache_manager.redis.Redis') as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis.ping.side_effect = Exception("Connection failed")
            mock_redis_class.return_value = mock_redis
            
            with pytest.raises(Exception):
                DistributedCacheManager(redis_config)

    def test_distributed_cache_stats(self, redis_config, mock_redis):
        """Test distributed cache statistics"""
        with patch('cache_manager.redis.Redis', return_value=mock_redis):
            cache = DistributedCacheManager(redis_config)
            
            # Mock info command
            mock_redis.info.return_value = {
                'keyspace_hits': 100,
                'keyspace_misses': 25,
                'used_memory': 1024000,
                'db0': {'keys': 50}
            }
            
            stats = cache.get_comprehensive_stats()
            
            assert 'hit_rate' in stats
            assert 'miss_rate' in stats
            assert 'memory_usage' in stats
            assert 'total_keys' in stats

    def test_distributed_cache_prediction_result(self, redis_config, mock_redis):
        """Test distributed cache prediction results"""
        with patch('cache_manager.redis.Redis', return_value=mock_redis):
            cache = DistributedCacheManager(redis_config)
            
            image_hash = "test_hash_123"
            result = {"label": "Jollof Rice", "confidence": 0.92}
            
            # Mock Redis get
            mock_redis.get.return_value = pickle.dumps(result)
            
            cache.cache_prediction_result(image_hash, result)
            cached_result = cache.get_cached_prediction(image_hash)
            
            assert cached_result == result

    def test_distributed_cache_pickle_serialization(self, redis_config, mock_redis):
        """Test pickle serialization in distributed cache"""
        with patch('cache_manager.redis.Redis', return_value=mock_redis):
            cache = DistributedCacheManager(redis_config)
            
            complex_value = {
                "nested": {"data": [1, 2, 3]},
                "timestamp": datetime.now()
            }
            
            key = "complex_key"
            cache.set(key, complex_value)
            
            # Verify pickle was used
            mock_redis.set.assert_called_once()
            call_args = mock_redis.set.call_args
            assert len(call_args[0]) == 2  # key and pickled value

    def test_distributed_cache_ttl_support(self, redis_config, mock_redis):
        """Test TTL support in distributed cache"""
        with patch('cache_manager.redis.Redis', return_value=mock_redis):
            cache = DistributedCacheManager(redis_config)
            
            key = "test_key"
            value = "test_value"
            custom_ttl = 1800  # 30 minutes
            
            cache.set(key, value, ttl_seconds=custom_ttl)
            
            # Verify TTL was passed to Redis
            mock_redis.set.assert_called_once()
            call_args = mock_redis.set.call_args
            assert call_args[1]['ex'] == custom_ttl
