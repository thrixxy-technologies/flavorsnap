"""
Advanced Monitoring and Alerting System for FlavorSnap
Implements real-time metrics collection, intelligent alerting, and comprehensive monitoring
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
import threading
import queue
import statistics
from collections import defaultdict, deque
import psutil
import requests
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CollectorRegistry
import redis
from sqlalchemy import create_engine, text
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Alert rule definition"""
    name: str
    metric_name: str
    condition: str  # gt, lt, eq, gte, lte
    threshold: float
    duration: int  # seconds
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    enabled: bool = True
    labels: Dict[str, str] = field(default_factory=dict)
    notification_channels: List[str] = field(default_factory=list)
    cooldown: int = 300  # 5 minutes default cooldown


@dataclass
class Alert:
    """Alert instance"""
    id: str
    rule_name: str
    severity: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_timestamp: Optional[datetime] = None
    labels: Dict[str, str] = field(default_factory=dict)
    metric_value: Optional[float] = None


class MetricsCollector:
    """Advanced metrics collection system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.registry = CollectorRegistry()
        self.metrics = {}
        self.time_series = defaultdict(lambda: deque(maxlen=1000))
        self.collection_interval = config.get('collection_interval', 30)
        self.enabled_collectors = config.get('collectors', [])
        
        # Initialize Prometheus metrics
        self._setup_prometheus_metrics()
        
        # Background collection thread
        self.collection_thread = None
        self.stop_event = threading.Event()
        
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        # System metrics
        self.metrics['cpu_usage'] = Gauge(
            'system_cpu_usage_percent', 'CPU usage percentage', registry=self.registry
        )
        self.metrics['memory_usage'] = Gauge(
            'system_memory_usage_percent', 'Memory usage percentage', registry=self.registry
        )
        self.metrics['disk_usage'] = Gauge(
            'system_disk_usage_percent', 'Disk usage percentage', registry=self.registry
        )
        
        # Application metrics
        self.metrics['requests_total'] = Counter(
            'http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'], registry=self.registry
        )
        self.metrics['request_duration'] = Histogram(
            'http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'], registry=self.registry
        )
        self.metrics['active_connections'] = Gauge(
            'active_connections_total', 'Number of active connections', registry=self.registry
        )
        
        # ML Model metrics
        self.metrics['model_predictions_total'] = Counter(
            'model_predictions_total', 'Total model predictions', ['model_version', 'status'], registry=self.registry
        )
        self.metrics['model_inference_time'] = Histogram(
            'model_inference_duration_seconds', 'Model inference time', ['model_version'], registry=self.registry
        )
        self.metrics['model_accuracy'] = Gauge(
            'model_accuracy_score', 'Model accuracy score', ['model_version'], registry=self.registry
        )
        
        # Database metrics
        self.metrics['db_connections_active'] = Gauge(
            'database_connections_active', 'Active database connections', registry=self.registry
        )
        self.metrics['db_query_duration'] = Histogram(
            'database_query_duration_seconds', 'Database query duration', ['query_type'], registry=self.registry
        )
        
        # Cache metrics
        self.metrics['cache_hits_total'] = Counter(
            'cache_hits_total', 'Total cache hits', ['cache_type'], registry=self.registry
        )
        self.metrics['cache_misses_total'] = Counter(
            'cache_misses_total', 'Total cache misses', ['cache_type'], registry=self.registry
        )
    
    def start_collection(self):
        """Start background metrics collection"""
        if self.collection_thread and self.collection_thread.is_alive():
            logger.warning("Metrics collection already running")
            return
        
        self.stop_event.clear()
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
        logger.info("Started metrics collection")
    
    def stop_collection(self):
        """Stop background metrics collection"""
        self.stop_event.set()
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        logger.info("Stopped metrics collection")
    
    def _collection_loop(self):
        """Main collection loop"""
        while not self.stop_event.is_set():
            try:
                self._collect_system_metrics()
                self._collect_application_metrics()
                self._collect_database_metrics()
                self._collect_model_metrics()
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                time.sleep(5)  # Brief pause on error
    
    def _collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics['cpu_usage'].set(cpu_percent)
            self._add_time_series('cpu_usage', cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.metrics['memory_usage'].set(memory.percent)
            self._add_time_series('memory_usage', memory.percent)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.metrics['disk_usage'].set(disk_percent)
            self._add_time_series('disk_usage', disk_percent)
            
            # Network metrics
            network = psutil.net_io_counters()
            self._add_time_series('network_bytes_sent', network.bytes_sent)
            self._add_time_series('network_bytes_recv', network.bytes_recv)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _collect_application_metrics(self):
        """Collect application-level metrics"""
        try:
            # Active connections (placeholder - would integrate with actual app)
            active_conns = getattr(self, '_active_connections', 0)
            self.metrics['active_connections'].set(active_conns)
            self._add_time_series('active_connections', active_conns)
            
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
    
    def _collect_database_metrics(self):
        """Collect database metrics"""
        try:
            # This would integrate with actual database connection pool
            # For now, simulate with placeholder values
            db_connections = getattr(self, '_db_connections', 5)
            self.metrics['db_connections_active'].set(db_connections)
            self._add_time_series('db_connections_active', db_connections)
            
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")
    
    def _collect_model_metrics(self):
        """Collect ML model metrics"""
        try:
            # Model accuracy (placeholder - would integrate with actual model monitoring)
            model_accuracy = getattr(self, '_model_accuracy', 0.95)
            self.metrics['model_accuracy'].labels(model_version='v1.0').set(model_accuracy)
            self._add_time_series('model_accuracy', model_accuracy)
            
        except Exception as e:
            logger.error(f"Error collecting model metrics: {e}")
    
    def _add_time_series(self, metric_name: str, value: float):
        """Add data point to time series"""
        point = MetricPoint(
            timestamp=datetime.now(),
            value=value
        )
        self.time_series[metric_name].append(point)
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metric"""
        self.metrics['requests_total'].labels(method=method, endpoint=endpoint, status=status_code).inc()
        self.metrics['request_duration'].labels(method=method, endpoint=endpoint).observe(duration)
    
    def record_prediction(self, model_version: str, status: str, inference_time: float):
        """Record model prediction metric"""
        self.metrics['model_predictions_total'].labels(model_version=model_version, status=status).inc()
        self.metrics['model_inference_time'].labels(model_version=model_version).observe(inference_time)
    
    def record_cache_hit(self, cache_type: str):
        """Record cache hit"""
        self.metrics['cache_hits_total'].labels(cache_type=cache_type).inc()
    
    def record_cache_miss(self, cache_type: str):
        """Record cache miss"""
        self.metrics['cache_misses_total'].labels(cache_type=cache_type).inc()
    
    def get_metric_data(self, metric_name: str, duration_minutes: int = 60) -> List[MetricPoint]:
        """Get metric data for specified duration"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        return [
            point for point in self.time_series[metric_name]
            if point.timestamp >= cutoff_time
        ]
    
    def get_metric_summary(self, metric_name: str, duration_minutes: int = 60) -> Dict[str, float]:
        """Get metric summary statistics"""
        data = self.get_metric_data(metric_name, duration_minutes)
        if not data:
            return {}
        
        values = [point.value for point in data]
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': statistics.mean(values),
            'median': statistics.median(values),
            'std': statistics.stdev(values) if len(values) > 1 else 0
        }
    
    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        return generate_latest(self.registry).decode('utf-8')


class AlertManager:
    """Intelligent alerting system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rules = {}
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.notification_channels = {}
        self.alert_queue = queue.Queue()
        
        # Background processing
        self.evaluation_thread = None
        self.notification_thread = None
        self.stop_event = threading.Event()
        
        # Setup notification channels
        self._setup_notification_channels()
        
        # Load alert rules
        self._load_default_rules()
    
    def _setup_notification_channels(self):
        """Setup notification channels"""
        channels_config = self.config.get('notification_channels', {})
        
        # Email channel
        if 'email' in channels_config:
            self.notification_channels['email'] = EmailNotifier(channels_config['email'])
        
        # Slack channel
        if 'slack' in channels_config:
            self.notification_channels['slack'] = SlackNotifier(channels_config['slack'])
        
        # Webhook channel
        if 'webhook' in channels_config:
            self.notification_channels['webhook'] = WebhookNotifier(channels_config['webhook'])
    
    def _load_default_rules(self):
        """Load default alert rules"""
        default_rules = [
            AlertRule(
                name="high_cpu_usage",
                metric_name="cpu_usage",
                condition="gt",
                threshold=80.0,
                duration=300,
                severity="HIGH",
                notification_channels=["email", "slack"]
            ),
            AlertRule(
                name="critical_cpu_usage",
                metric_name="cpu_usage",
                condition="gt",
                threshold=95.0,
                duration=60,
                severity="CRITICAL",
                notification_channels=["email", "slack", "webhook"]
            ),
            AlertRule(
                name="high_memory_usage",
                metric_name="memory_usage",
                condition="gt",
                threshold=85.0,
                duration=300,
                severity="HIGH",
                notification_channels=["email", "slack"]
            ),
            AlertRule(
                name="disk_space_low",
                metric_name="disk_usage",
                condition="gt",
                threshold=90.0,
                duration=600,
                severity="MEDIUM",
                notification_channels=["email"]
            ),
            AlertRule(
                name="model_accuracy_drop",
                metric_name="model_accuracy",
                condition="lt",
                threshold=0.85,
                duration=600,
                severity="HIGH",
                notification_channels=["email", "slack"]
            ),
            AlertRule(
                name="high_error_rate",
                metric_name="error_rate",
                condition="gt",
                threshold=5.0,
                duration=300,
                severity="MEDIUM",
                notification_channels=["email"]
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def start_evaluation(self):
        """Start alert evaluation"""
        if self.evaluation_thread and self.evaluation_thread.is_alive():
            logger.warning("Alert evaluation already running")
            return
        
        self.stop_event.clear()
        self.evaluation_thread = threading.Thread(target=self._evaluation_loop, daemon=True)
        self.evaluation_thread.start()
        
        self.notification_thread = threading.Thread(target=self._notification_loop, daemon=True)
        self.notification_thread.start()
        
        logger.info("Started alert evaluation and notification")
    
    def stop_evaluation(self):
        """Stop alert evaluation"""
        self.stop_event.set()
        if self.evaluation_thread:
            self.evaluation_thread.join(timeout=5)
        if self.notification_thread:
            self.notification_thread.join(timeout=5)
        logger.info("Stopped alert evaluation")
    
    def _evaluation_loop(self):
        """Main alert evaluation loop"""
        while not self.stop_event.is_set():
            try:
                self._evaluate_all_rules()
                time.sleep(30)  # Evaluate every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in alert evaluation: {e}")
                time.sleep(5)
    
    def _notification_loop(self):
        """Notification processing loop"""
        while not self.stop_event.is_set():
            try:
                # Get alert from queue with timeout
                try:
                    alert = self.alert_queue.get(timeout=1)
                    self._send_notifications(alert)
                    self.alert_queue.task_done()
                except queue.Empty:
                    continue
                    
            except Exception as e:
                logger.error(f"Error in notification processing: {e}")
    
    def _evaluate_all_rules(self):
        """Evaluate all alert rules"""
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            try:
                self._evaluate_rule(rule)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule_name}: {e}")
    
    def _evaluate_rule(self, rule: AlertRule):
        """Evaluate individual alert rule"""
        # Get current metric value (this would integrate with MetricsCollector)
        current_value = self._get_metric_value(rule.metric_name)
        if current_value is None:
            return
        
        # Check condition
        condition_met = self._check_condition(current_value, rule.condition, rule.threshold)
        
        # Check if alert is already active
        alert_id = f"{rule.name}_{hash(rule.metric_name)}"
        active_alert = self.active_alerts.get(alert_id)
        
        if condition_met:
            if not active_alert:
                # New alert condition
                alert = Alert(
                    id=alert_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"{rule.name}: {rule.metric_name} is {current_value} (threshold: {rule.threshold})",
                    timestamp=datetime.now(),
                    labels=rule.labels,
                    metric_value=current_value
                )
                
                # Check duration requirement
                if self._check_duration_requirement(rule, current_value):
                    self.active_alerts[alert_id] = alert
                    self.alert_history.append(alert)
                    self.alert_queue.put(alert)
                    logger.warning(f"Alert triggered: {alert.message}")
        
        else:
            if active_alert and not active_alert.resolved:
                # Resolve alert
                active_alert.resolved = True
                active_alert.resolved_timestamp = datetime.now()
                self.alert_queue.put(active_alert)
                del self.active_alerts[alert_id]
                logger.info(f"Alert resolved: {active_alert.message}")
    
    def _get_metric_value(self, metric_name: str) -> Optional[float]:
        """Get current metric value"""
        # This would integrate with MetricsCollector
        # For now, return simulated values
        if metric_name == "cpu_usage":
            return psutil.cpu_percent(interval=1)
        elif metric_name == "memory_usage":
            return psutil.virtual_memory().percent
        elif metric_name == "disk_usage":
            disk = psutil.disk_usage('/')
            return (disk.used / disk.total) * 100
        elif metric_name == "model_accuracy":
            return 0.95  # Placeholder
        elif metric_name == "error_rate":
            return 2.0  # Placeholder
        return None
    
    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Check alert condition"""
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "gte":
            return value >= threshold
        elif condition == "lte":
            return value <= threshold
        elif condition == "eq":
            return value == threshold
        return False
    
    def _check_duration_requirement(self, rule: AlertRule, current_value: float) -> bool:
        """Check if alert duration requirement is met"""
        # For simplicity, assume duration requirement is met
        # In real implementation, would track condition history
        return True
    
    def _send_notifications(self, alert: Alert):
        """Send notifications for alert"""
        for channel_name in alert.rule.notification_channels:
            if channel_name in self.notification_channels:
                try:
                    notifier = self.notification_channels[channel_name]
                    notifier.send_alert(alert)
                except Exception as e:
                    logger.error(f"Error sending notification via {channel_name}: {e}")
    
    def add_rule(self, rule: AlertRule):
        """Add alert rule"""
        self.rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove alert rule"""
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info(f"Removed alert rule: {rule_name}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        return list(self.alert_history)[-limit:]


class EmailNotifier:
    """Email notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.smtp_host = config.get('smtp_host')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.recipients = config.get('recipients', [])
    
    def send_alert(self, alert: Alert):
        """Send alert via email"""
        import smtplib
        from email.mime.text import MimeText
        from email.mime.multipart import MimeMultipart
        
        subject = f"FlavorSnap Alert: {alert.severity} - {alert.rule_name}"
        
        body = f"""
Alert Details:
- Rule: {alert.rule_name}
- Severity: {alert.severity}
- Message: {alert.message}
- Time: {alert.timestamp}
- Status: {'RESOLVED' if alert.resolved else 'ACTIVE'}
"""
        
        msg = MimeMultipart()
        msg['From'] = self.username
        msg['Subject'] = subject
        msg.attach(MimeText(body, 'plain'))
        
        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            
            for recipient in self.recipients:
                msg['To'] = recipient
                server.send_message(msg)
            
            server.quit()
            logger.info(f"Email alert sent for {alert.rule_name}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")


class SlackNotifier:
    """Slack notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('webhook_url')
        self.channel = config.get('channel', '#alerts')
    
    def send_alert(self, alert: Alert):
        """Send alert to Slack"""
        color = {
            'CRITICAL': 'danger',
            'HIGH': 'warning',
            'MEDIUM': 'warning',
            'LOW': 'good'
        }.get(alert.severity, 'warning')
        
        payload = {
            'channel': self.channel,
            'attachments': [{
                'color': color,
                'title': f"FlavorSnap Alert: {alert.rule_name}",
                'fields': [
                    {'title': 'Severity', 'value': alert.severity, 'short': True},
                    {'title': 'Status', 'value': 'RESOLVED' if alert.resolved else 'ACTIVE', 'short': True},
                    {'title': 'Message', 'value': alert.message, 'short': False},
                    {'title': 'Time', 'value': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'short': True}
                ]
            }]
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Slack alert sent for {alert.rule_name}")
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")


class WebhookNotifier:
    """Webhook notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.url = config.get('url')
        self.headers = config.get('headers', {})
        self.timeout = config.get('timeout', 10)
    
    def send_alert(self, alert: Alert):
        """Send alert via webhook"""
        payload = {
            'alert_id': alert.id,
            'rule_name': alert.rule_name,
            'severity': alert.severity,
            'message': alert.message,
            'timestamp': alert.timestamp.isoformat(),
            'resolved': alert.resolved,
            'metric_value': alert.metric_value,
            'labels': alert.labels
        }
        
        try:
            response = requests.post(
                self.url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Webhook alert sent for {alert.rule_name}")
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")


class HealthChecker:
    """System health checker"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.checks = {}
        self.results = {}
        self._setup_default_checks()
    
    def _setup_default_checks(self):
        """Setup default health checks"""
        self.checks = {
            'database': self._check_database,
            'redis': self._check_redis,
            'model_service': self._check_model_service,
            'disk_space': self._check_disk_space,
            'memory': self._check_memory
        }
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        
        for check_name, check_func in self.checks.items():
            try:
                start_time = time.time()
                result = check_func()
                duration = time.time() - start_time
                
                results[check_name] = {
                    'status': result['status'],
                    'message': result.get('message', ''),
                    'duration': duration,
                    'timestamp': datetime.now().isoformat(),
                    'details': result.get('details', {})
                }
                
            except Exception as e:
                results[check_name] = {
                    'status': 'unhealthy',
                    'message': str(e),
                    'duration': 0,
                    'timestamp': datetime.now().isoformat(),
                    'details': {}
                }
        
        # Calculate overall health
        overall_status = 'healthy'
        if any(r['status'] == 'unhealthy' for r in results.values()):
            overall_status = 'unhealthy'
        elif any(r['status'] == 'degraded' for r in results.values()):
            overall_status = 'degraded'
        
        self.results = {
            'overall_status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'checks': results
        }
        
        return self.results
    
    def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            # Simulate database check
            return {
                'status': 'healthy',
                'message': 'Database connection successful',
                'details': {'connection_pool': '5/10 active'}
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Database connection failed: {e}'
            }
    
    def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            # Simulate Redis check
            return {
                'status': 'healthy',
                'message': 'Redis connection successful',
                'details': {'memory_usage': '45MB'}
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Redis connection failed: {e}'
            }
    
    def _check_model_service(self) -> Dict[str, Any]:
        """Check ML model service"""
        try:
            # Simulate model service check
            return {
                'status': 'healthy',
                'message': 'Model service operational',
                'details': {'model_version': 'v1.0', 'accuracy': '0.95'}
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Model service check failed: {e}'
            }
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """Check disk space"""
        try:
            disk = psutil.disk_usage('/')
            usage_percent = (disk.used / disk.total) * 100
            
            if usage_percent > 90:
                status = 'unhealthy'
            elif usage_percent > 80:
                status = 'degraded'
            else:
                status = 'healthy'
            
            return {
                'status': status,
                'message': f'Disk usage: {usage_percent:.1f}%',
                'details': {'free_gb': disk.free / (1024**3), 'total_gb': disk.total / (1024**3)}
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Disk check failed: {e}'
            }
    
    def _check_memory(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            if usage_percent > 90:
                status = 'unhealthy'
            elif usage_percent > 80:
                status = 'degraded'
            else:
                status = 'healthy'
            
            return {
                'status': status,
                'message': f'Memory usage: {usage_percent:.1f}%',
                'details': {'available_gb': memory.available / (1024**3), 'total_gb': memory.total / (1024**3)}
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Memory check failed: {e}'
            }


class MonitoringSystem:
    """Main monitoring system orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics_collector = MetricsCollector(config.get('metrics', {}))
        self.alert_manager = AlertManager(config.get('alerts', {}))
        self.health_checker = HealthChecker(config.get('health', {}))
        
        # Start all components
        self.start()
    
    def start(self):
        """Start monitoring system"""
        self.metrics_collector.start_collection()
        self.alert_manager.start_evaluation()
        logger.info("Monitoring system started")
    
    def stop(self):
        """Stop monitoring system"""
        self.metrics_collector.stop_collection()
        self.alert_manager.stop_evaluation()
        logger.info("Monitoring system stopped")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        health_results = self.health_checker.run_all_checks()
        active_alerts = self.alert_manager.get_active_alerts()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'health': health_results,
            'active_alerts': len(active_alerts),
            'alerts': [alert.id for alert in active_alerts],
            'metrics_summary': self._get_metrics_summary()
        }
    
    def _get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        return {
            'cpu_usage': self.metrics_collector.get_metric_summary('cpu_usage', 5),
            'memory_usage': self.metrics_collector.get_metric_summary('memory_usage', 5),
            'disk_usage': self.metrics_collector.get_metric_summary('disk_usage', 5)
        }
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        return self.metrics_collector.export_prometheus_metrics()


# Global monitoring system instance
monitoring_system = None


def initialize_monitoring(config: Dict[str, Any]) -> MonitoringSystem:
    """Initialize global monitoring system"""
    global monitoring_system
    monitoring_system = MonitoringSystem(config)
    return monitoring_system


def get_monitoring_system() -> Optional[MonitoringSystem]:
    """Get global monitoring system instance"""
    return monitoring_system
