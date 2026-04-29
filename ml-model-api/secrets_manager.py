#!/usr/bin/env python3
"""
Advanced Secrets Manager for FlavorSnap
Implements comprehensive secrets management with encryption, rotation, and audit logging
"""

import os
import json
import logging
import hashlib
import secrets
import base64
import time
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import prometheus_client as prom
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import boto3
from botocore.exceptions import ClientError
import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecretType(Enum):
    PASSWORD = "password"
    API_KEY = "api_key"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    SSH_KEY = "ssh_key"
    DATABASE_URL = "database_url"
    ENCRYPTION_KEY = "encryption_key"
    CUSTOM = "custom"

class SecretStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING_ROTATION = "pending_rotation"

class RotationPolicy(Enum):
    NEVER = "never"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"

@dataclass
class SecretMetadata:
    """Secret metadata"""
    name: str
    type: SecretType
    description: str
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    rotation_policy: RotationPolicy
    rotation_interval_days: int
    last_rotated: Optional[datetime]
    next_rotation: Optional[datetime]
    status: SecretStatus
    version: int
    tags: List[str]
    owner: str
    environment: str

@dataclass
class SecretValue:
    """Encrypted secret value"""
    encrypted_value: str
    encryption_algorithm: str
    salt: str
    iv: str
    checksum: str
    created_at: datetime

@dataclass
class SecretAuditEvent:
    """Secret audit event"""
    timestamp: datetime
    action: str
    secret_name: str
    user: str
    ip_address: str
    success: bool
    details: str

class PrometheusMetrics:
    """Prometheus metrics for secrets management"""
    
    def __init__(self):
        self.secrets_total = prom.Gauge(
            'secrets_total',
            'Total number of secrets',
            ['environment', 'status', 'type']
        )
        
        self.secret_operations_total = prom.Counter(
            'secret_operations_total',
            'Total number of secret operations',
            ['operation', 'environment', 'success']
        )
        
        self.secret_rotation_total = prom.Counter(
            'secret_rotations_total',
            'Total number of secret rotations',
            ['environment', 'success']
        )
        
        self.secret_access_total = prom.Counter(
            'secret_access_total',
            'Total number of secret accesses',
            ['environment', 'secret_type']
        )
        
        self.secret_expiration_days = prom.Gauge(
            'secret_expiration_days',
            'Days until secret expiration',
            ['environment', 'secret_name']
        )
        
        self.encryption_operations_total = prom.Counter(
            'encryption_operations_total',
            'Total number of encryption operations',
            ['operation', 'algorithm', 'success']
        )

class AdvancedSecretsManager:
    """Advanced secrets manager with encryption, rotation, and audit logging"""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.secrets_dir = Path(__file__).parent.parent / 'config' / 'secrets'
        self.secrets_dir.mkdir(exist_ok=True)
        
        # Storage
        self.metadata_store: Dict[str, SecretMetadata] = {}
        self.value_store: Dict[str, SecretValue] = {}
        self.audit_log: List[SecretAuditEvent] = []
        
        # Encryption
        self.master_key = self._get_or_create_master_key()
        self.encryption_backend = default_backend()
        
        # Rotation
        self.rotation_enabled = True
        self.rotation_thread = None
        self.rotation_interval = 3600  # 1 hour
        
        # Cache
        self.cache_enabled = True
        self.cache_ttl = 300  # 5 minutes
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        
        # Redis for distributed caching (optional)
        self.redis_client = None
        self._setup_redis()
        
        # AWS Secrets Manager integration (optional)
        self.aws_secrets_manager = None
        self._setup_aws_secrets_manager()
        
        # Metrics
        self.metrics = PrometheusMetrics()
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Load existing secrets
        self._load_secrets()
        
        # Start rotation thread
        self._start_rotation_thread()
        
        logger.info(f"Advanced secrets manager initialized for environment: {environment}")
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        key_file = self.secrets_dir / '.master_key'
        
        # Try to get from environment first
        key_env = os.getenv('MASTER_ENCRYPTION_KEY')
        if key_env:
            return base64.urlsafe_b64decode(key_env.encode())
        
        # Try to load from file
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        
        # Generate new key for development/staging
        if self.environment in ['development', 'staging']:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            logger.warning("Generated new master key for development/staging")
            return key
        
        # Production requires explicit key
        raise ValueError("MASTER_ENCRYPTION_KEY must be set in production")
    
    def _setup_redis(self):
        """Setup Redis for distributed caching"""
        try:
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_password = os.getenv('REDIS_PASSWORD')
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=False,
                socket_timeout=5
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established for secrets caching")
            
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def _setup_aws_secrets_manager(self):
        """Setup AWS Secrets Manager integration"""
        try:
            if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
                self.aws_secrets_manager = boto3.client('secretsmanager')
                logger.info("AWS Secrets Manager integration enabled")
        except Exception as e:
            logger.warning(f"AWS Secrets Manager setup failed: {e}")
    
    def _load_secrets(self):
        """Load existing secrets from storage"""
        try:
            # Load metadata
            metadata_file = self.secrets_dir / 'metadata.json'
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata_data = json.load(f)
                
                for name, data in metadata_data.items():
                    # Convert datetime strings
                    for field in ['created_at', 'updated_at', 'expires_at', 'last_rotated', 'next_rotation']:
                        if data.get(field):
                            data[field] = datetime.fromisoformat(data[field])
                    
                    # Convert enums
                    data['type'] = SecretType(data['type'])
                    data['rotation_policy'] = RotationPolicy(data['rotation_policy'])
                    data['status'] = SecretStatus(data['status'])
                    
                    self.metadata_store[name] = SecretMetadata(**data)
            
            # Load values
            values_file = self.secrets_dir / 'values.json'
            if values_file.exists():
                with open(values_file, 'r') as f:
                    values_data = json.load(f)
                
                for name, data in values_data.items():
                    # Convert datetime strings
                    if data.get('created_at'):
                        data['created_at'] = datetime.fromisoformat(data['created_at'])
                    
                    self.value_store[name] = SecretValue(**data)
            
            # Update metrics
            self._update_metrics()
            
            logger.info(f"Loaded {len(self.metadata_store)} secrets from storage")
            
        except Exception as e:
            logger.error(f"Failed to load secrets: {e}")
    
    def _save_secrets(self):
        """Save secrets to storage"""
        try:
            # Save metadata
            metadata_file = self.secrets_dir / 'metadata.json'
            metadata_data = {}
            for name, metadata in self.metadata_store.items():
                data = asdict(metadata)
                # Convert datetime to string
                for field in ['created_at', 'updated_at', 'expires_at', 'last_rotated', 'next_rotation']:
                    if data.get(field):
                        data[field] = data[field].isoformat()
                # Convert enums to string
                data['type'] = metadata.type.value
                data['rotation_policy'] = metadata.rotation_policy.value
                data['status'] = metadata.status.value
                metadata_data[name] = data
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata_data, f, indent=2)
            
            # Save values
            values_file = self.secrets_dir / 'values.json'
            values_data = {}
            for name, value in self.value_store.items():
                data = asdict(value)
                # Convert datetime to string
                if data.get('created_at'):
                    data['created_at'] = data['created_at'].isoformat()
                values_data[name] = data
            
            with open(values_file, 'w') as f:
                json.dump(values_data, f, indent=2)
            
            # Set restrictive permissions
            os.chmod(metadata_file, 0o600)
            os.chmod(values_file, 0o600)
            
            logger.info("Secrets saved to storage")
            
        except Exception as e:
            logger.error(f"Failed to save secrets: {e}")
            raise
    
    def _encrypt_value(self, value: str) -> SecretValue:
        """Encrypt secret value"""
        try:
            # Generate salt and IV
            salt = os.urandom(16)
            iv = os.urandom(16)
            
            # Derive key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=self.encryption_backend
            )
            key = kdf.derive(self.master_key)
            
            # Encrypt
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.encryption_backend)
            encryptor = cipher.encryptor()
            
            # Pad the value
            padded_value = self._pad_value(value.encode())
            encrypted_value = encryptor.update(padded_value) + encryptor.finalize()
            
            # Calculate checksum
            checksum = hashlib.sha256(encrypted_value + salt + iv).hexdigest()
            
            secret_value = SecretValue(
                encrypted_value=base64.urlsafe_b64encode(encrypted_value).decode(),
                encryption_algorithm="AES-256-CBC",
                salt=base64.urlsafe_b64encode(salt).decode(),
                iv=base64.urlsafe_b64encode(iv).decode(),
                checksum=checksum,
                created_at=datetime.utcnow()
            )
            
            self.metrics.encryption_operations_total.labels(
                operation='encrypt',
                algorithm='AES-256-CBC',
                success=True
            ).inc()
            
            return secret_value
            
        except Exception as e:
            self.metrics.encryption_operations_total.labels(
                operation='encrypt',
                algorithm='AES-256-CBC',
                success=False
            ).inc()
            logger.error(f"Encryption failed: {e}")
            raise
    
    def _decrypt_value(self, secret_value: SecretValue) -> str:
        """Decrypt secret value"""
        try:
            # Decode base64 values
            encrypted_value = base64.urlsafe_b64decode(secret_value.encrypted_value.encode())
            salt = base64.urlsafe_b64decode(secret_value.salt.encode())
            iv = base64.urlsafe_b64decode(secret_value.iv.encode())
            
            # Derive key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=self.encryption_backend
            )
            key = kdf.derive(self.master_key)
            
            # Decrypt
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.encryption_backend)
            decryptor = cipher.decryptor()
            padded_value = decryptor.update(encrypted_value) + decryptor.finalize()
            
            # Unpad
            value = self._unpad_value(padded_value).decode()
            
            # Verify checksum
            calculated_checksum = hashlib.sha256(encrypted_value + salt + iv).hexdigest()
            if calculated_checksum != secret_value.checksum:
                raise ValueError("Checksum verification failed")
            
            self.metrics.encryption_operations_total.labels(
                operation='decrypt',
                algorithm='AES-256-CBC',
                success=True
            ).inc()
            
            return value
            
        except Exception as e:
            self.metrics.encryption_operations_total.labels(
                operation='decrypt',
                algorithm='AES-256-CBC',
                success=False
            ).inc()
            logger.error(f"Decryption failed: {e}")
            raise
    
    def _pad_value(self, value: bytes) -> bytes:
        """Pad value for AES encryption"""
        block_size = 16
        padding_length = block_size - (len(value) % block_size)
        padding = bytes([padding_length] * padding_length)
        return value + padding
    
    def _unpad_value(self, padded_value: bytes) -> bytes:
        """Unpad value after AES decryption"""
        padding_length = padded_value[-1]
        return padded_value[:-padding_length]
    
    def _log_audit_event(self, action: str, secret_name: str, user: str, 
                        ip_address: str, success: bool, details: str = ""):
        """Log audit event"""
        event = SecretAuditEvent(
            timestamp=datetime.utcnow(),
            action=action,
            secret_name=secret_name,
            user=user,
            ip_address=ip_address,
            success=success,
            details=details
        )
        
        self.audit_log.append(event)
        
        # Keep audit log size manageable
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-5000:]
        
        # Log to system logger
        level = logging.INFO if success else logging.WARNING
        logger.log(level, f"Secret audit: {action} on {secret_name} by {user} - {details}")
    
    def _update_metrics(self):
        """Update Prometheus metrics"""
        # Count secrets by status and type
        status_counts = {}
        type_counts = {}
        
        for metadata in self.metadata_store.values():
            status = metadata.status.value
            secret_type = metadata.type.value
            
            status_counts[status] = status_counts.get(status, 0) + 1
            type_counts[secret_type] = type_counts.get(secret_type, 0) + 1
        
        # Update metrics
        for status, count in status_counts.items():
            self.metrics.secrets_total.labels(
                environment=self.environment,
                status=status,
                type='all'
            ).set(count)
        
        for secret_type, count in type_counts.items():
            self.metrics.secrets_total.labels(
                environment=self.environment,
                status='all',
                type=secret_type
            ).set(count)
        
        # Update expiration metrics
        for name, metadata in self.metadata_store.items():
            if metadata.expires_at:
                days_until_expiry = (metadata.expires_at - datetime.utcnow()).days
                self.metrics.secret_expiration_days.labels(
                    environment=self.environment,
                    secret_name=name
                ).set(days_until_expiry)
    
    def _start_rotation_thread(self):
        """Start automatic rotation thread"""
        if self.rotation_enabled:
            self.rotation_thread = threading.Thread(target=self._rotation_worker, daemon=True)
            self.rotation_thread.start()
            logger.info("Secret rotation thread started")
    
    def _rotation_worker(self):
        """Worker thread for automatic rotation"""
        while True:
            try:
                self._check_rotations()
                time.sleep(self.rotation_interval)
            except Exception as e:
                logger.error(f"Rotation worker error: {e}")
                time.sleep(60)  # Wait before retrying
    
    def _check_rotations(self):
        """Check for secrets that need rotation"""
        now = datetime.utcnow()
        
        for name, metadata in self.metadata_store.items():
            if (metadata.rotation_policy != RotationPolicy.NEVER and
                metadata.next_rotation and
                now >= metadata.next_rotation):
                
                try:
                    self.rotate_secret(name, "automatic_rotation")
                except Exception as e:
                    logger.error(f"Failed to rotate secret {name}: {e}")
    
    def create_secret(self, name: str, value: str, secret_type: SecretType,
                     description: str = "", owner: str = "system",
                     rotation_policy: RotationPolicy = RotationPolicy.MONTHLY,
                     rotation_interval_days: int = 30,
                     expires_at: Optional[datetime] = None,
                     tags: List[str] = None) -> bool:
        """Create a new secret"""
        with self._lock:
            try:
                if name in self.metadata_store:
                    raise ValueError(f"Secret {name} already exists")
                
                # Encrypt value
                secret_value = self._encrypt_value(value)
                
                # Create metadata
                now = datetime.utcnow()
                next_rotation = self._calculate_next_rotation(now, rotation_policy, rotation_interval_days)
                
                metadata = SecretMetadata(
                    name=name,
                    type=secret_type,
                    description=description,
                    created_at=now,
                    updated_at=now,
                    expires_at=expires_at,
                    rotation_policy=rotation_policy,
                    rotation_interval_days=rotation_interval_days,
                    last_rotated=now,
                    next_rotation=next_rotation,
                    status=SecretStatus.ACTIVE,
                    version=1,
                    tags=tags or [],
                    owner=owner,
                    environment=self.environment
                )
                
                # Store
                self.metadata_store[name] = metadata
                self.value_store[name] = secret_value
                
                # Save to storage
                self._save_secrets()
                
                # Update metrics
                self.metrics.secret_operations_total.labels(
                    operation='create',
                    environment=self.environment,
                    success=True
                ).inc()
                self._update_metrics()
                
                # Log audit event
                self._log_audit_event('create', name, owner, '127.0.0.1', True)
                
                # Sync to AWS if enabled
                if self.aws_secrets_manager:
                    self._sync_to_aws(name, value)
                
                logger.info(f"Secret {name} created successfully")
                return True
                
            except Exception as e:
                self.metrics.secret_operations_total.labels(
                    operation='create',
                    environment=self.environment,
                    success=False
                ).inc()
                self._log_audit_event('create', name, owner, '127.0.0.1', False, str(e))
                logger.error(f"Failed to create secret {name}: {e}")
                return False
    
    def get_secret(self, name: str, use_cache: bool = True) -> Optional[str]:
        """Get secret value"""
        with self._lock:
            try:
                # Check cache first
                if use_cache and self.cache_enabled:
                    cached_value = self._get_from_cache(name)
                    if cached_value is not None:
                        self.metrics.secret_access_total.labels(
                            environment=self.environment,
                            secret_type=self.metadata_store.get(name, SecretType.CUSTOM).type.value
                        ).inc()
                        return cached_value
                
                # Check if secret exists
                if name not in self.metadata_store:
                    return None
                
                metadata = self.metadata_store[name]
                
                # Check if secret is active
                if metadata.status != SecretStatus.ACTIVE:
                    return None
                
                # Check if secret is expired
                if metadata.expires_at and datetime.utcnow() > metadata.expires_at:
                    metadata.status = SecretStatus.EXPIRED
                    self._save_secrets()
                    return None
                
                # Decrypt value
                secret_value = self.value_store[name]
                value = self._decrypt_value(secret_value)
                
                # Cache the value
                if self.cache_enabled:
                    self._set_cache(name, value)
                
                # Update metrics
                self.metrics.secret_access_total.labels(
                    environment=self.environment,
                    secret_type=metadata.type.value
                ).inc()
                
                # Log audit event
                self._log_audit_event('access', name, 'system', '127.0.0.1', True)
                
                return value
                
            except Exception as e:
                self._log_audit_event('access', name, 'system', '127.0.0.1', False, str(e))
                logger.error(f"Failed to get secret {name}: {e}")
                return None
    
    def update_secret(self, name: str, new_value: str, updated_by: str = "system") -> bool:
        """Update secret value"""
        with self._lock:
            try:
                if name not in self.metadata_store:
                    raise ValueError(f"Secret {name} not found")
                
                # Encrypt new value
                secret_value = self._encrypt_value(new_value)
                
                # Update metadata
                metadata = self.metadata_store[name]
                metadata.updated_at = datetime.utcnow()
                metadata.version += 1
                metadata.last_rotated = datetime.utcnow()
                metadata.next_rotation = self._calculate_next_rotation(
                    metadata.last_rotated,
                    metadata.rotation_policy,
                    metadata.rotation_interval_days
                )
                
                # Update value
                self.value_store[name] = secret_value
                
                # Save to storage
                self._save_secrets()
                
                # Clear cache
                if name in self.cache:
                    del self.cache[name]
                
                # Update metrics
                self.metrics.secret_operations_total.labels(
                    operation='update',
                    environment=self.environment,
                    success=True
                ).inc()
                self._update_metrics()
                
                # Log audit event
                self._log_audit_event('update', name, updated_by, '127.0.0.1', True)
                
                # Sync to AWS if enabled
                if self.aws_secrets_manager:
                    self._sync_to_aws(name, new_value)
                
                logger.info(f"Secret {name} updated successfully")
                return True
                
            except Exception as e:
                self.metrics.secret_operations_total.labels(
                    operation='update',
                    environment=self.environment,
                    success=False
                ).inc()
                self._log_audit_event('update', name, updated_by, '127.0.0.1', False, str(e))
                logger.error(f"Failed to update secret {name}: {e}")
                return False
    
    def delete_secret(self, name: str, deleted_by: str = "system") -> bool:
        """Delete secret"""
        with self._lock:
            try:
                if name not in self.metadata_store:
                    raise ValueError(f"Secret {name} not found")
                
                # Remove from stores
                del self.metadata_store[name]
                del self.value_store[name]
                
                # Clear cache
                if name in self.cache:
                    del self.cache[name]
                
                # Save to storage
                self._save_secrets()
                
                # Update metrics
                self.metrics.secret_operations_total.labels(
                    operation='delete',
                    environment=self.environment,
                    success=True
                ).inc()
                self._update_metrics()
                
                # Log audit event
                self._log_audit_event('delete', name, deleted_by, '127.0.0.1', True)
                
                # Delete from AWS if enabled
                if self.aws_secrets_manager:
                    self._delete_from_aws(name)
                
                logger.info(f"Secret {name} deleted successfully")
                return True
                
            except Exception as e:
                self.metrics.secret_operations_total.labels(
                    operation='delete',
                    environment=self.environment,
                    success=False
                ).inc()
                self._log_audit_event('delete', name, deleted_by, '127.0.0.1', False, str(e))
                logger.error(f"Failed to delete secret {name}: {e}")
                return False
    
    def rotate_secret(self, name: str, rotated_by: str = "system") -> bool:
        """Rotate secret (generate new value)"""
        with self._lock:
            try:
                if name not in self.metadata_store:
                    raise ValueError(f"Secret {name} not found")
                
                metadata = self.metadata_store[name]
                
                # Generate new value based on type
                new_value = self._generate_secret_value(metadata.type)
                
                # Update secret
                success = self.update_secret(name, new_value, rotated_by)
                
                if success:
                    # Update rotation metrics
                    self.metrics.secret_rotation_total.labels(
                        environment=self.environment,
                        success=True
                    ).inc()
                    
                    logger.info(f"Secret {name} rotated successfully")
                    return True
                else:
                    self.metrics.secret_rotation_total.labels(
                        environment=self.environment,
                        success=False
                    ).inc()
                    return False
                
            except Exception as e:
                self.metrics.secret_rotation_total.labels(
                    environment=self.environment,
                    success=False
                ).inc()
                logger.error(f"Failed to rotate secret {name}: {e}")
                return False
    
    def _generate_secret_value(self, secret_type: SecretType) -> str:
        """Generate a new secret value based on type"""
        if secret_type == SecretType.PASSWORD:
            # Generate strong password
            chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
            return ''.join(secrets.choice(chars) for _ in range(32))
        
        elif secret_type == SecretType.API_KEY:
            # Generate API key
            return secrets.token_urlsafe(32)
        
        elif secret_type == SecretType.TOKEN:
            # Generate JWT-like token
            header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip('=')
            payload = base64.urlsafe_b64encode(b'{"sub":"user","iat":1234567890}').decode().rstrip('=')
            signature = secrets.token_urlsafe(32)
            return f"{header}.{payload}.{signature}"
        
        elif secret_type == SecretType.ENCRYPTION_KEY:
            # Generate encryption key
            return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        
        else:
            # Default to random token
            return secrets.token_urlsafe(32)
    
    def _calculate_next_rotation(self, last_rotation: datetime, 
                               policy: RotationPolicy, interval_days: int) -> Optional[datetime]:
        """Calculate next rotation date"""
        if policy == RotationPolicy.NEVER:
            return None
        
        if policy == RotationPolicy.CUSTOM:
            return last_rotation + timedelta(days=interval_days)
        
        # Predefined intervals
        intervals = {
            RotationPolicy.DAILY: 1,
            RotationPolicy.WEEKLY: 7,
            RotationPolicy.MONTHLY: 30,
            RotationPolicy.QUARTERLY: 90,
            RotationPolicy.YEARLY: 365
        }
        
        days = intervals.get(policy, 30)
        return last_rotation + timedelta(days=days)
    
    def _get_from_cache(self, name: str) -> Optional[str]:
        """Get value from cache"""
        if not self.cache_enabled:
            return None
        
        # Check local cache
        if name in self.cache:
            value, timestamp = self.cache[name]
            if datetime.utcnow() - timestamp < timedelta(seconds=self.cache_ttl):
                return value
            else:
                del self.cache[name]
        
        # Check Redis cache
        if self.redis_client:
            try:
                cached_value = self.redis_client.get(f"secret:{name}")
                if cached_value:
                    return cached_value.decode()
            except Exception as e:
                logger.warning(f"Redis cache error: {e}")
        
        return None
    
    def _set_cache(self, name: str, value: str):
        """Set value in cache"""
        if not self.cache_enabled:
            return
        
        # Set local cache
        self.cache[name] = (value, datetime.utcnow())
        
        # Set Redis cache
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"secret:{name}",
                    self.cache_ttl,
                    value.encode()
                )
            except Exception as e:
                logger.warning(f"Redis cache error: {e}")
    
    def _sync_to_aws(self, name: str, value: str):
        """Sync secret to AWS Secrets Manager"""
        if not self.aws_secrets_manager:
            return
        
        try:
            secret_string = json.dumps({
                'value': value,
                'environment': self.environment,
                'updated_at': datetime.utcnow().isoformat()
            })
            
            self.aws_secrets_manager.create_secret(
                Name=f"flavorsnap/{self.environment}/{name}",
                SecretString=secret_string,
                Description=f"FlavorSnap secret: {name}"
            )
            
            logger.info(f"Secret {name} synced to AWS Secrets Manager")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceExistsException':
                # Update existing secret
                try:
                    self.aws_secrets_manager.update_secret(
                        SecretId=f"flavorsnap/{self.environment}/{name}",
                        SecretString=secret_string
                    )
                    logger.info(f"Secret {name} updated in AWS Secrets Manager")
                except Exception as update_error:
                    logger.error(f"Failed to update secret in AWS: {update_error}")
            else:
                logger.error(f"Failed to sync secret to AWS: {e}")
    
    def _delete_from_aws(self, name: str):
        """Delete secret from AWS Secrets Manager"""
        if not self.aws_secrets_manager:
            return
        
        try:
            self.aws_secrets_manager.delete_secret(
                SecretId=f"flavorsnap/{self.environment}/{name}",
                ForceDeleteWithoutRecovery=True
            )
            logger.info(f"Secret {name} deleted from AWS Secrets Manager")
        except Exception as e:
            logger.error(f"Failed to delete secret from AWS: {e}")
    
    def list_secrets(self, include_values: bool = False) -> Dict[str, Dict[str, Any]]:
        """List all secrets"""
        result = {}
        
        for name, metadata in self.metadata_store.items():
            secret_info = asdict(metadata)
            # Convert enums to strings
            secret_info['type'] = metadata.type.value
            secret_info['rotation_policy'] = metadata.rotation_policy.value
            secret_info['status'] = metadata.status.value
            
            # Convert datetime to string
            for field in ['created_at', 'updated_at', 'expires_at', 'last_rotated', 'next_rotation']:
                if secret_info.get(field):
                    secret_info[field] = secret_info[field].isoformat()
            
            # Add value if requested
            if include_values:
                try:
                    secret_info['value'] = self.get_secret(name)
                except Exception:
                    secret_info['value'] = '***ACCESS_DENIED***'
            
            result[name] = secret_info
        
        return result
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit log"""
        events = self.audit_log[-limit:] if limit > 0 else self.audit_log
        
        result = []
        for event in events:
            event_data = asdict(event)
            event_data['timestamp'] = event.timestamp.isoformat()
            result.append(event_data)
        
        return result
    
    def get_expiring_secrets(self, days: int = 30) -> List[str]:
        """Get secrets that will expire within specified days"""
        expiring = []
        cutoff = datetime.utcnow() + timedelta(days=days)
        
        for name, metadata in self.metadata_store.items():
            if (metadata.expires_at and 
                metadata.status == SecretStatus.ACTIVE and
                metadata.expires_at <= cutoff):
                expiring.append(name)
        
        return expiring
    
    def get_rotation_status(self) -> Dict[str, Any]:
        """Get rotation status"""
        now = datetime.utcnow()
        pending_rotation = []
        overdue_rotation = []
        
        for name, metadata in self.metadata_store.items():
            if metadata.next_rotation:
                if now >= metadata.next_rotation:
                    overdue_rotation.append(name)
                elif now >= metadata.next_rotation - timedelta(days=7):
                    pending_rotation.append(name)
        
        return {
            'rotation_enabled': self.rotation_enabled,
            'pending_rotation': pending_rotation,
            'overdue_rotation': overdue_rotation,
            'total_secrets': len(self.metadata_store),
            'secrets_with_rotation': len([
                m for m in self.metadata_store.values() 
                if m.rotation_policy != RotationPolicy.NEVER
            ])
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        checks = {
            'storage_accessible': True,
            'encryption_working': True,
            'cache_working': True,
            'rotation_enabled': self.rotation_enabled,
            'aws_sync_working': True,
            'redis_connected': True
        }
        
        # Test storage
        try:
            test_file = self.secrets_dir / '.health_check'
            test_file.write_text('test')
            test_file.unlink()
        except Exception:
            checks['storage_accessible'] = False
        
        # Test encryption
        try:
            test_value = "test_value"
            encrypted = self._encrypt_value(test_value)
            decrypted = self._decrypt_value(encrypted)
            if decrypted != test_value:
                checks['encryption_working'] = False
        except Exception:
            checks['encryption_working'] = False
        
        # Test cache
        if self.cache_enabled:
            try:
                self._set_cache('health_check', 'test')
                cached = self._get_from_cache('health_check')
                if cached != 'test':
                    checks['cache_working'] = False
                if 'health_check' in self.cache:
                    del self.cache['health_check']
            except Exception:
                checks['cache_working'] = False
        
        # Test Redis
        if self.redis_client:
            try:
                self.redis_client.ping()
            except Exception:
                checks['redis_connected'] = False
        else:
            checks['redis_connected'] = False
        
        # Test AWS
        if self.aws_secrets_manager:
            try:
                self.aws_secrets_manager.list_secrets(MaxResults=1)
            except Exception:
                checks['aws_sync_working'] = False
        else:
            checks['aws_sync_working'] = False
        
        # Overall health
        checks['healthy'] = all(checks.values())
        checks['issues'] = [k for k, v in checks.items() if not v and k != 'healthy']
        
        return checks

# Global instance
secrets_manager = AdvancedSecretsManager()

# Convenience functions
def get_secret(name: str, use_cache: bool = True) -> Optional[str]:
    """Get secret value"""
    return secrets_manager.get_secret(name, use_cache)

def create_secret(name: str, value: str, secret_type: SecretType, **kwargs) -> bool:
    """Create new secret"""
    return secrets_manager.create_secret(name, value, secret_type, **kwargs)

def update_secret(name: str, new_value: str, updated_by: str = "system") -> bool:
    """Update secret"""
    return secrets_manager.update_secret(name, new_value, updated_by)

def delete_secret(name: str, deleted_by: str = "system") -> bool:
    """Delete secret"""
    return secrets_manager.delete_secret(name, deleted_by)

def rotate_secret(name: str, rotated_by: str = "system") -> bool:
    """Rotate secret"""
    return secrets_manager.rotate_secret(name, rotated_by)

# Example usage
if __name__ == "__main__":
    # Test secrets manager
    print("Testing Advanced Secrets Manager")
    
    # Create a test secret
    success = create_secret(
        name="test_api_key",
        value="sk-test-1234567890",
        secret_type=SecretType.API_KEY,
        description="Test API key",
        owner="test_user"
    )
    print(f"Secret created: {success}")
    
    # Get the secret
    value = get_secret("test_api_key")
    print(f"Secret value: {value}")
    
    # List secrets
    secrets = secrets_manager.list_secrets()
    print(f"Total secrets: {len(secrets)}")
    
    # Health check
    health = secrets_manager.health_check()
    print(f"Health check: {health}")
    
    # Cleanup
    delete_secret("test_api_key")
    print("Test secret deleted")
