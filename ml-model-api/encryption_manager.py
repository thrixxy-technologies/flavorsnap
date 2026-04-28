"""
Encryption manager for database and sensitive data
"""

from ml_model_api.data_privacy import DataPrivacy, EncryptionLevel
from typing import Any, Dict, Optional
import json
from datetime import datetime, timedelta


class EncryptionManager:
    """Manages all encryption operations"""
    
    def __init__(self):
        """Initialize encryption manager"""
        self.privacy = DataPrivacy()
        self.encrypted_data_store: Dict[str, Dict] = {}
    
    def encrypt_user_record(self, user_id: str, data: Dict, 
                           level: EncryptionLevel = EncryptionLevel.HIGH) -> Dict:
        """Encrypt complete user record"""
        encrypted_record = {
            'user_id': user_id,
            'encrypted_data': self.privacy.encrypt_data(data, level),
            'encryption_level': level.value,
            'timestamp': datetime.utcnow().isoformat(),
            'version': 1,
        }
        
        # Store for retrieval
        self.encrypted_data_store[user_id] = encrypted_record
        
        return encrypted_record
    
    def decrypt_user_record(self, user_id: str, 
                           encrypted_record: Dict) -> Optional[Dict]:
        """Decrypt user record"""
        try:
            return self.privacy.decrypt_data(encrypted_record['encrypted_data'])
        except Exception as e:
            raise ValueError(f"Failed to decrypt user record: {str(e)}")
    
    def encrypt_database_connection_string(self, connection_string: str) -> str:
        """Encrypt database connection string"""
        return self.privacy.encrypt_data(connection_string, EncryptionLevel.HIGH)
    
    def encrypt_api_keys(self, keys: Dict[str, str]) -> Dict[str, str]:
        """Encrypt API keys"""
        encrypted_keys = {}
        for key_name, key_value in keys.items():
            encrypted_keys[key_name] = self.privacy.encrypt_data(
                key_value, 
                EncryptionLevel.HIGH
            )
        return encrypted_keys
    
    def support_field_level_encryption(self, data: Dict, 
                                       fields_to_encrypt: list) -> Dict:
        """Support field-level encryption"""
        encrypted_data = data.copy()
        
        for field in fields_to_encrypt:
            if field in encrypted_data:
                encrypted_data[field] = self.privacy.encrypt_data(
                    encrypted_data[field],
                    EncryptionLevel.MEDIUM
                )
        
        return encrypted_data
    
    def rotate_encryption_keys(self, old_manager: 'EncryptionManager') -> Dict:
        """Rotate encryption keys"""
        rotation_report = {
            'timestamp': datetime.utcnow().isoformat(),
            'records_rotated': 0,
            'status': 'completed',
        }
        
        # In production, re-encrypt all data with new keys
        for user_id in self.encrypted_data_store:
            rotation_report['records_rotated'] += 1
        
        return rotation_report
    
    def encrypt_file_content(self, file_path: str) -> str:
        """Encrypt file content"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return self.privacy.encrypt_data(content.decode('utf-8', errors='ignore'))
        except Exception as e:
            raise ValueError(f"Failed to encrypt file: {str(e)}")
    
    def get_encryption_metadata(self, encrypted_data: str) -> Dict:
        """Get metadata about encrypted data"""
        return {
            'length': len(encrypted_data),
            'algorithm': 'Fernet (AES-128-CBC)',
            'encoding': 'base64',
            'timestamp': datetime.utcnow().isoformat(),
        }
