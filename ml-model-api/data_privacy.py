"""
Comprehensive data privacy module for FlavorSnap
Handles encryption, anonymization, and data protection
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import os
import base64
import hashlib
from typing import Any, Dict
import json
from datetime import datetime
from enum import Enum


class EncryptionLevel(Enum):
    """Data encryption levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DataPrivacy:
    """Handles data encryption and privacy operations"""
    
    def __init__(self, master_key: str = None):
        """Initialize with encryption key"""
        if master_key is None:
            master_key = os.environ.get('ENCRYPTION_KEY', 'default-dev-key')
        
        self.key = self._derive_key(master_key)
        self.cipher = Fernet(self.key)
    
    @staticmethod
    def _derive_key(password: str) -> bytes:
        """Derive encryption key from password"""
        salt = b'flavorsnap_salt'  # In production, use random salt
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt_data(self, data: Any, level: EncryptionLevel = EncryptionLevel.MEDIUM) -> str:
        """Encrypt data with specified security level"""
        json_data = json.dumps(data) if not isinstance(data, str) else data
        encrypted = self.cipher.encrypt(json_data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_data(self, encrypted_data: str) -> Any:
        """Decrypt encrypted data"""
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {str(e)}")
    
    def anonymize_user_data(self, user_data: Dict) -> Dict:
        """Anonymize sensitive user information"""
        anonymized = {}
        
        for key, value in user_data.items():
            if key in ['email', 'phone', 'name']:
                # Hash sensitive data
                anonymized[key] = self._hash_data(value)
            elif key in ['ip_address']:
                # Mask IP address
                anonymized[key] = self._mask_ip(value)
            else:
                anonymized[key] = value
        
        return anonymized
    
    @staticmethod
    def _hash_data(data: str) -> str:
        """Hash data using SHA-256"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def _mask_ip(ip: str) -> str:
        """Mask the last octet of an IP address"""
        parts = ip.split('.')
        if len(parts) == 4:
            parts[-1] = '***'
            return '.'.join(parts)
        return ip
    
    def tokenize_sensitive_data(self, data: str) -> str:
        """Create a token reference for sensitive data"""
        token = hashlib.sha256(data.encode()).hexdigest()[:16]
        return f"token_{token}"


class PII(Enum):
    """Personally Identifiable Information types"""
    EMAIL = "email"
    PHONE = "phone"
    NAME = "name"
    ADDRESS = "address"
    PAYMENT_INFO = "payment_info"
    LOCATION = "location"


def detect_pii(data: Dict) -> Dict[str, Any]:
    """Detect PII in data"""
    detected_pii = {}
    
    pii_patterns = {
        PII.EMAIL.value: r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        PII.PHONE.value: r'^\+?1?\d{9,15}$',
    }
    
    import re
    
    for key, value in data.items():
        if isinstance(value, str):
            for pii_type, pattern in pii_patterns.items():
                if re.match(pattern, value):
                    detected_pii[key] = pii_type
    
    return detected_pii


def mask_pii_in_logs(log_message: str) -> str:
    """Mask PII in log messages"""
    import re
    
    # Mask email
    log_message = re.sub(
        r'[\w\.-]+@[\w\.-]+\.\w+',
        '[EMAIL]',
        log_message
    )
    
    # Mask phone numbers
    log_message = re.sub(
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        '[PHONE]',
        log_message
    )
    
    return log_message
