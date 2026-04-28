"""
Authentication Handlers for FlavorSnap API
Implements comprehensive authentication with JWT, OAuth2, session management,
and multi-factor authentication
"""
import os
import uuid
import secrets
import logging
import hashlib
import pyotp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from functools import wraps
from flask import request, jsonify, current_app, session

# Import user and security modules
from user_handlers import (
    user_manager, User, UserRole, UserStatus, 
    PasswordPolicy, Permission
)
from jwt_handler import jwt_token_manager, JWTPayload, TokenInfo
from oauth2_handler import oauth2_handler, OAuth2Token
from security_config import InputValidator, RateLimitManager


class AuthenticationMethod(str):
    """Authentication methods"""
    PASSWORD = "password"
    TWO_FACTOR = "two_factor"
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    SESSION = "session"


@dataclass
class AuthSession:
    """Authentication session"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    is_active: bool = True
    last_activity: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if session is valid"""
        return self.is_active and not self.is_expired()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'is_active': self.is_active,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None
        }


@dataclass
class LoginAttempt:
    """Login attempt tracking"""
    attempt_id: str
    username: str
    ip_address: str
    user_agent: str
    timestamp: datetime
    success: bool
    failure_reason: Optional[str] = None


class SessionConfig:
    """Session configuration"""
    SESSION_LIFETIME = 3600 * 24  # 24 hours
    SESSION_IDLE_TIMEOUT = 3600  # 1 hour
    MAX_SESSIONS_PER_USER = 5
    SESSION_COOKIE_NAME = 'flavorsnap_session'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class AuthenticationManager:
    """Comprehensive authentication management"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.sessions: Dict[str, AuthSession] = {}
        self.login_attempts: List[LoginAttempt] = []
        self.verification_tokens: Dict[str, Dict[str, Any]] = {}
        self.password_reset_tokens: Dict[str, Dict[str, Any]] = {}
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize authentication manager with Flask app"""
        self.app = app
        app.config.setdefault('SECRET_KEY', os.urandom(32))
        app.config.setdefault('SESSION_LIFETIME', SessionConfig.SESSION_LIFETIME)
    
    def login(self, username: str, password: str, 
             two_factor_code: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Authenticate user and create session"""
        # Sanitize inputs
        username = InputValidator.sanitize_string(username, max_length=50)
        
        if not username or not password:
            return False, None, "Username and password are required"
        
        # Get user
        user = user_manager.get_user_by_username(username)
        if not user:
            self._log_login_attempt(username, False, "User not found")
            return False, None, "Invalid username or password"
        
        # Check if account is locked
        if user.account_locked_until and datetime.now() < user.account_locked_until:
            remaining_time = (user.account_locked_until - datetime.now()).seconds // 60
            return False, None, f"Account is locked. Try again in {remaining_time} minutes"
        
        # Check account status
        if user.status == UserStatus.SUSPENDED:
            return False, None, "Account is suspended"
        
        if user.status == UserStatus.DELETED:
            return False, None, "Account has been deleted"
        
        # Verify password
        if not PasswordPolicy.verify_password(password, user.password_hash):
            user_manager._increment_failed_login(user.user_id)
            self._log_login_attempt(username, False, "Invalid password")
            return False, None, "Invalid username or password"
        
        # Check if 2FA is enabled
        if user.two_factor_enabled:
            if not two_factor_code:
                return False, None, "Two-factor authentication code required"
            
            if not self._verify_two_factor_code(user, two_factor_code):
                self._log_login_attempt(username, False, "Invalid 2FA code")
                return False, None, "Invalid two-factor authentication code"
        
        # Check if password needs to be changed
        if user.must_change_password:
            return False, None, "Password must be changed"
        
        # Check if password is expired
        if PasswordPolicy.is_password_expired(user.password_changed_at):
            return False, None, "Password has expired. Please reset your password"
        
        # Reset failed login attempts
        user_manager._reset_failed_login(user.user_id)
        
        # Update last login
        user.last_login = datetime.now()
        
        # Create session
        session_data = self._create_session(user)
        
        # Create JWT tokens
        access_token_info = jwt_token_manager.create_access_token(
            subject=user.user_id,
            user_id=user.user_id,
            role=user.role.value,
            permissions=user_manager.get_user_permissions(user.user_id)
        )
        
        refresh_token_info = jwt_token_manager.create_refresh_token(
            subject=user.user_id,
            access_token_jti=access_token_info.payload.jti
        )
        
        # Log successful login
        self._log_login_attempt(username, True)
        user_manager._log_activity(
            user_id=user.user_id,
            activity_type='login',
            activity_data={'method': AuthenticationMethod.PASSWORD}
        )
        
        self.logger.info(f"User logged in: {username} ({user.user_id})")
        
        return True, {
            'user': user.to_dict(),
            'session': session_data,
            'access_token': access_token_info.token,
            'refresh_token': refresh_token_info.token,
            'token_type': 'Bearer',
            'expires_in': SessionConfig.SESSION_LIFETIME
        }, None
    
    def logout(self, session_id: Optional[str] = None, 
              access_token: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Logout user and invalidate session"""
        # Invalidate session
        if session_id:
            if session_id in self.sessions:
                session_obj = self.sessions[session_id]
                session_obj.is_active = False
                
                user_manager._log_activity(
                    user_id=session_obj.user_id,
                    activity_type='logout',
                    activity_data={'session_id': session_id}
                )
                
                self.logger.info(f"User logged out: session {session_id}")
        
        # Revoke JWT token
        if access_token:
            jwt_token_manager.blacklist_token(access_token, reason="User logout")
        
        return True, None
    
    def refresh_token(self, refresh_token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Refresh access token"""
        success, new_token_info, error = jwt_token_manager.refresh_access_token(refresh_token)
        
        if not success:
            return False, None, error
        
        return True, {
            'access_token': new_token_info.token,
            'token_type': 'Bearer',
            'expires_in': new_token_info.expires_at.timestamp() - datetime.now().timestamp()
        }, None
    
    def validate_session(self, session_id: str) -> Tuple[bool, Optional[User], Optional[str]]:
        """Validate session and return user"""
        if session_id not in self.sessions:
            return False, None, "Invalid session"
        
        session_obj = self.sessions[session_id]
        
        if not session_obj.is_valid():
            return False, None, "Session expired or invalid"
        
        # Check idle timeout
        if session_obj.last_activity:
            idle_time = (datetime.now() - session_obj.last_activity).seconds
            if idle_time > SessionConfig.SESSION_IDLE_TIMEOUT:
                session_obj.is_active = False
                return False, None, "Session expired due to inactivity"
        
        # Update last activity
        session_obj.last_activity = datetime.now()
        
        # Get user
        user = user_manager.get_user(session_obj.user_id)
        if not user:
            return False, None, "User not found"
        
        if user.status != UserStatus.ACTIVE:
            return False, None, "User account is not active"
        
        return True, user, None
    
    def validate_token(self, token: str) -> Tuple[bool, Optional[User], Optional[str]]:
        """Validate JWT token and return user"""
        is_valid, payload, error = jwt_token_manager.validate_token(token)
        
        if not is_valid:
            return False, None, error
        
        user_id = payload.get('user_id') or payload.get('sub')
        if not user_id:
            return False, None, "Invalid token payload"
        
        user = user_manager.get_user(user_id)
        if not user:
            return False, None, "User not found"
        
        if user.status != UserStatus.ACTIVE:
            return False, None, "User account is not active"
        
        return True, user, None
    
    def register(self, username: str, email: str, password: str,
                phone_number: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Register new user"""
        # Create user
        success, user, error = user_manager.create_user(
            username=username,
            email=email,
            password=password,
            role=UserRole.USER,
            phone_number=phone_number
        )
        
        if not success:
            return False, None, error
        
        # Generate email verification token
        verification_token = self._generate_verification_token(user.user_id, email)
        
        self.logger.info(f"User registered: {username} ({user.user_id})")
        
        return True, {
            'user': user.to_dict(),
            'verification_token': verification_token,
            'message': 'Registration successful. Please verify your email.'
        }, None
    
    def verify_email(self, token: str) -> Tuple[bool, Optional[str]]:
        """Verify email with token"""
        if token not in self.verification_tokens:
            return False, "Invalid verification token"
        
        token_data = self.verification_tokens[token]
        
        # Check if token is expired
        if datetime.now() > token_data['expires_at']:
            del self.verification_tokens[token]
            return False, "Verification token has expired"
        
        # Verify email
        user_id = token_data['user_id']
        success, error = user_manager.verify_email(user_id)
        
        if not success:
            return False, error
        
        # Remove token
        del self.verification_tokens[token]
        
        self.logger.info(f"Email verified for user: {user_id}")
        return True, None
    
    def request_password_reset(self, email: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Request password reset"""
        email = InputValidator.sanitize_email(email)
        
        user = user_manager.get_user_by_email(email)
        if not user:
            # Don't reveal if email exists
            return True, None, None
        
        # Generate reset token
        reset_token = self._generate_password_reset_token(user.user_id, email)
        
        self.logger.info(f"Password reset requested for user: {user.username} ({user.user_id})")
        
        return True, reset_token, None
    
    def reset_password(self, token: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """Reset password with token"""
        if token not in self.password_reset_tokens:
            return False, "Invalid reset token"
        
        token_data = self.password_reset_tokens[token]
        
        # Check if token is expired
        if datetime.now() > token_data['expires_at']:
            del self.password_reset_tokens[token]
            return False, "Reset token has expired"
        
        # Reset password
        user_id = token_data['user_id']
        success, error = user_manager.reset_password(user_id, new_password)
        
        if not success:
            return False, error
        
        # Remove token
        del self.password_reset_tokens[token]
        
        # Invalidate all sessions for this user
        self._invalidate_user_sessions(user_id)
        
        self.logger.info(f"Password reset for user: {user_id}")
        return True, None
    
    def enable_two_factor(self, user_id: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Enable two-factor authentication"""
        success, secret, error = user_manager.enable_two_factor(user_id)
        
        if not success:
            return False, None, error
        
        # Generate QR code data for authenticator apps
        user = user_manager.get_user(user_id)
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name='FlavorSnap'
        )
        
        return True, {
            'secret': secret,
            'qr_code_uri': totp_uri,
            'backup_codes': self._generate_backup_codes()
        }, None
    
    def disable_two_factor(self, user_id: str, password: str) -> Tuple[bool, Optional[str]]:
        """Disable two-factor authentication"""
        user = user_manager.get_user(user_id)
        if not user:
            return False, "User not found"
        
        # Verify password
        if not PasswordPolicy.verify_password(password, user.password_hash):
            return False, "Invalid password"
        
        success, error = user_manager.disable_two_factor(user_id)
        return success, error
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for user"""
        user_sessions = [
            s.to_dict() for s in self.sessions.values()
            if s.user_id == user_id and s.is_valid()
        ]
        return user_sessions
    
    def revoke_session(self, session_id: str) -> Tuple[bool, Optional[str]]:
        """Revoke specific session"""
        if session_id not in self.sessions:
            return False, "Session not found"
        
        session_obj = self.sessions[session_id]
        session_obj.is_active = False
        
        self.logger.info(f"Session revoked: {session_id}")
        return True, None
    
    def revoke_all_sessions(self, user_id: str, except_session_id: Optional[str] = None) -> int:
        """Revoke all sessions for user except specified one"""
        count = 0
        for session_id, session_obj in self.sessions.items():
            if session_obj.user_id == user_id and session_id != except_session_id:
                session_obj.is_active = False
                count += 1
        
        self.logger.info(f"Revoked {count} sessions for user: {user_id}")
        return count
    
    def get_login_history(self, user_id: Optional[str] = None, 
                         limit: int = 50) -> List[Dict[str, Any]]:
        """Get login history"""
        if user_id:
            user = user_manager.get_user(user_id)
            if not user:
                return []
            
            attempts = [
                {
                    'attempt_id': a.attempt_id,
                    'username': a.username,
                    'ip_address': a.ip_address,
                    'timestamp': a.timestamp.isoformat(),
                    'success': a.success,
                    'failure_reason': a.failure_reason
                }
                for a in self.login_attempts
                if a.username == user.username
            ]
        else:
            attempts = [
                {
                    'attempt_id': a.attempt_id,
                    'username': a.username,
                    'ip_address': a.ip_address,
                    'timestamp': a.timestamp.isoformat(),
                    'success': a.success,
                    'failure_reason': a.failure_reason
                }
                for a in self.login_attempts
            ]
        
        # Sort by timestamp descending
        attempts.sort(key=lambda x: x['timestamp'], reverse=True)
        return attempts[:limit]
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        expired_sessions = []
        for session_id, session_obj in self.sessions.items():
            if not session_obj.is_valid():
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def _create_session(self, user: User) -> Dict[str, Any]:
        """Create new session for user"""
        # Check max sessions per user
        user_sessions = [s for s in self.sessions.values() if s.user_id == user.user_id and s.is_valid()]
        if len(user_sessions) >= SessionConfig.MAX_SESSIONS_PER_USER:
            # Remove oldest session
            oldest_session = min(user_sessions, key=lambda s: s.created_at)
            oldest_session.is_active = False
        
        # Create new session
        session_id = secrets.token_urlsafe(32)
        session_obj = AuthSession(
            session_id=session_id,
            user_id=user.user_id,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=SessionConfig.SESSION_LIFETIME),
            ip_address=request.remote_addr if request else 'system',
            user_agent=request.headers.get('User-Agent', 'system') if request else 'system',
            last_activity=datetime.now()
        )
        
        self.sessions[session_id] = session_obj
        
        return session_obj.to_dict()
    
    def _verify_two_factor_code(self, user: User, code: str) -> bool:
        """Verify two-factor authentication code"""
        if not user.two_factor_secret:
            return False
        
        totp = pyotp.TOTP(user.two_factor_secret)
        return totp.verify(code, valid_window=1)
    
    def _generate_verification_token(self, user_id: str, email: str) -> str:
        """Generate email verification token"""
        token = secrets.token_urlsafe(32)
        self.verification_tokens[token] = {
            'user_id': user_id,
            'email': email,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(hours=24)
        }
        return token
    
    def _generate_password_reset_token(self, user_id: str, email: str) -> str:
        """Generate password reset token"""
        token = secrets.token_urlsafe(32)
        self.password_reset_tokens[token] = {
            'user_id': user_id,
            'email': email,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(hours=1)
        }
        return token
    
    def _generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes for 2FA"""
        return [secrets.token_hex(4).upper() for _ in range(count)]
    
    def _invalidate_user_sessions(self, user_id: str):
        """Invalidate all sessions for user"""
        for session_obj in self.sessions.values():
            if session_obj.user_id == user_id:
                session_obj.is_active = False
    
    def _log_login_attempt(self, username: str, success: bool, failure_reason: Optional[str] = None):
        """Log login attempt"""
        attempt = LoginAttempt(
            attempt_id=str(uuid.uuid4()),
            username=username,
            ip_address=request.remote_addr if request else 'system',
            user_agent=request.headers.get('User-Agent', 'system') if request else 'system',
            timestamp=datetime.now(),
            success=success,
            failure_reason=failure_reason
        )
        
        self.login_attempts.append(attempt)
        
        # Keep only last 10000 attempts
        if len(self.login_attempts) > 10000:
            self.login_attempts = self.login_attempts[-10000:]


# Authentication decorators
def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for JWT token
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            is_valid, user, error = auth_manager.validate_token(token)
            if is_valid:
                request.current_user = user
                return f(*args, **kwargs)
        
        # Check for session
        session_id = request.cookies.get(SessionConfig.SESSION_COOKIE_NAME)
        if session_id:
            is_valid, user, error = auth_manager.validate_session(session_id)
            if is_valid:
                request.current_user = user
                return f(*args, **kwargs)
        
        return jsonify({'error': 'Authentication required'}), 401
    
    return decorated_function


def require_role(*roles: UserRole):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401
            
            user = request.current_user
            if user.role not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_permission(*permissions: Permission):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401
            
            user = request.current_user
            for permission in permissions:
                if not user_manager.has_permission(user.user_id, permission):
                    return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


# Initialize global authentication manager
auth_manager = AuthenticationManager()
