import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import dotenv
from cryptography.fernet import Fernet
import base64

class ConfigManager:
    """Configuration manager for FlavorSnap application"""
    
    def __init__(self, env: Optional[str] = None):
        self.env = env or os.getenv('NODE_ENV', 'development')
        self.config_dir = Path(__file__).parent / 'environments'
        self.config = self._load_config()
        self._setup_logging()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration based on environment"""
        config_file = self.config_dir / f'{self.env}.json'
        
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                return self._replace_env_vars(config)
            else:
                logging.warning(f"Config file not found for environment: {self.env}")
                return self._get_default_config()
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return self._get_default_config()
    
    def _replace_env_vars(self, obj: Any) -> Any:
        """Replace environment variables in configuration"""
        if isinstance(obj, str):
            return os.path.expandvars(obj)
        elif isinstance(obj, dict):
            return {k: self._replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_env_vars(item) for item in obj]
        return obj
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'app': {
                'name': 'FlavorSnap',
                'version': '0.1.0',
                'environment': 'development',
                'debug': True,
                'hot_reload': True
            },
            'ml': {
                'model_path': 'models/best_model.pth',
                'classes_path': 'food_classes.txt',
                'confidence_threshold': 0.7
            },
            'upload': {
                'max_file_size': 10485760,
                'upload_dir': 'uploads',
                'allowed_types': ['jpg', 'jpeg', 'png', 'gif'],
                'temp_dir': 'temp'
            },
            'logging': {
                'level': 'debug',
                'format': 'dev',
                'colorize': True,
                'timestamp': True
            },
            'features': {
                'ml_classification': True,
                'blockchain_integration': True,
                'analytics': False,
                'cache_enabled': False
            }
        }
    
    def _setup_logging(self):
        """Setup logging based on configuration"""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO').upper())
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self.get(f'features.{feature}', False)
    
    def get_env_var(self, key: str, default: str = '') -> str:
        """Get environment variable"""
        return os.getenv(key, default)

class SecretsManager:
    """Secrets management for FlavorSnap application"""
    
    def __init__(self):
        self.encryption_key = self._get_or_create_key()
        self.cipher_suite = Fernet(self.encryption_key)
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key"""
        key = os.getenv('ENCRYPTION_KEY')
        if key:
            return base64.urlsafe_b64decode(key.encode())
        
        if os.getenv('NODE_ENV') == 'production':
            raise ValueError("ENCRYPTION_KEY must be set in production")
        
        # Generate key for development
        logging.warning("No ENCRYPTION_KEY provided. Using generated key for development only.")
        return Fernet.generate_key()
    
    def encrypt(self, text: str) -> str:
        """Encrypt text"""
        try:
            encrypted = self.cipher_suite.encrypt(text.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logging.error(f"Encryption error: {e}")
            raise
    
    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt text"""
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted = self.cipher_suite.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logging.error(f"Decryption error: {e}")
            raise
    
    def hash_text(self, text: str) -> str:
        """Hash text using SHA-256"""
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()
    
    def generate_token(self, length: int = 32) -> str:
        """Generate secure token"""
        import secrets
        return secrets.token_urlsafe(length)
    
    def get_secure_env_var(self, key: str) -> Optional[str]:
        """Get encrypted environment variable"""
        value = os.getenv(key)
        if not value:
            return None
        
        # Check if value is encrypted (starts with 'enc:')
        if value.startswith('enc:'):
            try:
                return self.decrypt(value[4:])
            except Exception as e:
                logging.error(f"Failed to decrypt {key}: {e}")
                return None
        
        return value
    
    def validate_required_secrets(self, secrets: list) -> dict:
        """Validate required secrets"""
        missing = []
        for secret in secrets:
            value = self.get_secure_env_var(secret)
            if not value or not value.strip():
                missing.append(secret)
        
        return {
            'valid': len(missing) == 0,
            'missing': missing
        }
    
    def validate_environment_secrets(self) -> dict:
        """Validate environment-specific secrets"""
        errors = []
        env = os.getenv('NODE_ENV', 'development')
        
        # Common secrets
        common_secrets = ['JWT_SECRET']
        common_validation = self.validate_required_secrets(common_secrets)
        if not common_validation['valid']:
            errors.append(f"Missing common secrets: {', '.join(common_validation['missing'])}")
        
        # Environment-specific secrets
        if env == 'production':
            prod_secrets = ['ENCRYPTION_KEY', 'DATABASE_URL']
            prod_validation = self.validate_required_secrets(prod_secrets)
            if not prod_validation['valid']:
                errors.append(f"Missing production secrets: {', '.join(prod_validation['missing'])}")
        
        elif env == 'staging':
            staging_secrets = ['DATABASE_URL']
            staging_validation = self.validate_required_secrets(staging_secrets)
            if not staging_validation['valid']:
                errors.append(f"Missing staging secrets: {', '.join(staging_validation['missing'])}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

# Global instances
config_manager = ConfigManager()
secrets_manager = SecretsManager()

# Convenience functions
def get_config(key: str, default: Any = None) -> Any:
    return config_manager.get(key, default)

def is_feature_enabled(feature: str) -> bool:
    return config_manager.is_feature_enabled(feature)

def get_env_var(key: str, default: str = '') -> str:
    return config_manager.get_env_var(key, default)

def encrypt_text(text: str) -> str:
    return secrets_manager.encrypt(text)

def decrypt_text(encrypted_text: str) -> str:
    return secrets_manager.decrypt(encrypted_text)

def hash_text(text: str) -> str:
    return secrets_manager.hash_text(text)

def generate_token(length: int = 32) -> str:
    return secrets_manager.generate_token(length)

def get_secure_env_var(key: str) -> Optional[str]:
    return secrets_manager.get_secure_env_var(key)
