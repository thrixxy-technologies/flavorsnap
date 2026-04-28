import os
import json
import logging
import time
from typing import Dict, Any, Optional, List
import redis
from redis.cluster import RedisCluster
from cache_manager import CacheManager

logger = logging.getLogger(__name__)

class AdvancedCacheArchitecture(CacheManager):
    """Advanced distributed caching architecture with cluster support and intelligent warming"""
    
    def __init__(self, cluster_nodes: List[Dict[str, str]] = None, use_cluster: bool = False):
        super().__init__()
        self.use_cluster = use_cluster or os.environ.get("USE_REDIS_CLUSTER", "false").lower() == "true"
        self.cluster_nodes = cluster_nodes or self._get_cluster_nodes()
        
        if self.use_cluster:
            self._connect_cluster()
            
    def _get_cluster_nodes(self):
        """Parse cluster nodes from environment"""
        nodes_str = os.environ.get("REDIS_CLUSTER_NODES", "")
        if not nodes_str:
            return []
        nodes = []
        for node in nodes_str.split(","):
            host, port = node.split(":")
            nodes.append({"host": host, "port": port})
        return nodes

    def _connect_cluster(self):
        """Establish connection to Redis Cluster"""
        try:
            self.redis_client = RedisCluster(startup_nodes=self.cluster_nodes, decode_responses=True)
            logger.info("Connected to Redis Cluster")
        except Exception as e:
            logger.error(f"Failed to connect to Redis Cluster: {e}")
            self._connect_redis() # Fallback to standalone

    def warm_cache(self, key_patterns: List[str]):
        """Intelligently warm the cache with frequent access patterns"""
        logger.info(f"Starting cache warming for patterns: {key_patterns}")
        # In a real scenario, this would fetch data from the DB or a persistent layer
        # For now, we simulate warming by setting some metadata
        for pattern in key_patterns:
            self.redis_client.set(f"warming_meta:{pattern}", json.dumps({
                "warmed_at": time.time(),
                "status": "ready"
            }))

    def intelligent_invalidation(self, tags: List[str]):
        """Invalidate cache entries based on tags (e.g. model_update, category_change)"""
        logger.info(f"Intelligent invalidation triggered for tags: {tags}")
        for tag in tags:
            keys = self.redis_client.keys(f"tag:{tag}:*")
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Deleted {len(keys)} keys for tag: {tag}")

    def get_analytics(self):
        """Advanced analytics integration"""
        base_stats = self.get_cache_stats()
        # Add cluster-specific stats if applicable
        if self.use_cluster and hasattr(self.redis_client, 'cluster_info'):
            base_stats['cluster_info'] = self.redis_client.cluster_info()
        return base_stats

    def optimize_memory(self):
        """Memory optimization: clear low-priority keys if memory is tight"""
        try:
            info = self.redis_client.info('memory')
            used_memory = info.get('used_memory', 0)
            max_memory = info.get('maxmemory', 0)
            
            if max_memory > 0 and used_memory > (max_memory * 0.8):
                logger.warning("Memory usage high, performing optimization")
                # Delete keys with 'low_priority' prefix or older TTLs
                low_priority_keys = self.redis_client.keys("low_priority:*")
                if low_priority_keys:
                    self.redis_client.delete(*low_priority_keys)
        except Exception as e:
            logger.error(f"Memory optimization failed: {e}")

# Global instance
advanced_cache = AdvancedCacheArchitecture()
