import logging
import logging.handlers
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'getMessage'
            }:
                log_entry[key] = value
                
        return json.dumps(log_entry)


class StructuredLogger:
    """Centralized logging system for FlavorSnap"""
    
    def __init__(self, name: str = "flavorsnap", log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Setup handlers
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Setup console and file handlers with rotation"""
        
        # Console handler for development
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # File handler for structured logs with rotation
        log_file = self.log_dir / f"{self.name}.json"
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        
        # Error file handler
        error_log_file = self.log_dir / f"{self.name}-errors.json"
        error_handler = logging.handlers.RotatingFileHandler(
            filename=error_log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        
        # Add handlers to logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        
    def debug(self, message: str, **kwargs):
        """Log debug message with optional extra fields"""
        self.logger.debug(message, extra=kwargs)
        
    def info(self, message: str, **kwargs):
        """Log info message with optional extra fields"""
        self.logger.info(message, extra=kwargs)
        
    def warning(self, message: str, **kwargs):
        """Log warning message with optional extra fields"""
        self.logger.warning(message, extra=kwargs)
        
    def error(self, message: str, **kwargs):
        """Log error message with optional extra fields"""
        self.logger.error(message, extra=kwargs)
        
    def critical(self, message: str, **kwargs):
        """Log critical message with optional extra fields"""
        self.logger.critical(message, extra=kwargs)
        
    def log_api_request(self, method: str, endpoint: str, headers: Dict[str, Any] = None, 
                       body: Dict[str, Any] = None, **kwargs):
        """Log API request details"""
        self.info(
            f"API Request: {method} {endpoint}",
            request_method=method,
            request_endpoint=endpoint,
            request_headers=headers,
            request_body=body,
            event_type="api_request",
            **kwargs
        )
        
    def log_api_response(self, method: str, endpoint: str, status_code: int, 
                        response_body: Dict[str, Any] = None, duration_ms: float = None, **kwargs):
        """Log API response details"""
        self.info(
            f"API Response: {method} {endpoint} - {status_code}",
            request_method=method,
            request_endpoint=endpoint,
            response_status_code=status_code,
            response_body=response_body,
            response_duration_ms=duration_ms,
            event_type="api_response",
            **kwargs
        )
        
    def log_error_with_traceback(self, message: str, exception: Exception, **kwargs):
        """Log error with full exception traceback"""
        self.error(
            f"{message}: {str(exception)}",
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            event_type="error_with_traceback",
            **kwargs
        )


# Global logger instance
logger = StructuredLogger()
