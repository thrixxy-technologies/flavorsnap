#!/usr/bin/env python3
"""
Advanced Log Aggregator for FlavorSnap
Implements log collection, parsing, and analysis capabilities
"""

import asyncio
import json
import re
import gzip
import os
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import aiohttp
import aiofiles
import logging
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import statistics
import prometheus_client as prom

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: datetime
    level: str
    logger: str
    message: str
    module: str
    function: str
    line: int
    thread: int
    process: int
    extra: Dict[str, Any]
    raw: str

@dataclass
class LogAnalysis:
    """Log analysis results"""
    total_entries: int
    time_range: Tuple[datetime, datetime]
    level_distribution: Dict[str, int]
    logger_distribution: Dict[str, int]
    error_rate: float
    warning_rate: float
    top_errors: List[Dict[str, Any]]
    performance_metrics: Dict[str, float]
    security_events: List[Dict[str, Any]]
    compliance_events: List[Dict[str, Any]]

class PrometheusMetrics:
    """Prometheus metrics for log aggregation"""
    
    def __init__(self):
        self.logs_processed = prom.Counter(
            'log_aggregator_logs_processed_total',
            'Total logs processed',
            ['source', 'level']
        )
        
        self.log_processing_time = prom.Histogram(
            'log_aggregator_processing_duration_seconds',
            'Time spent processing logs',
            ['operation']
        )
        
        self.log_errors = prom.Counter(
            'log_aggregator_errors_total',
            'Total log processing errors',
            ['error_type']
        )
        
        self.log_storage_size = prom.Gauge(
            'log_aggregator_storage_size_bytes',
            'Log storage size',
            ['log_type']
        )
        
        self.analysis_results = prom.Gauge(
            'log_aggregator_analysis_results',
            'Log analysis results',
            ['metric']
        )

class LogAggregator:
    """Advanced log aggregator with analysis capabilities"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.log_sources: List[str] = []
        self.parsed_logs: List[LogEntry] = []
        self.analysis_cache: Dict[str, LogAnalysis] = {}
        
        # Metrics
        self.metrics = PrometheusMetrics()
        
        # Patterns for log parsing
        self.error_patterns = [
            re.compile(r'(?i)error|exception|failed|failure'),
            re.compile(r'(?i)timeout|connection.*refused|network.*error'),
            re.compile(r'(?i)permission.*denied|unauthorized|forbidden')
        ]
        
        self.security_patterns = [
            re.compile(r'(?i)login|authentication|authorization'),
            re.compile(r'(?i)security|breach|attack|intrusion'),
            re.compile(r'(?i)malware|virus|suspicious')
        ]
        
        self.performance_patterns = [
            re.compile(r'(?i)slow|performance|latency|timeout'),
            re.compile(r'(?i)memory|cpu|disk.*space'),
            re.compile(r'(?i)response.*time|duration|throughput')
        ]
    
    async def collect_logs(self) -> List[LogEntry]:
        """Collect logs from all configured sources"""
        start_time = time.time()
        
        try:
            # Collect from file sources
            file_logs = await self._collect_from_files()
            
            # Collect from HTTP sources
            http_logs = await self._collect_from_http()
            
            # Collect from database sources
            db_logs = await self._collect_from_database()
            
            # Combine all logs
            all_logs = file_logs + http_logs + db_logs
            
            # Update metrics
            processing_time = time.time() - start_time
            self.metrics.log_processing_time.labels(operation='collect').observe(processing_time)
            self.metrics.logs_processed.labels(source='all', level='total').inc(len(all_logs))
            
            logger.info(f"Collected {len(all_logs)} log entries in {processing_time:.2f}s")
            return all_logs
            
        except Exception as e:
            logger.error(f"Error collecting logs: {e}")
            self.metrics.log_errors.labels(error_type='collection').inc()
            return []
    
    async def _collect_from_files(self) -> List[LogEntry]:
        """Collect logs from file sources"""
        logs = []
        log_dir = Path(self.config.get('log_dir', '/app/logs'))
        
        if not log_dir.exists():
            logger.warning(f"Log directory {log_dir} does not exist")
            return logs
        
        # Process different log files
        log_files = {
            'structured': log_dir / 'structured.log',
            'detailed': log_dir / 'detailed.log',
            'error': log_dir / 'error.log',
            'audit': log_dir / 'audit.log',
            'performance': log_dir / 'performance.log',
            'security': log_dir / 'security.log'
        }
        
        for log_type, log_file in log_files.items():
            if log_file.exists():
                file_logs = await self._parse_log_file(log_file, log_type)
                logs.extend(file_logs)
                
                # Update metrics
                self.metrics.log_storage_size.labels(log_type=log_type).set(log_file.stat().st_size)
                self.metrics.logs_processed.labels(source=log_type, level='total').inc(len(file_logs))
        
        return logs
    
    async def _parse_log_file(self, file_path: Path, log_type: str) -> List[LogEntry]:
        """Parse a single log file"""
        logs = []
        
        try:
            # Handle compressed files
            if file_path.suffix == '.gz':
                opener = gzip.open
            else:
                opener = aiofiles.open
            
            async with opener(file_path, 'r', encoding='utf-8') as file:
                async for line in file:
                    if line.strip():
                        log_entry = await self._parse_log_line(line.strip(), log_type)
                        if log_entry:
                            logs.append(log_entry)
        
        except Exception as e:
            logger.error(f"Error parsing log file {file_path}: {e}")
            self.metrics.log_errors.labels(error_type='parsing').inc()
        
        return logs
    
    async def _parse_log_line(self, line: str, log_type: str) -> Optional[LogEntry]:
        """Parse a single log line"""
        try:
            # Try to parse as JSON first
            if line.startswith('{'):
                data = json.loads(line)
                return LogEntry(
                    timestamp=datetime.fromisoformat(data.get('timestamp', '').replace('Z', '+00:00')),
                    level=data.get('level', 'INFO'),
                    logger=data.get('logger', ''),
                    message=data.get('message', ''),
                    module=data.get('module', ''),
                    function=data.get('function', ''),
                    line=data.get('line', 0),
                    thread=data.get('thread', 0),
                    process=data.get('process', 0),
                    extra=data.get('extra', {}),
                    raw=line
                )
            
            # Fallback to regex parsing for non-JSON logs
            return await self._parse_with_regex(line, log_type)
            
        except Exception as e:
            logger.debug(f"Error parsing log line: {e}")
            return None
    
    async def _parse_with_regex(self, line: str, log_type: str) -> Optional[LogEntry]:
        """Parse log line using regex patterns"""
        # Common log format patterns
        patterns = [
            # Standard format: timestamp - logger - level - message
            r'^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2})?) - (?P<logger>\w+) - (?P<level>\w+) - (?P<message>.*)',
            # Apache/Nginx format
            r'^(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>.*?)\] "(?P<method>\S+) (?P<path>\S+) (?P<protocol>\S+)" (?P<status>\d+) (?P<size>\d+) "(?P<user_agent>[^"]*)"',
            # Simple format
            r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (?P<level>\w+) (?P<message>.*)'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groupdict()
                return LogEntry(
                    timestamp=self._parse_timestamp(groups.get('timestamp', '')),
                    level=groups.get('level', 'INFO'),
                    logger=groups.get('logger', log_type),
                    message=groups.get('message', line),
                    module='',
                    function='',
                    line=0,
                    thread=0,
                    process=0,
                    extra={},
                    raw=line
                )
        
        # If no pattern matches, create a basic entry
        return LogEntry(
            timestamp=datetime.utcnow(),
            level='INFO',
            logger=log_type,
            message=line,
            module='',
            function='',
            line=0,
            thread=0,
            process=0,
            extra={},
            raw=line
        )
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime object"""
        if not timestamp_str:
            return datetime.utcnow()
        
        # Try different timestamp formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%d %H:%M:%S',
            '%d/%b/%Y:%H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        return datetime.utcnow()
    
    async def _collect_from_http(self) -> List[LogEntry]:
        """Collect logs from HTTP endpoints"""
        logs = []
        http_sources = self.config.get('http_sources', [])
        
        async with aiohttp.ClientSession() as session:
            for source in http_sources:
                try:
                    async with session.get(source['url'], timeout=30) as response:
                        if response.status == 200:
                            text = await response.text()
                            for line in text.split('\n'):
                                if line.strip():
                                    log_entry = await self._parse_log_line(line.strip(), 'http')
                                    if log_entry:
                                        logs.append(log_entry)
                            
                            self.metrics.logs_processed.labels(source='http', level='total').inc(len(logs))
                
                except Exception as e:
                    logger.error(f"Error collecting from HTTP source {source['url']}: {e}")
                    self.metrics.log_errors.labels(error_type='http_collection').inc()
        
        return logs
    
    async def _collect_from_database(self) -> List[LogEntry]:
        """Collect logs from database sources"""
        logs = []
        db_config = self.config.get('database', {})
        
        if not db_config:
            return logs
        
        try:
            # This would connect to a database and query logs
            # For now, return empty list as placeholder
            logger.info("Database log collection not implemented yet")
            
        except Exception as e:
            logger.error(f"Error collecting logs from database: {e}")
            self.metrics.log_errors.labels(error_type='db_collection').inc()
        
        return logs
    
    async def analyze_logs(self, logs: List[LogEntry]) -> LogAnalysis:
        """Analyze collected logs"""
        start_time = time.time()
        
        try:
            if not logs:
                return LogAnalysis(
                    total_entries=0,
                    time_range=(datetime.utcnow(), datetime.utcnow()),
                    level_distribution={},
                    logger_distribution={},
                    error_rate=0.0,
                    warning_rate=0.0,
                    top_errors=[],
                    performance_metrics={},
                    security_events=[],
                    compliance_events=[]
                )
            
            # Basic statistics
            total_entries = len(logs)
            timestamps = [log.timestamp for log in logs]
            time_range = (min(timestamps), max(timestamps))
            
            # Level distribution
            level_counts = Counter(log.level for log in logs)
            level_distribution = dict(level_counts)
            
            # Logger distribution
            logger_counts = Counter(log.logger for log in logs)
            logger_distribution = dict(logger_counts)
            
            # Error and warning rates
            error_count = level_counts.get('ERROR', 0) + level_counts.get('CRITICAL', 0)
            warning_count = level_counts.get('WARNING', 0)
            error_rate = (error_count / total_entries) * 100
            warning_rate = (warning_count / total_entries) * 100
            
            # Top errors
            error_logs = [log for log in logs if log.level in ['ERROR', 'CRITICAL']]
            top_errors = self._get_top_messages(error_logs, 10)
            
            # Performance metrics
            performance_logs = [log for log in logs if any(
                pattern.search(log.message) for pattern in self.performance_patterns
            )]
            performance_metrics = self._analyze_performance_logs(performance_logs)
            
            # Security events
            security_logs = [log for log in logs if any(
                pattern.search(log.message) for pattern in self.security_patterns
            )]
            security_events = self._extract_security_events(security_logs)
            
            # Compliance events
            compliance_logs = [log for log in logs if 'audit' in log.logger.lower()]
            compliance_events = self._extract_compliance_events(compliance_logs)
            
            # Update metrics
            processing_time = time.time() - start_time
            self.metrics.log_processing_time.labels(operation='analyze').observe(processing_time)
            self.metrics.analysis_results.labels(metric='total_entries').set(total_entries)
            self.metrics.analysis_results.labels(metric='error_rate').set(error_rate)
            self.metrics.analysis_results.labels(metric='warning_rate').set(warning_rate)
            
            analysis = LogAnalysis(
                total_entries=total_entries,
                time_range=time_range,
                level_distribution=level_distribution,
                logger_distribution=logger_distribution,
                error_rate=error_rate,
                warning_rate=warning_rate,
                top_errors=top_errors,
                performance_metrics=performance_metrics,
                security_events=security_events,
                compliance_events=compliance_events
            )
            
            logger.info(f"Analyzed {total_entries} log entries in {processing_time:.2f}s")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing logs: {e}")
            self.metrics.log_errors.labels(error_type='analysis').inc()
            return LogAnalysis(
                total_entries=0,
                time_range=(datetime.utcnow(), datetime.utcnow()),
                level_distribution={},
                logger_distribution={},
                error_rate=0.0,
                warning_rate=0.0,
                top_errors=[],
                performance_metrics={},
                security_events=[],
                compliance_events=[]
            )
    
    def _get_top_messages(self, logs: List[LogEntry], limit: int) -> List[Dict[str, Any]]:
        """Get top error messages"""
        message_counts = Counter(log.message for log in logs)
        top_messages = []
        
        for message, count in message_counts.most_common(limit):
            top_messages.append({
                'message': message,
                'count': count,
                'percentage': (count / len(logs)) * 100
            })
        
        return top_messages
    
    def _analyze_performance_logs(self, logs: List[LogEntry]) -> Dict[str, float]:
        """Analyze performance-related logs"""
        if not logs:
            return {}
        
        # Extract performance metrics from log messages
        response_times = []
        memory_usage = []
        cpu_usage = []
        
        for log in logs:
            message = log.message.lower()
            
            # Extract response times
            rt_match = re.search(r'(\d+(?:\.\d+)?)\s*ms', message)
            if rt_match:
                response_times.append(float(rt_match.group(1)))
            
            # Extract memory usage
            mem_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mb|gb)', message)
            if mem_match:
                memory_usage.append(float(mem_match.group(1)))
            
            # Extract CPU usage
            cpu_match = re.search(r'(\d+(?:\.\d+)?)\s*%|cpu', message)
            if cpu_match:
                cpu_usage.append(float(cpu_match.group(1)))
        
        metrics = {}
        if response_times:
            metrics['avg_response_time'] = statistics.mean(response_times)
            metrics['max_response_time'] = max(response_times)
            metrics['p95_response_time'] = sorted(response_times)[int(len(response_times) * 0.95)]
        
        if memory_usage:
            metrics['avg_memory_usage'] = statistics.mean(memory_usage)
            metrics['max_memory_usage'] = max(memory_usage)
        
        if cpu_usage:
            metrics['avg_cpu_usage'] = statistics.mean(cpu_usage)
            metrics['max_cpu_usage'] = max(cpu_usage)
        
        return metrics
    
    def _extract_security_events(self, logs: List[LogEntry]) -> List[Dict[str, Any]]:
        """Extract security events from logs"""
        security_events = []
        
        for log in logs:
            # Check if log contains security event data
            if 'security_event' in log.extra:
                security_events.append(log.extra['security_event'])
            else:
                # Extract from message
                security_event = {
                    'timestamp': log.timestamp.isoformat(),
                    'message': log.message,
                    'level': log.level,
                    'source': log.logger
                }
                
                # Try to extract IP addresses
                ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', log.message)
                if ip_match:
                    security_event['ip_address'] = ip_match.group()
                
                # Try to extract user information
                user_match = re.search(r'user[:\s]*[:=]\s*(\w+)', log.message, re.IGNORECASE)
                if user_match:
                    security_event['user'] = user_match.group(1)
                
                security_events.append(security_event)
        
        return security_events
    
    def _extract_compliance_events(self, logs: List[LogEntry]) -> List[Dict[str, Any]]:
        """Extract compliance events from logs"""
        compliance_events = []
        
        for log in logs:
            # Check if log contains compliance event data
            if 'audit_event' in log.extra:
                compliance_events.append(log.extra['audit_event'])
            elif 'compliance_event' in log.extra:
                compliance_events.append(log.extra['compliance_event'])
            else:
                # Extract from message
                compliance_event = {
                    'timestamp': log.timestamp.isoformat(),
                    'message': log.message,
                    'level': log.level,
                    'source': log.logger
                }
                
                # Try to extract regulation information
                reg_match = re.search(r'(?:gdpr|hipaa|sox|pci|compliance)', log.message, re.IGNORECASE)
                if reg_match:
                    compliance_event['regulation'] = reg_match.group().upper()
                
                compliance_events.append(compliance_event)
        
        return compliance_events
    
    async def generate_report(self, analysis: LogAnalysis) -> Dict[str, Any]:
        """Generate comprehensive log analysis report"""
        report = {
            'summary': {
                'total_entries': analysis.total_entries,
                'time_range': {
                    'start': analysis.time_range[0].isoformat(),
                    'end': analysis.time_range[1].isoformat(),
                    'duration_hours': (analysis.time_range[1] - analysis.time_range[0]).total_seconds() / 3600
                },
                'error_rate': analysis.error_rate,
                'warning_rate': analysis.warning_rate
            },
            'level_distribution': analysis.level_distribution,
            'logger_distribution': analysis.logger_distribution,
            'top_errors': analysis.top_errors,
            'performance_metrics': analysis.performance_metrics,
            'security_events': analysis.security_events,
            'compliance_events': analysis.compliance_events,
            'recommendations': self._generate_recommendations(analysis),
            'generated_at': datetime.utcnow().isoformat()
        }
        
        return report
    
    def _generate_recommendations(self, analysis: LogAnalysis) -> List[Dict[str, Any]]:
        """Generate recommendations based on log analysis"""
        recommendations = []
        
        # Error rate recommendations
        if analysis.error_rate > 5.0:
            recommendations.append({
                'type': 'error_rate',
                'severity': 'high',
                'message': f'High error rate detected: {analysis.error_rate:.1f}%',
                'action': 'Investigate top errors and fix underlying issues'
            })
        elif analysis.error_rate > 2.0:
            recommendations.append({
                'type': 'error_rate',
                'severity': 'medium',
                'message': f'Elevated error rate: {analysis.error_rate:.1f}%',
                'action': 'Monitor error trends and address recurring issues'
            })
        
        # Performance recommendations
        if analysis.performance_metrics:
            avg_rt = analysis.performance_metrics.get('avg_response_time', 0)
            if avg_rt > 1000:  # > 1 second
                recommendations.append({
                    'type': 'performance',
                    'severity': 'high',
                    'message': f'High average response time: {avg_rt:.0f}ms',
                    'action': 'Optimize slow operations and investigate bottlenecks'
                })
        
        # Security recommendations
        if len(analysis.security_events) > 10:
            recommendations.append({
                'type': 'security',
                'severity': 'high',
                'message': f'High number of security events: {len(analysis.security_events)}',
                'action': 'Review security logs and implement additional monitoring'
            })
        
        # Compliance recommendations
        if len(analysis.compliance_events) > 20:
            recommendations.append({
                'type': 'compliance',
                'severity': 'medium',
                'message': f'High compliance activity: {len(analysis.compliance_events)} events',
                'action': 'Review compliance logs and ensure proper documentation'
            })
        
        return recommendations
    
    async def run_aggregation_cycle(self):
        """Run a complete aggregation cycle"""
        logger.info("Starting log aggregation cycle")
        
        # Collect logs
        logs = await self.collect_logs()
        
        # Analyze logs
        analysis = await self.analyze_logs(logs)
        
        # Generate report
        report = await self.generate_report(analysis)
        
        # Store results
        await self._store_results(report)
        
        logger.info("Log aggregation cycle completed")
        return report
    
    async def _store_results(self, report: Dict[str, Any]):
        """Store aggregation results"""
        try:
            # Store to file
            output_dir = Path(self.config.get('output_dir', '/app/logs/analysis'))
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            report_file = output_dir / f'log_analysis_{timestamp}.json'
            
            async with aiofiles.open(report_file, 'w') as f:
                await f.write(json.dumps(report, indent=2, default=str))
            
            logger.info(f"Analysis report saved to {report_file}")
            
            # Optionally send to external systems
            if self.config.get('send_to_external', False):
                await self._send_to_external(report)
                
        except Exception as e:
            logger.error(f"Error storing results: {e}")
            self.metrics.log_errors.labels(error_type='storage').inc()
    
    async def _send_to_external(self, report: Dict[str, Any]):
        """Send analysis results to external systems"""
        external_config = self.config.get('external', {})
        
        if not external_config:
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                # Send to webhook
                webhook_url = external_config.get('webhook_url')
                if webhook_url:
                    async with session.post(webhook_url, json=report) as response:
                        if response.status == 200:
                            logger.info("Analysis report sent to webhook successfully")
                        else:
                            logger.warning(f"Failed to send report to webhook: {response.status}")
                
                # Send to API
                api_url = external_config.get('api_url')
                if api_url:
                    headers = {'Authorization': f"Bearer {external_config.get('api_token')}"}
                    async with session.post(api_url, json=report, headers=headers) as response:
                        if response.status == 200:
                            logger.info("Analysis report sent to API successfully")
                        else:
                            logger.warning(f"Failed to send report to API: {response.status}")
                            
        except Exception as e:
            logger.error(f"Error sending to external systems: {e}")

# Example usage
if __name__ == "__main__":
    config = {
        'log_dir': '/app/logs',
        'output_dir': '/app/logs/analysis',
        'http_sources': [
            {'url': 'http://log-aggregator.example.com/logs'}
        ],
        'database': {
            'host': 'localhost',
            'port': 5432,
            'database': 'logs',
            'username': 'logger',
            'password': 'password'
        },
        'send_to_external': False,
        'external': {
            'webhook_url': 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK',
            'api_url': 'https://api.example.com/logs',
            'api_token': 'your-api-token'
        }
    }
    
    aggregator = LogAggregator(config)
    
    async def run_continuous():
        """Run continuous aggregation"""
        while True:
            try:
                await aggregator.run_aggregation_cycle()
                await asyncio.sleep(60)  # Run every minute
            except KeyboardInterrupt:
                logger.info("Stopping log aggregator")
                break
            except Exception as e:
                logger.error(f"Error in aggregation cycle: {e}")
                await asyncio.sleep(60)
    
    asyncio.run(run_continuous())
