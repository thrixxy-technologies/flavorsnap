"""
Monitoring dashboard for FlavorSnap.

Provides a lightweight JSON API that aggregates live metrics from
Prometheus gauges/counters and system stats into a single response
suitable for a frontend dashboard or health-check page.

Endpoints (mounted by src/api/main.py):
  GET /monitoring/dashboard   — full dashboard snapshot
  GET /monitoring/health      — condensed health summary
  GET /monitoring/alerts      — active alert list
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List

import psutil

from .metrics_collector import get_metrics_collector
from .alerting import get_alert_manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cpu_stats() -> Dict[str, Any]:
    return {
        "usage_percent": psutil.cpu_percent(interval=None),
        "count_logical": psutil.cpu_count(logical=True),
        "count_physical": psutil.cpu_count(logical=False),
        "load_avg_1m": (
            psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else None
        ),
    }


def _memory_stats() -> Dict[str, Any]:
    mem = psutil.virtual_memory()
    return {
        "total_bytes": mem.total,
        "used_bytes": mem.used,
        "available_bytes": mem.available,
        "usage_percent": mem.percent,
    }


def _disk_stats() -> List[Dict[str, Any]]:
    results = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            results.append(
                {
                    "mountpoint": part.mountpoint,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "usage_percent": usage.percent,
                }
            )
        except PermissionError:
            pass
    return results


def _network_stats() -> Dict[str, Any]:
    net = psutil.net_io_counters()
    return {
        "bytes_sent": net.bytes_sent,
        "bytes_recv": net.bytes_recv,
        "packets_sent": net.packets_sent,
        "packets_recv": net.packets_recv,
        "errin": net.errin,
        "errout": net.errout,
    }


def _process_stats() -> Dict[str, Any]:
    proc = psutil.Process(os.getpid())
    mem_info = proc.memory_info()
    stats: Dict[str, Any] = {
        "pid": proc.pid,
        "cpu_percent": proc.cpu_percent(interval=None),
        "memory_rss_bytes": mem_info.rss,
        "memory_vms_bytes": mem_info.vms,
        "num_threads": proc.num_threads(),
        "status": proc.status(),
    }
    try:
        stats["open_fds"] = proc.num_fds()
    except AttributeError:
        stats["open_fds"] = None  # Windows
    return stats


# ---------------------------------------------------------------------------
# Dashboard builder
# ---------------------------------------------------------------------------


class MonitoringDashboard:
    """Aggregates metrics into structured dashboard snapshots."""

    def __init__(self) -> None:
        self._start_time = time.time()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_full_snapshot(self) -> Dict[str, Any]:
        """Return a complete monitoring snapshot."""
        collector = get_metrics_collector()
        alert_manager = get_alert_manager()

        return {
            "timestamp": time.time(),
            "uptime_seconds": time.time() - self._start_time,
            "system": {
                "cpu": _cpu_stats(),
                "memory": _memory_stats(),
                "disk": _disk_stats(),
                "network": _network_stats(),
                "process": _process_stats(),
            },
            "alerts": {
                "active": alert_manager.get_active_alerts(),
                "total_active": len(alert_manager.get_active_alerts()),
            },
            "links": {
                "prometheus": "http://localhost:9090",
                "grafana": "http://localhost:3001",
                "alertmanager": "http://localhost:9093",
                "metrics_endpoint": "/metrics",
            },
        }

    def get_health_summary(self) -> Dict[str, Any]:
        """Return a condensed health summary."""
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        active_alerts = get_alert_manager().get_active_alerts()
        critical_alerts = [a for a in active_alerts if a["severity"] == "critical"]

        if critical_alerts or cpu > 95 or mem.percent > 95 or disk.percent > 95:
            overall = "critical"
        elif active_alerts or cpu > 80 or mem.percent > 85 or disk.percent > 90:
            overall = "degraded"
        else:
            overall = "healthy"

        return {
            "status": overall,
            "timestamp": time.time(),
            "checks": {
                "cpu": {
                    "status": "ok" if cpu < 80 else "warning" if cpu < 95 else "critical",
                    "value_percent": cpu,
                },
                "memory": {
                    "status": "ok" if mem.percent < 85 else "warning" if mem.percent < 95 else "critical",
                    "value_percent": mem.percent,
                },
                "disk": {
                    "status": "ok" if disk.percent < 80 else "warning" if disk.percent < 90 else "critical",
                    "value_percent": disk.percent,
                },
                "alerts": {
                    "status": "ok" if not active_alerts else "warning" if not critical_alerts else "critical",
                    "active_count": len(active_alerts),
                    "critical_count": len(critical_alerts),
                },
            },
        }

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        return get_alert_manager().get_active_alerts()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_dashboard: MonitoringDashboard | None = None


def get_dashboard() -> MonitoringDashboard:
    global _dashboard
    if _dashboard is None:
        _dashboard = MonitoringDashboard()
    return _dashboard
