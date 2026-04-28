#!/usr/bin/env python3
"""
Performance Monitor for FlavorSnap Logging System
Implements performance monitoring and optimization for logging infrastructure
"""

import asyncio
import time
import psutil
import json
import aiohttp
import aiofiles
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging
import prometheus_client as prom

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str]
    threshold: Optional[float]

@dataclass
class SystemResource:
    """System resource information"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_io_read_mb: float
    network_io_write_mb: float
    timestamp: datetime

@dataclass
class LogPerformance:
    """Log processing performance metrics"""
    logs_processed_per_second: float
    average_processing_time_ms: float
    p95_processing_time_ms: float
    memory_usage_mb: float
    disk_io_mb_per_second: float
    error_rate_percent: float
    timestamp: datetime

class PrometheusMetrics:
    """Prometheus metrics for performance monitoring"""
    
    def __init__(self):
        # System metrics
        self.cpu_usage = prom.Gauge('logging_system_cpu_usage_percent', 'CPU usage percentage')
        self.memory_usage = prom.Gauge('logging_system_memory_usage_percent', 'Memory usage percentage')
        self.disk_usage = prom.Gauge('logging_system_disk_usage_percent', 'Disk usage percentage')
        self.network_io = prom.Gauge('logging_system_network_io_mb', 'Network I/O in MB')
        
        # Log processing metrics
        self.logs_processed = prom.Counter('logging_logs_processed_total', 'Total logs processed', ['source', 'status'])
        self.processing_time = prom.Histogram('logging_processing_duration_seconds', 'Log processing time', ['operation'])
        self.log_throughput = prom.Gauge('logging_throughput_logs_per_second', 'Logs processed per second')
        self.error_rate = prom.Gauge('logging_error_rate_percent', 'Log processing error rate')
        
        # Alert metrics
        self.performance_alerts = prom.Counter('logging_performance_alerts_total', 'Performance alerts', ['type'])
        self.resource_thresholds = prom.Gauge('logging_resource_thresholds', 'Resource threshold breaches', ['resource'])
        
        # Health metrics
        self.health_score = prom.Gauge('logging_health_score', 'Overall logging system health score')
        self.uptime = prom.Counter('logging_uptime_seconds_total', 'System uptime in seconds')

class PerformanceMonitor:
    """Advanced performance monitor for logging system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics = PrometheusMetrics()
        self.performance_history: deque = deque(maxlen=1000)
        self.alert_thresholds = config.get('thresholds', {
            'cpu_warning': 70.0,
            'cpu_critical': 90.0,
            'memory_warning': 75.0,
            'memory_critical': 90.0,
            'disk_warning': 80.0,
            'disk_critical': 95.0,
            'processing_time_warning': 1000.0,  # 1 second
            'processing_time_critical': 5000.0,  # 5 seconds
            'error_rate_warning': 5.0,
            'error_rate_critical': 15.0,
            'throughput_warning': 100.0,  # logs per second
            'throughput_critical': 50.0
        })
        
        # Performance tracking
        self.log_processing_times: deque = deque(maxlen=1000)
        self.error_count = 0
        self.total_logs_processed = 0
        self.start_time = time.time()
        
        # System resource tracking
        self.resource_history: deque = deque(maxlen=100)
        self.last_network_io = None
        
        # Alert tracking
        self.active_alerts: Dict[str, datetime] = {}
        self.alert_cooldown = timedelta(minutes=5)
    
    async def start_monitoring(self):
        """Start continuous performance monitoring"""
        logger.info("Starting performance monitoring")
        
        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._monitor_system_resources()),
            asyncio.create_task(self._monitor_log_performance()),
            asyncio.create_task(self._check_performance_thresholds()),
            asyncio.create_task(self._generate_performance_reports()),
            asyncio.create_task(self._update_prometheus_metrics())
        ]
        
        await asyncio.gather(*tasks)
    
    async def _monitor_system_resources(self):
        """Monitor system resources"""
        while True:
            try:
                # Get CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # Get memory usage
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_used_mb = memory.used / (1024 * 1024)
                memory_available_mb = memory.available / (1024 * 1024)
                
                # Get disk usage
                disk = psutil.disk_usage('/')
                disk_usage_percent = (disk.used / disk.total) * 100
                disk_free_gb = disk.free / (1024 * 1024 * 1024)
                
                # Get network I/O
                network = psutil.net_io_counters()
                network_io_read_mb = network.bytes_recv / (1024 * 1024)
                network_io_write_mb = network.bytes_sent / (1024 * 1024)
                
                # Calculate network I/O rate
                network_io_rate = 0
                if self.last_network_io:
                    time_diff = time.time() - self.last_network_io['timestamp']
                    if time_diff > 0:
                        read_diff = network_io_read_mb - self.last_network_io['read_mb']
                        write_diff = network_io_write_mb - self.last_network_io['write_mb']
                        network_io_rate = (read_diff + write_diff) / time_diff
                
                self.last_network_io = {
                    'timestamp': time.time(),
                    'read_mb': network_io_read_mb,
                    'write_mb': network_io_write_mb
                }
                
                # Create system resource object
                system_resource = SystemResource(
                    cpu_percent=cpu_percent,
                    memory_percent=memory_percent,
                    memory_used_mb=memory_used_mb,
                    memory_available_mb=memory_available_mb,
                    disk_usage_percent=disk_usage_percent,
                    disk_free_gb=disk_free_gb,
                    network_io_read_mb=network_io_read_mb,
                    network_io_write_mb=network_io_write_mb,
                    timestamp=datetime.utcnow()
                )
                
                # Store in history
                self.resource_history.append(system_resource)
                
                # Log if thresholds exceeded
                await self._check_resource_thresholds(system_resource)
                
                # Update Prometheus metrics
                self.metrics.cpu_usage.set(cpu_percent)
                self.metrics.memory_usage.set(memory_percent)
                self.metrics.disk_usage.set(disk_usage_percent)
                self.metrics.network_io.set(network_io_read_mb + network_io_write_mb)
                
            except Exception as e:
                logger.error(f"Error monitoring system resources: {e}")
            
            await asyncio.sleep(10)  # Monitor every 10 seconds
    
    async def _monitor_log_performance(self):
        """Monitor log processing performance"""
        while True:
            try:
                # Calculate performance metrics
                current_time = time.time()
                uptime = current_time - self.start_time
                
                # Calculate logs per second
                logs_per_second = self.total_logs_processed / uptime if uptime > 0 else 0
                
                # Calculate average processing time
                avg_processing_time = 0
                p95_processing_time = 0
                if self.log_processing_times:
                    avg_processing_time = sum(self.log_processing_times) / len(self.log_processing_times)
                    sorted_times = sorted(self.log_processing_times)
                    p95_index = int(len(sorted_times) * 0.95)
                    p95_processing_time = sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1]
                
                # Calculate error rate
                error_rate = (self.error_count / self.total_logs_processed) * 100 if self.total_logs_processed > 0 else 0
                
                # Get memory usage for logging process
                memory_usage_mb = psutil.Process().memory_info().rss / (1024 * 1024)
                
                # Create performance metrics
                log_performance = LogPerformance(
                    logs_processed_per_second=logs_per_second,
                    average_processing_time_ms=avg_processing_time,
                    p95_processing_time_ms=p95_processing_time,
                    memory_usage_mb=memory_usage_mb,
                    disk_io_mb_per_second=self.last_network_io.get('read_mb', 0) / uptime if uptime > 0 else 0,
                    error_rate_percent=error_rate,
                    timestamp=datetime.utcnow()
                )
                
                # Store in history
                self.performance_history.append(log_performance)
                
                # Update Prometheus metrics
                self.metrics.log_throughput.set(logs_per_second)
                self.metrics.error_rate.set(error_rate)
                self.metrics.processing_time.labels(operation='average').observe(avg_processing_time / 1000)
                self.metrics.processing_time.labels(operation='p95').observe(p95_processing_time / 1000)
                
                # Calculate health score
                health_score = await self._calculate_health_score(log_performance)
                self.metrics.health_score.set(health_score)
                
            except Exception as e:
                logger.error(f"Error monitoring log performance: {e}")
            
            await asyncio.sleep(30)  # Monitor every 30 seconds
    
    async def _check_resource_thresholds(self, resource: SystemResource):
        """Check if resource thresholds are exceeded"""
        alerts = []
        
        # CPU thresholds
        if resource.cpu_percent > self.alert_thresholds['cpu_critical']:
            alerts.append({
                'type': 'cpu_critical',
                'message': f'CPU usage critical: {resource.cpu_percent:.1f}%',
                'severity': 'critical'
            })
        elif resource.cpu_percent > self.alert_thresholds['cpu_warning']:
            alerts.append({
                'type': 'cpu_warning',
                'message': f'CPU usage high: {resource.cpu_percent:.1f}%',
                'severity': 'warning'
            })
        
        # Memory thresholds
        if resource.memory_percent > self.alert_thresholds['memory_critical']:
            alerts.append({
                'type': 'memory_critical',
                'message': f'Memory usage critical: {resource.memory_percent:.1f}%',
                'severity': 'critical'
            })
        elif resource.memory_percent > self.alert_thresholds['memory_warning']:
            alerts.append({
                'type': 'memory_warning',
                'message': f'Memory usage high: {resource.memory_percent:.1f}%',
                'severity': 'warning'
            })
        
        # Disk thresholds
        if resource.disk_usage_percent > self.alert_thresholds['disk_critical']:
            alerts.append({
                'type': 'disk_critical',
                'message': f'Disk usage critical: {resource.disk_usage_percent:.1f}%',
                'severity': 'critical'
            })
        elif resource.disk_usage_percent > self.alert_thresholds['disk_warning']:
            alerts.append({
                'type': 'disk_warning',
                'message': f'Disk usage high: {resource.disk_usage_percent:.1f}%',
                'severity': 'warning'
            })
        
        # Send alerts
        for alert in alerts:
            await self._send_performance_alert(alert)
    
    async def _check_performance_thresholds(self):
        """Check performance thresholds"""
        while True:
            try:
                if not self.performance_history:
                    await asyncio.sleep(60)
                    continue
                
                latest_performance = self.performance_history[-1]
                alerts = []
                
                # Processing time thresholds
                if latest_performance.average_processing_time_ms > self.alert_thresholds['processing_time_critical']:
                    alerts.append({
                        'type': 'processing_time_critical',
                        'message': f'Processing time critical: {latest_performance.average_processing_time_ms:.0f}ms',
                        'severity': 'critical'
                    })
                elif latest_performance.average_processing_time_ms > self.alert_thresholds['processing_time_warning']:
                    alerts.append({
                        'type': 'processing_time_warning',
                        'message': f'Processing time high: {latest_performance.average_processing_time_ms:.0f}ms',
                        'severity': 'warning'
                    })
                
                # Error rate thresholds
                if latest_performance.error_rate_percent > self.alert_thresholds['error_rate_critical']:
                    alerts.append({
                        'type': 'error_rate_critical',
                        'message': f'Error rate critical: {latest_performance.error_rate_percent:.1f}%',
                        'severity': 'critical'
                    })
                elif latest_performance.error_rate_percent > self.alert_thresholds['error_rate_warning']:
                    alerts.append({
                        'type': 'error_rate_warning',
                        'message': f'Error rate high: {latest_performance.error_rate_percent:.1f}%',
                        'severity': 'warning'
                    })
                
                # Throughput thresholds
                if latest_performance.logs_processed_per_second < self.alert_thresholds['throughput_critical']:
                    alerts.append({
                        'type': 'throughput_critical',
                        'message': f'Throughput critical: {latest_performance.logs_processed_per_second:.1f} logs/sec',
                        'severity': 'critical'
                    })
                elif latest_performance.logs_processed_per_second < self.alert_thresholds['throughput_warning']:
                    alerts.append({
                        'type': 'throughput_warning',
                        'message': f'Throughput low: {latest_performance.logs_processed_per_second:.1f} logs/sec',
                        'severity': 'warning'
                    })
                
                # Send alerts
                for alert in alerts:
                    await self._send_performance_alert(alert)
                
            except Exception as e:
                logger.error(f"Error checking performance thresholds: {e}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _send_performance_alert(self, alert: Dict[str, Any]):
        """Send performance alert"""
        alert_key = alert['type']
        current_time = datetime.utcnow()
        
        # Check cooldown
        if alert_key in self.active_alerts:
            if current_time - self.active_alerts[alert_key] < self.alert_cooldown:
                return
        
        # Update alert timestamp
        self.active_alerts[alert_key] = current_time
        
        # Send to alert manager if available
        if self.config.get('alert_manager_url'):
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {
                        'title': f'Performance Alert: {alert["type"].replace("_", " ").title()}',
                        'message': alert['message'],
                        'severity': alert['severity'],
                        'source': 'performance_monitor',
                        'metadata': {
                            'alert_type': alert['type'],
                            'timestamp': current_time.isoformat()
                        }
                    }
                    
                    async with session.post(
                        f"{self.config['alert_manager_url']}/alerts",
                        json=payload
                    ) as response:
                        if response.status == 200:
                            logger.info(f"Performance alert sent: {alert['type']}")
                        else:
                            logger.warning(f"Failed to send performance alert: {response.status}")
            except Exception as e:
                logger.error(f"Error sending performance alert: {e}")
        
        # Update Prometheus metrics
        self.metrics.performance_alerts.labels(type=alert['type']).inc()
        self.metrics.resource_thresholds.labels(resource=alert['type']).set(1)
        
        logger.warning(f"Performance alert: {alert['message']}")
    
    async def _calculate_health_score(self, performance: LogPerformance) -> float:
        """Calculate overall health score"""
        score = 100.0
        
        # Throughput score (40% weight)
        throughput_score = min(100, (performance.logs_processed_per_second / 100) * 100)
        score = score * 0.6 + throughput_score * 0.4
        
        # Processing time penalty (20% weight)
        if performance.average_processing_time_ms > self.alert_thresholds['processing_time_warning']:
            penalty = min(20, (performance.average_processing_time_ms - self.alert_thresholds['processing_time_warning']) / 100)
            score = max(0, score - penalty)
        
        # Error rate penalty (20% weight)
        if performance.error_rate_percent > self.alert_thresholds['error_rate_warning']:
            penalty = min(20, (performance.error_rate_percent - self.alert_thresholds['error_rate_warning']) * 2)
            score = max(0, score - penalty)
        
        # Resource usage penalty (20% weight)
        if self.resource_history:
            latest_resource = self.resource_history[-1]
            resource_penalty = 0
            
            if latest_resource.cpu_percent > self.alert_thresholds['cpu_warning']:
                resource_penalty += (latest_resource.cpu_percent - self.alert_thresholds['cpu_warning']) / 10
            
            if latest_resource.memory_percent > self.alert_thresholds['memory_warning']:
                resource_penalty += (latest_resource.memory_percent - self.alert_thresholds['memory_warning']) / 10
            
            if latest_resource.disk_usage_percent > self.alert_thresholds['disk_warning']:
                resource_penalty += (latest_resource.disk_usage_percent - self.alert_thresholds['disk_warning']) / 10
            
            score = max(0, score - min(20, resource_penalty))
        
        return round(score, 2)
    
    async def _generate_performance_reports(self):
        """Generate periodic performance reports"""
        while True:
            try:
                await asyncio.sleep(3600)  # Generate every hour
                
                if not self.performance_history:
                    continue
                
                # Calculate hourly statistics
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                recent_performance = [
                    p for p in self.performance_history
                    if p.timestamp > cutoff_time
                ]
                
                if not recent_performance:
                    continue
                
                # Calculate statistics
                avg_throughput = sum(p.logs_processed_per_second for p in recent_performance) / len(recent_performance)
                avg_processing_time = sum(p.average_processing_time_ms for p in recent_performance) / len(recent_performance)
                avg_error_rate = sum(p.error_rate_percent for p in recent_performance) / len(recent_performance)
                avg_memory = sum(p.memory_usage_mb for p in recent_performance) / len(recent_performance)
                
                # Generate report
                report = {
                    'report_type': 'hourly_performance',
                    'timestamp': datetime.utcnow().isoformat(),
                    'period_hours': 1,
                    'metrics': {
                        'average_throughput': avg_throughput,
                        'average_processing_time_ms': avg_processing_time,
                        'average_error_rate_percent': avg_error_rate,
                        'average_memory_usage_mb': avg_memory,
                        'total_logs_processed': self.total_logs_processed,
                        'total_errors': self.error_count
                    },
                    'alerts': len(self.active_alerts),
                    'health_score': await self._calculate_health_score(recent_performance[-1]) if recent_performance else 100.0
                }
                
                # Save report
                await self._save_performance_report(report)
                
                logger.info(f"Performance report generated: avg throughput {avg_throughput:.1f} logs/sec, avg processing time {avg_processing_time:.0f}ms")
                
            except Exception as e:
                logger.error(f"Error generating performance report: {e}")
    
    async def _save_performance_report(self, report: Dict[str, Any]):
        """Save performance report to file"""
        try:
            output_dir = self.config.get('output_dir', '/app/logs/performance')
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            report_file = output_path / f'performance_report_{timestamp}.json'
            
            async with aiofiles.open(report_file, 'w') as f:
                await f.write(json.dumps(report, indent=2, default=str))
            
            logger.info(f"Performance report saved to {report_file}")
            
        except Exception as e:
            logger.error(f"Error saving performance report: {e}")
    
    async def _update_prometheus_metrics(self):
        """Update Prometheus metrics"""
        while True:
            try:
                # Update uptime
                uptime = time.time() - self.start_time
                self.metrics.uptime._value._value = uptime
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except Exception as e:
                logger.error(f"Error updating Prometheus metrics: {e}")
    
    def record_log_processing(self, processing_time_ms: float, success: bool = True):
        """Record log processing metrics"""
        self.log_processing_times.append(processing_time_ms)
        self.total_logs_processed += 1
        
        if not success:
            self.error_count += 1
        
        # Update Prometheus metrics
        self.metrics.logs_processed.labels(source='unknown', status='success' if success else 'error').inc()
        self.metrics.processing_time.labels(operation='process').observe(processing_time_ms / 1000)
    
    def get_current_performance(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        if not self.performance_history:
            return {'status': 'no_data'}
        
        latest = self.performance_history[-1]
        latest_resource = self.resource_history[-1] if self.resource_history else None
        
        return {
            'timestamp': latest.timestamp.isoformat(),
            'throughput': latest.logs_processed_per_second,
            'processing_time_ms': latest.average_processing_time_ms,
            'error_rate_percent': latest.error_rate_percent,
            'memory_usage_mb': latest.memory_usage_mb,
            'system_resources': asdict(latest_resource) if latest_resource else None,
            'health_score': await self._calculate_health_score(latest),
            'active_alerts': len(self.active_alerts),
            'uptime_seconds': time.time() - self.start_time
        }
    
    async def get_performance_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get performance history"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        history = []
        for performance in self.performance_history:
            if performance.timestamp > cutoff_time:
                history.append(asdict(performance))
        
        return history
    
    async def export_metrics(self, filepath: str, format: str = 'json'):
        """Export performance metrics"""
        try:
            data = {
                'performance_history': [asdict(p) for p in self.performance_history],
                'resource_history': [asdict(r) for r in self.resource_history],
                'current_performance': self.get_current_performance(),
                'alert_thresholds': self.alert_thresholds,
                'export_timestamp': datetime.utcnow().isoformat()
            }
            
            if format.lower() == 'json':
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
            elif format.lower() == 'csv':
                import pandas as pd
                
                # Convert to DataFrames
                perf_df = pd.DataFrame([asdict(p) for p in self.performance_history])
                resource_df = pd.DataFrame([asdict(r) for r in self.resource_history])
                
                # Save to CSV
                perf_df.to_csv(filepath.replace('.csv', '_performance.csv'), index=False)
                resource_df.to_csv(filepath.replace('.csv', '_resources.csv'), index=False)
            
            logger.info(f"Performance metrics exported to {filepath}")
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")

# Example usage
if __name__ == "__main__":
    config = {
        'thresholds': {
            'cpu_warning': 70.0,
            'cpu_critical': 90.0,
            'memory_warning': 75.0,
            'memory_critical': 90.0,
            'disk_warning': 80.0,
            'disk_critical': 95.0,
            'processing_time_warning': 1000.0,
            'processing_time_critical': 5000.0,
            'error_rate_warning': 5.0,
            'error_rate_critical': 15.0,
            'throughput_warning': 100.0,
            'throughput_critical': 50.0
        },
        'alert_manager_url': 'http://localhost:8001',
        'output_dir': '/app/logs/performance'
    }
    
    monitor = PerformanceMonitor(config)
    
    async def test_monitoring():
        # Test recording some metrics
        for i in range(10):
            monitor.record_log_processing(processing_time_ms=50 + i * 10, success=i % 4 != 0)
            await asyncio.sleep(0.1)
        
        # Get current performance
        current = monitor.get_current_performance()
        print("Current Performance:")
        print(json.dumps(current, indent=2, default=str))
        
        # Get performance history
        history = await monitor.get_performance_history(hours=1)
        print(f"\nPerformance History (last hour): {len(history)} data points")
        
        # Export metrics
        await monitor.export_metrics('/tmp/performance_metrics.json')
        await monitor.export_metrics('/tmp/performance_metrics.csv', format='csv')
        
        # Start monitoring (this would run continuously)
        # await monitor.start_monitoring()
    
    asyncio.run(test_monitoring())
