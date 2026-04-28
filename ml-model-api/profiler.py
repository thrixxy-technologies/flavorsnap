import time
import functools
from typing import Callable, Dict

class Profiler:
    """
    Tracks execution time of functions.
    """

    def __init__(self):
        self.metrics: Dict[str, list] = {}

    def profile(self, func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()

            result = func(*args, **kwargs)

            duration = time.time() - start
            name = func.__name__

            if name not in self.metrics:
                self.metrics[name] = []

            self.metrics[name].append(duration)

            return result

        return wrapper

    def get_stats(self):
        return {
            fn: {
                "calls": len(times),
                "avg_time": sum(times) / len(times),
                "max_time": max(times),
            }
            for fn, times in self.metrics.items()
        }

    def reset(self):
        self.metrics.clear()