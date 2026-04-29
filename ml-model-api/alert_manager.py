"""
Advanced Alert Manager for FlavorSnap
Intelligent alerting with machine learning-based anomaly detection
"""

import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading
import queue
import time
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
import joblib
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AlertPolicy:
    """Alert policy configuration"""
    name: str
    description: str
    conditions: List[Dict[str, Any]]
    severity: str
    notification_channels: List[str]
    cooldown_period: int = 300  # 5 minutes
    escalation_rules: List[Dict[str, Any]] = field(default_factory=list)
    auto_resolve: bool = True
    tags: List[str] = field(default_factory=list)


@dataclass
class AlertIncident:
    """Alert incident record"""
    id: str
    policy_name: str
    severity: str
    title: str
    description: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    status: str = "active"  # active, acknowledged, resolved, suppressed
    assignee: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    actions_taken: List[str] = field(default_factory=list)
    escalation_level: int = 0


class AnomalyDetector:
    """ML-based anomaly detection for metrics"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.models = {}
        self.scalers = {}
        self.training_data = defaultdict(lambda: deque(maxlen=1000))
        self.is_trained = False
        self.model_path = Path(config.get('model_path', 'models/anomaly_detectors'))
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize models for different metrics
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize anomaly detection models"""
        metrics = ['cpu_usage', 'memory_usage', 'disk_usage', 'response_time', 'error_rate']
        
        for metric in metrics:
            self.models[metric] = IsolationForest(
                contamination=0.1,  # Expected anomaly rate
                random_state=42,
                n_estimators=100
            )
            self.scalers[metric] = StandardScaler()
    
    def add_training_data(self, metric_name: str, value: float, timestamp: datetime):
        """Add training data point"""
        self.training_data[metric_name].append({
            'timestamp': timestamp,
            'value': value
        })
    
    def train_models(self):
        """Train anomaly detection models"""
        for metric_name, data_points in self.training_data.items():
            if len(data_points) < 100:  # Need minimum data for training
                continue
            
            try:
                # Prepare training data
                values = np.array([dp['value'] for dp in data_points]).reshape(-1, 1)
                
                # Scale data
                scaled_values = self.scalers[metric_name].fit_transform(values)
                
                # Train model
                self.models[metric_name].fit(scaled_values)
                
                # Save model
                model_file = self.model_path / f"{metric_name}_anomaly_model.pkl"
                scaler_file = self.model_path / f"{metric_name}_scaler.pkl"
                
                joblib.dump(self.models[metric_name], model_file)
                joblib.dump(self.scalers[metric_name], scaler_file)
                
                logger.info(f"Trained anomaly detection model for {metric_name}")
                
            except Exception as e:
                logger.error(f"Error training model for {metric_name}: {e}")
        
        self.is_trained = True
    
    def load_models(self):
        """Load pre-trained models"""
        for metric_name in self.models.keys():
            try:
                model_file = self.model_path / f"{metric_name}_anomaly_model.pkl"
                scaler_file = self.model_path / f"{metric_name}_scaler.pkl"
                
                if model_file.exists() and scaler_file.exists():
                    self.models[metric_name] = joblib.load(model_file)
                    self.scalers[metric_name] = joblib.load(scaler_file)
                    logger.info(f"Loaded anomaly detection model for {metric_name}")
                    
            except Exception as e:
                logger.error(f"Error loading model for {metric_name}: {e}")
        
        self.is_trained = any(
            hasattr(model, 'decision_function') 
            for model in self.models.values()
        )
    
    def detect_anomaly(self, metric_name: str, value: float) -> Tuple[bool, float]:
        """Detect if value is anomalous"""
        if not self.is_trained or metric_name not in self.models:
            return False, 0.0
        
        try:
            # Scale the value
            scaled_value = self.scalers[metric_name].transform([[value]])
            
            # Get anomaly score
            anomaly_score = self.models[metric_name].decision_function(scaled_value)[0]
            is_anomaly = self.models[metric_name].predict(scaled_value)[0] == -1
            
            return is_anomaly, float(anomaly_score)
            
        except Exception as e:
            logger.error(f"Error detecting anomaly for {metric_name}: {e}")
            return False, 0.0
    
    def get_anomaly_summary(self, metric_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get anomaly detection summary"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_data = [
            dp for dp in self.training_data[metric_name]
            if dp['timestamp'] >= cutoff_time
        ]
        
        if not recent_data:
            return {'total_points': 0}
        
        anomalies_detected = 0
        total_anomaly_score = 0.0
        
        for data_point in recent_data:
            is_anomaly, score = self.detect_anomaly(metric_name, data_point['value'])
            if is_anomaly:
                anomalies_detected += 1
                total_anomaly_score += abs(score)
        
        return {
            'total_points': len(recent_data),
            'anomalies_detected': anomalies_detected,
            'anomaly_rate': anomalies_detected / len(recent_data) if recent_data else 0,
            'average_anomaly_score': total_anomaly_score / anomalies_detected if anomalies_detected > 0 else 0
        }


class AlertRouting:
    """Intelligent alert routing and escalation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.routing_rules = config.get('routing_rules', [])
        self.escalation_policies = config.get('escalation_policies', {})
        self.on_call_schedule = config.get('on_call_schedule', {})
        
    def route_alert(self, incident: AlertIncident) -> List[str]:
        """Determine who should receive the alert"""
        recipients = []
        
        # Apply routing rules
        for rule in self.routing_rules:
            if self._match_rule(incident, rule):
                recipients.extend(rule.get('recipients', []))
        
        # Apply on-call schedule
        on_call = self._get_on_call_person()
        if on_call and incident.severity in ['CRITICAL', 'HIGH']:
            recipients.append(on_call)
        
        return list(set(recipients))  # Remove duplicates
    
    def _match_rule(self, incident: AlertIncident, rule: Dict[str, Any]) -> bool:
        """Check if incident matches routing rule"""
        conditions = rule.get('conditions', {})
        
        # Check severity
        if 'severity' in conditions:
            if incident.severity not in conditions['severity']:
                return False
        
        # Check policy name
        if 'policy_name' in conditions:
            if incident.policy_name not in conditions['policy_name']:
                return False
        
        # Check labels
        if 'labels' in conditions:
            for key, value in conditions['labels'].items():
                if incident.labels.get(key) != value:
                    return False
        
        # Check time-based conditions
        if 'time_window' in conditions:
            current_hour = datetime.now().hour
            time_window = conditions['time_window']
            if 'start' in time_window and 'end' in time_window:
                if not (time_window['start'] <= current_hour <= time_window['end']):
                    return False
        
        return True
    
    def _get_on_call_person(self) -> Optional[str]:
        """Get current on-call person"""
        # Simplified on-call logic
        # In real implementation, would use calendar integration or rotation system
        return self.on_call_schedule.get('primary')
    
    def should_escalate(self, incident: AlertIncident) -> bool:
        """Determine if alert should be escalated"""
        if incident.escalation_level >= 3:  # Max escalation level
            return False
        
        # Check escalation policies
        policy = self.escalation_policies.get(incident.severity.lower(), {})
        
        # Check time-based escalation
        if 'escalate_after_minutes' in policy:
            time_elapsed = (datetime.now() - incident.created_at).total_seconds() / 60
            if time_elapsed > policy['escalate_after_minutes']:
                return True
        
        # Check acknowledgment status
        if 'escalate_unacknowledged' in policy:
            if policy['escalate_unacknowledged'] and incident.status != 'acknowledged':
                return True
        
        return False
    
    def escalate_alert(self, incident: AlertIncident) -> AlertIncident:
        """Escalate alert to next level"""
        incident.escalation_level += 1
        
        # Add escalation action
        escalation_action = f"Escalated to level {incident.escalation_level}"
        incident.actions_taken.append(escalation_action)
        
        logger.info(f"Escalated alert {incident.id} to level {incident.escalation_level}")
        return incident


class IntelligentAlertManager:
    """Advanced alert management with ML and intelligent routing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.anomaly_detector = AnomalyDetector(config.get('anomaly_detection', {}))
        self.alert_routing = AlertRouting(config.get('routing', {}))
        
        self.policies = {}
        self.incidents = {}
        self.incident_history = deque(maxlen=10000)
        self.suppression_rules = {}
        
        # Background processing
        self.processing_queue = queue.Queue()
        self.processing_thread = None
        self.stop_event = threading.Event()
        
        # Load existing models
        self.anomaly_detector.load_models()
        
        # Setup default policies
        self._setup_default_policies()
        
        # Start processing
        self.start_processing()
    
    def _setup_default_policies(self):
        """Setup default alert policies"""
        default_policies = [
            AlertPolicy(
                name="system_performance_critical",
                description="Critical system performance issues",
                conditions=[
                    {"metric": "cpu_usage", "operator": "gt", "value": 95},
                    {"metric": "memory_usage", "operator": "gt", "value": 95}
                ],
                severity="CRITICAL",
                notification_channels=["email", "slack", "pagerduty"],
                escalation_rules=[
                    {"delay_minutes": 15, "action": "escalate_to_manager"},
                    {"delay_minutes": 30, "action": "escalate_to_director"}
                ]
            ),
            AlertPolicy(
                name="system_performance_high",
                description="High system performance issues",
                conditions=[
                    {"metric": "cpu_usage", "operator": "gt", "value": 85},
                    {"metric": "memory_usage", "operator": "gt", "value": 85}
                ],
                severity="HIGH",
                notification_channels=["email", "slack"],
                escalation_rules=[
                    {"delay_minutes": 30, "action": "escalate_to_manager"}
                ]
            ),
            AlertPolicy(
                name="anomaly_detection",
                description="Anomalous behavior detected",
                conditions=[
                    {"type": "anomaly", "confidence": "gt", "value": 0.8}
                ],
                severity="MEDIUM",
                notification_channels=["slack"],
                auto_resolve=True
            ),
            AlertPolicy(
                name="model_performance_degradation",
                description="ML model performance degradation",
                conditions=[
                    {"metric": "model_accuracy", "operator": "lt", "value": 0.85},
                    {"metric": "prediction_latency", "operator": "gt", "value": 1000}
                ],
                severity="HIGH",
                notification_channels=["email", "slack"]
            )
        ]
        
        for policy in default_policies:
            self.add_policy(policy)
    
    def start_processing(self):
        """Start background alert processing"""
        if self.processing_thread and self.processing_thread.is_alive():
            return
        
        self.stop_event.clear()
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        logger.info("Started intelligent alert processing")
    
    def stop_processing(self):
        """Stop background alert processing"""
        self.stop_event.set()
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        logger.info("Stopped intelligent alert processing")
    
    def _processing_loop(self):
        """Main alert processing loop"""
        while not self.stop_event.is_set():
            try:
                # Process alert from queue
                try:
                    alert_data = self.processing_queue.get(timeout=1)
                    self._process_alert(alert_data)
                    self.processing_queue.task_done()
                except queue.Empty:
                    continue
                    
            except Exception as e:
                logger.error(f"Error in alert processing: {e}")
                time.sleep(1)
    
    def _process_alert(self, alert_data: Dict[str, Any]):
        """Process incoming alert data"""
        try:
            # Check for anomalies
            if alert_data.get('type') == 'metric':
                metric_name = alert_data.get('metric_name')
                metric_value = alert_data.get('value')
                
                if metric_name and metric_value is not None:
                    # Add to training data
                    self.anomaly_detector.add_training_data(
                        metric_name, metric_value, datetime.now()
                    )
                    
                    # Check for anomalies
                    is_anomaly, anomaly_score = self.anomaly_detector.detect_anomaly(
                        metric_name, metric_value
                    )
                    
                    if is_anomaly:
                        self._create_anomaly_alert(metric_name, metric_value, anomaly_score)
            
            # Check policy conditions
            for policy_name, policy in self.policies.items():
                if self._evaluate_policy_conditions(policy, alert_data):
                    self._create_policy_alert(policy, alert_data)
                    
        except Exception as e:
            logger.error(f"Error processing alert: {e}")
    
    def _evaluate_policy_conditions(self, policy: AlertPolicy, alert_data: Dict[str, Any]) -> bool:
        """Evaluate if alert data matches policy conditions"""
        for condition in policy.conditions:
            condition_type = condition.get('type', 'metric')
            
            if condition_type == 'metric':
                metric_name = condition.get('metric')
                operator = condition.get('operator')
                threshold = condition.get('value')
                
                if metric_name not in alert_data:
                    return False
                
                metric_value = alert_data.get(metric_name)
                if not self._evaluate_condition(metric_value, operator, threshold):
                    return False
            
            elif condition_type == 'anomaly':
                confidence = condition.get('confidence', 0.8)
                operator = condition.get('operator', 'gt')
                threshold = condition.get('value', confidence)
                
                anomaly_score = alert_data.get('anomaly_score', 0)
                if not self._evaluate_condition(anomaly_score, operator, threshold):
                    return False
        
        return True
    
    def _evaluate_condition(self, value: float, operator: str, threshold: float) -> bool:
        """Evaluate condition operator"""
        if operator == 'gt':
            return value > threshold
        elif operator == 'gte':
            return value >= threshold
        elif operator == 'lt':
            return value < threshold
        elif operator == 'lte':
            return value <= threshold
        elif operator == 'eq':
            return value == threshold
        elif operator == 'ne':
            return value != threshold
        return False
    
    def _create_anomaly_alert(self, metric_name: str, value: float, anomaly_score: float):
        """Create anomaly-based alert"""
        incident_id = f"anomaly_{metric_name}_{int(time.time())}"
        
        incident = AlertIncident(
            id=incident_id,
            policy_name="anomaly_detection",
            severity="MEDIUM",
            title=f"Anomaly detected in {metric_name}",
            description=f"Anomalous value {value} detected for {metric_name} (anomaly score: {anomaly_score:.3f})",
            created_at=datetime.now(),
            labels={
                'metric_name': metric_name,
                'anomaly_score': str(anomaly_score),
                'detection_type': 'ml_anomaly'
            },
            metrics={'value': value, 'anomaly_score': anomaly_score}
        )
        
        self._add_incident(incident)
    
    def _create_policy_alert(self, policy: AlertPolicy, alert_data: Dict[str, Any]):
        """Create policy-based alert"""
        incident_id = f"policy_{policy.name}_{int(time.time())}"
        
        incident = AlertIncident(
            id=incident_id,
            policy_name=policy.name,
            severity=policy.severity,
            title=f"Alert: {policy.name}",
            description=policy.description,
            created_at=datetime.now(),
            labels=policy.tags.copy(),
            metrics=alert_data
        )
        
        self._add_incident(incident)
    
    def _add_incident(self, incident: AlertIncident):
        """Add incident and trigger notifications"""
        self.incidents[incident.id] = incident
        self.incident_history.append(incident)
        
        # Route alert
        recipients = self.alert_routing.route_alert(incident)
        
        # Send notifications (would integrate with notification system)
        logger.warning(f"Alert created: {incident.title} - Recipients: {recipients}")
    
    def add_policy(self, policy: AlertPolicy):
        """Add alert policy"""
        self.policies[policy.name] = policy
        logger.info(f"Added alert policy: {policy.name}")
    
    def remove_policy(self, policy_name: str):
        """Remove alert policy"""
        if policy_name in self.policies:
            del self.policies[policy_name]
            logger.info(f"Removed alert policy: {policy_name}")
    
    def acknowledge_alert(self, incident_id: str, user: str) -> bool:
        """Acknowledge alert"""
        if incident_id in self.incidents:
            incident = self.incidents[incident_id]
            incident.status = "acknowledged"
            incident.assignee = user
            incident.actions_taken.append(f"Acknowledged by {user}")
            
            logger.info(f"Alert {incident_id} acknowledged by {user}")
            return True
        return False
    
    def resolve_alert(self, incident_id: str, user: str, resolution_note: str = "") -> bool:
        """Resolve alert"""
        if incident_id in self.incidents:
            incident = self.incidents[incident_id]
            incident.status = "resolved"
            incident.resolved_at = datetime.now()
            incident.assignee = user
            incident.actions_taken.append(f"Resolved by {user}: {resolution_note}")
            
            logger.info(f"Alert {incident_id} resolved by {user}")
            return True
        return False
    
    def escalate_alert(self, incident_id: str) -> bool:
        """Escalate alert"""
        if incident_id in self.incidents:
            incident = self.incidents[incident_id]
            if self.alert_routing.should_escalate(incident):
                self.alert_routing.escalate_alert(incident)
                return True
        return False
    
    def process_metric_data(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Process metric data for alerting"""
        alert_data = {
            'type': 'metric',
            'metric_name': metric_name,
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'labels': labels or {}
        }
        
        self.processing_queue.put(alert_data)
    
    def get_active_incidents(self) -> List[AlertIncident]:
        """Get all active incidents"""
        return [inc for inc in self.incidents.values() if inc.status == 'active']
    
    def get_incident_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get incident statistics"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_incidents = [
            inc for inc in self.incident_history
            if inc.created_at >= cutoff_time
        ]
        
        stats = {
            'total_incidents': len(recent_incidents),
            'by_severity': defaultdict(int),
            'by_policy': defaultdict(int),
            'by_status': defaultdict(int),
            'average_resolution_time': 0,
            'escalation_rate': 0
        }
        
        resolution_times = []
        escalated_count = 0
        
        for incident in recent_incidents:
            stats['by_severity'][incident.severity] += 1
            stats['by_policy'][incident.policy_name] += 1
            stats['by_status'][incident.status] += 1
            
            if incident.resolved_at:
                resolution_time = (incident.resolved_at - incident.created_at).total_seconds()
                resolution_times.append(resolution_time)
            
            if incident.escalation_level > 0:
                escalated_count += 1
        
        if resolution_times:
            stats['average_resolution_time'] = sum(resolution_times) / len(resolution_times)
        
        if recent_incidents:
            stats['escalation_rate'] = escalated_count / len(recent_incidents)
        
        return dict(stats)
    
    def train_anomaly_models(self):
        """Train anomaly detection models"""
        self.anomaly_detector.train_models()
    
    def get_anomaly_summary(self, metric_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get anomaly detection summary"""
        return self.anomaly_detector.get_anomaly_summary(metric_name, hours)


# Global intelligent alert manager
intelligent_alert_manager = None


def initialize_intelligent_alerting(config: Dict[str, Any]) -> IntelligentAlertManager:
    """Initialize global intelligent alert manager"""
    global intelligent_alert_manager
    intelligent_alert_manager = IntelligentAlertManager(config)
    return intelligent_alert_manager


def get_intelligent_alert_manager() -> Optional[IntelligentAlertManager]:
    """Get global intelligent alert manager instance"""
    return intelligent_alert_manager
