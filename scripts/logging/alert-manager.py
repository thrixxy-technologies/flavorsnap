#!/usr/bin/env python3
"""
Advanced Alert Manager for FlavorSnap Logging System
Implements intelligent alerting with multiple channels and escalation
"""

import asyncio
import json
import smtplib
import aiohttp
import aiofiles
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertChannel(Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    DISCORD = "discord"
    TEAMS = "teams"

class AlertStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    ESCALATED = "escalated"

@dataclass
class Alert:
    id: str
    title: str
    message: str
    severity: AlertSeverity
    source: str
    timestamp: datetime
    metadata: Dict[str, Any]
    channels: List[AlertChannel]
    status: AlertStatus
    retry_count: int
    last_retry: Optional[datetime]
    escalation_level: int
    acknowledged: bool
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]

@dataclass
class AlertRule:
    name: str
    condition: str
    severity: AlertSeverity
    channels: List[AlertChannel]
    cooldown_minutes: int
    escalation_enabled: bool
    escalation_levels: List[Dict[str, Any]]
    enabled: bool

@dataclass
class AlertTemplate:
    name: str
    subject_template: str
    message_template: str
    severity_colors: Dict[str, str]
    channel_configs: Dict[str, Any]

class AlertManager:
    """Advanced alert manager with multiple channels and escalation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.alerts: List[Alert] = []
        self.rules: List[AlertRule] = []
        self.templates: Dict[str, AlertTemplate] = {}
        self.channel_handlers: Dict[AlertChannel, Any] = {}
        
        # Setup channel handlers
        self._setup_channel_handlers()
        
        # Load default rules and templates
        self._load_default_rules()
        self._load_default_templates()
    
    def _setup_channel_handlers(self):
        """Setup handlers for different alert channels"""
        # Email handler
        if self.config.get('email', {}).get('enabled', False):
            self.channel_handlers[AlertChannel.EMAIL] = EmailHandler(
                self.config.get('email', {})
            )
        
        # Slack handler
        if self.config.get('slack', {}).get('enabled', False):
            self.channel_handlers[AlertChannel.SLACK] = SlackHandler(
                self.config.get('slack', {})
            )
        
        # Webhook handler
        if self.config.get('webhook', {}).get('enabled', False):
            self.channel_handlers[AlertChannel.WEBHOOK] = WebhookHandler(
                self.config.get('webhook', {})
            )
        
        # Discord handler
        if self.config.get('discord', {}).get('enabled', False):
            self.channel_handlers[AlertChannel.DISCORD] = DiscordHandler(
                self.config.get('discord', {})
            )
        
        # Teams handler
        if self.config.get('teams', {}).get('enabled', False):
            self.channel_handlers[AlertChannel.TEAMS] = TeamsHandler(
                self.config.get('teams', {})
            )
    
    def _load_default_rules(self):
        """Load default alert rules"""
        default_rules = [
            AlertRule(
                name="high_error_rate",
                condition="error_rate > 5",
                severity=AlertSeverity.ERROR,
                channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
                cooldown_minutes=15,
                escalation_enabled=True,
                escalation_levels=[
                    {"level": 1, "delay_minutes": 15, "channels": [AlertChannel.EMAIL]},
                    {"level": 2, "delay_minutes": 30, "channels": [AlertChannel.EMAIL, AlertChannel.SLACK]},
                    {"level": 3, "delay_minutes": 60, "channels": [AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.SMS]}
                ],
                enabled=True
            ),
            AlertRule(
                name="security_breach",
                condition="security_event AND severity IN ('high', 'critical')",
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.SMS],
                cooldown_minutes=5,
                escalation_enabled=True,
                escalation_levels=[
                    {"level": 1, "delay_minutes": 5, "channels": [AlertChannel.EMAIL, AlertChannel.SLACK]},
                    {"level": 2, "delay_minutes": 10, "channels": [AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.SMS]}
                ],
                enabled=True
            ),
            AlertRule(
                name="performance_degradation",
                condition="avg_response_time > 2000",
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.EMAIL],
                cooldown_minutes=30,
                escalation_enabled=False,
                escalation_levels=[],
                enabled=True
            ),
            AlertRule(
                name="system_outage",
                condition="service_down OR error_rate > 20",
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.SMS],
                cooldown_minutes=2,
                escalation_enabled=True,
                escalation_levels=[
                    {"level": 1, "delay_minutes": 2, "channels": [AlertChannel.EMAIL, AlertChannel.SLACK]},
                    {"level": 2, "delay_minutes": 5, "channels": [AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.SMS]}
                ],
                enabled=True
            ),
            AlertRule(
                name="compliance_violation",
                condition="compliance_event AND regulation IN ('GDPR', 'HIPAA', 'PCI')",
                severity=AlertSeverity.ERROR,
                channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
                cooldown_minutes=60,
                escalation_enabled=True,
                escalation_levels=[
                    {"level": 1, "delay_minutes": 60, "channels": [AlertChannel.EMAIL]},
                    {"level": 2, "delay_minutes": 120, "channels": [AlertChannel.EMAIL, AlertChannel.SLACK]}
                ],
                enabled=True
            )
        ]
        
        self.rules.extend(default_rules)
    
    def _load_default_templates(self):
        """Load default alert templates"""
        default_templates = {
            "default": AlertTemplate(
                name="default",
                subject_template="[FlavorSnap Alert] {severity}: {title}",
                message_template="""
FlavorSnap Alert Notification

Severity: {severity}
Title: {title}
Message: {message}
Source: {source}
Timestamp: {timestamp}
Metadata: {metadata}

This is an automated alert from the FlavorSnap system.
                """,
                severity_colors={
                    "info": "#36a5f",
                    "warning": "#ff9800",
                    "error": "#f44336",
                    "critical": "#d32f2f"
                },
                channel_configs={}
            ),
            "security": AlertTemplate(
                name="security",
                subject_template="[SECURITY] {title}",
                message_template="""
🚨 SECURITY ALERT 🚨

{severity.upper()}: {title}

{message}

Source: {source}
Timestamp: {timestamp}

Immediate attention required!
                """,
                severity_colors={
                    "info": "#2196f3",
                    "warning": "#ff9800",
                    "error": "#f44336",
                    "critical": "#d32f2f"
                },
                channel_configs={}
            ),
            "performance": AlertTemplate(
                name="performance",
                subject_template="[PERFORMANCE] {title}",
                message_template="""
⚡ PERFORMANCE ALERT ⚡

{severity.upper()}: {title}

{message}

Source: {source}
Timestamp: {timestamp}
Performance Impact: {metadata.get('impact', 'Unknown')}
                """,
                severity_colors={
                    "info": "#4caf50",
                    "warning": "#ff9800",
                    "error": "#f44336",
                    "critical": "#d32f2f"
                },
                channel_configs={}
            )
        }
        
        self.templates.update(default_templates)
    
    async def create_alert(self, title: str, message: str, severity: AlertSeverity,
                        source: str, metadata: Dict[str, Any] = None,
                        channels: List[AlertChannel] = None,
                        template_name: str = "default") -> Alert:
        """Create a new alert"""
        import uuid
        
        alert_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        # Use default channels if not specified
        if channels is None:
            channels = [AlertChannel.EMAIL]  # Default to email
        
        alert = Alert(
            id=alert_id,
            title=title,
            message=message,
            severity=severity,
            source=source,
            timestamp=timestamp,
            metadata=metadata or {},
            channels=channels,
            status=AlertStatus.PENDING,
            retry_count=0,
            last_retry=None,
            escalation_level=0,
            acknowledged=False,
            acknowledged_by=None,
            acknowledged_at=None
        )
        
        self.alerts.append(alert)
        logger.info(f"Created alert {alert_id}: {title}")
        
        # Process alert immediately
        await self._process_alert(alert)
        
        return alert
    
    async def _process_alert(self, alert: Alert):
        """Process an alert through channels and escalation"""
        try:
            # Check if alert should be sent (cooldown, etc.)
            if not await self._should_send_alert(alert):
                return
            
            # Get template
            template = self.templates.get(alert.metadata.get('template', 'default'), 
                                   self.templates.get('default'))
            
            # Format message
            formatted_message = self._format_message(alert, template)
            
            # Send to all configured channels
            for channel in alert.channels:
                if channel in self.channel_handlers:
                    try:
                        await self._send_to_channel(alert, channel, formatted_message)
                        logger.info(f"Alert {alert.id} sent to {channel.value}")
                    except Exception as e:
                        logger.error(f"Failed to send alert {alert.id} to {channel.value}: {e}")
                        await self._handle_send_failure(alert, channel, str(e))
                else:
                    logger.warning(f"No handler configured for channel: {channel.value}")
            
            # Update alert status
            if all(channel in self.channel_handlers for channel in alert.channels):
                alert.status = AlertStatus.SENT
            else:
                alert.status = AlertStatus.FAILED
            
            # Schedule escalation if enabled
            if await self._should_escalate(alert):
                await self._schedule_escalation(alert)
        
        except Exception as e:
            logger.error(f"Error processing alert {alert.id}: {e}")
            alert.status = AlertStatus.FAILED
    
    async def _should_send_alert(self, alert: Alert) -> bool:
        """Check if alert should be sent based on rules"""
        # Check for similar recent alerts
        recent_alerts = [
            a for a in self.alerts
            if (a.source == alert.source and 
                a.title == alert.title and
                a.severity == alert.severity and
                (datetime.utcnow() - a.timestamp).total_seconds() < 300)  # 5 minutes
        ]
        
        if len(recent_alerts) > 2:  # More than 2 similar alerts in 5 minutes
            return False
        
        # Check cooldown for rules
        for rule in self.rules:
            if rule.enabled and await self._evaluate_rule_condition(rule, alert.metadata):
                cooldown_period = timedelta(minutes=rule.cooldown_minutes)
                
                # Check if similar alert was sent recently
                recent_rule_alerts = [
                    a for a in self.alerts
                    if (a.source == alert.source and
                        a.title == alert.title and
                        (datetime.utcnow() - a.timestamp) < cooldown_period)
                ]
                
                if recent_rule_alerts:
                    return False
        
        return True
    
    async def _evaluate_rule_condition(self, rule: AlertRule, metadata: Dict[str, Any]) -> bool:
        """Evaluate alert rule condition"""
        try:
            # Simple condition evaluation (in real implementation, use a proper expression parser)
            condition = rule.condition.lower()
            
            # Check for common conditions
            if 'error_rate' in condition:
                error_rate = metadata.get('error_rate', 0)
                threshold = float(condition.split('>')[-1].strip())
                return error_rate > threshold
            
            if 'security_event' in condition:
                return metadata.get('security_event', False)
            
            if 'avg_response_time' in condition:
                response_time = metadata.get('avg_response_time', 0)
                threshold = float(condition.split('>')[-1].strip())
                return response_time > threshold
            
            if 'service_down' in condition:
                return metadata.get('service_down', False)
            
            if 'compliance_event' in condition:
                return metadata.get('compliance_event', False)
            
            # Default to True if condition can't be parsed
            return True
            
        except Exception as e:
            logger.error(f"Error evaluating rule condition: {e}")
            return True
    
    def _format_message(self, alert: Alert, template: AlertTemplate) -> Dict[str, str]:
        """Format alert message using template"""
        try:
            subject = template.subject_template.format(
                severity=alert.severity.value.upper(),
                title=alert.title,
                source=alert.source
            )
            
            message = template.message_template.format(
                severity=alert.severity.value.upper(),
                title=alert.title,
                message=alert.message,
                source=alert.source,
                timestamp=alert.timestamp.isoformat(),
                metadata=json.dumps(alert.metadata, indent=2)
            )
            
            return {"subject": subject, "message": message}
            
        except Exception as e:
            logger.error(f"Error formatting message: {e}")
            return {
                "subject": f"[FlavorSnap Alert] {alert.title}",
                "message": f"{alert.title}\n\n{alert.message}\n\nSource: {alert.source}\nTimestamp: {alert.timestamp}"
            }
    
    async def _send_to_channel(self, alert: Alert, channel: AlertChannel, formatted_message: Dict[str, str]):
        """Send alert to specific channel"""
        handler = self.channel_handlers[channel]
        await handler.send_alert(alert, formatted_message)
    
    async def _handle_send_failure(self, alert: Alert, channel: AlertChannel, error: str):
        """Handle failed alert sending"""
        alert.retry_count += 1
        alert.last_retry = datetime.utcnow()
        
        # Log failure
        logger.error(f"Alert {alert.id} failed to send to {channel.value}: {error}")
        
        # Check if escalation should be triggered
        if alert.retry_count >= 3:
            await self._escalate_alert(alert, f"Failed to send after {alert.retry_count} attempts")
    
    async def _should_escalate(self, alert: Alert) -> bool:
        """Check if alert should be escalated"""
        for rule in self.rules:
            if rule.enabled and rule.escalation_enabled:
                if await self._evaluate_rule_condition(rule, alert.metadata):
                    return True
        return False
    
    async def _schedule_escalation(self, alert: Alert):
        """Schedule alert escalation"""
        if not alert.escalation_level:
            return
        
        # Find relevant rule
        for rule in self.rules:
            if rule.enabled and rule.escalation_enabled:
                if await self._evaluate_rule_condition(rule, alert.metadata):
                    if alert.escalation_level < len(rule.escalation_levels):
                        next_level = rule.escalation_levels[alert.escalation_level]
                        delay_minutes = next_level.get('delay_minutes', 60)
                        
                        # Schedule escalation
                        escalation_time = datetime.utcnow() + timedelta(minutes=delay_minutes)
                        
                        logger.info(f"Scheduled escalation for alert {alert.id} to level {alert.escalation_level + 1} at {escalation_time}")
                        
                        # In real implementation, use a job scheduler
                        # For now, just log the escalation
                        await asyncio.sleep(delay_minutes * 60)  # Simulate delay
                        await self._escalate_alert(alert, f"Automatic escalation to level {alert.escalation_level + 1}")
                    break
    
    async def _escalate_alert(self, alert: Alert, reason: str):
        """Escalate alert to next level"""
        alert.escalation_level += 1
        alert.status = AlertStatus.ESCALATED
        
        # Add escalation metadata
        alert.metadata['escalation_reason'] = reason
        alert.metadata['escalation_timestamp'] = datetime.utcnow().isoformat()
        
        # Find escalation channels
        escalation_channels = []
        for rule in self.rules:
            if rule.enabled and rule.escalation_enabled:
                if await self._evaluate_rule_condition(rule, alert.metadata):
                    if alert.escalation_level <= len(rule.escalation_levels):
                        level_config = rule.escalation_levels[min(alert.escalation_level - 1, len(rule.escalation_levels) - 1)]
                        escalation_channels.extend(level_config.get('channels', []))
        
        # Send to escalation channels
        if escalation_channels:
            template = self.templates.get('security', self.templates.get('default'))
            formatted_message = self._format_message(alert, template)
            
            for channel in escalation_channels:
                if channel in self.channel_handlers:
                    try:
                        await self._send_to_channel(alert, channel, formatted_message)
                        logger.info(f"Alert {alert.id} escalated to {channel.value}")
                    except Exception as e:
                        logger.error(f"Failed to escalate alert {alert.id} to {channel.value}: {e}")
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str, 
                            note: str = None) -> bool:
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.utcnow()
                
                if note:
                    alert.metadata['acknowledgment_note'] = note
                
                logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                return True
        
        return False
    
    async def get_active_alerts(self, severity: AlertSeverity = None, 
                              source: str = None) -> List[Alert]:
        """Get active alerts"""
        active_alerts = [
            alert for alert in self.alerts
            if alert.status in [AlertStatus.PENDING, AlertStatus.SENT, AlertStatus.ESCALATED]
            and not alert.acknowledged
        ]
        
        if severity:
            active_alerts = [a for a in active_alerts if a.severity == severity]
        
        if source:
            active_alerts = [a for a in active_alerts if a.source == source]
        
        return active_alerts
    
    async def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        total_alerts = len(self.alerts)
        
        # Status distribution
        status_counts = {}
        for status in AlertStatus:
            status_counts[status.value] = len([a for a in self.alerts if a.status == status])
        
        # Severity distribution
        severity_counts = {}
        for severity in AlertSeverity:
            severity_counts[severity.value] = len([a for a in self.alerts if a.severity == severity])
        
        # Channel distribution
        channel_counts = {}
        for alert in self.alerts:
            for channel in alert.channels:
                channel_counts[channel.value] = channel_counts.get(channel.value, 0) + 1
        
        # Recent alerts (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        recent_alerts = len([a for a in self.alerts if a.timestamp > cutoff_time])
        
        # Acknowledgment rate
        acknowledged_count = len([a for a in self.alerts if a.acknowledged])
        acknowledgment_rate = (acknowledged_count / total_alerts) * 100 if total_alerts > 0 else 0
        
        return {
            'total_alerts': total_alerts,
            'status_distribution': status_counts,
            'severity_distribution': severity_counts,
            'channel_distribution': channel_counts,
            'recent_alerts_24h': recent_alerts,
            'acknowledgment_rate': acknowledgment_rate,
            'escalated_alerts': len([a for a in self.alerts if a.escalation_level > 0])
        }

class EmailHandler:
    """Email alert handler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.smtp_server = config.get('smtp_server', 'localhost')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.from_email = config.get('from_email', 'alerts@flavorsnap.com')
        self.use_tls = config.get('use_tls', True)
    
    async def send_alert(self, alert: Alert, formatted_message: Dict[str, str]):
        """Send alert via email"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.config.get('recipients', []))
            msg['Subject'] = formatted_message['subject']
            
            msg.attach(MIMEText(formatted_message['message'], 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            
            if self.username and self.password:
                server.login(self.username, self.password)
            
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            raise Exception(f"Email send failed: {e}")

class SlackHandler:
    """Slack alert handler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('webhook_url', '')
        self.channel = config.get('channel', '#alerts')
        self.username = config.get('username', 'FlavorSnap')
    
    async def send_alert(self, alert: Alert, formatted_message: Dict[str, str]):
        """Send alert to Slack"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "channel": self.channel,
                "username": self.username,
                "text": formatted_message['subject'],
                "attachments": [
                    {
                        "color": self._get_slack_color(alert.severity),
                        "title": alert.title,
                        "text": formatted_message['message'],
                        "fields": [
                            {
                                "title": "Source",
                                "value": alert.source,
                                "short": True
                            },
                            {
                                "title": "Severity",
                                "value": alert.severity.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Time",
                                "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                "short": True
                            }
                        ]
                    }
                ]
            }
            
            async with session.post(self.webhook_url, json=payload) as response:
                if response.status != 200:
                    raise Exception(f"Slack webhook failed: {response.status}")
    
    def _get_slack_color(self, severity: AlertSeverity) -> str:
        """Get Slack color for severity"""
        colors = {
            AlertSeverity.INFO: "#36a5f",
            AlertSeverity.WARNING: "#ff9800",
            AlertSeverity.ERROR: "#f44336",
            AlertSeverity.CRITICAL: "#d32f2f"
        }
        return colors.get(severity, "#36a5f")

class WebhookHandler:
    """Generic webhook alert handler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('webhook_url', '')
        self.headers = config.get('headers', {'Content-Type': 'application/json'})
        self.auth = config.get('auth', None)
    
    async def send_alert(self, alert: Alert, formatted_message: Dict[str, str]):
        """Send alert to webhook"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "alert_id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity.value,
                "source": alert.source,
                "timestamp": alert.timestamp.isoformat(),
                "metadata": alert.metadata,
                "subject": formatted_message['subject'],
                "full_message": formatted_message['message']
            }
            
            headers = self.headers.copy()
            if self.auth:
                headers['Authorization'] = f"Bearer {self.auth}"
            
            async with session.post(self.webhook_url, json=payload, headers=headers) as response:
                if response.status not in [200, 201, 202]:
                    raise Exception(f"Webhook failed: {response.status}")

class DiscordHandler:
    """Discord alert handler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('webhook_url', '')
        self.username = config.get('username', 'FlavorSnap')
    
    async def send_alert(self, alert: Alert, formatted_message: Dict[str, str]):
        """Send alert to Discord"""
        async with aiohttp.ClientSession() as session:
            # Discord embed color based on severity
            color = self._get_discord_color(alert.severity)
            
            payload = {
                "username": self.username,
                "embeds": [
                    {
                        "title": formatted_message['subject'],
                        "description": formatted_message['message'],
                        "color": color,
                        "fields": [
                            {
                                "name": "Source",
                                "value": alert.source,
                                "inline": True
                            },
                            {
                                "name": "Severity",
                                "value": alert.severity.value.upper(),
                                "inline": True
                            },
                            {
                                "name": "Time",
                                "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                "inline": True
                            }
                        ],
                        "timestamp": alert.timestamp.isoformat()
                    }
                ]
            }
            
            async with session.post(self.webhook_url, json=payload) as response:
                if response.status != 204:
                    raise Exception(f"Discord webhook failed: {response.status}")
    
    def _get_discord_color(self, severity: AlertSeverity) -> int:
        """Get Discord color for severity"""
        colors = {
            AlertSeverity.INFO: 0x36a5f,
            AlertSeverity.WARNING: 0xff9800,
            AlertSeverity.ERROR: 0xf44336,
            AlertSeverity.CRITICAL: 0xd32f2f
        }
        return colors.get(severity, 0x36a5f)

class TeamsHandler:
    """Microsoft Teams alert handler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('webhook_url', '')
        self.title = config.get('title', 'FlavorSnap Alert')
    
    async def send_alert(self, alert: Alert, formatted_message: Dict[str, str]):
        """Send alert to Teams"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": self._get_teams_color(alert.severity),
                "summary": formatted_message['subject'],
                "sections": [
                    {
                        "activityTitle": self.title,
                        "activitySubtitle": formatted_message['subject'],
                        "facts": [
                            {
                                "name": "Severity",
                                "value": alert.severity.value.upper()
                            },
                            {
                                "name": "Source",
                                "value": alert.source
                            },
                            {
                                "name": "Time",
                                "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                            }
                        ],
                        "markdown": True,
                        "text": formatted_message['message']
                    }
                ]
            }
            
            async with session.post(self.webhook_url, json=payload) as response:
                if response.status != 200:
                    raise Exception(f"Teams webhook failed: {response.status}")
    
    def _get_teams_color(self, severity: AlertSeverity) -> str:
        """Get Teams color for severity"""
        colors = {
            AlertSeverity.INFO: "00FF00",
            AlertSeverity.WARNING: "FFD700",
            AlertSeverity.ERROR: "FF0000",
            AlertSeverity.CRITICAL: "8B0000"
        }
        return colors.get(severity, "00FF00")

# Example usage
if __name__ == "__main__":
    config = {
        "email": {
            "enabled": True,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "alerts@flavorsnap.com",
            "password": "your-password",
            "from_email": "alerts@flavorsnap.com",
            "use_tls": True,
            "recipients": ["admin@flavorsnap.com", "devops@flavorsnap.com"]
        },
        "slack": {
            "enabled": True,
            "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
            "channel": "#alerts",
            "username": "FlavorSnap"
        },
        "webhook": {
            "enabled": True,
            "webhook_url": "https://api.example.com/alerts",
            "headers": {"Content-Type": "application/json"},
            "auth": "your-api-token"
        },
        "discord": {
            "enabled": True,
            "webhook_url": "https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK",
            "username": "FlavorSnap"
        },
        "teams": {
            "enabled": True,
            "webhook_url": "https://outlook.office.com/webhook/YOUR/TEAMS/WEBHOOK",
            "title": "FlavorSnap Alert"
        }
    }
    
    async def test_alerts():
        alert_manager = AlertManager(config)
        
        # Test different types of alerts
        await alert_manager.create_alert(
            title="High Error Rate Detected",
            message="Error rate has exceeded 5% threshold",
            severity=AlertSeverity.ERROR,
            source="log_analyzer",
            metadata={"error_rate": 7.5, "threshold": 5.0},
            channels=[AlertChannel.EMAIL, AlertChannel.SLACK]
        )
        
        await alert_manager.create_alert(
            title="Security Breach Detected",
            message="Multiple failed login attempts detected from suspicious IP",
            severity=AlertSeverity.CRITICAL,
            source="security_monitor",
            metadata={"ip_address": "192.168.1.100", "failed_attempts": 10},
            channels=[AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.SMS],
            template_name="security"
        )
        
        await alert_manager.create_alert(
            title="Performance Degradation",
            message="Average response time is 3.5 seconds",
            severity=AlertSeverity.WARNING,
            source="performance_monitor",
            metadata={"avg_response_time": 3500, "threshold": 2000},
            channels=[AlertChannel.EMAIL],
            template_name="performance"
        )
        
        # Get statistics
        stats = await alert_manager.get_alert_statistics()
        print("Alert Statistics:")
        print(json.dumps(stats, indent=2, default=str))
        
        # Get active alerts
        active_alerts = await alert_manager.get_active_alerts()
        print(f"\nActive Alerts: {len(active_alerts)}")
        
        # Test acknowledgment
        if active_alerts:
            await alert_manager.acknowledge_alert(
                active_alerts[0].id,
                "admin@flavorsnap.com",
                "Investigating the issue"
            )
    
    asyncio.run(test_alerts())
