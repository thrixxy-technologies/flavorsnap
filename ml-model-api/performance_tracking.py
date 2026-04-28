#!/usr/bin/env python3
"""
Performance Tracking System for FlavorSnap ML Model API
Comprehensive performance tracking, analysis, and reporting for feature engineering
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
import uuid
from pathlib import Path
import pickle
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Performance metric types"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CUSTOM = "custom"
    SYSTEM = "system"

class TrackingLevel(Enum):
    """Performance tracking levels"""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"

class AggregationType(Enum):
    """Aggregation types for metrics"""
    MEAN = "mean"
    MEDIAN = "median"
    MIN = "min"
    MAX = "max"
    STD = "std"
    SUM = "sum"

@dataclass
class TrackingConfig:
    """Performance tracking configuration"""
    # Tracking settings
    enable_real_time_tracking: bool = True
    tracking_level: TrackingLevel = TrackingLevel.DETAILED
    tracking_interval: int = 60  # seconds
    
    # Metrics to track
    classification_metrics: List[str] = None
    regression_metrics: List[str] = None
    system_metrics: List[str] = None
    
    # Data retention
    max_history_days: int = 30
    max_records: int = 100000
    
    # Aggregation settings
    enable_aggregation: bool = True
    aggregation_intervals: List[str] = None  # "1h", "6h", "1d", "1w"
    
    # Alert settings
    enable_alerts: bool = True
    alert_thresholds: Dict[str, Dict[str, float]] = None
    alert_cooldown: int = 300  # seconds
    
    # Visualization settings
    enable_plotting: bool = True
    plot_frequency: int = 6  # every 6 tracking cycles
    plot_format: str = "png"
    plot_dpi: int = 300
    
    # Storage settings
    database_path: str = "performance_tracking.db"
    export_directory: str = "performance_exports"
    
    # Performance baselines
    enable_baselines: bool = True
    baseline_window: int = 100  # samples
    baseline_update_frequency: int = 1000  # samples
    
    def __post_init__(self):
        if self.classification_metrics is None:
            self.classification_metrics = ["accuracy", "precision", "recall", "f1_score", "roc_auc"]
        if self.regression_metrics is None:
            self.regression_metrics = ["mse", "mae", "r2_score", "rmse"]
        if self.system_metrics is None:
            self.system_metrics = ["latency", "throughput", "memory_usage", "cpu_usage"]
        if self.aggregation_intervals is None:
            self.aggregation_intervals = ["1h", "6h", "1d"]
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                "classification": {
                    "accuracy": {"min": 0.7, "max_degradation": 0.1},
                    "f1_score": {"min": 0.7, "max_degradation": 0.1}
                },
                "regression": {
                    "r2_score": {"min": 0.7, "max_degradation": 0.1},
                    "mse": {"max_increase": 0.2}
                },
                "system": {
                    "latency": {"max": 1000},  # ms
                    "memory_usage": {"max": 0.8}  # 80%
                }
            }

@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    metric_id: str
    timestamp: datetime
    metric_type: MetricType
    metric_name: str
    value: float
    context: Dict[str, Any]
    metadata: Dict[str, Any]

@dataclass
class PerformanceBaseline:
    """Performance baseline"""
    baseline_id: str
    metric_name: str
    metric_type: MetricType
    baseline_value: float
    confidence_interval: Tuple[float, float]
    sample_size: int
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

@dataclass
class PerformanceAlert:
    """Performance alert"""
    alert_id: str
    metric_name: str
    alert_type: str
    severity: str
    message: str
    current_value: float
    baseline_value: Optional[float]
    threshold: float
    timestamp: datetime
    resolved: bool = False

@dataclass
class PerformanceReport:
    """Performance report"""
    report_id: str
    report_type: str
    start_time: datetime
    end_time: datetime
    metrics_summary: Dict[str, Dict[str, float]]
    trends: Dict[str, str]
    anomalies: List[Dict[str, Any]]
    recommendations: List[str]
    generated_at: datetime
    metadata: Dict[str, Any]

class PerformanceTracker:
    """Advanced performance tracking system"""
    
    def __init__(self, config: TrackingConfig = None):
        self.config = config or TrackingConfig()
        self.logger = logging.getLogger(__name__)
        
        # Tracking state
        self.tracking_active = False
        self.tracking_thread = None
        self.metrics_queue = queue.Queue()
        
        # Data storage
        self.metrics = []
        self.baselines = {}
        self.alerts = []
        self.reports = []
        
        # Database
        self.db_path = self.config.database_path
        self._init_database()
        
        # Directories
        self.export_dir = Path(self.config.export_directory)
        self.export_dir.mkdir(exist_ok=True)
        
        # Thread safety
        self.data_lock = threading.Lock()
        self.alert_lock = threading.Lock()
        
        logger.info("PerformanceTracker initialized")
    
    def _init_database(self):
        """Initialize performance tracking database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    metric_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    context TEXT,
                    metadata TEXT
                )
            ''')
            
            # Baselines table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_baselines (
                    baseline_id TEXT PRIMARY KEY,
                    metric_name TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    baseline_value REAL NOT NULL,
                    confidence_interval_lower REAL,
                    confidence_interval_upper REAL,
                    sample_size INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            # Alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_alerts (
                    alert_id TEXT PRIMARY KEY,
                    metric_name TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    current_value REAL NOT NULL,
                    baseline_value REAL,
                    threshold REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Reports table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_reports (
                    report_id TEXT PRIMARY KEY,
                    report_type TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    metrics_summary TEXT NOT NULL,
                    trends TEXT NOT NULL,
                    anomalies TEXT NOT NULL,
                    recommendations TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            # Aggregated metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS aggregated_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aggregation_interval TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    aggregation_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Performance tracking database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def start_tracking(self):
        """Start performance tracking"""
        try:
            if self.tracking_active:
                logger.warning("Tracking already active")
                return
            
            self.tracking_active = True
            
            # Start tracking thread
            self.tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
            self.tracking_thread.start()
            
            # Load existing baselines
            self._load_baselines()
            
            logger.info("Performance tracking started")
            
        except Exception as e:
            logger.error(f"Failed to start tracking: {str(e)}")
            raise
    
    def stop_tracking(self):
        """Stop performance tracking"""
        try:
            self.tracking_active = False
            
            if self.tracking_thread and self.tracking_thread.is_alive():
                self.tracking_thread.join(timeout=10)
            
            logger.info("Performance tracking stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop tracking: {str(e)}")
    
    def _tracking_loop(self):
        """Main tracking loop"""
        try:
            cycle_count = 0
            
            while self.tracking_active:
                try:
                    # Process metrics queue
                    self._process_metrics_queue()
                    
                    # Update baselines if needed
                    if cycle_count % self.config.baseline_update_frequency == 0:
                        self._update_baselines()
                    
                    # Check for alerts
                    self._check_alerts()
                    
                    # Generate aggregated metrics
                    if self.config.enable_aggregation:
                        self._generate_aggregated_metrics()
                    
                    # Generate plots
                    if self.config.enable_plotting and cycle_count % self.config.plot_frequency == 0:
                        self._generate_performance_plots()
                    
                    # Generate reports
                    if cycle_count % (self.config.plot_frequency * 2) == 0:
                        self._generate_performance_report()
                    
                    # Clean old data
                    self._cleanup_old_data()
                    
                    cycle_count += 1
                    time.sleep(self.config.tracking_interval)
                    
                except Exception as e:
                    logger.error(f"Error in tracking cycle: {str(e)}")
                    time.sleep(self.config.tracking_interval)
                    
        except Exception as e:
            logger.error(f"Tracking loop failed: {str(e)}")
    
    def track_classification_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, 
                                   y_proba: Optional[np.ndarray] = None,
                                   context: Dict[str, Any] = None) -> Dict[str, float]:
        """Track classification performance metrics"""
        try:
            metrics = {}
            
            # Calculate classification metrics
            metrics["accuracy"] = accuracy_score(y_true, y_pred)
            metrics["precision"] = precision_score(y_true, y_pred, average='macro', zero_division=0)
            metrics["recall"] = recall_score(y_true, y_pred, average='macro', zero_division=0)
            metrics["f1_score"] = f1_score(y_true, y_pred, average='macro', zero_division=0)
            
            if y_proba is not None and len(np.unique(y_true)) == 2:
                metrics["roc_auc"] = roc_auc_score(y_true, y_proba[:, 1])
            
            # Store metrics
            timestamp = datetime.now()
            for metric_name, value in metrics.items():
                metric = PerformanceMetric(
                    metric_id=str(uuid.uuid4()),
                    timestamp=timestamp,
                    metric_type=MetricType.CLASSIFICATION,
                    metric_name=metric_name,
                    value=value,
                    context=context or {},
                    metadata={"sample_size": len(y_true)}
                )
                
                self.metrics_queue.put(metric)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to track classification metrics: {str(e)}")
            return {}
    
    def track_regression_metrics(self, y_true: np.ndarray, y_pred: np.ndarray,
                               context: Dict[str, Any] = None) -> Dict[str, float]:
        """Track regression performance metrics"""
        try:
            metrics = {}
            
            # Calculate regression metrics
            metrics["mse"] = mean_squared_error(y_true, y_pred)
            metrics["mae"] = mean_absolute_error(y_true, y_pred)
            metrics["r2_score"] = r2_score(y_true, y_pred)
            metrics["rmse"] = np.sqrt(mean_squared_error(y_true, y_pred))
            
            # Store metrics
            timestamp = datetime.now()
            for metric_name, value in metrics.items():
                metric = PerformanceMetric(
                    metric_id=str(uuid.uuid4()),
                    timestamp=timestamp,
                    metric_type=MetricType.REGRESSION,
                    metric_name=metric_name,
                    value=value,
                    context=context or {},
                    metadata={"sample_size": len(y_true)}
                )
                
                self.metrics_queue.put(metric)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to track regression metrics: {str(e)}")
            return {}
    
    def track_system_metrics(self, latency_ms: float, throughput: float,
                           memory_usage: float, cpu_usage: float,
                           context: Dict[str, Any] = None) -> Dict[str, float]:
        """Track system performance metrics"""
        try:
            metrics = {
                "latency": latency_ms,
                "throughput": throughput,
                "memory_usage": memory_usage,
                "cpu_usage": cpu_usage
            }
            
            # Store metrics
            timestamp = datetime.now()
            for metric_name, value in metrics.items():
                metric = PerformanceMetric(
                    metric_id=str(uuid.uuid4()),
                    timestamp=timestamp,
                    metric_type=MetricType.SYSTEM,
                    metric_name=metric_name,
                    value=value,
                    context=context or {},
                    metadata={}
                )
                
                self.metrics_queue.put(metric)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to track system metrics: {str(e)}")
            return {}
    
    def track_custom_metric(self, metric_name: str, value: float,
                          metric_type: MetricType = MetricType.CUSTOM,
                          context: Dict[str, Any] = None,
                          metadata: Dict[str, Any] = None):
        """Track custom performance metric"""
        try:
            metric = PerformanceMetric(
                metric_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                metric_type=metric_type,
                metric_name=metric_name,
                value=value,
                context=context or {},
                metadata=metadata or {}
            )
            
            self.metrics_queue.put(metric)
            
        except Exception as e:
            logger.error(f"Failed to track custom metric: {str(e)}")
    
    def _process_metrics_queue(self):
        """Process metrics from queue"""
        try:
            while not self.metrics_queue.empty():
                try:
                    metric = self.metrics_queue.get_nowait()
                    
                    with self.data_lock:
                        self.metrics.append(metric)
                        self._save_metric(metric)
                    
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"Failed to process metric: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Failed to process metrics queue: {str(e)}")
    
    def _save_metric(self, metric: PerformanceMetric):
        """Save metric to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_metrics 
                (metric_id, timestamp, metric_type, metric_name, value, context, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.metric_id,
                metric.timestamp.isoformat(),
                metric.metric_type.value,
                metric.metric_name,
                metric.value,
                json.dumps(metric.context),
                json.dumps(metric.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save metric: {str(e)}")
    
    def _load_baselines(self):
        """Load existing baselines from database"""
        try:
            if not self.config.enable_baselines:
                return
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM performance_baselines')
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                baseline = PerformanceBaseline(
                    baseline_id=row[0],
                    metric_name=row[1],
                    metric_type=MetricType(row[2]),
                    baseline_value=row[3],
                    confidence_interval=(row[4], row[5]),
                    sample_size=row[6],
                    created_at=datetime.fromisoformat(row[7]),
                    updated_at=datetime.fromisoformat(row[8]),
                    metadata=json.loads(row[9]) if row[9] else {}
                )
                
                self.baselines[f"{baseline.metric_type.value}_{baseline.metric_name}"] = baseline
            
            logger.info(f"Loaded {len(self.baselines)} baselines")
            
        except Exception as e:
            logger.error(f"Failed to load baselines: {str(e)}")
    
    def _update_baselines(self):
        """Update performance baselines"""
        try:
            if not self.config.enable_baselines:
                return
            
            with self.data_lock:
                # Group recent metrics by type and name
                recent_metrics = [
                    m for m in self.metrics
                    if m.timestamp > datetime.now() - timedelta(hours=24)
                ]
                
                if not recent_metrics:
                    return
                
                # Group metrics
                metric_groups = {}
                for metric in recent_metrics:
                    key = f"{metric.metric_type.value}_{metric.metric_name}"
                    if key not in metric_groups:
                        metric_groups[key] = []
                    metric_groups[key].append(metric.value)
                
                # Update baselines
                for key, values in metric_groups.items():
                    if len(values) >= self.config.baseline_window:
                        metric_type_str, metric_name = key.split('_', 1)
                        metric_type = MetricType(metric_type_str)
                        
                        # Calculate baseline statistics
                        baseline_value = np.mean(values)
                        confidence_interval = (
                            np.percentile(values, 2.5),
                            np.percentile(values, 97.5)
                        )
                        
                        # Create or update baseline
                        baseline_key = key
                        if baseline_key in self.baselines:
                            baseline = self.baselines[baseline_key]
                            baseline.baseline_value = baseline_value
                            baseline.confidence_interval = confidence_interval
                            baseline.updated_at = datetime.now()
                        else:
                            baseline = PerformanceBaseline(
                                baseline_id=str(uuid.uuid4()),
                                metric_name=metric_name,
                                metric_type=metric_type,
                                baseline_value=baseline_value,
                                confidence_interval=confidence_interval,
                                sample_size=len(values),
                                created_at=datetime.now(),
                                updated_at=datetime.now(),
                                metadata={}
                            )
                            self.baselines[baseline_key] = baseline
                        
                        # Save to database
                        self._save_baseline(baseline)
                
                logger.info(f"Updated {len(metric_groups)} baselines")
                
        except Exception as e:
            logger.error(f"Failed to update baselines: {str(e)}")
    
    def _save_baseline(self, baseline: PerformanceBaseline):
        """Save baseline to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO performance_baselines 
                (baseline_id, metric_name, metric_type, baseline_value,
                 confidence_interval_lower, confidence_interval_upper,
                 sample_size, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                baseline.baseline_id,
                baseline.metric_name,
                baseline.metric_type.value,
                baseline.baseline_value,
                baseline.confidence_interval[0],
                baseline.confidence_interval[1],
                baseline.sample_size,
                baseline.created_at.isoformat(),
                baseline.updated_at.isoformat(),
                json.dumps(baseline.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save baseline: {str(e)}")
    
    def _check_alerts(self):
        """Check for performance alerts"""
        try:
            if not self.config.enable_alerts:
                return
            
            with self.data_lock:
                # Get recent metrics
                recent_metrics = [
                    m for m in self.metrics
                    if m.timestamp > datetime.now() - timedelta(minutes=5)
                ]
                
                if not recent_metrics:
                    return
                
                # Check each metric against thresholds
                for metric in recent_metrics:
                    key = f"{metric.metric_type.value}_{metric.metric_name}"
                    
                    # Get threshold configuration
                    threshold_config = None
                    if metric.metric_type == MetricType.CLASSIFICATION:
                        threshold_config = self.config.alert_thresholds.get("classification", {}).get(metric.metric_name)
                    elif metric.metric_type == MetricType.REGRESSION:
                        threshold_config = self.config.alert_thresholds.get("regression", {}).get(metric.metric_name)
                    elif metric.metric_type == MetricType.SYSTEM:
                        threshold_config = self.config.alert_thresholds.get("system", {}).get(metric.metric_name)
                    
                    if not threshold_config:
                        continue
                    
                    # Check threshold conditions
                    alert_triggered = False
                    alert_type = ""
                    threshold_value = 0
                    
                    # Check minimum threshold
                    if "min" in threshold_config and metric.value < threshold_config["min"]:
                        alert_triggered = True
                        alert_type = "below_minimum"
                        threshold_value = threshold_config["min"]
                    
                    # Check maximum threshold
                    elif "max" in threshold_config and metric.value > threshold_config["max"]:
                        alert_triggered = True
                        alert_type = "above_maximum"
                        threshold_value = threshold_config["max"]
                    
                    # Check degradation against baseline
                    elif "max_degradation" in threshold_config and key in self.baselines:
                        baseline = self.baselines[key]
                        degradation = (baseline.baseline_value - metric.value) / baseline.baseline_value
                        if degradation > threshold_config["max_degradation"]:
                            alert_triggered = True
                            alert_type = "performance_degradation"
                            threshold_value = threshold_config["max_degradation"]
                    
                    # Check increase against baseline
                    elif "max_increase" in threshold_config and key in self.baselines:
                        baseline = self.baselines[key]
                        increase = (metric.value - baseline.baseline_value) / baseline.baseline_value
                        if increase > threshold_config["max_increase"]:
                            alert_triggered = True
                            alert_type = "performance_increase"
                            threshold_value = threshold_config["max_increase"]
                    
                    # Create alert if triggered
                    if alert_triggered:
                        self._create_alert(metric, alert_type, threshold_value, baseline.baseline_value if key in self.baselines else None)
                
        except Exception as e:
            logger.error(f"Failed to check alerts: {str(e)}")
    
    def _create_alert(self, metric: PerformanceMetric, alert_type: str, 
                     threshold: float, baseline_value: Optional[float]):
        """Create performance alert"""
        try:
            # Check cooldown
            recent_alerts = [
                a for a in self.alerts
                if a.metric_name == metric.metric_name and 
                a.timestamp > datetime.now() - timedelta(seconds=self.config.alert_cooldown)
            ]
            
            if recent_alerts:
                return
            
            # Determine severity
            severity = "warning"
            if alert_type in ["below_minimum", "above_maximum"]:
                severity = "critical"
            elif alert_type in ["performance_degradation", "performance_increase"]:
                severity = "warning"
            
            # Create alert message
            message = f"Metric '{metric.metric_name}' {alert_type}: {metric.value:.4f}"
            if baseline_value is not None:
                message += f" (baseline: {baseline_value:.4f})"
            message += f" (threshold: {threshold:.4f})"
            
            alert = PerformanceAlert(
                alert_id=str(uuid.uuid4()),
                metric_name=metric.metric_name,
                alert_type=alert_type,
                severity=severity,
                message=message,
                current_value=metric.value,
                baseline_value=baseline_value,
                threshold=threshold,
                timestamp=datetime.now()
            )
            
            with self.alert_lock:
                self.alerts.append(alert)
                self._save_alert(alert)
            
            logger.warning(f"Performance alert: {message}")
            
        except Exception as e:
            logger.error(f"Failed to create alert: {str(e)}")
    
    def _save_alert(self, alert: PerformanceAlert):
        """Save alert to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO performance_alerts 
                (alert_id, metric_name, alert_type, severity, message,
                 current_value, baseline_value, threshold, timestamp, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.alert_id,
                alert.metric_name,
                alert.alert_type,
                alert.severity,
                alert.message,
                alert.current_value,
                alert.baseline_value,
                alert.threshold,
                alert.timestamp.isoformat(),
                alert.resolved
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save alert: {str(e)}")
    
    def _generate_aggregated_metrics(self):
        """Generate aggregated metrics"""
        try:
            if not self.config.enable_aggregation:
                return
            
            with self.data_lock:
                current_time = datetime.now()
                
                for interval in self.config.aggregation_intervals:
                    # Calculate time window
                    if interval == "1h":
                        window_start = current_time - timedelta(hours=1)
                    elif interval == "6h":
                        window_start = current_time - timedelta(hours=6)
                    elif interval == "1d":
                        window_start = current_time - timedelta(days=1)
                    else:
                        continue
                    
                    # Get metrics in window
                    window_metrics = [
                        m for m in self.metrics
                        if m.timestamp > window_start
                    ]
                    
                    if not window_metrics:
                        continue
                    
                    # Group by metric type and name
                    metric_groups = {}
                    for metric in window_metrics:
                        key = f"{metric.metric_type.value}_{metric.metric_name}"
                        if key not in metric_groups:
                            metric_groups[key] = []
                        metric_groups[key].append(metric.value)
                    
                    # Calculate aggregations
                    for key, values in metric_groups.items():
                        metric_type_str, metric_name = key.split('_', 1)
                        metric_type = MetricType(metric_type_str)
                        
                        for agg_type in [AggregationType.MEAN, AggregationType.MEDIAN, 
                                       AggregationType.MIN, AggregationType.MAX, AggregationType.STD]:
                            if agg_type == AggregationType.MEAN:
                                agg_value = np.mean(values)
                            elif agg_type == AggregationType.MEDIAN:
                                agg_value = np.median(values)
                            elif agg_type == AggregationType.MIN:
                                agg_value = np.min(values)
                            elif agg_type == AggregationType.MAX:
                                agg_value = np.max(values)
                            elif agg_type == AggregationType.STD:
                                agg_value = np.std(values)
                            
                            # Save aggregated metric
                            self._save_aggregated_metric(
                                interval, metric_name, metric_type, 
                                agg_type.value, agg_value, len(values), current_time
                            )
                
                logger.info("Generated aggregated metrics")
                
        except Exception as e:
            logger.error(f"Failed to generate aggregated metrics: {str(e)}")
    
    def _save_aggregated_metric(self, interval: str, metric_name: str, 
                               metric_type: MetricType, aggregation_type: str,
                               value: float, sample_count: int, timestamp: datetime):
        """Save aggregated metric to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO aggregated_metrics 
                (aggregation_interval, metric_name, metric_type, aggregation_type,
                 value, sample_count, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                interval,
                metric_name,
                metric_type.value,
                aggregation_type,
                value,
                sample_count,
                timestamp.isoformat(),
                json.dumps({})
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save aggregated metric: {str(e)}")
    
    def _generate_performance_plots(self):
        """Generate performance visualization plots"""
        try:
            if not self.config.enable_plotting:
                return
            
            with self.data_lock:
                # Get recent metrics
                recent_metrics = [
                    m for m in self.metrics
                    if m.timestamp > datetime.now() - timedelta(days=7)
                ]
                
                if not recent_metrics:
                    return
                
                # Convert to DataFrame
                df = pd.DataFrame([
                    {
                        "timestamp": m.timestamp,
                        "metric_type": m.metric_type.value,
                        "metric_name": m.metric_name,
                        "value": m.value
                    }
                    for m in recent_metrics
                ])
                
                # Plot 1: Performance trends over time
                self._plot_performance_trends(df)
                
                # Plot 2: Metric distributions
                self._plot_metric_distributions(df)
                
                # Plot 3: Baseline comparisons
                self._plot_baseline_comparisons(df)
                
                # Plot 4: Alert timeline
                self._plot_alert_timeline()
                
                logger.info("Generated performance plots")
                
        except Exception as e:
            logger.error(f"Failed to generate performance plots: {str(e)}")
    
    def _plot_performance_trends(self, df: pd.DataFrame):
        """Plot performance trends over time"""
        try:
            # Group by metric type
            for metric_type in df["metric_type"].unique():
                type_df = df[df["metric_type"] == metric_type]
                
                # Get top metrics by frequency
                top_metrics = type_df["metric_name"].value_counts().head(6).index.tolist()
                
                plt.figure(figsize=(15, 10))
                
                for i, metric_name in enumerate(top_metrics):
                    metric_df = type_df[type_df["metric_name"] == metric_name]
                    
                    plt.subplot(3, 2, i + 1)
                    plt.plot(metric_df["timestamp"], metric_df["value"], marker='o', markersize=2)
                    
                    # Add baseline if available
                    baseline_key = f"{metric_type}_{metric_name}"
                    if baseline_key in self.baselines:
                        baseline = self.baselines[baseline_key]
                        plt.axhline(y=baseline.baseline_value, color='r', linestyle='--', 
                                   alpha=0.7, label=f'Baseline: {baseline.baseline_value:.3f}')
                        plt.legend()
                    
                    plt.title(f"{metric_name} ({metric_type})")
                    plt.xticks(rotation=45)
                    plt.ylabel("Value")
                
                plt.tight_layout()
                plot_path = self.export_dir / f"performance_trends_{metric_type}.{self.config.plot_format}"
                plt.savefig(plot_path, dpi=self.config.plot_dpi, bbox_inches='tight')
                plt.close()
                
        except Exception as e:
            logger.error(f"Failed to plot performance trends: {str(e)}")
    
    def _plot_metric_distributions(self, df: pd.DataFrame):
        """Plot metric distributions"""
        try:
            # Group by metric type
            for metric_type in df["metric_type"].unique():
                type_df = df[df["metric_type"] == metric_type]
                
                # Get top metrics
                top_metrics = type_df["metric_name"].value_counts().head(6).index.tolist()
                
                plt.figure(figsize=(15, 10))
                
                for i, metric_name in enumerate(top_metrics):
                    metric_df = type_df[type_df["metric_name"] == metric_name]
                    
                    plt.subplot(3, 2, i + 1)
                    plt.hist(metric_df["value"], bins=20, alpha=0.7, edgecolor='black')
                    
                    # Add baseline if available
                    baseline_key = f"{metric_type}_{metric_name}"
                    if baseline_key in self.baselines:
                        baseline = self.baselines[baseline_key]
                        plt.axvline(x=baseline.baseline_value, color='r', linestyle='--', 
                                   alpha=0.7, label=f'Baseline: {baseline.baseline_value:.3f}')
                        plt.legend()
                    
                    plt.title(f"{metric_name} Distribution ({metric_type})")
                    plt.xlabel("Value")
                    plt.ylabel("Frequency")
                
                plt.tight_layout()
                plot_path = self.export_dir / f"metric_distributions_{metric_type}.{self.config.plot_format}"
                plt.savefig(plot_path, dpi=self.config.plot_dpi, bbox_inches='tight')
                plt.close()
                
        except Exception as e:
            logger.error(f"Failed to plot metric distributions: {str(e)}")
    
    def _plot_baseline_comparisons(self, df: pd.DataFrame):
        """Plot baseline comparisons"""
        try:
            # Get metrics with baselines
            baseline_metrics = []
            for metric in self.metrics:
                baseline_key = f"{metric.metric_type.value}_{metric.metric_name}"
                if baseline_key in self.baselines:
                    baseline_metrics.append(metric)
            
            if not baseline_metrics:
                return
            
            # Convert to DataFrame
            baseline_df = pd.DataFrame([
                {
                    "metric_name": m.metric_name,
                    "metric_type": m.metric_type.value,
                    "current_value": m.value,
                    "baseline_value": self.baselines[f"{m.metric_type.value}_{m.metric_name}"].baseline_value
                }
                for m in baseline_metrics
            ])
            
            # Calculate deviation
            baseline_df["deviation"] = (baseline_df["current_value"] - baseline_df["baseline_value"]) / baseline_df["baseline_value"]
            
            # Plot deviations
            plt.figure(figsize=(12, 8))
            
            for metric_type in baseline_df["metric_type"].unique():
                type_df = baseline_df[baseline_df["metric_type"] == metric_type]
                
                plt.bar(type_df["metric_name"], type_df["deviation"], alpha=0.7, label=metric_type)
            
            plt.axhline(y=0, color='r', linestyle='--', alpha=0.5)
            plt.xlabel("Metrics")
            plt.ylabel("Deviation from Baseline")
            plt.title("Performance Deviation from Baselines")
            plt.legend()
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            plot_path = self.export_dir / f"baseline_comparisons.{self.config.plot_format}"
            plt.savefig(plot_path, dpi=self.config.plot_dpi, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            logger.error(f"Failed to plot baseline comparisons: {str(e)}")
    
    def _plot_alert_timeline(self):
        """Plot alert timeline"""
        try:
            with self.alert_lock:
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
                alert_df = pd.DataFrame([
                    {
                        "timestamp": a.timestamp,
                        "metric_name": a.metric_name,
                        "severity": a.severity,
                        "alert_type": a.alert_type
                    }
                    for a in recent_alerts
                ])
                
                # Plot timeline
                plt.figure(figsize=(15, 6))
                
                colors = {"critical": "red", "warning": "orange", "info": "blue"}
                
                for severity in alert_df["severity"].unique():
                    severity_df = alert_df[alert_df["severity"] == severity]
                    plt.scatter(severity_df["timestamp"], 
                              [1] * len(severity_df),
                              c=colors.get(severity, "gray"),
                              label=severity.upper(),
                              alpha=0.7,
                              s=100)
                
                plt.xlabel("Time")
                plt.ylabel("Alerts")
                plt.title("Performance Alert Timeline (Last 7 Days)")
                plt.legend()
                plt.xticks(rotation=45)
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                
                plot_path = self.export_dir / f"alert_timeline.{self.config.plot_format}"
                plt.savefig(plot_path, dpi=self.config.plot_dpi, bbox_inches='tight')
                plt.close()
                
        except Exception as e:
            logger.error(f"Failed to plot alert timeline: {str(e)}")
    
    def _generate_performance_report(self):
        """Generate comprehensive performance report"""
        try:
            with self.data_lock:
                # Get recent data
                recent_time = datetime.now() - timedelta(days=1)
                recent_metrics = [m for m in self.metrics if m.timestamp > recent_time]
                
                if not recent_metrics:
                    return
                
                # Calculate metrics summary
                metrics_summary = {}
                for metric_type in MetricType:
                    type_metrics = [m for m in recent_metrics if m.metric_type == metric_type]
                    
                    if type_metrics:
                        type_summary = {}
                        for metric_name in set(m.metric_name for m in type_metrics):
                            values = [m.value for m in type_metrics if m.metric_name == metric_name]
                            type_summary[metric_name] = {
                                "mean": np.mean(values),
                                "std": np.std(values),
                                "min": np.min(values),
                                "max": np.max(values),
                                "count": len(values)
                            }
                        
                        metrics_summary[metric_type.value] = type_summary
                
                # Analyze trends
                trends = self._analyze_trends(recent_metrics)
                
                # Detect anomalies
                anomalies = self._detect_anomalies(recent_metrics)
                
                # Generate recommendations
                recommendations = self._generate_recommendations(metrics_summary, trends, anomalies)
                
                # Create report
                report = PerformanceReport(
                    report_id=str(uuid.uuid4()),
                    report_type="daily_performance",
                    start_time=recent_time,
                    end_time=datetime.now(),
                    metrics_summary=metrics_summary,
                    trends=trends,
                    anomalies=anomalies,
                    recommendations=recommendations,
                    generated_at=datetime.now(),
                    metadata={"report_version": "1.0"}
                )
                
                self.reports.append(report)
                self._save_report(report)
                
                logger.info("Generated performance report")
                
        except Exception as e:
            logger.error(f"Failed to generate performance report: {str(e)}")
    
    def _analyze_trends(self, metrics: List[PerformanceMetric]) -> Dict[str, str]:
        """Analyze performance trends"""
        try:
            trends = {}
            
            # Group by metric
            metric_groups = {}
            for metric in metrics:
                key = f"{metric.metric_type.value}_{metric.metric_name}"
                if key not in metric_groups:
                    metric_groups[key] = []
                metric_groups[key].append(metric)
            
            # Analyze each metric
            for key, metric_list in metric_groups.items():
                if len(metric_list) < 10:
                    continue
                
                # Sort by timestamp
                metric_list.sort(key=lambda m: m.timestamp)
                values = [m.value for m in metric_list]
                
                # Calculate trend using linear regression
                x = np.arange(len(values))
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
                
                # Determine trend direction
                if p_value < 0.05:  # Significant trend
                    if slope > 0:
                        trend = "improving"
                    else:
                        trend = "degrading"
                else:
                    trend = "stable"
                
                trends[key] = trend
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to analyze trends: {str(e)}")
            return {}
    
    def _detect_anomalies(self, metrics: List[PerformanceMetric]) -> List[Dict[str, Any]]:
        """Detect performance anomalies"""
        try:
            anomalies = []
            
            # Group by metric
            metric_groups = {}
            for metric in metrics:
                key = f"{metric.metric_type.value}_{metric.metric_name}"
                if key not in metric_groups:
                    metric_groups[key] = []
                metric_groups[key].append(metric)
            
            # Detect anomalies using statistical methods
            for key, metric_list in metric_groups.items():
                values = [m.value for m in metric_list]
                
                if len(values) < 20:
                    continue
                
                # Calculate z-scores
                mean_val = np.mean(values)
                std_val = np.std(values)
                
                for metric in metric_list:
                    if std_val > 0:
                        z_score = abs((metric.value - mean_val) / std_val)
                        
                        if z_score > 3:  # 3-sigma rule
                            anomalies.append({
                                "metric_name": metric.metric_name,
                                "metric_type": metric.metric_type.value,
                                "timestamp": metric.timestamp.isoformat(),
                                "value": metric.value,
                                "z_score": z_score,
                                "anomaly_type": "statistical_outlier"
                            })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Failed to detect anomalies: {str(e)}")
            return []
    
    def _generate_recommendations(self, metrics_summary: Dict[str, Dict[str, float]], 
                                trends: Dict[str, str], 
                                anomalies: List[Dict[str, Any]]) -> List[str]:
        """Generate performance recommendations"""
        try:
            recommendations = []
            
            # Check for degrading trends
            degrading_metrics = [k for k, v in trends.items() if v == "degrading"]
            if degrading_metrics:
                recommendations.append(f"Investigate degrading performance in: {', '.join(degrading_metrics)}")
            
            # Check for high variance
            high_variance_metrics = []
            for metric_type, type_summary in metrics_summary.items():
                for metric_name, stats in type_summary.items():
                    if stats["std"] / stats["mean"] > 0.2:  # High coefficient of variation
                        high_variance_metrics.append(f"{metric_name} ({metric_type})")
            
            if high_variance_metrics:
                recommendations.append(f"High variance detected in: {', '.join(high_variance_metrics)}")
            
            # Check for anomalies
            if len(anomalies) > 5:
                recommendations.append(f"High number of anomalies detected ({len(anomalies)}). Consider investigating data quality.")
            
            # Check for performance issues
            for metric_type, type_summary in metrics_summary.items():
                if metric_type == "classification":
                    for metric_name, stats in type_summary.items():
                        if metric_name == "accuracy" and stats["mean"] < 0.7:
                            recommendations.append(f"Low accuracy detected: {stats['mean']:.3f}")
                
                elif metric_type == "system":
                    for metric_name, stats in type_summary.items():
                        if metric_name == "latency" and stats["mean"] > 500:
                            recommendations.append(f"High latency detected: {stats['mean']:.1f}ms")
            
            # General recommendations
            if not recommendations:
                recommendations.append("Performance is within expected ranges. Continue monitoring.")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}")
            return []
    
    def _save_report(self, report: PerformanceReport):
        """Save report to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_reports 
                (report_id, report_type, start_time, end_time, metrics_summary,
                 trends, anomalies, recommendations, generated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report.report_id,
                report.report_type,
                report.start_time.isoformat(),
                report.end_time.isoformat(),
                json.dumps(report.metrics_summary),
                json.dumps(report.trends),
                json.dumps(report.anomalies),
                json.dumps(report.recommendations),
                report.generated_at.isoformat(),
                json.dumps(report.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save report: {str(e)}")
    
    def _cleanup_old_data(self):
        """Clean up old data based on retention policy"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.max_history_days)
            
            with self.data_lock:
                # Clean metrics
                self.metrics = [m for m in self.metrics if m.timestamp > cutoff_date]
            
            with self.alert_lock:
                # Clean resolved alerts
                self.alerts = [
                    a for a in self.alerts 
                    if a.timestamp > cutoff_date or not a.resolved
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
            cursor.execute("DELETE FROM performance_metrics WHERE timestamp < ?", (cutoff_str,))
            cursor.execute("DELETE FROM performance_alerts WHERE timestamp < ? AND resolved = TRUE", (cutoff_str,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to cleanup database: {str(e)}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance tracking summary"""
        try:
            with self.data_lock:
                summary = {
                    "tracking_active": self.tracking_active,
                    "total_metrics": len(self.metrics),
                    "total_baselines": len(self.baselines),
                    "total_alerts": len(self.alerts),
                    "unresolved_alerts": len([a for a in self.alerts if not a.resolved]),
                    "total_reports": len(self.reports),
                    "metric_types": list(set(m.metric_type.value for m in self.metrics)),
                    "config": asdict(self.config)
                }
                
                # Recent performance
                recent_time = datetime.now() - timedelta(hours=1)
                recent_metrics = [m for m in self.metrics if m.timestamp > recent_time]
                
                if recent_metrics:
                    summary["recent_metrics_count"] = len(recent_metrics)
                    summary["recent_metric_types"] = list(set(m.metric_type.value for m in recent_metrics))
                
                return summary
                
        except Exception as e:
            logger.error(f"Failed to get performance summary: {str(e)}")
            return {}
    
    def export_tracking_data(self, output_path: str, format: str = "json"):
        """Export performance tracking data"""
        try:
            export_data = {
                "summary": self.get_performance_summary(),
                "metrics": [
                    {
                        "metric_id": m.metric_id,
                        "timestamp": m.timestamp.isoformat(),
                        "metric_type": m.metric_type.value,
                        "metric_name": m.metric_name,
                        "value": m.value,
                        "context": m.context,
                        "metadata": m.metadata
                    }
                    for m in self.metrics[-1000:]  # Last 1000 metrics
                ],
                "baselines": {
                    key: {
                        "baseline_id": baseline.baseline_id,
                        "metric_name": baseline.metric_name,
                        "metric_type": baseline.metric_type.value,
                        "baseline_value": baseline.baseline_value,
                        "confidence_interval": baseline.confidence_interval,
                        "sample_size": baseline.sample_size,
                        "created_at": baseline.created_at.isoformat(),
                        "updated_at": baseline.updated_at.isoformat()
                    }
                    for key, baseline in self.baselines.items()
                },
                "alerts": [
                    {
                        "alert_id": a.alert_id,
                        "metric_name": a.metric_name,
                        "alert_type": a.alert_type,
                        "severity": a.severity,
                        "message": a.message,
                        "current_value": a.current_value,
                        "baseline_value": a.baseline_value,
                        "threshold": a.threshold,
                        "timestamp": a.timestamp.isoformat(),
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
                
                if export_data["metrics"]:
                    pd.DataFrame(export_data["metrics"]).to_csv(
                        f"{base_path}_metrics.csv", index=False
                    )
                
                if export_data["baselines"]:
                    baseline_data = []
                    for key, baseline in export_data["baselines"].items():
                        baseline_data.append({
                            "key": key,
                            "metric_name": baseline["metric_name"],
                            "metric_type": baseline["metric_type"],
                            "baseline_value": baseline["baseline_value"],
                            "sample_size": baseline["sample_size"],
                            "created_at": baseline["created_at"]
                        })
                    pd.DataFrame(baseline_data).to_csv(
                        f"{base_path}_baselines.csv", index=False
                    )
                
                if export_data["alerts"]:
                    pd.DataFrame(export_data["alerts"]).to_csv(
                        f"{base_path}_alerts.csv", index=False
                    )
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Performance tracking data exported to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export tracking data: {str(e)}")
            raise

# Utility functions
def create_default_tracker() -> PerformanceTracker:
    """Create tracker with default configuration"""
    config = TrackingConfig()
    return PerformanceTracker(config)

def create_custom_tracker(**kwargs) -> PerformanceTracker:
    """Create tracker with custom configuration"""
    config = TrackingConfig(**kwargs)
    return PerformanceTracker(config)

if __name__ == "__main__":
    # Example usage
    tracker = create_default_tracker()
    
    try:
        # Start tracking
        tracker.start_tracking()
        
        # Track some sample metrics
        from sklearn.datasets import make_classification
        X, y = make_classification(n_samples=100, n_features=10, random_state=42)
        
        # Generate sample predictions
        y_pred = np.random.choice([0, 1], size=len(y))
        y_proba = np.random.rand(len(y), 2)
        
        # Track classification metrics
        metrics = tracker.track_classification_metrics(y, y_pred, y_proba)
        print(f"Classification metrics: {metrics}")
        
        # Track system metrics
        system_metrics = tracker.track_system_metrics(
            latency_ms=150.5, throughput=1000.0, memory_usage=0.65, cpu_usage=0.45
        )
        print(f"System metrics: {system_metrics}")
        
        # Get summary
        summary = tracker.get_performance_summary()
        print(f"Tracking summary: {summary}")
        
        # Export data
        tracker.export_tracking_data("performance_tracking_data.json")
        
        # Stop tracking
        tracker.stop_tracking()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        tracker.stop_tracking()
