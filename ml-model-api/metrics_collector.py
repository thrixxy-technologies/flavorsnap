"""
Advanced Metrics Collector for FlavorSnap
Real-time metrics collection with aggregation and storage
"""

import asyncio
import json
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict, deque
import statistics
import psutil
import redis
from sqlalchemy import create_engine, text
import numpy as np
import pandas as pd
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger(__name__)


@dataclass
class MetricDefinition:
    """Metric definition with metadata"""
    name: str
    type: str  # counter, gauge, histogram, summary
    description: str
    labels: List[str] = field(default_factory=list)
    unit: str = ""
    aggregation: List[str] = field(default_factory=list)  # sum, avg, min, max, p95, p99


@dataclass
class MetricValue:
    """Individual metric value with metadata"""
    metric_name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsStorage:
    """Metrics storage backend interface"""
    
    def store_metric(self, metric_value: MetricValue):
        """Store metric value"""
        raise NotImplementedError
    
    def query_metrics(self, metric_name: str, start_time: datetime, end_time: datetime, 
                     labels: Dict[str, str] = None) -> List[MetricValue]:
        """Query metrics"""
        raise NotImplementedError
    
    def aggregate_metrics(self, metric_name: str, start_time: datetime, end_time: datetime,
                         aggregation: str, interval: timedelta) -> List[MetricValue]:
        """Aggregate metrics"""
        raise NotImplementedError


class RedisMetricsStorage(MetricsStorage):
    """Redis-based metrics storage"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.key_prefix = "metrics:"
        self.retention_days = 7
    
    def store_metric(self, metric_value: MetricValue):
        """Store metric in Redis"""
        key = f"{self.key_prefix}{metric_value.metric_name}"
        
        # Create metric data
        metric_data = {
            'value': metric_value.value,
            'timestamp': metric_value.timestamp.isoformat(),
            'labels': metric_value.labels,
            'metadata': metric_value.metadata
        }
        
        # Store in sorted set with timestamp as score
        score = metric_value.timestamp.timestamp()
        self.redis.zadd(key, {json.dumps(metric_data): score})
        
        # Clean old data
        cutoff_score = (datetime.now() - timedelta(days=self.retention_days)).timestamp()
        self.redis.zremrangebyscore(key, 0, cutoff_score)
    
    def query_metrics(self, metric_name: str, start_time: datetime, end_time: datetime,
                     labels: Dict[str, str] = None) -> List[MetricValue]:
        """Query metrics from Redis"""
        key = f"{self.key_prefix}{metric_name}"
        
        # Get data by timestamp range
        start_score = start_time.timestamp()
        end_score = end_time.timestamp()
        
        raw_data = self.redis.zrangebyscore(key, start_score, end_score, withscores=True)
        
        metrics = []
        for data_json, score in raw_data:
            try:
                data = json.loads(data_json)
                
                # Filter by labels if specified
                if labels:
                    match = True
                    for label_key, label_value in labels.items():
                        if data.get('labels', {}).get(label_key) != label_value:
                            match = False
                            break
                    if not match:
                        continue
                
                metric = MetricValue(
                    metric_name=metric_name,
                    value=data['value'],
                    timestamp=datetime.fromisoformat(data['timestamp']),
                    labels=data.get('labels', {}),
                    metadata=data.get('metadata', {})
                )
                metrics.append(metric)
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error parsing metric data: {e}")
                continue
        
        return metrics
    
    def aggregate_metrics(self, metric_name: str, start_time: datetime, end_time: datetime,
                         aggregation: str, interval: timedelta) -> List[MetricValue]:
        """Aggregate metrics in Redis"""
        # Get raw metrics
        raw_metrics = self.query_metrics(metric_name, start_time, end_time)
        
        if not raw_metrics:
            return []
        
        # Group by time intervals
        grouped_metrics = defaultdict(list)
        for metric in raw_metrics:
            # Calculate interval bucket
            interval_start = self._get_interval_start(metric.timestamp, interval)
            grouped_metrics[interval_start].append(metric.value)
        
        # Apply aggregation function
        aggregated_metrics = []
        for interval_start, values in grouped_metrics.items():
            aggregated_value = self._apply_aggregation(values, aggregation)
            
            aggregated_metric = MetricValue(
                metric_name=f"{metric_name}_aggregated",
                value=aggregated_value,
                timestamp=interval_start,
                labels={'aggregation': aggregation, 'interval': str(interval)},
                metadata={'sample_count': len(values)}
            )
            aggregated_metrics.append(aggregated_metric)
        
        return aggregated_metrics
    
    def _get_interval_start(self, timestamp: datetime, interval: timedelta) -> datetime:
        """Get interval start time for timestamp"""
        seconds = int(timestamp.timestamp())
        interval_seconds = int(interval.total_seconds())
        interval_start = seconds - (seconds % interval_seconds)
        return datetime.fromtimestamp(interval_start)
    
    def _apply_aggregation(self, values: List[float], aggregation: str) -> float:
        """Apply aggregation function to values"""
        if not values:
            return 0.0
        
        if aggregation == 'sum':
            return sum(values)
        elif aggregation == 'avg':
            return statistics.mean(values)
        elif aggregation == 'min':
            return min(values)
        elif aggregation == 'max':
            return max(values)
        elif aggregation == 'p95':
            return np.percentile(values, 95)
        elif aggregation == 'p99':
            return np.percentile(values, 99)
        else:
            return statistics.mean(values)


class InfluxDBMetricsStorage(MetricsStorage):
    """InfluxDB-based metrics storage"""
    
    def __init__(self, influx_client: influxdb_client.InfluxDBClient, bucket: str, org: str):
        self.client = influx_client
        self.bucket = bucket
        self.org = org
        self.write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    
    def store_metric(self, metric_value: MetricValue):
        """Store metric in InfluxDB"""
        point = influxdb_client.Point(metric_value.metric_name) \
            .tag(**metric_value.labels) \
            .field("value", metric_value.value) \
            .time(metric_value.timestamp)
        
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)
    
    def query_metrics(self, metric_name: str, start_time: datetime, end_time: datetime,
                     labels: Dict[str, str] = None) -> List[MetricValue]:
        """Query metrics from InfluxDB"""
        query_api = self.client.query_api()
        
        # Build query
        query = f'''
        from(bucket: "{self.bucket}")
        |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
        |> filter(fn: (r) => r["_measurement"] == "{metric_name}")
        '''
        
        # Add label filters
        if labels:
            for label_key, label_value in labels.items():
                query += f'|> filter(fn: (r) => r["{label_key}"] == "{label_value}")\n'
        
        query += '|> filter(fn: (r) => r["_field"] == "value")'
        
        try:
            result = query_api.query(query)
            
            metrics = []
            for table in result:
                for record in table.records:
                    metric = MetricValue(
                        metric_name=metric_name,
                        value=record.get_value(),
                        timestamp=record.get_time(),
                        labels={k: v for k, v in record.values.items() if k.startswith('_') == False},
                        metadata={}
                    )
                    metrics.append(metric)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error querying InfluxDB: {e}")
            return []
    
    def aggregate_metrics(self, metric_name: str, start_time: datetime, end_time: datetime,
                         aggregation: str, interval: timedelta) -> List[MetricValue]:
        """Aggregate metrics in InfluxDB"""
        query_api = self.client.query_api()
        
        # Map aggregation to InfluxDB functions
        agg_function = {
            'sum': 'sum',
            'avg': 'mean',
            'min': 'min',
            'max': 'max',
            'p95': 'percentile(95.0)',
            'p99': 'percentile(99.0)'
        }.get(aggregation, 'mean')
        
        interval_str = f"{int(interval.total_seconds())}s"
        
        query = f'''
        from(bucket: "{self.bucket}")
        |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
        |> filter(fn: (r) => r["_measurement"] == "{metric_name}")
        |> filter(fn: (r) => r["_field"] == "value")
        |> aggregateWindow(every: {interval_str}, fn: {agg_function}, createEmpty: false)
        '''
        
        try:
            result = query_api.query(query)
            
            metrics = []
            for table in result:
                for record in table.records:
                    metric = MetricValue(
                        metric_name=f"{metric_name}_aggregated",
                        value=record.get_value(),
                        timestamp=record.get_time(),
                        labels={'aggregation': aggregation, 'interval': str(interval)},
                        metadata={}
                    )
                    metrics.append(metric)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error aggregating InfluxDB metrics: {e}")
            return []


class AdvancedMetricsCollector:
    """Advanced metrics collector with multiple backends and real-time processing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics_definitions = {}
        self.storage_backends = []
        self.prometheus_registry = CollectorRegistry()
        self.prometheus_metrics = {}
        
        # Real-time processing
        self.real_time_metrics = defaultdict(lambda: deque(maxlen=1000))
        self.aggregation_cache = {}
        
        # Background collection
        self.collection_threads = []
        self.stop_event = threading.Event()
        
        # Setup storage backends
        self._setup_storage_backends()
        
        # Setup Prometheus metrics
        self._setup_prometheus_metrics()
        
        # Setup default metric definitions
        self._setup_default_metrics()
        
        # Start collection
        self.start_collection()
    
    def _setup_storage_backends(self):
        """Setup metrics storage backends"""
        storage_config = self.config.get('storage', {})
        
        # Redis backend
        if 'redis' in storage_config:
            redis_config = storage_config['redis']
            redis_client = redis.Redis(
                host=redis_config.get('host', 'localhost'),
                port=redis_config.get('port', 6379),
                db=redis_config.get('db', 0),
                decode_responses=True
            )
            self.storage_backends.append(RedisMetricsStorage(redis_client))
        
        # InfluxDB backend
        if 'influxdb' in storage_config:
            influx_config = storage_config['influxdb']
            influx_client = influxdb_client.InfluxDBClient(
                url=influx_config.get('url'),
                token=influx_config.get('token'),
                org=influx_config.get('org')
            )
            self.storage_backends.append(InfluxDBMetricsStorage(
                influx_client,
                influx_config.get('bucket', 'metrics'),
                influx_config.get('org', 'flavorsnap')
            ))
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        # System metrics
        self.prometheus_metrics['system_cpu_usage'] = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.prometheus_registry
        )
        
        self.prometheus_metrics['system_memory_usage'] = Gauge(
            'system_memory_usage_percent',
            'System memory usage percentage',
            registry=self.prometheus_registry
        )
        
        self.prometheus_metrics['system_disk_usage'] = Gauge(
            'system_disk_usage_percent',
            'System disk usage percentage',
            registry=self.prometheus_registry
        )
        
        # Application metrics
        self.prometheus_metrics['http_requests_total'] = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.prometheus_registry
        )
        
        self.prometheus_metrics['http_request_duration'] = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint'],
            registry=self.prometheus_registry
        )
        
        # ML Model metrics
        self.prometheus_metrics['model_predictions_total'] = Counter(
            'model_predictions_total',
            'Total model predictions',
            ['model_version', 'status'],
            registry=self.prometheus_registry
        )
        
        self.prometheus_metrics['model_inference_duration'] = Histogram(
            'model_inference_duration_seconds',
            'Model inference duration',
            ['model_version'],
            registry=self.prometheus_registry
        )
        
        self.prometheus_metrics['model_accuracy'] = Gauge(
            'model_accuracy_score',
            'Model accuracy score',
            ['model_version'],
            registry=self.prometheus_registry
        )
    
    def _setup_default_metrics(self):
        """Setup default metric definitions"""
        default_metrics = [
            MetricDefinition(
                name="cpu_usage",
                type="gauge",
                description="CPU usage percentage",
                unit="percent",
                aggregation=["avg", "max", "p95"]
            ),
            MetricDefinition(
                name="memory_usage",
                type="gauge",
                description="Memory usage percentage",
                unit="percent",
                aggregation=["avg", "max", "p95"]
            ),
            MetricDefinition(
                name="disk_usage",
                type="gauge",
                description="Disk usage percentage",
                unit="percent",
                aggregation=["avg", "max"]
            ),
            MetricDefinition(
                name="http_request_count",
                type="counter",
                description="HTTP request count",
                labels=["method", "endpoint", "status"],
                aggregation=["sum", "rate"]
            ),
            MetricDefinition(
                name="http_request_duration",
                type="histogram",
                description="HTTP request duration",
                unit="seconds",
                labels=["method", "endpoint"],
                aggregation=["avg", "p95", "p99"]
            ),
            MetricDefinition(
                name="model_prediction_count",
                type="counter",
                description="Model prediction count",
                labels=["model_version", "status"],
                aggregation=["sum", "rate"]
            ),
            MetricDefinition(
                name="model_inference_time",
                type="histogram",
                description="Model inference time",
                unit="seconds",
                labels=["model_version"],
                aggregation=["avg", "p95", "p99"]
            ),
            MetricDefinition(
                name="model_accuracy",
                type="gauge",
                description="Model accuracy score",
                labels=["model_version"],
                aggregation=["avg", "min"]
            )
        ]
        
        for metric_def in default_metrics:
            self.metrics_definitions[metric_def.name] = metric_def
    
    def start_collection(self):
        """Start metrics collection"""
        # System metrics collection
        system_thread = threading.Thread(target=self._collect_system_metrics, daemon=True)
        system_thread.start()
        self.collection_threads.append(system_thread)
        
        # Application metrics collection (if configured)
        if self.config.get('collect_application_metrics', True):
            app_thread = threading.Thread(target=self._collect_application_metrics, daemon=True)
            app_thread.start()
            self.collection_threads.append(app_thread)
        
        logger.info("Started metrics collection")
    
    def stop_collection(self):
        """Stop metrics collection"""
        self.stop_event.set()
        for thread in self.collection_threads:
            thread.join(timeout=5)
        logger.info("Stopped metrics collection")
    
    def _collect_system_metrics(self):
        """Collect system metrics"""
        while not self.stop_event.is_set():
            try:
                timestamp = datetime.now()
                
                # CPU usage
                cpu_usage = psutil.cpu_percent(interval=1)
                self.record_metric("cpu_usage", cpu_usage, timestamp)
                self.prometheus_metrics['system_cpu_usage'].set(cpu_usage)
                
                # Memory usage
                memory = psutil.virtual_memory()
                memory_usage = memory.percent
                self.record_metric("memory_usage", memory_usage, timestamp)
                self.prometheus_metrics['system_memory_usage'].set(memory_usage)
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_usage = (disk.used / disk.total) * 100
                self.record_metric("disk_usage", disk_usage, timestamp)
                self.prometheus_metrics['system_disk_usage'].set(disk_usage)
                
                # Network I/O
                network = psutil.net_io_counters()
                self.record_metric("network_bytes_sent", network.bytes_sent, timestamp)
                self.record_metric("network_bytes_recv", network.bytes_recv, timestamp)
                
                # Process count
                process_count = len(psutil.pids())
                self.record_metric("process_count", process_count, timestamp)
                
                time.sleep(self.config.get('collection_interval', 30))
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                time.sleep(5)
    
    def _collect_application_metrics(self):
        """Collect application-specific metrics"""
        while not self.stop_event.is_set():
            try:
                timestamp = datetime.now()
                
                # Database connection pool (placeholder)
                db_connections = getattr(self, '_db_connections', 5)
                self.record_metric("db_connections_active", db_connections, timestamp)
                
                # Cache metrics (placeholder)
                cache_hit_rate = getattr(self, '_cache_hit_rate', 0.85)
                self.record_metric("cache_hit_rate", cache_hit_rate, timestamp)
                
                # Active user sessions (placeholder)
                active_sessions = getattr(self, '_active_sessions', 100)
                self.record_metric("active_sessions", active_sessions, timestamp)
                
                time.sleep(self.config.get('collection_interval', 30))
                
            except Exception as e:
                logger.error(f"Error collecting application metrics: {e}")
                time.sleep(5)
    
    def record_metric(self, metric_name: str, value: float, timestamp: datetime = None,
                     labels: Dict[str, str] = None, metadata: Dict[str, Any] = None):
        """Record a metric value"""
        if timestamp is None:
            timestamp = datetime.now()
        
        if labels is None:
            labels = {}
        
        if metadata is None:
            metadata = {}
        
        # Create metric value
        metric_value = MetricValue(
            metric_name=metric_name,
            value=value,
            timestamp=timestamp,
            labels=labels,
            metadata=metadata
        )
        
        # Store in real-time cache
        self.real_time_metrics[metric_name].append(metric_value)
        
        # Store in backends
        for backend in self.storage_backends:
            try:
                backend.store_metric(metric_value)
            except Exception as e:
                logger.error(f"Error storing metric in {backend.__class__.__name__}: {e}")
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metric"""
        timestamp = datetime.now()
        labels = {
            'method': method,
            'endpoint': endpoint,
            'status_code': str(status_code)
        }
        
        # Record request count
        self.record_metric("http_request_count", 1, timestamp, labels)
        
        # Update Prometheus metrics
        self.prometheus_metrics['http_requests_total'].labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()
        
        # Record request duration
        duration_labels = {'method': method, 'endpoint': endpoint}
        self.record_metric("http_request_duration", duration, timestamp, duration_labels)
        
        # Update Prometheus histogram
        self.prometheus_metrics['http_request_duration'].labels(
            method=method, endpoint=endpoint
        ).observe(duration)
    
    def record_model_prediction(self, model_version: str, status: str, inference_time: float, accuracy: float = None):
        """Record model prediction metric"""
        timestamp = datetime.now()
        labels = {
            'model_version': model_version,
            'status': status
        }
        
        # Record prediction count
        self.record_metric("model_prediction_count", 1, timestamp, labels)
        
        # Update Prometheus counter
        self.prometheus_metrics['model_predictions_total'].labels(
            model_version=model_version, status=status
        ).inc()
        
        # Record inference time
        time_labels = {'model_version': model_version}
        self.record_metric("model_inference_time", inference_time, timestamp, time_labels)
        
        # Update Prometheus histogram
        self.prometheus_metrics['model_inference_duration'].labels(
            model_version=model_version
        ).observe(inference_time)
        
        # Record accuracy if provided
        if accuracy is not None:
            self.record_metric("model_accuracy", accuracy, timestamp, time_labels)
            
            # Update Prometheus gauge
            self.prometheus_metrics['model_accuracy'].labels(
                model_version=model_version
            ).set(accuracy)
    
    def query_metrics(self, metric_name: str, start_time: datetime, end_time: datetime,
                     labels: Dict[str, str] = None) -> List[MetricValue]:
        """Query metrics from all backends"""
        all_metrics = []
        
        for backend in self.storage_backends:
            try:
                metrics = backend.query_metrics(metric_name, start_time, end_time, labels)
                all_metrics.extend(metrics)
            except Exception as e:
                logger.error(f"Error querying metrics from {backend.__class__.__name__}: {e}")
        
        # Sort by timestamp
        all_metrics.sort(key=lambda x: x.timestamp)
        return all_metrics
    
    def aggregate_metrics(self, metric_name: str, start_time: datetime, end_time: datetime,
                         aggregation: str, interval: timedelta) -> List[MetricValue]:
        """Aggregate metrics"""
        cache_key = f"{metric_name}_{aggregation}_{interval.total_seconds()}_{start_time.timestamp()}"
        
        # Check cache
        if cache_key in self.aggregation_cache:
            cached_time, cached_result = self.aggregation_cache[cache_key]
            if datetime.now() - cached_time < timedelta(minutes=5):  # 5-minute cache
                return cached_result
        
        aggregated_metrics = []
        
        for backend in self.storage_backends:
            try:
                metrics = backend.aggregate_metrics(metric_name, start_time, end_time, aggregation, interval)
                aggregated_metrics.extend(metrics)
            except Exception as e:
                logger.error(f"Error aggregating metrics in {backend.__class__.__name__}: {e}")
        
        # Sort and cache result
        aggregated_metrics.sort(key=lambda x: x.timestamp)
        self.aggregation_cache[cache_key] = (datetime.now(), aggregated_metrics)
        
        return aggregated_metrics
    
    def get_real_time_metrics(self, metric_name: str, minutes: int = 5) -> List[MetricValue]:
        """Get real-time metrics from cache"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        return [
            metric for metric in self.real_time_metrics[metric_name]
            if metric.timestamp >= cutoff_time
        ]
    
    def get_metric_summary(self, metric_name: str, minutes: int = 60) -> Dict[str, Any]:
        """Get metric summary statistics"""
        metrics = self.get_real_time_metrics(metric_name, minutes)
        
        if not metrics:
            return {}
        
        values = [metric.value for metric in metrics]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': statistics.mean(values),
            'median': statistics.median(values),
            'std': statistics.stdev(values) if len(values) > 1 else 0,
            'p95': np.percentile(values, 95),
            'p99': np.percentile(values, 99),
            'latest': values[-1] if values else None,
            'trend': self._calculate_trend(values)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction"""
        if len(values) < 2:
            return "stable"
        
        # Simple trend calculation
        recent_avg = statistics.mean(values[-10:]) if len(values) >= 10 else statistics.mean(values[-len(values)//2:])
        older_avg = statistics.mean(values[:10]) if len(values) >= 10 else statistics.mean(values[:len(values)//2])
        
        diff_percent = ((recent_avg - older_avg) / older_avg) * 100 if older_avg != 0 else 0
        
        if diff_percent > 5:
            return "increasing"
        elif diff_percent < -5:
            return "decreasing"
        else:
            return "stable"
    
    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        return generate_latest(self.prometheus_registry).decode('utf-8')
    
    def add_metric_definition(self, metric_def: MetricDefinition):
        """Add metric definition"""
        self.metrics_definitions[metric_def.name] = metric_def
        logger.info(f"Added metric definition: {metric_def.name}")
    
    def get_metric_definitions(self) -> Dict[str, MetricDefinition]:
        """Get all metric definitions"""
        return self.metrics_definitions.copy()


# Global metrics collector
metrics_collector = None


def initialize_metrics_collector(config: Dict[str, Any]) -> AdvancedMetricsCollector:
    """Initialize global metrics collector"""
    global metrics_collector
    metrics_collector = AdvancedMetricsCollector(config)
    return metrics_collector


def get_metrics_collector() -> Optional[AdvancedMetricsCollector]:
    """Get global metrics collector instance"""
    return metrics_collector
