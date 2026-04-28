"""
Advanced Anomaly Detection System for FlavorSnap
Implements performance, data quality, and security threat detection
"""
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
import json
import logging
from enum import Enum
import asyncio
from abc import ABC, abstractmethod

# ML Libraries for anomaly detection
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class AnomalyType(Enum):
    """Types of anomalies that can be detected"""
    PERFORMANCE = "performance"
    DATA_QUALITY = "data_quality"
    SECURITY = "security"
    SYSTEM = "system"
    MODEL = "model"

class Severity(Enum):
    """Severity levels for anomalies"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Anomaly:
    """Represents a detected anomaly"""
    id: str
    type: AnomalyType
    severity: Severity
    timestamp: datetime
    description: str
    metrics: Dict[str, Any]
    confidence: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type.value,
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'metrics': self.metrics,
            'confidence': self.confidence,
            'source': self.source,
            'metadata': self.metadata
        }

class BaseAnomalyDetector(ABC):
    """Abstract base class for anomaly detectors"""
    
    def __init__(self, name: str, window_size: int = 100):
        self.name = name
        self.window_size = window_size
        self.data_buffer = deque(maxlen=window_size)
        self.last_detection = None
        
    @abstractmethod
    def detect(self, data: Dict[str, Any]) -> Optional[Anomaly]:
        """Detect anomalies in the provided data"""
        pass
    
    @abstractmethod
    def train(self, historical_data: List[Dict[str, Any]]) -> None:
        """Train the detector on historical data"""
        pass

class PerformanceAnomalyDetector(BaseAnomalyDetector):
    """Detects performance-related anomalies"""
    
    def __init__(self):
        super().__init__("performance", window_size=200)
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.baseline_metrics = {
            'response_time': 0.5,
            'throughput': 100,
            'error_rate': 0.01,
            'memory_usage': 0.7,
            'cpu_usage': 0.5
        }
    
    def detect(self, metrics: Dict[str, Any]) -> Optional[Anomaly]:
        """Detect performance anomalies"""
        try:
            # Extract relevant metrics
            features = self._extract_features(metrics)
            if not features:
                return None
            
            # Add to buffer
            self.data_buffer.append(features)
            
            # Check for immediate threshold violations
            threshold_anomaly = self._check_thresholds(metrics)
            if threshold_anomaly:
                return threshold_anomaly
            
            # Use ML model if trained
            if self.is_trained and len(self.data_buffer) >= 10:
                return self._ml_detection(features)
            
        except Exception as e:
            logger.error(f"Performance anomaly detection error: {e}")
        
        return None
    
    def _extract_features(self, metrics: Dict[str, Any]) -> Optional[List[float]]:
        """Extract numerical features from metrics"""
        try:
            features = [
                metrics.get('response_time', 0),
                metrics.get('throughput', 0),
                metrics.get('error_rate', 0),
                metrics.get('memory_usage', 0),
                metrics.get('cpu_usage', 0),
                metrics.get('gpu_usage', 0),
                metrics.get('disk_io', 0),
                metrics.get('network_io', 0)
            ]
            return features
        except Exception:
            return None
    
    def _check_thresholds(self, metrics: Dict[str, Any]) -> Optional[Anomaly]:
        """Check for threshold-based anomalies"""
        anomalies = []
        
        # Response time threshold
        if metrics.get('response_time', 0) > self.baseline_metrics['response_time'] * 3:
            anomalies.append({
                'metric': 'response_time',
                'value': metrics.get('response_time'),
                'threshold': self.baseline_metrics['response_time'] * 3
            })
        
        # Error rate threshold
        if metrics.get('error_rate', 0) > self.baseline_metrics['error_rate'] * 5:
            anomalies.append({
                'metric': 'error_rate',
                'value': metrics.get('error_rate'),
                'threshold': self.baseline_metrics['error_rate'] * 5
            })
        
        # Memory usage threshold
        if metrics.get('memory_usage', 0) > 0.9:
            anomalies.append({
                'metric': 'memory_usage',
                'value': metrics.get('memory_usage'),
                'threshold': 0.9
            })
        
        if anomalies:
            return Anomaly(
                id=f"perf_threshold_{int(time.time())}",
                type=AnomalyType.PERFORMANCE,
                severity=Severity.HIGH,
                timestamp=datetime.now(),
                description=f"Performance threshold violations detected: {len(anomalies)} metrics",
                metrics={'violations': anomalies},
                confidence=0.9,
                source=self.name
            )
        
        return None
    
    def _ml_detection(self, features: List[float]) -> Optional[Anomaly]:
        """Use ML model for anomaly detection"""
        try:
            # Prepare data
            recent_data = np.array(list(self.data_buffer)[-50:])
            scaled_data = self.scaler.transform(recent_data)
            
            # Predict
            anomaly_scores = self.model.decision_function(scaled_data)
            latest_score = anomaly_scores[-1]
            
            if latest_score < -0.1:  # Anomaly threshold
                return Anomaly(
                    id=f"perf_ml_{int(time.time())}",
                    type=AnomalyType.PERFORMANCE,
                    severity=Severity.MEDIUM,
                    timestamp=datetime.now(),
                    description="ML-based performance anomaly detected",
                    metrics={'anomaly_score': float(latest_score)},
                    confidence=abs(latest_score),
                    source=self.name
                )
        except Exception as e:
            logger.error(f"ML detection error: {e}")
        
        return None
    
    def train(self, historical_data: List[Dict[str, Any]]) -> None:
        """Train the performance anomaly detector"""
        try:
            # Extract features from historical data
            features_list = []
            for data in historical_data:
                features = self._extract_features(data)
                if features:
                    features_list.append(features)
            
            if len(features_list) < 50:
                logger.warning("Insufficient data for training performance detector")
                return
            
            # Train model
            X = np.array(features_list)
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled)
            self.is_trained = True
            
            # Update baseline metrics
            self._update_baseline(X)
            
            logger.info("Performance anomaly detector trained successfully")
            
        except Exception as e:
            logger.error(f"Training performance detector failed: {e}")
    
    def _update_baseline(self, features: np.ndarray) -> None:
        """Update baseline metrics from training data"""
        try:
            self.baseline_metrics = {
                'response_time': float(np.median(features[:, 0])),
                'throughput': float(np.median(features[:, 1])),
                'error_rate': float(np.median(features[:, 2])),
                'memory_usage': float(np.median(features[:, 3])),
                'cpu_usage': float(np.median(features[:, 4]))
            }
        except Exception:
            pass

class DataQualityAnomalyDetector(BaseAnomalyDetector):
    """Detects data quality anomalies"""
    
    def __init__(self):
        super().__init__("data_quality", window_size=300)
        self.quality_metrics = {
            'missing_rate': 0.05,
            'duplicate_rate': 0.02,
            'outlier_rate': 0.1,
            'data_drift': 0.15
        }
    
    def detect(self, data_info: Dict[str, Any]) -> Optional[Anomaly]:
        """Detect data quality anomalies"""
        try:
            anomalies = []
            
            # Check missing data rate
            missing_rate = data_info.get('missing_rate', 0)
            if missing_rate > self.quality_metrics['missing_rate'] * 2:
                anomalies.append({
                    'type': 'high_missing_rate',
                    'value': missing_rate,
                    'threshold': self.quality_metrics['missing_rate'] * 2
                })
            
            # Check duplicate rate
            duplicate_rate = data_info.get('duplicate_rate', 0)
            if duplicate_rate > self.quality_metrics['duplicate_rate'] * 3:
                anomalies.append({
                    'type': 'high_duplicate_rate',
                    'value': duplicate_rate,
                    'threshold': self.quality_metrics['duplicate_rate'] * 3
                })
            
            # Check data drift
            drift_score = data_info.get('drift_score', 0)
            if drift_score > self.quality_metrics['data_drift']:
                anomalies.append({
                    'type': 'data_drift',
                    'value': drift_score,
                    'threshold': self.quality_metrics['data_drift']
                })
            
            # Check schema validation
            schema_errors = data_info.get('schema_errors', 0)
            if schema_errors > 0:
                anomalies.append({
                    'type': 'schema_validation_errors',
                    'value': schema_errors,
                    'threshold': 0
                })
            
            if anomalies:
                severity = Severity.HIGH if len(anomalies) > 2 else Severity.MEDIUM
                return Anomaly(
                    id=f"data_quality_{int(time.time())}",
                    type=AnomalyType.DATA_QUALITY,
                    severity=severity,
                    timestamp=datetime.now(),
                    description=f"Data quality issues detected: {len(anomalies)} problems",
                    metrics={'anomalies': anomalies},
                    confidence=0.85,
                    source=self.name
                )
            
        except Exception as e:
            logger.error(f"Data quality detection error: {e}")
        
        return None
    
    def train(self, historical_data: List[Dict[str, Any]]) -> None:
        """Train data quality detector"""
        try:
            if len(historical_data) < 10:
                return
            
            # Update quality metrics from historical data
            missing_rates = [d.get('missing_rate', 0) for d in historical_data]
            duplicate_rates = [d.get('duplicate_rate', 0) for d in historical_data]
            outlier_rates = [d.get('outlier_rate', 0) for d in historical_data]
            
            if missing_rates:
                self.quality_metrics['missing_rate'] = float(np.percentile(missing_rates, 75))
            if duplicate_rates:
                self.quality_metrics['duplicate_rate'] = float(np.percentile(duplicate_rates, 75))
            if outlier_rates:
                self.quality_metrics['outlier_rate'] = float(np.percentile(outlier_rates, 75))
            
            logger.info("Data quality detector trained")
            
        except Exception as e:
            logger.error(f"Training data quality detector failed: {e}")

class SecurityAnomalyDetector(BaseAnomalyDetector):
    """Detects security-related anomalies"""
    
    def __init__(self):
        super().__init__("security", window_size=500)
        self.suspicious_patterns = {
            'sql_injection': ['union', 'select', 'drop', 'insert', 'delete', 'update'],
            'xss': ['<script', 'javascript:', 'onload=', 'onerror=', 'alert('],
            'path_traversal': ['../', '..\\', '/etc/', '/var/'],
            'command_injection': ['; ', '&&', '||', '`', '$(', '${']
        }
        self.ip_request_counts = defaultdict(int)
        self.failed_logins = defaultdict(list)
    
    def detect(self, security_data: Dict[str, Any]) -> Optional[Anomaly]:
        """Detect security anomalies"""
        try:
            anomalies = []
            
            # Check for injection attacks
            request_data = security_data.get('request_data', '')
            injection_anomaly = self._check_injection_attacks(request_data)
            if injection_anomaly:
                anomalies.append(injection_anomaly)
            
            # Check for unusual request patterns
            ip_address = security_data.get('ip_address', '')
            pattern_anomaly = self._check_request_patterns(ip_address, security_data)
            if pattern_anomaly:
                anomalies.append(pattern_anomaly)
            
            # Check for authentication failures
            auth_anomaly = self._check_authentication_failures(security_data)
            if auth_anomaly:
                anomalies.append(auth_anomaly)
            
            # Check for privilege escalation attempts
            privilege_anomaly = self._check_privilege_escalation(security_data)
            if privilege_anomaly:
                anomalies.append(privilege_anomaly)
            
            if anomalies:
                return Anomaly(
                    id=f"security_{int(time.time())}",
                    type=AnomalyType.SECURITY,
                    severity=Severity.HIGH,
                    timestamp=datetime.now(),
                    description=f"Security threats detected: {len(anomalies)} issues",
                    metrics={'threats': anomalies},
                    confidence=0.9,
                    source=self.name
                )
            
        except Exception as e:
            logger.error(f"Security detection error: {e}")
        
        return None
    
    def _check_injection_attacks(self, request_data: str) -> Optional[Dict[str, Any]]:
        """Check for injection attack patterns"""
        request_lower = request_data.lower()
        
        for attack_type, patterns in self.suspicious_patterns.items():
            for pattern in patterns:
                if pattern in request_lower:
                    return {
                        'type': attack_type,
                        'pattern': pattern,
                        'severity': 'high'
                    }
        
        return None
    
    def _check_request_patterns(self, ip_address: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check for unusual request patterns"""
        current_time = datetime.now()
        
        # Track request frequency
        self.ip_request_counts[ip_address] += 1
        
        # Check for high request rate
        if self.ip_request_counts[ip_address] > 1000:  # More than 1000 requests
            return {
                'type': 'high_request_rate',
                'ip': ip_address,
                'count': self.ip_request_counts[ip_address],
                'severity': 'medium'
            }
        
        # Check for rapid requests (time-based)
        recent_requests = data.get('recent_request_count', 0)
        if recent_requests > 100:  # More than 100 requests in short time
            return {
                'type': 'rapid_requests',
                'ip': ip_address,
                'count': recent_requests,
                'severity': 'high'
            }
        
        return None
    
    def _check_authentication_failures(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check for authentication failure patterns"""
        ip_address = data.get('ip_address', '')
        is_failed_login = data.get('failed_login', False)
        
        if is_failed_login:
            current_time = datetime.now()
            self.failed_logins[ip_address].append(current_time)
            
            # Clean old failures (older than 1 hour)
            self.failed_logins[ip_address] = [
                t for t in self.failed_logins[ip_address] 
                if current_time - t < timedelta(hours=1)
            ]
            
            # Check for brute force
            if len(self.failed_logins[ip_address]) > 10:
                return {
                    'type': 'brute_force_attempt',
                    'ip': ip_address,
                    'failure_count': len(self.failed_logins[ip_address]),
                    'severity': 'high'
                }
        
        return None
    
    def _check_privilege_escalation(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check for privilege escalation attempts"""
        suspicious_endpoints = ['/admin', '/root', '/config', '/system']
        endpoint = data.get('endpoint', '')
        
        for suspicious in suspicious_endpoints:
            if suspicious in endpoint.lower():
                return {
                    'type': 'privilege_escalation_attempt',
                    'endpoint': endpoint,
                    'severity': 'critical'
                }
        
        return None
    
    def train(self, historical_data: List[Dict[str, Any]]) -> None:
        """Train security detector"""
        try:
            # Analyze historical patterns
            ip_patterns = defaultdict(int)
            for data in historical_data:
                ip = data.get('ip_address', '')
                if ip:
                    ip_patterns[ip] += 1
            
            # Update thresholds based on historical data
            if ip_patterns:
                avg_requests = np.mean(list(ip_patterns.values()))
                std_requests = np.std(list(ip_patterns.values()))
                
                # Set threshold at mean + 3*std
                self.high_request_threshold = avg_requests + (3 * std_requests)
            
            logger.info("Security anomaly detector trained")
            
        except Exception as e:
            logger.error(f"Training security detector failed: {e}")

class AnomalyDetectionSystem:
    """Main anomaly detection system"""
    
    def __init__(self):
        self.detectors = {
            AnomalyType.PERFORMANCE: PerformanceAnomalyDetector(),
            AnomalyType.DATA_QUALITY: DataQualityAnomalyDetector(),
            AnomalyType.SECURITY: SecurityAnomalyDetector()
        }
        self.anomalies = deque(maxlen=1000)
        self.alert_handlers = []
        self.is_running = False
        
    def add_detector(self, anomaly_type: AnomalyType, detector: BaseAnomalyDetector):
        """Add a custom detector"""
        self.detectors[anomaly_type] = detector
    
    def detect_anomalies(self, data: Dict[str, Any]) -> List[Anomaly]:
        """Detect all types of anomalies"""
        detected_anomalies = []
        
        for anomaly_type, detector in self.detectors.items():
            try:
                anomaly = detector.detect(data)
                if anomaly:
                    detected_anomalies.append(anomaly)
                    self.anomalies.append(anomaly)
                    
                    # Trigger alerts
                    self._trigger_alerts(anomaly)
                    
            except Exception as e:
                logger.error(f"Detector {detector.name} failed: {e}")
        
        return detected_anomalies
    
    def _trigger_alerts(self, anomaly: Anomaly):
        """Trigger alert handlers for detected anomaly"""
        for handler in self.alert_handlers:
            try:
                handler(anomaly)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
    
    def add_alert_handler(self, handler):
        """Add an alert handler"""
        self.alert_handlers.append(handler)
    
    def get_anomalies(self, 
                     anomaly_type: Optional[AnomalyType] = None,
                     severity: Optional[Severity] = None,
                     time_range: Optional[timedelta] = None) -> List[Anomaly]:
        """Get filtered anomalies"""
        filtered_anomalies = list(self.anomalies)
        
        # Filter by type
        if anomaly_type:
            filtered_anomalies = [a for a in filtered_anomalies if a.type == anomaly_type]
        
        # Filter by severity
        if severity:
            filtered_anomalies = [a for a in filtered_anomalies if a.severity == severity]
        
        # Filter by time range
        if time_range:
            cutoff_time = datetime.now() - time_range
            filtered_anomalies = [a for a in filtered_anomalies if a.timestamp >= cutoff_time]
        
        return filtered_anomalies
    
    def train_all_detectors(self, historical_data: Dict[AnomalyType, List[Dict[str, Any]]]):
        """Train all detectors with historical data"""
        for anomaly_type, detector in self.detectors.items():
            if anomaly_type in historical_data:
                detector.train(historical_data[anomaly_type])
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        recent_anomalies = self.get_anomalies(time_range=timedelta(hours=1))
        
        health_score = 100
        if recent_anomalies:
            # Deduct points based on severity
            for anomaly in recent_anomalies:
                if anomaly.severity == Severity.CRITICAL:
                    health_score -= 20
                elif anomaly.severity == Severity.HIGH:
                    health_score -= 10
                elif anomaly.severity == Severity.MEDIUM:
                    health_score -= 5
                elif anomaly.severity == Severity.LOW:
                    health_score -= 2
        
        health_score = max(0, health_score)
        
        return {
            'health_score': health_score,
            'status': 'healthy' if health_score > 80 else 'degraded' if health_score > 50 else 'unhealthy',
            'recent_anomalies': len(recent_anomalies),
            'active_detectors': len(self.detectors),
            'total_anomalies': len(self.anomalies)
        }

# Global instance
anomaly_system = AnomalyDetectionSystem()
