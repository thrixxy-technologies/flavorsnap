"""
Advanced Input Validation and Security Configuration
Provides comprehensive input validation, sanitization, and security checks
"""

import re
import os
import hashlib
import magic
from typing import Dict, List, Optional, Tuple, Any
from werkzeug.datastructures import FileStorage
from dataclasses import dataclass
from enum import Enum
import logging
import tempfile
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation severity levels"""
    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"

@dataclass
class ValidationResult:
    """Validation result data class"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_data: Any = None
    security_score: float = 0.0
    metadata: Dict[str, Any] = None

class InputValidator:
    """Comprehensive input validation and sanitization"""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.validation_level = validation_level
        self.allowed_image_types = {
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/png': ['.png'],
            'image/webp': ['.webp'],
            'image/gif': ['.gif']
        }
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.max_filename_length = 255
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'eval\s*\(',
            r'exec\s*\(',
            r'system\s*\(',
            r'\$\(',
            r'`[^`]*`',
            r'\.\./.*',
            r'file://',
            r'ftp://',
            r'http://',
            r'https://'
        ]
        
    def validate_text_input(self, text: str, field_name: str = "input", 
                          max_length: int = 1000, allow_html: bool = False) -> ValidationResult:
        """Validate text input with comprehensive checks"""
        errors = []
        warnings = []
        
        if not isinstance(text, str):
            errors.append(f"{field_name} must be a string")
            return ValidationResult(False, errors, warnings)
        
        # Length validation
        if len(text) > max_length:
            errors.append(f"{field_name} exceeds maximum length of {max_length}")
        
        # Null byte injection
        if '\x00' in text:
            errors.append(f"{field_name} contains null bytes")
        
        # Check for dangerous patterns
        if not allow_html:
            for pattern in self.dangerous_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    warnings.append(f"{field_name} contains potentially dangerous content")
        
        # SQL injection patterns
        sql_patterns = [
            r'(union|select|insert|update|delete|drop|create|alter)\s+',
            r'--',
            r'/\*.*\*/',
            r'or\s+1\s*=\s*1',
            r'and\s+1\s*=\s*1'
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                warnings.append(f"{field_name} contains potential SQL injection patterns")
        
        # Sanitize input
        sanitized = self._sanitize_text(text, allow_html)
        
        # Calculate security score
        security_score = self._calculate_text_security_score(text, errors, warnings)
        
        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            sanitized_data=sanitized,
            security_score=security_score,
            metadata={'original_length': len(text), 'sanitized_length': len(sanitized)}
        )
    
    def validate_file_upload(self, file: FileStorage, field_name: str = "file") -> ValidationResult:
        """Comprehensive file upload validation"""
        errors = []
        warnings = []
        metadata = {}
        
        if not file or not hasattr(file, 'filename'):
            errors.append(f"{field_name} is not a valid file")
            return ValidationResult(False, errors, warnings)
        
        # Basic file checks
        if file.filename == '':
            errors.append(f"{field_name} has no filename")
        
        # Filename validation
        filename_validation = self._validate_filename(file.filename)
        errors.extend(filename_validation.errors)
        warnings.extend(filename_validation.warnings)
        
        # File size validation
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        metadata['file_size'] = file_size
        
        if file_size > self.max_file_size:
            errors.append(f"{field_name} exceeds maximum size of {self.max_file_size} bytes")
        
        if file_size == 0:
            errors.append(f"{field_name} is empty")
        
        # Content type validation
        content_type = file.content_type or 'application/octet-stream'
        if content_type not in self.allowed_image_types:
            errors.append(f"{field_name} has unsupported content type: {content_type}")
        
        # Magic number validation
        try:
            file_content = file.read(1024)
            file.seek(0)
            
            detected_type = magic.from_buffer(file_content, mime=True)
            metadata['detected_mime_type'] = detected_type
            
            if detected_type != content_type:
                warnings.append(f"{field_name} content type mismatch: {content_type} vs {detected_type}")
            
            if detected_type not in self.allowed_image_types:
                errors.append(f"{field_name} contains non-image content: {detected_type}")
        
        except Exception as e:
            warnings.append(f"Could not verify file content type: {str(e)}")
        
        # Malware scanning
        malware_result = self._scan_for_malware(file)
        if malware_result:
            errors.append(f"{field_name} failed security scan: {malware_result}")
        
        # Image validation
        if content_type in self.allowed_image_types:
            image_validation = self._validate_image_content(file)
            errors.extend(image_validation.errors)
            warnings.extend(image_validation.warnings)
            metadata.update(image_validation.metadata or {})
        
        # Calculate security score
        security_score = self._calculate_file_security_score(
            file_size, content_type, errors, warnings
        )
        
        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            security_score=security_score,
            metadata=metadata
        )
    
    def validate_json_input(self, json_data: Dict, schema: Optional[Dict] = None) -> ValidationResult:
        """Validate JSON input against schema and security checks"""
        errors = []
        warnings = []
        
        if not isinstance(json_data, dict):
            errors.append("Input must be a JSON object")
            return ValidationResult(False, errors, warnings)
        
        # Check for nested depth
        max_depth = 10
        current_depth = self._get_json_depth(json_data)
        if current_depth > max_depth:
            errors.append(f"JSON depth exceeds maximum of {max_depth}")
        
        # Check for dangerous keys
        dangerous_keys = ['__proto__', 'constructor', 'prototype']
        for key in str(json_data).split():
            if key.strip(',:{}[]"\'') in dangerous_keys:
                errors.append(f"JSON contains dangerous key: {key}")
        
        # Schema validation if provided
        if schema:
            schema_result = self._validate_json_schema(json_data, schema)
            errors.extend(schema_result.errors)
            warnings.extend(schema_result.warnings)
        
        # Sanitize string values
        sanitized_json = self._sanitize_json_strings(json_data)
        
        # Calculate security score
        security_score = self._calculate_json_security_score(json_data, errors, warnings)
        
        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            sanitized_data=sanitized_json,
            security_score=security_score,
            metadata={'depth': current_depth, 'keys_count': len(str(json_data).split(','))}
        )
    
    def _sanitize_text(self, text: str, allow_html: bool = False) -> str:
        """Sanitize text input"""
        if not allow_html:
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', text)
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Escape special characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')
        
        return text.strip()
    
    def _validate_filename(self, filename: str) -> ValidationResult:
        """Validate filename for security"""
        errors = []
        warnings = []
        
        if len(filename) > self.max_filename_length:
            errors.append(f"Filename exceeds maximum length of {self.max_filename_length}")
        
        # Check for dangerous characters
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            if char in filename:
                errors.append(f"Filename contains dangerous character: {char}")
        
        # Check for reserved names (Windows)
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            errors.append(f"Filename uses reserved name: {name_without_ext}")
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        if file_ext not in allowed_extensions:
            errors.append(f"File extension not allowed: {file_ext}")
        
        return ValidationResult(len(errors) == 0, errors, warnings)
    
    def _scan_for_malware(self, file: FileStorage) -> Optional[str]:
        """Basic malware scanning using file signatures"""
        try:
            # Read first few KB for signature checking
            file.seek(0)
            header = file.read(4096)
            file.seek(0)
            
            # Check for common malware signatures
            malware_signatures = [
                b'MZ',  # PE executable
                b'\x7fELF',  # ELF executable
                b'PK\x03\x04',  # ZIP (could contain malware)
                b'\x1f\x8b\x08',  # GZIP
            ]
            
            for signature in malware_signatures:
                if header.startswith(signature):
                    return f"File contains executable signature: {signature}"
            
            # Check for suspicious patterns
            suspicious_patterns = [
                b'eval(',
                b'system(',
                b'exec(',
                b'shell_exec(',
                b'passthru(',
            ]
            
            for pattern in suspicious_patterns:
                if pattern in header:
                    return f"File contains suspicious pattern: {pattern}"
        
        except Exception as e:
            logger.warning(f"Malware scan failed: {str(e)}")
        
        return None
    
    def _validate_image_content(self, file: FileStorage) -> ValidationResult:
        """Validate image content for integrity"""
        errors = []
        warnings = []
        metadata = {}
        
        try:
            from PIL import Image
            import io
            
            file.seek(0)
            image_data = file.read()
            file.seek(0)
            
            # Try to open with PIL
            image = Image.open(io.BytesIO(image_data))
            
            # Verify image can be loaded
            image.verify()
            
            # Reopen for metadata extraction
            image = Image.open(io.BytesIO(image_data))
            
            metadata.update({
                'image_format': image.format,
                'image_mode': image.mode,
                'image_size': image.size,
                'has_transparency': image.mode in ('RGBA', 'LA') or 'transparency' in image.info
            })
            
            # Check for reasonable dimensions
            max_dimension = 10000
            if image.size[0] > max_dimension or image.size[1] > max_dimension:
                warnings.append(f"Image dimensions are very large: {image.size}")
            
            # Check for reasonable aspect ratio
            aspect_ratio = max(image.size) / min(image.size)
            if aspect_ratio > 20:
                warnings.append(f"Image has extreme aspect ratio: {aspect_ratio:.2f}")
        
        except Exception as e:
            errors.append(f"Image validation failed: {str(e)}")
        
        return ValidationResult(len(errors) == 0, errors, warnings, metadata=metadata)
    
    def _get_json_depth(self, obj: Any, current_depth: int = 0) -> int:
        """Calculate maximum depth of JSON object"""
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(self._get_json_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(self._get_json_depth(item, current_depth + 1) for item in obj)
        else:
            return current_depth
    
    def _validate_json_schema(self, data: Dict, schema: Dict) -> ValidationResult:
        """Basic JSON schema validation"""
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in data:
                errors.append(f"Required field missing: {field}")
        
        # Check field types
        properties = schema.get('properties', {})
        for field, field_schema in properties.items():
            if field in data:
                expected_type = field_schema.get('type')
                if expected_type == 'string' and not isinstance(data[field], str):
                    errors.append(f"Field {field} should be string")
                elif expected_type == 'number' and not isinstance(data[field], (int, float)):
                    errors.append(f"Field {field} should be number")
                elif expected_type == 'boolean' and not isinstance(data[field], bool):
                    errors.append(f"Field {field} should be boolean")
                elif expected_type == 'array' and not isinstance(data[field], list):
                    errors.append(f"Field {field} should be array")
                elif expected_type == 'object' and not isinstance(data[field], dict):
                    errors.append(f"Field {field} should be object")
        
        return ValidationResult(len(errors) == 0, errors, warnings)
    
    def _sanitize_json_strings(self, data: Any) -> Any:
        """Recursively sanitize string values in JSON"""
        if isinstance(data, str):
            return self._sanitize_text(data)
        elif isinstance(data, dict):
            return {k: self._sanitize_json_strings(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_json_strings(item) for item in data]
        else:
            return data
    
    def _calculate_text_security_score(self, text: str, errors: List[str], warnings: List[str]) -> float:
        """Calculate security score for text input"""
        base_score = 100.0
        
        # Deduct points for errors and warnings
        base_score -= len(errors) * 20
        base_score -= len(warnings) * 5
        
        # Additional checks
        if len(text) > 1000:
            base_score -= 10
        
        dangerous_pattern_count = sum(1 for pattern in self.dangerous_patterns 
                                     if re.search(pattern, text, re.IGNORECASE))
        base_score -= dangerous_pattern_count * 15
        
        return max(0.0, min(100.0, base_score))
    
    def _calculate_file_security_score(self, file_size: int, content_type: str, 
                                     errors: List[str], warnings: List[str]) -> float:
        """Calculate security score for file upload"""
        base_score = 100.0
        
        # Deduct points for errors and warnings
        base_score -= len(errors) * 25
        base_score -= len(warnings) * 10
        
        # Size-based scoring
        if file_size > 5 * 1024 * 1024:  # 5MB
            base_score -= 10
        
        # Content type scoring
        if content_type in self.allowed_image_types:
            base_score += 5  # Bonus for allowed types
        
        return max(0.0, min(100.0, base_score))
    
    def _calculate_json_security_score(self, data: Dict, errors: List[str], warnings: List[str]) -> float:
        """Calculate security score for JSON input"""
        base_score = 100.0
        
        # Deduct points for errors and warnings
        base_score -= len(errors) * 20
        base_score -= len(warnings) * 5
        
        # Depth-based scoring
        depth = self._get_json_depth(data)
        if depth > 5:
            base_score -= (depth - 5) * 5
        
        return max(0.0, min(100.0, base_score))

class SecurityMiddleware:
    """Security middleware for Flask applications"""
    
    def __init__(self, app=None, validator: InputValidator = None):
        self.validator = validator or InputValidator()
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security middleware with Flask app"""
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        # Store validation reports
        app.validation_reports = {}
    
    def _before_request(self):
        """Pre-request security checks"""
        from flask import request, g
        
        # Store request start time
        g.start_time = time.time()
        
        # Validate request data
        validation_report = {
            'timestamp': datetime.now().isoformat(),
            'endpoint': request.endpoint,
            'method': request.method,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'validations': {}
        }
        
        # Validate JSON data if present
        if request.is_json and request.get_json():
            json_validation = self.validator.validate_json_input(request.get_json())
            validation_report['validations']['json'] = {
                'is_valid': json_validation.is_valid,
                'errors': json_validation.errors,
                'warnings': json_validation.warnings,
                'security_score': json_validation.security_score
            }
            
            if not json_validation.is_valid:
                return jsonify({'error': 'Invalid JSON data', 'details': json_validation.errors}), 400
        
        # Validate form data if present
        if request.form:
            form_validations = {}
            for key, value in request.form.items():
                text_validation = self.validator.validate_text_input(value, key)
                form_validations[key] = {
                    'is_valid': text_validation.is_valid,
                    'errors': text_validation.errors,
                    'warnings': text_validation.warnings,
                    'security_score': text_validation.security_score
                }
            
            validation_report['validations']['form'] = form_validations
        
        # Validate files if present
        if request.files:
            file_validations = {}
            for key, file in request.files.items():
                file_validation = self.validator.validate_file_upload(file, key)
                file_validations[key] = {
                    'is_valid': file_validation.is_valid,
                    'errors': file_validation.errors,
                    'warnings': file_validation.warnings,
                    'security_score': file_validation.security_score,
                    'metadata': file_validation.metadata
                }
            
            validation_report['validations']['files'] = file_validations
        
        # Store validation report
        from flask import current_app
        current_app.validation_reports[request.id] = validation_report
    
    def _after_request(self, response):
        """Post-request security headers"""
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        
        return response

# Utility functions
def create_security_report_summary(app) -> Dict[str, Any]:
    """Create summary of validation reports"""
    if not hasattr(app, 'validation_reports'):
        return {'error': 'No validation reports available'}
    
    reports = app.validation_reports
    summary = {
        'total_requests': len(reports),
        'valid_requests': 0,
        'invalid_requests': 0,
        'average_security_score': 0.0,
        'common_errors': {},
        'common_warnings': {}
    }
    
    total_score = 0.0
    error_counts = {}
    warning_counts = {}
    
    for report in reports.values():
        is_valid = True
        report_scores = []
        
        for validation_type, validation_data in report['validations'].items():
            if isinstance(validation_data, dict):
                if validation_type == 'json':
                    if not validation_data['is_valid']:
                        is_valid = False
                    report_scores.append(validation_data['security_score'])
                elif validation_type == 'form':
                    for field_data in validation_data.values():
                        if not field_data['is_valid']:
                            is_valid = False
                        report_scores.append(field_data['security_score'])
                elif validation_type == 'files':
                    for file_data in validation_data.values():
                        if not file_data['is_valid']:
                            is_valid = False
                        report_scores.append(file_data['security_score'])
        
        if is_valid:
            summary['valid_requests'] += 1
        else:
            summary['invalid_requests'] += 1
        
        if report_scores:
            total_score += sum(report_scores) / len(report_scores)
    
    if reports:
        summary['average_security_score'] = total_score / len(reports)
    
    return summary

# Import required modules
try:
    import time
    from datetime import datetime
    from flask import jsonify
except ImportError as e:
    logger.warning(f"Could not import required modules: {e}")
