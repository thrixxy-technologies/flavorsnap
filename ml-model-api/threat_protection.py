"""
Threat Protection System for FlavorSnap API
Implements advanced threat detection, prevention, and response mechanisms
"""
import os
import re
import json
import time
import hashlib
import logging
import ipaddress
import geoip2.database
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from urllib.parse import urlparse, parse_qs
import requests
from flask import request, current_app
import redis
from sklearn.ensemble import IsolationForest
import numpy as np


class ThreatConfig:
    """Threat protection configuration"""
    
    # Rate limiting thresholds
    RATE_LIMIT_THRESHOLDS = {
        'default': {'requests': 100, 'window': 60},  # 100 requests per minute
        'auth': {'requests': 10, 'window': 300},     # 10 auth requests per 5 minutes
        'upload': {'requests': 20, 'window': 300},   # 20 uploads per 5 minutes
        'api': {'requests': 1000, 'window': 3600}   # 1000 API requests per hour
    }
    
    # Suspicious patterns
    SUSPICIOUS_PATTERNS = {
        'sql_injection': [
            r'(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)',
            r'(\'|\"|;|--|#|\/\*|\*\/)',
            r'(\bor\s+1\s*=\s*1\b)',
            r'(\band\s+1\s*=\s*1\b)',
            r'(\bxor\s+1\s*=\s*1\b)'
        ],
        'xss': [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'eval\s*\(',
            r'document\.',
            r'window\.',
            r'<iframe',
            r'<object',
            r'<embed'
        ],
        'path_traversal': [
            r'\.\./',
            r'\.\.\\',
            r'%2e%2e%2f',
            r'%2e%2e\\',
            r'\.\.%2f',
            r'\.\.%5c'
        ],
        'command_injection': [
            r'[;&|`$()<>]',
            r'(\b(cat|ls|dir|whoami|id|pwd)\b)',
            r'(\b(rm|del|mv|cp)\b)',
            r'(\b(curl|wget|nc|netcat)\b)'
        ],
        'ldap_injection': [
            r'\(\)',
            r'\*\)',
            r'\)\(',
            r'\)\(',
            r'\|\(',
            r'\&\('
        ]
    }
    
    # Blocked countries and IPs
    BLOCKED_COUNTRIES = {'CN', 'RU', 'KP', 'IR'}
    BLOCKED_ASN = [13335, 8075, 15169]  # Cloudflare, Microsoft, Google (for example)
    
    # Threat scoring
    THRESHOLDS = {
        'low': 20,
        'medium': 50,
        'high': 80,
        'critical': 95
    }
    
    # GeoIP database path
    GEOIP_DB_PATH = 'data/GeoLite2-Country.mmdb'
    
    # Redis configuration
    REDIS_PREFIX = 'threat_protection'
    REDIS_TTL = 3600  # 1 hour


@dataclass
class ThreatEvent:
    """Threat event data structure"""
    timestamp: datetime
    ip_address: str
    user_agent: str
    endpoint: str
    method: str
    threat_type: str
    threat_score: int
    details: Dict[str, Any]
    country: Optional[str] = None
    asn: Optional[int] = None
    blocked: bool = False


@dataclass
class ThreatMetrics:
    """Threat metrics data structure"""
    total_requests: int
    blocked_requests: int
    threats_detected: Dict[str, int]
    top_threat_ips: List[Tuple[str, int]]
    threat_trends: Dict[str, List[int]]
    average_threat_score: float


class IPReputationManager:
    """IP reputation and geolocation management"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.geoip_reader = None
        self.redis_client = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize IP reputation manager"""
        self.app = app
        
        # Initialize GeoIP database
        try:
            geoip_path = app.config.get('GEOIP_DB_PATH', ThreatConfig.GEOIP_DB_PATH)
            if os.path.exists(geoip_path):
                self.geoip_reader = geoip2.database.Reader(geoip_path)
                self.logger.info("GeoIP database loaded successfully")
            else:
                self.logger.warning(f"GeoIP database not found at {geoip_path}")
        except Exception as e:
            self.logger.error(f"Failed to load GeoIP database: {str(e)}")
        
        # Initialize Redis
        try:
            redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            self.logger.info("Redis connection established")
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {str(e)}")
    
    def get_ip_info(self, ip_address: str) -> Dict[str, Any]:
        """Get IP information including geolocation and reputation"""
        ip_info = {
            'ip_address': ip_address,
            'is_private': self._is_private_ip(ip_address),
            'country': None,
            'asn': None,
            'reputation_score': 100,  # Default to neutral
            'is_proxy': False,
            'is_tor': False
        }
        
        # Skip private IPs
        if ip_info['is_private']:
            return ip_info
        
        # Get geolocation
        if self.geoip_reader:
            try:
                response = self.geoip_reader.country(ip_address)
                ip_info['country'] = response.country.iso_code
            except Exception as e:
                self.logger.debug(f"GeoIP lookup failed for {ip_address}: {str(e)}")
        
        # Get ASN information (would need separate ASN database)
        # For now, we'll use a simple lookup or external API
        ip_info['asn'] = self._get_asn_info(ip_address)
        
        # Check reputation (using Redis cache or external service)
        ip_info['reputation_score'] = self._get_reputation_score(ip_address)
        
        # Check if proxy or Tor
        ip_info['is_proxy'] = self._is_proxy_ip(ip_address)
        ip_info['is_tor'] = self._is_tor_ip(ip_address)
        
        return ip_info
    
    def _is_private_ip(self, ip_address: str) -> bool:
        """Check if IP is private"""
        try:
            ip = ipaddress.ip_address(ip_address)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except ValueError:
            return True
    
    def _get_asn_info(self, ip_address: str) -> Optional[int]:
        """Get ASN information for IP"""
        # This would typically use an ASN database or API
        # For now, return None
        return None
    
    def _get_reputation_score(self, ip_address: str) -> int:
        """Get reputation score for IP (0-100)"""
        if not self.redis_client:
            return 100
        
        cache_key = f"{ThreatConfig.REDIS_PREFIX}:reputation:{ip_address}"
        cached_score = self.redis_client.get(cache_key)
        
        if cached_score:
            return int(cached_score)
        
        # Simple reputation calculation based on request history
        # In production, you'd use services like AbuseIPDB, VirusTotal, etc.
        score = 100
        
        # Check if IP has been blocked recently
        block_key = f"{ThreatConfig.REDIS_PREFIX}:blocked:{ip_address}"
        if self.redis_client.exists(block_key):
            score -= 50
        
        # Check request frequency
        request_key = f"{ThreatConfig.REDIS_PREFIX}:requests:{ip_address}"
        request_count = int(self.redis_client.get(request_key) or 0)
        if request_count > 1000:  # High frequency
            score -= 20
        elif request_count > 500:
            score -= 10
        
        # Cache the score
        self.redis_client.setex(cache_key, ThreatConfig.REDIS_TTL, score)
        
        return max(0, score)
    
    def _is_proxy_ip(self, ip_address: str) -> bool:
        """Check if IP is a known proxy"""
        # This would check against proxy databases
        # For now, return False
        return False
    
    def _is_tor_ip(self, ip_address: str) -> bool:
        """Check if IP is a Tor exit node"""
        # This would check against Tor exit node lists
        # For now, return False
        return False
    
    def update_reputation(self, ip_address: str, delta: int):
        """Update IP reputation score"""
        if not self.redis_client:
            return
        
        current_score = self._get_reputation_score(ip_address)
        new_score = max(0, min(100, current_score + delta))
        
        cache_key = f"{ThreatConfig.REDIS_PREFIX}:reputation:{ip_address}"
        self.redis_client.setex(cache_key, ThreatConfig.REDIS_TTL, new_score)


class ThreatDetector:
    """Advanced threat detection using multiple techniques"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.ip_reputation = IPReputationManager(app)
        self.ml_model = None
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize threat detector"""
        self.app = app
        self._initialize_ml_model()
    
    def _initialize_ml_model(self):
        """Initialize machine learning model for anomaly detection"""
        try:
            # Initialize Isolation Forest for anomaly detection
            self.ml_model = IsolationForest(
                n_estimators=100,
                contamination=0.1,  # Expected 10% anomalies
                random_state=42
            )
            self.logger.info("ML threat detection model initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize ML model: {str(e)}")
    
    def analyze_request(self, request_data: Dict[str, Any]) -> ThreatEvent:
        """Analyze request for threats"""
        ip_address = request_data.get('ip_address', request.remote_addr)
        user_agent = request_data.get('user_agent', request.headers.get('User-Agent', ''))
        endpoint = request_data.get('endpoint', request.endpoint or 'unknown')
        method = request_data.get('method', request.method)
        
        # Get IP information
        ip_info = self.ip_reputation.get_ip_info(ip_address)
        
        # Calculate threat score
        threat_score = 0
        detected_threats = []
        
        # 1. Pattern-based detection
        pattern_score, pattern_threats = self._detect_patterns(request_data)
        threat_score += pattern_score
        detected_threats.extend(pattern_threats)
        
        # 2. Rate limiting analysis
        rate_score = self._analyze_rate_limits(ip_address, endpoint)
        threat_score += rate_score
        if rate_score > 0:
            detected_threats.append('rate_limit_exceeded')
        
        # 3. IP reputation analysis
        reputation_score = 100 - ip_info['reputation_score']
        threat_score += reputation_score // 10  # Scale down
        if reputation_score > 50:
            detected_threats.append('poor_reputation')
        
        # 4. Geographic analysis
        geo_score = self._analyze_geography(ip_info)
        threat_score += geo_score
        if geo_score > 0:
            detected_threats.append('suspicious_location')
        
        # 5. Behavioral analysis
        behavior_score = self._analyze_behavior(ip_address, request_data)
        threat_score += behavior_score
        if behavior_score > 0:
            detected_threats.append('anomalous_behavior')
        
        # 6. ML-based anomaly detection
        if self.ml_model:
            anomaly_score = self._detect_anomalies(request_data, ip_info)
            threat_score += anomaly_score
            if anomaly_score > 0:
                detected_threats.append('ml_anomaly')
        
        # Cap threat score at 100
        threat_score = min(100, threat_score)
        
        # Determine primary threat type
        primary_threat = detected_threats[0] if detected_threats else 'unknown'
        
        # Create threat event
        threat_event = ThreatEvent(
            timestamp=datetime.now(),
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            threat_type=primary_threat,
            threat_score=threat_score,
            details={
                'detected_threats': detected_threats,
                'ip_info': ip_info,
                'request_data': self._sanitize_request_data(request_data)
            },
            country=ip_info.get('country'),
            asn=ip_info.get('asn'),
            blocked=threat_score >= ThreatConfig.THRESHOLDS['high']
        )
        
        # Update request history
        self.request_history[ip_address].append({
            'timestamp': datetime.now(),
            'endpoint': endpoint,
            'threat_score': threat_score
        })
        
        # Update IP reputation based on threat score
        if threat_score > 50:
            self.ip_reputation.update_reputation(ip_address, -10)
        
        return threat_event
    
    def _detect_patterns(self, request_data: Dict[str, Any]) -> Tuple[int, List[str]]:
        """Detect threat patterns in request"""
        threat_score = 0
        detected_threats = []
        
        # Analyze URL parameters
        url = request_data.get('url', request.url)
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        # Analyze form data
        form_data = request_data.get('form', request.form.to_dict())
        
        # Analyze JSON data
        json_data = request_data.get('json', {})
        if not json_data and request.is_json:
            try:
                json_data = request.get_json() or {}
            except:
                json_data = {}
        
        # Combine all text data for analysis
        all_text_data = []
        
        # Add URL and parameters
        all_text_data.append(parsed_url.path)
        all_text_data.extend(query_params.keys())
        all_text_data.extend(query_params.values())
        
        # Add form data
        all_text_data.extend(form_data.keys())
        all_text_data.extend(form_data.values())
        
        # Add JSON data
        if isinstance(json_data, dict):
            all_text_data.extend(json_data.keys())
            all_text_data.extend(str(v) for v in json_data.values())
        
        # Check against threat patterns
        combined_text = ' '.join(str(item) for item in all_text_data).lower()
        
        for threat_type, patterns in ThreatConfig.SUSPICIOUS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    threat_score += 10
                    detected_threats.append(threat_type)
                    break
        
        return threat_score, detected_threats
    
    def _analyze_rate_limits(self, ip_address: str, endpoint: str) -> int:
        """Analyze rate limiting violations"""
        if not self.ip_reputation.redis_client:
            return 0
        
        # Get appropriate threshold for endpoint
        threshold_key = 'default'
        if 'auth' in endpoint:
            threshold_key = 'auth'
        elif 'upload' in endpoint:
            threshold_key = 'upload'
        elif endpoint.startswith('/api/'):
            threshold_key = 'api'
        
        threshold = ThreatConfig.RATE_LIMIT_THRESHOLDS[threshold_key]
        
        # Check request count in window
        window_key = f"{ThreatConfig.REDIS_PREFIX}:requests:{ip_address}:{endpoint}"
        request_count = int(self.ip_reputation.redis_client.get(window_key) or 0)
        
        if request_count > threshold['requests']:
            # Calculate score based on how much they exceeded the limit
            excess = request_count - threshold['requests']
            return min(30, excess * 2)  # Max 30 points for rate limiting
        
        return 0
    
    def _analyze_geography(self, ip_info: Dict[str, Any]) -> int:
        """Analyze geographic threats"""
        score = 0
        
        # Check blocked countries
        if ip_info.get('country') in ThreatConfig.BLOCKED_COUNTRIES:
            score += 50
        
        # Check suspicious ASN
        if ip_info.get('asn') in ThreatConfig.BLOCKED_ASN:
            score += 30
        
        # Check for proxy/Tor
        if ip_info.get('is_proxy'):
            score += 20
        if ip_info.get('is_tor'):
            score += 40
        
        return score
    
    def _analyze_behavior(self, ip_address: str, request_data: Dict[str, Any]) -> int:
        """Analyze behavioral patterns"""
        score = 0
        history = self.request_history.get(ip_address, deque(maxlen=1000))
        
        if len(history) < 10:
            return 0  # Not enough data
        
        # Analyze request frequency patterns
        now = datetime.now()
        recent_requests = [req for req in history 
                          if (now - req['timestamp']).total_seconds() < 300]  # Last 5 minutes
        
        if len(recent_requests) > 100:  # Very high frequency
            score += 20
        
        # Analyze endpoint diversity
        endpoints = set(req['endpoint'] for req in recent_requests)
        if len(endpoints) == 1 and len(recent_requests) > 50:  # Single endpoint spam
            score += 15
        
        # Analyze threat score trend
        recent_scores = [req['threat_score'] for req in recent_requests]
        if recent_scores and np.mean(recent_scores) > 30:  # Consistently high threat scores
            score += 10
        
        return score
    
    def _detect_anomalies(self, request_data: Dict[str, Any], ip_info: Dict[str, Any]) -> int:
        """Detect anomalies using machine learning"""
        if not self.ml_model:
            return 0
        
        try:
            # Extract features for ML model
            features = self._extract_features(request_data, ip_info)
            
            # Predict anomaly
            prediction = self.ml_model.predict([features])[0]
            
            # Isolation Forest returns -1 for anomalies, 1 for normal
            if prediction == -1:
                return 25  # Anomaly detected
            return 0
        except Exception as e:
            self.logger.error(f"ML anomaly detection failed: {str(e)}")
            return 0
    
    def _extract_features(self, request_data: Dict[str, Any], ip_info: Dict[str, Any]) -> List[float]:
        """Extract features for ML model"""
        features = []
        
        # Request features
        features.append(float(len(request_data.get('url', ''))))
        features.append(float(len(request_data.get('user_agent', ''))))
        
        # IP features
        features.append(float(ip_info.get('reputation_score', 100)))
        features.append(1.0 if ip_info.get('is_private', False) else 0.0)
        features.append(1.0 if ip_info.get('is_proxy', False) else 0.0)
        features.append(1.0 if ip_info.get('is_tor', False) else 0.0)
        
        # Geographic features
        features.append(1.0 if ip_info.get('country') in ThreatConfig.BLOCKED_COUNTRIES else 0.0)
        
        # Request history features
        history = self.request_history.get(ip_info.get('ip_address', ''), deque(maxlen=1000))
        features.append(float(len(history)))
        
        if history:
            recent_threats = [req['threat_score'] for req in history 
                            if (datetime.now() - req['timestamp']).total_seconds() < 300]
            features.append(float(np.mean(recent_threats)) if recent_threats else 0.0)
        else:
            features.append(0.0)
        
        return features
    
    def _sanitize_request_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize request data for logging"""
        sanitized = {}
        
        # Copy safe fields
        safe_fields = ['url', 'method', 'endpoint', 'content_length', 'content_type']
        for field in safe_fields:
            if field in request_data:
                sanitized[field] = request_data[field]
        
        # Sanitize headers
        if 'headers' in request_data:
            headers = request_data['headers'].copy()
            # Remove sensitive headers
            sensitive_headers = ['authorization', 'cookie', 'x-api-key']
            for header in sensitive_headers:
                headers.pop(header, None)
            sanitized['headers'] = headers
        
        return sanitized


class ThreatProtectionMiddleware:
    """Threat protection middleware for Flask"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.detector = ThreatDetector(app)
        self.threat_events: List[ThreatEvent] = []
        self.blocked_ips: Set[str] = set()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize threat protection middleware"""
        self.app = app
        app.before_request(self._protect_request)
        app.after_request(self._log_response)
    
    def _protect_request(self):
        """Protect incoming requests"""
        # Collect request data
        request_data = {
            'ip_address': self._get_client_ip(),
            'url': request.url,
            'method': request.method,
            'endpoint': request.endpoint,
            'user_agent': request.headers.get('User-Agent', ''),
            'headers': dict(request.headers),
            'form': request.form.to_dict(),
            'content_length': request.content_length or 0,
            'content_type': request.content_type
        }
        
        # Analyze request for threats
        threat_event = self.detector.analyze_request(request_data)
        
        # Store threat event
        self.threat_events.append(threat_event)
        
        # Log threat event
        if threat_event.threat_score > 0:
            self._log_threat_event(threat_event)
        
        # Block request if threat score is high
        if threat_event.blocked or threat_event.threat_score >= ThreatConfig.THRESHOLDS['critical']:
            self.blocked_ips.add(threat_event.ip_address)
            self.logger.warning(f"Blocked request from {threat_event.ip_address} - {threat_event.threat_type} (score: {threat_event.threat_score})")
            return {
                'error': 'Request blocked',
                'message': 'Your request has been blocked due to suspicious activity',
                'threat_score': threat_event.threat_score,
                'threat_type': threat_event.threat_type
            }, 403
        
        # Update request counters
        self._update_request_counters(threat_event)
    
    def _log_response(self, response):
        """Log response for threat analysis"""
        # Log response status codes for threat analysis
        if response.status_code >= 400:
            ip_address = self._get_client_ip()
            self.logger.warning(f"Error response {response.status_code} for {ip_address}")
        
        return response
    
    def _get_client_ip(self) -> str:
        """Get client IP address"""
        # Check for proxy headers
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        return request.remote_addr or 'unknown'
    
    def _log_threat_event(self, threat_event: ThreatEvent):
        """Log threat event"""
        log_data = {
            'timestamp': threat_event.timestamp.isoformat(),
            'ip_address': threat_event.ip_address,
            'threat_type': threat_event.threat_type,
            'threat_score': threat_event.threat_score,
            'endpoint': threat_event.endpoint,
            'method': threat_event.method,
            'country': threat_event.country,
            'blocked': threat_event.blocked,
            'details': threat_event.details
        }
        
        if threat_event.threat_score >= ThreatConfig.THRESHOLDS['high']:
            self.logger.error(f"High threat detected: {json.dumps(log_data)}")
        elif threat_event.threat_score >= ThreatConfig.THRESHOLDS['medium']:
            self.logger.warning(f"Medium threat detected: {json.dumps(log_data)}")
        else:
            self.logger.info(f"Low threat detected: {json.dumps(log_data)}")
    
    def _update_request_counters(self, threat_event: ThreatEvent):
        """Update request counters in Redis"""
        if not self.detector.ip_reputation.redis_client:
            return
        
        ip_address = threat_event.ip_address
        endpoint = threat_event.endpoint
        
        # Update general request counter
        request_key = f"{ThreatConfig.REDIS_PREFIX}:requests:{ip_address}"
        self.detector.ip_reputation.redis_client.incr(request_key)
        self.detector.ip_reputation.redis_client.expire(request_key, ThreatConfig.REDIS_TTL)
        
        # Update endpoint-specific counter
        endpoint_key = f"{ThreatConfig.REDIS_PREFIX}:requests:{ip_address}:{endpoint}"
        self.detector.ip_reputation.redis_client.incr(endpoint_key)
        self.detector.ip_reputation.redis_client.expire(endpoint_key, ThreatConfig.REDIS_TTL)
    
    def get_threat_metrics(self) -> ThreatMetrics:
        """Get threat protection metrics"""
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        
        # Filter events from last hour
        recent_events = [event for event in self.threat_events 
                        if event.timestamp > last_hour]
        
        # Calculate metrics
        total_requests = len(recent_events)
        blocked_requests = len([e for e in recent_events if e.blocked])
        
        # Count threat types
        threats_detected = defaultdict(int)
        for event in recent_events:
            threats_detected[event.threat_type] += 1
        
        # Get top threat IPs
        ip_counts = defaultdict(int)
        for event in recent_events:
            ip_counts[event.ip_address] += 1
        top_threat_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Calculate threat trends (last 24 hours in hourly buckets)
        threat_trends = defaultdict(list)
        for i in range(24):
            hour_start = now - timedelta(hours=i+1)
            hour_end = now - timedelta(hours=i)
            hour_events = [e for e in self.threat_events 
                          if hour_start <= e.timestamp < hour_end]
            threat_trends['threat_scores'].append(
                sum(e.threat_score for e in hour_events) // max(1, len(hour_events))
            )
            threat_trends['blocked_requests'].append(len([e for e in hour_events if e.blocked]))
        
        # Calculate average threat score
        avg_score = sum(e.threat_score for e in recent_events) // max(1, total_requests)
        
        return ThreatMetrics(
            total_requests=total_requests,
            blocked_requests=blocked_requests,
            threats_detected=dict(threats_detected),
            top_threat_ips=top_threat_ips,
            threat_trends=dict(threat_trends),
            average_threat_score=avg_score
        )
    
    def block_ip(self, ip_address: str, reason: str = None, duration: int = 3600):
        """Manually block an IP address"""
        self.blocked_ips.add(ip_address)
        
        if self.detector.ip_reputation.redis_client:
            block_key = f"{ThreatConfig.REDIS_PREFIX}:blocked:{ip_address}"
            self.detector.ip_reputation.redis_client.setex(block_key, duration, reason or 'manual_block')
        
        self.logger.info(f"Manually blocked IP {ip_address} for {duration} seconds - {reason}")
    
    def unblock_ip(self, ip_address: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip_address)
        
        if self.detector.ip_reputation.redis_client:
            block_key = f"{ThreatConfig.REDIS_PREFIX}:blocked:{ip_address}"
            self.detector.ip_reputation.redis_client.delete(block_key)
        
        self.logger.info(f"Unblocked IP {ip_address}")
    
    def cleanup_old_events(self):
        """Clean up old threat events"""
        cutoff_time = datetime.now() - timedelta(days=7)
        original_count = len(self.threat_events)
        
        self.threat_events = [event for event in self.threat_events 
                             if event.timestamp > cutoff_time]
        
        removed_count = original_count - len(self.threat_events)
        if removed_count > 0:
            self.logger.info(f"Cleaned up {removed_count} old threat events")


# Initialize global threat protection
threat_protection = ThreatProtectionMiddleware()
