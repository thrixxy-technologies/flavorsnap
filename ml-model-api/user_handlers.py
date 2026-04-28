"""
Advanced User Management System for FlavorSnap API
Implements comprehensive user management with CRUD operations, role-based access control,
user analytics, and GDPR compliance
"""
import os
import uuid
import hashlib
import secrets
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import bcrypt
from flask import request, jsonify, current_app

# Import security and compliance modules
from security_config import InputValidator, SecurityConfig
from gdpr_compliance import GDPRCompliance
from jwt_handler import jwt_token_manager, JWTPayload


class UserRole(Enum):
    """User role enumeration"""
    ADMIN = "admin"
    MODERATOR = "moderator"
    PREMIUM = "premium"
    USER = "user"
    GUEST = "guest"


class UserStatus(Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    DELETED = "deleted"


class Permission(Enum):
    """System permissions"""
    # User permissions
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # Content permissions
    CONTENT_READ = "content:read"
    CONTENT_WRITE = "content:write"
    CONTENT_DELETE = "content:delete"
    
    # Admin permissions
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    ADMIN_DELETE = "admin:delete"
    
    # Analytics permissions
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_WRITE = "analytics:write"
    
    # System permissions
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"


# Role-based permission mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.USER_READ, Permission.USER_WRITE, Permission.USER_DELETE,
        Permission.CONTENT_READ, Permission.CONTENT_WRITE, Permission.CONTENT_DELETE,
        Permission.ADMIN_READ, Permission.ADMIN_WRITE, Permission.ADMIN_DELETE,
        Permission.ANALYTICS_READ, Permission.ANALYTICS_WRITE,
        Permission.SYSTEM_CONFIG, Permission.SYSTEM_MONITOR
    ],
    UserRole.MODERATOR: [
        Permission.USER_READ, Permission.USER_WRITE,
        Permission.CONTENT_READ, Permission.CONTENT_WRITE, Permission.CONTENT_DELETE,
        Permission.ANALYTICS_READ
    ],
    UserRole.PREMIUM: [
        Permission.USER_READ, Permission.USER_WRITE,
        Permission.CONTENT_READ, Permission.CONTENT_WRITE,
        Permission.ANALYTICS_READ
    ],
    UserRole.USER: [
        Permission.USER_READ,
        Permission.CONTENT_READ, Permission.CONTENT_WRITE
    ],
    UserRole.GUEST: [
        Permission.CONTENT_READ
    ]
}


@dataclass
class User:
    """User data model"""
    user_id: str
    username: str
    email: str
    password_hash: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    email_verified: bool = False
    phone_number: Optional[str] = None
    phone_verified: bool = False
    two_factor_enabled: bool = False
    two_factor_secret: Optional[str] = None
    failed_login_attempts: int = 0
    account_locked_until: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    must_change_password: bool = False
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert user to dictionary"""
        data = {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'role': self.role.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'email_verified': self.email_verified,
            'phone_verified': self.phone_verified,
            'two_factor_enabled': self.two_factor_enabled,
            'metadata': self.metadata or {}
        }
        
        if include_sensitive:
            data.update({
                'password_hash': self.password_hash,
                'two_factor_secret': self.two_factor_secret,
                'failed_login_attempts': self.failed_login_attempts,
                'account_locked_until': self.account_locked_until.isoformat() if self.account_locked_until else None,
                'password_changed_at': self.password_changed_at.isoformat() if self.password_changed_at else None,
                'must_change_password': self.must_change_password
            })
        
        return data


@dataclass
class UserActivity:
    """User activity tracking"""
    activity_id: str
    user_id: str
    activity_type: str
    activity_data: Dict[str, Any]
    ip_address: str
    user_agent: str
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'activity_id': self.activity_id,
            'user_id': self.user_id,
            'activity_type': self.activity_type,
            'activity_data': self.activity_data,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat()
        }


class PasswordPolicy:
    """Password policy enforcement"""
    
    MIN_LENGTH = 12
    MAX_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARACTERS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    PASSWORD_HISTORY_COUNT = 5
    PASSWORD_EXPIRY_DAYS = 90
    MAX_FAILED_ATTEMPTS = 5
    ACCOUNT_LOCKOUT_DURATION = 30  # minutes
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, Optional[str]]:
        """Validate password against policy"""
        if not password:
            return False, "Password is required"
        
        if len(password) < PasswordPolicy.MIN_LENGTH:
            return False, f"Password must be at least {PasswordPolicy.MIN_LENGTH} characters"
        
        if len(password) > PasswordPolicy.MAX_LENGTH:
            return False, f"Password must not exceed {PasswordPolicy.MAX_LENGTH} characters"
        
        if PasswordPolicy.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if PasswordPolicy.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if PasswordPolicy.REQUIRE_DIGITS and not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if PasswordPolicy.REQUIRE_SPECIAL and not any(c in PasswordPolicy.SPECIAL_CHARACTERS for c in password):
            return False, f"Password must contain at least one special character ({PasswordPolicy.SPECIAL_CHARACTERS})"
        
        # Check for common patterns
        if re.search(r'(.)\1{2,}', password):
            return False, "Password must not contain repeated characters"
        
        # Check for sequential characters
        if any(password[i:i+3] in '0123456789abcdefghijklmnopqrstuvwxyz' for i in range(len(password)-2)):
            return False, "Password must not contain sequential characters"
        
        return True, None
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
    
    @staticmethod
    def is_password_expired(password_changed_at: Optional[datetime]) -> bool:
        """Check if password has expired"""
        if not password_changed_at:
            return True
        
        expiry_date = password_changed_at + timedelta(days=PasswordPolicy.PASSWORD_EXPIRY_DAYS)
        return datetime.now() > expiry_date


class UserManager:
    """Comprehensive user management system"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.users: Dict[str, User] = {}
        self.user_activities: List[UserActivity] = []
        self.password_history: Dict[str, List[str]] = {}
        self.gdpr_compliance = GDPRCompliance()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize user manager with Flask app"""
        self.app = app
        self._initialize_default_users()
    
    def _initialize_default_users(self):
        """Initialize default admin user"""
        admin_password = os.getenv('ADMIN_PASSWORD', 'Admin@123456')
        
        admin_user = User(
            user_id=str(uuid.uuid4()),
            username='admin',
            email='admin@flavorsnap.com',
            password_hash=PasswordPolicy.hash_password(admin_password),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            email_verified=True,
            password_changed_at=datetime.now()
        )
        
        self.users[admin_user.user_id] = admin_user
        self.logger.info("Default admin user initialized")
    
    def create_user(self, username: str, email: str, password: str, 
                   role: UserRole = UserRole.USER,
                   phone_number: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[User], Optional[str]]:
        """Create new user"""
        # Validate inputs
        username = InputValidator.sanitize_string(username, max_length=50)
        email = InputValidator.sanitize_email(email)
        
        if not username or not email:
            return False, None, "Invalid username or email"
        
        # Check if user already exists
        if self._user_exists_by_username(username):
            return False, None, "Username already exists"
        
        if self._user_exists_by_email(email):
            return False, None, "Email already exists"
        
        # Validate password
        is_valid, error_msg = PasswordPolicy.validate_password(password)
        if not is_valid:
            return False, None, error_msg
        
        # Hash password
        password_hash = PasswordPolicy.hash_password(password)
        
        # Create user
        user = User(
            user_id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            status=UserStatus.PENDING_VERIFICATION,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            phone_number=phone_number,
            password_changed_at=datetime.now(),
            metadata=metadata or {}
        )
        
        self.users[user.user_id] = user
        self.password_history[user.user_id] = [password_hash]
        
        # Log activity
        self._log_activity(
            user_id=user.user_id,
            activity_type='user_created',
            activity_data={'username': username, 'email': email, 'role': role.value}
        )
        
        self.logger.info(f"User created: {username} ({user.user_id})")
        return True, user, None
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        for user in self.users.values():
            if user.email == email:
                return user
        return None
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> Tuple[bool, Optional[User], Optional[str]]:
        """Update user information"""
        user = self.get_user(user_id)
        if not user:
            return False, None, "User not found"
        
        # Validate and apply updates
        if 'username' in updates:
            new_username = InputValidator.sanitize_string(updates['username'], max_length=50)
            if new_username and new_username != user.username:
                if self._user_exists_by_username(new_username):
                    return False, None, "Username already exists"
                user.username = new_username
        
        if 'email' in updates:
            new_email = InputValidator.sanitize_email(updates['email'])
            if new_email and new_email != user.email:
                if self._user_exists_by_email(new_email):
                    return False, None, "Email already exists"
                user.email = new_email
                user.email_verified = False
        
        if 'phone_number' in updates:
            user.phone_number = InputValidator.sanitize_string(updates['phone_number'], max_length=20)
            user.phone_verified = False
        
        if 'role' in updates and isinstance(updates['role'], UserRole):
            user.role = updates['role']
        
        if 'status' in updates and isinstance(updates['status'], UserStatus):
            user.status = updates['status']
        
        if 'metadata' in updates and isinstance(updates['metadata'], dict):
            user.metadata = updates['metadata']
        
        user.updated_at = datetime.now()
        
        # Log activity
        self._log_activity(
            user_id=user_id,
            activity_type='user_updated',
            activity_data={'updates': list(updates.keys())}
        )
        
        self.logger.info(f"User updated: {user.username} ({user_id})")
        return True, user, None
    
    def delete_user(self, user_id: str, soft_delete: bool = True) -> Tuple[bool, Optional[str]]:
        """Delete user (soft or hard delete)"""
        user = self.get_user(user_id)
        if not user:
            return False, "User not found"
        
        if soft_delete:
            # Soft delete - mark as deleted
            user.status = UserStatus.DELETED
            user.updated_at = datetime.now()
            
            # Request GDPR data deletion
            self.gdpr_compliance.request_data_deletion(user_id, reason="User account deletion")
            
            self.logger.info(f"User soft deleted: {user.username} ({user_id})")
        else:
            # Hard delete - remove from system
            del self.users[user_id]
            if user_id in self.password_history:
                del self.password_history[user_id]
            
            self.logger.info(f"User hard deleted: {user.username} ({user_id})")
        
        # Log activity
        self._log_activity(
            user_id=user_id,
            activity_type='user_deleted',
            activity_data={'soft_delete': soft_delete}
        )
        
        return True, None
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """Change user password"""
        user = self.get_user(user_id)
        if not user:
            return False, "User not found"
        
        # Verify old password
        if not PasswordPolicy.verify_password(old_password, user.password_hash):
            self._increment_failed_login(user_id)
            return False, "Invalid current password"
        
        # Validate new password
        is_valid, error_msg = PasswordPolicy.validate_password(new_password)
        if not is_valid:
            return False, error_msg
        
        # Check password history
        new_password_hash = PasswordPolicy.hash_password(new_password)
        if self._is_password_in_history(user_id, new_password):
            return False, f"Password has been used recently. Please choose a different password."
        
        # Update password
        user.password_hash = new_password_hash
        user.password_changed_at = datetime.now()
        user.must_change_password = False
        user.updated_at = datetime.now()
        
        # Update password history
        if user_id not in self.password_history:
            self.password_history[user_id] = []
        self.password_history[user_id].append(new_password_hash)
        if len(self.password_history[user_id]) > PasswordPolicy.PASSWORD_HISTORY_COUNT:
            self.password_history[user_id].pop(0)
        
        # Log activity
        self._log_activity(
            user_id=user_id,
            activity_type='password_changed',
            activity_data={}
        )
        
        self.logger.info(f"Password changed for user: {user.username} ({user_id})")
        return True, None
    
    def reset_password(self, user_id: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """Reset user password (admin function)"""
        user = self.get_user(user_id)
        if not user:
            return False, "User not found"
        
        # Validate new password
        is_valid, error_msg = PasswordPolicy.validate_password(new_password)
        if not is_valid:
            return False, error_msg
        
        # Update password
        user.password_hash = PasswordPolicy.hash_password(new_password)
        user.password_changed_at = datetime.now()
        user.must_change_password = True
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.updated_at = datetime.now()
        
        # Log activity
        self._log_activity(
            user_id=user_id,
            activity_type='password_reset',
            activity_data={}
        )
        
        self.logger.info(f"Password reset for user: {user.username} ({user_id})")
        return True, None
    
    def verify_email(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """Verify user email"""
        user = self.get_user(user_id)
        if not user:
            return False, "User not found"
        
        user.email_verified = True
        if user.status == UserStatus.PENDING_VERIFICATION:
            user.status = UserStatus.ACTIVE
        user.updated_at = datetime.now()
        
        # Log activity
        self._log_activity(
            user_id=user_id,
            activity_type='email_verified',
            activity_data={}
        )
        
        self.logger.info(f"Email verified for user: {user.username} ({user_id})")
        return True, None
    
    def enable_two_factor(self, user_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Enable two-factor authentication"""
        user = self.get_user(user_id)
        if not user:
            return False, None, "User not found"
        
        # Generate 2FA secret
        secret = secrets.token_hex(16)
        user.two_factor_secret = secret
        user.two_factor_enabled = True
        user.updated_at = datetime.now()
        
        # Log activity
        self._log_activity(
            user_id=user_id,
            activity_type='two_factor_enabled',
            activity_data={}
        )
        
        self.logger.info(f"2FA enabled for user: {user.username} ({user_id})")
        return True, secret, None
    
    def disable_two_factor(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """Disable two-factor authentication"""
        user = self.get_user(user_id)
        if not user:
            return False, "User not found"
        
        user.two_factor_enabled = False
        user.two_factor_secret = None
        user.updated_at = datetime.now()
        
        # Log activity
        self._log_activity(
            user_id=user_id,
            activity_type='two_factor_disabled',
            activity_data={}
        )
        
        self.logger.info(f"2FA disabled for user: {user.username} ({user_id})")
        return True, None
    
    def list_users(self, filters: Optional[Dict[str, Any]] = None, 
                  page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """List users with pagination and filtering"""
        users_list = list(self.users.values())
        
        # Apply filters
        if filters:
            if 'role' in filters:
                users_list = [u for u in users_list if u.role == filters['role']]
            if 'status' in filters:
                users_list = [u for u in users_list if u.status == filters['status']]
            if 'email_verified' in filters:
                users_list = [u for u in users_list if u.email_verified == filters['email_verified']]
            if 'search' in filters:
                search_term = filters['search'].lower()
                users_list = [u for u in users_list if search_term in u.username.lower() or search_term in u.email.lower()]
        
        # Pagination
        total_users = len(users_list)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_users = users_list[start_idx:end_idx]
        
        return {
            'users': [u.to_dict() for u in paginated_users],
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_users': total_users,
                'total_pages': (total_users + page_size - 1) // page_size
            }
        }
    
    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions based on role"""
        user = self.get_user(user_id)
        if not user:
            return []
        
        permissions = ROLE_PERMISSIONS.get(user.role, [])
        return [p.value for p in permissions]
    
    def has_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has specific permission"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        if user.status != UserStatus.ACTIVE:
            return False
        
        permissions = ROLE_PERMISSIONS.get(user.role, [])
        return permission in permissions
    
    def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get user analytics"""
        user = self.get_user(user_id)
        if not user:
            return {}
        
        # Get user activities
        user_activities = [a for a in self.user_activities if a.user_id == user_id]
        
        # Calculate statistics
        activity_by_type = {}
        for activity in user_activities:
            activity_type = activity.activity_type
            activity_by_type[activity_type] = activity_by_type.get(activity_type, 0) + 1
        
        return {
            'user_id': user_id,
            'username': user.username,
            'account_age_days': (datetime.now() - user.created_at).days,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'total_activities': len(user_activities),
            'activity_by_type': activity_by_type,
            'email_verified': user.email_verified,
            'two_factor_enabled': user.two_factor_enabled,
            'role': user.role.value,
            'status': user.status.value
        }
    
    def get_system_analytics(self) -> Dict[str, Any]:
        """Get system-wide user analytics"""
        total_users = len(self.users)
        
        # Count by role
        users_by_role = {}
        for role in UserRole:
            users_by_role[role.value] = len([u for u in self.users.values() if u.role == role])
        
        # Count by status
        users_by_status = {}
        for status in UserStatus:
            users_by_status[status.value] = len([u for u in self.users.values() if u.status == status])
        
        # Count verified users
        email_verified_count = len([u for u in self.users.values() if u.email_verified])
        two_factor_enabled_count = len([u for u in self.users.values() if u.two_factor_enabled])
        
        # Recent activities
        recent_activities = sorted(self.user_activities, key=lambda a: a.timestamp, reverse=True)[:10]
        
        return {
            'total_users': total_users,
            'users_by_role': users_by_role,
            'users_by_status': users_by_status,
            'email_verified_count': email_verified_count,
            'two_factor_enabled_count': two_factor_enabled_count,
            'recent_activities': [a.to_dict() for a in recent_activities]
        }
    
    def _user_exists_by_username(self, username: str) -> bool:
        """Check if username exists"""
        return any(u.username == username for u in self.users.values())
    
    def _user_exists_by_email(self, email: str) -> bool:
        """Check if email exists"""
        return any(u.email == email for u in self.users.values())
    
    def _is_password_in_history(self, user_id: str, password: str) -> bool:
        """Check if password is in history"""
        if user_id not in self.password_history:
            return False
        
        for old_hash in self.password_history[user_id]:
            if PasswordPolicy.verify_password(password, old_hash):
                return True
        return False
    
    def _increment_failed_login(self, user_id: str):
        """Increment failed login attempts"""
        user = self.get_user(user_id)
        if not user:
            return
        
        user.failed_login_attempts += 1
        
        if user.failed_login_attempts >= PasswordPolicy.MAX_FAILED_ATTEMPTS:
            user.account_locked_until = datetime.now() + timedelta(minutes=PasswordPolicy.ACCOUNT_LOCKOUT_DURATION)
            self.logger.warning(f"Account locked due to failed login attempts: {user.username} ({user_id})")
    
    def _reset_failed_login(self, user_id: str):
        """Reset failed login attempts"""
        user = self.get_user(user_id)
        if not user:
            return
        
        user.failed_login_attempts = 0
        user.account_locked_until = None
    
    def _log_activity(self, user_id: str, activity_type: str, activity_data: Dict[str, Any]):
        """Log user activity"""
        activity = UserActivity(
            activity_id=str(uuid.uuid4()),
            user_id=user_id,
            activity_type=activity_type,
            activity_data=activity_data,
            ip_address=request.remote_addr if request else 'system',
            user_agent=request.headers.get('User-Agent', 'system') if request else 'system',
            timestamp=datetime.now()
        )
        
        self.user_activities.append(activity)
        
        # Keep only last 10000 activities
        if len(self.user_activities) > 10000:
            self.user_activities = self.user_activities[-10000:]


# Initialize global user manager
user_manager = UserManager()
