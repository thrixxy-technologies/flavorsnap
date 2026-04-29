"""
Comprehensive Configuration Management for FlavorSnap
Handles environment-specific configs, validation, hot reload, versioning, security, monitoring, and backup
"""

import os
import yaml
import json
import threading
import time
import hashlib
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import cryptography.fernet
from dataclasses import dataclass, asdict
import copy

logger = logging.getLogger(__name__)

@dataclass
class ConfigVersion:
    """Configuration version metadata"""
    version: str
    timestamp: datetime
    checksum: str
    author: str
    description: str
    environment: str

class ConfigSecurity:
    """Handles encryption and decryption of sensitive configuration data"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        self.encryption_key = encryption_key or os.getenv('CONFIG_ENCRYPTION_KEY')
        if self.encryption_key:
            self.cipher_suite = cryptography.fernet.Fernet(self.encryption_key.encode())
        else:
            self.cipher_suite = None
            logger.warning("No encryption key provided, sensitive data will be stored in plain text")
    
    def encrypt_value(self, value: str) -> str:
        """Encrypt a configuration value"""
        if not self.cipher_suite:
            return value
        return self.cipher_suite.encrypt(value.encode()).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a configuration value"""
        if not self.cipher_suite:
            return encrypted_value
        try:
            return self.cipher_suite.decrypt(encrypted_value.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt value: {e}")
            return encrypted_value
    
    def encrypt_sensitive_fields(self, config: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
        """Encrypt sensitive fields in configuration"""
        encrypted_config = copy.deepcopy(config)
        for field_path in sensitive_fields:
            self._encrypt_nested_field(encrypted_config, field_path.split('.'))
        return encrypted_config
    
    def _encrypt_nested_field(self, config: Dict[str, Any], field_parts: List[str]):
        """Recursively encrypt nested field"""
        if len(field_parts) == 1:
            field = field_parts[0]
            if field in config and isinstance(config[field], str):
                config[field] = self.encrypt_value(config[field])
        else:
            current_field = field_parts[0]
            if current_field in config and isinstance(config[current_field], dict):
                self._encrypt_nested_field(config[current_field], field_parts[1:])

class ConfigValidator:
    """Configuration validation with schema support"""
    
    def __init__(self):
        self.schemas = {}
        self._load_default_schemas()
    
    def _load_default_schemas(self):
        """Load default validation schemas"""
        self.schemas = {
            'app': {
                'required': ['name', 'version', 'debug', 'host', 'port'],
                'types': {
                    'name': str,
                    'version': str,
                    'debug': bool,
                    'host': str,
                    'port': int,
                    'secret_key': str
                },
                'ranges': {
                    'port': (1, 65535)
                }
            },
            'database': {
                'required': ['type', 'host', 'port', 'name', 'user', 'password'],
                'types': {
                    'type': str,
                    'host': str,
                    'port': int,
                    'name': str,
                    'user': str,
                    'password': str,
                    'pool_size': int,
                    'max_overflow': int,
                    'pool_timeout': int,
                    'pool_recycle': int
                },
                'ranges': {
                    'port': (1, 65535),
                    'pool_size': (1, 100),
                    'max_overflow': (0, 100),
                    'pool_timeout': (1, 300),
                    'pool_recycle': (60, 86400)
                }
            },
            'logging': {
                'required': ['level'],
                'types': {
                    'level': str,
                    'format': str,
                    'file': str,
                    'max_bytes': int,
                    'backup_count': int,
                    'enable_console': bool
                },
                'enums': {
                    'level': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                },
                'ranges': {
                    'max_bytes': (1024, 1073741824),  # 1KB to 1GB
                    'backup_count': (1, 50)
                }
            }
        }
    
    def validate_section(self, section_name: str, config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate a configuration section"""
        errors = []
        
        if section_name not in self.schemas:
            errors.append(f"No schema found for section: {section_name}")
            return False, errors
        
        schema = self.schemas[section_name]
        
        # Check required fields
        for field in schema.get('required', []):
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Check types
        for field, expected_type in schema.get('types', {}).items():
            if field in config and not isinstance(config[field], expected_type):
                errors.append(f"Field {field} must be of type {expected_type.__name__}")
        
        # Check enums
        for field, allowed_values in schema.get('enums', {}).items():
            if field in config and config[field] not in allowed_values:
                errors.append(f"Field {field} must be one of: {allowed_values}")
        
        # Check ranges
        for field, (min_val, max_val) in schema.get('ranges', {}).items():
            if field in config:
                value = config[field]
                if not (min_val <= value <= max_val):
                    errors.append(f"Field {field} must be between {min_val} and {max_val}")
        
        return len(errors) == 0, errors
    
    def validate_all(self, config: Dict[str, Any]) -> tuple[bool, Dict[str, List[str]]]:
        """Validate entire configuration"""
        all_errors = {}
        is_valid = True
        
        for section_name in self.schemas.keys():
            if section_name in config:
                valid, errors = self.validate_section(section_name, config[section_name])
                if not valid:
                    all_errors[section_name] = errors
                    is_valid = False
        
        return is_valid, all_errors

class ConfigBackup:
    """Configuration backup and restore functionality"""
    
    def __init__(self, backup_dir: str = "./config_backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, config: Dict[str, Any], description: str = "") -> str:
        """Create a configuration backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"config_backup_{timestamp}.yaml"
        
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'description': description,
            'config': config
        }
        
        with open(backup_file, 'w') as f:
            yaml.dump(backup_data, f, default_flow_style=False)
        
        logger.info(f"Configuration backup created: {backup_file}")
        return str(backup_file)
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        backups = []
        
        for backup_file in self.backup_dir.glob("config_backup_*.yaml"):
            try:
                with open(backup_file, 'r') as f:
                    backup_data = yaml.safe_load(f)
                    backups.append({
                        'file': str(backup_file),
                        'timestamp': backup_data.get('timestamp'),
                        'description': backup_data.get('description', '')
                    })
            except Exception as e:
                logger.error(f"Error reading backup file {backup_file}: {e}")
        
        return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
    
    def restore_backup(self, backup_file: str) -> Dict[str, Any]:
        """Restore configuration from backup"""
        with open(backup_file, 'r') as f:
            backup_data = yaml.safe_load(f)
        
        logger.info(f"Configuration restored from backup: {backup_file}")
        return backup_data['config']
    
    def cleanup_old_backups(self, days_to_keep: int = 30):
        """Clean up old backup files"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for backup_file in self.backup_dir.glob("config_backup_*.yaml"):
            try:
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_date:
                    backup_file.unlink()
                    logger.info(f"Deleted old backup: {backup_file}")
            except Exception as e:
                logger.error(f"Error deleting old backup {backup_file}: {e}")

class ConfigFileWatcher(FileSystemEventHandler):
    """File system watcher for configuration changes"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.last_modified = {}
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        if not file_path.endswith('.yaml') and not file_path.endswith('.yml'):
            return
        
        # Debounce rapid file changes
        current_time = time.time()
        if file_path in self.last_modified and current_time - self.last_modified[file_path] < 1:
            return
        
        self.last_modified[file_path] = current_time
        
        # Trigger reload after a short delay to ensure file write is complete
        threading.Timer(1.0, self.config_manager.reload_config).start()

class ConfigManager:
    """Main configuration manager with all advanced features"""
    
    def __init__(self, config_path: str = None, environment: str = None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
        self.environment = environment or os.getenv('ENVIRONMENT', 'development')
        self.config = {}
        self.versions = []
        self.callbacks = []
        self._lock = threading.Lock()
        
        # Initialize components
        self.security = ConfigSecurity()
        self.validator = ConfigValidator()
        self.backup = ConfigBackup()
        self.observer = None
        
        # Sensitive fields that need encryption
        self.sensitive_fields = [
            'app.secret_key',
            'database.password',
            'security.jwt_secret_key',
            'cache.password'
        ]
        
        self._load_config()
        self._setup_file_watcher()
    
    def _load_config(self):
        """Load and process configuration"""
        try:
            with open(self.config_path, 'r') as f:
                raw_config = yaml.safe_load(f)
            
            # Process environment-specific overrides
            self.config = self._process_environment_overrides(raw_config)
            
            # Substitute environment variables
            self.config = self._substitute_env_vars(self.config)
            
            # Decrypt sensitive fields
            self.config = self._decrypt_sensitive_fields(self.config)
            
            # Validate configuration
            is_valid, errors = self.validator.validate_all(self.config)
            if not is_valid:
                logger.error(f"Configuration validation failed: {errors}")
                raise ValueError(f"Invalid configuration: {errors}")
            
            logger.info(f"Configuration loaded successfully for environment: {self.environment}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _process_environment_overrides(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process environment-specific configuration overrides"""
        config = copy.deepcopy(base_config)
        
        # Look for environment-specific config file
        env_config_path = self.config_path.replace('.yaml', f'.{self.environment}.yaml')
        if os.path.exists(env_config_path):
            try:
                with open(env_config_path, 'r') as f:
                    env_config = yaml.safe_load(f)
                
                # Deep merge environment config
                self._deep_merge(config, env_config)
                logger.info(f"Loaded environment-specific config from: {env_config_path}")
            except Exception as e:
                logger.warning(f"Failed to load environment config: {e}")
        
        return config
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]):
        """Deep merge two dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _substitute_env_vars(self, config: Any) -> Any:
        """Recursively substitute environment variables"""
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith('${') and config.endswith('}'):
            env_var = config[2:-1]
            if ':' in env_var:
                var_name, default_value = env_var.split(':', 1)
                return os.getenv(var_name.strip(), default_value.strip())
            else:
                return os.getenv(env_var.strip(), '')
        else:
            return config
    
    def _decrypt_sensitive_fields(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in configuration"""
        for field_path in self.sensitive_fields:
            self._decrypt_nested_field(config, field_path.split('.'))
        return config
    
    def _decrypt_nested_field(self, config: Dict[str, Any], field_parts: List[str]):
        """Recursively decrypt nested field"""
        if len(field_parts) == 1:
            field = field_parts[0]
            if field in config and isinstance(config[field], str):
                config[field] = self.security.decrypt_value(config[field])
        else:
            current_field = field_parts[0]
            if current_field in config and isinstance(config[current_field], dict):
                self._decrypt_nested_field(config[current_field], field_parts[1:])
    
    def _setup_file_watcher(self):
        """Setup file system watcher for hot reload"""
        if self.observer is None:
            self.observer = Observer()
            handler = ConfigFileWatcher(self)
            config_dir = os.path.dirname(self.config_path)
            self.observer.schedule(handler, config_dir, recursive=False)
            self.observer.start()
            logger.info("Configuration file watcher started")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports dot notation)"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        return self.config.get(section, {})
    
    def reload_config(self):
        """Reload configuration from file"""
        with self._lock:
            try:
                old_config = copy.deepcopy(self.config)
                old_checksum = self._calculate_checksum(old_config)
                
                self._load_config()
                new_checksum = self._calculate_checksum(self.config)
                
                if old_checksum != new_checksum:
                    # Create version entry
                    version = ConfigVersion(
                        version=f"v{len(self.versions) + 1}",
                        timestamp=datetime.now(),
                        checksum=new_checksum,
                        author="system",
                        description="Hot reload",
                        environment=self.environment
                    )
                    self.versions.append(version)
                    
                    # Create backup
                    self.backup.create_backup(self.config, f"Auto backup before hot reload")
                    
                    # Notify callbacks
                    for callback in self.callbacks:
                        try:
                            callback(self.config, old_config)
                        except Exception as e:
                            logger.error(f"Error in config change callback: {e}")
                    
                    logger.info("Configuration reloaded successfully")
                else:
                    logger.info("Configuration unchanged, no reload needed")
                    
            except Exception as e:
                logger.error(f"Failed to reload configuration: {e}")
    
    def _calculate_checksum(self, config: Dict[str, Any]) -> str:
        """Calculate configuration checksum"""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()
    
    def add_change_callback(self, callback: Callable[[Dict[str, Any], Dict[str, Any]], None]):
        """Add callback for configuration changes"""
        self.callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable[[Dict[str, Any], Dict[str, Any]], None]):
        """Remove configuration change callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def get_version_history(self) -> List[Dict[str, Any]]:
        """Get configuration version history"""
        return [asdict(version) for version in self.versions]
    
    def get_monitoring_info(self) -> Dict[str, Any]:
        """Get configuration monitoring information"""
        return {
            'environment': self.environment,
            'config_path': self.config_path,
            'last_reload': self.versions[-1].timestamp.isoformat() if self.versions else None,
            'version_count': len(self.versions),
            'checksum': self._calculate_checksum(self.config),
            'watcher_active': self.observer.is_alive() if self.observer else False,
            'backup_count': len(self.backup.list_backups()),
            'validation_status': "valid"
        }
    
    def save_config(self, description: str = "", author: str = "system"):
        """Save current configuration with versioning"""
        with self._lock:
            try:
                # Create backup before saving
                self.backup.create_backup(self.config, f"Backup before save: {description}")
                
                # Encrypt sensitive fields for storage
                storage_config = self.security.encrypt_sensitive_fields(
                    copy.deepcopy(self.config), 
                    self.sensitive_fields
                )
                
                # Add metadata
                storage_config['_metadata'] = {
                    'version': f"v{len(self.versions) + 1}",
                    'timestamp': datetime.now().isoformat(),
                    'author': author,
                    'description': description,
                    'environment': self.environment
                }
                
                # Save to file
                with open(self.config_path, 'w') as f:
                    yaml.dump(storage_config, f, default_flow_style=False)
                
                # Create version entry
                version = ConfigVersion(
                    version=f"v{len(self.versions) + 1}",
                    timestamp=datetime.now(),
                    checksum=self._calculate_checksum(self.config),
                    author=author,
                    description=description,
                    environment=self.environment
                )
                self.versions.append(version)
                
                logger.info(f"Configuration saved: {description}")
                
            except Exception as e:
                logger.error(f"Failed to save configuration: {e}")
                raise
    
    def cleanup(self):
        """Cleanup resources"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
        logger.info("Configuration manager cleanup completed")

# Global configuration manager instance
config_manager = ConfigManager()

def get_config() -> ConfigManager:
    """Get global configuration manager instance"""
    return config_manager

def get_config_value(key: str, default: Any = None) -> Any:
    """Get configuration value by key"""
    return config_manager.get(key, default)

def get_config_section(section: str) -> Dict[str, Any]:
    """Get configuration section"""
    return config_manager.get_section(section)
