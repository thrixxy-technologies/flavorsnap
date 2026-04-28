"""
Advanced Audit Monitoring System for FlavorSnap API
Implements real-time monitoring, anomaly detection, and alerting for audit events
"""
import os
import json
import time
import threading
import queue
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import uuid
import redis
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import numpy as np
from audit_logger import audit_logger, AuditEvent, AuditEventType, AuditSeverity
from compliance_checker import compliance_checker, ComplianceFramework


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MonitorType(Enum):
    """Monitor types"""
    THRESHOLD = "threshold"
    ANOMALY = "anomaly"
    PATTERN = "pattern"
    COMPLIANCE = "compliance"


@dataclass
class Alert:
    """Alert data structure"""
    alert_id: str
    timestamp: datetime
    severity: AlertSeverity
    monitor_type: MonitorType
    title: str
    description: str
    source: str
    event_data: Dict[str, Any]
    metadata: Dict[str, Any]
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        if self.acknowledged_at:
            data['acknowledged_at'] = self.acknowledged_at.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data


@dataclass
class MonitorConfig:
    """Monitor configuration"""
    monitor_id: str
    name: str
    type: MonitorType
    enabled: bool
    check_interval: int  # seconds
    threshold_value: Optional[float] = None
    window_size: Optional[int] = None
    alert_severity: AlertSeverity = AlertSeverity.WARNING
    description: str = ""
    metadata: Dict[str, Any] = None


@dataclass
class MonitoringMetrics:
    """Monitoring metrics data structure"""
    timestamp: datetime
    total_events: int
    events_by_type: Dict[str, int]
    events_by_severity: Dict[str, int]
    unique_users: int
    unique_ips: int
    error_rate: float
    avg_response_time: float
    anomaly_score: float
    compliance_score: float


class AuditMonitor:
    """Base audit monitor class"""
    
    def __init__(self, config: MonitorConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.last_check = datetime.now()
        self.alert_callbacks: List[Callable[[Alert], None]] = []
    
    def check(self, events: List[AuditEvent]) -> List[Alert]:
        """Check for conditions and return alerts"""
        raise NotImplementedError
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Add alert callback"""
        self.alert_callbacks.append(callback)
    
    def _create_alert(self, severity: AlertSeverity, title: str, 
                     description: str, event_data: Dict[str, Any]) -> Alert:
        """Create alert"""
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            severity=severity,
            monitor_type=self.config.type,
            title=title,
            description=description,
            source=self.config.name,
            event_data=event_data,
            metadata=self.config.metadata or {}
        )
        
        # Trigger callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {str(e)}")
        
        return alert


class ThresholdMonitor(AuditMonitor):
    """Threshold-based monitor"""
    
    def check(self, events: List[AuditEvent]) -> List[Alert]:
        """Check threshold conditions"""
        alerts = []
        
        if not self.config.threshold_value or not self.config.window_size:
            return alerts
        
        # Filter events in window
        window_start = datetime.now() - timedelta(seconds=self.config.window_size)
        recent_events = [e for e in events if e.timestamp >= window_start]
        
        # Check different threshold types
        if self.config.monitor_id == "error_rate_threshold":
            alerts.extend(self._check_error_rate(recent_events))
        elif self.config.monitor_id == "failed_auth_threshold":
            alerts.extend(self._check_failed_auth(recent_events))
        elif self.config.monitor_id == "high_severity_threshold":
            alerts.extend(self._check_high_severity(recent_events))
        elif self.config.monitor_id == "request_volume_threshold":
            alerts.extend(self._check_request_volume(recent_events))
        
        return alerts
    
    def _check_error_rate(self, events: List[AuditEvent]) -> List[Alert]:
        """Check error rate threshold"""
        error_events = [e for e in events if e.status_code and e.status_code >= 400]
        error_rate = len(error_events) / len(events) if events else 0
        
        if error_rate > self.config.threshold_value:
            alert = self._create_alert(
                severity=self.config.alert_severity,
                title="High Error Rate Detected",
                description=f"Error rate ({error_rate:.2%}) exceeds threshold ({self.config.threshold_value:.2%})",
                event_data={
                    'error_rate': error_rate,
                    'error_count': len(error_events),
                    'total_events': len(events),
                    'window_size': self.config.window_size
                }
            )
            return [alert]
        
        return []
    
    def _check_failed_auth(self, events: List[AuditEvent]) -> List[Alert]:
        """Check failed authentication threshold"""
        auth_events = [e for e in events if e.event_type == AuditEventType.AUTHENTICATION]
        failed_auth = [e for e in auth_events if e.status_code and e.status_code >= 400]
        failed_rate = len(failed_auth) / len(auth_events) if auth_events else 0
        
        if failed_rate > self.config.threshold_value:
            alert = self._create_alert(
                severity=self.config.alert_severity,
                title="High Failed Authentication Rate",
                description=f"Failed authentication rate ({failed_rate:.2%}) exceeds threshold ({self.config.threshold_value:.2%})",
                event_data={
                    'failed_rate': failed_rate,
                    'failed_count': len(failed_auth),
                    'total_auth_events': len(auth_events),
                    'window_size': self.config.window_size
                }
            )
            return [alert]
        
        return []
    
    def _check_high_severity(self, events: List[AuditEvent]) -> List[Alert]:
        """Check high severity events threshold"""
        high_severity_events = [e for e in events if e.severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]]
        
        if len(high_severity_events) > self.config.threshold_value:
            alert = self._create_alert(
                severity=self.config.alert_severity,
                title="High Severity Events Threshold Exceeded",
                description=f"High severity events ({len(high_severity_events)}) exceed threshold ({self.config.threshold_value})",
                event_data={
                    'high_severity_count': len(high_severity_events),
                    'total_events': len(events),
                    'window_size': self.config.window_size
                }
            )
            return [alert]
        
        return []
    
    def _check_request_volume(self, events: List[AuditEvent]) -> List[Alert]:
        """Check request volume threshold"""
        request_events = [e for e in events if e.event_type == AuditEventType.API_REQUEST]
        
        if len(request_events) > self.config.threshold_value:
            alert = self._create_alert(
                severity=self.config.alert_severity,
                title="High Request Volume Detected",
                description=f"Request volume ({len(request_events)}) exceeds threshold ({self.config.threshold_value})",
                event_data={
                    'request_count': len(request_events),
                    'window_size': self.config.window_size,
                    'requests_per_second': len(request_events) / self.config.window_size
                }
            )
            return [alert]
        
        return []


class AnomalyMonitor(AuditMonitor):
    """Anomaly detection monitor using machine learning"""
    
    def __init__(self, config: MonitorConfig):
        super().__init__(config)
        self.scaler = StandardScaler()
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.is_trained = False
        self.feature_history: deque = deque(maxlen=10000)
    
    def check(self, events: List[AuditEvent]) -> List[Alert]:
        """Check for anomalies"""
        alerts = []
        
        if len(events) < 10:  # Need minimum events for anomaly detection
            return alerts
        
        # Extract features
        features = self._extract_features(events)
        
        if not features:
            return alerts
        
        # Train model if not trained or retrain periodically
        if not self.is_trained or len(self.feature_history) > 5000:
            self._train_model()
        
        # Detect anomalies
        anomalies = self._detect_anomalies(features, events)
        
        for anomaly_idx, anomaly_score in anomalies:
            event = events[anomaly_idx]
            
            alert = self._create_alert(
                severity=AlertSeverity.WARNING if anomaly_score < 0.5 else AlertSeverity.ERROR,
                title="Anomalous Activity Detected",
                description=f"Anomaly detected with score {anomaly_score:.3f}",
                event_data={
                    'anomaly_score': anomaly_score,
                    'event_id': event.event_id,
                    'event_type': event.event_type.value,
                    'user_id': event.user_id,
                    'ip_address': event.ip_address,
                    'features': features[anomaly_idx].tolist()
                }
            )
            alerts.append(alert)
        
        return alerts
    
    def _extract_features(self, events: List[AuditEvent]) -> np.ndarray:
        """Extract features from events"""
        features = []
        
        for event in events:
            feature_vector = [
                # Time-based features
                event.timestamp.hour,
                event.timestamp.minute,
                event.timestamp.weekday(),
                
                # Event type (one-hot encoded)
                1 if event.event_type == AuditEventType.API_REQUEST else 0,
                1 if event.event_type == AuditEventType.API_RESPONSE else 0,
                1 if event.event_type == AuditEventType.AUTHENTICATION else 0,
                1 if event.event_type == AuditEventType.DATA_ACCESS else 0,
                1 if event.event_type == AuditEventType.DATA_MODIFICATION else 0,
                1 if event.event_type == AuditEventType.SECURITY_EVENT else 0,
                
                # Severity (numeric)
                1 if event.severity == AuditSeverity.LOW else 0,
                1 if event.severity == AuditSeverity.MEDIUM else 0,
                1 if event.severity == AuditSeverity.HIGH else 0,
                1 if event.severity == AuditSeverity.CRITICAL else 0,
                
                # Status code
                event.status_code or 200,
                
                # Response time (if available)
                event.details.get('duration_ms', 0) / 1000.0,  # Convert to seconds
            ]
            
            features.append(feature_vector)
            self.feature_history.append(feature_vector)
        
        return np.array(features)
    
    def _train_model(self):
        """Train anomaly detection model"""
        if len(self.feature_history) < 100:
            return
        
        try:
            # Prepare training data
            train_data = np.array(list(self.feature_history))
            
            # Scale features
            self.scaler.fit(train_data)
            scaled_data = self.scaler.transform(train_data)
            
            # Train model
            self.model.fit(scaled_data)
            self.is_trained = True
            
            self.logger.info("Anomaly detection model trained successfully")
        except Exception as e:
            self.logger.error(f"Failed to train anomaly detection model: {str(e)}")
    
    def _detect_anomalies(self, features: np.ndarray, events: List[AuditEvent]) -> List[Tuple[int, float]]:
        """Detect anomalies in features"""
        if not self.is_trained:
            return []
        
        try:
            # Scale features
            scaled_features = self.scaler.transform(features)
            
            # Predict anomalies
            predictions = self.model.predict(scaled_features)
            scores = self.model.decision_function(scaled_features)
            
            # Find anomalies (predictions == -1)
            anomalies = []
            for i, (pred, score) in enumerate(zip(predictions, scores)):
                if pred == -1:  # Anomaly
                    # Convert score to 0-1 range (higher = more anomalous)
                    anomaly_score = (1 - score) / 2
                    anomalies.append((i, anomaly_score))
            
            return anomalies
        except Exception as e:
            self.logger.error(f"Anomaly detection failed: {str(e)}")
            return []


class PatternMonitor(AuditMonitor):
    """Pattern-based monitor for specific event patterns"""
    
    def __init__(self, config: MonitorConfig):
        super().__init__(config)
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> List[Dict[str, Any]]:
        """Load monitoring patterns"""
        return [
            {
                'name': 'brute_force_attack',
                'description': 'Multiple failed auth attempts from same IP',
                'conditions': {
                    'event_type': AuditEventType.AUTHENTICATION,
                    'status_code_range': (400, 499),
                    'same_ip': True,
                    'count_threshold': 5,
                    'time_window': 300  # 5 minutes
                },
                'severity': AlertSeverity.ERROR
            },
            {
                'name': 'privilege_escalation',
                'description': 'User accessing admin resources',
                'conditions': {
                    'event_type': AuditEventType.AUTHORIZATION,
                    'resource_contains': '/admin',
                    'allowed': False,
                    'count_threshold': 1,
                    'time_window': 3600  # 1 hour
                },
                'severity': AlertSeverity.WARNING
            },
            {
                'name': 'data_exfiltration',
                'description': 'Unusual data access patterns',
                'conditions': {
                    'event_type': AuditEventType.DATA_ACCESS,
                    'record_count_threshold': 1000,
                    'time_window': 300  # 5 minutes
                },
                'severity': AlertSeverity.CRITICAL
            },
            {
                'name': 'suspicious_user_activity',
                'description': 'Activity from unusual location/time',
                'conditions': {
                    'unusual_hours': True,  # Outside business hours
                    'count_threshold': 10,
                    'time_window': 3600  # 1 hour
                },
                'severity': AlertSeverity.WARNING
            }
        ]
    
    def check(self, events: List[AuditEvent]) -> List[Alert]:
        """Check for pattern matches"""
        alerts = []
        
        for pattern in self.patterns:
            pattern_alerts = self._check_pattern(events, pattern)
            alerts.extend(pattern_alerts)
        
        return alerts
    
    def _check_pattern(self, events: List[AuditEvent], pattern: Dict[str, Any]) -> List[Alert]:
        """Check specific pattern"""
        conditions = pattern['conditions']
        time_window = conditions.get('time_window', 300)
        count_threshold = conditions.get('count_threshold', 1)
        
        # Filter events by time window
        window_start = datetime.now() - timedelta(seconds=time_window)
        recent_events = [e for e in events if e.timestamp >= window_start]
        
        # Apply pattern-specific filters
        filtered_events = self._apply_filters(recent_events, conditions)
        
        # Check if threshold is exceeded
        if len(filtered_events) >= count_threshold:
            # Group by IP or user if required
            if conditions.get('same_ip'):
                ip_groups = defaultdict(list)
                for event in filtered_events:
                    ip_groups[event.ip_address].append(event)
                
                for ip, ip_events in ip_groups.items():
                    if len(ip_events) >= count_threshold:
                        alert = self._create_alert(
                            severity=pattern['severity'],
                            title=f"Pattern Detected: {pattern['name']}",
                            description=pattern['description'],
                            event_data={
                                'pattern': pattern['name'],
                                'ip_address': ip,
                                'event_count': len(ip_events),
                                'time_window': time_window,
                                'sample_events': [e.event_id for e in ip_events[:5]]
                            }
                        )
                        return [alert]
            else:
                alert = self._create_alert(
                    severity=pattern['severity'],
                    title=f"Pattern Detected: {pattern['name']}",
                    description=pattern['description'],
                    event_data={
                        'pattern': pattern['name'],
                        'event_count': len(filtered_events),
                        'time_window': time_window,
                        'sample_events': [e.event_id for e in filtered_events[:5]]
                    }
                )
                return [alert]
        
        return []
    
    def _apply_filters(self, events: List[AuditEvent], conditions: Dict[str, Any]) -> List[AuditEvent]:
        """Apply conditions to filter events"""
        filtered = events
        
        # Filter by event type
        if 'event_type' in conditions:
            filtered = [e for e in filtered if e.event_type == conditions['event_type']]
        
        # Filter by status code range
        if 'status_code_range' in conditions:
            min_code, max_code = conditions['status_code_range']
            filtered = [e for e in filtered if e.status_code and min_code <= e.status_code <= max_code]
        
        # Filter by specific status code
        if 'status_code' in conditions:
            filtered = [e for e in filtered if e.status_code == conditions['status_code']]
        
        # Filter by authorization result
        if 'allowed' in conditions:
            filtered = [e for e in filtered if e.details.get('allowed') == conditions['allowed']]
        
        # Filter by resource
        if 'resource_contains' in conditions:
            resource = conditions['resource_contains']
            filtered = [e for e in filtered if e.resource and resource in e.resource]
        
        # Filter by record count
        if 'record_count_threshold' in conditions:
            threshold = conditions['record_count_threshold']
            filtered = [e for e in filtered if e.details.get('record_count', 0) >= threshold]
        
        # Filter by unusual hours (outside 9-5 weekdays)
        if conditions.get('unusual_hours'):
            filtered = [e for e in filtered if 
                       e.timestamp.hour < 9 or e.timestamp.hour > 17 or 
                       e.timestamp.weekday() >= 6]
        
        return filtered


class ComplianceMonitor(AuditMonitor):
    """Compliance monitor"""
    
    def check(self, events: List[AuditEvent]) -> List[Alert]:
        """Check compliance-related alerts"""
        alerts = []
        
        # Check for compliance violations
        compliance_summary = compliance_checker.get_compliance_summary()
        
        # Alert on critical violations
        if compliance_summary['critical_violations'] > 0:
            alert = self._create_alert(
                severity=AlertSeverity.CRITICAL,
                title="Critical Compliance Violations",
                description=f"{compliance_summary['critical_violations']} critical compliance violations detected",
                event_data={
                    'critical_violations': compliance_summary['critical_violations'],
                    'high_violations': compliance_summary['high_risk_violations'],
                    'overall_score': compliance_summary['overall_score'],
                    'framework_status': compliance_summary['framework_status']
                }
            )
            alerts.append(alert)
        
        # Alert on low compliance score
        if compliance_summary['overall_score'] < 80:
            alert = self._create_alert(
                severity=AlertSeverity.ERROR,
                title="Low Compliance Score",
                description=f"Overall compliance score ({compliance_summary['overall_score']:.1f}%) below threshold",
                event_data={
                    'overall_score': compliance_summary['overall_score'],
                    'framework_status': compliance_summary['framework_status']
                }
            )
            alerts.append(alert)
        
        return alerts


class AuditMonitoringSystem:
    """Main audit monitoring system"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.monitors: Dict[str, AuditMonitor] = {}
        self.alerts: deque = deque(maxlen=10000)
        self.metrics: deque = deque(maxlen=1440)  # 24 hours of minute data
        self.event_buffer: deque = deque(maxlen=10000)
        self.monitoring_active = False
        self.monitor_thread = None
        self.redis_client = None
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize monitoring system with Flask app"""
        self.app = app
        
        # Initialize Redis for distributed monitoring
        try:
            redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            self.logger.info("Redis connection established for monitoring")
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {str(e)}")
        
        # Initialize monitors
        self._initialize_monitors()
        
        # Add default alert callbacks
        self.add_alert_callback(self._log_alert)
        self.add_alert_callback(self._store_alert)
        
        self.logger.info("Audit monitoring system initialized")
    
    def _initialize_monitors(self):
        """Initialize default monitors"""
        # Threshold monitors
        threshold_configs = [
            MonitorConfig(
                monitor_id="error_rate_threshold",
                name="Error Rate Monitor",
                type=MonitorType.THRESHOLD,
                enabled=True,
                check_interval=60,
                threshold_value=0.05,  # 5% error rate
                window_size=300,  # 5 minutes
                alert_severity=AlertSeverity.WARNING,
                description="Monitor error rate threshold"
            ),
            MonitorConfig(
                monitor_id="failed_auth_threshold",
                name="Failed Authentication Monitor",
                type=MonitorType.THRESHOLD,
                enabled=True,
                check_interval=60,
                threshold_value=0.10,  # 10% failed auth rate
                window_size=300,  # 5 minutes
                alert_severity=AlertSeverity.ERROR,
                description="Monitor failed authentication threshold"
            ),
            MonitorConfig(
                monitor_id="high_severity_threshold",
                name="High Severity Events Monitor",
                type=MonitorType.THRESHOLD,
                enabled=True,
                check_interval=60,
                threshold_value=5,  # 5 high severity events
                window_size=300,  # 5 minutes
                alert_severity=AlertSeverity.WARNING,
                description="Monitor high severity events threshold"
            ),
            MonitorConfig(
                monitor_id="request_volume_threshold",
                name="Request Volume Monitor",
                type=MonitorType.THRESHOLD,
                enabled=True,
                check_interval=60,
                threshold_value=1000,  # 1000 requests
                window_size=300,  # 5 minutes
                alert_severity=AlertSeverity.INFO,
                description="Monitor request volume threshold"
            )
        ]
        
        for config in threshold_configs:
            monitor = ThresholdMonitor(config)
            monitor.add_alert_callback(self._on_monitor_alert)
            self.monitors[config.monitor_id] = monitor
        
        # Anomaly monitor
        anomaly_config = MonitorConfig(
            monitor_id="anomaly_detector",
            name="Anomaly Detection Monitor",
            type=MonitorType.ANOMALY,
            enabled=True,
            check_interval=120,
            alert_severity=AlertSeverity.WARNING,
            description="Detect anomalous activity patterns"
        )
        anomaly_monitor = AnomalyMonitor(anomaly_config)
        anomaly_monitor.add_alert_callback(self._on_monitor_alert)
        self.monitors[anomaly_config.monitor_id] = anomaly_monitor
        
        # Pattern monitor
        pattern_config = MonitorConfig(
            monitor_id="pattern_detector",
            name="Pattern Detection Monitor",
            type=MonitorType.PATTERN,
            enabled=True,
            check_interval=60,
            alert_severity=AlertSeverity.WARNING,
            description="Detect specific activity patterns"
        )
        pattern_monitor = PatternMonitor(pattern_config)
        pattern_monitor.add_alert_callback(self._on_monitor_alert)
        self.monitors[pattern_config.monitor_id] = pattern_monitor
        
        # Compliance monitor
        compliance_config = MonitorConfig(
            monitor_id="compliance_monitor",
            name="Compliance Monitor",
            type=MonitorType.COMPLIANCE,
            enabled=True,
            check_interval=300,  # 5 minutes
            alert_severity=AlertSeverity.ERROR,
            description="Monitor compliance status"
        )
        compliance_monitor = ComplianceMonitor(compliance_config)
        compliance_monitor.add_alert_callback(self._on_monitor_alert)
        self.monitors[compliance_config.monitor_id] = compliance_monitor
    
    def start_monitoring(self):
        """Start monitoring in background thread"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Audit monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("Audit monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Get recent events
                recent_events = self._get_recent_events()
                
                # Update metrics
                self._update_metrics(recent_events)
                
                # Run monitors
                self._run_monitors(recent_events)
                
                # Sleep until next check
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {str(e)}")
                time.sleep(30)
    
    def _get_recent_events(self) -> List[AuditEvent]:
        """Get recent audit events"""
        # Get events from buffer
        events = list(self.event_buffer)
        
        # Also get events from audit logger if needed
        if len(events) < 100:
            query = {
                'start_date': datetime.now() - timedelta(minutes=30),
                'end_date': datetime.now(),
                'limit': 1000
            }
            logger_events = audit_logger.query_events(query)
            events.extend(logger_events)
        
        # Sort by timestamp
        events.sort(key=lambda x: x.timestamp, reverse=True)
        
        return events[:1000]  # Limit to last 1000 events
    
    def _update_metrics(self, events: List[AuditEvent]):
        """Update monitoring metrics"""
        if not events:
            return
        
        # Calculate metrics
        total_events = len(events)
        events_by_type = defaultdict(int)
        events_by_severity = defaultdict(int)
        unique_users = set()
        unique_ips = set()
        error_count = 0
        response_times = []
        
        for event in events:
            events_by_type[event.event_type.value] += 1
            events_by_severity[event.severity.value] += 1
            
            if event.user_id:
                unique_users.add(event.user_id)
            unique_ips.add(event.ip_address)
            
            if event.status_code and event.status_code >= 400:
                error_count += 1
            
            if 'duration_ms' in event.details:
                response_times.append(event.details['duration_ms'] / 1000.0)
        
        error_rate = error_count / total_events if total_events > 0 else 0
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        # Calculate anomaly score (simplified)
        anomaly_score = len([e for e in events if e.event_type == AuditEventType.SECURITY_EVENT]) / total_events
        
        # Get compliance score
        compliance_summary = compliance_checker.get_compliance_summary()
        compliance_score = compliance_summary['overall_score'] / 100.0
        
        # Create metrics object
        metrics = MonitoringMetrics(
            timestamp=datetime.now(),
            total_events=total_events,
            events_by_type=dict(events_by_type),
            events_by_severity=dict(events_by_severity),
            unique_users=len(unique_users),
            unique_ips=len(unique_ips),
            error_rate=error_rate,
            avg_response_time=avg_response_time,
            anomaly_score=anomaly_score,
            compliance_score=compliance_score
        )
        
        self.metrics.append(metrics)
        
        # Store metrics in Redis
        if self.redis_client:
            metrics_key = f"audit_monitoring:metrics:{int(metrics.timestamp.timestamp())}"
            self.redis_client.setex(metrics_key, 86400, json.dumps(asdict(metrics)))
    
    def _run_monitors(self, events: List[AuditEvent]):
        """Run all enabled monitors"""
        for monitor_id, monitor in self.monitors.items():
            if not monitor.config.enabled:
                continue
            
            try:
                # Check if enough time has passed since last check
                if (datetime.now() - monitor.last_check).total_seconds() < monitor.config.check_interval:
                    continue
                
                # Run monitor
                alerts = monitor.check(events)
                
                # Update last check time
                monitor.last_check = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Monitor {monitor_id} failed: {str(e)}")
    
    def _on_monitor_alert(self, alert: Alert):
        """Handle alert from monitor"""
        self.alerts.append(alert)
        
        # Trigger global alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {str(e)}")
    
    def _log_alert(self, alert: Alert):
        """Log alert"""
        log_message = f"[{alert.severity.value.upper()}] {alert.title}: {alert.description}"
        
        if alert.severity == AlertSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif alert.severity == AlertSeverity.ERROR:
            self.logger.error(log_message)
        elif alert.severity == AlertSeverity.WARNING:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def _store_alert(self, alert: Alert):
        """Store alert in Redis"""
        if self.redis_client:
            alert_key = f"audit_monitoring:alerts:{alert.alert_id}"
            self.redis_client.setex(alert_key, 604800, json.dumps(alert.to_dict()))  # 7 days TTL
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Add global alert callback"""
        self.alert_callbacks.append(callback)
    
    def add_event(self, event: AuditEvent):
        """Add event to monitoring buffer"""
        self.event_buffer.append(event)
    
    def get_alerts(self, severity: AlertSeverity = None, 
                  monitor_type: MonitorType = None,
                  acknowledged: bool = None,
                  limit: int = 100) -> List[Alert]:
        """Get alerts with filters"""
        alerts = list(self.alerts)
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if monitor_type:
            alerts = [a for a in alerts if a.monitor_type == monitor_type]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return alerts[:limit]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = None) -> bool:
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now()
                
                # Update in Redis
                if self.redis_client:
                    alert_key = f"audit_monitoring:alerts:{alert_id}"
                    self.redis_client.setex(alert_key, 604800, json.dumps(alert.to_dict()))
                
                self.logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                return True
        
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                
                # Update in Redis
                if self.redis_client:
                    alert_key = f"audit_monitoring:alerts:{alert_id}"
                    self.redis_client.setex(alert_key, 604800, json.dumps(alert.to_dict()))
                
                self.logger.info(f"Alert {alert_id} resolved")
                return True
        
        return False
    
    def get_metrics(self, hours: int = 24) -> List[MonitoringMetrics]:
        """Get monitoring metrics"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        metrics = [m for m in self.metrics if m.timestamp >= cutoff_time]
        metrics.sort(key=lambda x: x.timestamp, reverse=True)
        
        return metrics
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring system status"""
        return {
            'monitoring_active': self.monitoring_active,
            'monitors': {
                monitor_id: {
                    'name': monitor.config.name,
                    'type': monitor.config.type.value,
                    'enabled': monitor.config.enabled,
                    'last_check': monitor.last_check.isoformat(),
                    'check_interval': monitor.config.check_interval
                }
                for monitor_id, monitor in self.monitors.items()
            },
            'alerts': {
                'total': len(self.alerts),
                'unacknowledged': len([a for a in self.alerts if not a.acknowledged]),
                'by_severity': {
                    severity.value: len([a for a in self.alerts if a.severity == severity])
                    for severity in AlertSeverity
                }
            },
            'metrics': {
                'events_in_buffer': len(self.event_buffer),
                'metrics_points': len(self.metrics)
            }
        }


# Initialize global audit monitoring system
audit_monitoring = AuditMonitoringSystem()
