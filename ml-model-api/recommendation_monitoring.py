"""
Performance Monitoring and Metrics for FlavorSnap Recommendation System

This module provides comprehensive monitoring, metrics collection, and
performance analysis for the recommendation system.
"""

import logging
import time
import psutil
import threading
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import numpy as np
from statistics import mean, median, stdev
import sqlite3
from db_config import get_connection

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    metric_name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]
    unit: str
    metadata: Dict[str, Any]

@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    timestamp: datetime

@dataclass
class RecommendationMetrics:
    """Recommendation-specific metrics"""
    request_count: int
    avg_response_time_ms: float
    cache_hit_rate: float
    error_rate: float
    diversity_score: float
    novelty_score: float
    user_satisfaction: float
    conversion_rate: float
    timestamp: datetime

@dataclass
class MonitoringConfig:
    """Configuration for monitoring system"""
    # Metrics collection
    collection_interval_seconds: int = 60
    metrics_retention_days: int = 30
    batch_size: int = 1000
    
    # Performance thresholds
    response_time_threshold_ms: float = 500.0
    error_rate_threshold: float = 0.05
    cpu_usage_threshold: float = 80.0
    memory_usage_threshold: float = 85.0
    
    # Alerting
    enable_alerts: bool = True
    alert_cooldown_minutes: int = 15
    alert_channels: List[str] = None
    
    # Performance tracking
    enable_real_time_monitoring: bool = True
    enable_historical_analysis: bool = True
    enable_anomaly_detection: bool = True

class RecommendationMonitoring:
    """Main monitoring system for recommendations"""
    
    def __init__(self, config: MonitoringConfig = None, db_connection=None):
        self.config = config or MonitoringConfig()
        self.db_connection = db_connection or get_connection()
        
        # Metrics storage
        self.metrics_buffer = deque(maxlen=self.config.batch_size * 10)
        self.performance_history = deque(maxlen=1000)
        self.alert_history = deque(maxlen=100)
        
        # Performance counters
        self.request_times = deque(maxlen=1000)
        self.error_count = 0
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_requests = 0
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_thread = None
        self.last_alert_times = {}
        
        # Metric callbacks
        self.metric_callbacks = []
        
        self._init_database()
        self._start_monitoring()
    
    def _init_database(self):
        """Initialize monitoring database tables"""
        if not self.db_connection:
            logger.warning("No database connection available for monitoring")
            return
            
        try:
            cursor = self.db_connection.cursor()
            
            # Performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT,
                    value REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tags TEXT,
                    unit TEXT,
                    metadata TEXT
                )
            """)
            
            # Recommendation metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendation_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_count INTEGER,
                    avg_response_time_ms REAL,
                    cache_hit_rate REAL,
                    error_rate REAL,
                    diversity_score REAL,
                    novelty_score REAL,
                    user_satisfaction REAL,
                    conversion_rate REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # System metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cpu_usage REAL,
                    memory_usage REAL,
                    disk_usage REAL,
                    network_io TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT,
                    severity TEXT,
                    message TEXT,
                    metric_name TEXT,
                    threshold_value REAL,
                    actual_value REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at TIMESTAMP
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON performance_metrics(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rec_metrics_timestamp ON recommendation_metrics(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON monitoring_alerts(timestamp)")
            
            self.db_connection.commit()
            logger.info("Monitoring database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitoring database: {e}")
    
    def _start_monitoring(self):
        """Start background monitoring"""
        try:
            if self.config.enable_real_time_monitoring:
                self.is_monitoring = True
                self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
                self.monitoring_thread.start()
                logger.info("Started recommendation system monitoring")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Collect system metrics
                system_metrics = self._collect_system_metrics()
                self._store_system_metrics(system_metrics)
                
                # Calculate recommendation metrics
                rec_metrics = self._calculate_recommendation_metrics()
                self._store_recommendation_metrics(rec_metrics)
                
                # Check for alerts
                if self.config.enable_alerts:
                    self._check_alerts(system_metrics, rec_metrics)
                
                # Flush metrics buffer
                self._flush_metrics_buffer()
                
                # Sleep until next collection
                time.sleep(self.config.collection_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)
    
    def record_request(self, response_time_ms: float, success: bool = True,
                      cache_hit: bool = False, user_id: str = None,
                      recommendation_count: int = 0) -> str:
        """Record a recommendation request"""
        try:
            self.request_times.append(response_time_ms)
            self.total_requests += 1
            
            if not success:
                self.error_count += 1
            
            if cache_hit:
                self.cache_hits += 1
            
            self.cache_requests += 1
            
            # Create metric
            metric = PerformanceMetric(
                metric_name="recommendation_request",
                value=response_time_ms,
                timestamp=datetime.now(),
                tags={
                    "success": str(success),
                    "cache_hit": str(cache_hit),
                    "user_id": user_id or "anonymous"
                },
                unit="milliseconds",
                metadata={
                    "recommendation_count": recommendation_count
                }
            )
            
            self.metrics_buffer.append(metric)
            
            # Trigger callbacks
            for callback in self.metric_callbacks:
                try:
                    callback(metric)
                except Exception as e:
                    logger.error(f"Metric callback error: {e}")
            
            return metric.metric_name
            
        except Exception as e:
            logger.error(f"Failed to record request: {e}")
            return ""
    
    def record_user_feedback(self, user_id: str, item_id: str, rating: float,
                           feedback_type: str = "rating") -> str:
        """Record user feedback"""
        try:
            metric = PerformanceMetric(
                metric_name="user_feedback",
                value=rating,
                timestamp=datetime.now(),
                tags={
                    "user_id": user_id,
                    "item_id": item_id,
                    "feedback_type": feedback_type
                },
                unit="rating",
                metadata={}
            )
            
            self.metrics_buffer.append(metric)
            return metric.metric_name
            
        except Exception as e:
            logger.error(f"Failed to record user feedback: {e}")
            return ""
    
    def record_diversity_score(self, score: float, user_id: str = None,
                            algorithm: str = "hybrid") -> str:
        """Record recommendation diversity score"""
        try:
            metric = PerformanceMetric(
                metric_name="diversity_score",
                value=score,
                timestamp=datetime.now(),
                tags={
                    "user_id": user_id or "anonymous",
                    "algorithm": algorithm
                },
                unit="score",
                metadata={}
            )
            
            self.metrics_buffer.append(metric)
            return metric.metric_name
            
        except Exception as e:
            logger.error(f"Failed to record diversity score: {e}")
            return ""
    
    def record_novelty_score(self, score: float, user_id: str = None,
                          algorithm: str = "hybrid") -> str:
        """Record recommendation novelty score"""
        try:
            metric = PerformanceMetric(
                metric_name="novelty_score",
                value=score,
                timestamp=datetime.now(),
                tags={
                    "user_id": user_id or "anonymous",
                    "algorithm": algorithm
                },
                unit="score",
                metadata={}
            )
            
            self.metrics_buffer.append(metric)
            return metric.metric_name
            
        except Exception as e:
            logger.error(f"Failed to record novelty score: {e}")
            return ""
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
            
            return SystemMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io=network_io,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(0, 0, 0, {}, datetime.now())
    
    def _calculate_recommendation_metrics(self) -> RecommendationMetrics:
        """Calculate recommendation performance metrics"""
        try:
            # Response time metrics
            avg_response_time = mean(self.request_times) if self.request_times else 0
            median_response_time = median(self.request_times) if self.request_times else 0
            p95_response_time = np.percentile(list(self.request_times), 95) if self.request_times else 0
            
            # Error rate
            error_rate = self.error_count / max(1, self.total_requests)
            
            # Cache hit rate
            cache_hit_rate = self.cache_hits / max(1, self.cache_requests)
            
            # Get recent diversity and novelty scores
            recent_diversity = self._get_recent_metric_average("diversity_score", hours=1)
            recent_novelty = self._get_recent_metric_average("novelty_score", hours=1)
            recent_satisfaction = self._get_recent_metric_average("user_feedback", hours=24)
            
            # Conversion rate (simplified - based on positive feedback)
            conversion_rate = self._calculate_conversion_rate()
            
            return RecommendationMetrics(
                request_count=self.total_requests,
                avg_response_time_ms=avg_response_time,
                cache_hit_rate=cache_hit_rate,
                error_rate=error_rate,
                diversity_score=recent_diversity,
                novelty_score=recent_novelty,
                user_satisfaction=recent_satisfaction,
                conversion_rate=conversion_rate,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate recommendation metrics: {e}")
            return RecommendationMetrics(0, 0, 0, 0, 0, 0, 0, 0, datetime.now())
    
    def _get_recent_metric_average(self, metric_name: str, hours: int = 1) -> float:
        """Get average value for a metric over recent time period"""
        try:
            if not self.db_connection:
                return 0
                
            cursor = self.db_connection.cursor()
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute("""
                SELECT AVG(value) FROM performance_metrics 
                WHERE metric_name = ? AND timestamp > ?
            """, (metric_name, cutoff_time.isoformat()))
            
            result = cursor.fetchone()
            return result[0] if result and result[0] else 0
            
        except Exception as e:
            logger.error(f"Failed to get recent metric average: {e}")
            return 0
    
    def _calculate_conversion_rate(self) -> float:
        """Calculate conversion rate based on user feedback"""
        try:
            if not self.db_connection:
                return 0
                
            cursor = self.db_connection.cursor()
            
            # Get positive feedback (rating >= 4) in last 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            cursor.execute("""
                SELECT COUNT(*) FROM performance_metrics 
                WHERE metric_name = 'user_feedback' 
                AND value >= 4 
                AND timestamp > ?
            """, (cutoff_time.isoformat(),))
            
            positive_feedback = cursor.fetchone()[0]
            
            # Get total unique users in same period
            cursor.execute("""
                SELECT COUNT(DISTINCT JSON_EXTRACT(tags, '$.user_id')) 
                FROM performance_metrics 
                WHERE metric_name = 'recommendation_request' 
                AND timestamp > ?
            """, (cutoff_time.isoformat(),))
            
            total_users = cursor.fetchone()[0]
            
            return positive_feedback / max(1, total_users)
            
        except Exception as e:
            logger.error(f"Failed to calculate conversion rate: {e}")
            return 0
    
    def _store_system_metrics(self, metrics: SystemMetrics):
        """Store system metrics in database"""
        try:
            if not self.db_connection:
                return
                
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                INSERT INTO system_metrics 
                (cpu_usage, memory_usage, disk_usage, network_io)
                VALUES (?, ?, ?, ?)
            """, (
                metrics.cpu_usage, metrics.memory_usage, metrics.disk_usage,
                json.dumps(metrics.network_io)
            ))
            
            self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to store system metrics: {e}")
    
    def _store_recommendation_metrics(self, metrics: RecommendationMetrics):
        """Store recommendation metrics in database"""
        try:
            if not self.db_connection:
                return
                
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                INSERT INTO recommendation_metrics 
                (request_count, avg_response_time_ms, cache_hit_rate, error_rate,
                 diversity_score, novelty_score, user_satisfaction, conversion_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.request_count, metrics.avg_response_time_ms,
                metrics.cache_hit_rate, metrics.error_rate, metrics.diversity_score,
                metrics.novelty_score, metrics.user_satisfaction, metrics.conversion_rate
            ))
            
            self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to store recommendation metrics: {e}")
    
    def _flush_metrics_buffer(self):
        """Flush metrics buffer to database"""
        try:
            if not self.db_connection or not self.metrics_buffer:
                return
                
            cursor = self.db_connection.cursor()
            
            metrics_to_store = list(self.metrics_buffer)
            self.metrics_buffer.clear()
            
            for metric in metrics_to_store:
                cursor.execute("""
                    INSERT INTO performance_metrics 
                    (metric_name, value, timestamp, tags, unit, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    metric.metric_name, metric.value, metric.timestamp.isoformat(),
                    json.dumps(metric.tags), metric.unit, json.dumps(metric.metadata)
                ))
            
            self.db_connection.commit()
            logger.debug(f"Flushed {len(metrics_to_store)} metrics to database")
            
        except Exception as e:
            logger.error(f"Failed to flush metrics buffer: {e}")
    
    def _check_alerts(self, system_metrics: SystemMetrics, rec_metrics: RecommendationMetrics):
        """Check for performance alerts"""
        try:
            current_time = datetime.now()
            
            # Check CPU usage
            if system_metrics.cpu_usage > self.config.cpu_usage_threshold:
                self._trigger_alert(
                    "high_cpu_usage",
                    "warning",
                    f"CPU usage is {system_metrics.cpu_usage:.1f}%",
                    "cpu_usage",
                    self.config.cpu_usage_threshold,
                    system_metrics.cpu_usage,
                    current_time
                )
            
            # Check memory usage
            if system_metrics.memory_usage > self.config.memory_usage_threshold:
                self._trigger_alert(
                    "high_memory_usage",
                    "warning",
                    f"Memory usage is {system_metrics.memory_usage:.1f}%",
                    "memory_usage",
                    self.config.memory_usage_threshold,
                    system_metrics.memory_usage,
                    current_time
                )
            
            # Check response time
            if rec_metrics.avg_response_time_ms > self.config.response_time_threshold_ms:
                self._trigger_alert(
                    "high_response_time",
                    "warning",
                    f"Average response time is {rec_metrics.avg_response_time_ms:.1f}ms",
                    "response_time_ms",
                    self.config.response_time_threshold_ms,
                    rec_metrics.avg_response_time_ms,
                    current_time
                )
            
            # Check error rate
            if rec_metrics.error_rate > self.config.error_rate_threshold:
                self._trigger_alert(
                    "high_error_rate",
                    "critical",
                    f"Error rate is {rec_metrics.error_rate:.2%}",
                    "error_rate",
                    self.config.error_rate_threshold,
                    rec_metrics.error_rate,
                    current_time
                )
            
        except Exception as e:
            logger.error(f"Failed to check alerts: {e}")
    
    def _trigger_alert(self, alert_type: str, severity: str, message: str,
                      metric_name: str, threshold: float, actual_value: float,
                      timestamp: datetime):
        """Trigger a performance alert"""
        try:
            # Check cooldown
            if alert_type in self.last_alert_times:
                time_since_last = timestamp - self.last_alert_times[alert_type]
                if time_since_last < timedelta(minutes=self.config.alert_cooldown_minutes):
                    return
            
            # Store alert
            if self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute("""
                    INSERT INTO monitoring_alerts 
                    (alert_type, severity, message, metric_name, threshold_value, actual_value)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (alert_type, severity, message, metric_name, threshold, actual_value))
                self.db_connection.commit()
            
            # Update last alert time
            self.last_alert_times[alert_type] = timestamp
            
            # Add to alert history
            self.alert_history.append({
                'alert_type': alert_type,
                'severity': severity,
                'message': message,
                'timestamp': timestamp
            })
            
            logger.warning(f"ALERT: {message}")
            
        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for specified time period"""
        try:
            if not self.db_connection:
                return {}
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cursor = self.db_connection.cursor()
            
            # Get recommendation metrics
            cursor.execute("""
                SELECT AVG(avg_response_time_ms), AVG(cache_hit_rate), AVG(error_rate),
                       AVG(diversity_score), AVG(novelty_score), AVG(user_satisfaction),
                       AVG(conversion_rate), SUM(request_count)
                FROM recommendation_metrics 
                WHERE timestamp > ?
            """, (cutoff_time.isoformat(),))
            
            rec_data = cursor.fetchone()
            
            # Get system metrics
            cursor.execute("""
                SELECT AVG(cpu_usage), AVG(memory_usage), AVG(disk_usage)
                FROM system_metrics 
                WHERE timestamp > ?
            """, (cutoff_time.isoformat(),))
            
            system_data = cursor.fetchone()
            
            # Get recent alerts
            cursor.execute("""
                SELECT alert_type, severity, message, timestamp 
                FROM monitoring_alerts 
                WHERE timestamp > ? AND resolved = FALSE
                ORDER BY timestamp DESC
                LIMIT 10
            """, (cutoff_time.isoformat(),))
            
            alerts = cursor.fetchall()
            
            return {
                'time_period_hours': hours,
                'recommendation_metrics': {
                    'avg_response_time_ms': rec_data[0] or 0,
                    'cache_hit_rate': rec_data[1] or 0,
                    'error_rate': rec_data[2] or 0,
                    'diversity_score': rec_data[3] or 0,
                    'novelty_score': rec_data[4] or 0,
                    'user_satisfaction': rec_data[5] or 0,
                    'conversion_rate': rec_data[6] or 0,
                    'total_requests': rec_data[7] or 0
                },
                'system_metrics': {
                    'avg_cpu_usage': system_data[0] or 0,
                    'avg_memory_usage': system_data[1] or 0,
                    'avg_disk_usage': system_data[2] or 0
                },
                'recent_alerts': [
                    {
                        'alert_type': alert[0],
                        'severity': alert[1],
                        'message': alert[2],
                        'timestamp': alert[3]
                    }
                    for alert in alerts
                ],
                'performance_status': self._calculate_performance_status(rec_data, system_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {}
    
    def _calculate_performance_status(self, rec_data: Tuple, system_data: Tuple) -> str:
        """Calculate overall performance status"""
        try:
            # Check critical metrics
            error_rate = rec_data[2] or 0
            response_time = rec_data[0] or 0
            cpu_usage = system_data[0] or 0
            memory_usage = system_data[1] or 0
            
            if error_rate > self.config.error_rate_threshold:
                return "critical"
            elif (response_time > self.config.response_time_threshold_ms or
                  cpu_usage > self.config.cpu_usage_threshold or
                  memory_usage > self.config.memory_usage_threshold):
                return "warning"
            else:
                return "healthy"
                
        except Exception as e:
            logger.error(f"Failed to calculate performance status: {e}")
            return "unknown"
    
    def get_metric_history(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric"""
        try:
            if not self.db_connection:
                return []
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                SELECT value, timestamp, tags FROM performance_metrics 
                WHERE metric_name = ? AND timestamp > ?
                ORDER BY timestamp ASC
            """, (metric_name, cutoff_time.isoformat()))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'value': row[0],
                    'timestamp': row[1],
                    'tags': json.loads(row[2]) if row[2] else {}
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get metric history: {e}")
            return []
    
    def get_top_performing_items(self, hours: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing items based on user feedback"""
        try:
            if not self.db_connection:
                return []
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                SELECT 
                    JSON_EXTRACT(tags, '$.item_id') as item_id,
                    AVG(value) as avg_rating,
                    COUNT(*) as feedback_count
                FROM performance_metrics 
                WHERE metric_name = 'user_feedback' 
                AND timestamp > ?
                AND JSON_EXTRACT(tags, '$.item_id') IS NOT NULL
                GROUP BY JSON_EXTRACT(tags, '$.item_id')
                HAVING feedback_count >= 3
                ORDER BY avg_rating DESC, feedback_count DESC
                LIMIT ?
            """, (cutoff_time.isoformat(), limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'item_id': row[0],
                    'avg_rating': row[1],
                    'feedback_count': row[2]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get top performing items: {e}")
            return []
    
    def add_metric_callback(self, callback: Callable[[PerformanceMetric], None]):
        """Add a callback function to be called when metrics are recorded"""
        self.metric_callbacks.append(callback)
    
    def remove_metric_callback(self, callback: Callable[[PerformanceMetric], None]):
        """Remove a metric callback function"""
        if callback in self.metric_callbacks:
            self.metric_callbacks.remove(callback)
    
    def cleanup_old_metrics(self):
        """Clean up old metrics data"""
        try:
            if not self.db_connection:
                return
            
            cutoff_date = datetime.now() - timedelta(days=self.config.metrics_retention_days)
            cursor = self.db_connection.cursor()
            
            # Clean old performance metrics
            cursor.execute("DELETE FROM performance_metrics WHERE timestamp < ?", (cutoff_date.isoformat(),))
            perf_deleted = cursor.rowcount
            
            # Clean old recommendation metrics
            cursor.execute("DELETE FROM recommendation_metrics WHERE timestamp < ?", (cutoff_date.isoformat(),))
            rec_deleted = cursor.rowcount
            
            # Clean old system metrics
            cursor.execute("DELETE FROM system_metrics WHERE timestamp < ?", (cutoff_date.isoformat(),))
            sys_deleted = cursor.rowcount
            
            # Clean old resolved alerts
            cursor.execute("DELETE FROM monitoring_alerts WHERE timestamp < ? AND resolved = TRUE", (cutoff_date.isoformat(),))
            alerts_deleted = cursor.rowcount
            
            self.db_connection.commit()
            
            logger.info(f"Cleaned up old metrics: {perf_deleted} performance, {rec_deleted} recommendation, {sys_deleted} system, {alerts_deleted} alerts")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
    
    def generate_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            summary = self.get_performance_summary(hours)
            
            # Get additional analytics
            response_time_history = self.get_metric_history("recommendation_request", hours)
            diversity_history = self.get_metric_history("diversity_score", hours)
            top_items = self.get_top_performing_items(hours)
            
            # Calculate percentiles
            response_times = [m['value'] for m in response_time_history]
            if response_times:
                response_percentiles = {
                    'p50': np.percentile(response_times, 50),
                    'p90': np.percentile(response_times, 90),
                    'p95': np.percentile(response_times, 95),
                    'p99': np.percentile(response_times, 99)
                }
            else:
                response_percentiles = {}
            
            # Calculate trends
            trends = self._calculate_trends(hours)
            
            return {
                'summary': summary,
                'analytics': {
                    'response_time_percentiles': response_percentiles,
                    'top_performing_items': top_items,
                    'diversity_trend': diversity_history[-10:] if diversity_history else [],
                    'trends': trends
                },
                'recommendations': self._generate_recommendations(summary),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {}
    
    def _calculate_trends(self, hours: int) -> Dict[str, str]:
        """Calculate performance trends"""
        try:
            if not self.db_connection:
                return {}
            
            # Get data for two periods
            mid_time = datetime.now() - timedelta(hours=hours//2)
            start_time = datetime.now() - timedelta(hours=hours)
            
            cursor = self.db_connection.cursor()
            
            # Recent period
            cursor.execute("""
                SELECT AVG(avg_response_time_ms), AVG(error_rate), AVG(cache_hit_rate)
                FROM recommendation_metrics 
                WHERE timestamp > ?
            """, (mid_time.isoformat(),))
            
            recent_data = cursor.fetchone()
            
            # Earlier period
            cursor.execute("""
                SELECT AVG(avg_response_time_ms), AVG(error_rate), AVG(cache_hit_rate)
                FROM recommendation_metrics 
                WHERE timestamp BETWEEN ? AND ?
            """, (start_time.isoformat(), mid_time.isoformat()))
            
            earlier_data = cursor.fetchone()
            
            trends = {}
            
            if recent_data[0] and earlier_data[0]:
                if recent_data[0] < earlier_data[0]:
                    trends['response_time'] = "improving"
                elif recent_data[0] > earlier_data[0] * 1.1:
                    trends['response_time'] = "degrading"
                else:
                    trends['response_time'] = "stable"
            
            if recent_data[1] and earlier_data[1]:
                if recent_data[1] < earlier_data[1]:
                    trends['error_rate'] = "improving"
                elif recent_data[1] > earlier_data[1] * 1.1:
                    trends['error_rate'] = "degrading"
                else:
                    trends['error_rate'] = "stable"
            
            if recent_data[2] and earlier_data[2]:
                if recent_data[2] > earlier_data[2]:
                    trends['cache_hit_rate'] = "improving"
                elif recent_data[2] < earlier_data[2] * 0.9:
                    trends['cache_hit_rate'] = "degrading"
                else:
                    trends['cache_hit_rate'] = "stable"
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to calculate trends: {e}")
            return {}
    
    def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Generate performance improvement recommendations"""
        try:
            recommendations = []
            
            rec_metrics = summary.get('recommendation_metrics', {})
            system_metrics = summary.get('system_metrics', {})
            
            # Response time recommendations
            if rec_metrics.get('avg_response_time_ms', 0) > self.config.response_time_threshold_ms:
                recommendations.append("Consider optimizing recommendation algorithms or increasing cache size")
            
            # Cache hit rate recommendations
            if rec_metrics.get('cache_hit_rate', 0) < 0.7:
                recommendations.append("Implement more aggressive caching strategies")
            
            # Error rate recommendations
            if rec_metrics.get('error_rate', 0) > self.config.error_rate_threshold:
                recommendations.append("Investigate and fix error sources in recommendation pipeline")
            
            # Diversity recommendations
            if rec_metrics.get('diversity_score', 0) < 0.3:
                recommendations.append("Increase diversity threshold for more varied recommendations")
            
            # System resource recommendations
            if system_metrics.get('avg_cpu_usage', 0) > self.config.cpu_usage_threshold:
                recommendations.append("Scale up compute resources or optimize algorithms")
            
            if system_metrics.get('avg_memory_usage', 0) > self.config.memory_usage_threshold:
                recommendations.append("Optimize memory usage or increase available memory")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return []
    
    def shutdown(self):
        """Shutdown the monitoring system"""
        try:
            logger.info("Shutting down recommendation monitoring...")
            
            self.is_monitoring = False
            
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=5.0)
            
            # Flush remaining metrics
            self._flush_metrics_buffer()
            
            logger.info("Recommendation monitoring shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during monitoring shutdown: {e}")

# Global monitoring instance
_monitoring_instance = None

def get_monitoring_instance(config: MonitoringConfig = None, db_connection=None) -> RecommendationMonitoring:
    """Get or create global monitoring instance"""
    global _monitoring_instance
    if _monitoring_instance is None:
        _monitoring_instance = RecommendationMonitoring(config, db_connection)
    return _monitoring_instance

def record_recommendation_request(response_time_ms: float, success: bool = True,
                                cache_hit: bool = False, user_id: str = None,
                                recommendation_count: int = 0):
    """Convenience function to record recommendation request"""
    monitoring = get_monitoring_instance()
    return monitoring.record_request(response_time_ms, success, cache_hit, user_id, recommendation_count)

def record_user_feedback(user_id: str, item_id: str, rating: float,
                        feedback_type: str = "rating"):
    """Convenience function to record user feedback"""
    monitoring = get_monitoring_instance()
    return monitoring.record_user_feedback(user_id, item_id, rating, feedback_type)

def record_diversity_score(score: float, user_id: str = None, algorithm: str = "hybrid"):
    """Convenience function to record diversity score"""
    monitoring = get_monitoring_instance()
    return monitoring.record_diversity_score(score, user_id, algorithm)

def record_novelty_score(score: float, user_id: str = None, algorithm: str = "hybrid"):
    """Convenience function to record novelty score"""
    monitoring = get_monitoring_instance()
    return monitoring.record_novelty_score(score, user_id, algorithm)
