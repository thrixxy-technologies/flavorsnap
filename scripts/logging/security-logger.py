#!/usr/bin/env python3
"""
Security Logger for FlavorSnap
Implements comprehensive security event logging and monitoring
"""

import asyncio
import json
import hashlib
import re
import aiohttp
import aiofiles
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import prometheus_client as prom

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityEventType(Enum):
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    API_ACCESS = "api_access"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    MALICIOUS_REQUEST = "malicious_request"
    INJECTION_ATTEMPT = "injection_attempt"
    BRUTE_FORCE_ATTACK = "brute_force_attack"
    DDOS_ATTACK = "ddos_attack"
    SESSION_HIJACK = "session_hijack"
    POLICY_VIOLATION = "policy_violation"
    COMPLIANCE_BREACH = "compliance_breach"

class SecuritySeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityEvent:
    id: str
    event_type: SecurityEventType
    severity: SecuritySeverity
    threat_level: ThreatLevel
    timestamp: datetime
    user_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    resource: Optional[str]
    action: Optional[str]
    result: Optional[str]
    details: Dict[str, Any]
    source: str
    correlation_id: Optional[str]
    hash_value: str

@dataclass
class SecurityIncident:
    id: str
    title: str
    description: str
    severity: SecuritySeverity
    threat_level: ThreatLevel
    status: str
    created_at: datetime
    updated_at: datetime
    events: List[str]
    affected_users: List[str]
    affected_resources: List[str]
    mitigation_actions: List[str]
    investigation_notes: List[str]

class PrometheusMetrics:
    """Prometheus metrics for security logging"""
    
    def __init__(self):
        self.security_events = prom.Counter(
            'security_events_total',
            'Total security events',
            ['event_type', 'severity', 'result']
        )
        
        self.failed_login_attempts = prom.Counter(
            'security_failed_login_attempts_total',
            'Total failed login attempts',
            ['ip_address', 'user_id']
        )
        
        self.suspicious_activities = prom.Counter(
            'security_suspicious_activities_total',
            'Total suspicious activities',
            ['activity_type', 'severity']
        )
        
        self.security_incidents = prom.Counter(
            'security_incidents_total',
            'Total security incidents',
            ['severity', 'status']
        )
        
        self.threat_level = prom.Gauge(
            'security_current_threat_level',
            'Current threat level'
        )
        
        self.blocked_requests = prom.Counter(
            'security_blocked_requests_total',
            'Total blocked requests',
            ['block_reason', 'ip_address']
        )

class SecurityLogger:
    """Advanced security logger with threat detection"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.events: List[SecurityEvent] = []
        self.incidents: Dict[str, SecurityIncident] = {}
        self.blocked_ips: Dict[str, datetime] = {}
        self.suspicious_patterns: List[Dict[str, Any]] = []
        
        # Metrics
        self.metrics = PrometheusMetrics()
        
        # Security patterns and rules
        self.threat_patterns = [
            {
                'name': 'sql_injection',
                'pattern': r'(?i)(union|select|insert|update|delete|drop|create|alter)\s+.*\s+(from|into)',
                'severity': SecuritySeverity.HIGH,
                'threat_level': ThreatLevel.HIGH
            },
            {
                'name': 'xss_attempt',
                'pattern': r'(?i)<script[^>]*>.*?</script>',
                'severity': SecuritySeverity.HIGH,
                'threat_level': ThreatLevel.HIGH
            },
            {
                'name': 'path_traversal',
                'pattern': r'(?i)(\.\./|\.\.\\|%2e%2f|%252e%252f)',
                'severity': SecuritySeverity.HIGH,
                'threat_level': ThreatLevel.HIGH
            },
            {
                'name': 'command_injection',
                'pattern': r'(?i)(;|\||&&|\|\|)\s*(rm|del|format|shutdown|reboot)',
                'severity': SecuritySeverity.CRITICAL,
                'threat_level': ThreatLevel.CRITICAL
            }
        ]
        
        # Suspicious activity patterns
        self.suspicious_patterns = [
            {
                'name': 'multiple_failed_logins',
                'condition': lambda events: len([
                    e for e in events 
                    if e.event_type == SecurityEventType.LOGIN_FAILURE
                    and (datetime.utcnow() - e.timestamp).total_seconds() < 300
                ]) >= 5,
                'severity': SecuritySeverity.HIGH,
                'message': 'Multiple failed login attempts detected'
            },
            {
                'name': 'unusual_access_time',
                'condition': lambda events: self._check_unusual_access_times(events),
                'severity': SecuritySeverity.MEDIUM,
                'message': 'Access detected at unusual time'
            },
            {
                'name': 'privilege_escalation',
                'condition': lambda events: any(
                    e.event_type == SecurityEventType.PRIVILEGE_ESCALATION
                    for e in events
                ),
                'severity': SecuritySeverity.CRITICAL,
                'message': 'Privilege escalation attempt detected'
            }
        ]
    
    async def log_security_event(self, event_type: SecurityEventType,
                             severity: SecuritySeverity,
                             user_id: str = None,
                             ip_address: str = None,
                             user_agent: str = None,
                             session_id: str = None,
                             resource: str = None,
                             action: str = None,
                             result: str = None,
                             details: Dict[str, Any] = None,
                             source: str = 'unknown',
                             correlation_id: str = None) -> SecurityEvent:
        """Log a security event"""
        import uuid
        
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        # Determine threat level
        threat_level = self._calculate_threat_level(event_type, severity, details)
        
        # Create security event
        event = SecurityEvent(
            id=event_id,
            event_type=event_type,
            severity=severity,
            threat_level=threat_level,
            timestamp=timestamp,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
            source=source,
            correlation_id=correlation_id,
            hash_value=self._generate_event_hash(event_type, user_id, ip_address, timestamp)
        )
        
        # Store event
        self.events.append(event)
        
        # Update metrics
        self.metrics.security_events.labels(
            event_type=event_type.value,
            severity=severity.value,
            result=result or 'unknown'
        ).inc()
        
        # Check for suspicious patterns
        await self._check_suspicious_patterns(event)
        
        # Check for threat patterns
        await self._check_threat_patterns(event)
        
        # Check if incident should be created
        await self._check_incident_creation(event)
        
        # Log to main logger
        logger.info(f"Security event logged: {event_type.value} - {severity.value}")
        
        return event
    
    def _calculate_threat_level(self, event_type: SecurityEventType,
                            severity: SecuritySeverity,
                            details: Dict[str, Any]) -> ThreatLevel:
        """Calculate threat level based on event type and context"""
        # Base threat level from severity
        base_threat = {
            SecuritySeverity.LOW: ThreatLevel.LOW,
            SecuritySeverity.MEDIUM: ThreatLevel.MEDIUM,
            SecuritySeverity.HIGH: ThreatLevel.HIGH,
            SecuritySeverity.CRITICAL: ThreatLevel.CRITICAL
        }.get(severity, ThreatLevel.LOW)
        
        # Adjust based on event type
        if event_type in [SecurityEventType.BRUTE_FORCE_ATTACK, SecurityEventType.DDOS_ATTACK]:
            return ThreatLevel.CRITICAL
        
        if event_type in [SecurityEventType.UNAUTHORIZED_ACCESS, SecurityEventType.MALICIOUS_REQUEST]:
            return ThreatLevel.HIGH
        
        if event_type in [SecurityEventType.SUSPICIOUS_ACTIVITY, SecurityEventType.INJECTION_ATTEMPT]:
            return ThreatLevel.MEDIUM
        
        # Adjust based on details
        if details:
            if details.get('blocked', False):
                return base_threat  # Blocked threats are lower priority
            
            if details.get('automated', False):
                return ThreatLevel.HIGH  # Automated attacks are higher priority
        
        return base_threat
    
    def _generate_event_hash(self, event_type: SecurityEventType,
                           user_id: str, ip_address: str,
                           timestamp: datetime) -> str:
        """Generate unique hash for event deduplication"""
        hash_data = f"{event_type.value}:{user_id}:{ip_address}:{timestamp.strftime('%Y%m%d%H%M')}"
        return hashlib.sha256(hash_data.encode()).hexdigest()[:16]
    
    async def _check_suspicious_patterns(self, event: SecurityEvent):
        """Check for suspicious activity patterns"""
        recent_events = [
            e for e in self.events
            if (datetime.utcnow() - e.timestamp).total_seconds() < 3600  # Last hour
        ]
        
        for pattern in self.suspicious_patterns:
            try:
                if pattern['condition'](recent_events + [event]):
                    # Create suspicious activity event
                    await self.log_security_event(
                        event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                        severity=pattern['severity'],
                        user_id=event.user_id,
                        ip_address=event.ip_address,
                        details={
                            'pattern_name': pattern['name'],
                            'description': pattern['message'],
                            'triggering_event_id': event.id
                        },
                        source='pattern_detection',
                        correlation_id=event.correlation_id
                    )
                    
                    logger.warning(f"Suspicious pattern detected: {pattern['name']}")
                    
            except Exception as e:
                logger.error(f"Error checking suspicious pattern {pattern['name']}: {e}")
    
    async def _check_threat_patterns(self, event: SecurityEvent):
        """Check for known threat patterns in event details"""
        if not event.details:
            return
        
        # Check in message, user agent, and other text fields
        text_to_check = [
            event.details.get('message', ''),
            event.user_agent or '',
            event.action or '',
            json.dumps(event.details)
        ]
        
        for pattern in self.threat_patterns:
            for text in text_to_check:
                if re.search(pattern['pattern'], text):
                    # Create threat event
                    await self.log_security_event(
                        event_type=SecurityEventType.MALICIOUS_REQUEST,
                        severity=pattern['severity'],
                        user_id=event.user_id,
                        ip_address=event.ip_address,
                        user_agent=event.user_agent,
                        details={
                            'threat_pattern': pattern['name'],
                            'matched_text': text[:200],  # First 200 chars
                            'original_event_id': event.id
                        },
                        source='threat_detection',
                        correlation_id=event.correlation_id
                    )
                    
                    logger.warning(f"Threat pattern detected: {pattern['name']}")
                    break
    
    async def _check_incident_creation(self, event: SecurityEvent):
        """Check if security incident should be created"""
        # Create incident for critical events
        if event.severity == SecuritySeverity.CRITICAL:
            await self._create_security_incident([event])
        
        # Create incident for multiple related events
        if event.event_type in [SecurityEventType.LOGIN_FAILURE, SecurityEventType.UNAUTHORIZED_ACCESS]:
            related_events = [
                e for e in self.events
                if (e.user_id == event.user_id or e.ip_address == event.ip_address) and
                   (datetime.utcnow() - e.timestamp).total_seconds() < 1800 and  # 30 minutes
                   e.event_type in [SecurityEventType.LOGIN_FAILURE, SecurityEventType.UNAUTHORIZED_ACCESS]
            ]
            
            if len(related_events) >= 3:
                await self._create_security_incident(related_events + [event])
    
    def _check_unusual_access_times(self, events: List[SecurityEvent]) -> bool:
        """Check for access at unusual times"""
        if not events:
            return False
        
        # Get access times for the user
        access_times = [
            e.timestamp.hour for e in events
            if e.event_type == SecurityEventType.LOGIN_SUCCESS and e.user_id
        ]
        
        if len(access_times) < 5:
            return False  # Not enough data
        
        # Check if current access is outside normal hours (9-17)
        current_hour = datetime.utcnow().hour
        normal_hours = set(range(9, 18))  # 9 AM to 5 PM
        
        return current_hour not in normal_hours
    
    async def _create_security_incident(self, events: List[SecurityEvent]):
        """Create a security incident from events"""
        import uuid
        
        incident_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        # Determine incident severity and threat level
        max_severity = max(e.severity for e in events)
        max_threat = max(e.threat_level for e in events)
        
        severity_map = {
            SecuritySeverity.LOW: 1,
            SecuritySeverity.MEDIUM: 2,
            SecuritySeverity.HIGH: 3,
            SecuritySeverity.CRITICAL: 4
        }
        
        # Create incident
        incident = SecurityIncident(
            id=incident_id,
            title=f"Security Incident - {max_severity.value.upper()}",
            description=f"Security incident created from {len(events)} related events",
            severity=max_severity,
            threat_level=max_threat,
            status='open',
            created_at=timestamp,
            updated_at=timestamp,
            events=[e.id for e in events],
            affected_users=list(set(e.user_id for e in events if e.user_id)),
            affected_resources=list(set(e.resource for e in events if e.resource)),
            mitigation_actions=[],
            investigation_notes=[]
        )
        
        self.incidents[incident_id] = incident
        
        # Update metrics
        self.metrics.security_incidents.labels(
            severity=max_severity.value,
            status='open'
        ).inc()
        
        logger.warning(f"Security incident created: {incident_id}")
    
    async def block_ip_address(self, ip_address: str, reason: str, duration_hours: int = 24):
        """Block an IP address"""
        block_until = datetime.utcnow() + timedelta(hours=duration_hours)
        self.blocked_ips[ip_address] = block_until
        
        # Update metrics
        self.metrics.blocked_requests.labels(
            block_reason=reason,
            ip_address=ip_address
        ).inc()
        
        logger.info(f"IP address blocked: {ip_address} until {block_until}")
    
    async def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP address is blocked"""
        if ip_address not in self.blocked_ips:
            return False
        
        block_until = self.blocked_ips[ip_address]
        if datetime.utcnow() > block_until:
            # Remove expired block
            del self.blocked_ips[ip_address]
            return False
        
        return True
    
    async def get_security_events(self, event_type: SecurityEventType = None,
                              user_id: str = None,
                              ip_address: str = None,
                              hours: int = 24,
                              severity: SecuritySeverity = None) -> List[SecurityEvent]:
        """Get security events with filters"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        filtered_events = [
            event for event in self.events
            if event.timestamp > cutoff_time
        ]
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
        
        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]
        
        if ip_address:
            filtered_events = [e for e in filtered_events if e.ip_address == ip_address]
        
        if severity:
            filtered_events = [e for e in filtered_events if e.severity == severity]
        
        return filtered_events
    
    async def get_security_incidents(self, status: str = None,
                                 severity: SecuritySeverity = None,
                                 hours: int = 168) -> List[SecurityIncident]:  # Default 7 days
        """Get security incidents"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        filtered_incidents = [
            incident for incident in self.incidents.values()
            if incident.created_at > cutoff_time
        ]
        
        if status:
            filtered_incidents = [i for i in filtered_incidents if i.status == status]
        
        if severity:
            filtered_incidents = [i for i in filtered_incidents if i.severity == severity]
        
        return filtered_incidents
    
    async def get_threat_level(self) -> ThreatLevel:
        """Get current threat level"""
        if not self.events:
            return ThreatLevel.NONE
        
        # Get events from last hour
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        recent_events = [
            event for event in self.events
            if event.timestamp > cutoff_time
        ]
        
        if not recent_events:
            return ThreatLevel.NONE
        
        # Calculate threat level based on recent events
        threat_scores = {
            ThreatLevel.NONE: 0,
            ThreatLevel.LOW: 0,
            ThreatLevel.MEDIUM: 0,
            ThreatLevel.HIGH: 0,
            ThreatLevel.CRITICAL: 0
        }
        
        for event in recent_events:
            threat_scores[event.threat_level] += {
                SecuritySeverity.LOW: 1,
                SecuritySeverity.MEDIUM: 2,
                SecuritySeverity.HIGH: 3,
                SecuritySeverity.CRITICAL: 5
            }.get(event.severity, 1)
        
        # Find highest threat level with score
        for threat_level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH, ThreatLevel.MEDIUM, ThreatLevel.LOW]:
            if threat_scores[threat_level] > 0:
                self.metrics.threat_level.set({
                    ThreatLevel.NONE: 0,
                    ThreatLevel.LOW: 1,
                    ThreatLevel.MEDIUM: 2,
                    ThreatLevel.HIGH: 3,
                    ThreatLevel.CRITICAL: 4
                }.get(threat_level))
                return threat_level
        
        return ThreatLevel.NONE
    
    async def generate_security_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get events in time range
        events_in_range = [
            event for event in self.events
            if event.timestamp > cutoff_time
        ]
        
        # Event type distribution
        event_type_counts = {}
        for event in events_in_range:
            event_type_counts[event.event_type.value] = event_type_counts.get(event.event_type.value, 0) + 1
        
        # Severity distribution
        severity_counts = {}
        for event in events_in_range:
            severity_counts[event.severity.value] = severity_counts.get(event.severity.value, 0) + 1
        
        # Top IP addresses
        ip_counts = {}
        for event in events_in_range:
            if event.ip_address:
                ip_counts[event.ip_address] = ip_counts.get(event.ip_address, 0) + 1
        
        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Failed login attempts
        failed_logins = [
            event for event in events_in_range
            if event.event_type == SecurityEventType.LOGIN_FAILURE
        ]
        
        # Incidents
        incidents_in_range = [
            incident for incident in self.incidents.values()
            if incident.created_at > cutoff_time
        ]
        
        # Current threat level
        current_threat = await self.get_threat_level()
        
        report = {
            'report_metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'period_hours': hours,
                'total_events': len(events_in_range),
                'total_incidents': len(incidents_in_range),
                'current_threat_level': current_threat.value
            },
            'event_analysis': {
                'event_type_distribution': event_type_counts,
                'severity_distribution': severity_counts,
                'failed_login_attempts': len(failed_logins),
                'unique_ips': len(ip_counts),
                'top_ips_by_activity': top_ips
            },
            'incidents': [
                {
                    'id': incident.id,
                    'title': incident.title,
                    'severity': incident.severity.value,
                    'threat_level': incident.threat_level.value,
                    'status': incident.status,
                    'created_at': incident.created_at.isoformat(),
                    'events_count': len(incident.events),
                    'affected_users': incident.affected_users,
                    'affected_resources': incident.affected_resources
                }
                for incident in incidents_in_range
            ],
            'recommendations': self._generate_security_recommendations(events_in_range, incidents_in_range),
            'blocked_ips': {
                ip: block_until.isoformat()
                for ip, block_until in self.blocked_ips.items()
                if block_until > datetime.utcnow()
            }
        }
        
        return report
    
    def _generate_security_recommendations(self, events: List[SecurityEvent],
                                     incidents: List[SecurityIncident]) -> List[Dict[str, Any]]:
        """Generate security recommendations based on events and incidents"""
        recommendations = []
        
        # High failed login rate
        failed_logins = [e for e in events if e.event_type == SecurityEventType.LOGIN_FAILURE]
        if len(failed_logins) > 10:
            recommendations.append({
                'priority': 'high',
                'category': 'authentication',
                'title': 'Implement Account Lockout Policy',
                'description': f'{len(failed_logins)} failed login attempts detected',
                'action': 'Implement automatic account lockout after multiple failed attempts'
            })
        
        # Multiple unauthorized access attempts
        unauthorized_attempts = [e for e in events if e.event_type == SecurityEventType.UNAUTHORIZED_ACCESS]
        if len(unauthorized_attempts) > 5:
            recommendations.append({
                'priority': 'high',
                'category': 'access_control',
                'title': 'Review Access Permissions',
                'description': f'{len(unauthorized_attempts)} unauthorized access attempts',
                'action': 'Review and tighten access control policies'
            })
        
        # Suspicious activities
        suspicious_activities = [e for e in events if e.event_type == SecurityEventType.SUSPICIOUS_ACTIVITY]
        if len(suspicious_activities) > 0:
            recommendations.append({
                'priority': 'medium',
                'category': 'monitoring',
                'title': 'Investigate Suspicious Activities',
                'description': f'{len(suspicious_activities)} suspicious activities detected',
                'action': 'Investigate and respond to suspicious activities'
            })
        
        # Open incidents
        open_incidents = [i for i in incidents if i.status == 'open']
        if len(open_incidents) > 0:
            recommendations.append({
                'priority': 'critical',
                'category': 'incident_response',
                'title': 'Address Open Security Incidents',
                'description': f'{len(open_incidents)} security incidents remain open',
                'action': 'Prioritize and resolve open security incidents'
            })
        
        return recommendations
    
    async def export_security_data(self, filepath: str, format: str = 'json'):
        """Export security data to file"""
        try:
            data = {
                'security_events': [asdict(event) for event in self.events],
                'security_incidents': [asdict(incident) for incident in self.incidents.values()],
                'blocked_ips': {
                    ip: block_until.isoformat()
                    for ip, block_until in self.blocked_ips.items()
                },
                'export_timestamp': datetime.utcnow().isoformat()
            }
            
            if format.lower() == 'json':
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
            elif format.lower() == 'csv':
                import pandas as pd
                
                # Export events
                events_df = pd.DataFrame([asdict(event) for event in self.events])
                events_df.to_csv(filepath.replace('.csv', '_events.csv'), index=False)
                
                # Export incidents
                incidents_df = pd.DataFrame([asdict(incident) for incident in self.incidents.values()])
                incidents_df.to_csv(filepath.replace('.csv', '_incidents.csv'), index=False)
            
            logger.info(f"Security data exported to {filepath}")
            
        except Exception as e:
            logger.error(f"Error exporting security data: {e}")

# Example usage
if __name__ == "__main__":
    config = {
        'output_dir': '/app/logs/security',
        'retention_days': 90,
        'alert_thresholds': {
            'failed_logins_per_hour': 5,
            'unauthorized_access_per_hour': 3,
            'suspicious_activities_per_hour': 1
        }
    }
    
    security_logger = SecurityLogger(config)
    
    async def test_security_logging():
        # Test different security events
        await security_logger.log_security_event(
            event_type=SecurityEventType.LOGIN_ATTEMPT,
            severity=SecuritySeverity.INFO,
            user_id='user123',
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0...',
            details={'login_method': 'password'}
        )
        
        await security_logger.log_security_event(
            event_type=SecurityEventType.LOGIN_FAILURE,
            severity=SecuritySeverity.WARNING,
            user_id='user123',
            ip_address='192.168.1.100',
            details={'reason': 'invalid_password'}
        )
        
        await security_logger.log_security_event(
            event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
            severity=SecuritySeverity.HIGH,
            user_id='attacker',
            ip_address='192.168.1.200',
            resource='/admin/users',
            action='GET',
            details={'blocked': True, 'reason': 'insufficient_privileges'}
        )
        
        # Block malicious IP
        await security_logger.block_ip_address('192.168.1.200', 'brute_force_attack', 24)
        
        # Generate security report
        report = await security_logger.generate_security_report(hours=1)
        print("Security Report:")
        print(json.dumps(report, indent=2, default=str))
        
        # Get current threat level
        threat_level = await security_logger.get_threat_level()
        print(f"\nCurrent Threat Level: {threat_level.value}")
        
        # Export security data
        await security_logger.export_security_data('/tmp/security_data.json')
    
    asyncio.run(test_security_logging())
