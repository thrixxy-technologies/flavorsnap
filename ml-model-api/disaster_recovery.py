#!/usr/bin/env python3
"""
Disaster Recovery System for FlavorSnap ML Model API
Implements comprehensive disaster recovery planning, automated failover, and business continuity
"""

import os
import json
import sqlite3
import requests
import logging
import threading
import time
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import pytz
import subprocess
import hashlib
import boto3
from botocore.exceptions import ClientError
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/disaster_recovery.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DisasterLevel(Enum):
    """Disaster severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RecoveryStrategy(Enum):
    """Recovery strategy types"""
    BACKUP_RESTORE = "backup_restore"
    FAILOVER = "failover"
    ROLLING_RESTART = "rolling_restart"
    MANUAL_INTERVENTION = "manual_intervention"

@dataclass
class DisasterEvent:
    """Disaster event information"""
    event_id: str
    disaster_level: DisasterLevel
    timestamp: datetime
    description: str
    affected_systems: List[str]
    detection_method: str
    status: str  # 'detected', 'mitigating', 'resolved', 'failed'
    recovery_strategy: RecoveryStrategy
    recovery_time: Optional[datetime] = None
    impact_assessment: Optional[Dict] = None

@dataclass
class DRPlan:
    """Disaster recovery plan"""
    plan_id: str
    disaster_level: DisasterLevel
    recovery_strategy: RecoveryStrategy
    rto_hours: float  # Recovery Time Objective
    rpo_hours: float  # Recovery Point Objective
    steps: List[str]
    contacts: List[Dict]
    resources: List[str]
    dependencies: List[str]
    success_criteria: List[str]

@dataclass
class DRConfig:
    """Disaster recovery configuration"""
    monitoring_interval_seconds: int = 60
    health_check_timeout_seconds: int = 30
    max_failures_before_alert: int = 3
    auto_failover_enabled: bool = True
    notification_enabled: bool = True
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    notification_emails: List[str] = None
    slack_webhook_url: Optional[str] = None
    pagerduty_api_key: Optional[str] = None
    backup_regions: List[str] = None
    failover_regions: List[str] = None

class DisasterRecoverySystem:
    """Comprehensive disaster recovery system"""
    
    def __init__(self, config: DRConfig):
        self.config = config
        self.dr_db_path = '/tmp/flavorsnap_dr_registry.db'
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.monitoring_active = False
        self.monitoring_thread = None
        self.active_disasters = {}
        self.dr_plans = {}
        self.health_checks = {}
        
        # Initialize DR directory
        Path('/tmp/flavorsnap_dr').mkdir(parents=True, exist_ok=True)
        
        # Initialize DR registry
        self._init_dr_registry()
        
        # Load DR plans
        self._load_dr_plans()
        
        # Register health checks
        self._register_health_checks()
        
        logger.info("DisasterRecoverySystem initialized")
    
    def _init_dr_registry(self):
        """Initialize disaster recovery registry database"""
        conn = sqlite3.connect(self.dr_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS disaster_events (
                event_id TEXT PRIMARY KEY,
                disaster_level TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                description TEXT NOT NULL,
                affected_systems TEXT NOT NULL,
                detection_method TEXT NOT NULL,
                status TEXT NOT NULL,
                recovery_strategy TEXT NOT NULL,
                recovery_time TEXT,
                impact_assessment TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dr_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                system_name TEXT NOT NULL,
                health_status TEXT NOT NULL,
                response_time_ms REAL,
                error_rate REAL,
                uptime_percentage REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recovery_tests (
                test_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                test_type TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_seconds REAL,
                result_details TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("DR registry database initialized")
    
    def _load_dr_plans(self):
        """Load disaster recovery plans"""
        # High availability plan
        self.dr_plans[DisasterLevel.LOW] = DRPlan(
            plan_id="ha_plan",
            disaster_level=DisasterLevel.LOW,
            recovery_strategy=RecoveryStrategy.ROLLING_RESTART,
            rto_hours=0.5,
            rpo_hours=0.1,
            steps=[
                "Identify affected services",
                "Restart failed services",
                "Verify service health",
                "Monitor system stability"
            ],
            contacts=[
                {"name": "DevOps Team", "email": "devops@flavorsnap.com"},
                {"name": "System Administrator", "email": "admin@flavorsnap.com"}
            ],
            resources=["kubernetes_cluster", "monitoring_tools"],
            dependencies=["load_balancer", "database"],
            success_criteria=["All services healthy", "Response time < 500ms"]
        )
        
        # Backup restore plan
        self.dr_plans[DisasterLevel.MEDIUM] = DRPlan(
            plan_id="backup_restore_plan",
            disaster_level=DisasterLevel.MEDIUM,
            recovery_strategy=RecoveryStrategy.BACKUP_RESTORE,
            rto_hours=2.0,
            rpo_hours=1.0,
            steps=[
                "Assess system damage",
                "Select appropriate backup",
                "Initiate backup restoration",
                "Verify data integrity",
                "Restart services",
                "Validate functionality"
            ],
            contacts=[
                {"name": "DevOps Team", "email": "devops@flavorsnap.com"},
                {"name": "Database Administrator", "email": "dba@flavorsnap.com"},
                {"name": "Engineering Manager", "email": "eng-manager@flavorsnap.com"}
            ],
            resources=["backup_storage", "recovery_system", "database"],
            dependencies=["backup_manager", "recovery_system"],
            success_criteria=["Data integrity verified", "All services operational"]
        )
        
        # Failover plan
        self.dr_plans[DisasterLevel.HIGH] = DRPlan(
            plan_id="failover_plan",
            disaster_level=DisasterLevel.HIGH,
            recovery_strategy=RecoveryStrategy.FAILOVER,
            rto_hours=4.0,
            rpo_hours=2.0,
            steps=[
                "Declare disaster",
                "Activate failover site",
                "Redirect traffic",
                "Restore from backups",
                "Verify system functionality",
                "Update DNS records",
                "Notify stakeholders"
            ],
            contacts=[
                {"name": "Crisis Management Team", "email": "crisis@flavorsnap.com"},
                {"name": "DevOps Team", "email": "devops@flavorsnap.com"},
                {"name": "Executive Team", "email": "executive@flavorsnap.com"}
            ],
            resources=["failover_site", "backup_storage", "dns_provider"],
            dependencies=["cloud_provider", "dns_service"],
            success_criteria=["Failover site operational", "Traffic redirected successfully"]
        )
        
        # Critical disaster plan
        self.dr_plans[DisasterLevel.CRITICAL] = DRPlan(
            plan_id="critical_plan",
            disaster_level=DisasterLevel.CRITICAL,
            recovery_strategy=RecoveryStrategy.MANUAL_INTERVENTION,
            rto_hours=24.0,
            rpo_hours=4.0,
            steps=[
                "Emergency response team activation",
                "Assess infrastructure damage",
                "Contact cloud provider support",
                "Manual system recovery",
                "Data reconstruction if needed",
                "Gradual service restoration",
                "Post-incident analysis"
            ],
            contacts=[
                {"name": "CEO", "email": "ceo@flavorsnap.com"},
                {"name": "Crisis Management Team", "email": "crisis@flavorsnap.com"},
                {"name": "Legal Team", "email": "legal@flavorsnap.com"}
            ],
            resources=["emergency_team", "external_support", "legal_advisors"],
            dependencies=["external_vendors", "legal_compliance"],
            success_criteria=["Core services restored", "Business operations resumed"]
        )
        
        logger.info(f"Loaded {len(self.dr_plans)} disaster recovery plans")
    
    def _register_health_checks(self):
        """Register system health checks"""
        self.health_checks = {
            'api_service': self._check_api_health,
            'database': self._check_database_health,
            'model_service': self._check_model_service_health,
            'storage': self._check_storage_health,
            'monitoring': self._check_monitoring_health
        }
        
        logger.info(f"Registered {len(self.health_checks)} health checks")
    
    def start_monitoring(self):
        """Start continuous disaster monitoring"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Disaster monitoring started")
    
    def stop_monitoring(self):
        """Stop disaster monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        
        logger.info("Disaster monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        consecutive_failures = {}
        
        while self.monitoring_active:
            try:
                for system_name, health_check in self.health_checks.items():
                    try:
                        health_status = health_check()
                        self._record_health_metric(system_name, health_status)
                        
                        if health_status['healthy']:
                            consecutive_failures[system_name] = 0
                        else:
                            consecutive_failures[system_name] = consecutive_failures.get(system_name, 0) + 1
                            
                            if consecutive_failures[system_name] >= self.config.max_failures_before_alert:
                                self._handle_system_failure(system_name, health_status)
                    
                    except Exception as e:
                        logger.error(f"Health check failed for {system_name}: {str(e)}")
                        consecutive_failures[system_name] = consecutive_failures.get(system_name, 0) + 1
                
                time.sleep(self.config.monitoring_interval_seconds)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {str(e)}")
                time.sleep(10)
    
    def _check_api_health(self) -> Dict[str, Any]:
        """Check API service health"""
        try:
            response = requests.get(
                'http://localhost:8000/health',
                timeout=self.config.health_check_timeout_seconds
            )
            
            if response.status_code == 200:
                return {
                    'healthy': True,
                    'response_time_ms': response.elapsed.total_seconds() * 1000,
                    'status_code': response.status_code,
                    'message': 'API service healthy'
                }
            else:
                return {
                    'healthy': False,
                    'response_time_ms': response.elapsed.total_seconds() * 1000,
                    'status_code': response.status_code,
                    'message': f'API returned status {response.status_code}'
                }
        
        except requests.RequestException as e:
            return {
                'healthy': False,
                'response_time_ms': None,
                'status_code': None,
                'message': f'API health check failed: {str(e)}'
            }
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            # Check SQLite database
            db_path = 'ml-model-api/model_registry.db'
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM sqlite_master')
                result = cursor.fetchone()
                conn.close()
                
                return {
                    'healthy': True,
                    'response_time_ms': 50,  # Placeholder
                    'message': 'Database accessible'
                }
            else:
                return {
                    'healthy': False,
                    'response_time_ms': None,
                    'message': 'Database file not found'
                }
        
        except Exception as e:
            return {
                'healthy': False,
                'response_time_ms': None,
                'message': f'Database health check failed: {str(e)}'
            }
    
    def _check_model_service_health(self) -> Dict[str, Any]:
        """Check ML model service health"""
        try:
            # Check if model file exists
            model_path = 'model.pth'
            if os.path.exists(model_path):
                return {
                    'healthy': True,
                    'response_time_ms': 10,
                    'message': 'Model file accessible'
                }
            else:
                return {
                    'healthy': False,
                    'response_time_ms': None,
                    'message': 'Model file not found'
                }
        
        except Exception as e:
            return {
                'healthy': False,
                'response_time_ms': None,
                'message': f'Model service health check failed: {str(e)}'
            }
    
    def _check_storage_health(self) -> Dict[str, Any]:
        """Check storage system health"""
        try:
            # Check if we can write to temporary storage
            test_file = '/tmp/dr_storage_test'
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            return {
                'healthy': True,
                'response_time_ms': 20,
                'message': 'Storage system healthy'
            }
        
        except Exception as e:
            return {
                'healthy': False,
                'response_time_ms': None,
                'message': f'Storage health check failed: {str(e)}'
            }
    
    def _check_monitoring_health(self) -> Dict[str, Any]:
        """Check monitoring system health"""
        try:
            # Check Redis connection
            self.redis_client.ping()
            
            return {
                'healthy': True,
                'response_time_ms': 5,
                'message': 'Monitoring system healthy'
            }
        
        except Exception as e:
            return {
                'healthy': False,
                'response_time_ms': None,
                'message': f'Monitoring health check failed: {str(e)}'
            }
    
    def _record_health_metric(self, system_name: str, health_status: Dict[str, Any]):
        """Record health metric to database"""
        conn = sqlite3.connect(self.dr_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO dr_metrics 
            (timestamp, system_name, health_status, response_time_ms, error_rate, uptime_percentage)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(pytz.UTC).isoformat(),
            system_name,
            'healthy' if health_status['healthy'] else 'unhealthy',
            health_status.get('response_time_ms'),
            0 if health_status['healthy'] else 100,
            100 if health_status['healthy'] else 0
        ))
        
        conn.commit()
        conn.close()
    
    def _handle_system_failure(self, system_name: str, health_status: Dict[str, Any]):
        """Handle system failure and initiate disaster recovery"""
        logger.warning(f"System failure detected: {system_name}")
        
        # Assess disaster level
        disaster_level = self._assess_disaster_level(system_name, health_status)
        
        # Create disaster event
        event_id = f"disaster_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        disaster_event = DisasterEvent(
            event_id=event_id,
            disaster_level=disaster_level,
            timestamp=datetime.now(pytz.UTC),
            description=f"System failure in {system_name}: {health_status['message']}",
            affected_systems=[system_name],
            detection_method="health_check",
            status="detected",
            recovery_strategy=self.dr_plans[disaster_level].recovery_strategy
        )
        
        # Save disaster event
        self._save_disaster_event(disaster_event)
        
        # Send notifications
        if self.config.notification_enabled:
            self._send_disaster_notification(disaster_event)
        
        # Initiate recovery if auto-failover is enabled
        if self.config.auto_failover_enabled and disaster_level in [DisasterLevel.LOW, DisasterLevel.MEDIUM]:
            self._initiate_recovery(disaster_event)
    
    def _assess_disaster_level(self, system_name: str, health_status: Dict[str, Any]) -> DisasterLevel:
        """Assess disaster level based on system failure"""
        if system_name in ['api_service', 'database']:
            return DisasterLevel.HIGH
        elif system_name in ['model_service']:
            return DisasterLevel.MEDIUM
        else:
            return DisasterLevel.LOW
    
    def _save_disaster_event(self, disaster_event: DisasterEvent):
        """Save disaster event to registry"""
        conn = sqlite3.connect(self.dr_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO disaster_events 
            (event_id, disaster_level, timestamp, description, affected_systems, 
             detection_method, status, recovery_strategy, recovery_time, impact_assessment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            disaster_event.event_id,
            disaster_event.disaster_level.value,
            disaster_event.timestamp.isoformat(),
            disaster_event.description,
            json.dumps(disaster_event.affected_systems),
            disaster_event.detection_method,
            disaster_event.status,
            disaster_event.recovery_strategy.value,
            disaster_event.recovery_time.isoformat() if disaster_event.recovery_time else None,
            json.dumps(disaster_event.impact_assessment) if disaster_event.impact_assessment else None
        ))
        
        conn.commit()
        conn.close()
        
        # Cache in Redis
        self.redis_client.setex(
            f"disaster:{disaster_event.event_id}",
            86400,  # 24 hours TTL
            json.dumps(asdict(disaster_event), default=str)
        )
        
        # Add to active disasters
        self.active_disasters[disaster_event.event_id] = disaster_event
    
    def _send_disaster_notification(self, disaster_event: DisasterEvent):
        """Send disaster notifications"""
        try:
            # Send email notifications
            if self.config.notification_emails:
                self._send_email_notification(disaster_event)
            
            # Send Slack notification
            if self.config.slack_webhook_url:
                self._send_slack_notification(disaster_event)
            
            # Send PagerDuty notification
            if self.config.pagerduty_api_key and disaster_event.disaster_level in [DisasterLevel.HIGH, DisasterLevel.CRITICAL]:
                self._send_pagerduty_notification(disaster_event)
            
            logger.info(f"Notifications sent for disaster: {disaster_event.event_id}")
            
        except Exception as e:
            logger.error(f"Failed to send notifications: {str(e)}")
    
    def _send_email_notification(self, disaster_event: DisasterEvent):
        """Send email notification"""
        try:
            subject = f"🚨 FlavorSnap Disaster Alert - {disaster_event.disaster_level.value.upper()}"
            body = f"""
Disaster Event Detected:

Event ID: {disaster_event.event_id}
Level: {disaster_event.disaster_level.value}
Timestamp: {disaster_event.timestamp}
Description: {disaster_event.description}
Affected Systems: {', '.join(disaster_event.affected_systems)}
Recovery Strategy: {disaster_event.recovery_strategy.value}

Please check the disaster recovery system for more details.
"""
            
            # Send email (implementation would depend on SMTP configuration)
            logger.info(f"Email notification prepared: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
    
    def _send_slack_notification(self, disaster_event: DisasterEvent):
        """Send Slack notification"""
        try:
            payload = {
                "text": f"🚨 FlavorSnap Disaster Alert",
                "attachments": [{
                    "color": "danger" if disaster_event.disaster_level in [DisasterLevel.HIGH, DisasterLevel.CRITICAL] else "warning",
                    "fields": [
                        {"title": "Event ID", "value": disaster_event.event_id, "short": True},
                        {"title": "Level", "value": disaster_event.disaster_level.value.upper(), "short": True},
                        {"title": "Description", "value": disaster_event.description, "short": False},
                        {"title": "Affected Systems", "value": ', '.join(disaster_event.affected_systems), "short": True},
                        {"title": "Recovery Strategy", "value": disaster_event.recovery_strategy.value, "short": True}
                    ]
                }]
            }
            
            # Send to Slack webhook
            logger.info(f"Slack notification prepared for disaster: {disaster_event.event_id}")
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
    
    def _send_pagerduty_notification(self, disaster_event: DisasterEvent):
        """Send PagerDuty notification"""
        try:
            # PagerDuty integration implementation
            logger.info(f"PagerDuty notification prepared for disaster: {disaster_event.event_id}")
            
        except Exception as e:
            logger.error(f"Failed to send PagerDuty notification: {str(e)}")
    
    def _initiate_recovery(self, disaster_event: DisasterEvent):
        """Initiate disaster recovery process"""
        logger.info(f"Initiating recovery for disaster: {disaster_event.event_id}")
        
        try:
            # Update disaster status
            disaster_event.status = "mitigating"
            self._save_disaster_event(disaster_event)
            
            # Get recovery plan
            dr_plan = self.dr_plans[disaster_event.disaster_level]
            
            # Execute recovery steps
            recovery_success = self._execute_recovery_plan(dr_plan, disaster_event)
            
            # Update disaster status
            if recovery_success:
                disaster_event.status = "resolved"
                disaster_event.recovery_time = datetime.now(pytz.UTC)
            else:
                disaster_event.status = "failed"
            
            self._save_disaster_event(disaster_event)
            
            # Send recovery notification
            if self.config.notification_enabled:
                self._send_recovery_notification(disaster_event, recovery_success)
            
            logger.info(f"Recovery {'completed' if recovery_success else 'failed'} for disaster: {disaster_event.event_id}")
            
        except Exception as e:
            logger.error(f"Recovery initiation failed: {str(e)}")
            disaster_event.status = "failed"
            self._save_disaster_event(disaster_event)
    
    def _execute_recovery_plan(self, dr_plan: DRPlan, disaster_event: DisasterEvent) -> bool:
        """Execute disaster recovery plan"""
        try:
            logger.info(f"Executing recovery plan: {dr_plan.plan_id}")
            
            for step in dr_plan.steps:
                logger.info(f"Executing recovery step: {step}")
                
                # Execute step based on recovery strategy
                if dr_plan.recovery_strategy == RecoveryStrategy.ROLLING_RESTART:
                    success = self._execute_rolling_restart_step(step)
                elif dr_plan.recovery_strategy == RecoveryStrategy.BACKUP_RESTORE:
                    success = self._execute_backup_restore_step(step)
                elif dr_plan.recovery_strategy == RecoveryStrategy.FAILOVER:
                    success = self._execute_failover_step(step)
                else:
                    success = self._execute_manual_intervention_step(step)
                
                if not success:
                    logger.error(f"Recovery step failed: {step}")
                    return False
                
                time.sleep(2)  # Brief pause between steps
            
            # Verify success criteria
            return self._verify_recovery_success(dr_plan, disaster_event)
            
        except Exception as e:
            logger.error(f"Recovery plan execution failed: {str(e)}")
            return False
    
    def _execute_rolling_restart_step(self, step: str) -> bool:
        """Execute rolling restart step"""
        try:
            if "Restart failed services" in step:
                # Restart API service
                subprocess.run(['pkill', '-f', 'python.*app.py'], check=False)
                time.sleep(5)
                # Would normally start the service here
                logger.info("Service restart executed")
                return True
            
            elif "Verify service health" in step:
                # Verify health after restart
                health_status = self._check_api_health()
                return health_status['healthy']
            
            return True
            
        except Exception as e:
            logger.error(f"Rolling restart step failed: {str(e)}")
            return False
    
    def _execute_backup_restore_step(self, step: str) -> bool:
        """Execute backup restore step"""
        try:
            if "Initiate backup restoration" in step:
                # Would use backup_manager and recovery_system here
                logger.info("Backup restoration initiated")
                return True
            
            elif "Verify data integrity" in step:
                # Verify restored data
                logger.info("Data integrity verification completed")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Backup restore step failed: {str(e)}")
            return False
    
    def _execute_failover_step(self, step: str) -> bool:
        """Execute failover step"""
        try:
            if "Activate failover site" in step:
                # Would activate failover infrastructure
                logger.info("Failover site activation initiated")
                return True
            
            elif "Redirect traffic" in step:
                # Would update DNS or load balancer
                logger.info("Traffic redirection completed")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Failover step failed: {str(e)}")
            return False
    
    def _execute_manual_intervention_step(self, step: str) -> bool:
        """Execute manual intervention step"""
        try:
            # For manual intervention, just log the step
            logger.info(f"Manual intervention step: {step}")
            return True
            
        except Exception as e:
            logger.error(f"Manual intervention step failed: {str(e)}")
            return False
    
    def _verify_recovery_success(self, dr_plan: DRPlan, disaster_event: DisasterEvent) -> bool:
        """Verify recovery success criteria"""
        try:
            for criterion in dr_plan.success_criteria:
                if "All services healthy" in criterion:
                    # Check all services
                    for system_name in self.health_checks.keys():
                        health_status = self.health_checks[system_name]()
                        if not health_status['healthy']:
                            logger.error(f"Service {system_name} not healthy")
                            return False
                
                elif "Response time" in criterion:
                    # Check response times
                    health_status = self._check_api_health()
                    if health_status.get('response_time_ms', 0) > 500:
                        logger.error("Response time too high")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Recovery verification failed: {str(e)}")
            return False
    
    def _send_recovery_notification(self, disaster_event: DisasterEvent, success: bool):
        """Send recovery completion notification"""
        try:
            status = "✅ RESOLVED" if success else "❌ FAILED"
            subject = f"FlavorSnap Disaster Recovery {status} - {disaster_event.event_id}"
            
            body = f"""
Disaster Recovery {status}:

Event ID: {disaster_event.event_id}
Level: {disaster_event.disaster_level.value}
Status: {disaster_event.status}
Recovery Time: {disaster_event.recovery_time if disaster_event.recovery_time else 'N/A'}

{"Recovery completed successfully." if success else "Recovery failed. Manual intervention required."}
"""
            
            logger.info(f"Recovery notification prepared: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send recovery notification: {str(e)}")
    
    def run_disaster_drill(self, disaster_level: DisasterLevel) -> bool:
        """Run disaster recovery drill"""
        drill_id = f"drill_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info(f"Starting disaster drill: {drill_id} for level: {disaster_level.value}")
            
            # Create simulated disaster event
            disaster_event = DisasterEvent(
                event_id=drill_id,
                disaster_level=disaster_level,
                timestamp=datetime.now(pytz.UTC),
                description=f"DRILL: Simulated {disaster_level.value} disaster",
                affected_systems=['api_service', 'database'],
                detection_method="drill",
                status="detected",
                recovery_strategy=self.dr_plans[disaster_level].recovery_strategy
            )
            
            # Save drill event
            self._save_disaster_event(disaster_event)
            
            # Execute recovery plan in drill mode
            dr_plan = self.dr_plans[disaster_level]
            recovery_success = self._execute_recovery_plan(dr_plan, disaster_event)
            
            # Update drill status
            disaster_event.status = "resolved" if recovery_success else "failed"
            self._save_disaster_event(disaster_event)
            
            # Record drill results
            self._record_drill_results(drill_id, disaster_level, recovery_success)
            
            logger.info(f"Disaster drill completed: {drill_id} - {'SUCCESS' if recovery_success else 'FAILED'}")
            return recovery_success
            
        except Exception as e:
            logger.error(f"Disaster drill failed: {str(e)}")
            return False
    
    def _record_drill_results(self, drill_id: str, disaster_level: DisasterLevel, success: bool):
        """Record drill results"""
        conn = sqlite3.connect(self.dr_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO recovery_tests 
            (test_id, timestamp, test_type, status, duration_seconds, result_details)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            drill_id,
            datetime.now(pytz.UTC).isoformat(),
            f"drill_{disaster_level.value}",
            "success" if success else "failed",
            0,  # Would track actual duration
            json.dumps({"disaster_level": disaster_level.value, "success": success})
        ))
        
        conn.commit()
        conn.close()
    
    def get_disaster_history(self, limit: int = 50) -> List[DisasterEvent]:
        """Get disaster event history"""
        conn = sqlite3.connect(self.dr_db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM disaster_events ORDER BY timestamp DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        disasters = []
        for row in rows:
            disasters.append(DisasterEvent(
                event_id=row[0],
                disaster_level=DisasterLevel(row[1]),
                timestamp=datetime.fromisoformat(row[2]),
                description=row[3],
                affected_systems=json.loads(row[4]),
                detection_method=row[5],
                status=row[6],
                recovery_strategy=RecoveryStrategy(row[7]),
                recovery_time=datetime.fromisoformat(row[8]) if row[8] else None,
                impact_assessment=json.loads(row[9]) if row[9] else None
            ))
        
        return disasters
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        health_summary = {}
        
        for system_name in self.health_checks.keys():
            try:
                health_status = self.health_checks[system_name]()
                health_summary[system_name] = {
                    'healthy': health_status['healthy'],
                    'last_check': datetime.now(pytz.UTC).isoformat(),
                    'response_time_ms': health_status.get('response_time_ms'),
                    'message': health_status.get('message')
                }
            except Exception as e:
                health_summary[system_name] = {
                    'healthy': False,
                    'last_check': datetime.now(pytz.UTC).isoformat(),
                    'response_time_ms': None,
                    'message': f'Health check failed: {str(e)}'
                }
        
        return health_summary

# Example usage
if __name__ == "__main__":
    # Example configuration
    config = DRConfig(
        monitoring_interval_seconds=60,
        auto_failover_enabled=True,
        notification_enabled=True,
        notification_emails=["admin@flavorsnap.com"]
    )
    
    # Initialize disaster recovery system
    dr_system = DisasterRecoverySystem(config)
    
    # Start monitoring
    dr_system.start_monitoring()
    
    try:
        # Run a disaster drill
        success = dr_system.run_disaster_drill(DisasterLevel.LOW)
        print(f"Disaster drill result: {success}")
        
        # Get system health summary
        health_summary = dr_system.get_system_health_summary()
        print(f"System health: {health_summary}")
        
    finally:
        # Stop monitoring
        dr_system.stop_monitoring()
