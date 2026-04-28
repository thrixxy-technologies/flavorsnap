"""
Performance profiler for FlavorSnap.

Provides:
  - A context-manager / decorator for timing code blocks
  - A PerformanceProfiler that stores recent timing samples and
    exposes aggregated statistics (p50, p95, p99, mean, max)
  - Integration with the MetricsCollector so profiled spans are
    also recorded as Prometheus histograms

Usage
-----
    from src.monitoring.profiler import get_profiler, profile

    profiler = get_profiler()

    # As a context manager
    with profiler.span("image_preprocessing"):
        result = preprocess(image)

    # As a decorator
    @profile("model_inference")
    def run_inference(tensor):
        ...

    # Get stats
    stats = profiler.get_stats("model_inference")
    # {"count": 42, "mean_ms": 45.3, "p50_ms": 43.1, "p95_ms": 89.2, ...}
"""

from __future__ import annotations

import contextlib
import functools
import logging
import statistics
import threading
import time
from collections import deque
from typing import Any, Callable, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

# Maximum number of timing samples retained per span name
_MAX_SAMPLES = 1000


# ---------------------------------------------------------------------------
# Span context manager
# ---------------------------------------------------------------------------


class Span:
    """A single timed execution span."""

    def __init__(self, name: str, profiler: "PerformanceProfiler") -> None:
        self.name = name
        self._profiler = profiler
        self._start: float = 0.0
        self.duration_ms: float = 0.0

    def __enter__(self) -> "Span":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.duration_ms = (time.perf_counter() - self._start) * 1000.0
        self._profiler._record(self.name, self.duration_ms, error=exc_type is not None)
        return False  # do not suppress exceptions


# ---------------------------------------------------------------------------
# Profiler
# ---------------------------------------------------------------------------


class PerformanceProfiler:
    """
    Collects timing samples for named spans and exposes aggregated stats.

    Thread-safe.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # name -> deque of (duration_ms, error_flag) tuples
        self._samples: Dict[str, deque] = {}
        self._error_counts: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def _record(self, name: str, duration_ms: float, error: bool = False) -> None:
        with self._lock:
            if name not in self._samples:
                self._samples[name] = deque(maxlen=_MAX_SAMPLES)
                self._error_counts[name] = 0
            self._samples[name].append(duration_ms)
            if error:
                self._error_counts[name] += 1

        # Also push to Prometheus histogram if available
        try:
            from .metrics_collector import MODEL_INFERENCE_DURATION_SECONDS

            if name.startswith("inference"):
                MODEL_INFERENCE_DURATION_SECONDS.labels(model_version="v1").observe(
                    duration_ms / 1000.0
                )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Context manager / decorator
    # ------------------------------------------------------------------

    @contextlib.contextmanager
    def span(self, name: str) -> Generator[Span, None, None]:
        """Context manager that times the enclosed block."""
        s = Span(name, self)
        with s:
            yield s

    def profile(self, name: str) -> Callable:
        """Decorator that times the wrapped function."""

        def decorator(fn: Callable) -> Callable:
            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                with self.span(name):
                    return fn(*args, **kwargs)

            return wrapper

        return decorator

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self, name: str) -> Dict[str, Any]:
        """Return aggregated statistics for a named span."""
        with self._lock:
            samples = list(self._samples.get(name, []))
            errors = self._error_counts.get(name, 0)

        if not samples:
            return {
                "name": name,
                "count": 0,
                "error_count": 0,
                "mean_ms": None,
                "min_ms": None,
                "max_ms": None,
                "p50_ms": None,
                "p95_ms": None,
                "p99_ms": None,
            }

        sorted_samples = sorted(samples)
        n = len(sorted_samples)

        def percentile(p: float) -> float:
            idx = int(p / 100.0 * n)
            return sorted_samples[min(idx, n - 1)]

        return {
            "name": name,
            "count": n,
            "error_count": errors,
            "mean_ms": round(statistics.mean(samples), 3),
            "min_ms": round(min(samples), 3),
            "max_ms": round(max(samples), 3),
            "p50_ms": round(percentile(50), 3),
            "p95_ms": round(percentile(95), 3),
            "p99_ms": round(percentile(99), 3),
        }

    def get_all_stats(self) -> List[Dict[str, Any]]:
        """Return stats for every recorded span."""
        with self._lock:
            names = list(self._samples.keys())
        return [self.get_stats(n) for n in names]

    def reset(self, name: Optional[str] = None) -> None:
        """Clear samples for one span (or all spans if name is None)."""
        with self._lock:
            if name:
                self._samples.pop(name, None)
                self._error_counts.pop(name, None)
            else:
                self._samples.clear()
                self._error_counts.clear()


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

_profiler: Optional[PerformanceProfiler] = None
_lock = threading.Lock()


def get_profiler() -> PerformanceProfiler:
    """Return the process-wide PerformanceProfiler singleton."""
    global _profiler
    if _profiler is None:
        with _lock:
            if _profiler is None:
                _profiler = PerformanceProfiler()
    return _profiler


def profile(name: str) -> Callable:
    """Module-level decorator shortcut using the singleton profiler."""
    return get_profiler().profile(name)
