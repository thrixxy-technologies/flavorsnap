#!/usr/bin/env python3
"""
Compliance Reporter for FlavorSnap Logging System
Implements comprehensive compliance reporting for various regulations
"""

import asyncio
import json
import hashlib
import re
import aiohttp
import aiofiles
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplianceStandard(Enum):
    GDPR = "GDPR"
    HIPAA = "HIPAA"
    SOX = "SOX"
    PCI_DSS = "PCI_DSS"
    ISO_27001 = "ISO_27001"
    NIST_800_53 = "NIST_800_53"
    CCPA = "CCPA"
    LGPD = "LGPD"

class ComplianceCategory(Enum):
    DATA_PROTECTION = "data_protection"
    ACCESS_CONTROL = "access_control"
    AUDIT_LOGGING = "audit_logging"
    INCIDENT_RESPONSE = "incident_response"
    PRIVACY = "privacy"
    SECURITY = "security"
    RETENTION = "retention"
    ENCRYPTION = "encryption"

class ComplianceStatus(Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NOT_ASSESSED = "not_assessed"
    EXCEPTION = "exception"

@dataclass
class ComplianceRequirement:
    id: str
    standard: ComplianceStandard
    category: ComplianceCategory
    requirement: str
    description: str
    controls: List[str]
    evidence_required: List[str]
    assessment_frequency: str

@dataclass
class ComplianceEvidence:
    id: str
    requirement_id: str
    evidence_type: str
    evidence_data: Dict[str, Any]
    timestamp: datetime
    source: str
    hash_value: str

@dataclass
class ComplianceAssessment:
    id: str
    requirement_id: str
    status: ComplianceStatus
    score: float
    findings: List[str]
    recommendations: List[str]
    assessed_by: str
    assessed_at: datetime
    next_assessment: datetime

@dataclass
class ComplianceReport:
    id: str
    standard: ComplianceStandard
    period_start: datetime
    period_end: datetime
    overall_status: ComplianceStatus
    overall_score: float
    requirements: List[ComplianceRequirement]
    assessments: List[ComplianceAssessment]
    evidence: List[ComplianceEvidence]
    summary: Dict[str, Any]
    generated_at: datetime

class ComplianceReporter:
    """Advanced compliance reporter for multiple regulations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.requirements: Dict[str, ComplianceRequirement] = {}
        self.evidence: List[ComplianceEvidence] = []
        self.assessments: Dict[str, ComplianceAssessment] = {}
        
        # Load compliance requirements
        self._load_compliance_requirements()
        
        # Compliance rules and patterns
        self.compliance_rules = self._initialize_compliance_rules()
    
    def _load_compliance_requirements(self):
        """Load compliance requirements for different standards"""
        # GDPR Requirements
        gdpr_requirements = [
            ComplianceRequirement(
                id="GDPR_001",
                standard=ComplianceStandard.GDPR,
                category=ComplianceCategory.DATA_PROTECTION,
                requirement="Lawful basis for processing",
                description="Personal data shall be processed lawfully, fairly and in a transparent manner",
                controls=["privacy_policy", "consent_management", "data_processing_records"],
                evidence_required=["consent_records", "processing_logs", "privacy_policy"],
                assessment_frequency="quarterly"
            ),
            ComplianceRequirement(
                id="GDPR_002",
                standard=ComplianceStandard.GDPR,
                category=ComplianceCategory.AUDIT_LOGGING,
                requirement="Data protection impact assessments",
                description="Where processing is likely to result in high risk to data subjects, DPIA required",
                controls=["risk_assessments", "documentation", "review_process"],
                evidence_required=["dpia_reports", "risk_assessments", "review_documentation"],
                assessment_frequency="annually"
            ),
            ComplianceRequirement(
                id="GDPR_003",
                standard=ComplianceStandard.GDPR,
                category=ComplianceCategory.ACCESS_CONTROL,
                requirement="Right to access",
                description="Data subjects shall have right to access their personal data",
                controls=["access_requests", "identity_verification", "response_tracking"],
                evidence_required=["access_request_logs", "identity_verification_records", "response_logs"],
                assessment_frequency="monthly"
            ),
            ComplianceRequirement(
                id="GDPR_004",
                standard=ComplianceStandard.GDPR,
                category=ComplianceCategory.RETENTION,
                requirement="Data retention limits",
                description="Personal data shall not be retained longer than necessary",
                controls=["retention_policies", "automated_deletion", "retention_audits"],
                evidence_required=["retention_policy", "deletion_logs", "retention_audit_reports"],
                assessment_frequency="quarterly"
            )
        ]
        
        # HIPAA Requirements
        hipaa_requirements = [
            ComplianceRequirement(
                id="HIPAA_001",
                standard=ComplianceStandard.HIPAA,
                category=ComplianceCategory.ACCESS_CONTROL,
                requirement="Access management",
                description="Implement procedures for granting and revoking access to EPHI",
                controls=["user_access", "access_logs", "termination_procedures"],
                evidence_required=["access_logs", "user_access_records", "termination_logs"],
                assessment_frequency="quarterly"
            ),
            ComplianceRequirement(
                id="HIPAA_002",
                standard=ComplianceStandard.HIPAA,
                category=ComplianceCategory.AUDIT_LOGGING,
                requirement="Audit controls",
                description="Implement hardware, software, and procedural mechanisms that record access",
                controls=["audit_logs", "access_monitoring", "tamper_detection"],
                evidence_required=["audit_logs", "access_monitoring_reports", "tamper_detection_logs"],
                assessment_frequency="quarterly"
            ),
            ComplianceRequirement(
                id="HIPAA_003",
                standard=ComplianceStandard.HIPAA,
                category=ComplianceCategory.SECURITY,
                requirement="Transmission security",
                description="Implement security measures to guard against unauthorized access",
                controls=["encryption", "secure_transmission", "integrity_controls"],
                evidence_required=["encryption_certificates", "transmission_logs", "integrity_checks"],
                assessment_frequency="quarterly"
            )
        ]
        
        # PCI DSS Requirements
        pci_requirements = [
            ComplianceRequirement(
                id="PCI_001",
                standard=ComplianceStandard.PCI_DSS,
                category=ComplianceCategory.ENCRYPTION,
                requirement="Strong cryptography",
                description="Use strong cryptography and security protocols",
                controls=["encryption_algorithms", "key_management", "secure_protocols"],
                evidence_required=["encryption_configuration", "key_management_logs", "protocol_configuration"],
                assessment_frequency="quarterly"
            ),
            ComplianceRequirement(
                id="PCI_002",
                standard=ComplianceStandard.PCI_DSS,
                category=ComplianceCategory.ACCESS_CONTROL,
                requirement="Access control measures",
                description="Restrict access to cardholder data by business need-to-know",
                controls=["access_control", "user_authentication", "access_logs"],
                evidence_required=["access_control_policies", "authentication_logs", "access_logs"],
                assessment_frequency="quarterly"
            )
        ]
        
        # Store all requirements
        for req in gdpr_requirements + hipaa_requirements + pci_requirements:
            self.requirements[req.id] = req
        
        logger.info(f"Loaded {len(self.requirements)} compliance requirements")
    
    def _initialize_compliance_rules(self) -> Dict[str, Any]:
        """Initialize compliance checking rules"""
        return {
            'data_protection': {
                'personal_data_patterns': [
                    r'(?i)(email|phone|ssn|credit.*card|bank.*account|passport|driver.*license)',
                    r'(?i)(first.*name|last.*name|address|birth.*date|gender|nationality)',
                    r'(?i)(health.*record|medical.*history|insurance|treatment|diagnosis)'
                ],
                'consent_keywords': [
                    r'(?i)(consent|agree|accept|opt.*in|permission)',
                    r'(?i)(privacy.*policy|terms.*of.*service|data.*processing)'
                ],
                'data_retention_periods': {
                    'personal_data': 2555,  # 7 years in days
                    'financial_data': 2555,
                    'health_data': 2555,
                    'transaction_data': 2555
                }
            },
            'access_control': {
                'authentication_events': [
                    'login', 'logout', 'password_change', 'account_lock', 'account_unlock',
                    'multi_factor_auth', 'session_creation', 'session_termination'
                ],
                'access_grant_events': [
                    'permission_grant', 'role_assignment', 'access_approval', 'privilege_escalation'
                ],
                'access_revoke_events': [
                    'permission_revoke', 'role_removal', 'access_denial', 'account_termination'
                ],
                'failed_access_threshold': 5,  # 5 failed attempts
                'failed_access_window': 300  # 5 minutes
            },
            'audit_logging': {
                'required_events': [
                    'data_access', 'data_modification', 'data_deletion', 'data_export',
                    'system_configuration', 'user_management', 'security_incident',
                    'policy_violation', 'compliance_breach', 'emergency_access'
                ],
                'log_retention_days': 2555,  # 7 years
                'log_integrity_checks': True,
                'tamper_detection': True
            },
            'security': {
                'encryption_required': True,
                'encryption_algorithms': ['AES-256', 'RSA-2048', 'SHA-256'],
                'secure_protocols': ['TLS-1.2', 'HTTPS'],
                'vulnerability_scanning': True,
                'penetration_testing': True,
                'security_incident_response': True
            },
            'privacy': {
                'data_minimization': True,
                'purpose_limitation': True,
                'accuracy_maintenance': True,
                'storage_limitation': True,
                'accountability': True,
                'privacy_impact_assessments': True
            }
        }
    
    async def assess_compliance(self, standard: ComplianceStandard,
                             period_start: datetime = None,
                             period_end: datetime = None) -> ComplianceReport:
        """Assess compliance for a specific standard"""
        if period_start is None:
            period_start = datetime.utcnow() - timedelta(days=90)
        
        if period_end is None:
            period_end = datetime.utcnow()
        
        import uuid
        report_id = str(uuid.uuid4())
        
        # Get requirements for standard
        standard_requirements = [
            req for req in self.requirements.values()
            if req.standard == standard
        ]
        
        # Assess each requirement
        assessments = []
        for requirement in standard_requirements:
            assessment = await self._assess_requirement(requirement, period_start, period_end)
            assessments.append(assessment)
            self.assessments[f"{requirement.id}_{report_id}"] = assessment
        
        # Get evidence for the period
        period_evidence = [
            ev for ev in self.evidence
            if period_start <= ev.timestamp <= period_end
        ]
        
        # Calculate overall score and status
        scores = [a.score for a in assessments]
        overall_score = sum(scores) / len(scores) if scores else 0
        
        if overall_score >= 90:
            overall_status = ComplianceStatus.COMPLIANT
        elif overall_score >= 70:
            overall_status = ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            overall_status = ComplianceStatus.NON_COMPLIANT
        
        # Generate summary
        summary = await self._generate_compliance_summary(assessments, period_evidence)
        
        report = ComplianceReport(
            id=report_id,
            standard=standard,
            period_start=period_start,
            period_end=period_end,
            overall_status=overall_status,
            overall_score=overall_score,
            requirements=standard_requirements,
            assessments=assessments,
            evidence=period_evidence,
            summary=summary,
            generated_at=datetime.utcnow()
        )
        
        logger.info(f"Compliance assessment completed for {standard.value}: {overall_score:.1f}% ({overall_status.value})")
        return report
    
    async def _assess_requirement(self, requirement: ComplianceRequirement,
                                period_start: datetime,
                                period_end: datetime) -> ComplianceAssessment:
        """Assess a specific compliance requirement"""
        import uuid
        assessment_id = str(uuid.uuid4())
        
        # Get relevant evidence
        relevant_evidence = [
            ev for ev in self.evidence
            if ev.requirement_id == requirement.id and
               period_start <= ev.timestamp <= period_end
        ]
        
        # Assess based on requirement category
        if requirement.category == ComplianceCategory.DATA_PROTECTION:
            score, findings, recommendations = await self._assess_data_protection(
                requirement, relevant_evidence
            )
        elif requirement.category == ComplianceCategory.ACCESS_CONTROL:
            score, findings, recommendations = await self._assess_access_control(
                requirement, relevant_evidence
            )
        elif requirement.category == ComplianceCategory.AUDIT_LOGGING:
            score, findings, recommendations = await self._assess_audit_logging(
                requirement, relevant_evidence
            )
        elif requirement.category == ComplianceCategory.SECURITY:
            score, findings, recommendations = await self._assess_security(
                requirement, relevant_evidence
            )
        elif requirement.category == ComplianceCategory.RETENTION:
            score, findings, recommendations = await self._assess_retention(
                requirement, relevant_evidence
            )
        else:
            score, findings, recommendations = await self._assess_generic(
                requirement, relevant_evidence
            )
        
        assessment = ComplianceAssessment(
            id=assessment_id,
            requirement_id=requirement.id,
            status=self._score_to_status(score),
            score=score,
            findings=findings,
            recommendations=recommendations,
            assessed_by='compliance_system',
            assessed_at=datetime.utcnow(),
            next_assessment=datetime.utcnow() + timedelta(days=90)
        )
        
        return assessment
    
    async def _assess_data_protection(self, requirement: ComplianceRequirement,
                                    evidence: List[ComplianceEvidence]) -> Tuple[float, List[str], List[str]]:
        """Assess data protection compliance"""
        score = 100.0
        findings = []
        recommendations = []
        
        # Check for personal data identification
        personal_data_detected = False
        for ev in evidence:
            if 'personal_data' in ev.evidence_data:
                personal_data_detected = True
                if not ev.evidence_data.get('consent_obtained', False):
                    score -= 20
                    findings.append("Personal data processed without consent")
                    recommendations.append("Implement consent management system")
        
        if not personal_data_detected:
            score -= 10
            findings.append("No evidence of personal data processing controls")
            recommendations.append("Document personal data processing activities")
        
        # Check data minimization
        data_minimization_score = 100
        for ev in evidence:
            if ev.evidence_data.get('data_collected', 0) > ev.evidence_data.get('data_required', 0):
                data_minimization_score -= 30
        
        if data_minimization_score < 70:
            score -= 15
            findings.append("Data minimization principles not followed")
            recommendations.append("Implement data minimization controls")
        
        return max(0, score), findings, recommendations
    
    async def _assess_access_control(self, requirement: ComplianceRequirement,
                                  evidence: List[ComplianceEvidence]) -> Tuple[float, List[str], List[str]]:
        """Assess access control compliance"""
        score = 100.0
        findings = []
        recommendations = []
        
        # Check authentication events
        auth_events = [ev for ev in evidence if 'authentication' in ev.evidence_type]
        if not auth_events:
            score -= 25
            findings.append("Insufficient authentication logging")
            recommendations.append("Implement comprehensive authentication logging")
        
        # Check access grant/revoke events
        access_events = [ev for ev in evidence if 'access_control' in ev.evidence_type]
        if len(access_events) < 5:  # Require at least 5 access events
            score -= 20
            findings.append("Insufficient access control event logging")
            recommendations.append("Log all access grant and revoke events")
        
        # Check for failed access attempts
        failed_attempts = 0
        for ev in evidence:
            if ev.evidence_data.get('failed_access', False):
                failed_attempts += 1
        
        if failed_attempts > 10:
            score -= 15
            findings.append(f"High number of failed access attempts: {failed_attempts}")
            recommendations.append("Implement stronger access controls and monitoring")
        
        return max(0, score), findings, recommendations
    
    async def _assess_audit_logging(self, requirement: ComplianceRequirement,
                                evidence: List[ComplianceEvidence]) -> Tuple[float, List[str], List[str]]:
        """Assess audit logging compliance"""
        score = 100.0
        findings = []
        recommendations = []
        
        # Check for required audit events
        required_events = self.compliance_rules['audit_logging']['required_events']
        logged_events = set()
        
        for ev in evidence:
            if 'audit_event' in ev.evidence_type:
                event_type = ev.evidence_data.get('event_type', '')
                logged_events.add(event_type)
        
        missing_events = set(required_events) - logged_events
        if missing_events:
            score -= len(missing_events) * 10
            findings.append(f"Missing audit events: {', '.join(missing_events)}")
            recommendations.append(f"Implement logging for missing events: {', '.join(missing_events)}")
        
        # Check log retention
        oldest_log = min([ev.timestamp for ev in evidence]) if evidence else datetime.utcnow()
        retention_days = (datetime.utcnow() - oldest_log).days
        required_retention = self.compliance_rules['audit_logging']['log_retention_days']
        
        if retention_days < required_retention:
            score -= 20
            findings.append(f"Log retention period ({retention_days} days) below requirement ({required_retention} days)")
            recommendations.append(f"Implement log retention for at least {required_retention} days")
        
        return max(0, score), findings, recommendations
    
    async def _assess_security(self, requirement: ComplianceRequirement,
                            evidence: List[ComplianceEvidence]) -> Tuple[float, List[str], List[str]]:
        """Assess security compliance"""
        score = 100.0
        findings = []
        recommendations = []
        
        # Check encryption
        encryption_evidence = [ev for ev in evidence if 'encryption' in ev.evidence_type]
        if not encryption_evidence:
            score -= 30
            findings.append("No evidence of encryption implementation")
            recommendations.append("Implement encryption for sensitive data")
        else:
            # Check encryption algorithms
            for ev in encryption_evidence:
                algorithm = ev.evidence_data.get('algorithm', '')
                if algorithm not in self.compliance_rules['security']['encryption_algorithms']:
                    score -= 15
                    findings.append(f"Weak encryption algorithm: {algorithm}")
                    recommendations.append("Upgrade to strong encryption algorithms")
        
        # Check for security incidents
        security_incidents = [ev for ev in evidence if 'security_incident' in ev.evidence_type]
        if len(security_incidents) > 0:
            incident_response = any(ev.evidence_data.get('response_time', 0) < 3600 for ev in security_incidents)
            if not incident_response:
                score -= 20
                findings.append("Security incidents not properly responded to")
                recommendations.append("Implement security incident response procedures")
        
        return max(0, score), findings, recommendations
    
    async def _assess_retention(self, requirement: ComplianceRequirement,
                             evidence: List[ComplianceEvidence]) -> Tuple[float, List[str], List[str]]:
        """Assess data retention compliance"""
        score = 100.0
        findings = []
        recommendations = []
        
        # Check retention policies
        retention_evidence = [ev for ev in evidence if 'retention' in ev.evidence_type]
        if not retention_evidence:
            score -= 25
            findings.append("No evidence of retention policy implementation")
            recommendations.append("Implement and document data retention policies")
        
        # Check automated deletion
        automated_deletion = any(ev.evidence_data.get('automated', False) for ev in retention_evidence)
        if not automated_deletion:
            score -= 15
            findings.append("Data deletion not automated")
            recommendations.append("Implement automated data deletion procedures")
        
        # Check retention periods
        for ev in retention_evidence:
            data_type = ev.evidence_data.get('data_type', '')
            retention_period = ev.evidence_data.get('retention_days', 0)
            required_period = self.compliance_rules['data_protection']['data_retention_periods'].get(data_type, 2555)
            
            if retention_period > required_period:
                score -= 10
                findings.append(f"Retention period for {data_type} exceeds requirement")
                recommendations.append(f"Reduce retention period for {data_type} to {required_period} days")
        
        return max(0, score), findings, recommendations
    
    async def _assess_generic(self, requirement: ComplianceRequirement,
                            evidence: List[ComplianceEvidence]) -> Tuple[float, List[str], List[str]]:
        """Generic assessment for other requirement types"""
        score = 100.0
        findings = []
        recommendations = []
        
        # Base assessment on evidence availability
        if not evidence:
            score -= 50
            findings.append("No evidence available for assessment")
            recommendations.append("Implement evidence collection for compliance requirements")
        else:
            # Check if controls are implemented
            controls_implemented = set()
            for ev in evidence:
                controls_implemented.update(ev.evidence_data.get('controls', []))
            
            missing_controls = set(requirement.controls) - controls_implemented
            if missing_controls:
                score -= len(missing_controls) * 10
                findings.append(f"Missing controls: {', '.join(missing_controls)}")
                recommendations.append(f"Implement missing controls: {', '.join(missing_controls)}")
        
        return max(0, score), findings, recommendations
    
    def _score_to_status(self, score: float) -> ComplianceStatus:
        """Convert compliance score to status"""
        if score >= 90:
            return ComplianceStatus.COMPLIANT
        elif score >= 70:
            return ComplianceStatus.PARTIALLY_COMPLIANT
        elif score >= 50:
            return ComplianceStatus.NON_COMPLIANT
        else:
            return ComplianceStatus.NOT_ASSESSED
    
    async def _generate_compliance_summary(self, assessments: List[ComplianceAssessment],
                                       evidence: List[ComplianceEvidence]) -> Dict[str, Any]:
        """Generate compliance summary statistics"""
        # Status distribution
        status_counts = {}
        for status in ComplianceStatus:
            status_counts[status.value] = len([a for a in assessments if a.status == status])
        
        # Category distribution
        category_scores = {}
        for assessment in assessments:
            req = self.requirements.get(assessment.requirement_id)
            if req:
                category = req.category.value
                if category not in category_scores:
                    category_scores[category] = []
                category_scores[category].append(assessment.score)
        
        # Calculate average scores by category
        category_averages = {
            cat: sum(scores) / len(scores)
            for cat, scores in category_scores.items()
        }
        
        # Evidence statistics
        evidence_types = {}
        for ev in evidence:
            evidence_types[ev.evidence_type] = evidence_types.get(ev.evidence_type, 0) + 1
        
        # Risk assessment
        high_risk_requirements = [
            a for a in assessments
            if a.status in [ComplianceStatus.NON_COMPLIANT, ComplianceStatus.NOT_ASSESSED]
        ]
        
        return {
            'status_distribution': status_counts,
            'category_averages': category_averages,
            'evidence_types': evidence_types,
            'total_requirements': len(assessments),
            'compliant_requirements': len([a for a in assessments if a.status == ComplianceStatus.COMPLIANT]),
            'high_risk_requirements': len(high_risk_requirements),
            'average_score': sum(a.score for a in assessments) / len(assessments) if assessments else 0
        }
    
    async def add_evidence(self, requirement_id: str, evidence_type: str,
                         evidence_data: Dict[str, Any], source: str = 'manual'):
        """Add compliance evidence"""
        import uuid
        
        evidence = ComplianceEvidence(
            id=str(uuid.uuid4()),
            requirement_id=requirement_id,
            evidence_type=evidence_type,
            evidence_data=evidence_data,
            timestamp=datetime.utcnow(),
            source=source,
            hash_value=self._generate_evidence_hash(evidence_type, evidence_data)
        )
        
        self.evidence.append(evidence)
        logger.info(f"Added evidence for requirement {requirement_id}: {evidence_type}")
    
    def _generate_evidence_hash(self, evidence_type: str, evidence_data: Dict[str, Any]) -> str:
        """Generate hash for evidence integrity"""
        hash_data = f"{evidence_type}:{json.dumps(evidence_data, sort_keys=True)}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(hash_data.encode()).hexdigest()[:16]
    
    async def generate_compliance_dashboard(self, reports: List[ComplianceReport]) -> Dict[str, Any]:
        """Generate compliance dashboard data"""
        dashboard = {
            'dashboard_metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'total_reports': len(reports),
                'standards_covered': list(set(r.standard for r in reports))
            },
            'overall_compliance': {},
            'standard_breakdown': {},
            'trend_analysis': {},
            'risk_assessment': {},
            'recommendations': []
        }
        
        # Overall compliance metrics
        all_scores = [r.overall_score for r in reports]
        if all_scores:
            dashboard['overall_compliance'] = {
                'average_score': sum(all_scores) / len(all_scores),
                'best_score': max(all_scores),
                'worst_score': min(all_scores),
                'compliant_standards': len([r for r in reports if r.overall_status == ComplianceStatus.COMPLIANT]),
                'total_standards': len(set(r.standard for r in reports))
            }
        
        # Breakdown by standard
        for report in reports:
            standard = report.standard.value
            dashboard['standard_breakdown'][standard] = {
                'status': report.overall_status.value,
                'score': report.overall_score,
                'requirements_count': len(report.requirements),
                'compliant_requirements': len([a for a in report.assessments if a.status == ComplianceStatus.COMPLIANT]),
                'last_assessment': report.generated_at.isoformat()
            }
        
        # Trend analysis (simplified - would use historical data)
        dashboard['trend_analysis'] = {
            'improvement_needed': [r.standard.value for r in reports if r.overall_score < 80],
            'well_performing': [r.standard.value for r in reports if r.overall_score >= 90],
            'attention_required': [r.standard.value for r in reports if r.overall_status != ComplianceStatus.COMPLIANT]
        }
        
        # Risk assessment
        high_risk_items = []
        for report in reports:
            high_risk_assessments = [
                a for a in report.assessments
                if a.status in [ComplianceStatus.NON_COMPLIANT, ComplianceStatus.NOT_ASSESSED]
            ]
            high_risk_items.extend(high_risk_assessments)
        
        dashboard['risk_assessment'] = {
            'total_high_risk_items': len(high_risk_items),
            'risk_categories': list(set(
                self.requirements.get(a.requirement_id, {}).category.value
                for a in high_risk_items
            )),
            'urgent_actions_needed': len([a for a in high_risk_items if a.score < 50])
        }
        
        # Aggregate recommendations
        all_recommendations = []
        for report in reports:
            for assessment in report.assessments:
                all_recommendations.extend(assessment.recommendations)
        
        # Remove duplicates and prioritize
        unique_recommendations = list(set(all_recommendations))
        dashboard['recommendations'] = unique_recommendations[:10]  # Top 10
        
        return dashboard
    
    async def export_compliance_report(self, report: ComplianceReport, filepath: str, format: str = 'json'):
        """Export compliance report to file"""
        try:
            report_data = asdict(report)
            
            if format.lower() == 'json':
                with open(filepath, 'w') as f:
                    json.dump(report_data, f, indent=2, default=str)
            elif format.lower() == 'csv':
                # Export assessments to CSV
                assessments_df = pd.DataFrame([asdict(a) for a in report.assessments])
                assessments_df.to_csv(filepath.replace('.csv', '_assessments.csv'), index=False)
                
                # Export evidence to CSV
                evidence_df = pd.DataFrame([asdict(e) for e in report.evidence])
                evidence_df.to_csv(filepath.replace('.csv', '_evidence.csv'), index=False)
            elif format.lower() == 'pdf':
                # Generate PDF report (simplified - would use reportlab)
                self._generate_pdf_report(report, filepath)
            
            logger.info(f"Compliance report exported to {filepath}")
            
        except Exception as e:
            logger.error(f"Error exporting compliance report: {e}")
    
    def _generate_pdf_report(self, report: ComplianceReport, filepath: str):
        """Generate PDF compliance report"""
        # This is a simplified PDF generation
        # In real implementation, use reportlab or similar library
        pdf_content = f"""
        Compliance Report - {report.standard.value}
        
        Period: {report.period_start.strftime('%Y-%m-%d')} to {report.period_end.strftime('%Y-%m-%d')}
        Overall Status: {report.overall_status.value}
        Overall Score: {report.overall_score:.1f}%
        
        Requirements Assessed: {len(report.assessments)}
        Compliant Requirements: {len([a for a in report.assessments if a.status == ComplianceStatus.COMPLIANT])}
        
        Summary:
        {json.dumps(report.summary, indent=2)}
        """
        
        # Write as text file with .pdf extension (simplified)
        with open(filepath.replace('.pdf', '.txt'), 'w') as f:
            f.write(pdf_content)

# Example usage
if __name__ == "__main__":
    config = {
        'output_dir': '/app/logs/compliance',
        'evidence_retention_days': 2555,
        'assessment_frequency_days': 90,
        'dashboard_refresh_interval_minutes': 60
    }
    
    reporter = ComplianceReporter(config)
    
    async def test_compliance_reporting():
        # Add some sample evidence
        await reporter.add_evidence(
            requirement_id="GDPR_001",
            evidence_type="consent_records",
            evidence_data={
                "consent_obtained": True,
                "consent_date": "2024-04-24T10:00:00Z",
                "consent_method": "electronic",
                "data_purpose": "service_provisioning"
            },
            source="privacy_policy"
        )
        
        await reporter.add_evidence(
            requirement_id="HIPAA_001",
            evidence_type="access_logs",
            evidence_data={
                "access_granted": True,
                "user_id": "user123",
                "resource": "patient_records",
                "timestamp": "2024-04-24T10:30:00Z",
                "authorized_by": "admin"
            },
            source="access_control_system"
        )
        
        # Assess GDPR compliance
        gdpr_report = await reporter.assess_compliance(ComplianceStandard.GDPR)
        
        # Assess HIPAA compliance
        hipaa_report = await reporter.assess_compliance(ComplianceStandard.HIPAA)
        
        # Generate dashboard
        dashboard = await reporter.generate_compliance_dashboard([gdpr_report, hipaa_report])
        
        print("Compliance Dashboard:")
        print(json.dumps(dashboard, indent=2, default=str))
        
        # Export reports
        await reporter.export_compliance_report(gdpr_report, '/tmp/gdpr_report.json')
        await reporter.export_compliance_report(hipaa_report, '/tmp/hipaa_report.json')
    
    asyncio.run(test_compliance_reporting())
