"""
Enhanced Security configuration and middleware for FlavorSnap API
Implements comprehensive security scanning, vulnerability detection, and remediation
"""
import os
import re
import json
import time
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from flask import request, abort
from werkzeug.utils import secure_filename
import hashlib
import hmac
import json
import logging
import subprocess
import tempfile
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import logging

try:
    from anomaly_detection import anomaly_system, AnomalyType
except Exception:
    anomaly_system = None
    AnomalyType = None

logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration class"""
    
    # Rate limiting configurations with tier-based access

    RATE_LIMITS = {
        # Default limits for unauthenticated requests
        'default': '20 per minute',
        'health': '1000 per hour',
        'api_info': '30 per minute',
        
        # Free tier limits (authenticated)
        'free_predict': '10 per minute',
        'free_upload': '5 per minute',
        'free_admin': '5 per minute',
        'free_dashboard': '20 per minute',
        
        # Premium tier limits (authenticated)
        'premium_predict': '100 per minute',
        'premium_upload': '50 per minute',
        'premium_admin': '20 per minute',
        'premium_dashboard': '100 per minute',
        
        # Enterprise tier limits (authenticated)
        'enterprise_predict': '500 per minute',
        'enterprise_upload': '200 per minute',
        'enterprise_admin': '100 per minute',
        'enterprise_dashboard': '500 per minute'
    }
    
    # API key tiers and their prefixes
    API_KEY_TIERS = {
        'free': {'prefix': 'free_', 'weight': 1},
        'premium': {'prefix': 'prem_', 'weight': 5},
        'enterprise': {'prefix': 'ent_', 'weight': 10}
    }
    
    # File upload security
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    ALLOWED_MIME_TYPES = {
        'image/jpeg',
        'image/png',
        'image/webp'
    }
    # Malicious file signatures
    MALICIOUS_SIGNATURES = {
        b'\x4D\x5A',  # PE executable
        b'\x7FELF',   # ELF executable
        b'\xCA\xFE\xBA\xBE',  # Java class
        b'\xD0\xCF\x11\xE0',  # Microsoft Office
        b'PK\x03\x04',  # ZIP (could contain malicious content)
    }
    # Image validation thresholds
    MAX_IMAGE_DIMENSION = 8192
    MIN_IMAGE_DIMENSION = 32
    
    # Image dimension constraints
    MIN_IMAGE_WIDTH = 100
    MIN_IMAGE_HEIGHT = 100
    MAX_IMAGE_WIDTH = 10000  # Prevent memory exhaustion
    MAX_IMAGE_HEIGHT = 10000
    
    # Input validation patterns
    PATTERNS = {
        'filename': re.compile(r'^[a-zA-Z0-9._-]+$'),
        'api_key': re.compile(r'^[a-zA-Z0-9]{32,}$'),
        'request_id': re.compile(r'^[a-zA-Z0-9\-_]{8,64}$')
    }

    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }


class InputValidator:
    """Input validation and sanitization utilities"""

    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000, allow_html: bool = False) -> str:
        """Sanitize string input with comprehensive XSS protection"""
        if not text or not isinstance(text, str):
            return ""

        # Remove null bytes and control characters
        text = text.replace('\x00', '').replace('\r', '').replace('\n', ' ')

        # Strip HTML tags if not allowed (basic XSS protection)
        if not allow_html:
            # More comprehensive HTML tag removal
            text = re.sub(r'<[^>]+>', '', text)
            # Remove script tags and their content
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
            # Remove javascript: and other dangerous protocols
            text = re.sub(r'(javascript|vbscript|data|file):', '', text, flags=re.IGNORECASE)

        # Remove potential SQL injection patterns
        text = re.sub(r'(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)', '', text, flags=re.IGNORECASE)

        # Remove command injection patterns
        text = re.sub(r'[;&|`$()<>]', '', text)

        # Limit length
        return text[:max_length].strip()

    @staticmethod
    def sanitize_json_input(data: Dict[str, Any], schema: Dict[str, Any] = None) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Sanitize JSON input data with schema validation"""
        if not isinstance(data, dict):
            return False, "Invalid JSON format", {}

        sanitized_data = {}

        for key, value in data.items():
            # Sanitize keys
            clean_key = InputValidator.sanitize_string(str(key), max_length=100, allow_html=False)
            if not clean_key:
                continue

            # Sanitize values based on type
            if isinstance(value, str):
                sanitized_data[clean_key] = InputValidator.sanitize_string(value, max_length=1000)
            elif isinstance(value, (int, float)):
                # Ensure numeric values are within reasonable bounds
                if isinstance(value, int) and (-1000000 <= value <= 1000000):
                    sanitized_data[clean_key] = value
                elif isinstance(value, float) and (-1000000 <= value <= 1000000):
                    sanitized_data[clean_key] = value
            elif isinstance(value, bool):
                sanitized_data[clean_key] = value
            elif isinstance(value, list):
                # Sanitize list items (limit to 100 items)
                sanitized_list = []
                for item in value[:100]:
                    if isinstance(item, str):
                        sanitized_list.append(InputValidator.sanitize_string(item, max_length=500))
                    elif isinstance(item, (int, float, bool)):
                        sanitized_list.append(item)
                sanitized_data[clean_key] = sanitized_list
            # Skip other types (dict, None, etc.) for security

        # Schema validation if provided
        if schema:
            for required_field in schema.get('required', []):
                if required_field not in sanitized_data:
                    return False, f"Missing required field: {required_field}", sanitized_data

            for field, field_schema in schema.get('properties', {}).items():
                if field in sanitized_data:
                    field_type = field_schema.get('type')
                    if field_type == 'string' and not isinstance(sanitized_data[field], str):
                        return False, f"Field {field} must be a string", sanitized_data
                    elif field_type == 'number' and not isinstance(sanitized_data[field], (int, float)):
                        return False, f"Field {field} must be a number", sanitized_data
                    elif field_type == 'boolean' and not isinstance(sanitized_data[field], bool):
                        return False, f"Field {field} must be a boolean", sanitized_data

        return True, None, sanitized_data

    @staticmethod
    def sanitize_url(url: str) -> str:
        """Sanitize URL input"""
        if not url or not isinstance(url, str):
            return ""

        # Remove dangerous protocols
        url = re.sub(r'(javascript|vbscript|data|file):', '', url, flags=re.IGNORECASE)

        # Basic URL validation
        if not re.match(r'^https?://', url):
            return ""

        # Limit length
        return url[:2000]

    @staticmethod
    def sanitize_email(email: str) -> str:
        """Sanitize email input"""
        if not email or not isinstance(email, str):
            return ""

        # Basic email pattern validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return ""

        return email[:254].lower()  # RFC 5321 limit

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename input"""
        if not filename or not isinstance(filename, str):
            return ""

        # Remove path traversal attempts
        filename = os.path.basename(filename)

        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)

        # Limit length
        return filename[:255]

    @staticmethod
    def validate_filename(filename: str) -> bool:
        if not filename:
            return False
        if not SecurityConfig.PATTERNS['filename'].match(filename):
            return False
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        return ext in SecurityConfig.ALLOWED_EXTENSIONS

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        if not api_key:
            return False
        return bool(SecurityConfig.PATTERNS['api_key'].match(api_key))

    @staticmethod
    def validate_file_upload(file) -> tuple[bool, Optional[str]]:
        """Validate uploaded file with comprehensive security checks"""
        if not file:
            return False, "No file provided"
        if file.filename == '':
            return False, "Empty filename"
        
        # Validate filename format and extension
        if not InputValidator.validate_filename(file.filename):
            return False, "Invalid filename format or unsupported file extension"
        
        # Validate MIME type
        if file.content_type not in SecurityConfig.ALLOWED_MIME_TYPES:
            return False, f"Unsupported file type. Allowed types: jpg, png, webp"
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size == 0:
            return False, "File is empty"
        
        if file_size > SecurityConfig.MAX_CONTENT_LENGTH:
            max_size_mb = SecurityConfig.MAX_CONTENT_LENGTH / (1024 * 1024)
            return False, f"File too large. Maximum size: {max_size_mb}MB"
        
        # Validate image dimensions and detect malicious files
        try:
            file_data = file.read()
            file.seek(0)  # Reset file pointer
            
            # Attempt to open as image (will fail for malicious files)
            img = Image.open(io.BytesIO(file_data))
            
            # Verify image format matches extension
            img_format = img.format.lower() if img.format else ''
            allowed_formats = {'jpeg', 'jpg', 'png', 'webp'}
            if img_format not in allowed_formats:
                return False, f"Invalid image format. Allowed formats: jpg, png, webp"
            
            # Check image dimensions
            width, height = img.size
            
            if width < SecurityConfig.MIN_IMAGE_WIDTH or height < SecurityConfig.MIN_IMAGE_HEIGHT:
                return False, f"Image too small. Minimum dimensions: {SecurityConfig.MIN_IMAGE_WIDTH}x{SecurityConfig.MIN_IMAGE_HEIGHT}px"
            
            if width > SecurityConfig.MAX_IMAGE_WIDTH or height > SecurityConfig.MAX_IMAGE_HEIGHT:
                return False, f"Image too large. Maximum dimensions: {SecurityConfig.MAX_IMAGE_WIDTH}x{SecurityConfig.MAX_IMAGE_HEIGHT}px"
            
            # Verify image can be loaded (detects corrupted/malicious files)
            img.verify()
            
            # Re-open for additional checks after verify()
            img = Image.open(io.BytesIO(file_data))
            
            # Check for suspicious metadata or embedded scripts
            if hasattr(img, 'info') and img.info:
                # Check for suspicious keys in metadata
                suspicious_keys = ['comment', 'software', 'exif']
                for key in suspicious_keys:
                    if key in img.info:
                        value = str(img.info[key]).lower()
                        if any(pattern in value for pattern in ['<script', 'javascript:', 'data:', 'vbscript:']):
                            return False, "Suspicious content detected in image metadata"
            
        except Exception as e:
            return False, f"Invalid or corrupted image file: {str(e)}"
        
        return True, None

    @staticmethod
    def _check_malicious_signatures(file_content: bytes) -> Tuple[bool, str]:
        """Check for malicious file signatures"""
        # Check file header for known malicious signatures
        for signature, description in {
            b'\x4D\x5A': 'PE executable',
            b'\x7FELF': 'ELF executable', 
            b'\xCA\xFE\xBA\xBE': 'Java class',
            b'\xD0\xCF\x11\xE0': 'Microsoft Office',
            b'PK\x03\x04': 'ZIP archive'
        }.items():
            if file_content.startswith(signature):
                return True, description
        
        # Check for script content in image files
        text_content = file_content.decode('utf-8', errors='ignore').lower()
        script_patterns = [
            '<script', 'javascript:', 'vbscript:', 
            'onload=', 'onerror=', 'onclick=',
            'eval(', 'document.', 'window.',
            'php://', 'data://', 'file://'
        ]
        
        for pattern in script_patterns:
            if pattern in text_content:
                return True, f'Script content detected: {pattern}'
        
        return False, ''
    
    @staticmethod
    def _validate_image_content(file_content: bytes) -> Tuple[bool, str]:
        """Validate image content using PIL"""
        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(file_content))
            
            # Verify image format
            if image.format not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                return False, f"Unsupported image format: {image.format}"
            
            # Check image dimensions
            width, height = image.size
            if width < SecurityConfig.MIN_IMAGE_DIMENSION or height < SecurityConfig.MIN_IMAGE_DIMENSION:
                return False, f"Image too small: {width}x{height}"
            
            if width > SecurityConfig.MAX_IMAGE_DIMENSION or height > SecurityConfig.MAX_IMAGE_DIMENSION:
                return False, f"Image too large: {width}x{height}"
            
            # Verify image can be loaded (detects corrupted files)
            image.verify()
            
            # Re-open after verify (verify() closes the image)
            image = Image.open(io.BytesIO(file_content))
            
            # Check for reasonable aspect ratio (to detect panorama attacks)
            aspect_ratio = max(width, height) / min(width, height)
            if aspect_ratio > 20:  # Very extreme aspect ratios
                return False, f"Extreme aspect ratio: {aspect_ratio:.2f}"
            
            return True, ''
            
        except Exception as e:
            return False, f"Image validation failed: {str(e)}"
    
    @staticmethod
    def secure_filename_custom(filename: str) -> str:
        """Custom secure filename generation with path traversal protection"""
        # Remove any path components
        filename = os.path.basename(filename)
        
        # Use Werkzeug's secure_filename as base
        secure_name = secure_filename(filename)
        
        # Additional sanitization: remove any remaining suspicious characters
        secure_name = re.sub(r'[^\w\s.-]', '', secure_name)
        
        # Prevent path traversal attempts
        if '..' in secure_name or secure_name.startswith('.'):
            secure_name = secure_name.replace('..', '').lstrip('.')
        
        # Add timestamp to prevent collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(secure_name)
        
        # Ensure extension is lowercase and valid
        ext = ext.lower()
        if ext.lstrip('.') not in SecurityConfig.ALLOWED_EXTENSIONS:
            ext = '.jpg'  # Default to jpg if invalid
        
        return f"{name}_{timestamp}{ext}"


class APIKeyManager:
    """API key management utilities"""

    @staticmethod
    def generate_api_key(tier: str = 'free') -> str:
        """Generate a secure API key with tier prefix"""
        import secrets
        
        if tier not in SecurityConfig.API_KEY_TIERS:
            tier = 'free'
        
        prefix = SecurityConfig.API_KEY_TIERS[tier]['prefix']
        random_part = secrets.token_urlsafe(24)  # 32 chars total with prefix
        return f"{prefix}{random_part}"
    
    @staticmethod
    def generate_tiered_api_key(tier: str = 'free') -> dict:
        """Generate API key with tier information"""
        api_key = APIKeyManager.generate_api_key(tier)
        return {
            'api_key': api_key,
            'tier': tier,
            'limits': {
                'predict': SecurityConfig.RATE_LIMITS[f'{tier}_predict'],
                'upload': SecurityConfig.RATE_LIMITS[f'{tier}_upload'],
                'admin': SecurityConfig.RATE_LIMITS[f'{tier}_admin'],
                'dashboard': SecurityConfig.RATE_LIMITS[f'{tier}_dashboard']
            }
        }
    
    def generate_api_key() -> str:
        import secrets
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def verify_api_key(api_key: str, hashed_key: str) -> bool:
        return hmac.compare_digest(
            hashlib.sha256(api_key.encode()).hexdigest(),
            hashed_key
        )


class RateLimitManager:
    """Rate limiting utilities with tier-based access"""
    
    """Rate limiting utilities"""

    @staticmethod
    def get_client_ip() -> str:
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        return request.remote_addr or 'unknown'

    @staticmethod
    def get_rate_limit_key(endpoint: str = None) -> str:
        ip = RateLimitManager.get_client_ip()
        endpoint = endpoint or request.endpoint or 'unknown'
        return f"rate_limit:{endpoint}:{ip}"
    
    @staticmethod
    def get_api_key_tier(api_key: str) -> str:
        """Determine API key tier from key format"""
        if not api_key:
            return 'default'
        
        for tier, config in SecurityConfig.API_KEY_TIERS.items():
            if api_key.startswith(config['prefix']):
                return tier
        
        # Default to free tier for unrecognized keys
        return 'free'
    
    @staticmethod
    def get_rate_limit_for_endpoint(endpoint: str, api_key: str = None) -> str:
        """Get appropriate rate limit for endpoint based on API key tier"""
        tier = RateLimitManager.get_api_key_tier(api_key)
        
        # Map endpoints to rate limit keys
        endpoint_mapping = {
            'predict': f'{tier}_predict',
            'upload': f'{tier}_upload', 
            'generate_api_key': f'{tier}_admin',
            'performance_dashboard': f'{tier}_dashboard',
            'api_info': 'api_info',
            'health_check': 'health'
        }
        
        rate_limit_key = endpoint_mapping.get(endpoint, 'default')
        return SecurityConfig.RATE_LIMITS.get(rate_limit_key, SecurityConfig.RATE_LIMITS['default'])
    
    @staticmethod
    def get_tiered_key_func():
        """Key function that considers both IP and API tier"""
        def tiered_key():
            api_key = request.headers.get('X-API-Key')
            tier = RateLimitManager.get_api_key_tier(api_key)
            ip = RateLimitManager.get_client_ip()
            return f"{tier}:{ip}"
        return tiered_key


class SecurityMiddleware:
    """Security middleware for Flask application"""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self._app = app
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        content_length = request.content_length or 0
        if content_length > SecurityConfig.MAX_CONTENT_LENGTH:
            abort(413, description="Request too large")
        self._log_request()

    def after_request(self, response):
        for header, value in SecurityConfig.SECURITY_HEADERS.items():
            response.headers[header] = value
        return response

    def _log_request(self):
        ip = RateLimitManager.get_client_ip()
        suspicious_patterns = ['../', '<script', 'javascript:', 'data:', 'vbscript:', 'onload=', 'onerror=']
        request_data = str(request.data) if request.data else ""
        for pattern in suspicious_patterns:
            if pattern.lower() in request_data.lower():
                self._app.logger.warning(f"Suspicious request from {ip}: pattern '{pattern}' detected")
                break


class SecurityMonitor:
    """Security monitoring and alerting"""

    def __init__(self, app=None):
        self.app = app
        self.suspicious_ips: Dict[str, Any] = {}
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self._app = app
        app.before_request(self.monitor_request)

    def monitor_request(self):
        ip = RateLimitManager.get_client_ip()
        current_time = datetime.now()
        if ip not in self.suspicious_ips:
            self.suspicious_ips[ip] = {'count': 0, 'first_seen': current_time}
        self.suspicious_ips[ip]['count'] += 1
        if self._is_suspicious(ip):
            self._app.logger.warning(f"Suspicious activity detected from {ip}")

    def _is_suspicious(self, ip: str) -> bool:
        data = self.suspicious_ips[ip]
        if data['count'] > 1000:
            return True
        time_diff = datetime.now() - data['first_seen']
        if time_diff.total_seconds() < 60 and data['count'] > 100:
            return True
        return False

# Advanced Security Threat Detection
class ThreatType(Enum):
    """Types of security threats"""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    CSRF = "csrf"
    BRUTE_FORCE = "brute_force"
    DDOS = "ddos"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"

@dataclass
class SecurityThreat:
    """Represents a detected security threat"""
    id: str
    threat_type: ThreatType
    severity: str
    timestamp: datetime
    source_ip: str
    description: str
    evidence: Dict[str, Any]
    confidence: float
    blocked: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'threat_type': self.threat_type.value,
            'severity': self.severity,
            'timestamp': self.timestamp.isoformat(),
            'source_ip': self.source_ip,
            'description': self.description,
            'evidence': self.evidence,
            'confidence': self.confidence,
            'blocked': self.blocked
        }

class AdvancedThreatDetector:
    """Advanced security threat detection system"""
    
    def __init__(self):
        self.threat_patterns = {
            ThreatType.SQL_INJECTION: [
                r'(\bUNION\b.*\bSELECT\b)',
                r'(\bSELECT\b.*\bFROM\b)',
                r'(\bDROP\b.*\bTABLE\b)',
                r'(\bINSERT\b.*\bINTO\b)',
                r'(\bDELETE\b.*\bFROM\b)',
                r'(\bUPDATE\b.*\bSET\b)',
                r'(\'|\"|;|\-\-|\/\*|\*\/)',
                r'(\bOR\b.*\b1\s*=\s*1\b)',
                r'(\bAND\b.*\b1\s*=\s*1\b)'
            ],
            ThreatType.XSS: [
                r'(<script[^>]*>.*?</script>)',
                r'(javascript\s*:)',
                r'(on\w+\s*=)',
                r'(<iframe[^>]*>)',
                r'(alert\s*\()',
                r'(document\.cookie)',
                r'(eval\s*\()'
            ],
            ThreatType.PATH_TRAVERSAL: [
                r'(\.\.\/|\.\.\\)',
                r'(%2e%2e%2f|%2e%2e%5c)',
                r'(/etc/passwd|/etc/shadow)',
                r'(/var/log/|/proc/)',
                r'(\/windows\/system32\/)'
            ],
            ThreatType.COMMAND_INJECTION: [
                r'(;|\&\&|\|\||`|\$\(|\$\{)',
                r'(\bcat\b|\bls\b|\bdir\b)',
                r'(\bwhoami\b|\bid\b)',
                r'(\bping\b|\bnslookup\b)',
                r'(\bnc\b|\bnetcat\b)'
            ]
        }
        
        self.ip_reputation = defaultdict(float)
        self.request_patterns = defaultdict(lambda: deque(maxlen=100))
        self.failed_attempts = defaultdict(lambda: deque(maxlen=50))
        self.blocked_ips = set()
        self.threat_history = deque(maxlen=1000)
        
        # Behavioral baselines
        self.baseline_request_rate = 10.0  # requests per minute
        self.baseline_payload_size = 1024  # bytes
        self.baseline_response_time = 0.5  # seconds
    
    def analyze_request(self, request_data: Dict[str, Any]) -> List[SecurityThreat]:
        """Analyze incoming request for security threats"""
        threats = []
        ip_address = request_data.get('ip_address', 'unknown')
        
        try:
            # Check if IP is blocked
            if ip_address in self.blocked_ips:
                threats.append(SecurityThreat(
                    id=f"blocked_ip_{int(time.time())}",
                    threat_type=ThreatType.ANOMALOUS_BEHAVIOR,
                    severity="high",
                    timestamp=datetime.now(),
                    source_ip=ip_address,
                    description="Request from blocked IP address",
                    evidence={'blocked_ip': True},
                    confidence=1.0,
                    blocked=True
                ))
                return threats
            
            # Pattern-based detection
            pattern_threats = self._detect_pattern_attacks(request_data, ip_address)
            threats.extend(pattern_threats)
            
            # Behavioral anomaly detection
            behavioral_threats = self._detect_behavioral_anomalies(request_data, ip_address)
            threats.extend(behavioral_threats)
            
            # Rate-based detection
            rate_threats = self._detect_rate_based_attacks(request_data, ip_address)
            threats.extend(rate_threats)
            
            # Data exfiltration detection
            exfil_threats = self._detect_data_exfiltration(request_data, ip_address)
            threats.extend(exfil_threats)
            
            # Update threat history
            for threat in threats:
                self.threat_history.append(threat)
            
            # Trigger anomaly detection if available
            if anomaly_system and threats:
                security_data = {
                    'ip_address': ip_address,
                    'request_data': str(request_data.get('request_body', '')),
                    'threat_count': len(threats),
                    'high_severity_count': len([t for t in threats if t.severity == 'high']),
                    'endpoint': request_data.get('endpoint', ''),
                    'failed_login': any('login' in request_data.get('endpoint', '').lower() and 
                                      request_data.get('status_code', 200) >= 400 for _ in [1])
                }
                anomalies = anomaly_system.detect_anomalies(security_data)
                if anomalies:
                    for anomaly in anomalies:
                        threats.append(SecurityThreat(
                            id=f"anomaly_{anomaly.id}",
                            threat_type=ThreatType.ANOMALOUS_BEHAVIOR,
                            severity="medium",
                            timestamp=anomaly.timestamp,
                            source_ip=ip_address,
                            description=f"Anomaly detected: {anomaly.description}",
                            evidence={'anomaly': anomaly.to_dict()},
                            confidence=anomaly.confidence
                        ))
            
            # Auto-block high confidence threats
            self._auto_block_threats(threats, ip_address)
            
        except Exception as e:
            logger.error(f"Threat detection error: {e}")
        
        return threats
    
    def _detect_pattern_attacks(self, request_data: Dict[str, Any], ip_address: str) -> List[SecurityThreat]:
        """Detect pattern-based attacks"""
        threats = []
        
        # Extract request data
        request_body = request_data.get('request_body', '')
        query_params = request_data.get('query_params', '')
        headers = str(request_data.get('headers', {}))
        user_agent = request_data.get('user_agent', '')
        
        # Combine all text data for analysis
        combined_text = f"{request_body} {query_params} {headers} {user_agent}".lower()
        
        for threat_type, patterns in self.threat_patterns.items():
            for pattern in patterns:
                try:
                    matches = re.findall(pattern, combined_text, re.IGNORECASE)
                    if matches:
                        threats.append(SecurityThreat(
                            id=f"{threat_type.value}_{int(time.time())}",
                            threat_type=threat_type,
                            severity="high",
                            timestamp=datetime.now(),
                            source_ip=ip_address,
                            description=f"{threat_type.value.replace('_', ' ').title()} attack detected",
                            evidence={
                                'pattern': pattern,
                                'matches': matches[:3],  # Limit to first 3 matches
                                'location': self._find_attack_location(request_data, pattern)
                            },
                            confidence=min(0.9, len(matches) * 0.3)
                        ))
                        break  # One threat per type per request
                except Exception as e:
                    logger.warning(f"Pattern matching error for {threat_type}: {e}")
        
        return threats
    
    def _find_attack_location(self, request_data: Dict[str, Any], pattern: str) -> str:
        """Find where the attack pattern was detected"""
        locations = []
        
        for key, value in request_data.items():
            if isinstance(value, str) and re.search(pattern, value, re.IGNORECASE):
                locations.append(key)
        
        return ', '.join(locations) if locations else 'unknown'
    
    def _detect_behavioral_anomalies(self, request_data: Dict[str, Any], ip_address: str) -> List[SecurityThreat]:
        """Detect behavioral anomalies"""
        threats = []
        current_time = datetime.now()
        
        # Track request patterns
        self.request_patterns[ip_address].append({
            'timestamp': current_time,
            'endpoint': request_data.get('endpoint', ''),
            'method': request_data.get('method', ''),
            'payload_size': len(str(request_data.get('request_body', ''))),
            'user_agent': request_data.get('user_agent', ''),
            'status_code': request_data.get('status_code', 200)
        })
        
        # Analyze patterns
        recent_requests = list(self.request_patterns[ip_address])
        if len(recent_requests) >= 10:
            # Check for unusual endpoint access
            endpoints = [r['endpoint'] for r in recent_requests]
            unique_endpoints = len(set(endpoints))
            if unique_endpoints > len(recent_requests) * 0.8:  # 80% unique endpoints
                threats.append(SecurityThreat(
                    id=f"endpoint_scan_{int(time.time())}",
                    threat_type=ThreatType.ANOMALOUS_BEHAVIOR,
                    severity="medium",
                    timestamp=current_time,
                    source_ip=ip_address,
                    description="Potential endpoint scanning detected",
                    evidence={
                        'unique_endpoints': unique_endpoints,
                        'total_requests': len(recent_requests),
                        'endpoints': list(set(endpoints))[:5]
                    },
                    confidence=0.7
                ))
            
            # Check for unusual user agent changes
            user_agents = [r['user_agent'] for r in recent_requests if r['user_agent']]
            if len(set(user_agents)) > 3:
                threats.append(SecurityThreat(
                    id=f"ua_rotation_{int(time.time())}",
                    threat_type=ThreatType.ANOMALOUS_BEHAVIOR,
                    severity="medium",
                    timestamp=current_time,
                    source_ip=ip_address,
                    description="User agent rotation detected",
                    evidence={
                        'unique_user_agents': len(set(user_agents)),
                        'user_agents': list(set(user_agents))[:3]
                    },
                    confidence=0.6
                ))
            
            # Check for payload size anomalies
            payload_sizes = [r['payload_size'] for r in recent_requests]
            avg_payload = np.mean(payload_sizes)
            if avg_payload > self.baseline_payload_size * 10:  # 10x larger than baseline
                threats.append(SecurityThreat(
                    id=f"large_payload_{int(time.time())}",
                    threat_type=ThreatType.DATA_EXFILTRATION,
                    severity="high",
                    timestamp=current_time,
                    source_ip=ip_address,
                    description="Unusually large payload detected",
                    evidence={
                        'avg_payload_size': avg_payload,
                        'baseline_size': self.baseline_payload_size,
                        'max_payload': max(payload_sizes)
                    },
                    confidence=0.8
                ))
        
        return threats
    
    def _detect_rate_based_attacks(self, request_data: Dict[str, Any], ip_address: str) -> List[SecurityThreat]:
        """Detect rate-based attacks"""
        threats = []
        current_time = datetime.now()
        
        # Track failed attempts
        status_code = request_data.get('status_code', 200)
        if status_code >= 400:
            self.failed_attempts[ip_address].append(current_time)
        
        # Check for brute force
        recent_failures = [
            t for t in self.failed_attempts[ip_address]
            if current_time - t < timedelta(minutes=15)
        ]
        
        if len(recent_failures) > 20:  # 20 failures in 15 minutes
            threats.append(SecurityThreat(
                id=f"brute_force_{int(time.time())}",
                threat_type=ThreatType.BRUTE_FORCE,
                severity="high",
                timestamp=current_time,
                source_ip=ip_address,
                description="Brute force attack detected",
                evidence={
                    'failure_count': len(recent_failures),
                    'time_window': '15 minutes'
                },
                confidence=0.9
            ))
        
        # Check for DDoS patterns
        recent_requests = [
            r for r in self.request_patterns[ip_address]
            if current_time - r['timestamp'] < timedelta(minutes=1)
        ]
        
        if len(recent_requests) > 100:  # More than 100 requests per minute
            threats.append(SecurityThreat(
                id=f"ddos_{int(time.time())}",
                threat_type=ThreatType.DDOS,
                severity="critical",
                timestamp=current_time,
                source_ip=ip_address,
                description="Potential DDoS attack detected",
                evidence={
                    'requests_per_minute': len(recent_requests),
                    'baseline_rate': self.baseline_request_rate
                },
                confidence=0.8
            ))
        
        return threats
    
    def _detect_data_exfiltration(self, request_data: Dict[str, Any], ip_address: str) -> List[SecurityThreat]:
        """Detect data exfiltration patterns"""
        threats = []
        
        # Check for large response sizes
        response_size = request_data.get('response_size', 0)
        if response_size > 1024 * 1024:  # 1MB
            threats.append(SecurityThreat(
                id=f"large_response_{int(time.time())}",
                threat_type=ThreatType.DATA_EXFILTRATION,
                severity="medium",
                timestamp=datetime.now(),
                source_ip=ip_address,
                description="Large response detected - potential data exfiltration",
                evidence={
                    'response_size': response_size,
                    'endpoint': request_data.get('endpoint', '')
                },
                confidence=0.6
            ))
        
        # Check for suspicious endpoints
        endpoint = request_data.get('endpoint', '').lower()
        suspicious_endpoints = ['/export', '/download', '/backup', '/dump', '/admin']
        for suspicious in suspicious_endpoints:
            if suspicious in endpoint:
                threats.append(SecurityThreat(
                    id=f"suspicious_endpoint_{int(time.time())}",
                    threat_type=ThreatType.PRIVILEGE_ESCALATION,
                    severity="high",
                    timestamp=datetime.now(),
                    source_ip=ip_address,
                    description=f"Access to suspicious endpoint: {endpoint}",
                    evidence={'endpoint': endpoint},
                    confidence=0.7
                ))
                break
        
        return threats
    
    def _auto_block_threats(self, threats: List[SecurityThreat], ip_address: str):
        """Automatically block threats based on confidence and severity"""
        for threat in threats:
            if (threat.confidence > 0.8 and 
                threat.severity in ['high', 'critical'] and 
                threat.threat_type not in [ThreatType.ANOMALOUS_BEHAVIOR]):
                
                self.blocked_ips.add(ip_address)
                threat.blocked = True
                
                logger.warning(f"Auto-blocked IP {ip_address} due to {threat.threat_type.value}")
                
                # Add to IP reputation system
                self.ip_reputation[ip_address] -= 0.5
    
    def get_security_dashboard(self) -> Dict[str, Any]:
        """Get security dashboard data"""
        current_time = datetime.now()
        recent_threats = [
            t for t in self.threat_history 
            if current_time - t.timestamp < timedelta(hours=24)
        ]
        
        # Calculate threat statistics
        threat_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for threat in recent_threats:
            threat_counts[threat.threat_type.value] += 1
            severity_counts[threat.severity] += 1
        
        # Calculate risk score
        risk_score = 0
        for severity, count in severity_counts.items():
            if severity == 'critical':
                risk_score += count * 25
            elif severity == 'high':
                risk_score += count * 15
            elif severity == 'medium':
                risk_score += count * 10
            elif severity == 'low':
                risk_score += count * 5
        
        risk_score = min(100, risk_score)
        
        return {
            'summary': {
                'total_threats': len(recent_threats),
                'blocked_ips': len(self.blocked_ips),
                'risk_score': risk_score,
                'risk_level': 'low' if risk_score < 30 else 'medium' if risk_score < 70 else 'high'
            },
            'threat_breakdown': dict(threat_counts),
            'severity_breakdown': dict(severity_counts),
            'recent_threats': [t.to_dict() for t in recent_threats[-10:]],  # Last 10 threats
            'top_source_ips': self._get_top_source_ips(recent_threats),
            'trends': self._calculate_threat_trends(recent_threats)
        }
    
    def _get_top_source_ips(self, threats: List[SecurityThreat], limit: int = 5) -> List[Dict[str, Any]]:
        """Get top source IPs by threat count"""
        ip_counts = defaultdict(int)
        ip_threats = defaultdict(list)
        
        for threat in threats:
            ip_counts[threat.source_ip] += 1
            ip_threats[threat.source_ip].append(threat)
        
        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return [
            {
                'ip': ip,
                'threat_count': count,
                'blocked': ip in self.blocked_ips,
                'reputation_score': self.ip_reputation.get(ip, 0.0),
                'last_seen': max([t.timestamp for t in ip_threats[ip]]).isoformat()
            }
            for ip, count in top_ips
        ]
    
    def _calculate_threat_trends(self, threats: List[SecurityThreat]) -> Dict[str, Any]:
        """Calculate threat trends over time"""
        if len(threats) < 2:
            return {'trend': 'insufficient_data'}
        
        # Group threats by hour
        hourly_counts = defaultdict(int)
        for threat in threats:
            hour = threat.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour] += 1
        
        if len(hourly_counts) < 2:
            return {'trend': 'insufficient_data'}
        
        # Calculate trend
        sorted_hours = sorted(hourly_counts.keys())
        recent_count = hourly_counts[sorted_hours[-1]]
        previous_count = hourly_counts[sorted_hours[-2]] if len(sorted_hours) > 1 else 0
        
        if recent_count > previous_count * 1.5:
            trend = 'increasing'
        elif recent_count < previous_count * 0.5:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'recent_hourly_count': recent_count,
            'previous_hourly_count': previous_count,
            'hourly_breakdown': {hour.isoformat(): count for hour, count in hourly_counts.items()}
        }
    
    def unblock_ip(self, ip_address: str) -> bool:
        """Unblock an IP address"""
        if ip_address in self.blocked_ips:
            self.blocked_ips.remove(ip_address)
            self.ip_reputation[ip_address] = max(0.0, self.ip_reputation.get(ip_address, 0.0) + 0.2)
            logger.info(f"Unblocked IP: {ip_address}")
            return True
        return False
    
    def update_reputation(self, ip_address: str, delta: float):
        """Update IP reputation score"""
        current_score = self.ip_reputation.get(ip_address, 0.0)
        new_score = max(-1.0, min(1.0, current_score + delta))
        self.ip_reputation[ip_address] = new_score

# Global threat detector instance
threat_detector = AdvancedThreatDetector()
