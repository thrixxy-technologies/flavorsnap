from cache_manager import CacheManager
from profiler import Profiler
from monitoring import PerformanceMonitor
import time

class PerformanceOptimizer:
    """
    Central performance optimization engine:
    caching, profiling, tuning hooks.
    """

    def __init__(self):
        self.cache = CacheManager()
        self.profiler = Profiler()
        self.monitor = PerformanceMonitor()

    # ---------------------------
    # CACHING LAYER
    # ---------------------------
    def cached(self, key: str, ttl: int = 300):
        def decorator(func):
            def wrapper(*args, **kwargs):
                cached_value = self.cache.get(key)

                if cached_value is not None:
                    self.monitor.log_cache_hit()
                    return cached_value

                self.monitor.log_cache_miss()
                result = func(*args, **kwargs)

                self.cache.set(key, result, ttl)
                return result

            return wrapper
        return decorator

    # ---------------------------
    # PROFILING WRAPPER
    # ---------------------------
    def profile(self, func):
        return self.profiler.profile(func)

    # ---------------------------
    # DB OPTIMIZATION HOOK
    # ---------------------------
    def optimize_query(self, query: str) -> str:
        """
        Simulated query optimizer.
        """
        self.monitor.log_db_query()

        optimized = query.strip().lower().replace("select *", "select indexed_fields")
        return optimized

    # ---------------------------
    # LOAD TEST SIMULATION
    # ---------------------------
    def load_test(self, func, requests: int = 100):
        start = time.time()

        results = []
        for _ in range(requests):
            try:
                self.monitor.log_request()
                results.append(func())
            except Exception:
                self.monitor.log_error()

        duration = time.time() - start

        return {
            "requests": requests,
            "duration": duration,
            "rps": requests / duration if duration > 0 else 0
        }

    # ---------------------------
    # REPORTING
    # ---------------------------
    def optimization_report(self):
        return {
            "cache": self.cache.stats(),
            "profiling": self.profiler.get_stats(),
            "monitoring": self.monitor.snapshot()
        }