"""
Model Performance Monitoring and Anomaly Visualization
"""
import time
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path

# ML and statistical libraries
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

try:
    from anomaly_detection import anomaly_system, Anomaly, AnomalyType, Severity
    from monitoring import data_quality_monitor
    from security_config import threat_detector
except Exception as e:
    logging.warning(f"Could not import monitoring modules: {e}")
    anomaly_system = None
    data_quality_monitor = None
    threat_detector = None

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Alert:
    """Represents a system alert"""
    id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    source: str
    metadata: Dict[str, Any]
    acknowledged: bool = False
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['level'] = self.level.value
        return data

class RealTimeAlertSystem:
    """Real-time alert system for anomalies and threats"""
    
    def __init__(self):
        self.alerts = deque(maxlen=1000)
        self.alert_handlers = []
        self.alert_rules = self._initialize_alert_rules()
        self.alert_history = defaultdict(list)
        self.suppression_rules = {}
        
    def _initialize_alert_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize default alert rules"""
        return {
            'performance_anomaly': {
                'enabled': True,
                'threshold': 0.7,
                'cooldown': 300,  # 5 minutes
                'escalation_threshold': 3
            },
            'security_threat': {
                'enabled': True,
                'threshold': 0.8,
                'cooldown': 60,  # 1 minute
                'escalation_threshold': 1
            },
            'data_quality': {
                'enabled': True,
                'threshold': 0.6,
                'cooldown': 600,  # 10 minutes
                'escalation_threshold': 5
            },
            'system_health': {
                'enabled': True,
                'threshold': 0.5,
                'cooldown': 1800,  # 30 minutes
                'escalation_threshold': 2
            }
        }
    
    def check_anomalies(self) -> List[Alert]:
        """Check for anomalies and generate alerts"""
        alerts = []
        
        try:
            if anomaly_system:
                # Get recent anomalies
                recent_anomalies = anomaly_system.get_anomalies(
                    time_range=timedelta(minutes=5)
                )
                
                for anomaly in recent_anomalies:
                    alert = self._create_anomaly_alert(anomaly)
                    if alert:
                        alerts.append(alert)
            
            if threat_detector:
                # Get security dashboard
                security_data = threat_detector.get_security_dashboard()
                if security_data['summary']['risk_score'] > 70:
                    alert = self._create_security_alert(security_data)
                    if alert:
                        alerts.append(alert)
            
            if data_quality_monitor:
                # Get data quality report
                quality_report = data_quality_monitor.get_quality_report()
                if quality_report.get('summary', {}).get('avg_quality_score', 100) < 70:
                    alert = self._create_quality_alert(quality_report)
                    if alert:
                        alerts.append(alert)
            
        except Exception as e:
            logger.error(f"Error checking anomalies: {e}")
        
        return alerts
    
    def _create_anomaly_alert(self, anomaly: Anomaly) -> Optional[Alert]:
        """Create alert from anomaly"""
        try:
            rule_key = f"{anomaly.type.value}_anomaly"
            if rule_key not in self.alert_rules:
                return None
            
            rule = self.alert_rules[rule_key]
            if not rule['enabled']:
                return None
            
            # Check cooldown
            if self._is_suppressed(anomaly.source, rule['cooldown']):
                return None
            
            # Determine alert level
            level = self._determine_alert_level(anomaly.severity)
            
            alert = Alert(
                id=f"anomaly_{anomaly.id}",
                level=level,
                title=f"{anomaly.type.value.title()} Anomaly Detected",
                message=anomaly.description,
                timestamp=anomaly.timestamp,
                source=anomaly.source,
                metadata={
                    'anomaly_id': anomaly.id,
                    'type': anomaly.type.value,
                    'severity': anomaly.severity.value,
                    'confidence': anomaly.confidence,
                    'metrics': anomaly.metrics
                }
            )
            
            # Add suppression
            self._add_suppression(anomaly.source, rule['cooldown'])
            
            return alert
            
        except Exception as e:
            logger.error(f"Error creating anomaly alert: {e}")
            return None
    
    def _create_security_alert(self, security_data: Dict[str, Any]) -> Optional[Alert]:
        """Create security alert"""
        try:
            rule = self.alert_rules['security_threat']
            if not rule['enabled']:
                return None
            
            if self._is_suppressed('security', rule['cooldown']):
                return None
            
            summary = security_data['summary']
            
            alert = Alert(
                id=f"security_{int(time.time())}",
                level=AlertLevel.CRITICAL if summary['risk_score'] > 80 else AlertLevel.ERROR,
                title="High Security Risk Detected",
                message=f"Security risk score: {summary['risk_score']} ({summary['risk_level']})",
                timestamp=datetime.now(),
                source="security_monitor",
                metadata={
                    'risk_score': summary['risk_score'],
                    'risk_level': summary['risk_level'],
                    'total_threats': summary['total_threats'],
                    'blocked_ips': summary['blocked_ips']
                }
            )
            
            self._add_suppression('security', rule['cooldown'])
            return alert
            
        except Exception as e:
            logger.error(f"Error creating security alert: {e}")
            return None
    
    def _create_quality_alert(self, quality_report: Dict[str, Any]) -> Optional[Alert]:
        """Create data quality alert"""
        try:
            rule = self.alert_rules['data_quality']
            if not rule['enabled']:
                return None
            
            if self._is_suppressed('data_quality', rule['cooldown']):
                return None
            
            summary = quality_report.get('summary', {})
            
            alert = Alert(
                id=f"quality_{int(time.time())}",
                level=AlertLevel.WARNING,
                title="Data Quality Degradation",
                message=f"Average quality score: {summary.get('avg_quality_score', 0):.1f}",
                timestamp=datetime.now(),
                source="data_quality_monitor",
                metadata={
                    'quality_score': summary.get('avg_quality_score', 0),
                    'total_records': summary.get('total_records', 0),
                    'issues': quality_report.get('issues', {})
                }
            )
            
            self._add_suppression('data_quality', rule['cooldown'])
            return alert
            
        except Exception as e:
            logger.error(f"Error creating quality alert: {e}")
            return None
    
    def _determine_alert_level(self, severity: Severity) -> AlertLevel:
        """Determine alert level from anomaly severity"""
        mapping = {
            Severity.LOW: AlertLevel.INFO,
            Severity.MEDIUM: AlertLevel.WARNING,
            Severity.HIGH: AlertLevel.ERROR,
            Severity.CRITICAL: AlertLevel.CRITICAL
        }
        return mapping.get(severity, AlertLevel.WARNING)
    
    def _is_suppressed(self, source: str, cooldown: int) -> bool:
        """Check if alert source is suppressed"""
        if source not in self.suppression_rules:
            return False
        
        suppression_time = self.suppression_rules[source]
        return datetime.now() < suppression_time
    
    def _add_suppression(self, source: str, cooldown: int):
        """Add suppression rule for source"""
        self.suppression_rules[source] = datetime.now() + timedelta(seconds=cooldown)
    
    def add_alert(self, alert: Alert):
        """Add alert to system"""
        self.alerts.append(alert)
        self.alert_history[alert.level.value].append(alert)
        
        # Trigger handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get active (unresolved) alerts"""
        return [alert for alert in self.alerts if not alert.resolved]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        total_alerts = len(self.alerts)
        active_alerts = len(self.get_active_alerts())
        
        level_counts = defaultdict(int)
        source_counts = defaultdict(int)
        
        for alert in self.alerts:
            level_counts[alert.level.value] += 1
            source_counts[alert.source] += 1
        
        return {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'resolved_alerts': total_alerts - active_alerts,
            'level_breakdown': dict(level_counts),
            'source_breakdown': dict(source_counts),
            'recent_alerts': [alert.to_dict() for alert in list(self.alerts)[-10:]]
        }
    
    def add_handler(self, handler):
        """Add alert handler"""
        self.alert_handlers.append(handler)

class AnomalyVisualizer:
    """Visualization system for anomalies and metrics"""
    
    def __init__(self, output_dir: str = "anomaly_charts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def create_anomaly_dashboard(self, anomalies: List[Anomaly]) -> str:
        """Create comprehensive anomaly dashboard"""
        if not anomalies:
            return self._create_no_data_chart("No anomalies detected")
        
        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Anomaly Detection Dashboard', fontsize=16, fontweight='bold')
        
        # 1. Anomaly types distribution
        self._plot_anomaly_types(axes[0, 0], anomalies)
        
        # 2. Anomaly timeline
        self._plot_anomaly_timeline(axes[0, 1], anomalies)
        
        # 3. Severity distribution
        self._plot_severity_distribution(axes[1, 0], anomalies)
        
        # 4. Confidence scores
        self._plot_confidence_scores(axes[1, 1], anomalies)
        
        plt.tight_layout()
        
        # Save chart
        chart_path = self.output_dir / f"anomaly_dashboard_{int(time.time())}.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(chart_path)
    
    def _plot_anomaly_types(self, ax, anomalies: List[Anomaly]):
        """Plot anomaly types distribution"""
        type_counts = defaultdict(int)
        for anomaly in anomalies:
            type_counts[anomaly.type.value] += 1
        
        if type_counts:
            ax.pie(type_counts.values(), labels=type_counts.keys(), autopct='%1.1f%%')
            ax.set_title('Anomaly Types Distribution')
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center')
            ax.set_title('Anomaly Types Distribution')
    
    def _plot_anomaly_timeline(self, ax, anomalies: List[Anomaly]):
        """Plot anomaly timeline"""
        if not anomalies:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center')
            ax.set_title('Anomaly Timeline')
            return
        
        # Group by hour
        hourly_counts = defaultdict(int)
        for anomaly in anomalies:
            hour = anomaly.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour] += 1
        
        if hourly_counts:
            hours = sorted(hourly_counts.keys())
            counts = [hourly_counts[hour] for hour in hours]
            
            ax.plot(hours, counts, marker='o', linewidth=2, markersize=6)
            ax.set_title('Anomalies Over Time')
            ax.set_xlabel('Time')
            ax.set_ylabel('Count')
            ax.tick_params(axis='x', rotation=45)
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center')
            ax.set_title('Anomaly Timeline')
    
    def _plot_severity_distribution(self, ax, anomalies: List[Anomaly]):
        """Plot severity distribution"""
        severity_counts = defaultdict(int)
        for anomaly in anomalies:
            severity_counts[anomaly.severity.value] += 1
        
        if severity_counts:
            bars = ax.bar(severity_counts.keys(), severity_counts.values())
            ax.set_title('Severity Distribution')
            ax.set_ylabel('Count')
            
            # Color bars by severity
            colors = {'low': 'green', 'medium': 'orange', 'high': 'red', 'critical': 'darkred'}
            for bar, severity in zip(bars, severity_counts.keys()):
                bar.set_color(colors.get(severity, 'blue'))
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center')
            ax.set_title('Severity Distribution')
    
    def _plot_confidence_scores(self, ax, anomalies: List[Anomaly]):
        """Plot confidence score distribution"""
        if not anomalies:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center')
            ax.set_title('Confidence Score Distribution')
            return
        
        confidences = [anomaly.confidence for anomaly in anomalies]
        
        ax.hist(confidences, bins=20, alpha=0.7, edgecolor='black')
        ax.set_title('Confidence Score Distribution')
        ax.set_xlabel('Confidence Score')
        ax.set_ylabel('Frequency')
        ax.axvline(np.mean(confidences), color='red', linestyle='--', 
                  label=f'Mean: {np.mean(confidences):.2f}')
        ax.legend()
    
    def _create_no_data_chart(self, message: str) -> str:
        """Create chart with no data message"""
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=16)
        ax.set_title('Anomaly Detection Dashboard')
        
        chart_path = self.output_dir / f"no_data_{int(time.time())}.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(chart_path)
    
    def create_system_health_chart(self, health_data: Dict[str, Any]) -> str:
        """Create system health visualization"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('System Health Dashboard', fontsize=16, fontweight='bold')
        
        # Health score gauge
        self._plot_health_gauge(axes[0, 0], health_data.get('health_score', 0))
        
        # Component status
        self._plot_component_status(axes[0, 1], health_data)
        
        # Recent activity
        self._plot_recent_activity(axes[1, 0], health_data)
        
        # Performance metrics
        self._plot_performance_metrics(axes[1, 1], health_data)
        
        plt.tight_layout()
        
        chart_path = self.output_dir / f"system_health_{int(time.time())}.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(chart_path)
    
    def _plot_health_gauge(self, ax, health_score: float):
        """Plot health score gauge"""
        # Create gauge-like visualization
        theta = np.linspace(0, np.pi, 100)
        r = 1
        
        # Background arc
        ax.fill_between(theta, 0, r, alpha=0.3, color='lightgray')
        
        # Health score arc
        health_theta = np.linspace(0, np.pi * (health_score / 100), 100)
        color = 'green' if health_score > 80 else 'orange' if health_score > 50 else 'red'
        ax.fill_between(health_theta, 0, r, alpha=0.7, color=color)
        
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-0.2, 1.2)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.text(0, 0.5, f'{health_score:.1f}%', ha='center', va='center', 
                fontsize=24, fontweight='bold')
        ax.set_title('System Health Score')
    
    def _plot_component_status(self, ax, health_data: Dict[str, Any]):
        """Plot component status"""
        components = ['Performance', 'Data Quality', 'Security', 'Model']
        status = [0.85, 0.92, 0.78, 0.88]  # Example status values
        
        bars = ax.bar(components, status)
        ax.set_title('Component Status')
        ax.set_ylabel('Health Score')
        ax.set_ylim(0, 1)
        
        # Color bars
        for bar, score in zip(bars, status):
            color = 'green' if score > 0.8 else 'orange' if score > 0.6 else 'red'
            bar.set_color(color)
        
        ax.tick_params(axis='x', rotation=45)
    
    def _plot_recent_activity(self, ax, health_data: Dict[str, Any]):
        """Plot recent activity"""
        # Generate sample data
        hours = pd.date_range(end=datetime.now(), periods=24, freq='H')
        activity = np.random.randint(10, 100, 24)
        
        ax.plot(hours, activity, marker='o', linewidth=2)
        ax.set_title('Recent Activity (24h)')
        ax.set_xlabel('Time')
        ax.set_ylabel('Activity Count')
        ax.tick_params(axis='x', rotation=45)
    
    def _plot_performance_metrics(self, ax, health_data: Dict[str, Any]):
        """Plot performance metrics"""
        metrics = ['Response Time', 'Throughput', 'Error Rate', 'Memory']
        values = [0.3, 0.85, 0.05, 0.67]  # Normalized values
        
        bars = ax.bar(metrics, values)
        ax.set_title('Performance Metrics')
        ax.set_ylabel('Normalized Value')
        ax.set_ylim(0, 1)
        
        # Color bars
        for bar, value in zip(bars, values):
            color = 'green' if value > 0.7 else 'orange' if value > 0.4 else 'red'
            bar.set_color(color)
        
        ax.tick_params(axis='x', rotation=45)

class RootCauseAnalyzer:
    """Root cause analysis for anomalies"""
    
    def __init__(self):
        self.correlation_threshold = 0.7
        self.causality_window = timedelta(minutes=30)
    
    def analyze_anomaly_causes(self, anomaly: Anomaly, 
                              context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze potential root causes of an anomaly"""
        causes = []
        
        try:
            # Analyze performance metrics
            if anomaly.type == AnomalyType.PERFORMANCE:
                perf_causes = self._analyze_performance_causes(anomaly, context_data)
                causes.extend(perf_causes)
            
            # Analyze data quality issues
            if anomaly.type == AnomalyType.DATA_QUALITY:
                data_causes = self._analyze_data_quality_causes(anomaly, context_data)
                causes.extend(data_causes)
            
            # Analyze security threats
            if anomaly.type == AnomalyType.SECURITY:
                security_causes = self._analyze_security_causes(anomaly, context_data)
                causes.extend(security_causes)
            
            # Analyze correlations
            correlations = self._find_correlations(anomaly, context_data)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(causes, correlations)
            
            return {
                'anomaly_id': anomaly.id,
                'analysis_timestamp': datetime.now().isoformat(),
                'potential_causes': causes,
                'correlations': correlations,
                'recommendations': recommendations,
                'confidence': self._calculate_analysis_confidence(causes, correlations)
            }
            
        except Exception as e:
            logger.error(f"Root cause analysis error: {e}")
            return {
                'anomaly_id': anomaly.id,
                'error': str(e),
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    def _analyze_performance_causes(self, anomaly: Anomaly, 
                                  context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze performance-related causes"""
        causes = []
        
        metrics = anomaly.metrics
        
        # High response time
        if 'response_time' in metrics and metrics['response_time'] > 2.0:
            causes.append({
                'type': 'performance',
                'factor': 'high_response_time',
                'description': 'Response time significantly elevated',
                'evidence': {'response_time': metrics['response_time']},
                'likelihood': 0.8
            })
        
        # High CPU usage
        if 'cpu_usage' in metrics and metrics['cpu_usage'] > 0.8:
            causes.append({
                'type': 'performance',
                'factor': 'high_cpu_usage',
                'description': 'CPU usage exceeding normal thresholds',
                'evidence': {'cpu_usage': metrics['cpu_usage']},
                'likelihood': 0.7
            })
        
        # Memory pressure
        if 'memory_usage' in metrics and metrics['memory_usage'] > 0.9:
            causes.append({
                'type': 'performance',
                'factor': 'memory_pressure',
                'description': 'Memory usage approaching capacity limits',
                'evidence': {'memory_usage': metrics['memory_usage']},
                'likelihood': 0.9
            })
        
        return causes
    
    def _analyze_data_quality_causes(self, anomaly: Anomaly, 
                                   context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze data quality-related causes"""
        causes = []
        
        metrics = anomaly.metrics
        
        # High missing data rate
        if 'missing_rate' in metrics and metrics['missing_rate'] > 0.1:
            causes.append({
                'type': 'data_quality',
                'factor': 'high_missing_rate',
                'description': 'Elevated missing data rate detected',
                'evidence': {'missing_rate': metrics['missing_rate']},
                'likelihood': 0.8
            })
        
        # Data drift
        if 'drift_score' in metrics and metrics['drift_score'] > 0.2:
            causes.append({
                'type': 'data_quality',
                'factor': 'data_drift',
                'description': 'Significant data drift from baseline',
                'evidence': {'drift_score': metrics['drift_score']},
                'likelihood': 0.7
            })
        
        return causes
    
    def _analyze_security_causes(self, anomaly: Anomaly, 
                                context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze security-related causes"""
        causes = []
        
        metrics = anomaly.metrics
        
        # Attack patterns
        if 'threats' in metrics:
            for threat in metrics['threats']:
                causes.append({
                    'type': 'security',
                    'factor': threat.get('type', 'unknown_threat'),
                    'description': f"Security threat detected: {threat.get('type', 'unknown')}",
                    'evidence': threat,
                    'likelihood': 0.9
                })
        
        return causes
    
    def _find_correlations(self, anomaly: Anomaly, 
                          context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find correlations with other system events"""
        correlations = []
        
        # This would typically involve analyzing time-series correlations
        # with other system metrics and events
        
        return correlations
    
    def _generate_recommendations(self, causes: List[Dict[str, Any]], 
                               correlations: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        for cause in causes:
            if cause['factor'] == 'high_response_time':
                recommendations.append("Consider scaling up resources or optimizing code")
            elif cause['factor'] == 'high_cpu_usage':
                recommendations.append("Investigate CPU-intensive processes and optimize")
            elif cause['factor'] == 'memory_pressure':
                recommendations.append("Monitor memory usage and consider increasing capacity")
            elif cause['factor'] == 'high_missing_rate':
                recommendations.append("Review data collection processes and input validation")
            elif cause['factor'] == 'data_drift':
                recommendations.append("Retrain model with recent data or update preprocessing")
        
        return recommendations
    
    def _calculate_analysis_confidence(self, causes: List[Dict[str, Any]], 
                                    correlations: List[Dict[str, Any]]) -> float:
        """Calculate confidence in the analysis"""
        if not causes:
            return 0.0
        
        # Weight causes by likelihood
        cause_confidence = sum(cause['likelihood'] for cause in causes) / len(causes)
        
        # Factor in correlations
        correlation_boost = len(correlations) * 0.1
        
        return min(1.0, cause_confidence + correlation_boost)

class AutomatedResponseSystem:
    """Automated response system for detected anomalies"""
    
    def __init__(self):
        self.response_rules = self._initialize_response_rules()
        self.response_history = deque(maxlen=1000)
    
    def _initialize_response_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize automated response rules"""
        return {
            'critical_performance': {
                'enabled': True,
                'actions': ['scale_up', 'alert_admins'],
                'threshold': 0.9
            },
            'security_threat': {
                'enabled': True,
                'actions': ['block_ip', 'alert_security'],
                'threshold': 0.8
            },
            'data_quality_degradation': {
                'enabled': True,
                'actions': ['validate_pipeline', 'alert_data_team'],
                'threshold': 0.7
            }
        }
    
    def execute_response(self, anomaly: Anomaly) -> Dict[str, Any]:
        """Execute automated response for anomaly"""
        response_id = f"response_{int(time.time())}"
        actions_taken = []
        
        try:
            # Determine response rule
            rule_key = self._determine_response_rule(anomaly)
            if rule_key not in self.response_rules:
                return {'response_id': response_id, 'status': 'no_rule', 'actions': []}
            
            rule = self.response_rules[rule_key]
            if not rule['enabled']:
                return {'response_id': response_id, 'status': 'disabled', 'actions': []}
            
            # Check threshold
            if anomaly.confidence < rule['threshold']:
                return {'response_id': response_id, 'status': 'below_threshold', 'actions': []}
            
            # Execute actions
            for action in rule['actions']:
                result = self._execute_action(action, anomaly)
                actions_taken.append({
                    'action': action,
                    'status': result['status'],
                    'details': result.get('details', {})
                })
            
            # Record response
            response_record = {
                'response_id': response_id,
                'anomaly_id': anomaly.id,
                'timestamp': datetime.now(),
                'rule': rule_key,
                'actions': actions_taken
            }
            self.response_history.append(response_record)
            
            return {
                'response_id': response_id,
                'status': 'executed',
                'actions': actions_taken
            }
            
        except Exception as e:
            logger.error(f"Automated response error: {e}")
            return {
                'response_id': response_id,
                'status': 'error',
                'error': str(e),
                'actions': actions_taken
            }
    
    def _determine_response_rule(self, anomaly: Anomaly) -> str:
        """Determine which response rule to apply"""
        if anomaly.type == AnomalyType.SECURITY:
            return 'security_threat'
        elif anomaly.type == AnomalyType.PERFORMANCE and anomaly.severity == Severity.CRITICAL:
            return 'critical_performance'
        elif anomaly.type == AnomalyType.DATA_QUALITY:
            return 'data_quality_degradation'
        
        return 'default'
    
    def _execute_action(self, action: str, anomaly: Anomaly) -> Dict[str, Any]:
        """Execute individual response action"""
        try:
            if action == 'scale_up':
                return self._scale_up_resources(anomaly)
            elif action == 'alert_admins':
                return self._alert_administrators(anomaly)
            elif action == 'block_ip':
                return self._block_malicious_ip(anomaly)
            elif action == 'alert_security':
                return self._alert_security_team(anomaly)
            elif action == 'validate_pipeline':
                return self._validate_data_pipeline(anomaly)
            elif action == 'alert_data_team':
                return self._alert_data_team(anomaly)
            else:
                return {'status': 'unknown_action', 'details': {'action': action}}
        
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _scale_up_resources(self, anomaly: Anomaly) -> Dict[str, Any]:
        """Scale up system resources"""
        # This would integrate with your infrastructure
        return {
            'status': 'executed',
            'details': {
                'action': 'scale_up_initiated',
                'target': 'compute_resources',
                'reason': 'performance_anomaly'
            }
        }
    
    def _alert_administrators(self, anomaly: Anomaly) -> Dict[str, Any]:
        """Send alert to administrators"""
        # This would integrate with your notification system
        return {
            'status': 'executed',
            'details': {
                'action': 'alert_sent',
                'recipients': ['admin@company.com'],
                'channel': 'email'
            }
        }
    
    def _block_malicious_ip(self, anomaly: Anomaly) -> Dict[str, Any]:
        """Block malicious IP address"""
        # This would integrate with your firewall/security system
        return {
            'status': 'executed',
            'details': {
                'action': 'ip_blocked',
                'ip': 'malicious_ip_address'  # Would extract from anomaly
            }
        }
    
    def _alert_security_team(self, anomaly: Anomaly) -> Dict[str, Any]:
        """Alert security team"""
        return {
            'status': 'executed',
            'details': {
                'action': 'security_alert_sent',
                'team': 'security@company.com',
                'priority': 'high'
            }
        }
    
    def _validate_data_pipeline(self, anomaly: Anomaly) -> Dict[str, Any]:
        """Validate data pipeline"""
        return {
            'status': 'executed',
            'details': {
                'action': 'pipeline_validation_initiated',
                'components': ['data_ingestion', 'preprocessing', 'validation']
            }
        }
    
    def _alert_data_team(self, anomaly: Anomaly) -> Dict[str, Any]:
        """Alert data team"""
        return {
            'status': 'executed',
            'details': {
                'action': 'data_team_alert_sent',
                'team': 'data@company.com',
                'issue': 'data_quality_degradation'
            }
        }
    
    def get_response_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get response history"""
        history = list(self.response_history)[-limit:]
        
        # Convert datetime objects to strings
        for record in history:
            record['timestamp'] = record['timestamp'].isoformat()
        
        return history

# Global instances
alert_system = RealTimeAlertSystem()
visualizer = AnomalyVisualizer()
root_cause_analyzer = RootCauseAnalyzer()
response_system = AutomatedResponseSystem()
