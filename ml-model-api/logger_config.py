"""
Logging Configuration Management for FlavorSnap
Handles logging setup, rotation, validation, and configuration management
"""

import os
import logging
import logging.handlers
import yaml
import threading
from typing import Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime

class LoggingConfig:
    """Logging configuration manager with rotation and validation"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
        self.config = {}
        self.loggers = {}
        self._lock = threading.Lock()
        self._load_config()
        self._setup_logging()
        
    def _load_config(self):
        """Load logging configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                full_config = yaml.safe_load(file)
                self.config = full_config.get('logging', {})
        except Exception as e:
            # Set default configuration if loading fails
            self.config = {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': './logs/app.log',
                'max_bytes': 10485760,
                'backup_count': 5,
                'enable_console': True
            }
            print(f"Warning: Failed to load logging config, using defaults: {e}")
    
    def _substitute_env_vars(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute environment variables in configuration"""
        def substitute_value(value):
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                if ':' in env_var:
                    var_name, default_value = env_var.split(':', 1)
                    return os.getenv(var_name.strip(), default_value.strip())
                else:
                    return os.getenv(env_var.strip(), '')
            return value
        
        return {k: substitute_value(v) for k, v in config_dict.items()}
    
    def validate_config(self) -> bool:
        """Validate logging configuration parameters"""
        config = self._substitute_env_vars(self.config)
        
        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if config.get('level', '').upper() not in valid_levels:
            print(f"Error: Invalid log level: {config.get('level')}")
            return False
        
        # Validate numeric values
        numeric_fields = ['max_bytes', 'backup_count']
        for field in numeric_fields:
            if field in config:
                try:
                    int(config[field])
                except ValueError:
                    print(f"Error: {field} must be a number")
                    return False
        
        return True
    
    def _setup_logging(self):
        """Setup logging configuration"""
        if not self.validate_config():
            raise ValueError("Invalid logging configuration")
        
        config = self._substitute_env_vars(self.config)
        
        # Create logs directory if it doesn't exist
        log_file = config.get('file', './logs/app.log')
        log_dir = os.path.dirname(log_file)
        if log_dir:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, config.get('level', 'INFO').upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        # Add file handler with rotation
        if log_file:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=config.get('max_bytes', 10485760),
                backupCount=config.get('backup_count', 5)
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # Add console handler if enabled
        if config.get('enable_console', True):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # Store configuration for monitoring
        self.loggers['root'] = {
            'level': config.get('level'),
            'handlers': [type(h).__name__ for h in root_logger.handlers],
            'file': log_file if log_file else None
        }
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance with the specified name"""
        return logging.getLogger(name)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics and configuration"""
        stats = {
            'config': self._substitute_env_vars(self.config),
            'loggers': {}
        }
        
        for logger_name, logger_info in self.loggers.items():
            logger = logging.getLogger(logger_name)
            stats['loggers'][logger_name] = {
                'level': logger.level,
                'handlers': len(logger.handlers),
                'effective_level': logger.getEffectiveLevel()
            }
        
        # Add log file information if available
        config = self._substitute_env_vars(self.config)
        log_file = config.get('file')
        if log_file and os.path.exists(log_file):
            try:
                stat = os.stat(log_file)
                stats['log_file'] = {
                    'path': log_file,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            except Exception as e:
                stats['log_file'] = {'error': str(e)}
        
        return stats
    
    def reload_config(self):
        """Reload logging configuration"""
        with self._lock:
            try:
                self._load_config()
                self._setup_logging()
                print("Logging configuration reloaded successfully")
            except Exception as e:
                print(f"Failed to reload logging configuration: {e}")
    
    def set_level(self, level: str, logger_name: str = None):
        """Dynamically change log level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {level}")
        
        logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
        logger.setLevel(getattr(logging, level.upper()))
        
        print(f"Log level set to {level} for {'root' if not logger_name else logger_name}")
    
    def add_custom_handler(self, handler: logging.Handler, logger_name: str = None):
        """Add a custom handler to a logger"""
        logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
        logger.addHandler(handler)
    
    def remove_handler(self, handler_type: str, logger_name: str = None):
        """Remove a handler by type from a logger"""
        logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
        handlers_to_remove = [h for h in logger.handlers if type(h).__name__ == handler_type]
        
        for handler in handlers_to_remove:
            logger.removeHandler(handler)
            handler.close()
    
    def create_json_formatter(self) -> logging.Formatter:
        """Create a JSON formatter for structured logging"""
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                }
                
                if record.exc_info:
                    log_entry['exception'] = self.formatException(record.exc_info)
                
                return json.dumps(log_entry)
        
        return JsonFormatter()
    
    def setup_structured_logging(self, logger_name: str = None):
        """Setup structured JSON logging"""
        logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
        
        # Remove existing handlers
        logger.handlers.clear()
        
        # Add JSON file handler
        config = self._substitute_env_vars(self.config)
        log_file = config.get('file', './logs/app.log')
        if log_file:
            json_log_file = log_file.replace('.log', '_structured.log')
            json_handler = logging.handlers.RotatingFileHandler(
                json_log_file,
                maxBytes=config.get('max_bytes', 10485760),
                backupCount=config.get('backup_count', 5)
            )
            json_handler.setFormatter(self.create_json_formatter())
            logger.addHandler(json_handler)
        
        # Add console handler with simple format
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger.addHandler(console_handler)

# Global logging configuration instance
logging_config = LoggingConfig()

def get_logger(name: str) -> logging.Logger:
    """Get logger instance"""
    return logging_config.get_logger(name)

def setup_logging():
    """Setup logging configuration"""
    global logging_config
    logging_config._setup_logging()

def reload_logging():
    """Reload logging configuration"""
    logging_config.reload_config()
