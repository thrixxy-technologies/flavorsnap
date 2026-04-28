"""
Advanced Memory Monitoring for FlavorSnap API
Implements comprehensive memory monitoring with metrics collection and performance analysis
"""
import os
import time
import threading
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import logging
import psutil
import gc
from memory_manager import MemorySnapshot, MemoryStatus, memory_manager
from gc_optimizer import GCPerformanceMonitor, gc_optimizer
from leak_detector import MemoryLeakDetector, leak_detector


class MonitoringLevel(Enum):
    """Monitoring detail levels"""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


class AlertThreshold(Enum):
    """Alert threshold types"""
    MEMORY_USAGE = "memory_usage"
    GROWTH_RATE = "growth_rate"
    COLLECTION_TIME = "collection_time"
    LEAK_DETECTION = "leak_detection"


@dataclass
class MemoryMetrics:
    """Comprehensive memory metrics"""
    timestamp: datetime
    process_memory_mb: float
    system_memory_mb: float
    available_memory_mb: float
    memory_usage_percent: float
    virtual_memory_mb: float
    swap_memory_mb: float
    swap_usage_percent: float
    gc_generation_0: int
    gc_generation_1: int
    gc_generation_2: int
    gc_collections_total: int
    gc_uncollectable: int
    tracked_objects: int
    total_objects: int
    leak_count: int
    threads_active: int
    file_handles_open: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class PerformanceMetrics:
    """Performance metrics related to memory"""
    timestamp: datetime
    avg_response_time_ms: float
    requests_per_second: float
    error_rate: float
    memory_efficiency: float
    gc_efficiency: float
    allocation_rate: float
    deallocation_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class MemoryAlert:
    """Memory alert data structure"""
    alert_id: str
    timestamp: datetime
    threshold_type: AlertThreshold
    severity: str
    message: str
    current_value: float
    threshold_value: float
    metadata: Dict[str, Any]
    acknowledged: bool = False
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['threshold_type'] = self.threshold_type.value
        return data


class MemoryMonitorConfig:
    """Memory monitor configuration"""
    
    # Monitoring intervals
    METRICS_INTERVAL = 30  # seconds
    PERFORMANCE_INTERVAL = 60  # seconds
    ALERT_CHECK_INTERVAL = 10  # seconds
    
    # Data retention
    METRICS_HISTORY_SIZE = 2880  # 24 hours at 30-second intervals
    PERFORMANCE_HISTORY_SIZE = 1440  # 24 hours at 1-minute intervals
    ALERT_HISTORY_SIZE = 1000
    
    # Alert thresholds
    MEMORY_WARNING_THRESHOLD = 80.0  # percent
    MEMORY_CRITICAL_THRESHOLD = 90.0  # percent
    GROWTH_RATE_WARNING = 10.0  # MB per minute
    GROWTH_RATE_CRITICAL = 50.0  # MB per minute
    GC_TIME_WARNING = 100.0  # milliseconds
    GC_TIME_CRITICAL = 500.0  # milliseconds
    LEAK_COUNT_WARNING = 5
    LEAK_COUNT_CRITICAL = 20
    
    # Performance targets
    TARGET_MEMORY_EFFICIENCY = 0.8
    TARGET_GC_EFFICIENCY = 0.7
    MAX_RESPONSE_TIME = 1000.0  # milliseconds


class MemoryMetricsCollector:
    """Collect memory and performance metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.process = psutil.Process()
    
    def collect_memory_metrics(self) -> MemoryMetrics:
        """Collect comprehensive memory metrics"""
        timestamp = datetime.now()
        
        # Process memory
        memory_info = self.process.memory_info()
        process_memory_mb = memory_info.rss / 1024 / 1024
        virtual_memory_mb = memory_info.vms / 1024 / 1024
        
        # System memory
        system_memory = psutil.virtual_memory()
        system_memory_mb = system_memory.total / 1024 / 1024
        available_memory_mb = system_memory.available / 1024 / 1024
        memory_usage_percent = system_memory.percent
        
        # Swap memory
        swap_memory = psutil.swap_memory()
        swap_memory_mb = swap_memory.total / 1024 / 1024
        swap_usage_percent = swap_memory.percent
        
        # GC metrics
        gc_counts = gc.get_count()
        gc_uncollectable = len(gc.garbage)
        
        # Object metrics
        tracked_objects = len(gc.get_objects())
        
        # Leak detection
        leak_summary = leak_detector.get_leak_summary()
        leak_count = leak_summary['active_leaks']
        
        # System resources
        threads_active = len(threading.enumerate())
        file_handles_open = len(self.process.open_files())
        
        return MemoryMetrics(
            timestamp=timestamp,
            process_memory_mb=process_memory_mb,
            system_memory_mb=system_memory_mb,
            available_memory_mb=available_memory_mb,
            memory_usage_percent=memory_usage_percent,
            virtual_memory_mb=virtual_memory_mb,
            swap_memory_mb=swap_memory_mb,
            swap_usage_percent=swap_usage_percent,
            gc_generation_0=gc_counts[0],
            gc_generation_1=gc_counts[1],
            gc_generation_2=gc_counts[2],
            gc_collections_total=sum(gc_counts),
            gc_uncollectable=gc_uncollectable,
            tracked_objects=tracked_objects,
            total_objects=tracked_objects,  # Simplified
            leak_count=leak_count,
            threads_active=threads_active,
            file_handles_open=file_handles_open
        )
    
    def collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect performance metrics"""
        timestamp = datetime.now()
        
        # Get recent memory metrics to calculate rates
        memory_info = memory_manager.get_memory_info()
        memory_history = memory_manager.get_memory_history(minutes=5)
        
        # Calculate allocation/deallocation rates
        allocation_rate = 0.0
        deallocation_rate = 0.0
        
        if len(memory_history) > 1:
            recent_metrics = memory_history[:2]
            time_diff = (recent_metrics[0].timestamp - recent_metrics[1].timestamp).total_seconds()
            if time_diff > 0:
                object_diff = recent_metrics[0].tracked_allocations - recent_metrics[1].tracked_allocations
                allocation_rate = object_diff / time_diff if object_diff > 0 else 0
        
        # Calculate efficiency metrics
        memory_efficiency = self._calculate_memory_efficiency()
        gc_efficiency = self._calculate_gc_efficiency()
        
        # Performance metrics (simplified - would integrate with actual request tracking)
        avg_response_time_ms = 100.0  # Placeholder
        requests_per_second = 10.0     # Placeholder
        error_rate = 0.01              # Placeholder
        
        return PerformanceMetrics(
            timestamp=timestamp,
            avg_response_time_ms=avg_response_time_ms,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            memory_efficiency=memory_efficiency,
            gc_efficiency=gc_efficiency,
            allocation_rate=allocation_rate,
            deallocation_rate=deallocation_rate
        )
    
    def _calculate_memory_efficiency(self) -> float:
        """Calculate memory efficiency score"""
        try:
            memory_info = memory_manager.get_memory_info()
            current_usage = memory_info['current']['memory_usage_percent']
            
            # Efficiency based on how well memory is utilized
            if current_usage < 50:
                return 1.0
            elif current_usage < 80:
                return 0.8
            elif current_usage < 90:
                return 0.6
            else:
                return 0.4
        except:
            return 0.5
    
    def _calculate_gc_efficiency(self) -> float:
        """Calculate GC efficiency score"""
        try:
            gc_report = gc_optimizer.get_performance_report()
            
            # Get recent optimization results
            optimizations = gc_optimizer.adaptive_optimizer.optimization_history
            if not optimizations:
                return 0.5
            
            recent_opt = optimizations[-1]
            if recent_opt.success:
                return min(1.0, recent_opt.performance_impact + 0.5)
            else:
                return 0.3
        except:
            return 0.5


class MemoryAlertManager:
    """Manage memory-related alerts"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.alerts: deque = deque(maxlen=MemoryMonitorConfig.ALERT_HISTORY_SIZE)
        self.alert_callbacks: List[Callable[[MemoryAlert], None]] = []
        self.last_alert_times: Dict[str, datetime] = {}
    
    def check_alerts(self, metrics: MemoryMetrics, performance_metrics: PerformanceMetrics) -> List[MemoryAlert]:
        """Check for alert conditions"""
        new_alerts = []
        
        # Memory usage alerts
        if metrics.memory_usage_percent >= MemoryMonitorConfig.MEMORY_CRITICAL_THRESHOLD:
            alert = self._create_alert(
                AlertThreshold.MEMORY_USAGE,
                "critical",
                f"Critical memory usage: {metrics.memory_usage_percent:.1f}%",
                metrics.memory_usage_percent,
                MemoryMonitorConfig.MEMORY_CRITICAL_THRESHOLD,
                {'process_memory_mb': metrics.process_memory_mb}
            )
            new_alerts.append(alert)
        elif metrics.memory_usage_percent >= MemoryMonitorConfig.MEMORY_WARNING_THRESHOLD:
            alert = self._create_alert(
                AlertThreshold.MEMORY_USAGE,
                "warning",
                f"High memory usage: {metrics.memory_usage_percent:.1f}%",
                metrics.memory_usage_percent,
                MemoryMonitorConfig.MEMORY_WARNING_THRESHOLD,
                {'process_memory_mb': metrics.process_memory_mb}
            )
            new_alerts.append(alert)
        
        # Leak count alerts
        if metrics.leak_count >= MemoryMonitorConfig.LEAK_COUNT_CRITICAL:
            alert = self._create_alert(
                AlertThreshold.LEAK_DETECTION,
                "critical",
                f"Critical number of memory leaks: {metrics.leak_count}",
                metrics.leak_count,
                MemoryMonitorConfig.LEAK_COUNT_CRITICAL,
                {'leak_summary': leak_detector.get_leak_summary()}
            )
            new_alerts.append(alert)
        elif metrics.leak_count >= MemoryMonitorConfig.LEAK_COUNT_WARNING:
            alert = self._create_alert(
                AlertThreshold.LEAK_DETECTION,
                "warning",
                f"Multiple memory leaks detected: {metrics.leak_count}",
                metrics.leak_count,
                MemoryMonitorConfig.LEAK_COUNT_WARNING,
                {'leak_summary': leak_detector.get_leak_summary()}
            )
            new_alerts.append(alert)
        
        # Growth rate alerts
        growth_rate = self._calculate_growth_rate(metrics)
        if growth_rate >= MemoryMonitorConfig.GROWTH_RATE_CRITICAL:
            alert = self._create_alert(
                AlertThreshold.GROWTH_RATE,
                "critical",
                f"Critical memory growth rate: {growth_rate:.1f} MB/min",
                growth_rate,
                MemoryMonitorConfig.GROWTH_RATE_CRITICAL,
                {'trend_direction': 'increasing'}
            )
            new_alerts.append(alert)
        elif growth_rate >= MemoryMonitorConfig.GROWTH_RATE_WARNING:
            alert = self._create_alert(
                AlertThreshold.GROWTH_RATE,
                "warning",
                f"High memory growth rate: {growth_rate:.1f} MB/min",
                growth_rate,
                MemoryMonitorConfig.GROWTH_RATE_WARNING,
                {'trend_direction': 'increasing'}
            )
            new_alerts.append(alert)
        
        # Performance alerts
        if performance_metrics.memory_efficiency < 0.5:
            alert = self._create_alert(
                AlertThreshold.MEMORY_USAGE,
                "warning",
                f"Low memory efficiency: {performance_metrics.memory_efficiency:.1%}",
                performance_metrics.memory_efficiency,
                MemoryMonitorConfig.TARGET_MEMORY_EFFICIENCY,
                {'efficiency_type': 'memory'}
            )
            new_alerts.append(alert)
        
        # Add new alerts to history
        for alert in new_alerts:
            self.alerts.append(alert)
            
            # Trigger callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Alert callback failed: {str(e)}")
        
        return new_alerts
    
    def _create_alert(self, threshold_type: AlertThreshold, severity: str, 
                     message: str, current_value: float, threshold_value: float,
                     metadata: Dict[str, Any]) -> MemoryAlert:
        """Create a new alert"""
        alert_key = f"{threshold_type.value}_{severity}"
        
        # Check if we recently sent the same alert
        if alert_key in self.last_alert_times:
            time_since_last = datetime.now() - self.last_alert_times[alert_key]
            if time_since_last < timedelta(minutes=5):  # Don't spam alerts
                return None
        
        alert = MemoryAlert(
            alert_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            threshold_type=threshold_type,
            severity=severity,
            message=message,
            current_value=current_value,
            threshold_value=threshold_value,
            metadata=metadata
        )
        
        self.last_alert_times[alert_key] = datetime.now()
        
        return alert
    
    def _calculate_growth_rate(self, metrics: MemoryMetrics) -> float:
        """Calculate memory growth rate in MB per minute"""
        try:
            memory_history = memory_manager.get_memory_history(minutes=10)
            
            if len(memory_history) < 2:
                return 0.0
            
            # Calculate growth rate over the last 10 minutes
            recent = memory_history[0]
            oldest = memory_history[-1]
            
            time_diff = (recent.timestamp - oldest.timestamp).total_seconds() / 60  # minutes
            memory_diff = recent.process_memory - oldest.process_memory
            
            if time_diff > 0:
                return memory_diff / (1024 * 1024) / time_diff  # MB per minute
            
            return 0.0
        except:
            return 0.0
    
    def add_alert_callback(self, callback: Callable[[MemoryAlert], None]):
        """Add alert callback"""
        self.alert_callbacks.append(callback)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                self.logger.info(f"Alert {alert_id} acknowledged")
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                self.logger.info(f"Alert {alert_id} resolved")
                return True
        return False
    
    def get_active_alerts(self) -> List[MemoryAlert]:
        """Get active (unresolved) alerts"""
        return [alert for alert in self.alerts if not alert.resolved]


class MemoryMonitoringSystem:
    """Main memory monitoring system"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.metrics_collector = MemoryMetricsCollector()
        self.alert_manager = MemoryAlertManager()
        
        self.monitoring_active = False
        self.monitoring_level = MonitoringLevel.BASIC
        
        # Metrics storage
        self.memory_metrics: deque = deque(maxlen=MemoryMonitorConfig.METRICS_HISTORY_SIZE)
        self.performance_metrics: deque = deque(maxlen=MemoryMonitorConfig.PERFORMANCE_HISTORY_SIZE)
        
        # Monitoring threads
        self.metrics_thread = None
        self.performance_thread = None
        self.alert_thread = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize monitoring system with Flask app"""
        self.app = app
        
        # Add default alert callback
        self.alert_manager.add_alert_callback(self._log_alert)
        
        # Start monitoring
        self.start_monitoring()
        
        self.logger.info("Memory monitoring system initialized")
    
    def start_monitoring(self, level: MonitoringLevel = None):
        """Start memory monitoring"""
        if self.monitoring_active:
            return
        
        if level:
            self.monitoring_level = level
        
        self.monitoring_active = True
        
        # Start monitoring threads
        self.metrics_thread = threading.Thread(target=self._metrics_loop, daemon=True)
        self.metrics_thread.start()
        
        self.performance_thread = threading.Thread(target=self._performance_loop, daemon=True)
        self.performance_thread.start()
        
        self.alert_thread = threading.Thread(target=self._alert_loop, daemon=True)
        self.alert_thread.start()
        
        self.logger.info(f"Memory monitoring started at {self.monitoring_level.value} level")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.monitoring_active = False
        
        if self.metrics_thread:
            self.metrics_thread.join(timeout=5)
        if self.performance_thread:
            self.performance_thread.join(timeout=5)
        if self.alert_thread:
            self.alert_thread.join(timeout=5)
        
        self.logger.info("Memory monitoring stopped")
    
    def _metrics_loop(self):
        """Metrics collection loop"""
        while self.monitoring_active:
            try:
                # Collect memory metrics
                metrics = self.metrics_collector.collect_memory_metrics()
                self.memory_metrics.append(metrics)
                
                # Adjust collection frequency based on level
                if self.monitoring_level == MonitoringLevel.BASIC:
                    sleep_time = MemoryMonitorConfig.METRICS_INTERVAL * 2
                elif self.monitoring_level == MonitoringLevel.DETAILED:
                    sleep_time = MemoryMonitorConfig.METRICS_INTERVAL
                else:  # COMPREHENSIVE
                    sleep_time = MemoryMonitorConfig.METRICS_INTERVAL // 2
                
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Metrics collection error: {str(e)}")
                time.sleep(MemoryMonitorConfig.METRICS_INTERVAL)
    
    def _performance_loop(self):
        """Performance metrics collection loop"""
        while self.monitoring_active:
            try:
                # Collect performance metrics
                metrics = self.metrics_collector.collect_performance_metrics()
                self.performance_metrics.append(metrics)
                
                time.sleep(MemoryMonitorConfig.PERFORMANCE_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Performance metrics collection error: {str(e)}")
                time.sleep(MemoryMonitorConfig.PERFORMANCE_INTERVAL)
    
    def _alert_loop(self):
        """Alert checking loop"""
        while self.monitoring_active:
            try:
                # Get latest metrics
                latest_memory = self.memory_metrics[-1] if self.memory_metrics else None
                latest_performance = self.performance_metrics[-1] if self.performance_metrics else None
                
                if latest_memory and latest_performance:
                    self.alert_manager.check_alerts(latest_memory, latest_performance)
                
                time.sleep(MemoryMonitorConfig.ALERT_CHECK_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Alert checking error: {str(e)}")
                time.sleep(MemoryMonitorConfig.ALERT_CHECK_INTERVAL)
    
    def _log_alert(self, alert: MemoryAlert):
        """Log alert"""
        if alert.severity == "critical":
            self.logger.critical(f"Memory Alert: {alert.message}")
        elif alert.severity == "warning":
            self.logger.warning(f"Memory Alert: {alert.message}")
        else:
            self.logger.info(f"Memory Alert: {alert.message}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring system status"""
        return {
            'monitoring_active': self.monitoring_active,
            'monitoring_level': self.monitoring_level.value,
            'metrics_collected': len(self.memory_metrics),
            'performance_metrics_collected': len(self.performance_metrics),
            'active_alerts': len(self.alert_manager.get_active_alerts()),
            'total_alerts': len(self.alert_manager.alerts),
            'last_metrics_time': self.memory_metrics[-1].timestamp.isoformat() if self.memory_metrics else None,
            'last_performance_time': self.performance_metrics[-1].timestamp.isoformat() if self.performance_metrics else None
        }
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current memory and performance metrics"""
        latest_memory = self.memory_metrics[-1] if self.memory_metrics else None
        latest_performance = self.performance_metrics[-1] if self.performance_metrics else None
        
        return {
            'memory_metrics': latest_memory.to_dict() if latest_memory else None,
            'performance_metrics': latest_performance.to_dict() if latest_performance else None,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_metrics_history(self, hours: int = 24) -> Dict[str, List[Dict[str, Any]]]:
        """Get metrics history"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter memory metrics
        memory_history = [
            m.to_dict() for m in self.memory_metrics 
            if m.timestamp >= cutoff_time
        ]
        
        # Filter performance metrics
        performance_history = [
            p.to_dict() for p in self.performance_metrics 
            if p.timestamp >= cutoff_time
        ]
        
        return {
            'memory_metrics': memory_history,
            'performance_metrics': performance_history,
            'time_range_hours': hours
        }
    
    def get_alerts(self, active_only: bool = True, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alerts"""
        if active_only:
            alerts = self.alert_manager.get_active_alerts()
        else:
            alerts = list(self.alert_manager.alerts)
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [alert.to_dict() for alert in alerts[:limit]]
    
    def get_memory_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive memory analysis"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter metrics
        recent_memory = [m for m in self.memory_metrics if m.timestamp >= cutoff_time]
        recent_performance = [p for p in self.performance_metrics if p.timestamp >= cutoff_time]
        
        if not recent_memory:
            return {}
        
        # Calculate statistics
        memory_usage = [m.memory_usage_percent for m in recent_memory]
        process_memory = [m.process_memory_mb for m in recent_memory]
        gc_collections = [m.gc_collections_total for m in recent_memory]
        
        analysis = {
            'time_range_hours': hours,
            'sample_count': len(recent_memory),
            'memory_usage': {
                'current': memory_usage[-1] if memory_usage else 0,
                'average': statistics.mean(memory_usage) if memory_usage else 0,
                'min': min(memory_usage) if memory_usage else 0,
                'max': max(memory_usage) if memory_usage else 0,
                'trend': 'increasing' if len(memory_usage) > 1 and memory_usage[-1] > memory_usage[0] else 'stable'
            },
            'process_memory': {
                'current': process_memory[-1] if process_memory else 0,
                'average': statistics.mean(process_memory) if process_memory else 0,
                'min': min(process_memory) if process_memory else 0,
                'max': max(process_memory) if process_memory else 0
            },
            'gc_activity': {
                'current_collections': gc_collections[-1] if gc_collections else 0,
                'total_collections': max(gc_collections) - min(gc_collections) if len(gc_collections) > 1 else 0,
                'avg_uncollectable': statistics.mean([m.gc_uncollectable for m in recent_memory]) if recent_memory else 0
            },
            'performance': {
                'avg_efficiency': statistics.mean([p.memory_efficiency for p in recent_performance]) if recent_performance else 0,
                'avg_gc_efficiency': statistics.mean([p.gc_efficiency for p in recent_performance]) if recent_performance else 0
            }
        }
        
        return analysis
    
    def export_monitoring_report(self, hours: int = 24, format: str = 'json') -> str:
        """Export comprehensive monitoring report"""
        # Get all data
        status = self.get_monitoring_status()
        current = self.get_current_metrics()
        history = self.get_metrics_history(hours)
        alerts = self.get_alerts(active_only=False)
        analysis = self.get_memory_analysis(hours)
        
        if format == 'json':
            report_data = {
                'generated_at': datetime.now().isoformat(),
                'time_range_hours': hours,
                'monitoring_status': status,
                'current_metrics': current,
                'metrics_history': history,
                'alerts': alerts,
                'analysis': analysis,
                'summary': {
                    'total_metrics_points': len(history['memory_metrics']) + len(history['performance_metrics']),
                    'total_alerts': len(alerts),
                    'active_alerts': len([a for a in alerts if not a['resolved']]),
                    'memory_status': 'healthy' if current['memory_metrics']['memory_usage_percent'] < 80 else 'warning'
                }
            }
            
            return json.dumps(report_data, indent=2)
        
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write memory metrics
            if history['memory_metrics']:
                writer.writerow(['Memory Metrics'])
                header = ['timestamp', 'process_memory_mb', 'memory_usage_percent', 'gc_collections_total', 'leak_count']
                writer.writerow(header)
                
                for metric in history['memory_metrics']:
                    row = [
                        metric['timestamp'],
                        metric['process_memory_mb'],
                        metric['memory_usage_percent'],
                        metric['gc_collections_total'],
                        metric['leak_count']
                    ]
                    writer.writerow(row)
                
                writer.writerow([])  # Empty row
            
            # Write performance metrics
            if history['performance_metrics']:
                writer.writerow(['Performance Metrics'])
                header = ['timestamp', 'memory_efficiency', 'gc_efficiency', 'allocation_rate']
                writer.writerow(header)
                
                for metric in history['performance_metrics']:
                    row = [
                        metric['timestamp'],
                        metric['memory_efficiency'],
                        metric['gc_efficiency'],
                        metric['allocation_rate']
                    ]
                    writer.writerow(row)
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Initialize global memory monitoring system
memory_monitoring = MemoryMonitoringSystem()
