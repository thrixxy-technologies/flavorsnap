"""
Advanced Queue Monitoring System for FlavorSnap
Provides comprehensive monitoring, analytics, and alerting for queue operations
"""

import time
import psutil
import torch
import numpy as np
import pandas as pd
from functools import wraps
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask import Flask, Response, request, make_response
from dataclasses import dataclass, asdict
import pytz

# Optional imports
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
try:
    from persistence import log_prediction_history
except Exception:
    log_prediction_history = None
try:
    from anomaly_detection import anomaly_system, AnomalyType
except Exception:
    anomaly_system = None
    AnomalyType = None

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'flask_http_request_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'flask_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

REQUEST_EXCEPTIONS = Counter(
    'flask_http_request_exceptions_total',
    'Total HTTP request exceptions',
    ['method', 'endpoint']
)

MODEL_INFERENCE_COUNT = Counter(
    'model_inference_total',
    'Total model inferences',
    ['label', 'status']
)

MODEL_INFERENCE_DURATION = Histogram(
    'model_inference_duration_seconds',
    'Model inference duration in seconds',
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)

MODEL_INFERENCE_FAILURES = Counter(
    'model_inference_failures_total',
    'Total model inference failures'
)

MODEL_ACCURACY = Gauge(
    'model_accuracy',
    'Current model accuracy'
)

MEMORY_USAGE = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
)

CPU_USAGE = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage'
)

GPU_MEMORY_USAGE = Gauge(
    'gpu_memory_usage_bytes',
    'GPU memory usage in bytes'
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Number of active connections'
)

DATABASE_CONNECTIONS = Gauge(
    'database_connection_pool_active',
    'Active database connections'
)

REDIS_CONNECTION_STATUS = Gauge(
    'redis_connection_status',
    'Redis connection status (1=connected, 0=disconnected)'
)

MODEL_LOAD_TIME = Gauge(
    'model_load_time_seconds',
    'Time taken to load the model'
)
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import logging
import statistics

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MetricType(Enum):
    """Types of metrics to track"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class Metric:
    """Metric data point"""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE

@dataclass
class Alert:
    """Alert definition"""
    name: str
    level: AlertLevel
    condition: str
    threshold: float
    message: str
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

@dataclass
class QueueMetrics:
    """Queue-specific metrics"""
    queue_name: str
    total_tasks: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    average_wait_time: float = 0.0
    average_processing_time: float = 0.0
    throughput: float = 0.0  # tasks per second
    error_rate: float = 0.0  # percentage
    last_updated: datetime = field(default_factory=datetime.now)

class MetricsCollector:
    """Collects and stores metrics"""
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._lock = threading.RLock()
    
    def record_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Record counter metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] += value
            metric = Metric(name, self._counters[key], metric_type=MetricType.COUNTER, labels=labels or {})
            self._metrics[key].append(metric)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set gauge metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value
            metric = Metric(name, value, metric_type=MetricType.GAUGE, labels=labels or {})
            self._metrics[key].append(metric)
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record histogram metric"""
        with self._lock:
            key = self._make_key(name, labels)
            metric = Metric(name, value, metric_type=MetricType.HISTOGRAM, labels=labels or {})
            self._metrics[key].append(metric)
    
    def record_timer(self, name: str, duration_ms: float, labels: Dict[str, str] = None):
        """Record timer metric"""
        with self._lock:
            key = self._make_key(name, labels)
            metric = Metric(name, duration_ms, metric_type=MetricType.TIMER, labels=labels or {})
            self._metrics[key].append(metric)
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create metric key from name and labels"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}[{label_str}]"
    
    def get_metric_history(self, name: str, labels: Dict[str, str] = None, 
                          since: Optional[datetime] = None) -> List[Metric]:
        """Get metric history"""
        with self._lock:
            key = self._make_key(name, labels)
            metrics = list(self._metrics[key])
            
            if since:
                metrics = [m for m in metrics if m.timestamp >= since]
            
            return metrics
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metric values"""
        with self._lock:
            result = {}
            
            # Add counters
            for key, value in self._counters.items():
                result[key] = {"type": "counter", "value": value}
            
            # Add gauges
            for key, value in self._gauges.items():
                result[key] = {"type": "gauge", "value": value}
            
            return result
    
    def calculate_percentiles(self, name: str, percentiles: List[float] = None,
                            labels: Dict[str, str] = None) -> Dict[str, float]:
        """Calculate percentiles for histogram/timer metrics"""
        if percentiles is None:
            percentiles = [50.0, 90.0, 95.0, 99.0]
        
        metrics = self.get_metric_history(name, labels)
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        result = {}
        
        for p in percentiles:
            try:
                result[f"p{p}"] = statistics.percentile(values, p)
            except Exception as e:
                logger.error(f"Error calculating percentile {p}: {e}")
                result[f"p{p}"] = 0.0
        
        return result

class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self):
        self._alerts: Dict[str, Alert] = {}
        self._alert_handlers: List[Callable] = []
        self._lock = threading.RLock()
    
    def add_alert(self, alert: Alert):
        """Add alert definition"""
        with self._lock:
            self._alerts[alert.name] = alert
    
    def remove_alert(self, name: str):
        """Remove alert"""
        with self._lock:
            self._alerts.pop(name, None)
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add alert notification handler"""
        self._alert_handlers.append(handler)
    
    def check_alerts(self, metrics_collector: MetricsCollector):
        """Check all alerts against current metrics"""
        current_metrics = metrics_collector.get_current_metrics()
        
        with self._lock:
            for alert in self._alerts.values():
                if not alert.enabled:
                    continue
                
                try:
                    if self._evaluate_condition(alert.condition, alert.threshold, current_metrics):
                        self._trigger_alert(alert)
                except Exception as e:
                    logger.error(f"Error evaluating alert {alert.name}: {e}")
    
    def _evaluate_condition(self, condition: str, threshold: float, metrics: Dict[str, Any]) -> bool:
        """Evaluate alert condition"""
        # Simple condition evaluation - can be extended with more complex logic
        metric_name = condition.split()[0]  # Extract metric name
        
        if metric_name in metrics:
            current_value = metrics[metric_name]["value"]
            
            if ">" in condition:
                return current_value > threshold
            elif "<" in condition:
                return current_value < threshold
            elif ">=" in condition:
                return current_value >= threshold
            elif "<=" in condition:
                return current_value <= threshold
            elif "==" in condition:
                return current_value == threshold
        
        return False
    
    def _trigger_alert(self, alert: Alert):
        """Trigger alert notification"""
        alert.last_triggered = datetime.now()
        alert.trigger_count += 1
        
        logger.warning(f"Alert triggered: {alert.name} - {alert.message}")
        
        for handler in self._alert_handlers:
            try:
                resp_obj = make_response(result)
            except Exception:
                resp_obj = None
            return result
        except Exception as e:
            status = 'failure'
            MODEL_INFERENCE_FAILURES.inc()
            raise
        finally:
            duration = time.time() - start_time
            MODEL_INFERENCE_DURATION.observe(duration)
            
            # Extract label from result if available
            label = 'unknown'
            payload = None
            try:
                if resp_obj is not None:
                    payload = resp_obj.get_json(silent=True)
                    if isinstance(payload, dict):
                        label = payload.get('label', 'unknown')
            except Exception:
                payload = None
            
            MODEL_INFERENCE_COUNT.labels(label=label, status=status).inc()
            try:
                if log_prediction_history and isinstance(payload, dict):
                    meta = {
                        "request_id": request.headers.get("X-Request-Id"),
                        "user_id": request.headers.get("X-User-Id"),
                        "error_message": None if status == 'success' else 'inference_failed'
                    }
                    log_prediction_history(payload, duration, status, meta)
            except Exception:
                pass
    
    return wrapper

def update_model_accuracy(accuracy: float):
    """Update model accuracy metric"""
    MODEL_ACCURACY.set(accuracy)

# Data Quality Monitoring
DATA_QUALITY_SCORE = Gauge(
    'data_quality_score',
    'Overall data quality score (0-100)'
)

MISSING_DATA_RATE = Gauge(
    'missing_data_rate',
    'Rate of missing data in incoming requests'
)

DUPLICATE_DATA_RATE = Gauge(
    'duplicate_data_rate',
    'Rate of duplicate data detected'
)

DATA_DRIFT_SCORE = Gauge(
    'data_drift_score',
    'Data drift detection score'
)


MISSING_DATA_RATE = Gauge(
    'missing_data_rate',
    'Rate of missing data in incoming requests'
)

DUPLICATE_DATA_RATE = Gauge(
    'duplicate_data_rate',
    'Rate of duplicate data detected'
)


MISSING_DATA_RATE = Gauge(
    'missing_data_rate',
    'Rate of missing data in incoming requests'
)

DUPLICATE_DATA_RATE = Gauge(
    'duplicate_data_rate',
    'Rate of duplicate data detected'
)

DATA_DRIFT_SCORE = Gauge(
    'data_drift_score',
    'Data drift detection score'
)



MISSING_DATA_RATE = Gauge(
    'missing_data_rate',
    'Rate of missing data in incoming requests'
)

DUPLICATE_DATA_RATE = Gauge(
    'duplicate_data_rate',
    'Rate of duplicate data detected'
)

DATA_DRIFT_SCORE = Gauge(
    'data_drift_score',
    'Data drift detection score'
)

VALIDATION_ERRORS = Counter(
    'validation_errors_total',
    'Total validation errors',
    ['error_type']
)

class DataQualityMonitor:
    """Data quality monitoring and validation"""
    
    def __init__(self):
        self.data_buffer = deque(maxlen=1000)
        self.baseline_stats = {}
        self.validation_rules = {
            'image_size_range': (10, 16 * 1024 * 1024),  # 10 bytes to 16MB
            'allowed_formats': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
            'max_text_length': 1000,
            'required_fields': ['image', 'timestamp']
        }
        self.duplicate_detector = set()
        self.drift_detector = None
    
    
    def __init__(self):
        self.data_buffer = deque(maxlen=1000)
        self.baseline_stats = {}
        self.validation_rules = {
            'image_size_range': (10, 16 * 1024 * 1024),  # 10 bytes to 16MB
            'allowed_formats': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
            'max_text_length': 1000,
            'required_fields': ['image', 'timestamp']
        }
        self.duplicate_detector = set()
        self.drift_detector = None
    
    def validate_request_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate incoming request data"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'quality_score': 100
        }
        
        try:
            # Check required fields
            for field in self.validation_rules['required_fields']:
                if field not in request_data:
                    validation_result['errors'].append(f"Missing required field: {field}")
                    validation_result['is_valid'] = False
                    VALIDATION_ERRORS.labels(error_type='missing_field').inc()
            
            # Validate image data if present
            if 'image' in request_data:
                image_errors = self._validate_image_data(request_data['image'])
                validation_result['errors'].extend(image_errors)
                if image_errors:
                    validation_result['is_valid'] = False
                    VALIDATION_ERRORS.labels(error_type='image_validation').inc()
            
            # Check for duplicates
            if self._is_duplicate(request_data):
                validation_result['warnings'].append("Potential duplicate data detected")
                validation_result['quality_score'] -= 10
            
            # Calculate quality score
            validation_result['quality_score'] = max(0, validation_result['quality_score'] - len(validation_result['errors']) * 20 - len(validation_result['warnings']) * 5)
            
            # Update metrics
            self._update_quality_metrics(validation_result)
            
            # Store for drift detection
            self.data_buffer.append({
                'timestamp': datetime.now(),
                'data': request_data,
                'quality_score': validation_result['quality_score']
            })
            
            # Trigger anomaly detection if available
            if anomaly_system:
                quality_data = {
                    'missing_rate': len([e for e in validation_result['errors'] if 'missing' in e.lower()]) / max(len(self.validation_rules['required_fields']), 1),
                    'duplicate_rate': 1.0 if self._is_duplicate(request_data) else 0.0,
                    'quality_score': validation_result['quality_score'] / 100.0,
                    'validation_errors': len(validation_result['errors'])
                }
                anomalies = anomaly_system.detect_anomalies(quality_data)
                if anomalies:
                    validation_result['anomalies'] = [a.to_dict() for a in anomalies]
            
        except Exception as e:
            validation_result['errors'].append(f"Validation error: {str(e)}")
            validation_result['is_valid'] = False
            VALIDATION_ERRORS.labels(error_type='system_error').inc()
        
        return validation_result
    
    def _validate_image_data(self, image_data: Any) -> List[str]:
        """Validate image data"""
        errors = []
        
        try:
            # Check image size
            if hasattr(image_data, 'seek') and hasattr(image_data, 'tell'):
                image_data.seek(0, 2)  # Seek to end
                size = image_data.tell()
                image_data.seek(0)  # Reset position
                
                min_size, max_size = self.validation_rules['image_size_range']
                if size < min_size or size > max_size:
                    errors.append(f"Image size {size} bytes is outside valid range [{min_size}, {max_size}]")
            
            # Check file format if filename is available
            if hasattr(image_data, 'filename') and image_data.filename:
                ext = image_data.filename.rsplit('.', 1)[1].lower() if '.' in image_data.filename else ''
                if ext not in self.validation_rules['allowed_formats']:
                    errors.append(f"Unsupported image format: {ext}")
        
        except Exception as e:
            errors.append(f"Image validation error: {str(e)}")
        
        return errors
    
    def _is_duplicate(self, request_data: Dict[str, Any]) -> bool:
        """Check for duplicate data"""
        try:
            # Create a hash of key fields for duplicate detection
            key_fields = []
            if 'image' in request_data and hasattr(request_data['image'], 'filename'):
                key_fields.append(request_data['image'].filename)
            if 'timestamp' in request_data:
                key_fields.append(str(request_data['timestamp']))
            
            if key_fields:
                data_hash = hash(tuple(key_fields))
                if data_hash in self.duplicate_detector:
                    return True
                self.duplicate_detector.add(data_hash)
                
                # Clean old hashes to prevent memory issues
                if len(self.duplicate_detector) > 10000:
                    # Keep only recent half
                    self.duplicate_detector = set(list(self.duplicate_detector)[-5000:])
        
        except Exception:
            pass
        
        
        try:
            # Check image size
            if hasattr(image_data, 'seek') and hasattr(image_data, 'tell'):
                image_data.seek(0, 2)  # Seek to end
                size = image_data.tell()
                image_data.seek(0)  # Reset position
                
                min_size, max_size = self.validation_rules['image_size_range']
                if size < min_size or size > max_size:
                    errors.append(f"Image size {size} bytes is outside valid range [{min_size}, {max_size}]")
            
            # Check file format if filename is available
            if hasattr(image_data, 'filename') and image_data.filename:
                ext = image_data.filename.rsplit('.', 1)[1].lower() if '.' in image_data.filename else ''
                if ext not in self.validation_rules['allowed_formats']:
                    errors.append(f"Unsupported image format: {ext}")
        
        except Exception as e:
            errors.append(f"Image validation error: {str(e)}")
        
        return errors
    
    def _is_duplicate(self, request_data: Dict[str, Any]) -> bool:
        """Check for duplicate data"""
        try:
            # Create a hash of key fields for duplicate detection
            key_fields = []
            if 'image' in request_data and hasattr(request_data['image'], 'filename'):
                key_fields.append(request_data['image'].filename)
            if 'timestamp' in request_data:
                key_fields.append(str(request_data['timestamp']))
            
            if key_fields:
                data_hash = hash(tuple(key_fields))
                if data_hash in self.duplicate_detector:
                    return True
                self.duplicate_detector.add(data_hash)
                
                # Clean old hashes to prevent memory issues
                if len(self.duplicate_detector) > 10000:
                    # Keep only recent half
                    self.duplicate_detector = set(list(self.duplicate_detector)[-5000:])
        
        except Exception:
            pass
        
        return False
    
    def _update_quality_metrics(self, validation_result: Dict[str, Any]):
        """Update data quality metrics"""
        try:
        
        try:
            # Check image size
            if hasattr(image_data, 'seek') and hasattr(image_data, 'tell'):
                image_data.seek(0, 2)  # Seek to end
                size = image_data.tell()
                image_data.seek(0)  # Reset position
                
                min_size, max_size = self.validation_rules['image_size_range']
                if size < min_size or size > max_size:
                    errors.append(f"Image size {size} bytes is outside valid range [{min_size}, {max_size}]")
            
            # Check file format if filename is available
            if hasattr(image_data, 'filename') and image_data.filename:
                ext = image_data.filename.rsplit('.', 1)[1].lower() if '.' in image_data.filename else ''
                if ext not in self.validation_rules['allowed_formats']:
                    errors.append(f"Unsupported image format: {ext}")
        
        except Exception as e:
            errors.append(f"Image validation error: {str(e)}")
        
        return errors
    
    def _is_duplicate(self, request_data: Dict[str, Any]) -> bool:
        """Check for duplicate data"""
        try:
            # Create a hash of key fields for duplicate detection
            key_fields = []
            if 'image' in request_data and hasattr(request_data['image'], 'filename'):
                key_fields.append(request_data['image'].filename)
            if 'timestamp' in request_data:
                key_fields.append(str(request_data['timestamp']))
            
            if key_fields:
                data_hash = hash(tuple(key_fields))
                if data_hash in self.duplicate_detector:
                    return True
                self.duplicate_detector.add(data_hash)
                
                # Clean old hashes to prevent memory issues
                if len(self.duplicate_detector) > 10000:
                    # Keep only recent half
                    self.duplicate_detector = set(list(self.duplicate_detector)[-5000:])
        
        except Exception:
            pass
        
        return False
    
    def _update_quality_metrics(self, validation_result: Dict[str, Any]):
        """Update data quality metrics"""
        try:
            # Update quality score
            DATA_QUALITY_SCORE.set(validation_result['quality_score'])
            
            # Calculate missing data rate
            missing_rate = len([e for e in validation_result['errors'] if 'missing' in e.lower()]) / max(len(self.validation_rules['required_fields']), 1)
            MISSING_DATA_RATE.set(missing_rate)
            
            # Calculate duplicate rate
            duplicate_rate = 1.0 if any('duplicate' in w.lower() for w in validation_result['warnings']) else 0.0
            DUPLICATE_DATA_RATE.set(duplicate_rate)
            
        except Exception:
            pass
    
            
        except Exception:
            pass
    
            
        except Exception:
            pass
    
    def detect_data_drift(self) -> Dict[str, Any]:
        """Detect data drift using statistical methods"""
        try:
            if len(self.data_buffer) < 100:
                return {'drift_detected': False, 'reason': 'Insufficient data'}
            
            # Get recent and historical data
            recent_data = list(self.data_buffer)[-50:]  # Last 50 records
            historical_data = list(self.data_buffer)[:-50]  # Everything before recent
            
            if len(historical_data) < 50:
                return {'drift_detected': False, 'reason': 'Insufficient historical data'}
            
            # Compare quality scores
            recent_scores = [d['quality_score'] for d in recent_data]
            historical_scores = [d['quality_score'] for d in historical_data]
            
            # Statistical test for drift
            recent_mean = np.mean(recent_scores)
            historical_mean = np.mean(historical_scores)
            
            # Calculate drift score
            drift_score = abs(recent_mean - historical_mean) / max(historical_mean, 1)
            
            # Update drift metric
            DATA_DRIFT_SCORE.set(drift_score)
            
            drift_detected = drift_score > 0.15  # 15% change threshold
            
            return {
                'drift_detected': drift_detected,
                'drift_score': drift_score,
                'recent_mean': recent_mean,
                'historical_mean': historical_mean,
                'sample_sizes': {'recent': len(recent_data), 'historical': len(historical_data)}
            }
        
        except Exception as e:
            return {'drift_detected': False, 'error': str(e)}
    
    def get_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive data quality report"""
        try:
            if not self.data_buffer:
                return {'status': 'no_data', 'message': 'No data available for analysis'}
            
            recent_data = list(self.data_buffer)[-100:]  # Last 100 records
            
            # Calculate statistics
            quality_scores = [d['quality_score'] for d in recent_data]
            timestamps = [d['timestamp'] for d in recent_data]
            
            report = {
                'summary': {
                    'total_records': len(recent_data),
                    'avg_quality_score': np.mean(quality_scores),
                    'min_quality_score': np.min(quality_scores),
                    'max_quality_score': np.max(quality_scores),
                    'time_range': {
                        'start': min(timestamps).isoformat(),
                        'end': max(timestamps).isoformat()
                    }
                },
                'trends': {
                    'quality_trend': 'improving' if len(quality_scores) > 1 and quality_scores[-1] > quality_scores[0] else 'declining',
                    'data_volume_trend': 'increasing' if len(recent_data) > 50 else 'stable'
                },
                'issues': {
                    'low_quality_records': len([s for s in quality_scores if s < 70]),
                    'validation_errors': sum(1 for d in recent_data if d.get('validation_errors', 0) > 0),
                    'duplicate_warnings': sum(1 for d in recent_data if 'duplicate' in str(d.get('warnings', [])))
                },
                'drift_analysis': self.detect_data_drift()
            }
            
            return report
        
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

# Global data quality monitor instance
data_quality_monitor = DataQualityMonitor()

def validate_data_quality(func):
    """Decorator to validate data quality for API endpoints"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Get request data
            request_data = {}
            
            # Extract data from request
            if request.files:
                request_data.update(request.files.to_dict())
            if request.form:
                request_data.update(request.form.to_dict())
            if request.get_json():
                request_data.update(request.get_json())
            
            # Add metadata
            request_data['timestamp'] = datetime.now().isoformat()
            request_data['ip_address'] = request.remote_addr
            request_data['user_agent'] = request.headers.get('User-Agent', '')
            
            # Validate data quality
            validation_result = data_quality_monitor.validate_request_data(request_data)
            
            # Store validation result in request context for later use
            request.data_quality = validation_result
            
            # If data quality is too low, you might want to reject the request
            if validation_result['quality_score'] < 30:
                return {
                    'error': 'Data quality too low',
                    'quality_score': validation_result['quality_score'],
                    'errors': validation_result['errors']
                }, 400
            
            return func(*args, **kwargs)
        
        except Exception as e:
            return {'error': f'Data quality validation failed: {str(e)}'}, 500
    
    return wrapper
            
        except Exception:
            pass
    
    def detect_data_drift(self) -> Dict[str, Any]:
        """Detect data drift using statistical methods"""
        try:
            if len(self.data_buffer) < 100:
                return {'drift_detected': False, 'reason': 'Insufficient data'}
            
            # Get recent and historical data
            recent_data = list(self.data_buffer)[-50:]  # Last 50 records
            historical_data = list(self.data_buffer)[:-50]  # Everything before recent
            
            if len(historical_data) < 50:
                return {'drift_detected': False, 'reason': 'Insufficient historical data'}
            
            # Compare quality scores
            recent_scores = [d['quality_score'] for d in recent_data]
            historical_scores = [d['quality_score'] for d in historical_data]
            
            # Statistical test for drift
            recent_mean = np.mean(recent_scores)
            historical_mean = np.mean(historical_scores)
            
            # Calculate drift score
            drift_score = abs(recent_mean - historical_mean) / max(historical_mean, 1)
            
            # Update drift metric
            DATA_DRIFT_SCORE.set(drift_score)
            
            drift_detected = drift_score > 0.15  # 15% change threshold
            
            
            # Get recent and historical data
            recent_data = list(self.data_buffer)[-50:]  # Last 50 records
            historical_data = list(self.data_buffer)[:-50]  # Everything before recent
            
            if len(historical_data) < 50:
                return {'drift_detected': False, 'reason': 'Insufficient historical data'}
            
            # Compare quality scores
            recent_scores = [d['quality_score'] for d in recent_data]
            historical_scores = [d['quality_score'] for d in historical_data]
            
            # Statistical test for drift
            recent_mean = np.mean(recent_scores)
            historical_mean = np.mean(historical_scores)
            
            # Calculate drift score
            drift_score = abs(recent_mean - historical_mean) / max(historical_mean, 1)
            
            # Update drift metric
            DATA_DRIFT_SCORE.set(drift_score)
            
            drift_detected = drift_score > 0.15  # 15% change threshold
            
            return {
                'drift_detected': drift_detected,
                'drift_score': drift_score,
                'recent_mean': recent_mean,
                'historical_mean': historical_mean,
                'sample_sizes': {'recent': len(recent_data), 'historical': len(historical_data)}
            }
        
        except Exception as e:
            return {'drift_detected': False, 'error': str(e)}
    
    def get_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive data quality report"""
        try:
            if not self.data_buffer:
                return {'status': 'no_data', 'message': 'No data available for analysis'}
            
            recent_data = list(self.data_buffer)[-100:]  # Last 100 records
            
            # Calculate statistics
            quality_scores = [d['quality_score'] for d in recent_data]
            timestamps = [d['timestamp'] for d in recent_data]
            
            report = {
                'summary': {
                    'total_records': len(recent_data),
                    'avg_quality_score': np.mean(quality_scores),
                    'min_quality_score': np.min(quality_scores),
                    'max_quality_score': np.max(quality_scores),
                    'time_range': {
                        'start': min(timestamps).isoformat(),
                        'end': max(timestamps).isoformat()
                    }
                },
                'trends': {
                    'quality_trend': 'improving' if len(quality_scores) > 1 and quality_scores[-1] > quality_scores[0] else 'declining',
                    'data_volume_trend': 'increasing' if len(recent_data) > 50 else 'stable'
                },
                'issues': {
                    'low_quality_records': len([s for s in quality_scores if s < 70]),
                    'validation_errors': sum(1 for d in recent_data if d.get('validation_errors', 0) > 0),
                    'duplicate_warnings': sum(1 for d in recent_data if 'duplicate' in str(d.get('warnings', [])))
                },
                'drift_analysis': self.detect_data_drift()
            }
            
            return report
        
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

# Global data quality monitor instance
data_quality_monitor = DataQualityMonitor()

def validate_data_quality(func):
    """Decorator to validate data quality for API endpoints"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Get request data
            request_data = {}
            
            # Extract data from request
            if request.files:
                request_data.update(request.files.to_dict())
            if request.form:
                request_data.update(request.form.to_dict())
            if request.get_json():
                request_data.update(request.get_json())
            
            # Add metadata
            request_data['timestamp'] = datetime.now().isoformat()
            request_data['ip_address'] = request.remote_addr
            request_data['user_agent'] = request.headers.get('User-Agent', '')
            
            # Validate data quality
            validation_result = data_quality_monitor.validate_request_data(request_data)
            
            # Store validation result in request context for later use
            request.data_quality = validation_result
            
            # If data quality is too low, you might want to reject the request
            if validation_result['quality_score'] < 30:
                return {
                    'error': 'Data quality too low',
                    'quality_score': validation_result['quality_score'],
                    'errors': validation_result['errors']
                }, 400
            
            return func(*args, **kwargs)
        
        except Exception as e:
            return {'error': f'Data quality validation failed: {str(e)}'}, 500
    
    return wrapper
            
            # Get recent and historical data
            recent_data = list(self.data_buffer)[-50:]  # Last 50 records
            historical_data = list(self.data_buffer)[:-50]  # Everything before recent
            
            if len(historical_data) < 50:
                return {'drift_detected': False, 'reason': 'Insufficient historical data'}
            
            # Compare quality scores
            recent_scores = [d['quality_score'] for d in recent_data]
            historical_scores = [d['quality_score'] for d in historical_data]
            
            # Statistical test for drift
            recent_mean = np.mean(recent_scores)
            historical_mean = np.mean(historical_scores)
            
            # Calculate drift score
            drift_score = abs(recent_mean - historical_mean) / max(historical_mean, 1)
            
            # Update drift metric
            DATA_DRIFT_SCORE.set(drift_score)
            
            drift_detected = drift_score > 0.15  # 15% change threshold
            
            return {
                'drift_detected': drift_detected,
                'drift_score': drift_score,
                'recent_mean': recent_mean,
                'historical_mean': historical_mean,
                'sample_sizes': {'recent': len(recent_data), 'historical': len(historical_data)}
            }
        
        except Exception as e:
            return {'drift_detected': False, 'error': str(e)}
    
    def get_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive data quality report"""
        try:
            if not self.data_buffer:
                return {'status': 'no_data', 'message': 'No data available for analysis'}
            
            recent_data = list(self.data_buffer)[-100:]  # Last 100 records
            
            # Calculate statistics
            quality_scores = [d['quality_score'] for d in recent_data]
            timestamps = [d['timestamp'] for d in recent_data]
            
            report = {
                'summary': {
                    'total_records': len(recent_data),
                    'avg_quality_score': np.mean(quality_scores),
                    'min_quality_score': np.min(quality_scores),
                    'max_quality_score': np.max(quality_scores),
                    'time_range': {
                        'start': min(timestamps).isoformat(),
                        'end': max(timestamps).isoformat()
                    }
                },
                'trends': {
                    'quality_trend': 'improving' if len(quality_scores) > 1 and quality_scores[-1] > quality_scores[0] else 'declining',
                    'data_volume_trend': 'increasing' if len(recent_data) > 50 else 'stable'
                },
                'issues': {
                    'low_quality_records': len([s for s in quality_scores if s < 70]),
                    'validation_errors': sum(1 for d in recent_data if d.get('validation_errors', 0) > 0),
                    'duplicate_warnings': sum(1 for d in recent_data if 'duplicate' in str(d.get('warnings', [])))
                },
                'drift_analysis': self.detect_data_drift()
            }
            
            return report
        
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

# Global data quality monitor instance
data_quality_monitor = DataQualityMonitor()

def validate_data_quality(func):
    """Decorator to validate data quality for API endpoints"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Get request data
            request_data = {}
            
            # Extract data from request
            if request.files:
                request_data.update(request.files.to_dict())
            if request.form:
                request_data.update(request.form.to_dict())
            if request.get_json():
                request_data.update(request.get_json())
            
            # Add metadata
            request_data['timestamp'] = datetime.now().isoformat()
            request_data['ip_address'] = request.remote_addr
            request_data['user_agent'] = request.headers.get('User-Agent', '')
            
            # Validate data quality
            validation_result = data_quality_monitor.validate_request_data(request_data)
            
            # Store validation result in request context for later use
            request.data_quality = validation_result
            
            # If data quality is too low, you might want to reject the request
            if validation_result['quality_score'] < 30:
                return {
                    'error': 'Data quality too low',
                    'quality_score': validation_result['quality_score'],
                    'errors': validation_result['errors']
                }, 400
            
            return func(*args, **kwargs)
        
        except Exception as e:
            return {'error': f'Data quality validation failed: {str(e)}'}, 500
    
    return wrapper
            
            return report
        
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

# Global data quality monitor instance
data_quality_monitor = DataQualityMonitor()

def validate_data_quality(func):
    """Decorator to validate data quality for API endpoints"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Get request data
            request_data = {}
            
            # Extract data from request
            if request.files:
                request_data.update(request.files.to_dict())
            if request.form:
                request_data.update(request.form.to_dict())
            if request.get_json():
                request_data.update(request.get_json())
            
            # Add metadata
            request_data['timestamp'] = datetime.now().isoformat()
            request_data['ip_address'] = request.remote_addr
            request_data['user_agent'] = request.headers.get('User-Agent', '')
            
            # Validate data quality
            validation_result = data_quality_monitor.validate_request_data(request_data)
            
            # Store validation result in request context for later use
            request.data_quality = validation_result
            
            # If data quality is too low, you might want to reject the request
            if validation_result['quality_score'] < 30:
                return {
                    'error': 'Data quality too low',
                    'quality_score': validation_result['quality_score'],
                    'errors': validation_result['errors']
                }, 400
            
            return func(*args, **kwargs)
        
        except Exception as e:
            return {'error': f'Data quality validation failed: {str(e)}'}, 500
    
    return wrapper
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")

class QueueMonitor:
    """Comprehensive queue monitoring system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.metrics_collector = MetricsCollector(
            max_history=self.config.get('max_history', 10000)
        )
        self.alert_manager = AlertManager()
        
        # Queue metrics tracking
        self._queue_metrics: Dict[str, QueueMetrics] = {}
        self._lock = threading.RLock()
        
        # Performance tracking
        self._performance_window = deque(maxlen=1000)  # Last 1000 operations
        
        # Monitoring thread
        self._monitoring_active = False
        self._monitoring_thread = None
        
        # Setup default alerts
        self._setup_default_alerts()
    
    def _setup_default_alerts(self):
        """Setup default alert rules"""
        default_alerts = [
            Alert(
                name="high_queue_size",
                level=AlertLevel.WARNING,
                condition="queue_size >",
                threshold=1000,
                message="Queue size is getting large"
            ),
            Alert(
                name="high_error_rate",
                level=AlertLevel.ERROR,
                condition="error_rate >",
                threshold=10.0,
                message="Error rate is too high"
            ),
            Alert(
                name="low_throughput",
                level=AlertLevel.WARNING,
                condition="throughput <",
                threshold=1.0,
                message="Queue throughput is too low"
            ),
            Alert(
                name="high_processing_time",
                level=AlertLevel.WARNING,
                condition="avg_processing_time >",
                threshold=30000,  # 30 seconds in ms
                message="Average processing time is too high"
            ),
            # Rate limiting alerts
            Alert(
                name="high_rate_limit_violations",
                level=AlertLevel.WARNING,
                condition="rate_limit_violations >",
                threshold=100,
                message="High rate limit violation rate detected"
            ),
            Alert(
                name="many_blocked_users",
                level=AlertLevel.ERROR,
                condition="blocked_users >",
                threshold=50,
                message="Too many users are blocked"
            ),
            Alert(
                name="rate_limit_bypass_usage",
                level=AlertLevel.INFO,
                condition="bypass_usage >",
                threshold=10,
                message="High rate limit bypass usage detected"
            )
        ]
        
        for alert in default_alerts:
            self.alert_manager.add_alert(alert)
    
    def start_monitoring(self, interval_seconds: int = 30):
        """Start background monitoring"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._monitoring_thread.start()
        logger.info("Queue monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        logger.info("Queue monitoring stopped")
    
    def _monitoring_loop(self, interval_seconds: int):
        """Background monitoring loop"""
        while self._monitoring_active:
            try:
                self._collect_metrics()
                self.alert_manager.check_alerts(self.metrics_collector)
                time.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(5)
    
    def _collect_metrics(self):
        """Collect current metrics from all queues"""
        with self._lock:
            for queue_name, metrics in self._queue_metrics.items():
                labels = {"queue": queue_name}
                
                # Record queue metrics
                self.metrics_collector.set_gauge("queue_size", metrics.pending_tasks, labels)
                self.metrics_collector.set_gauge("running_tasks", metrics.running_tasks, labels)
                self.metrics_collector.set_gauge("completed_tasks", metrics.completed_tasks, labels)
                self.metrics_collector.set_gauge("failed_tasks", metrics.failed_tasks, labels)
                self.metrics_collector.set_gauge("error_rate", metrics.error_rate, labels)
                self.metrics_collector.set_gauge("throughput", metrics.throughput, labels)
                self.metrics_collector.set_gauge("avg_wait_time", metrics.average_wait_time, labels)
                self.metrics_collector.set_gauge("avg_processing_time", metrics.average_processing_time, labels)
            
            # Collect rate limiting metrics if available
            try:
                from security_config import get_rate_limiter
                rate_limiter = get_rate_limiter()
                rate_limit_stats = rate_limiter.get_analytics(1)  # Last hour
                
                # Rate limiting metrics
                rate_limit_analytics = rate_limit_stats.get('rate_limit_analytics', {})
                current_stats = rate_limit_analytics.get('current_stats', {})
                
                self.metrics_collector.set_gauge("rate_limit_total_requests", current_stats.get('total_requests', 0))
                self.metrics_collector.set_gauge("rate_limit_blocked_requests", current_stats.get('blocked_requests', 0))
                self.metrics_collector.set_gauge("rate_limit_active_clients", rate_limit_stats.get('active_clients', 0))
                self.metrics_collector.set_gauge("rate_limit_blocked_clients", rate_limit_stats.get('blocked_clients', 0))
                
                # Calculate violation rate
                total_requests = current_stats.get('total_requests', 0)
                blocked_requests = current_stats.get('blocked_requests', 0)
                violation_rate = (blocked_requests / total_requests * 100) if total_requests > 0 else 0
                self.metrics_collector.set_gauge("rate_limit_violation_rate", violation_rate)
                
                # Dynamic adjustment metrics
                dynamic_adjustments = rate_limit_stats.get('dynamic_adjustments', {})
                for user_type, adjustment_stats in dynamic_adjustments.items():
                    labels = {"user_type": user_type}
                    self.metrics_collector.set_gauge("rate_limit_load_factor", 
                                                    adjustment_stats.get('current_load_factor', 1.0), labels)
                
            except Exception as e:
                logger.debug(f"Could not collect rate limiting metrics: {e}")
    
    def update_queue_metrics(self, queue_name: str, **kwargs):
        """Update metrics for a specific queue"""
        with self._lock:
            if queue_name not in self._queue_metrics:
                self._queue_metrics[queue_name] = QueueMetrics(queue_name=queue_name)
            
            metrics = self._queue_metrics[queue_name]
            
            # Update metrics
            for key, value in kwargs.items():
                if hasattr(metrics, key):
                    setattr(metrics, key, value)
            
            metrics.last_updated = datetime.now()
            
            # Record performance data
            self._record_performance(queue_name, metrics)
    
    def _record_performance(self, queue_name: str, metrics: QueueMetrics):
        """Record performance data point"""
        performance_data = {
            'timestamp': datetime.now(),
            'queue': queue_name,
            'throughput': metrics.throughput,
            'error_rate': metrics.error_rate,
            'avg_processing_time': metrics.average_processing_time,
            'pending_tasks': metrics.pending_tasks
        }
        
        self._performance_window.append(performance_data)
    
    def record_task_event(self, queue_name: str, event_type: str, duration_ms: Optional[float] = None):
        """Record task-related events"""
        labels = {"queue": queue_name, "event": event_type}
        
        if event_type == "completed":
            self.metrics_collector.record_counter("tasks_completed", 1.0, labels)
            if duration_ms is not None:
                self.metrics_collector.record_timer("task_duration", duration_ms, labels)
        elif event_type == "failed":
            self.metrics_collector.record_counter("tasks_failed", 1.0, labels)
        elif event_type == "started":
            self.metrics_collector.record_counter("tasks_started", 1.0, labels)
        elif event_type == "queued":
            self.metrics_collector.record_counter("tasks_queued", 1.0, labels)
    
    def get_queue_metrics(self, queue_name: str) -> Optional[QueueMetrics]:
        """Get metrics for a specific queue"""
        with self._lock:
            return self._queue_metrics.get(queue_name)
    
    def get_all_queue_metrics(self) -> Dict[str, QueueMetrics]:
        """Get metrics for all queues"""
        with self._lock:
            return self._queue_metrics.copy()
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter performance data
        recent_data = [
            data for data in self._performance_window
            if data['timestamp'] >= cutoff_time
        ]
        
        if not recent_data:
            return {}
        
        # Calculate summary statistics
        throughputs = [data['throughput'] for data in recent_data]
        error_rates = [data['error_rate'] for data in recent_data]
        processing_times = [data['avg_processing_time'] for data in recent_data]
        
        return {
            'period_hours': hours,
            'total_data_points': len(recent_data),
            'throughput': {
                'avg': statistics.mean(throughputs),
                'min': min(throughputs),
                'max': max(throughputs),
                'median': statistics.median(throughputs)
            },
            'error_rate': {
                'avg': statistics.mean(error_rates),
                'min': min(error_rates),
                'max': max(error_rates),
                'median': statistics.median(error_rates)
            },
            'processing_time': {
                'avg': statistics.mean(processing_times),
                'min': min(processing_times),
                'max': max(processing_times),
                'median': statistics.median(processing_times)
            }
        }
    
    def get_queue_analytics(self, queue_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get detailed analytics for a specific queue"""
        metrics = self.get_queue_metrics(queue_name)
        if not metrics:
            return {}
        
        # Get task duration percentiles
        duration_percentiles = self.metrics_collector.calculate_percentiles(
            "task_duration", labels={"queue": queue_name}
        )
        
        # Get task counts by event type
        task_events = {}
        for event_type in ["completed", "failed", "started", "queued"]:
            history = self.metrics_collector.get_metric_history(
                "tasks_completed" if event_type == "completed" else f"tasks_{event_type}",
                labels={"queue": queue_name}
            )
            task_events[event_type] = len(history)
        
        return {
            'queue_name': queue_name,
            'current_metrics': {
                'pending_tasks': metrics.pending_tasks,
                'running_tasks': metrics.running_tasks,
                'completed_tasks': metrics.completed_tasks,
                'failed_tasks': metrics.failed_tasks,
                'error_rate': metrics.error_rate,
                'throughput': metrics.throughput,
                'avg_wait_time': metrics.average_wait_time,
                'avg_processing_time': metrics.average_processing_time
            },
            'task_events': task_events,
            'duration_percentiles': duration_percentiles,
            'last_updated': metrics.last_updated.isoformat()
        }
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format"""
        all_metrics = self.metrics_collector.get_current_metrics()
        
        if format.lower() == "json":
            return json.dumps(all_metrics, indent=2, default=str)
        elif format.lower() == "prometheus":
            return self._export_prometheus_format(all_metrics)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_prometheus_format(self, metrics: Dict[str, Any]) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        for metric_name, metric_data in metrics.items():
            metric_type = metric_data["type"]
            value = metric_data["value"]
            
            # Add metric type
            if metric_type == "counter":
                lines.append(f"# TYPE {metric_name} counter")
            elif metric_type == "gauge":
                lines.append(f"# TYPE {metric_name} gauge")
            
            # Add metric value
            lines.append(f"{metric_name} {value}")
        
        return "\n".join(lines)
    
    def reset_metrics(self):
        """Reset all metrics"""
        with self._lock:
            self.metrics_collector = MetricsCollector(
                max_history=self.config.get('max_history', 10000)
            )
            self._queue_metrics.clear()
            self._performance_window.clear()
        
        logger.info("All metrics reset")

# Alert handlers
def console_alert_handler(alert: Alert):
    """Simple console alert handler"""
    print(f"[{alert.level.value.upper()}] {alert.name}: {alert.message}")

def log_alert_handler(alert: Alert):
    """Logging alert handler"""
    if alert.level == AlertLevel.INFO:
        logger.info(f"Alert: {alert.name} - {alert.message}")
    elif alert.level == AlertLevel.WARNING:
        logger.warning(f"Alert: {alert.name} - {alert.message}")
    elif alert.level == AlertLevel.ERROR:
        logger.error(f"Alert: {alert.name} - {alert.message}")
    elif alert.level == AlertLevel.CRITICAL:
        logger.critical(f"Alert: {alert.name} - {alert.message}")

class QueueDashboard:
    """Simple dashboard data provider for queue monitoring"""
    
    def __init__(self, monitor: QueueMonitor):
        self.monitor = monitor
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard display"""
        queue_metrics = self.monitor.get_all_queue_metrics()
        performance_summary = self.monitor.get_performance_summary()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'queues': {
                name: {
                    'pending_tasks': metrics.pending_tasks,
                    'running_tasks': metrics.running_tasks,
                    'completed_tasks': metrics.completed_tasks,
                    'failed_tasks': metrics.failed_tasks,
                    'error_rate': metrics.error_rate,
                    'throughput': metrics.throughput,
                    'avg_processing_time': metrics.average_processing_time
                }
                for name, metrics in queue_metrics.items()
            },
            'performance_summary': performance_summary,
            'total_queues': len(queue_metrics),
            'monitoring_active': self.monitor._monitoring_active
        }
