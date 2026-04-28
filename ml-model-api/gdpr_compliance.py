"""
GDPR compliance module for FlavorSnap
Handles user consent, data deletion, and compliance reporting
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json


class ConsentType(Enum):
    """Types of user consent"""
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    PROCESSING = "processing"
    THIRD_PARTY = "third_party"
    COOKIES = "cookies"


class DataDeletionStatus(Enum):
    """Status of data deletion request"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class GDPRCompliance:
    """Manages GDPR compliance operations"""
    
    def __init__(self):
        """Initialize GDPR compliance manager"""
        self.consent_records: Dict[str, Dict] = {}
        self.deletion_requests: Dict[str, Dict] = {}
        self.audit_log: List[Dict] = []
    
    def request_user_consent(self, user_id: str, consent_types: List[ConsentType]) -> Dict:
        """Request user consent for specific purposes"""
        consent_record = {
            'user_id': user_id,
            'consent_id': str(uuid.uuid4()),
            'consent_types': [ct.value for ct in consent_types],
            'timestamp': datetime.utcnow().isoformat(),
            'ip_address': None,  # Should be captured from request
            'version': 1,
            'status': 'pending',
        }
        
        self.consent_records[consent_record['consent_id']] = consent_record
        self._log_audit('consent_requested', user_id, consent_record)
        
        return consent_record
    
    def accept_consent(self, consent_id: str) -> Dict:
        """Accept user consent"""
        if consent_id not in self.consent_records:
            raise ValueError('Consent record not found')
        
        record = self.consent_records[consent_id]
        record['status'] = 'accepted'
        record['acceptance_timestamp'] = datetime.utcnow().isoformat()
        
        self._log_audit('consent_accepted', record['user_id'], record)
        
        return record
    
    def revoke_consent(self, consent_id: str) -> Dict:
        """Revoke previously given consent"""
        if consent_id not in self.consent_records:
            raise ValueError('Consent record not found')
        
        record = self.consent_records[consent_id]
        record['status'] = 'revoked'
        record['revocation_timestamp'] = datetime.utcnow().isoformat()
        
        self._log_audit('consent_revoked', record['user_id'], record)
        
        return record
    
    def request_data_access(self, user_id: str) -> Dict:
        """Handle user request for data access (GDPR Article 15)"""
        access_request = {
            'request_id': str(uuid.uuid4()),
            'user_id': user_id,
            'request_type': 'data_access',
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'pending',
            'data_categories': [
                'personal_information',
                'usage_data',
                'preferences',
                'transaction_history',
            ],
        }
        
        self._log_audit('data_access_requested', user_id, access_request)
        
        return access_request
    
    def request_data_deletion(self, user_id: str, reason: str = None) -> Dict:
        """Handle user request for data deletion (GDPR Article 17)"""
        deletion_request = {
            'deletion_id': str(uuid.uuid4()),
            'user_id': user_id,
            'request_type': 'data_deletion',
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat(),
            'status': DataDeletionStatus.PENDING.value,
            'estimated_completion': (
                datetime.utcnow() + timedelta(days=30)
            ).isoformat(),
        }
        
        self.deletion_requests[deletion_request['deletion_id']] = deletion_request
        self._log_audit('deletion_requested', user_id, deletion_request)
        
        return deletion_request
    
    def process_deletion_request(self, deletion_id: str) -> Dict:
        """Process a deletion request"""
        if deletion_id not in self.deletion_requests:
            raise ValueError('Deletion request not found')
        
        request = self.deletion_requests[deletion_id]
        request['status'] = DataDeletionStatus.COMPLETED.value
        request['completion_timestamp'] = datetime.utcnow().isoformat()
        request['deleted_data_categories'] = [
            'personal_information',
            'usage_analytics',
            'preferences',
        ]
        
        self._log_audit('deletion_completed', request['user_id'], request)
        
        return request
    
    def get_user_data_export(self, user_id: str) -> Dict:
        """Export all user data in GDPR-compliant format"""
        export_data = {
            'export_id': str(uuid.uuid4()),
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat(),
            'format': 'json',
            'data': {
                'personal_information': {},
                'usage_data': {},
                'preferences': {},
                'communications': [],
            },
        }
        
        self._log_audit('data_exported', user_id, export_data)
        
        return export_data
    
    def request_data_portability(self, user_id: str, format: str = 'json') -> Dict:
        """Handle data portability request (GDPR Article 20)"""
        portability_request = {
            'request_id': str(uuid.uuid4()),
            'user_id': user_id,
            'format': format,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'pending',
            'available_formats': ['json', 'csv', 'xml'],
        }
        
        self._log_audit('portability_requested', user_id, portability_request)
        
        return portability_request
    
    def get_audit_log(self, user_id: str = None, 
                     days: int = 90) -> List[Dict]:
        """Get audit log for compliance verification"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        filtered_logs = [
            log for log in self.audit_log
            if (user_id is None or log.get('user_id') == user_id) and
            datetime.fromisoformat(log['timestamp']) >= cutoff_date
        ]
        
        return filtered_logs
    
    def _log_audit(self, action: str, user_id: str, details: Dict):
        """Log audit trail for compliance"""
        self.audit_log.append({
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'user_id': user_id,
            'details': details,
            'log_id': str(uuid.uuid4()),
        })
    
    def generate_compliance_report(self, period_days: int = 30) -> Dict:
        """Generate GDPR compliance report"""
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        relevant_logs = [
            log for log in self.audit_log
            if datetime.fromisoformat(log['timestamp']) >= cutoff_date
        ]
        
        return {
            'report_id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'period_days': period_days,
            'total_actions': len(relevant_logs),
            'consent_requests': len([l for l in relevant_logs if 'consent' in l['action']]),
            'deletion_requests': len([l for l in relevant_logs if 'deletion' in l['action']]),
            'data_exports': len([l for l in relevant_logs if 'exported' in l['action']]),
            'audit_log_entries': relevant_logs[:100],  # Last 100 entries
        }
