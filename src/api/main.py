from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

import yaml
from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .classifier import PyTorchFoodClassifier
from .middleware import configure_middleware
from .models import AppSettings
from .routes import router

# Monitoring imports — imported lazily so the app still starts if psutil
# or prometheus_client are not installed in the current environment.
try:
    from src.monitoring.metrics_collector import get_metrics_collector
    from src.monitoring.alerting import get_alert_manager
    from src.monitoring.dashboard import get_dashboard
    from src.monitoring.profiler import get_profiler
    _MONITORING_AVAILABLE = True
except ImportError:
    _MONITORING_AVAILABLE = False


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_settings(config_path: Path | None = None) -> AppSettings:
    config_file = config_path or repo_root() / "config.yaml"
    if not config_file.exists():
        return AppSettings()

    with config_file.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    return AppSettings.model_validate(data)


# ---------------------------------------------------------------------------
# Metrics middleware
# ---------------------------------------------------------------------------


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Records per-request HTTP metrics (count, latency, sizes) into
    Prometheus counters/histograms via MetricsCollector.

    Skipped gracefully when the monitoring package is unavailable.
    """

    async def dispatch(self, request: Request, call_next):
        if not _MONITORING_AVAILABLE:
            return await call_next(request)

        collector = get_metrics_collector()
        collector.increment_active_requests()

        # Normalise the path to avoid high-cardinality label explosion
        endpoint = _normalise_path(request.url.path)
        method = request.method
        request_size = int(request.headers.get("content-length", 0))

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            collector.decrement_active_requests()
            raise

        duration = time.perf_counter() - start
        collector.decrement_active_requests()

        # Response body size (best-effort from Content-Length header)
        response_size = int(response.headers.get("content-length", 0))

        collector.record_request(
            method=method,
            endpoint=endpoint,
            status_code=response.status_code,
            duration_seconds=duration,
            request_size_bytes=request_size,
            response_size_bytes=response_size,
        )
        return response


def _normalise_path(path: str) -> str:
    """
    Replace numeric path segments with {id} to keep label cardinality low.
    e.g. /api/v1/items/42 -> /api/v1/items/{id}
    """
    import re
    return re.sub(r"/\d+", "/{id}", path)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(
    settings: AppSettings | None = None,
    classifier: PyTorchFoodClassifier | None = None,
) -> FastAPI:
    resolved_settings = settings or load_settings()
    resolved_classifier = classifier or PyTorchFoodClassifier(
        model_path=repo_root() / resolved_settings.model.path,
        classes_path=repo_root() / resolved_settings.model.classes_path,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Load model
        try:
            await run_in_threadpool(app.state.classifier.load)
            app.state.startup_error = None
        except Exception as exc:
            app.state.startup_error = str(exc)

        # Start monitoring services
        if _MONITORING_AVAILABLE:
            try:
                get_metrics_collector()  # starts background system-metrics thread
                alert_manager = get_alert_manager()
                alert_manager.start()
                # Signal model loaded state
                get_metrics_collector().set_model_loaded(
                    app.state.startup_error is None
                )
            except Exception:
                pass  # monitoring failure must never prevent the app from starting

        yield

        # Shutdown monitoring services
        if _MONITORING_AVAILABLE:
            try:
                get_alert_manager().stop()
                get_metrics_collector().stop()
            except Exception:
                pass

    app = FastAPI(
        title=resolved_settings.api.title,
        version=resolved_settings.api.version,
        description=(
            "Programmatic REST API for FlavorSnap food classification. "
            "Upload a food image as multipart/form-data and receive ranked predictions."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.state.settings = resolved_settings
    app.state.classifier = resolved_classifier
    app.state.startup_error = None

    # Metrics middleware must be added before other middleware so it wraps
    # the full request lifecycle.
    if _MONITORING_AVAILABLE:
        app.add_middleware(MetricsMiddleware)

    configure_middleware(app, resolved_settings.api)
    app.include_router(router, prefix=resolved_settings.api.prefix)

    # ------------------------------------------------------------------
    # Root
    # ------------------------------------------------------------------

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "message": "FlavorSnap REST API",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    # ------------------------------------------------------------------
    # Prometheus metrics endpoint
    # ------------------------------------------------------------------

    @app.get("/metrics", include_in_schema=False, tags=["monitoring"])
    async def prometheus_metrics():
        """Expose Prometheus metrics for scraping."""
        if not _MONITORING_AVAILABLE:
            return Response(content="# monitoring unavailable\n", media_type="text/plain")
        body, content_type = get_metrics_collector().generate_metrics()
        return Response(content=body, media_type=content_type)

    # ------------------------------------------------------------------
    # Monitoring dashboard endpoints
    # ------------------------------------------------------------------

    @app.get("/monitoring/dashboard", tags=["monitoring"])
    async def monitoring_dashboard():
        """Full monitoring snapshot (system, inference, cache, alerts)."""
        if not _MONITORING_AVAILABLE:
            return JSONResponse({"error": "monitoring package not available"}, status_code=503)
        return get_dashboard().get_full_snapshot()

    @app.get("/monitoring/health", tags=["monitoring"])
    async def monitoring_health():
        """Condensed health summary with overall status."""
        if not _MONITORING_AVAILABLE:
            return JSONResponse({"status": "unknown", "reason": "monitoring package not available"})
        return get_dashboard().get_health_summary()

    @app.get("/monitoring/alerts", tags=["monitoring"])
    async def monitoring_alerts():
        """List of currently firing alerts."""
        if not _MONITORING_AVAILABLE:
            return JSONResponse({"alerts": [], "reason": "monitoring package not available"})
        return {"alerts": get_alert_manager().get_active_alerts()}

    @app.get("/monitoring/profiler", tags=["monitoring"])
    async def profiler_stats():
        """Performance profiler statistics for all recorded spans."""
        if not _MONITORING_AVAILABLE:
            return JSONResponse({"spans": [], "reason": "monitoring package not available"})
        return {"spans": get_profiler().get_all_stats()}

    return app


app = create_app()
