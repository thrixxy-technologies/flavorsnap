#!/usr/bin/env python3
"""
Advanced Log Analyzer for FlavorSnap
Implements intelligent log analysis, pattern detection, and insights
"""

import asyncio
import json
import re
import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging
from dataclasses import dataclass, asdict
import aiohttp
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LogPattern:
    """Detected log pattern"""
    pattern: str
    description: str
    severity: str
    count: int
    first_seen: datetime
    last_seen: datetime
    samples: List[str]

@dataclass
class Anomaly:
    """Detected anomaly in logs"""
    type: str
    description: str
    severity: str
    confidence: float
    timestamp: datetime
    affected_logs: List[str]
    context: Dict[str, Any]

@dataclass
class Insight:
    """Log analysis insight"""
    category: str
    title: str
    description: str
    impact: str
    recommendation: str
    confidence: float
    data: Dict[str, Any]

class LogAnalyzer:
    """Advanced log analyzer with pattern detection and insights"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.patterns: List[LogPattern] = []
        self.anomalies: List[Anomaly] = []
        self.insights: List[Insight] = []
        
        # Predefined patterns for common issues
        self.error_patterns = [
            (r'(?i)error|exception|failed|failure', 'Error/Exception'),
            (r'(?i)timeout|connection.*refused|network.*error', 'Network/Timeout Issues'),
            (r'(?i)permission.*denied|unauthorized|forbidden', 'Permission/Authorization Issues'),
            (r'(?i)out.*of.*memory|memory.*exhausted', 'Memory Issues'),
            (r'(?i)disk.*full|no.*space.*left', 'Storage Issues'),
            (r'(?i)database.*connection|sql.*error', 'Database Issues'),
            (r'(?i)ssl|tls|certificate.*error', 'Security/SSL Issues')
        ]
        
        self.performance_patterns = [
            (r'(?i)slow.*request|high.*latency', 'Slow Response'),
            (r'(?i)high.*cpu|cpu.*spike', 'High CPU Usage'),
            (r'(?i)memory.*usage.*high|memory.*spike', 'High Memory Usage'),
            (r'(?i)queue.*full|backlog.*high', 'Queue/Backlog Issues'),
            (r'(?i)connection.*pool.*exhausted', 'Connection Pool Issues')
        ]
        
        self.security_patterns = [
            (r'(?i)brute.*force|multiple.*failed.*login', 'Brute Force Attack'),
            (r'(?i)sql.*injection|union.*select', 'SQL Injection Attempt'),
            (r'(?i)xss|cross.*site.*scripting', 'XSS Attempt'),
            (r'(?i)ddos|distributed.*denial.*of.*service', 'DDoS Attack'),
            (r'(?i)unusual.*ip|suspicious.*activity', 'Suspicious Activity')
        ]
        
        self.business_patterns = [
            (r'(?i)payment.*failed|transaction.*error', 'Payment/Transaction Issues'),
            (r'(?i)user.*registration|account.*creation', 'User Registration'),
            (r'(?i)login.*successful|authentication.*success', 'User Login'),
            (r'(?i)order.*placed|purchase.*completed', 'Order/Purchase'),
            (r'(?i)api.*call|service.*request', 'API Usage')
        ]
    
    async def analyze_logs(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform comprehensive log analysis"""
        logger.info(f"Starting analysis of {len(logs)} log entries")
        
        analysis_results = {
            'summary': await self._generate_summary(logs),
            'patterns': await self._detect_patterns(logs),
            'anomalies': await self._detect_anomalies(logs),
            'insights': await self._generate_insights(logs),
            'trends': await self._analyze_trends(logs),
            'recommendations': await self._generate_recommendations(logs)
        }
        
        logger.info("Log analysis completed")
        return analysis_results
    
    async def _generate_summary(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate log summary statistics"""
        if not logs:
            return {'total_entries': 0, 'message': 'No logs to analyze'}
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(logs)
        
        # Time range
        timestamps = pd.to_datetime(df['timestamp'])
        time_range = {
            'start': timestamps.min().isoformat(),
            'end': timestamps.max().isoformat(),
            'duration_hours': (timestamps.max() - timestamps.min()).total_seconds() / 3600
        }
        
        # Level distribution
        level_counts = df['level'].value_counts().to_dict()
        
        # Logger distribution
        logger_counts = df['logger'].value_counts().to_dict()
        
        # Hourly distribution
        df['hour'] = timestamps.dt.hour
        hourly_counts = df['hour'].value_counts().sort_index().to_dict()
        
        # Error rate over time
        error_df = df[df['level'].isin(['ERROR', 'CRITICAL'])]
        if not error_df.empty:
            error_df['hour'] = pd.to_datetime(error_df['timestamp']).dt.hour
            error_rate_by_hour = (error_df.groupby('hour').size() / df.groupby('hour').size()).to_dict()
        else:
            error_rate_by_hour = {}
        
        return {
            'total_entries': len(logs),
            'time_range': time_range,
            'level_distribution': level_counts,
            'logger_distribution': logger_counts,
            'hourly_distribution': hourly_counts,
            'error_rate_by_hour': error_rate_by_hour,
            'top_loggers': logger_counts.most_common(5),
            'error_percentage': (len(error_df) / len(logs)) * 100
        }
    
    async def _detect_patterns(self, logs: List[Dict[str, Any]]) -> List[LogPattern]:
        """Detect recurring patterns in logs"""
        patterns = []
        messages = [log.get('message', '') for log in logs]
        
        # Check error patterns
        for pattern, description in self.error_patterns:
            matches = [msg for msg in messages if re.search(pattern, msg)]
            if matches:
                pattern_obj = LogPattern(
                    pattern=pattern,
                    description=description,
                    severity='high',
                    count=len(matches),
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    samples=matches[:5]
                )
                patterns.append(pattern_obj)
        
        # Check performance patterns
        for pattern, description in self.performance_patterns:
            matches = [msg for msg in messages if re.search(pattern, msg)]
            if matches:
                pattern_obj = LogPattern(
                    pattern=pattern,
                    description=description,
                    severity='medium',
                    count=len(matches),
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    samples=matches[:5]
                )
                patterns.append(pattern_obj)
        
        # Check security patterns
        for pattern, description in self.security_patterns:
            matches = [msg for msg in messages if re.search(pattern, msg)]
            if matches:
                pattern_obj = LogPattern(
                    pattern=pattern,
                    description=description,
                    severity='critical',
                    count=len(matches),
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    samples=matches[:5]
                )
                patterns.append(pattern_obj)
        
        # Check business patterns
        for pattern, description in self.business_patterns:
            matches = [msg for msg in messages if re.search(pattern, msg)]
            if matches:
                pattern_obj = LogPattern(
                    pattern=pattern,
                    description=description,
                    severity='info',
                    count=len(matches),
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    samples=matches[:5]
                )
                patterns.append(pattern_obj)
        
        self.patterns = patterns
        return patterns
    
    async def _detect_anomalies(self, logs: List[Dict[str, Any]]) -> List[Anomaly]:
        """Detect anomalies in log patterns"""
        anomalies = []
        
        if len(logs) < 100:
            return anomalies
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(logs)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Detect unusual error spikes
        error_logs = df[df['level'].isin(['ERROR', 'CRITICAL'])]
        if not error_logs.empty:
            error_logs['hour'] = error_logs['timestamp'].dt.hour
            error_counts = error_logs.groupby('hour').size()
            
            # Calculate threshold (mean + 2*std)
            threshold = error_counts.mean() + 2 * error_counts.std()
            
            for hour, count in error_counts.items():
                if count > threshold:
                    anomaly = Anomaly(
                        type='error_spike',
                        description=f'Unusual error spike at hour {hour}: {count} errors',
                        severity='high',
                        confidence=min(0.9, (count - threshold) / threshold),
                        timestamp=datetime.utcnow(),
                        affected_logs=[],
                        context={'hour': hour, 'error_count': count, 'threshold': threshold}
                    )
                    anomalies.append(anomaly)
        
        # Detect unusual log volume
        df['hour'] = df['timestamp'].dt.hour
        hourly_volume = df.groupby('hour').size()
        
        volume_threshold = hourly_volume.mean() + 2 * hourly_volume.std()
        
        for hour, count in hourly_volume.items():
            if count > volume_threshold * 1.5:  # 50% above threshold
                anomaly = Anomaly(
                    type='volume_spike',
                    description=f'Unusual log volume spike at hour {hour}: {count} logs',
                    severity='medium',
                    confidence=min(0.8, (count - volume_threshold) / volume_threshold),
                    timestamp=datetime.utcnow(),
                    affected_logs=[],
                    context={'hour': hour, 'log_count': count, 'threshold': volume_threshold}
                )
                anomalies.append(anomaly)
        
        # Detect unusual IP patterns (if available)
        if 'ip_address' in df.columns:
            ip_counts = df['ip_address'].value_counts()
            
            # IPs with unusual activity
            for ip, count in ip_counts.items():
                if count > ip_counts.mean() + 3 * ip_counts.std():
                    anomaly = Anomaly(
                        type='unusual_ip_activity',
                        description=f'Unusual activity from IP {ip}: {count} requests',
                        severity='medium',
                        confidence=min(0.7, (count - ip_counts.mean()) / ip_counts.std()),
                        timestamp=datetime.utcnow(),
                        affected_logs=[],
                        context={'ip_address': ip, 'request_count': count}
                    )
                    anomalies.append(anomaly)
        
        # Detect new error patterns
        recent_errors = error_logs[error_logs['timestamp'] > (datetime.utcnow() - timedelta(hours=1))]
        if not recent_errors.empty:
            recent_messages = recent_errors['message'].tolist()
            
            # Check for new error patterns
            existing_patterns = set()
            for pattern in self.patterns:
                existing_patterns.add(pattern.pattern)
            
            new_patterns = []
            for msg in recent_messages:
                for pattern, _ in self.error_patterns:
                    if re.search(pattern, msg) and pattern not in existing_patterns:
                        new_patterns.append(pattern)
            
            if new_patterns:
                anomaly = Anomaly(
                    type='new_error_pattern',
                    description=f'New error pattern detected: {new_patterns[0]}',
                    severity='high',
                    confidence=0.8,
                    timestamp=datetime.utcnow(),
                    affected_logs=recent_messages[:5],
                    context={'new_patterns': new_patterns}
                )
                anomalies.append(anomaly)
        
        self.anomalies = anomalies
        return anomalies
    
    async def _generate_insights(self, logs: List[Dict[str, Any]]) -> List[Insight]:
        """Generate actionable insights from log analysis"""
        insights = []
        
        if len(logs) < 50:
            return insights
        
        df = pd.DataFrame(logs)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Performance insights
        performance_logs = df[df['level'].isin(['WARNING', 'ERROR'])]
        if not performance_logs.empty:
            # Response time insights
            slow_requests = df[df['message'].str.contains(r'slow|timeout', case=False, na=False)]
            if not slow_requests.empty:
                insight = Insight(
                    category='performance',
                    title='Performance Degradation Detected',
                    description=f'Found {len(slow_requests)} slow requests in analyzed logs',
                    impact='High response times affecting user experience',
                    recommendation='Investigate slow endpoints and optimize database queries',
                    confidence=0.8,
                    data={'slow_request_count': len(slow_requests), 'percentage': (len(slow_requests) / len(df)) * 100}
                )
                insights.append(insight)
        
        # Security insights
        security_logs = df[df['message'].str.contains(r'(?i)login|auth|security|attack', case=False, na=False)]
        if not security_logs.empty:
            failed_logins = security_logs[security_logs['message'].str.contains(r'(?i)failed|denied|unauthorized', case=False, na=False)]
            if not failed_logins.empty:
                insight = Insight(
                    category='security',
                    title='Authentication Issues Detected',
                    description=f'Found {len(failed_logins)} failed authentication attempts',
                    impact='Potential security risk or user experience issues',
                    recommendation='Review authentication logs and implement rate limiting',
                    confidence=0.9,
                    data={'failed_attempts': len(failed_logins), 'success_rate': ((len(security_logs) - len(failed_logins)) / len(security_logs)) * 100}
                )
                insights.append(insight)
        
        # Business insights
        business_logs = df[df['message'].str.contains(r'(?i)payment|order|purchase|transaction', case=False, na=False)]
        if not business_logs.empty:
            failed_transactions = business_logs[business_logs['message'].str.contains(r'(?i)failed|error|declined', case=False, na=False)]
            if not failed_transactions.empty:
                insight = Insight(
                    category='business',
                    title='Transaction Issues Detected',
                    description=f'Found {len(failed_transactions)} failed transactions',
                    impact='Revenue loss and customer dissatisfaction',
                    recommendation='Review payment processing and implement better error handling',
                    confidence=0.85,
                    data={'failed_transactions': len(failed_transactions), 'success_rate': ((len(business_logs) - len(failed_transactions)) / len(business_logs)) * 100}
                )
                insights.append(insight)
        
        # System health insights
        error_rate = len(df[df['level'].isin(['ERROR', 'CRITICAL'])]) / len(df)
        if error_rate > 0.05:  # > 5% error rate
            insight = Insight(
                category='system_health',
                title='High Error Rate Detected',
                description=f'Error rate is {error_rate:.1%}, which is above acceptable threshold',
                impact='System stability and reliability issues',
                recommendation='Investigate root causes and implement better error handling',
                confidence=0.9,
                data={'error_rate': error_rate, 'threshold': 0.05}
            )
            insights.append(insight)
        
        # Resource utilization insights
        resource_logs = df[df['message'].str.contains(r'(?i)memory|cpu|disk|space', case=False, na=False)]
        if not resource_logs.empty:
            memory_issues = resource_logs[resource_logs['message'].str.contains(r'(?i)memory', case=False, na=False)]
            if not memory_issues.empty:
                insight = Insight(
                    category='resources',
                    title='Memory Issues Detected',
                    description=f'Found {len(memory_issues)} memory-related issues',
                    impact='System performance and stability',
                    recommendation='Monitor memory usage and consider scaling resources',
                    confidence=0.8,
                    data={'memory_issues': len(memory_issues), 'percentage': (len(memory_issues) / len(resource_logs)) * 100}
                )
                insights.append(insight)
        
        self.insights = insights
        return insights
    
    async def _analyze_trends(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends in log data"""
        if len(logs) < 100:
            return {'message': 'Insufficient data for trend analysis'}
        
        df = pd.DataFrame(logs)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        
        trends = {}
        
        # Error rate trend
        daily_errors = df[df['level'].isin(['ERROR', 'CRITICAL'])].groupby('date').size()
        if len(daily_errors) > 1:
            error_trend = np.polyfit(range(len(daily_errors)), daily_errors.values, 1)
            trends['error_trend'] = {
                'slope': error_trend[0],
                'direction': 'increasing' if error_trend[0] > 0 else 'decreasing',
                'confidence': abs(error_trend[0]) / (daily_errors.std() + 1e-6)
            }
        
        # Volume trend
        daily_volume = df.groupby('date').size()
        if len(daily_volume) > 1:
            volume_trend = np.polyfit(range(len(daily_volume)), daily_volume.values, 1)
            trends['volume_trend'] = {
                'slope': volume_trend[0],
                'direction': 'increasing' if volume_trend[0] > 0 else 'decreasing',
                'confidence': abs(volume_trend[0]) / (daily_volume.std() + 1e-6)
            }
        
        # Peak hours analysis
        hourly_activity = df.groupby('hour').size()
        peak_hours = hourly_activity.nlargest(3).index.tolist()
        trends['peak_hours'] = {
            'hours': peak_hours,
            'avg_activity': hourly_activity.mean(),
            'peak_activity': hourly_activity.max()
        }
        
        # Day of week patterns
        dow_activity = df.groupby('day_of_week').size()
        busiest_days = dow_activity.nlargest(3).index.tolist()
        trends['day_of_week_patterns'] = {
            'busiest_days': busiest_days,
            'day_names': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'activity_by_day': dow_activity.to_dict()
        }
        
        return trends
    
    async def _generate_recommendations(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if len(logs) < 50:
            return recommendations
        
        df = pd.DataFrame(logs)
        
        # Error rate recommendations
        error_rate = len(df[df['level'].isin(['ERROR', 'CRITICAL'])]) / len(df)
        if error_rate > 0.05:
            recommendations.append({
                'priority': 'high',
                'category': 'reliability',
                'title': 'Reduce Error Rate',
                'description': f'Error rate is {error_rate:.1%}, above 5% threshold',
                'action': 'Investigate root causes of errors and implement better error handling',
                'impact': 'System reliability and user experience'
            })
        
        # Performance recommendations
        slow_logs = df[df['message'].str.contains(r'slow|timeout|performance', case=False, na=False)]
        if len(slow_logs) > len(df) * 0.1:  # > 10% slow operations
            recommendations.append({
                'priority': 'medium',
                'category': 'performance',
                'title': 'Optimize Performance',
                'description': f'{len(slow_logs)} slow operations detected',
                'action': 'Profile slow operations and optimize bottlenecks',
                'impact': 'User experience and system efficiency'
            })
        
        # Security recommendations
        security_logs = df[df['message'].str.contains(r'(?i)attack|breach|unauthorized', case=False, na=False)]
        if len(security_logs) > 0:
            recommendations.append({
                'priority': 'high',
                'category': 'security',
                'title': 'Enhance Security',
                'description': f'{len(security_logs)} security-related events detected',
                'action': 'Review security logs and implement additional monitoring',
                'impact': 'System security and data protection'
            })
        
        # Resource recommendations
        resource_logs = df[df['message'].str.contains(r'(?i)memory|cpu|disk.*full', case=False, na=False)]
        if len(resource_logs) > len(df) * 0.05:  # > 5% resource issues
            recommendations.append({
                'priority': 'medium',
                'category': 'resources',
                'title': 'Optimize Resource Usage',
                'description': f'{len(resource_logs)} resource-related issues detected',
                'action': 'Monitor resource usage and scale infrastructure if needed',
                'impact': 'System performance and stability'
            })
        
        # Log volume recommendations
        if len(logs) > 10000:  # High volume
            recommendations.append({
                'priority': 'low',
                'category': 'maintenance',
                'title': 'Implement Log Rotation',
                'description': f'High log volume: {len(logs)} entries',
                'action': 'Implement log rotation and archival policies',
                'impact': 'Storage management and system performance'
            })
        
        return recommendations
    
    async def generate_report(self, analysis_results: Dict[str, Any]) -> str:
        """Generate comprehensive analysis report"""
        report = {
            'analysis_metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'analyzer_version': '1.0.0',
                'data_source': 'FlavorSnap Logs'
            },
            'results': analysis_results
        }
        
        return json.dumps(report, indent=2, default=str)
    
    async def export_patterns(self, filepath: str):
        """Export detected patterns to file"""
        if not self.patterns:
            return
        
        patterns_data = [asdict(pattern) for pattern in self.patterns]
        
        with open(filepath, 'w') as f:
            json.dump(patterns_data, f, indent=2, default=str)
        
        logger.info(f"Patterns exported to {filepath}")
    
    async def export_anomalies(self, filepath: str):
        """Export detected anomalies to file"""
        if not self.anomalies:
            return
        
        anomalies_data = [asdict(anomaly) for anomaly in self.anomalies]
        
        with open(filepath, 'w') as f:
            json.dump(anomalies_data, f, indent=2, default=str)
        
        logger.info(f"Anomalies exported to {filepath}")
    
    async def export_insights(self, filepath: str):
        """Export insights to file"""
        if not self.insights:
            return
        
        insights_data = [asdict(insight) for insight in self.insights]
        
        with open(filepath, 'w') as f:
            json.dump(insights_data, f, indent=2, default=str)
        
        logger.info(f"Insights exported to {filepath}")

# Example usage
if __name__ == "__main__":
    config = {
        'output_dir': '/app/logs/analysis',
        'pattern_detection_threshold': 5,
        'anomaly_detection_threshold': 2.0
    }
    
    analyzer = LogAnalyzer(config)
    
    # Example log data
    sample_logs = [
        {
            'timestamp': '2024-04-24T10:00:00Z',
            'level': 'INFO',
            'logger': 'flavorsnap.api',
            'message': 'User login successful',
            'module': 'auth',
            'function': 'login',
            'line': 45,
            'thread': 12345,
            'process': 6789,
            'extra': {'user_id': 'user123', 'ip_address': '192.168.1.1'}
        },
        {
            'timestamp': '2024-04-24T10:01:00Z',
            'level': 'ERROR',
            'logger': 'flavorsnap.api',
            'message': 'Database connection failed: timeout',
            'module': 'database',
            'function': 'connect',
            'line': 23,
            'thread': 12346,
            'process': 6789,
            'extra': {'error_code': 'DB_TIMEOUT'}
        },
        {
            'timestamp': '2024-04-24T10:02:00Z',
            'level': 'WARNING',
            'logger': 'flavorsnap.performance',
            'message': 'Slow request detected: response time 2.5s',
            'module': 'api',
            'function': 'handle_request',
            'line': 67,
            'thread': 12347,
            'process': 6789,
            'extra': {'response_time': 2.5, 'endpoint': '/api/predict'}
        }
    ]
    
    async def run_analysis():
        results = await analyzer.analyze_logs(sample_logs)
        report = await analyzer.generate_report(results)
        
        print("Log Analysis Results:")
        print("=" * 50)
        print(report)
        
        # Export results
        await analyzer.export_patterns('/tmp/patterns.json')
        await analyzer.export_anomalies('/tmp/anomalies.json')
        await analyzer.export_insights('/tmp/insights.json')
    
    asyncio.run(run_analysis())
