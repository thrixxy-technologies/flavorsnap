"""
Alerting system for FlavorSnap.

Evaluates threshold-based rules against live Prometheus metrics and
dispatches notifications via configurable channels (log, webhook, email).

Usage
-----
    from src.monitoring.alerting import get_alert_manager

    alert_manager = get_alert_manager()
    alert_manager.start()          # begin background evaluation loop
    ...
    alert_manager.stop()
"""

from __future__ import annotations

import dataclasses
import json
import logging
import smtplib
import threading
import time
import urllib.request
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclasses.dataclass
class AlertRule:
    """A single threshold-based alert rule."""

    name: str
    description: str
    severity: Severity
    # Callable that returns a float metric value; raise to signal unavailability
    metric_fn: Callable[[], float]
    threshold: float
    # "gt" (greater-than) or "lt" (less-than)
    comparison: str = "gt"
    # Seconds the condition must be true before firing
    for_seconds: float = 60.0
    # Seconds between re-notifications for the same active alert
    repeat_interval_seconds: float = 3600.0

    def evaluate(self, value: float) -> bool:
        if self.comparison == "gt":
            return value > self.threshold
        if self.comparison == "lt":
            return value < self.threshold
        return False


@dataclasses.dataclass
class ActiveAlert:
    rule: AlertRule
    first_triggered_at: float
    last_notified_at: float
    current_value: float
    firing: bool = False


# ---------------------------------------------------------------------------
# Notification channels
# ---------------------------------------------------------------------------


class NotificationChannel:
    """Base class for notification channels."""

    def send(self, alert: ActiveAlert) -> None:
        raise NotImplementedError


class LogChannel(NotificationChannel):
    """Writes alerts to the Python logging system."""

    def send(self, alert: ActiveAlert) -> None:
        level = {
            Severity.INFO: logging.INFO,
            Severity.WARNING: logging.WARNING,
            Severity.CRITICAL: logging.CRITICAL,
        }.get(alert.rule.severity, logging.WARNING)

        logger.log(
            level,
            "[ALERT] %s | severity=%s | value=%.4f | threshold=%.4f | %s",
            alert.rule.name,
            alert.rule.severity.value,
            alert.current_value,
            alert.rule.threshold,
            alert.rule.description,
        )


class WebhookChannel(NotificationChannel):
    """Posts a JSON payload to a webhook URL."""

    def __init__(self, url: str, timeout_seconds: int = 10) -> None:
        self.url = url
        self.timeout = timeout_seconds

    def send(self, alert: ActiveAlert) -> None:
        payload = json.dumps(
            {
                "alert": alert.rule.name,
                "severity": alert.rule.severity.value,
                "description": alert.rule.description,
                "value": alert.current_value,
                "threshold": alert.rule.threshold,
                "fired_at": alert.first_triggered_at,
            }
        ).encode()

        req = urllib.request.Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout):
                pass
        except Exception as exc:
            logger.warning("Webhook notification failed for %s: %s", alert.rule.name, exc)


class EmailChannel(NotificationChannel):
    """Sends alert emails via SMTP."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        from_addr: str,
        to_addrs: List[str],
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def send(self, alert: ActiveAlert) -> None:
        subject = f"[{alert.rule.severity.value.upper()}] FlavorSnap Alert: {alert.rule.name}"
        body = (
            f"Alert: {alert.rule.name}\n"
            f"Severity: {alert.rule.severity.value}\n"
            f"Description: {alert.rule.description}\n"
            f"Current value: {alert.current_value:.4f}\n"
            f"Threshold: {alert.rule.threshold}\n"
            f"Triggered at: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(alert.first_triggered_at))}\n"
        )
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)

        try:
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)

            if self.username and self.password:
                server.login(self.username, self.password)

            server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
            server.quit()
        except Exception as exc:
            logger.warning("Email notification failed for %s: %s", alert.rule.name, exc)


# ---------------------------------------------------------------------------
# Alert manager
# ---------------------------------------------------------------------------


class AlertManager:
    """
    Evaluates alert rules on a background thread and dispatches
    notifications through registered channels.
    """

    def __init__(self, evaluation_interval_seconds: float = 30.0) -> None:
        self._interval = evaluation_interval_seconds
        self._rules: List[AlertRule] = []
        self._channels: List[NotificationChannel] = [LogChannel()]
        self._active: Dict[str, ActiveAlert] = {}
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Register default rules (populated lazily when metrics are available)
        self._register_default_rules()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def add_rule(self, rule: AlertRule) -> None:
        with self._lock:
            self._rules.append(rule)

    def add_channel(self, channel: NotificationChannel) -> None:
        with self._lock:
            self._channels.append(channel)

    def _register_default_rules(self) -> None:
        """Register built-in alert rules using live psutil metrics."""
        import psutil

        self.add_rule(
            AlertRule(
                name="HighCPUUsage",
                description="CPU usage has exceeded 80% for the configured duration.",
                severity=Severity.WARNING,
                metric_fn=lambda: psutil.cpu_percent(interval=None),
                threshold=80.0,
                comparison="gt",
                for_seconds=120.0,
            )
        )
        self.add_rule(
            AlertRule(
                name="CriticalCPUUsage",
                description="CPU usage has exceeded 95%.",
                severity=Severity.CRITICAL,
                metric_fn=lambda: psutil.cpu_percent(interval=None),
                threshold=95.0,
                comparison="gt",
                for_seconds=60.0,
            )
        )
        self.add_rule(
            AlertRule(
                name="HighMemoryUsage",
                description="Memory usage has exceeded 85%.",
                severity=Severity.WARNING,
                metric_fn=lambda: psutil.virtual_memory().percent,
                threshold=85.0,
                comparison="gt",
                for_seconds=120.0,
            )
        )
        self.add_rule(
            AlertRule(
                name="CriticalMemoryUsage",
                description="Memory usage has exceeded 95%.",
                severity=Severity.CRITICAL,
                metric_fn=lambda: psutil.virtual_memory().percent,
                threshold=95.0,
                comparison="gt",
                for_seconds=60.0,
            )
        )
        self.add_rule(
            AlertRule(
                name="LowDiskSpace",
                description="Root filesystem disk usage has exceeded 90%.",
                severity=Severity.CRITICAL,
                metric_fn=lambda: psutil.disk_usage("/").percent,
                threshold=90.0,
                comparison="gt",
                for_seconds=300.0,
            )
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background evaluation loop."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._evaluation_loop,
            daemon=True,
            name="alert-manager",
        )
        self._thread.start()
        logger.info("AlertManager started (interval=%ss)", self._interval)

    def stop(self) -> None:
        """Stop the background evaluation loop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("AlertManager stopped")

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def _evaluation_loop(self) -> None:
        while not self._stop_event.is_set():
            self._evaluate_all()
            self._stop_event.wait(self._interval)

    def _evaluate_all(self) -> None:
        now = time.time()
        with self._lock:
            rules = list(self._rules)
            channels = list(self._channels)

        for rule in rules:
            try:
                value = rule.metric_fn()
            except Exception as exc:
                logger.debug("Metric function for %s raised: %s", rule.name, exc)
                continue

            triggered = rule.evaluate(value)

            with self._lock:
                active = self._active.get(rule.name)

                if triggered:
                    if active is None:
                        # New potential alert — start the "for" timer
                        self._active[rule.name] = ActiveAlert(
                            rule=rule,
                            first_triggered_at=now,
                            last_notified_at=0.0,
                            current_value=value,
                        )
                    else:
                        active.current_value = value
                        # Check if the "for" duration has elapsed
                        if not active.firing and (now - active.first_triggered_at) >= rule.for_seconds:
                            active.firing = True

                        if active.firing:
                            # Notify if first time or repeat interval elapsed
                            if (now - active.last_notified_at) >= rule.repeat_interval_seconds:
                                active.last_notified_at = now
                                for ch in channels:
                                    try:
                                        ch.send(active)
                                    except Exception as exc:
                                        logger.warning("Channel send failed: %s", exc)
                else:
                    # Condition cleared — resolve the alert
                    if active and active.firing:
                        logger.info("[RESOLVED] %s", rule.name)
                    self._active.pop(rule.name, None)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Return a snapshot of currently firing alerts."""
        with self._lock:
            return [
                {
                    "name": a.rule.name,
                    "severity": a.rule.severity.value,
                    "description": a.rule.description,
                    "value": a.current_value,
                    "threshold": a.rule.threshold,
                    "firing": a.firing,
                    "first_triggered_at": a.first_triggered_at,
                }
                for a in self._active.values()
            ]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_manager: Optional[AlertManager] = None
_lock = threading.Lock()


def get_alert_manager() -> AlertManager:
    """Return the process-wide AlertManager singleton."""
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = AlertManager()
    return _manager
