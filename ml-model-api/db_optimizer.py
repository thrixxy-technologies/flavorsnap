from query_optimizer import QueryOptimizer
from index_manager import IndexManager
from persistence import PersistenceLayer
import time

class DBOptimizer:
    """
    Central database optimization engine.
    """

    def __init__(self):
        self.query_optimizer = QueryOptimizer()
        self.index_manager = IndexManager()
        self.db = PersistenceLayer()

        self.metrics = {
            "queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "slow_queries": 0,
        }

    # --------------------------
    # QUERY EXECUTION
    # --------------------------
    def execute_query(self, query: str):
        self.metrics["queries"] += 1

        optimized_query = self.query_optimizer.optimize(query)

        start = time.time()

        # simulate execution delay
        time.sleep(0.01)

        duration = time.time() - start

        if duration > 0.05:
            self.metrics["slow_queries"] += 1

        return {
            "original": query,
            "optimized": optimized_query,
            "duration": duration
        }

    # --------------------------
    # INDEX MANAGEMENT
    # --------------------------
    def create_index(self, table: str, columns: list):
        self.index_manager.create_index(table, columns)

    def suggest_indexes(self, query_fields: list, table: str):
        return self.index_manager.optimize_indexes(query_fields, table)

    # --------------------------
    # MONITORING
    # --------------------------
    def get_metrics(self):
        return {
            **self.metrics,
            "index_usage": self.index_manager.indexes,
            "active_connections": self.db.active_connections
        }

    # --------------------------
    # CACHE INTEGRATION
    # --------------------------
    def cached_query(self, key: str, query_func):
        cached = self.db.cache_get(key)

        if cached:
            self.metrics["cache_hits"] += 1
            return cached

        self.metrics["cache_misses"] += 1
        result = query_func()

        self.db.cache_set(key, result)
        return result