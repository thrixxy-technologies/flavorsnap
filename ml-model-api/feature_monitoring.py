#!/usr/bin/env python3
"""
Feature Monitoring System for FlavorSnap ML Model API
Comprehensive feature monitoring, drift detection, and performance tracking
"""

import os
import time
import logging
import numpy as np
import pandas as pd
import json
import sqlite3
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import threading
import queue
import hashlib
from pathlib import Path
import pickle
from scipy import stats
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import seaborn as sns

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MonitoringStatus(Enum):
    """Monitoring system status"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class DriftType(Enum):
    """Types of data drift"""
    COVARIATE_SHIFT = "covariate_shift"
    PRIOR_PROBABILITY_SHIFT = "prior_probability_shift"
    CONCEPT_DRIFT = "concept_drift"
    FEATURE_DRIFT = "feature_drift"
    PERFORMANCE_DRIFT = "performance_drift"

@dataclass
class MonitoringConfig:
    """Feature monitoring configuration"""
    # Monitoring settings
    enable_real_time_monitoring: bool = True
    monitoring_interval: int = 300  # seconds
    batch_size: int = 100
    max_history_days: int = 30
    
    # Drift detection settings
    drift_detection_methods: List[str] = None
    drift_threshold: float = 0.05
    statistical_test: str = "ks"  # "ks", "chi2", "wasserstein"
    window_size: int = 1000
    reference_window_size: int = 2000
    
    # Performance monitoring
    performance_metrics: List[str] = None
    performance_threshold: float = 0.1  # 10% degradation
    baseline_performance: Dict[str, float] = None
    
    # Alert settings
    enable_alerts: bool = True
    alert_thresholds: Dict[str, float] = None
    alert_cooldown: int = 3600  # seconds
    
    # Storage settings
    database_path: str = "feature_monitoring.db"
    log_directory: str = "monitoring_logs"
    plot_directory: str = "monitoring_plots"
    
    # Visualization settings
    enable_plotting: bool = True
    plot_frequency: int = 6  # every 6 monitoring cycles
    plot_format: str = "png"
    plot_dpi: int = 300
    
    def __post_init__(self):
        if self.drift_detection_methods is None:
            self.drift_detection_methods = ["statistical", "model_based", "distribution_based"]
        if self.performance_metrics is None:
            self.performance_metrics = ["accuracy", "precision", "recall", "f1_score"]
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                "drift_probability": 0.7,
                "performance_degradation": 0.15,
                "feature_correlation": 0.9
            }
        if self.baseline_performance is None:
            self.baseline_performance = {
                "accuracy": 0.85,
                "precision": 0.85,
                "recall": 0.85,
                "f1_score": 0.85
            }

@dataclass
class FeatureMetric:
    """Feature metric data point"""
    feature_name: str
    timestamp: datetime
    metric_type: str
    value: float
    metadata: Dict[str, Any]

@dataclass
class DriftDetectionResult:
    """Drift detection result"""
    feature_name: str
    drift_type: DriftType
    drift_score: float
    p_value: float
    threshold: float
    is_drift_detected: bool
    detection_method: str
    timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    model_id: str
    timestamp: datetime
    metric_name: str
    value: float
    dataset_split: str  # "train", "validation", "test"
    metadata: Dict[str, Any]

@dataclass
class MonitoringAlert:
    """Monitoring alert"""
    alert_id: str
    level: AlertLevel
    feature_name: Optional[str]
    alert_type: str
    message: str
    timestamp: datetime
    metadata: Dict[str, Any]
    resolved: bool = False

class FeatureMonitoringSystem:
    """Advanced feature monitoring system"""
    
    def __init__(self, config: MonitoringConfig = None):
        self.config = config or MonitoringConfig()
        self.logger = logging.getLogger(__name__)
        
        # Monitoring state
        self.status = MonitoringStatus.STOPPED
        self.monitoring_thread = None
        self.monitoring_active = False
        
        # Data storage
        self.feature_metrics = []
        self.performance_metrics = []
        self.drift_results = []
        self.alerts = []
        
        # Reference data
        self.reference_features = None
        self.reference_labels = None
        self.reference_timestamp = None
        
        # Current data window
        self.current_features = []
        self.current_labels = []
        
        # Alert queue
        self.alert_queue = queue.Queue()
        
        # Database
        self.db_path = self.config.database_path
        self._init_database()
        
        # Directories
        self.log_dir = Path(self.config.log_directory)
        self.log_dir.mkdir(exist_ok=True)
        self.plot_dir = Path(self.config.plot_directory)
        self.plot_dir.mkdir(exist_ok=True)
        
        # Thread safety
        self.data_lock = threading.Lock()
        self.alert_lock = threading.Lock()
        
        logger.info("FeatureMonitoringSystem initialized")
    
    def _init_database(self):
        """Initialize monitoring database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Feature metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feature_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feature_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    metadata TEXT
                )
            ''')
            
            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    dataset_split TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            # Drift detection results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS drift_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feature_name TEXT NOT NULL,
                    drift_type TEXT NOT NULL,
                    drift_score REAL NOT NULL,
                    p_value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    is_drift_detected BOOLEAN NOT NULL,
                    detection_method TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            # Alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    level TEXT NOT NULL,
                    feature_name TEXT,
                    alert_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Monitoring status table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monitoring_status (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    status TEXT NOT NULL,
                    last_update TEXT NOT NULL,
                    metadata TEXT,
                    UNIQUE (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Monitoring database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def set_reference_data(self, X: Union[np.ndarray, pd.DataFrame], 
                          y: Union[np.ndarray, pd.Series] = None):
        """Set reference data for drift detection"""
        try:
            with self.data_lock:
                self.reference_features = X.copy() if hasattr(X, 'copy') else X
                self.reference_labels = y.copy() if y is not None and hasattr(y, 'copy') else y
                self.reference_timestamp = datetime.now()
                
                # Calculate baseline statistics
                self._calculate_baseline_statistics()
                
                logger.info(f"Reference data set with {len(X)} samples")
                
        except Exception as e:
            logger.error(f"Failed to set reference data: {str(e)}")
            raise
    
    def _calculate_baseline_statistics(self):
        """Calculate baseline statistics for reference data"""
        try:
            if self.reference_features is None:
                return
            
            # Convert to DataFrame if needed
            if isinstance(self.reference_features, np.ndarray):
                if hasattr(self, 'feature_names'):
                    X_df = pd.DataFrame(self.reference_features, columns=self.feature_names)
                else:
                    X_df = pd.DataFrame(self.reference_features, columns=[f"feature_{i}" for i in range(self.reference_features.shape[1])])
            else:
                X_df = self.reference_features.copy()
            
            # Calculate statistics for each feature
            self.baseline_stats = {}
            
            for column in X_df.columns:
                feature_data = X_df[column].dropna()
                
                self.baseline_stats[column] = {
                    'mean': feature_data.mean(),
                    'std': feature_data.std(),
                    'min': feature_data.min(),
                    'max': feature_data.max(),
                    'median': feature_data.median(),
                    'q25': feature_data.quantile(0.25),
                    'q75': feature_data.quantile(0.75),
                    'skewness': feature_data.skew(),
                    'kurtosis': feature_data.kurtosis()
                }
            
            logger.info(f"Baseline statistics calculated for {len(self.baseline_stats)} features")
            
        except Exception as e:
            logger.error(f"Failed to calculate baseline statistics: {str(e)}")
    
    def start_monitoring(self):
        """Start the monitoring system"""
        try:
            if self.status == MonitoringStatus.ACTIVE:
                logger.warning("Monitoring already active")
                return
            
            if self.reference_features is None:
                raise ValueError("Reference data not set. Call set_reference_data() first.")
            
            self.monitoring_active = True
            self.status = MonitoringStatus.ACTIVE
            
            # Start monitoring thread
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            # Update database status
            self._update_status_in_db()
            
            logger.info("Feature monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {str(e)}")
            self.status = MonitoringStatus.ERROR
            raise
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        try:
            self.monitoring_active = False
            self.status = MonitoringStatus.STOPPED
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=10)
            
            # Update database status
            self._update_status_in_db()
            
            logger.info("Feature monitoring stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {str(e)}")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        try:
            cycle_count = 0
            
            while self.monitoring_active:
                try:
                    self.logger.info(f"Monitoring cycle {cycle_count + 1}")
                    
                    # Collect current metrics
                    self._collect_feature_metrics()
                    
                    # Detect drift
                    if len(self.current_features) >= self.config.window_size:
                        self._detect_drift()
                    
                    # Monitor performance
                    self._monitor_performance()
                    
                    # Process alerts
                    self._process_alerts()
                    
                    # Generate plots
                    if self.config.enable_plotting and cycle_count % self.config.plot_frequency == 0:
                        self._generate_monitoring_plots()
                    
                    # Clean old data
                    self._cleanup_old_data()
                    
                    cycle_count += 1
                    
                    # Wait for next cycle
                    time.sleep(self.config.monitoring_interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in monitoring cycle: {str(e)}")
                    time.sleep(self.config.monitoring_interval)
                    
        except Exception as e:
            self.logger.error(f"Monitoring loop failed: {str(e)}")
            self.status = MonitoringStatus.ERROR
    
    def add_data_point(self, X: Union[np.ndarray, pd.DataFrame], 
                       y: Union[np.ndarray, pd.Series] = None,
                       model_predictions: np.ndarray = None,
                       true_labels: np.ndarray = None):
        """Add new data point for monitoring"""
        try:
            with self.data_lock:
                # Add to current window
                if isinstance(X, np.ndarray):
                    X_df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])
                else:
                    X_df = X.copy()
                
                self.current_features.append(X_df)
                
                if y is not None:
                    if isinstance(y, np.ndarray):
                        self.current_labels.append(pd.Series(y))
                    else:
                        self.current_labels.append(y.copy())
                
                # Calculate and store feature metrics
                timestamp = datetime.now()
                
                for column in X_df.columns:
                    value = X_df[column].iloc[0] if len(X_df) == 1 else X_df[column].mean()
                    
                    metric = FeatureMetric(
                        feature_name=column,
                        timestamp=timestamp,
                        metric_type="value",
                        value=value,
                        metadata={"source": "real_time"}
                    )
                    
                    self.feature_metrics.append(metric)
                    self._save_feature_metric(metric)
                
                # Calculate performance metrics if available
                if model_predictions is not None and true_labels is not None:
                    self._calculate_performance_metrics(
                        model_predictions, true_labels, timestamp
                    )
                
                # Maintain window size
                if len(self.current_features) > self.config.window_size:
                    self.current_features.pop(0)
                    if self.current_labels:
                        self.current_labels.pop(0)
                
        except Exception as e:
            logger.error(f"Failed to add data point: {str(e)}")
    
    def _collect_feature_metrics(self):
        """Collect feature metrics from current data"""
        try:
            if not self.current_features:
                return
            
            timestamp = datetime.now()
            
            # Aggregate current data
            current_df = pd.concat(self.current_features, ignore_index=True)
            
            for column in current_df.columns:
                feature_data = current_df[column].dropna()
                
                if len(feature_data) == 0:
                    continue
                
                # Calculate various metrics
                metrics = {
                    "mean": feature_data.mean(),
                    "std": feature_data.std(),
                    "min": feature_data.min(),
                    "max": feature_data.max(),
                    "median": feature_data.median()
                }
                
                for metric_type, value in metrics.items():
                    metric = FeatureMetric(
                        feature_name=column,
                        timestamp=timestamp,
                        metric_type=metric_type,
                        value=value,
                        metadata={"source": "batch"}
                    )
                    
                    self.feature_metrics.append(metric)
                    self._save_feature_metric(metric)
            
        except Exception as e:
            logger.error(f"Failed to collect feature metrics: {str(e)}")
    
    def _detect_drift(self):
        """Detect drift in current data"""
        try:
            if self.reference_features is None or not self.current_features:
                return
            
            # Aggregate current data
            current_df = pd.concat(self.current_features, ignore_index=True)
            
            # Convert reference data to DataFrame if needed
            if isinstance(self.reference_features, np.ndarray):
                if hasattr(self, 'feature_names'):
                    ref_df = pd.DataFrame(self.reference_features, columns=self.feature_names)
                else:
                    ref_df = pd.DataFrame(self.reference_features, columns=[f"feature_{i}" for i in range(self.reference_features.shape[1])])
            else:
                ref_df = self.reference_features.copy()
            
            # Detect drift for each feature
            for column in current_df.columns:
                if column not in ref_df.columns:
                    continue
                
                ref_data = ref_df[column].dropna()
                cur_data = current_df[column].dropna()
                
                if len(ref_data) == 0 or len(cur_data) == 0:
                    continue
                
                # Apply drift detection methods
                for method in self.config.drift_detection_methods:
                    try:
                        drift_result = self._apply_drift_detection(
                            ref_data, cur_data, column, method
                        )
                        
                        if drift_result:
                            self.drift_results.append(drift_result)
                            self._save_drift_result(drift_result)
                            
                            # Generate alert if drift detected
                            if drift_result.is_drift_detected:
                                self._generate_drift_alert(drift_result)
                    
                    except Exception as e:
                        logger.error(f"Drift detection failed for {column} with {method}: {str(e)}")
                        continue
            
        except Exception as e:
            logger.error(f"Failed to detect drift: {str(e)}")
    
    def _apply_drift_detection(self, ref_data: pd.Series, cur_data: pd.Series, 
                             feature_name: str, method: str) -> Optional[DriftDetectionResult]:
        """Apply specific drift detection method"""
        try:
            timestamp = datetime.now()
            
            if method == "statistical":
                # Kolmogorov-Smirnov test
                if self.config.statistical_test == "ks":
                    statistic, p_value = stats.ks_2samp(ref_data, cur_data)
                    drift_score = statistic
                elif self.config.statistical_test == "chi2":
                    # Chi-square test for categorical data
                    statistic, p_value = stats.chi2_contingency(
                        pd.crosstab(ref_data, cur_data)
                    )[:2]
                    drift_score = statistic
                else:
                    # Wasserstein distance
                    from scipy.stats import wasserstein_distance
                    drift_score = wasserstein_distance(ref_data, cur_data)
                    p_value = None  # No p-value for Wasserstein
                
                is_drift = p_value is not None and p_value < self.config.drift_threshold
                
                return DriftDetectionResult(
                    feature_name=feature_name,
                    drift_type=DriftType.FEATURE_DRIFT,
                    drift_score=drift_score,
                    p_value=p_value if p_value is not None else 0.0,
                    threshold=self.config.drift_threshold,
                    is_drift_detected=is_drift,
                    detection_method=method,
                    timestamp=timestamp,
                    metadata={
                        "test_type": self.config.statistical_test,
                        "ref_size": len(ref_data),
                        "cur_size": len(cur_data)
                    }
                )
            
            elif method == "model_based":
                # Model-based drift detection using classifier
                from sklearn.ensemble import RandomForestClassifier
                from sklearn.metrics import accuracy_score
                
                # Create labels for reference (0) and current (1) data
                combined_data = pd.concat([ref_data, cur_data]).values.reshape(-1, 1)
                labels = np.array([0] * len(ref_data) + [1] * len(cur_data))
                
                # Train classifier
                clf = RandomForestClassifier(n_estimators=50, random_state=42)
                clf.fit(combined_data, labels)
                
                # Calculate accuracy
                predictions = clf.predict(combined_data)
                accuracy = accuracy_score(labels, predictions)
                
                # Drift score is 1 - accuracy (higher means more drift)
                drift_score = 1 - accuracy
                p_value = None  # No p-value for this method
                is_drift = drift_score > self.config.drift_threshold
                
                return DriftDetectionResult(
                    feature_name=feature_name,
                    drift_type=DriftType.COVARIATE_SHIFT,
                    drift_score=drift_score,
                    p_value=p_value if p_value is not None else 0.0,
                    threshold=self.config.drift_threshold,
                    is_drift_detected=is_drift,
                    detection_method=method,
                    timestamp=timestamp,
                    metadata={
                        "accuracy": accuracy,
                        "ref_size": len(ref_data),
                        "cur_size": len(cur_data)
                    }
                )
            
            elif method == "distribution_based":
                # Distribution-based drift detection
                ref_mean, ref_std = ref_data.mean(), ref_data.std()
                cur_mean, cur_std = cur_data.mean(), cur_data.std()
                
                # Calculate distribution distance
                mean_diff = abs(ref_mean - cur_mean) / (ref_std + 1e-8)
                std_diff = abs(ref_std - cur_std) / (ref_std + 1e-8)
                
                drift_score = (mean_diff + std_diff) / 2
                p_value = None
                is_drift = drift_score > self.config.drift_threshold
                
                return DriftDetectionResult(
                    feature_name=feature_name,
                    drift_type=DriftType.FEATURE_DRIFT,
                    drift_score=drift_score,
                    p_value=p_value if p_value is not None else 0.0,
                    threshold=self.config.drift_threshold,
                    is_drift_detected=is_drift,
                    detection_method=method,
                    timestamp=timestamp,
                    metadata={
                        "ref_mean": ref_mean,
                        "ref_std": ref_std,
                        "cur_mean": cur_mean,
                        "cur_std": cur_std,
                        "ref_size": len(ref_data),
                        "cur_size": len(cur_data)
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to apply {method} drift detection: {str(e)}")
            return None
    
    def _monitor_performance(self):
        """Monitor model performance"""
        try:
            # This would be called with actual performance data
            # For now, we'll check if there are recent performance metrics
            recent_metrics = [
                m for m in self.performance_metrics
                if m.timestamp > datetime.now() - timedelta(hours=1)
            ]
            
            if not recent_metrics:
                return
            
            # Check for performance degradation
            for metric_name in self.config.performance_metrics:
                metric_values = [m.value for m in recent_metrics if m.metric_name == metric_name]
                
                if len(metric_values) >= 5:  # Need enough data points
                    current_avg = np.mean(metric_values[-5:])  # Last 5 measurements
                    baseline = self.config.baseline_performance.get(metric_name, 0.8)
                    
                    if baseline > 0:
                        degradation = (baseline - current_avg) / baseline
                        
                        if degradation > self.config.performance_threshold:
                            self._generate_performance_alert(metric_name, current_avg, baseline, degradation)
            
        except Exception as e:
            logger.error(f"Failed to monitor performance: {str(e)}")
    
    def _calculate_performance_metrics(self, predictions: np.ndarray, 
                                      true_labels: np.ndarray, timestamp: datetime):
        """Calculate performance metrics"""
        try:
            metrics = {}
            
            if len(np.unique(true_labels)) > 2:  # Multi-class
                metrics['accuracy'] = accuracy_score(true_labels, predictions)
                metrics['precision'] = precision_score(true_labels, predictions, average='macro', zero_division=0)
                metrics['recall'] = recall_score(true_labels, predictions, average='macro', zero_division=0)
                metrics['f1_score'] = f1_score(true_labels, predictions, average='macro', zero_division=0)
            else:  # Binary
                metrics['accuracy'] = accuracy_score(true_labels, predictions)
                metrics['precision'] = precision_score(true_labels, predictions, zero_division=0)
                metrics['recall'] = recall_score(true_labels, predictions, zero_division=0)
                metrics['f1_score'] = f1_score(true_labels, predictions, zero_division=0)
            
            # Store performance metrics
            for metric_name, value in metrics.items():
                perf_metric = PerformanceMetric(
                    model_id="current_model",  # Would be actual model ID
                    timestamp=timestamp,
                    metric_name=metric_name,
                    value=value,
                    dataset_split="real_time",
                    metadata={"source": "monitoring"}
                )
                
                self.performance_metrics.append(perf_metric)
                self._save_performance_metric(perf_metric)
            
        except Exception as e:
            logger.error(f"Failed to calculate performance metrics: {str(e)}")
    
    def _generate_drift_alert(self, drift_result: DriftDetectionResult):
        """Generate drift alert"""
        try:
            if not self.config.enable_alerts:
                return
            
            alert_id = str(uuid.uuid4())
            
            # Determine alert level
            if drift_result.drift_score > 2 * self.config.drift_threshold:
                level = AlertLevel.CRITICAL
            elif drift_result.drift_score > 1.5 * self.config.drift_threshold:
                level = AlertLevel.WARNING
            else:
                level = AlertLevel.INFO
            
            message = (f"Drift detected in feature '{drift_result.feature_name}' "
                      f"using {drift_result.detection_method} method. "
                      f"Drift score: {drift_result.drift_score:.4f}, "
                      f"Threshold: {drift_result.threshold:.4f}")
            
            alert = MonitoringAlert(
                alert_id=alert_id,
                level=level,
                feature_name=drift_result.feature_name,
                alert_type="drift_detection",
                message=message,
                timestamp=drift_result.timestamp,
                metadata={
                    "drift_result": asdict(drift_result)
                }
            )
            
            self.alerts.append(alert)
            self._save_alert(alert)
            
            logger.warning(f"Drift alert generated: {message}")
            
        except Exception as e:
            logger.error(f"Failed to generate drift alert: {str(e)}")
    
    def _generate_performance_alert(self, metric_name: str, current_value: float, 
                                  baseline: float, degradation: float):
        """Generate performance alert"""
        try:
            if not self.config.enable_alerts:
                return
            
            alert_id = str(uuid.uuid4())
            
            # Determine alert level
            if degradation > 2 * self.config.performance_threshold:
                level = AlertLevel.CRITICAL
            elif degradation > 1.5 * self.config.performance_threshold:
                level = AlertLevel.WARNING
            else:
                level = AlertLevel.INFO
            
            message = (f"Performance degradation detected for {metric_name}. "
                      f"Current: {current_value:.4f}, Baseline: {baseline:.4f}, "
                      f"Degradation: {degradation:.2%}")
            
            alert = MonitoringAlert(
                alert_id=alert_id,
                level=level,
                feature_name=None,
                alert_type="performance_degradation",
                message=message,
                timestamp=datetime.now(),
                metadata={
                    "metric_name": metric_name,
                    "current_value": current_value,
                    "baseline": baseline,
                    "degradation": degradation
                }
            )
            
            self.alerts.append(alert)
            self._save_alert(alert)
            
            logger.warning(f"Performance alert generated: {message}")
            
        except Exception as e:
            logger.error(f"Failed to generate performance alert: {str(e)}")
    
    def _process_alerts(self):
        """Process pending alerts"""
        try:
            while not self.alert_queue.empty():
                try:
                    alert = self.alert_queue.get_nowait()
                    # Process alert (e.g., send notification, log, etc.)
                    self._handle_alert(alert)
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"Failed to process alert: {str(e)}")
            
        except Exception as e:
            logger.error(f"Failed to process alerts: {str(e)}")
    
    def _handle_alert(self, alert: MonitoringAlert):
        """Handle individual alert"""
        try:
            # Log alert
            log_message = f"[{alert.level.value.upper()}] {alert.message}"
            
            if alert.level == AlertLevel.CRITICAL or alert.level == AlertLevel.EMERGENCY:
                logger.critical(log_message)
            elif alert.level == AlertLevel.WARNING:
                logger.warning(log_message)
            else:
                logger.info(log_message)
            
            # Additional alert handling can be added here:
            # - Send email notifications
            # - Push to monitoring systems
            # - Trigger automated responses
            
        except Exception as e:
            logger.error(f"Failed to handle alert: {str(e)}")
    
    def _generate_monitoring_plots(self):
        """Generate monitoring visualization plots"""
        try:
            if not self.config.enable_plotting:
                return
            
            # Plot 1: Feature value trends
            self._plot_feature_trends()
            
            # Plot 2: Drift detection results
            self._plot_drift_results()
            
            # Plot 3: Performance metrics
            self._plot_performance_metrics()
            
            # Plot 4: Alert timeline
            self._plot_alert_timeline()
            
            logger.info("Monitoring plots generated")
            
        except Exception as e:
            logger.error(f"Failed to generate monitoring plots: {str(e)}")
    
    def _plot_feature_trends(self):
        """Plot feature value trends over time"""
        try:
            # Get recent feature metrics
            recent_metrics = [
                m for m in self.feature_metrics
                if m.timestamp > datetime.now() - timedelta(days=7)
                and m.metric_type == "mean"
            ]
            
            if not recent_metrics:
                return
            
            # Convert to DataFrame
            df = pd.DataFrame([
                {
                    "feature": m.feature_name,
                    "timestamp": m.timestamp,
                    "value": m.value
                }
                for m in recent_metrics
            ])
            
            # Plot top features
            top_features = df.groupby("feature")["value"].count().nlargest(10).index.tolist()
            
            plt.figure(figsize=(15, 10))
            
            for i, feature in enumerate(top_features):
                feature_data = df[df["feature"] == feature]
                plt.subplot(5, 2, i + 1)
                plt.plot(feature_data["timestamp"], feature_data["value"])
                plt.title(feature)
                plt.xticks(rotation=45)
            
            plt.tight_layout()
            plot_path = self.plot_dir / f"feature_trends.{self.config.plot_format}"
            plt.savefig(plot_path, dpi=self.config.plot_dpi, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            logger.error(f"Failed to plot feature trends: {str(e)}")
    
    def _plot_drift_results(self):
        """Plot drift detection results"""
        try:
            if not self.drift_results:
                return
            
            # Get recent drift results
            recent_drift = [
                d for d in self.drift_results
                if d.timestamp > datetime.now() - timedelta(days=7)
            ]
            
            if not recent_drift:
                return
            
            # Convert to DataFrame
            df = pd.DataFrame([
                {
                    "feature": d.feature_name,
                    "timestamp": d.timestamp,
                    "drift_score": d.drift_score,
                    "method": d.detection_method,
                    "is_drift": d.is_drift_detected
                }
                for d in recent_drift
            ])
            
            # Plot drift scores over time
            plt.figure(figsize=(15, 8))
            
            for method in df["method"].unique():
                method_data = df[df["method"] == method]
                
                for feature in method_data["feature"].unique()[:5]:  # Top 5 features
                    feature_data = method_data[method_data["feature"] == feature]
                    plt.plot(feature_data["timestamp"], feature_data["drift_score"], 
                           label=f"{feature} ({method})", marker='o')
            
            plt.axhline(y=self.config.drift_threshold, color='r', linestyle='--', label='Threshold')
            plt.xlabel("Time")
            plt.ylabel("Drift Score")
            plt.title("Feature Drift Scores Over Time")
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            plot_path = self.plot_dir / f"drift_scores.{self.config.plot_format}"
            plt.savefig(plot_path, dpi=self.config.plot_dpi, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            logger.error(f"Failed to plot drift results: {str(e)}")
    
    def _plot_performance_metrics(self):
        """Plot performance metrics over time"""
        try:
            if not self.performance_metrics:
                return
            
            # Get recent performance metrics
            recent_perf = [
                p for p in self.performance_metrics
                if p.timestamp > datetime.now() - timedelta(days=7)
            ]
            
            if not recent_perf:
                return
            
            # Convert to DataFrame
            df = pd.DataFrame([
                {
                    "timestamp": p.timestamp,
                    "metric": p.metric_name,
                    "value": p.value
                }
                for p in recent_perf
            ])
            
            # Plot each metric
            plt.figure(figsize=(15, 10))
            
            for i, metric in enumerate(df["metric"].unique()):
                metric_data = df[df["metric"] == metric]
                plt.subplot(2, 2, i + 1)
                plt.plot(metric_data["timestamp"], metric_data["value"], marker='o')
                
                # Add baseline
                baseline = self.config.baseline_performance.get(metric, 0.8)
                plt.axhline(y=baseline, color='r', linestyle='--', label=f'Baseline: {baseline:.3f}')
                
                plt.title(metric)
                plt.ylabel("Value")
                plt.legend()
                plt.xticks(rotation=45)
            
            plt.tight_layout()
            plot_path = self.plot_dir / f"performance_metrics.{self.config.plot_format}"
            plt.savefig(plot_path, dpi=self.config.plot_dpi, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            logger.error(f"Failed to plot performance metrics: {str(e)}")
    
    def _plot_alert_timeline(self):
        """Plot alert timeline"""
        try:
            if not self.alerts:
                return
            
            # Get recent alerts
            recent_alerts = [
                a for a in self.alerts
                if a.timestamp > datetime.now() - timedelta(days=7)
            ]
            
            if not recent_alerts:
                return
            
            # Convert to DataFrame
            df = pd.DataFrame([
                {
                    "timestamp": a.timestamp,
                    "level": a.level.value,
                    "type": a.alert_type,
                    "feature": a.feature_name or "N/A"
                }
                for a in recent_alerts
            ])
            
            # Create timeline plot
            plt.figure(figsize=(15, 6))
            
            colors = {
                "info": "blue",
                "warning": "orange", 
                "critical": "red",
                "emergency": "darkred"
            }
            
            for level in df["level"].unique():
                level_data = df[df["level"] == level]
                plt.scatter(level_data["timestamp"], 
                          [1] * len(level_data),
                          c=colors.get(level, "gray"),
                          label=level.upper(),
                          alpha=0.7,
                          s=100)
            
            plt.xlabel("Time")
            plt.ylabel("Alerts")
            plt.title("Alert Timeline (Last 7 Days)")
            plt.legend()
            plt.xticks(rotation=45)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            plot_path = self.plot_dir / f"alert_timeline.{self.config.plot_format}"
            plt.savefig(plot_path, dpi=self.config.plot_dpi, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            logger.error(f"Failed to plot alert timeline: {str(e)}")
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.max_history_days)
            
            # Clean feature metrics
            self.feature_metrics = [
                m for m in self.feature_metrics 
                if m.timestamp > cutoff_date
            ]
            
            # Clean performance metrics
            self.performance_metrics = [
                p for p in self.performance_metrics 
                if p.timestamp > cutoff_date
            ]
            
            # Clean drift results
            self.drift_results = [
                d for d in self.drift_results 
                if d.timestamp > cutoff_date
            ]
            
            # Clean old alerts (keep resolved alerts for shorter time)
            alert_cutoff = datetime.now() - timedelta(days=7)
            self.alerts = [
                a for a in self.alerts 
                if a.timestamp > alert_cutoff or not a.resolved
            ]
            
            # Clean database
            self._cleanup_database(cutoff_date)
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {str(e)}")
    
    def _cleanup_database(self, cutoff_date: datetime):
        """Clean up old database records"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_str = cutoff_date.isoformat()
            
            # Clean old tables
            cursor.execute("DELETE FROM feature_metrics WHERE timestamp < ?", (cutoff_str,))
            cursor.execute("DELETE FROM performance_metrics WHERE timestamp < ?", (cutoff_str,))
            cursor.execute("DELETE FROM drift_results WHERE timestamp < ?", (cutoff_str,))
            
            # Clean old resolved alerts
            cursor.execute("DELETE FROM alerts WHERE timestamp < ? AND resolved = TRUE", (cutoff_str,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to cleanup database: {str(e)}")
    
    def _save_feature_metric(self, metric: FeatureMetric):
        """Save feature metric to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO feature_metrics 
                (feature_name, timestamp, metric_type, value, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                metric.feature_name,
                metric.timestamp.isoformat(),
                metric.metric_type,
                metric.value,
                json.dumps(metric.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save feature metric: {str(e)}")
    
    def _save_performance_metric(self, metric: PerformanceMetric):
        """Save performance metric to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_metrics 
                (model_id, timestamp, metric_name, value, dataset_split, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                metric.model_id,
                metric.timestamp.isoformat(),
                metric.metric_name,
                metric.value,
                metric.dataset_split,
                json.dumps(metric.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save performance metric: {str(e)}")
    
    def _save_drift_result(self, drift_result: DriftDetectionResult):
        """Save drift result to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO drift_results 
                (feature_name, drift_type, drift_score, p_value, threshold,
                 is_drift_detected, detection_method, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                drift_result.feature_name,
                drift_result.drift_type.value,
                drift_result.drift_score,
                drift_result.p_value,
                drift_result.threshold,
                drift_result.is_drift_detected,
                drift_result.detection_method,
                drift_result.timestamp.isoformat(),
                json.dumps(drift_result.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save drift result: {str(e)}")
    
    def _save_alert(self, alert: MonitoringAlert):
        """Save alert to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO alerts 
                (alert_id, level, feature_name, alert_type, message, timestamp, metadata, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.alert_id,
                alert.level.value,
                alert.feature_name,
                alert.alert_type,
                alert.message,
                alert.timestamp.isoformat(),
                json.dumps(alert.metadata),
                alert.resolved
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save alert: {str(e)}")
    
    def _update_status_in_db(self):
        """Update monitoring status in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO monitoring_status 
                (id, status, last_update, metadata)
                VALUES (1, ?, ?, ?)
            ''', (
                self.status.value,
                datetime.now().isoformat(),
                json.dumps({
                    "config": asdict(self.config),
                    "reference_data_set": self.reference_timestamp.isoformat() if self.reference_timestamp else None
                })
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update status in database: {str(e)}")
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get monitoring system summary"""
        try:
            summary = {
                "status": self.status.value,
                "reference_data_set": self.reference_timestamp.isoformat() if self.reference_timestamp else None,
                "current_window_size": len(self.current_features),
                "total_feature_metrics": len(self.feature_metrics),
                "total_performance_metrics": len(self.performance_metrics),
                "total_drift_results": len(self.drift_results),
                "total_alerts": len(self.alerts),
                "unresolved_alerts": len([a for a in self.alerts if not a.resolved]),
                "recent_drift_detections": len([
                    d for d in self.drift_results 
                    if d.is_drift_detected and d.timestamp > datetime.now() - timedelta(hours=24)
                ]),
                "config": asdict(self.config)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get monitoring summary: {str(e)}")
            return {}
    
    def export_monitoring_data(self, output_path: str, format: str = "json"):
        """Export monitoring data"""
        try:
            export_data = {
                "summary": self.get_monitoring_summary(),
                "feature_metrics": [
                    {
                        "feature_name": m.feature_name,
                        "timestamp": m.timestamp.isoformat(),
                        "metric_type": m.metric_type,
                        "value": m.value,
                        "metadata": m.metadata
                    }
                    for m in self.feature_metrics[-1000:]  # Last 1000 metrics
                ],
                "performance_metrics": [
                    {
                        "model_id": p.model_id,
                        "timestamp": p.timestamp.isoformat(),
                        "metric_name": p.metric_name,
                        "value": p.value,
                        "dataset_split": p.dataset_split,
                        "metadata": p.metadata
                    }
                    for p in self.performance_metrics[-1000:]  # Last 1000 metrics
                ],
                "drift_results": [
                    {
                        "feature_name": d.feature_name,
                        "drift_type": d.drift_type.value,
                        "drift_score": d.drift_score,
                        "p_value": d.p_value,
                        "threshold": d.threshold,
                        "is_drift_detected": d.is_drift_detected,
                        "detection_method": d.detection_method,
                        "timestamp": d.timestamp.isoformat(),
                        "metadata": d.metadata
                    }
                    for d in self.drift_results[-100:]  # Last 100 drift results
                ],
                "alerts": [
                    {
                        "alert_id": a.alert_id,
                        "level": a.level.value,
                        "feature_name": a.feature_name,
                        "alert_type": a.alert_type,
                        "message": a.message,
                        "timestamp": a.timestamp.isoformat(),
                        "metadata": a.metadata,
                        "resolved": a.resolved
                    }
                    for a in self.alerts[-100:]  # Last 100 alerts
                ]
            }
            
            if format.lower() == "json":
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            
            elif format.lower() == "csv":
                # Export as multiple CSV files
                base_path = Path(output_path).with_suffix('')
                
                if export_data["feature_metrics"]:
                    pd.DataFrame(export_data["feature_metrics"]).to_csv(
                        f"{base_path}_feature_metrics.csv", index=False
                    )
                
                if export_data["performance_metrics"]:
                    pd.DataFrame(export_data["performance_metrics"]).to_csv(
                        f"{base_path}_performance_metrics.csv", index=False
                    )
                
                if export_data["drift_results"]:
                    pd.DataFrame(export_data["drift_results"]).to_csv(
                        f"{base_path}_drift_results.csv", index=False
                    )
                
                if export_data["alerts"]:
                    pd.DataFrame(export_data["alerts"]).to_csv(
                        f"{base_path}_alerts.csv", index=False
                    )
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Monitoring data exported to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export monitoring data: {str(e)}")
            raise

# Utility functions
def create_default_monitor() -> FeatureMonitoringSystem:
    """Create monitoring system with default configuration"""
    config = MonitoringConfig()
    return FeatureMonitoringSystem(config)

def create_custom_monitor(**kwargs) -> FeatureMonitoringSystem:
    """Create monitoring system with custom configuration"""
    config = MonitoringConfig(**kwargs)
    return FeatureMonitoringSystem(config)

if __name__ == "__main__":
    # Example usage
    monitor = create_default_monitor()
    
    # Generate sample reference data
    from sklearn.datasets import make_classification
    X_ref, y_ref = make_classification(n_samples=1000, n_features=20, n_informative=10, 
                                      n_redundant=5, random_state=42)
    
    try:
        # Set reference data
        monitor.set_reference_data(X_ref, y_ref)
        
        # Start monitoring
        monitor.start_monitoring()
        
        # Add some data points
        for i in range(10):
            X_new, y_new = make_classification(n_samples=10, n_features=20, n_informative=10, 
                                               n_redundant=5, random_state=42 + i)
            monitor.add_data_point(X_new, y_new)
            time.sleep(1)
        
        # Get summary
        summary = monitor.get_monitoring_summary()
        print(f"Monitoring summary: {summary}")
        
        # Export data
        monitor.export_monitoring_data("monitoring_data.json")
        
        # Stop monitoring
        monitor.stop_monitoring()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        monitor.stop_monitoring()
