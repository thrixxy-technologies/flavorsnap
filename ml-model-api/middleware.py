"""
Middleware Management System for API Gateway
Provides request/response processing pipeline with configurable middleware components
"""

import logging
import time
import json
import hashlib
import re
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)

class MiddlewareType(Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMITING = "rate_limiting"
    LOGGING = "logging"
    SECURITY = "security"
    TRANSFORMATION = "transformation"
    VALIDATION = "validation"
    MONITORING = "monitoring"
    CUSTOM = "custom"

@dataclass
class MiddlewareContext:
    """Context object passed through middleware chain"""
    request_id: str
    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, str]
    client_ip: str
    start_time: float
    user: Optional[Dict[str, Any]] = None
    response_status: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    response_body: Optional[bytes] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class Middleware(ABC):
    """Abstract base class for middleware components"""
    
    def __init__(self, name: str, middleware_type: MiddlewareType, priority: int = 100):
        self.name = name
        self.type = middleware_type
        self.priority = priority
        self.enabled = True
    
    @abstractmethod
    def process_request(self, context: MiddlewareContext) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """
        Process incoming request
        Returns error response if request should be rejected, None otherwise
        """
        pass
    
    @abstractmethod
    def process_response(self, context: MiddlewareContext) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """
        Process outgoing response
        Returns modified response if needed, None otherwise
        """
        pass

class LoggingMiddleware(Middleware):
    """Request/response logging middleware"""
    
    def __init__(self, log_level: str = "INFO", log_body: bool = False):
        super().__init__("logging", MiddlewareType.LOGGING, priority=10)
        self.log_level = getattr(logging, log_level.upper())
        self.log_body = log_body
    
    def process_request(self, context: MiddlewareContext) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """Log incoming request"""
        logger.log(self.log_level, 
                  f"[{context.request_id}] {context.method} {context.path} "
                  f"from {context.client_ip}")
        
        # Log headers if in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"[{context.request_id}] Headers: {context.headers}")
            logger.debug(f"[{context.request_id}] Query: {context.query_params}")
        
        return None
    
    def process_response(self, context: MiddlewareContext) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """Log outgoing response"""
        duration = time.time() - context.start_time
        logger.log(self.log_level,
                  f"[{context.request_id}] {context.response_status} "
                  f"completed in {duration:.3f}s")
        
        # Log response body if enabled and not too large
        if self.log_body and context.response_body and len(context.response_body) < 1000:
            try:
                body_str = context.response_body.decode('utf-8')
                logger.debug(f"[{context.request_id}] Response body: {body_str}")
            except UnicodeDecodeError:
                logger.debug(f"[{context.request_id}] Response body: [binary data]")
        
        return None

class RateLimitMiddleware(Middleware):
    """Rate limiting middleware using token bucket algorithm"""
    
    def __init__(self, default_limit: int = 100, default_window: int = 60):
        super().__init__("rate_limit", MiddlewareType.RATE_LIMITING, priority=50)
        self.default_limit = default_limit
        self.default_window = default_window
        
        # Rate limit storage: {key: {tokens: int, last_refill: float, window: int}}
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
    
    def process_request(self, context: MiddlewareContext) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """Check rate limits"""
        # Use client IP as default key
        key = context.client_ip
        
        # Check for custom rate limit in headers or metadata
        limit = self.default_limit
        window = self.default_window
        
        # Could be extended to check user-specific limits
        if context.user and 'rate_limit' in context.user:
            limit = context.user['rate_limit']
        
        with self.lock:
            if key not in self.rate_limits:
                self.rate_limits[key] = {
                    'tokens': limit,
                    'last_refill': time.time(),
                    'window': window,
                    'limit': limit
                }
            
            rate_limit = self.rate_limits[key]
            current_time = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = current_time - rate_limit['last_refill']
            tokens_to_add = int(elapsed * rate_limit['limit'] / rate_limit['window'])
            
            if tokens_to_add > 0:
                rate_limit['tokens'] = min(rate_limit['limit'], 
                                          rate_limit['tokens'] + tokens_to_add)
                rate_limit['last_refill'] = current_time
            
            # Check if request is allowed
            if rate_limit['tokens'] > 0:
                rate_limit['tokens'] -= 1
                logger.debug(f"[{context.request_id}] Rate limit check passed: "
                           f"{rate_limit['tokens']}/{rate_limit['limit']} tokens remaining")
                return None
            else:
                logger.warning(f"[{context.request_id}] Rate limit exceeded for {key}")
                return (429, 
                       {"Content-Type": "application/json", 
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(current_time + window))},
                       json.dumps({
                           "error": "Too Many Requests",
                           "message": "Rate limit exceeded",
                           "request_id": context.request_id
                       }).encode())
    
    def process_response(self, context: MiddlewareContext) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """Add rate limit headers to response"""
        key = context.client_ip
        
        with self.lock:
            if key in self.rate_limits:
                rate_limit = self.rate_limits[key]
                if context.response_headers:
                    context.response_headers.update({
                        "X-RateLimit-Limit": str(rate_limit['limit']),
                        "X-RateLimit-Remaining": str(max(0, rate_limit['tokens'])),
                        "X-RateLimit-Reset": str(int(time.time() + rate_limit['window']))
                    })
        
        return None

class SecurityMiddleware(Middleware):
    """Security middleware for common security checks"""
    
    def __init__(self):
        super().__init__("security", MiddlewareType.SECURITY, priority=30)
        
        # Common attack patterns
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)"
        ]
        
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>"
        ]
        
        self.path_traversal_patterns = [
            r"\.\.[\\/]",
            r"%2e%2e[\\/]",
            r"\.\.%2f",
            r"%2e%2e%2f"
        ]
    
    def process_request(self, context: MiddlewareContext) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """Perform security checks"""
        # Check for common attacks in query parameters
        for param_name, param_value in context.query_params.items():
            if self._check_sql_injection(param_value):
                logger.warning(f"[{context.request_id}] SQL injection detected in parameter {param_name}")
                return self._security_violation_response("SQL injection detected")
            
            if self._check_xss(param_value):
                logger.warning(f"[{context.request_id}] XSS detected in parameter {param_name}")
                return self._security_violation_response("XSS detected")
        
        # Check path traversal
        if self._check_path_traversal(context.path):
            logger.warning(f"[{context.request_id}] Path traversal detected in path {context.path}")
            return self._security_violation_response("Path traversal detected")
        
        # Check for suspicious headers
        for header_name, header_value in context.headers.items():
            if self._check_sql_injection(header_value) or self._check_xss(header_value):
                logger.warning(f"[{context.request_id}] Attack detected in header {header_name}")
                return self._security_violation_response("Malicious headers detected")
        
        return None
    
    def process_response(self, context: MiddlewareContext) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """Add security headers to response"""
        if context.response_headers:
            security_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": "default-src 'self'",
                "Referrer-Policy": "strict-origin-when-cross-origin"
            }
            context.response_headers.update(security_headers)
        
        return None
    
    def _check_sql_injection(self, value: str) -> bool:
        """Check for SQL injection patterns"""
        value_upper = value.upper()
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, value_upper, re.IGNORECASE):
                return True
        return False
    
    def _check_xss(self, value: str) -> bool:
        """Check for XSS patterns"""
        for pattern in self.xss_patterns:
            if re.search(pattern, value, re.IGNORECASE | re.DOTALL):
                return True
        return False
    
    def _check_path_traversal(self, path: str) -> bool:
        """Check for path traversal patterns"""
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        return False
    
    def _security_violation_response(self, message: str) -> Tuple[int, Dict[str, str], bytes]:
        """Create security violation response"""
        return (403, 
               {"Content-Type": "application/json"},
               json.dumps({
                   "error": "Forbidden",
                   "message": message,
                   "request_id": ""
               }).encode())

class AuthenticationMiddleware(Middleware):
    """JWT-based authentication middleware"""
    
    def __init__(self, jwt_secret: str, required_paths: List[str] = None):
        super().__init__("authentication", MiddlewareType.AUTHENTICATION, priority=40)
        self.jwt_secret = jwt_secret
        self.required_paths = required_paths or []
    
    def process_request(self, context: MiddlewareContext) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """Check authentication for protected paths"""
        # Check if path requires authentication
        if not self._path_requires_auth(context.path):
            return None
        
        # Get Authorization header
        auth_header = context.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            logger.warning(f"[{context.request_id}] Missing or invalid Authorization header")
            return (401, 
                   {"Content-Type": "application/json"},
                   json.dumps({
                       "error": "Unauthorized",
                       "message": "Authentication required",
                       "request_id": context.request_id
                   }).encode())
        
        # Extract and validate token
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        try:
            # This would integrate with the existing JWT handler
            # For now, just set a mock user
            context.user = {
                'id': 'test-user',
                'roles': ['user'],
                'authenticated': True
            }
            return None
        except Exception as e:
            logger.warning(f"[{context.request_id}] Invalid JWT token: {e}")
            return (401, 
                   {"Content-Type": "application/json"},
                   json.dumps({
                       "error": "Unauthorized",
                       "message": "Invalid authentication token",
                       "request_id": context.request_id
                   }).encode())
    
    def process_response(self, context: MiddlewareContext) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """No response processing needed for authentication"""
        return None
    
    def _path_requires_auth(self, path: str) -> bool:
        """Check if path requires authentication"""
        for protected_path in self.required_paths:
            if path.startswith(protected_path):
                return True
        return False

class RequestTransformationMiddleware(Middleware):
    """Request/response transformation middleware"""
    
    def __init__(self, transformations: Dict[str, Dict[str, Any]] = None):
        super().__init__("transformation", MiddlewareType.TRANSFORMATION, priority=60)
        self.transformations = transformations or {}
    
    def process_request(self, context: MiddlewareContext) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """Transform incoming request"""
        # Add gateway headers
        context.headers['X-Gateway-Request-ID'] = context.request_id
        context.headers['X-Gateway-Timestamp'] = str(int(time.time()))
        
        # Could add request body transformations here
        # For example: JSON normalization, field mapping, etc.
        
        return None
    
    def process_response(self, context: MiddlewareContext) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """Transform outgoing response"""
        if context.response_body and context.response_headers:
            content_type = context.response_headers.get('Content-Type', '')
            
            # Transform JSON responses
            if 'application/json' in content_type:
                try:
                    response_data = json.loads(context.response_body.decode('utf-8'))
                    
                    # Add gateway metadata
                    if isinstance(response_data, dict):
                        response_data['_gateway'] = {
                            'request_id': context.request_id,
                            'processing_time': time.time() - context.start_time,
                            'version': '1.0.0'
                        }
                    
                    # Update response body
                    context.response_body = json.dumps(response_data).encode('utf-8')
                    
                    # Update content-length header
                    context.response_headers['Content-Length'] = str(len(context.response_body))
                    
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Not JSON or not UTF-8, skip transformation
                    pass
        
        return None

class MiddlewareManager:
    """Manages middleware registration and execution"""
    
    def __init__(self):
        self.middleware_registry: Dict[str, Middleware] = {}
        self.middleware_chains: Dict[str, List[str]] = {}
        self.global_chain: List[str] = []
    
    def register_middleware(self, name: str, middleware: Middleware):
        """Register a middleware component"""
        self.middleware_registry[name] = middleware
        logger.info(f"Registered middleware: {name} ({middleware.type.value})")
    
    def unregister_middleware(self, name: str):
        """Unregister a middleware component"""
        if name in self.middleware_registry:
            del self.middleware_registry[name]
            logger.info(f"Unregistered middleware: {name}")
    
    def create_chain(self, chain_name: str, middleware_names: List[str]):
        """Create a named middleware chain"""
        # Validate middleware names
        for name in middleware_names:
            if name not in self.middleware_registry:
                raise ValueError(f"Middleware '{name}' not found")
        
        self.middleware_chains[chain_name] = middleware_names
        logger.info(f"Created middleware chain '{chain_name}' with {len(middleware_names)} components")
    
    def set_global_chain(self, middleware_names: List[str]):
        """Set the global middleware chain"""
        # Validate middleware names
        for name in middleware_names:
            if name not in self.middleware_registry:
                raise ValueError(f"Middleware '{name}' not found")
        
        self.global_chain = middleware_names
        logger.info(f"Set global middleware chain with {len(middleware_names)} components")
    
    def apply_pre_request(self, context: MiddlewareContext, chain_name: Optional[str] = None) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """Apply pre-request middleware chain"""
        # Determine which chain to use
        if chain_name and chain_name in self.middleware_chains:
            middleware_names = self.middleware_chains[chain_name]
        else:
            middleware_names = self.global_chain
        
        # Sort by priority
        middleware_list = []
        for name in middleware_names:
            if name in self.middleware_registry:
                middleware_list.append(self.middleware_registry[name])
        
        middleware_list.sort(key=lambda m: m.priority)
        
        # Apply middleware in order
        for middleware in middleware_list:
            if not middleware.enabled:
                continue
            
            try:
                result = middleware.process_request(context)
                if result:
                    # Middleware rejected the request
                    return result
            except Exception as e:
                logger.error(f"Middleware {middleware.name} error: {e}")
                return (500, 
                       {"Content-Type": "application/json"},
                       json.dumps({
                           "error": "Internal Server Error",
                           "message": "Middleware processing error",
                           "request_id": context.request_id
                       }).encode())
        
        return None
    
    def apply_post_request(self, context: MiddlewareContext, chain_name: Optional[str] = None) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """Apply post-request middleware chain"""
        # Determine which chain to use
        if chain_name and chain_name in self.middleware_chains:
            middleware_names = self.middleware_chains[chain_name]
        else:
            middleware_names = self.global_chain
        
        # Sort by priority (reverse order for post-processing)
        middleware_list = []
        for name in middleware_names:
            if name in self.middleware_registry:
                middleware_list.append(self.middleware_registry[name])
        
        middleware_list.sort(key=lambda m: m.priority, reverse=True)
        
        # Apply middleware in reverse order
        for middleware in middleware_list:
            if not middleware.enabled:
                continue
            
            try:
                result = middleware.process_response(context)
                if result:
                    # Middleware modified the response
                    return result
            except Exception as e:
                logger.error(f"Middleware {middleware.name} error: {e}")
                # Don't fail the request for post-processing errors
                continue
        
        return None
    
    def get_middleware_stats(self) -> Dict[str, Any]:
        """Get middleware statistics"""
        stats = {
            'total_middleware': len(self.middleware_registry),
            'enabled_middleware': sum(1 for m in self.middleware_registry.values() if m.enabled),
            'middleware_types': defaultdict(int),
            'chains': len(self.middleware_chains),
            'global_chain_length': len(self.global_chain)
        }
        
        for middleware in self.middleware_registry.values():
            stats['middleware_types'][middleware.type.value] += 1
        
        return dict(stats)

# Example usage
if __name__ == "__main__":
    # Create middleware manager
    manager = MiddlewareManager()
    
    # Register middleware
    manager.register_middleware('logging', LoggingMiddleware())
    manager.register_middleware('rate_limit', RateLimitMiddleware())
    manager.register_middleware('security', SecurityMiddleware())
    manager.register_middleware('auth', AuthenticationMiddleware('secret'))
    manager.register_middleware('transform', RequestTransformationMiddleware())
    
    # Set global chain
    manager.set_global_chain(['logging', 'security', 'rate_limit', 'transform'])
    
    # Create specialized chain for authenticated endpoints
    manager.create_chain('auth_chain', ['logging', 'security', 'auth', 'rate_limit', 'transform'])
    
    # Test middleware processing
    context = MiddlewareContext(
        request_id='test-123',
        method='GET',
        path='/api/test',
        headers={'Host': 'example.com'},
        query_params={'param': 'value'},
        client_ip='192.168.1.1',
        start_time=time.time()
    )
    
    # Apply pre-request middleware
    result = manager.apply_pre_request(context)
    if result:
        print("Request rejected:", result)
    else:
        print("Request allowed")
    
    # Simulate response
    context.response_status = 200
    context.response_headers = {'Content-Type': 'application/json'}
    context.response_body = b'{"message": "success"}'
    
    # Apply post-request middleware
    result = manager.apply_post_request(context)
    if result:
        print("Response modified:", result)
    else:
        print("Response unchanged")
