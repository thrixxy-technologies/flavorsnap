"""
Advanced Compliance Checker for FlavorSnap API
Implements comprehensive compliance checking for GDPR, SOX, HIPAA, PCI DSS, and other frameworks
"""
import os
import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import re
from pathlib import Path
import subprocess
from audit_logger import audit_logger, AuditEventType, AuditSeverity


class ComplianceFramework(Enum):
    """Compliance frameworks"""
    GDPR = "gdpr"
    SOX = "sox"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    NIST = "nist"
    CCPA = "ccpa"


class ComplianceStatus(Enum):
    """Compliance status levels"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    """Risk levels for compliance violations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ComplianceRequirement:
    """Compliance requirement definition"""
    id: str
    framework: ComplianceFramework
    category: str
    title: str
    description: str
    mandatory: bool
    risk_level: RiskLevel
    check_function: str
    remediation_steps: List[str]
    references: List[str]


@dataclass
class ComplianceViolation:
    """Compliance violation data structure"""
    requirement_id: str
    framework: ComplianceFramework
    status: ComplianceStatus
    risk_level: RiskLevel
    description: str
    evidence: Dict[str, Any]
    affected_resources: List[str]
    discovered_at: datetime
    remediation_steps: List[str]
    false_positive: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class ComplianceReport:
    """Compliance report data structure"""
    framework: ComplianceFramework
    overall_status: ComplianceStatus
    total_requirements: int
    compliant_requirements: int
    violations: List[ComplianceViolation]
    risk_assessment: Dict[RiskLevel, int]
    compliance_score: float
    generated_at: datetime
    next_review_date: datetime


class ComplianceConfig:
    """Compliance checker configuration"""
    
    # Compliance requirements definitions
    REQUIREMENTS_FILE = "config/compliance_requirements.json"
    
    # Check intervals (in days)
    CHECK_INTERVALS = {
        ComplianceFramework.GDPR: 30,      # Monthly
        ComplianceFramework.SOX: 90,        # Quarterly
        ComplianceFramework.HIPAA: 30,      # Monthly
        ComplianceFramework.PCI_DSS: 30,    # Monthly
        ComplianceFramework.ISO_27001: 180, # Semi-annually
        ComplianceFramework.NIST: 90,       # Quarterly
        ComplianceFramework.CCPA: 30       # Monthly
    }
    
    # Risk scoring
    RISK_SCORES = {
        RiskLevel.LOW: 1,
        RiskLevel.MEDIUM: 5,
        RiskLevel.HIGH: 15,
        RiskLevel.CRITICAL: 50
    }
    
    # Alert thresholds
    ALERT_THRESHOLDS = {
        'critical_violations': 1,
        'high_violations': 3,
        'compliance_score_below': 80.0
    }


class GDPRComplianceChecker:
    """GDPR compliance checker"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def check_data_processing_records(self) -> Tuple[bool, List[str]]:
        """Check for data processing records (Article 30)"""
        violations = []
        
        # Check if data processing registry exists
        registry_file = Path("data/gdpr/data_processing_registry.json")
        if not registry_file.exists():
            violations.append("Data processing registry not found")
            return False, violations
        
        try:
            with open(registry_file, 'r') as f:
                registry = json.load(f)
            
            # Check required fields
            required_fields = ['controller', 'purposes', 'recipients', 'retention_period']
            for entry in registry.get('entries', []):
                for field in required_fields:
                    if field not in entry:
                        violations.append(f"Missing required field '{field}' in data processing entry")
        except Exception as e:
            violations.append(f"Error reading data processing registry: {str(e)}")
        
        return len(violations) == 0, violations
    
    def check_consent_management(self) -> Tuple[bool, List[str]]:
        """Check consent management (Article 7)"""
        violations = []
        
        # Check consent records
        consent_file = Path("data/gdpr/consent_records.json")
        if not consent_file.exists():
            violations.append("Consent records not found")
            return False, violations
        
        try:
            with open(consent_file, 'r') as f:
                consent_data = json.load(f)
            
            # Check consent validity
            for consent in consent_data.get('consents', []):
                if 'granted_at' not in consent:
                    violations.append("Consent missing granted timestamp")
                
                if 'purpose' not in consent:
                    violations.append("Consent missing purpose description")
                
                if 'withdrawn' in consent and consent['withdrawn']:
                    if 'withdrawn_at' not in consent:
                        violations.append("Withdrawn consent missing withdrawal timestamp")
        except Exception as e:
            violations.append(f"Error reading consent records: {str(e)}")
        
        return len(violations) == 0, violations
    
    def check_data_breach_procedures(self) -> Tuple[bool, List[str]]:
        """Check data breach notification procedures (Article 33)"""
        violations = []
        
        # Check breach response plan
        breach_plan_file = Path("docs/gdpr/breach_response_plan.md")
        if not breach_plan_file.exists():
            violations.append("Data breach response plan not found")
        
        # Check notification templates
        notification_template = Path("templates/gdpr/breach_notification.md")
        if not notification_template.exists():
            violations.append("Breach notification template not found")
        
        # Check 72-hour notification capability
        # This would typically involve checking notification systems
        # For now, just check if notification service is configured
        if not os.getenv('GDPR_NOTIFICATION_EMAIL'):
            violations.append("GDPR notification email not configured")
        
        return len(violations) == 0, violations
    
    def check_data_subject_rights(self) -> Tuple[bool, List[str]]:
        """Check data subject rights implementation (Articles 15-22)"""
        violations = []
        
        # Check if DSAR (Data Subject Access Request) system exists
        dsar_endpoints = [
            '/api/gdpr/data-request',
            '/api/gdpr/data-export',
            '/api/gdpr/data-deletion',
            '/api/gdpr/data-portability'
        ]
        
        # In a real implementation, you would check if these endpoints exist
        # For now, we'll check if the DSAR handler file exists
        dsar_handler = Path("ml-model-api/gdpr_handlers.py")
        if not dsar_handler.exists():
            violations.append("Data Subject Access Request handler not implemented")
        
        # Check response time capabilities (should be within 30 days)
        # This would involve checking the system's ability to respond in time
        # For now, assume it's implemented if the handler exists
        
        return len(violations) == 0, violations


class SOXComplianceChecker:
    """SOX compliance checker"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def check_financial_reporting_controls(self) -> Tuple[bool, List[str]]:
        """Check financial reporting controls (Section 302/404)"""
        violations = []
        
        # Check audit trail for financial data
        audit_trail_file = Path("data/sox/financial_audit_trail.json")
        if not audit_trail_file.exists():
            violations.append("Financial audit trail not found")
        
        # Check segregation of duties
        # This would involve checking user roles and permissions
        # For now, check if role-based access control exists
        rbac_config = Path("config/rbac.json")
        if not rbac_config.exists():
            violations.append("Role-based access control not configured")
        
        # Check change management procedures
        change_mgmt_file = Path("docs/sox/change_management.md")
        if not change_mgmt_file.exists():
            violations.append("Change management procedures not documented")
        
        return len(violations) == 0, violations
    
    def check_internal_controls(self) -> Tuple[bool, List[str]]:
        """Check internal controls documentation"""
        violations = []
        
        # Check control matrix
        control_matrix = Path("docs/sox/control_matrix.xlsx")
        if not control_matrix.exists():
            violations.append("SOX control matrix not found")
        
        # Check control testing evidence
        control_testing = Path("data/sox/control_testing.json")
        if not control_testing.exists():
            violations.append("Control testing evidence not found")
        
        return len(violations) == 0, violations


class HIPAAComplianceChecker:
    """HIPAA compliance checker"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def check_phi_protection(self) -> Tuple[bool, List[str]]:
        """Check Protected Health Information (PHI) protection"""
        violations = []
        
        # Check encryption at rest
        encryption_config = Path("config/encryption.json")
        if not encryption_config.exists():
            violations.append("Encryption configuration not found")
        
        # Check access controls
        access_logs = Path("data/hipaa/access_logs.json")
        if not access_logs.exists():
            violations.append("PHI access logs not maintained")
        
        # Check minimum necessary policy
        min_necessary_policy = Path("docs/hipaa/minimum_necessary.md")
        if not min_necessary_policy.exists():
            violations.append("Minimum necessary policy not documented")
        
        return len(violations) == 0, violations
    
    def check_business_associate_agreements(self) -> Tuple[bool, List[str]]:
        """Check Business Associate Agreements (BAAs)"""
        violations = []
        
        # Check BAA templates
        baa_template = Path("templates/hipaa/business_associate_agreement.md")
        if not baa_template.exists():
            violations.append("Business Associate Agreement template not found")
        
        # Check signed BAAs
        signed_baas = Path("data/hipaa/signed_baas.json")
        if not signed_baas.exists():
            violations.append("Signed Business Associate Agreements not tracked")
        
        return len(violations) == 0, violations


class PCIDSSComplianceChecker:
    """PCI DSS compliance checker"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def check_cardholder_data_protection(self) -> Tuple[bool, List[str]]:
        """Check cardholder data protection (Requirements 3-4)"""
        violations = []
        
        # Check if card data is stored (should not be)
        card_data_patterns = [
            r'\b4[0-9]{12}(?:[0-9]{3})?\b',  # Visa
            r'\b5[1-5][0-9]{14}\b',          # MasterCard
            r'\b3[47][0-9]{13}\b',            # American Express
            r'\b3[0-9]{13}\b',                # Diners Club
            r'\b6(?:011|5[0-9]{2})[0-9]{12}\b'  # Discover
        ]
        
        # Scan code for potential card data storage
        code_files = list(Path("ml-model-api").glob("*.py"))
        for code_file in code_files:
            try:
                content = code_file.read_text()
                for pattern in card_data_patterns:
                    if re.search(pattern, content):
                        violations.append(f"Potential card data pattern found in {code_file.name}")
                        break
            except Exception:
                continue
        
        # Check encryption of transmission
        tls_config = Path("config/tls.json")
        if not tls_config.exists():
            violations.append("TLS configuration not found")
        
        return len(violations) == 0, violations
    
    def check_network_security(self) -> Tuple[bool, List[str]]:
        """Check network security (Requirements 1-2)"""
        violations = []
        
        # Check firewall configuration
        firewall_rules = Path("config/firewall.json")
        if not firewall_rules.exists():
            violations.append("Firewall rules not documented")
        
        # Check vulnerability scanning
        scan_results = Path("data/pci/vulnerability_scans.json")
        if not scan_results.exists():
            violations.append("Vulnerability scan results not found")
        
        return len(violations) == 0, violations


class ComplianceChecker:
    """Main compliance checker class"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.framework_checkers = {
            ComplianceFramework.GDPR: GDPRComplianceChecker(),
            ComplianceFramework.SOX: SOXComplianceChecker(),
            ComplianceFramework.HIPAA: HIPAAComplianceChecker(),
            ComplianceFramework.PCI_DSS: PCIDSSComplianceChecker()
        }
        self.requirements: Dict[str, ComplianceRequirement] = {}
        self.violations: List[ComplianceViolation] = []
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize compliance checker with Flask app"""
        self.app = app
        self._load_requirements()
        self.logger.info("Compliance checker initialized")
    
    def _load_requirements(self):
        """Load compliance requirements from configuration"""
        requirements_file = Path(ComplianceConfig.REQUIREMENTS_FILE)
        
        if requirements_file.exists():
            try:
                with open(requirements_file, 'r') as f:
                    requirements_data = json.load(f)
                
                for req_data in requirements_data.get('requirements', []):
                    requirement = ComplianceRequirement(
                        id=req_data['id'],
                        framework=ComplianceFramework(req_data['framework']),
                        category=req_data['category'],
                        title=req_data['title'],
                        description=req_data['description'],
                        mandatory=req_data['mandatory'],
                        risk_level=RiskLevel(req_data['risk_level']),
                        check_function=req_data['check_function'],
                        remediation_steps=req_data['remediation_steps'],
                        references=req_data['references']
                    )
                    self.requirements[requirement.id] = requirement
                
                self.logger.info(f"Loaded {len(self.requirements)} compliance requirements")
            except Exception as e:
                self.logger.error(f"Failed to load requirements: {str(e)}")
        else:
            self.logger.warning(f"Requirements file not found at {requirements_file}")
            self._create_default_requirements()
    
    def _create_default_requirements(self):
        """Create default compliance requirements"""
        default_requirements = [
            # GDPR Requirements
            ComplianceRequirement(
                id="GDPR_ART30",
                framework=ComplianceFramework.GDPR,
                category="Data Processing Records",
                title="Article 30: Records of processing activities",
                description="Maintain records of data processing activities",
                mandatory=True,
                risk_level=RiskLevel.HIGH,
                check_function="check_data_processing_records",
                remediation_steps=[
                    "Create data processing registry",
                    "Document all data processing activities",
                    "Include controller, purposes, recipients, and retention periods"
                ],
                references=["https://gdpr.eu/article-30-records-of-processing-activities/"]
            ),
            ComplianceRequirement(
                id="GDPR_ART7",
                framework=ComplianceFramework.GDPR,
                category="Consent Management",
                title="Article 7: Conditions for consent",
                description="Obtain and manage valid consent for data processing",
                mandatory=True,
                risk_level=RiskLevel.HIGH,
                check_function="check_consent_management",
                remediation_steps=[
                    "Implement consent management system",
                    "Record consent timestamps and purposes",
                    "Allow easy consent withdrawal"
                ],
                references=["https://gdpr.eu/article-7-conditions-for-consent/"]
            ),
            ComplianceRequirement(
                id="GDPR_ART33",
                framework=ComplianceFramework.GDPR,
                category="Data Breach Notification",
                title="Article 33: Notification of personal data breach",
                description="Implement data breach notification procedures",
                mandatory=True,
                risk_level=RiskLevel.CRITICAL,
                check_function="check_data_breach_procedures",
                remediation_steps=[
                    "Create breach response plan",
                    "Implement 72-hour notification system",
                    "Create notification templates"
                ],
                references=["https://gdpr.eu/article-33-notification-of-personal-data-breach/"]
            ),
            # SOX Requirements
            ComplianceRequirement(
                id="SOX_302",
                framework=ComplianceFramework.SOX,
                category="Financial Controls",
                title="Section 302: Corporate responsibility for financial reports",
                description="Implement financial reporting controls",
                mandatory=True,
                risk_level=RiskLevel.CRITICAL,
                check_function="check_financial_reporting_controls",
                remediation_steps=[
                    "Implement audit trail for financial data",
                    "Establish segregation of duties",
                    "Document change management procedures"
                ],
                references=["https://www.sec.gov/spotlight/sox.htm"]
            ),
            # HIPAA Requirements
            ComplianceRequirement(
                id="HIPAA_PHI",
                framework=ComplianceFramework.HIPAA,
                category="PHI Protection",
                title="PHI Protection Requirements",
                description="Protect Protected Health Information",
                mandatory=True,
                risk_level=RiskLevel.CRITICAL,
                check_function="check_phi_protection",
                remediation_steps=[
                    "Implement encryption for PHI",
                    "Maintain access logs",
                    "Document minimum necessary policy"
                ],
                references=["https://www.hhs.gov/hipaa/for-professionals/privacy/index.html"]
            ),
            # PCI DSS Requirements
            ComplianceRequirement(
                id="PCI_DSS_3",
                framework=ComplianceFramework.PCI_DSS,
                category="Cardholder Data",
                title="Requirement 3: Protect stored cardholder data",
                description="Protect stored cardholder data",
                mandatory=True,
                risk_level=RiskLevel.CRITICAL,
                check_function="check_cardholder_data_protection",
                remediation_steps=[
                    "Do not store sensitive card data",
                    "Implement strong cryptography",
                    "Implement secure transmission"
                ],
                references=["https://www.pcisecuritystandards.org/document/PCI-DSS-v4-0.pdf"]
            )
        ]
        
        for requirement in default_requirements:
            self.requirements[requirement.id] = requirement
        
        self.logger.info(f"Created {len(self.requirements)} default compliance requirements")
    
    def run_compliance_check(self, framework: ComplianceFramework = None) -> List[ComplianceReport]:
        """Run compliance check for specified framework(s)"""
        reports = []
        
        frameworks_to_check = [framework] if framework else list(ComplianceFramework)
        
        for fw in frameworks_to_check:
            if fw not in self.framework_checkers:
                self.logger.warning(f"No checker available for framework: {fw}")
                continue
            
            report = self._check_framework(fw)
            reports.append(report)
            
            # Log compliance check
            audit_logger.log_event(
                event_type=AuditEventType.COMPLIANCE_CHECK,
                severity=AuditSeverity.MEDIUM,
                user_id=None,
                ip_address="system",
                user_agent="compliance_checker",
                endpoint="/compliance/check",
                method="SYSTEM",
                status_code=200,
                request_id=None,
                client_id=None,
                resource=fw.value,
                action="compliance_check",
                details={
                    'framework': fw.value,
                    'overall_status': report.overall_status.value,
                    'compliance_score': report.compliance_score,
                    'violations_count': len(report.violations)
                },
                compliance_tags=[fw.value]
            )
        
        return reports
    
    def _check_framework(self, framework: ComplianceFramework) -> ComplianceReport:
        """Check compliance for a specific framework"""
        checker = self.framework_checkers[framework]
        
        # Get requirements for this framework
        framework_requirements = [
            req for req in self.requirements.values() 
            if req.framework == framework
        ]
        
        violations = []
        compliant_count = 0
        
        for requirement in framework_requirements:
            # Run the check
            check_function = getattr(checker, requirement.check_function, None)
            if not check_function:
                self.logger.warning(f"Check function {requirement.check_function} not found")
                continue
            
            try:
                is_compliant, violation_details = check_function()
                
                if is_compliant:
                    compliant_count += 1
                else:
                    # Create violation
                    violation = ComplianceViolation(
                        requirement_id=requirement.id,
                        framework=requirement.framework,
                        status=ComplianceStatus.NON_COMPLIANT,
                        risk_level=requirement.risk_level,
                        description=requirement.description,
                        evidence={'details': violation_details},
                        affected_resources=[],
                        discovered_at=datetime.now(),
                        remediation_steps=requirement.remediation_steps
                    )
                    violations.append(violation)
                    self.violations.append(violation)
                    
            except Exception as e:
                self.logger.error(f"Error checking requirement {requirement.id}: {str(e)}")
                
                # Create violation for check failure
                violation = ComplianceViolation(
                    requirement_id=requirement.id,
                    framework=requirement.framework,
                    status=ComplianceStatus.UNKNOWN,
                    risk_level=RiskLevel.MEDIUM,
                    description=f"Compliance check failed: {str(e)}",
                    evidence={'error': str(e)},
                    affected_resources=[],
                    discovered_at=datetime.now(),
                    remediation_steps=["Fix compliance check function", "Re-run compliance check"]
                )
                violations.append(violation)
        
        # Calculate overall status
        if not framework_requirements:
            overall_status = ComplianceStatus.NOT_APPLICABLE
        elif compliant_count == len(framework_requirements):
            overall_status = ComplianceStatus.COMPLIANT
        elif compliant_count >= len(framework_requirements) * 0.8:
            overall_status = ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            overall_status = ComplianceStatus.NON_COMPLIANT
        
        # Calculate risk assessment
        risk_assessment = {level: 0 for level in RiskLevel}
        for violation in violations:
            risk_assessment[violation.risk_level] += 1
        
        # Calculate compliance score
        total_risk_score = sum(
            ComplianceConfig.RISK_SCORES[risk_level] * count
            for risk_level, count in risk_assessment.items()
        )
        
        max_possible_score = len(framework_requirements) * ComplianceConfig.RISK_SCORES[RiskLevel.CRITICAL]
        compliance_score = max(0, 100 - (total_risk_score / max_possible_score * 100))
        
        # Determine next review date
        check_interval = ComplianceConfig.CHECK_INTERVALS.get(framework, 30)
        next_review_date = datetime.now() + timedelta(days=check_interval)
        
        return ComplianceReport(
            framework=framework,
            overall_status=overall_status,
            total_requirements=len(framework_requirements),
            compliant_requirements=compliant_count,
            violations=violations,
            risk_assessment=risk_assessment,
            compliance_score=compliance_score,
            generated_at=datetime.now(),
            next_review_date=next_review_date
        )
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get compliance summary across all frameworks"""
        all_reports = self.run_compliance_check()
        
        summary = {
            'overall_score': 0,
            'framework_status': {},
            'total_violations': 0,
            'critical_violations': 0,
            'high_risk_violations': 0,
            'next_reviews': {}
        }
        
        total_score = 0
        framework_count = 0
        
        for report in all_reports:
            framework_count += 1
            total_score += report.compliance_score
            
            summary['framework_status'][report.framework.value] = {
                'status': report.overall_status.value,
                'score': report.compliance_score,
                'violations': len(report.violations)
            }
            
            summary['total_violations'] += len(report.violations)
            summary['critical_violations'] += report.risk_assessment[RiskLevel.CRITICAL]
            summary['high_risk_violations'] += report.risk_assessment[RiskLevel.HIGH]
            summary['next_reviews'][report.framework.value] = report.next_review_date.isoformat()
        
        if framework_count > 0:
            summary['overall_score'] = total_score / framework_count
        
        return summary
    
    def get_violations(self, framework: ComplianceFramework = None, 
                      risk_level: RiskLevel = None, 
                      status: ComplianceStatus = None) -> List[ComplianceViolation]:
        """Get compliance violations with filters"""
        violations = self.violations
        
        if framework:
            violations = [v for v in violations if v.framework == framework]
        
        if risk_level:
            violations = [v for v in violations if v.risk_level == risk_level]
        
        if status:
            violations = [v for v in violations if v.status == status]
        
        return sorted(violations, key=lambda x: x.discovered_at, reverse=True)
    
    def resolve_violation(self, violation_id: str, resolution_notes: str = None):
        """Mark a violation as resolved"""
        for violation in self.violations:
            if violation.requirement_id == violation_id:
                violation.status = ComplianceStatus.COMPLIANT
                violation.resolved_at = datetime.now()
                
                # Log resolution
                audit_logger.log_event(
                    event_type=AuditEventType.COMPLIANCE_CHECK,
                    severity=AuditSeverity.LOW,
                    user_id=None,
                    ip_address="system",
                    user_agent="compliance_checker",
                    endpoint="/compliance/resolve",
                    method="SYSTEM",
                    status_code=200,
                    request_id=None,
                    client_id=None,
                    resource=violation.framework.value,
                    action="violation_resolved",
                    details={
                        'violation_id': violation_id,
                        'resolution_notes': resolution_notes
                    },
                    compliance_tags=[violation.framework.value]
                )
                
                self.logger.info(f"Resolved compliance violation: {violation_id}")
                return True
        
        return False
    
    def export_compliance_report(self, framework: ComplianceFramework = None, 
                               format: str = 'json') -> str:
        """Export compliance report"""
        reports = self.run_compliance_check(framework)
        
        if format == 'json':
            report_data = {
                'generated_at': datetime.now().isoformat(),
                'reports': [
                    {
                        'framework': report.framework.value,
                        'overall_status': report.overall_status.value,
                        'compliance_score': report.compliance_score,
                        'total_requirements': report.total_requirements,
                        'compliant_requirements': report.compliant_requirements,
                        'violations': [
                            {
                                'requirement_id': v.requirement_id,
                                'risk_level': v.risk_level.value,
                                'description': v.description,
                                'discovered_at': v.discovered_at.isoformat(),
                                'remediation_steps': v.remediation_steps
                            }
                            for v in report.violations
                        ],
                        'risk_assessment': {
                            level.value: count for level, count in report.risk_assessment.items()
                        },
                        'next_review_date': report.next_review_date.isoformat()
                    }
                    for report in reports
                ]
            }
            
            return json.dumps(report_data, indent=2)
        
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            header = ['framework', 'requirement_id', 'status', 'risk_level', 
                     'description', 'discovered_at', 'remediation_steps']
            writer.writerow(header)
            
            # Write violations
            for report in reports:
                for violation in report.violations:
                    row = [
                        violation.framework.value,
                        violation.requirement_id,
                        violation.status.value,
                        violation.risk_level.value,
                        violation.description,
                        violation.discovered_at.isoformat(),
                        '; '.join(violation.remediation_steps)
                    ]
                    writer.writerow(row)
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def schedule_compliance_checks(self):
        """Schedule periodic compliance checks"""
        # In a real implementation, you would use a scheduler like Celery
        # For now, this is a placeholder for the scheduling logic
        
        def run_scheduled_checks():
            """Run scheduled compliance checks"""
            self.logger.info("Running scheduled compliance checks")
            
            reports = self.run_compliance_check()
            
            # Check for alerts
            for report in reports:
                critical_count = report.risk_assessment[RiskLevel.CRITICAL]
                high_count = report.risk_assessment[RiskLevel.HIGH]
                
                if (critical_count >= ComplianceConfig.ALERT_THRESHOLDS['critical_violations'] or
                    high_count >= ComplianceConfig.ALERT_THRESHOLDS['high_violations'] or
                    report.compliance_score < ComplianceConfig.ALERT_THRESHOLDS['compliance_score_below']):
                    
                    self._send_compliance_alert(report)
        
        # This would be scheduled to run periodically
        # run_scheduled_checks()
    
    def _send_compliance_alert(self, report: ComplianceReport):
        """Send compliance alert for critical issues"""
        alert_message = f"🚨 COMPLIANCE ALERT - {report.framework.value.upper()}\n\n"
        alert_message += f"Status: {report.overall_status.value.upper()}\n"
        alert_message += f"Compliance Score: {report.compliance_score:.1f}%\n"
        alert_message += f"Critical Violations: {report.risk_assessment[RiskLevel.CRITICAL]}\n"
        alert_message += f"High Risk Violations: {report.risk_assessment[RiskLevel.HIGH]}\n\n"
        
        if report.violations:
            alert_message += "Top Violations:\n"
            for i, violation in enumerate(report.violations[:3], 1):
                alert_message += f"{i}. {violation.requirement_id} - {violation.risk_level.value.upper()}\n"
                alert_message += f"   {violation.description}\n\n"
        
        alert_message += "IMMEDIATE ACTION REQUIRED!\n"
        alert_message += "Please review and address compliance violations."
        
        self.logger.critical(alert_message)
        
        # Log compliance alert
        audit_logger.log_security_event(
            threat_type="compliance_violation",
            threat_score=90,
            ip_address="system",
            details={
                'framework': report.framework.value,
                'compliance_score': report.compliance_score,
                'violations_count': len(report.violations),
                'alert_message': alert_message
            }
        )


# Initialize global compliance checker
compliance_checker = ComplianceChecker()
