"""
Metrics collection for FlavorSnap.

Exposes Prometheus counters, histograms, and gauges for:
  - HTTP request counts and latencies
  - Model inference latency and throughput
  - Cache hit/miss rates
  - System resource utilisation (CPU, memory, disk)
  - Custom business metrics (classifications per food class, confidence distribution)
"""

from __future__ import annotations

import os
import threading
import time
from typing import Optional

import psutil
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Summary,
    generate_latest,
    multiprocess,
    CollectorRegistry,
    REGISTRY,
)

# ---------------------------------------------------------------------------
# HTTP metrics
# ---------------------------------------------------------------------------

HTTP_REQUESTS_TOTAL = Counter(
    "flavorsnap_http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "flavorsnap_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

HTTP_REQUEST_SIZE_BYTES = Histogram(
    "flavorsnap_http_request_size_bytes",
    "HTTP request body size in bytes",
    ["method", "endpoint"],
    buckets=(100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000),
)

HTTP_RESPONSE_SIZE_BYTES = Histogram(
    "flavorsnap_http_response_size_bytes",
    "HTTP response body size in bytes",
    ["method", "endpoint"],
    buckets=(100, 1_000, 10_000, 100_000),
)

HTTP_ERRORS_TOTAL = Counter(
    "flavorsnap_http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "status_code"],
)

# ---------------------------------------------------------------------------
# Model / inference metrics
# ---------------------------------------------------------------------------

MODEL_INFERENCE_DURATION_SECONDS = Histogram(
    "flavorsnap_model_inference_duration_seconds",
    "Model inference duration in seconds",
    ["model_version"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

MODEL_INFERENCE_TOTAL = Counter(
    "flavorsnap_model_inference_total",
    "Total model inference calls",
    ["model_version", "status"],  # status: success | error
)

MODEL_CONFIDENCE_HISTOGRAM = Histogram(
    "flavorsnap_model_confidence",
    "Distribution of top-1 confidence scores",
    ["predicted_class"],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

MODEL_PREDICTIONS_TOTAL = Counter(
    "flavorsnap_model_predictions_total",
    "Total predictions per food class",
    ["predicted_class"],
)

MODEL_LOADED = Gauge(
    "flavorsnap_model_loaded",
    "Whether the ML model is currently loaded (1=yes, 0=no)",
)

# ---------------------------------------------------------------------------
# Cache metrics
# ---------------------------------------------------------------------------

CACHE_HITS_TOTAL = Counter(
    "flavorsnap_cache_hits_total",
    "Total cache hits",
    ["cache_type"],  # redis | memory
)

CACHE_MISSES_TOTAL = Counter(
    "flavorsnap_cache_misses_total",
    "Total cache misses",
    ["cache_type"],
)

CACHE_SIZE_BYTES = Gauge(
    "flavorsnap_cache_size_bytes",
    "Estimated cache size in bytes",
    ["cache_type"],
)

# ---------------------------------------------------------------------------
# System metrics
# ---------------------------------------------------------------------------

SYSTEM_CPU_USAGE_PERCENT = Gauge(
    "flavorsnap_system_cpu_usage_percent",
    "System CPU usage percentage",
)

SYSTEM_MEMORY_USAGE_BYTES = Gauge(
    "flavorsnap_system_memory_usage_bytes",
    "System memory usage in bytes",
)

SYSTEM_MEMORY_TOTAL_BYTES = Gauge(
    "flavorsnap_system_memory_total_bytes",
    "Total system memory in bytes",
)

SYSTEM_DISK_USAGE_PERCENT = Gauge(
    "flavorsnap_system_disk_usage_percent",
    "Disk usage percentage",
    ["mount_point"],
)

PROCESS_OPEN_FDS = Gauge(
    "flavorsnap_process_open_fds",
    "Number of open file descriptors in the current process",
)

PROCESS_THREADS = Gauge(
    "flavorsnap_process_threads",
    "Number of threads in the current process",
)

# ---------------------------------------------------------------------------
# Business / application metrics
# ---------------------------------------------------------------------------

ACTIVE_REQUESTS = Gauge(
    "flavorsnap_active_requests",
    "Number of requests currently being processed",
)

UPLOAD_SIZE_BYTES = Histogram(
    "flavorsnap_upload_size_bytes",
    "Size of uploaded images in bytes",
    buckets=(10_000, 50_000, 100_000, 500_000, 1_000_000, 5_000_000, 10_000_000),
)

CLASSIFICATION_LATENCY_SUMMARY = Summary(
    "flavorsnap_classification_latency_seconds",
    "End-to-end classification latency (upload → response)",
)

API_UPTIME_SECONDS = Gauge(
    "flavorsnap_api_uptime_seconds",
    "Seconds since the API process started",
)


# ---------------------------------------------------------------------------
# Collector class
# ---------------------------------------------------------------------------


class MetricsCollector:
    """
    Central metrics collector.

    Wraps Prometheus metric objects and provides helper methods used by
    middleware and route handlers.  A background thread periodically
    refreshes system-level gauges.
    """

    def __init__(self, scrape_interval_seconds: int = 15) -> None:
        self._start_time = time.time()
        self._scrape_interval = scrape_interval_seconds
        self._stop_event = threading.Event()
        self._collector_thread = threading.Thread(
            target=self._collect_system_metrics_loop,
            daemon=True,
            name="metrics-collector",
        )
        self._collector_thread.start()

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def record_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration_seconds: float,
        request_size_bytes: int = 0,
        response_size_bytes: int = 0,
    ) -> None:
        """Record a completed HTTP request."""
        labels = {"method": method, "endpoint": endpoint}
        HTTP_REQUESTS_TOTAL.labels(
            method=method, endpoint=endpoint, status_code=str(status_code)
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(**labels).observe(duration_seconds)
        if request_size_bytes:
            HTTP_REQUEST_SIZE_BYTES.labels(**labels).observe(request_size_bytes)
        if response_size_bytes:
            HTTP_RESPONSE_SIZE_BYTES.labels(**labels).observe(response_size_bytes)
        if status_code >= 400:
            HTTP_ERRORS_TOTAL.labels(
                method=method, endpoint=endpoint, status_code=str(status_code)
            ).inc()

    def increment_active_requests(self) -> None:
        ACTIVE_REQUESTS.inc()

    def decrement_active_requests(self) -> None:
        ACTIVE_REQUESTS.dec()

    # ------------------------------------------------------------------
    # Inference helpers
    # ------------------------------------------------------------------

    def record_inference(
        self,
        duration_seconds: float,
        predicted_class: str,
        confidence: float,
        model_version: str = "v1",
        success: bool = True,
    ) -> None:
        """Record a model inference call."""
        status = "success" if success else "error"
        MODEL_INFERENCE_TOTAL.labels(model_version=model_version, status=status).inc()
        if success:
            MODEL_INFERENCE_DURATION_SECONDS.labels(model_version=model_version).observe(
                duration_seconds
            )
            MODEL_CONFIDENCE_HISTOGRAM.labels(predicted_class=predicted_class).observe(
                confidence
            )
            MODEL_PREDICTIONS_TOTAL.labels(predicted_class=predicted_class).inc()
            CLASSIFICATION_LATENCY_SUMMARY.observe(duration_seconds)

    def set_model_loaded(self, loaded: bool) -> None:
        MODEL_LOADED.set(1 if loaded else 0)

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def record_cache_hit(self, cache_type: str = "redis") -> None:
        CACHE_HITS_TOTAL.labels(cache_type=cache_type).inc()

    def record_cache_miss(self, cache_type: str = "redis") -> None:
        CACHE_MISSES_TOTAL.labels(cache_type=cache_type).inc()

    def set_cache_size(self, size_bytes: int, cache_type: str = "redis") -> None:
        CACHE_SIZE_BYTES.labels(cache_type=cache_type).set(size_bytes)

    # ------------------------------------------------------------------
    # Upload helpers
    # ------------------------------------------------------------------

    def record_upload(self, size_bytes: int) -> None:
        UPLOAD_SIZE_BYTES.observe(size_bytes)

    # ------------------------------------------------------------------
    # System metrics collection
    # ------------------------------------------------------------------

    def _collect_system_metrics(self) -> None:
        """Refresh system-level Prometheus gauges."""
        try:
            # CPU
            SYSTEM_CPU_USAGE_PERCENT.set(psutil.cpu_percent(interval=None))

            # Memory
            mem = psutil.virtual_memory()
            SYSTEM_MEMORY_USAGE_BYTES.set(mem.used)
            SYSTEM_MEMORY_TOTAL_BYTES.set(mem.total)

            # Disk (root mount)
            disk = psutil.disk_usage("/")
            SYSTEM_DISK_USAGE_PERCENT.labels(mount_point="/").set(disk.percent)

            # Process
            proc = psutil.Process(os.getpid())
            try:
                PROCESS_OPEN_FDS.set(proc.num_fds())
            except AttributeError:
                # Windows does not support num_fds
                pass
            PROCESS_THREADS.set(proc.num_threads())

            # Uptime
            API_UPTIME_SECONDS.set(time.time() - self._start_time)

        except Exception:
            # Never crash the background thread
            pass

    def _collect_system_metrics_loop(self) -> None:
        while not self._stop_event.is_set():
            self._collect_system_metrics()
            self._stop_event.wait(self._scrape_interval)

    def stop(self) -> None:
        """Stop the background collection thread."""
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Prometheus exposition
    # ------------------------------------------------------------------

    def generate_metrics(self) -> tuple[bytes, str]:
        """Return (body, content_type) for the /metrics endpoint."""
        return generate_latest(REGISTRY), CONTENT_TYPE_LATEST


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_collector: Optional[MetricsCollector] = None
_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """Return the process-wide MetricsCollector singleton."""
    global _collector
    if _collector is None:
        with _lock:
            if _collector is None:
                _collector = MetricsCollector()
    return _collector
