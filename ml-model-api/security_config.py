"""
Advanced API Rate Limiting and Security Configuration for FlavorSnap
Implements sophisticated rate limiting with user-based limits, burst handling, and analytics
"""

import time
import threading
import json
import hashlib
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class UserType(Enum):
    """User types for rate limiting"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    ADMIN = "admin"

class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"

@dataclass
class RateLimitConfig:
    """Rate limit configuration for a user type"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_capacity: int = 10
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    bypass_allowed: bool = False
    priority_weight: float = 1.0

@dataclass
class RateLimitState:
    """Rate limit state for a client"""
    user_id: str
    user_type: UserType
    ip_address: str
    request_count: int = 0
    last_request_time: datetime = field(default_factory=datetime.now)
    window_start: datetime = field(default_factory=datetime.now)
    tokens: float = field(default_factory=lambda: 60.0)  # Token bucket
    last_refill: datetime = field(default_factory=datetime.now)
    burst_tokens: int = field(default_factory=lambda: 10)
    violation_count: int = 0
    last_violation: Optional[datetime] = None
    is_blocked: bool = False
    block_expires: Optional[datetime] = None

@dataclass
class RateLimitEvent:
    """Rate limit event for analytics"""
    timestamp: datetime
    user_id: str
    user_type: UserType
    ip_address: str
    endpoint: str
    action: str  # 'allowed', 'blocked', 'warning'
    current_rate: float
    limit: float
    remaining: float
    response_time_ms: Optional[float] = None

class RateLimitAnalytics:
    """Analytics for rate limiting"""
    
    def __init__(self, max_events: int = 100000):
        self.max_events = max_events
        self.events: deque = deque(maxlen=max_events)
        self._lock = threading.RLock()
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'warnings': 0,
            'unique_users': set(),
            'unique_ips': set(),
            'endpoint_stats': defaultdict(lambda: {'requests': 0, 'blocked': 0}),
            'user_type_stats': defaultdict(lambda: {'requests': 0, 'blocked': 0})
        }
    
    def record_event(self, event: RateLimitEvent):
        """Record a rate limit event"""
        with self._lock:
            self.events.append(event)
            
            # Update statistics
            self.stats['total_requests'] += 1
            self.stats['unique_users'].add(event.user_id)
            self.stats['unique_ips'].add(event.ip_address)
            
            if event.action == 'blocked':
                self.stats['blocked_requests'] += 1
                self.stats['endpoint_stats'][event.endpoint]['blocked'] += 1
                self.stats['user_type_stats'][event.user_type.value]['blocked'] += 1
            elif event.action == 'warning':
                self.stats['warnings'] += 1
            
            self.stats['endpoint_stats'][event.endpoint]['requests'] += 1
            self.stats['user_type_stats'][event.user_type.value]['requests'] += 1
    
    def get_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get analytics for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            recent_events = [e for e in self.events if e.timestamp >= cutoff_time]
            
            if not recent_events:
                return {'period_hours': hours, 'no_data': True}
            
            # Calculate metrics
            total_requests = len(recent_events)
            blocked_requests = sum(1 for e in recent_events if e.action == 'blocked')
            warnings = sum(1 for e in recent_events if e.action == 'warning')
            
            # Top endpoints
            endpoint_counts = defaultdict(int)
            for event in recent_events:
                endpoint_counts[event.endpoint] += 1
            
            top_endpoints = sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # User type distribution
            user_type_counts = defaultdict(int)
            for event in recent_events:
                user_type_counts[event.user_type.value] += 1
            
            # Hourly distribution
            hourly_counts = defaultdict(int)
            for event in recent_events:
                hour = event.timestamp.replace(minute=0, second=0, microsecond=0)
                hourly_counts[hour] += 1
            
            return {
                'period_hours': hours,
                'total_requests': total_requests,
                'blocked_requests': blocked_requests,
                'warnings': warnings,
                'block_rate': (blocked_requests / total_requests * 100) if total_requests > 0 else 0,
                'unique_users': len(set(e.user_id for e in recent_events)),
                'unique_ips': len(set(e.ip_address for e in recent_events)),
                'top_endpoints': [{'endpoint': ep, 'count': cnt} for ep, cnt in top_endpoints],
                'user_type_distribution': dict(user_type_counts),
                'hourly_distribution': {str(k): v for k, v in hourly_counts.items()},
                'current_stats': {
                    'total_requests': self.stats['total_requests'],
                    'blocked_requests': self.stats['blocked_requests'],
                    'unique_users': len(self.stats['unique_users']),
                    'unique_ips': len(self.stats['unique_ips'])
                }
            }
    
    def get_user_analytics(self, user_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get analytics for a specific user"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            user_events = [e for e in self.events 
                          if e.user_id == user_id and e.timestamp >= cutoff_time]
            
            if not user_events:
                return {'user_id': user_id, 'period_hours': hours, 'no_data': True}
            
            total_requests = len(user_events)
            blocked_requests = sum(1 for e in user_events if e.action == 'blocked')
            
            # Endpoint usage
            endpoint_usage = defaultdict(int)
            for event in user_events:
                endpoint_usage[event.endpoint] += 1
            
            return {
                'user_id': user_id,
                'period_hours': hours,
                'total_requests': total_requests,
                'blocked_requests': blocked_requests,
                'block_rate': (blocked_requests / total_requests * 100) if total_requests > 0 else 0,
                'top_endpoints': sorted(endpoint_usage.items(), key=lambda x: x[1], reverse=True)[:5],
                'first_request': min(e.timestamp for e in user_events).isoformat(),
                'last_request': max(e.timestamp for e in user_events).isoformat()
            }

class DynamicRateLimiter:
    """Dynamic rate limiter with adaptive limits"""
    
    def __init__(self, base_config: RateLimitConfig):
        self.base_config = base_config
        self.load_factor = 1.0
        self.last_adjustment = datetime.now()
        self._lock = threading.RLock()
        
        # Load metrics
        self.recent_loads = deque(maxlen=100)  # Last 100 load measurements
        self.violation_rate = 0.0
        self.adjustment_history = []
    
    def update_load_metrics(self, current_load: float):
        """Update system load metrics"""
        with self._lock:
            self.recent_loads.append(current_load)
            
            # Calculate average load
            avg_load = sum(self.recent_loads) / len(self.recent_loads) if self.recent_loads else 1.0
            
            # Adjust load factor based on system load
            if avg_load > 0.8:  # High load
                self.load_factor = max(0.5, self.load_factor * 0.95)
            elif avg_load < 0.3:  # Low load
                self.load_factor = min(2.0, self.load_factor * 1.05)
            
            self.last_adjustment = datetime.now()
            self.adjustment_history.append({
                'timestamp': self.last_adjustment,
                'load_factor': self.load_factor,
                'avg_load': avg_load
            })
    
    def get_adjusted_config(self) -> RateLimitConfig:
        """Get adjusted rate limit configuration"""
        with self._lock:
            return RateLimitConfig(
                requests_per_minute=int(self.base_config.requests_per_minute * self.load_factor),
                requests_per_hour=int(self.base_config.requests_per_hour * self.load_factor),
                requests_per_day=int(self.base_config.requests_per_day * self.load_factor),
                burst_capacity=max(1, int(self.base_config.burst_capacity * self.load_factor)),
                strategy=self.base_config.strategy,
                bypass_allowed=self.base_config.bypass_allowed,
                priority_weight=self.base_config.priority_weight
            )
    
    def get_adjustment_stats(self) -> Dict[str, Any]:
        """Get adjustment statistics"""
        with self._lock:
            return {
                'current_load_factor': self.load_factor,
                'last_adjustment': self.last_adjustment.isoformat(),
                'recent_loads_avg': sum(self.recent_loads) / len(self.recent_loads) if self.recent_loads else 0,
                'adjustment_count': len(self.adjustment_history),
                'recent_adjustments': self.adjustment_history[-10:] if self.adjustment_history else []
            }

class TokenBucketLimiter:
    """Token bucket rate limiter implementation"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self._lock = threading.RLock()
    
    def consume_token(self, state: RateLimitState, config: RateLimitConfig) -> Tuple[bool, float]:
        """Consume a token from the bucket"""
        with self._lock:
            now = datetime.now()
            
            # Calculate time since last refill
            time_delta = (now - state.last_refill).total_seconds()
            
            # Refill tokens
            tokens_to_add = time_delta * self.refill_rate
            state.tokens = min(config.requests_per_minute, state.tokens + tokens_to_add)
            state.last_refill = now
            
            # Check if we have enough tokens
            if state.tokens >= 1.0:
                state.tokens -= 1.0
                return True, state.tokens
            
            return False, state.tokens

class SlidingWindowLimiter:
    """Sliding window rate limiter implementation"""
    
    def __init__(self, window_size_seconds: int):
        self.window_size = window_size_seconds
        self._lock = threading.RLock()
    
    def check_request(self, state: RateLimitState, config: RateLimitConfig) -> Tuple[bool, int]:
        """Check if request is allowed in sliding window"""
        with self._lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_size)
            
            # This would need to be integrated with a request history store
            # For now, we'll use a simplified approach
            time_in_window = (now - state.window_start).total_seconds()
            
            if time_in_window >= self.window_size:
                # Reset window
                state.window_start = now
                state.request_count = 1
                return True, config.requests_per_minute - 1
            
            if state.request_count < config.requests_per_minute:
                state.request_count += 1
                return True, config.requests_per_minute - state.request_count
            
            return False, 0

class AdvancedRateLimiter:
    """Advanced rate limiter with multiple strategies and analytics"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.analytics = RateLimitAnalytics()
        self._lock = threading.RLock()
        
        # Rate limit configurations by user type
        self.rate_configs = self._init_rate_configs()
        
        # Dynamic limiters
        self.dynamic_limiters = {
            user_type: DynamicRateLimiter(config) 
            for user_type, config in self.rate_configs.items()
        }
        
        # Client states
        self.client_states: Dict[str, RateLimitState] = {}
        
        # Strategy implementations
        self.token_bucket = TokenBucketLimiter(60, 1.0)  # 60 tokens, 1 token/second
        self.sliding_window = SlidingWindowLimiter(60)  # 60-second window
        
        # Background cleanup thread
        self._cleanup_thread = threading.Thread(target=self._background_cleanup, daemon=True)
        self._cleanup_stop_event = threading.Event()
        self._cleanup_thread.start()
    
    def _init_rate_configs(self) -> Dict[UserType, RateLimitConfig]:
        """Initialize rate limit configurations"""
        return {
            UserType.FREE: RateLimitConfig(
                requests_per_minute=10,
                requests_per_hour=100,
                requests_per_day=500,
                burst_capacity=5,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                bypass_allowed=False,
                priority_weight=0.5
            ),
            UserType.BASIC: RateLimitConfig(
                requests_per_minute=30,
                requests_per_hour=500,
                requests_per_day=2000,
                burst_capacity=10,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                bypass_allowed=False,
                priority_weight=0.75
            ),
            UserType.PREMIUM: RateLimitConfig(
                requests_per_minute=100,
                requests_per_hour=2000,
                requests_per_day=10000,
                burst_capacity=20,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                bypass_allowed=True,
                priority_weight=1.5
            ),
            UserType.ENTERPRISE: RateLimitConfig(
                requests_per_minute=500,
                requests_per_hour=10000,
                requests_per_day=100000,
                burst_capacity=50,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                bypass_allowed=True,
                priority_weight=2.0
            ),
            UserType.ADMIN: RateLimitConfig(
                requests_per_minute=1000,
                requests_per_hour=50000,
                requests_per_day=1000000,
                burst_capacity=100,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                bypass_allowed=True,
                priority_weight=10.0
            )
        }
    
    def get_client_identifier(self, request) -> str:
        """Get unique client identifier from request"""
        # Try to get user ID from headers or session
        user_id = request.headers.get('X-User-ID') or request.headers.get('User-ID')
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        ip = self._get_client_ip(request)
        return f"ip:{ip}"
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address"""
        # Check for forwarded headers
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip.strip()
        
        # Fall back to remote address
        return request.remote_addr or 'unknown'
    
    def get_user_type(self, request) -> UserType:
        """Determine user type from request"""
        user_type_header = request.headers.get('X-User-Type') or request.headers.get('User-Type')
        
        if user_type_header:
            try:
                return UserType(user_type_header.lower())
            except ValueError:
                pass
        
        # Check for API key that indicates premium/enterprise
        api_key = request.headers.get('X-API-Key') or request.headers.get('API-Key')
        if api_key:
            # This would integrate with your user management system
            if api_key.startswith('ent_'):
                return UserType.ENTERPRISE
            elif api_key.startswith('premium_'):
                return UserType.PREMIUM
            elif api_key.startswith('basic_'):
                return UserType.BASIC
        
        # Default to free tier
        return UserType.FREE
    
    def check_rate_limit(self, request, endpoint: str = None) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed"""
        start_time = time.time()
        
        try:
            client_id = self.get_client_identifier(request)
            user_type = self.get_user_type(request)
            ip_address = self._get_client_ip(request)
            endpoint = endpoint or request.endpoint or 'unknown'
            
            # Get or create client state
            with self._lock:
                if client_id not in self.client_states:
                    self.client_states[client_id] = RateLimitState(
                        user_id=client_id,
                        user_type=user_type,
                        ip_address=ip_address
                    )
                
                state = self.client_states[client_id]
            
            # Check if user is blocked
            if state.is_blocked and state.block_expires and datetime.now() < state.block_expires:
                self.analytics.record_event(RateLimitEvent(
                    timestamp=datetime.now(),
                    user_id=client_id,
                    user_type=user_type,
                    ip_address=ip_address,
                    endpoint=endpoint,
                    action='blocked',
                    current_rate=0,
                    limit=0,
                    remaining=0,
                    response_time_ms=(time.time() - start_time) * 1000
                ))
                
                return False, {
                    'allowed': False,
                    'reason': 'blocked',
                    'retry_after': int((state.block_expires - datetime.now()).total_seconds()),
                    'user_type': user_type.value
                }
            
            # Get adjusted configuration
            dynamic_limiter = self.dynamic_limiters[user_type]
            config = dynamic_limiter.get_adjusted_config()
            
            # Check bypass for premium users
            if config.bypass_allowed and request.headers.get('X-Rate-Limit-Bypass') == 'true':
                self.analytics.record_event(RateLimitEvent(
                    timestamp=datetime.now(),
                    user_id=client_id,
                    user_type=user_type,
                    ip_address=ip_address,
                    endpoint=endpoint,
                    action='allowed',
                    current_rate=0,
                    limit=float('inf'),
                    remaining=float('inf'),
                    response_time_ms=(time.time() - start_time) * 1000
                ))
                
                return True, {
                    'allowed': True,
                    'reason': 'bypass',
                    'user_type': user_type.value,
                    'bypass_used': True
                }
            
            # Apply rate limiting strategy
            allowed, remaining = self._apply_strategy(state, config)
            
            # Update state
            state.last_request_time = datetime.now()
            
            # Handle violations
            if not allowed:
                state.violation_count += 1
                state.last_violation = datetime.now()
                
                # Block user if too many violations
                if state.violation_count >= 10:
                    state.is_blocked = True
                    state.block_expires = datetime.now() + timedelta(minutes=30)
                
                action = 'blocked'
            else:
                action = 'allowed'
                if remaining < config.burst_capacity:
                    action = 'warning'  # Approaching limit
            
            # Record analytics
            current_rate = self._calculate_current_rate(state)
            self.analytics.record_event(RateLimitEvent(
                timestamp=datetime.now(),
                user_id=client_id,
                user_type=user_type,
                ip_address=ip_address,
                endpoint=endpoint,
                action=action,
                current_rate=current_rate,
                limit=config.requests_per_minute,
                remaining=remaining,
                response_time_ms=(time.time() - start_time) * 1000
            ))
            
            return allowed, {
                'allowed': allowed,
                'remaining': remaining,
                'limit': config.requests_per_minute,
                'reset_time': (state.last_refill + timedelta(seconds=60)).isoformat(),
                'user_type': user_type.value,
                'retry_after': 60 if not allowed else None
            }
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Fail open - allow request on error
            return True, {'allowed': True, 'error': str(e)}
    
    def _apply_strategy(self, state: RateLimitState, config: RateLimitConfig) -> Tuple[bool, float]:
        """Apply rate limiting strategy"""
        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return self.token_bucket.consume_token(state, config)
        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return self.sliding_window.check_request(state, config)
        else:
            # Default to token bucket
            return self.token_bucket.consume_token(state, config)
    
    def _calculate_current_rate(self, state: RateLimitState) -> float:
        """Calculate current request rate"""
        if state.last_request_time == state.window_start:
            return 1.0
        
        time_diff = (datetime.now() - state.window_start).total_seconds()
        if time_diff <= 0:
            return 0.0
        
        return state.request_count / time_diff
    
    def update_system_load(self, load_factor: float):
        """Update system load for dynamic adjustment"""
        for dynamic_limiter in self.dynamic_limiters.values():
            dynamic_limiter.update_load_metrics(load_factor)
    
    def get_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive analytics"""
        return {
            'rate_limit_analytics': self.analytics.get_analytics(hours),
            'dynamic_adjustments': {
                user_type.value: limiter.get_adjustment_stats()
                for user_type, limiter in self.dynamic_limiters.items()
            },
            'active_clients': len(self.client_states),
            'blocked_clients': sum(1 for s in self.client_states.values() if s.is_blocked)
        }
    
    def get_user_analytics(self, user_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get analytics for specific user"""
        return self.analytics.get_user_analytics(user_id, hours)
    
    def unblock_user(self, user_id: str) -> bool:
        """Unblock a user"""
        with self._lock:
            if user_id in self.client_states:
                state = self.client_states[user_id]
                state.is_blocked = False
                state.block_expires = None
                state.violation_count = 0
                return True
            return False
    
    def _background_cleanup(self):
        """Background cleanup of expired states"""
        while not self._cleanup_stop_event.is_set():
            try:
                with self._lock:
                    now = datetime.now()
                    expired_keys = []
                    
                    for key, state in self.client_states.items():
                        # Clean up states inactive for more than 24 hours
                        if (now - state.last_request_time).total_seconds() > 86400:
                            expired_keys.append(key)
                        
                        # Unblock expired blocks
                        if state.is_blocked and state.block_expires and now >= state.block_expires:
                            state.is_blocked = False
                            state.block_expires = None
                    
                    for key in expired_keys:
                        del self.client_states[key]
                
                # Sleep for 5 minutes
                self._cleanup_stop_event.wait(300)
                
            except Exception as e:
                logger.error(f"Rate limiter cleanup error: {e}")
                self._cleanup_stop_event.wait(60)
    
    def shutdown(self):
        """Shutdown rate limiter"""
        logger.info("Shutting down rate limiter")
        self._cleanup_stop_event.set()
        self._cleanup_thread.join(timeout=5)
        logger.info("Rate limiter shutdown complete")

# Global rate limiter instance
_rate_limiter: Optional[AdvancedRateLimiter] = None

def get_rate_limiter() -> AdvancedRateLimiter:
    """Get global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = AdvancedRateLimiter()
    return _rate_limiter

def init_rate_limiter(config: Optional[Dict[str, Any]] = None) -> AdvancedRateLimiter:
    """Initialize rate limiter with configuration"""
    global _rate_limiter
    _rate_limiter = AdvancedRateLimiter(config)
    return _rate_limiter

def rate_limit(limit_config: Optional[Dict[str, Any]] = None):
    """Rate limiting decorator for Flask routes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            limiter = get_rate_limiter()
            
            # Get Flask request context
            from flask import request, g
            
            # Check rate limit
            allowed, limit_info = limiter.check_rate_limit(request)
            
            # Store limit info in Flask g for response headers
            g.rate_limit_info = limit_info
            
            if not allowed:
                from flask import jsonify
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Rate limit exceeded. Try again in {limit_info.get("retry_after", 60)} seconds.',
                    'retry_after': limit_info.get('retry_after'),
                    'limit': limit_info.get('limit'),
                    'user_type': limit_info.get('user_type')
                })
                response.status_code = 429
                return response
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def add_rate_limit_headers(response):
    """Add rate limit headers to response"""
    from flask import g
    
    if hasattr(g, 'rate_limit_info'):
        info = g.rate_limit_info
        
        if info.get('allowed'):
            response.headers['X-RateLimit-Limit'] = str(info.get('limit', 'N/A'))
            response.headers['X-RateLimit-Remaining'] = str(info.get('remaining', 'N/A'))
            response.headers['X-RateLimit-Reset'] = info.get('reset_time', '')
            response.headers['X-User-Type'] = info.get('user_type', 'unknown')
            
            if info.get('bypass_used'):
                response.headers['X-RateLimit-Bypass'] = 'true'
        
        response.headers['X-RateLimit-Allowed'] = str(info.get('allowed', 'false'))
    
    return response
