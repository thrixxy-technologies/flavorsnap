"""
JWT Token Handler for FlavorSnap API
Implements JWT token creation, validation, and management
"""
import os
import json
import time
import secrets
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
import jwt
from jwt import PyJWTError
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from flask import current_app, request


class JWTConfig:
    """JWT configuration settings"""
    
    # Token lifetimes
    ACCESS_TOKEN_LIFETIME = 3600  # 1 hour
    REFRESH_TOKEN_LIFETIME = 86400 * 30  # 30 days
    ID_TOKEN_LIFETIME = 3600  # 1 hour
    
    # Token algorithms
    ALGORITHM = 'HS256'
    ALTERNATIVE_ALGORITHMS = ['RS256', 'ES256']
    
    # Token settings
    ISSUER = 'https://api.flavorsnap.com'
    AUDIENCE = 'flavorsnap-api'
    
    # Key rotation
    KEY_ROTATION_INTERVAL = 86400 * 7  # 7 days
    MAX_KEYS_STORED = 3
    
    # Security settings
    REQUIRE_EXPIRATION = True
    REQUIRE_ISSUER = True
    REQUIRE_AUDIENCE = True
    CLOCK_SKEW = 30  # seconds
    
    # Claims
    STANDARD_CLAIMS = ['iss', 'sub', 'aud', 'exp', 'iat', 'jti', 'nbf']
    CUSTOM_CLAIMS = ['scope', 'client_id', 'user_id', 'role', 'permissions']


@dataclass
class JWTPayload:
    """JWT payload data structure"""
    iss: str  # Issuer
    sub: str  # Subject
    aud: Union[str, List[str]]  # Audience
    exp: int  # Expiration time
    iat: int  # Issued at
    jti: str  # JWT ID
    nbf: Optional[int] = None  # Not before
    scope: Optional[str] = None
    client_id: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[List[str]] = None
    custom_claims: Optional[Dict[str, Any]] = None


@dataclass
class TokenInfo:
    """Token information structure"""
    token: str
    token_type: str
    expires_at: datetime
    issued_at: datetime
    payload: JWTPayload
    is_revoked: bool = False
    is_blacklisted: bool = False


class JWTKeyManager:
    """JWT key management with rotation support"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.keys: Dict[str, Dict[str, Any]] = {}
        self.current_key_id: Optional[str] = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize key manager with Flask app"""
        self.app = app
        self._generate_initial_keys()
        self._schedule_key_rotation()
    
    def _generate_initial_keys(self):
        """Generate initial encryption keys"""
        # Generate current key
        current_key_id = self._generate_key_id()
        self.keys[current_key_id] = {
            'key': self._generate_secret_key(),
            'created_at': datetime.now(),
            'is_active': True,
            'key_id': current_key_id
        }
        self.current_key_id = current_key_id
        
        self.logger.info(f"Generated initial JWT key: {current_key_id}")
    
    def _generate_key_id(self) -> str:
        """Generate unique key ID"""
        return f"jwt_key_{int(time.time())}_{secrets.token_hex(8)}"
    
    def _generate_secret_key(self) -> bytes:
        """Generate secret key for JWT signing"""
        return os.urandom(32)
    
    def _schedule_key_rotation(self):
        """Schedule periodic key rotation"""
        # In a real implementation, you would use a scheduler like Celery
        # For now, we'll check rotation on each token creation
        pass
    
    def rotate_key(self):
        """Rotate to a new encryption key"""
        # Deactivate current key
        if self.current_key_id and self.current_key_id in self.keys:
            self.keys[self.current_key_id]['is_active'] = False
        
        # Generate new key
        new_key_id = self._generate_key_id()
        self.keys[new_key_id] = {
            'key': self._generate_secret_key(),
            'created_at': datetime.now(),
            'is_active': True,
            'key_id': new_key_id
        }
        
        self.current_key_id = new_key_id
        
        # Clean up old keys
        self._cleanup_old_keys()
        
        self.logger.info(f"Rotated JWT key to: {new_key_id}")
    
    def _cleanup_old_keys(self):
        """Clean up old keys beyond retention limit"""
        if len(self.keys) > JWTConfig.MAX_KEYS_STORED:
            # Sort keys by creation time
            sorted_keys = sorted(
                self.keys.items(),
                key=lambda x: x[1]['created_at']
            )
            
            # Remove oldest keys
            keys_to_remove = len(self.keys) - JWTConfig.MAX_KEYS_STORED
            for i in range(keys_to_remove):
                key_id = sorted_keys[i][0]
                if not self.keys[key_id]['is_active']:
                    del self.keys[key_id]
                    self.logger.info(f"Removed old JWT key: {key_id}")
    
    def get_current_key(self) -> Tuple[bytes, str]:
        """Get current active signing key"""
        if not self.current_key_id or self.current_key_id not in self.keys:
            self.rotate_key()
        
        key_data = self.keys[self.current_key_id]
        return key_data['key'], self.current_key_id
    
    def get_key_by_id(self, key_id: str) -> Optional[bytes]:
        """Get key by ID for token validation"""
        if key_id in self.keys:
            return self.keys[key_id]['key']
        return None
    
    def get_all_keys(self) -> Dict[str, Dict[str, Any]]:
        """Get all keys (for debugging/admin purposes)"""
        return {
            key_id: {
                'created_at': data['created_at'].isoformat(),
                'is_active': data['is_active'],
                'key_id': data['key_id']
            }
            for key_id, data in self.keys.items()
        }


class JWTTokenManager:
    """JWT token creation and management"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.key_manager = JWTKeyManager(app)
        self.token_blacklist: Dict[str, Dict[str, Any]] = {}
        self.revoked_tokens: Dict[str, Dict[str, Any]] = {}
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize token manager with Flask app"""
        self.app = app
        app.config.setdefault('JWT_SECRET_KEY', os.urandom(32))
        app.config.setdefault('JWT_ISSUER', JWTConfig.ISSUER)
        app.config.setdefault('JWT_AUDIENCE', JWTConfig.AUDIENCE)
    
    def create_access_token(self, subject: str, scope: str = None, 
                          client_id: str = None, user_id: str = None,
                          role: str = None, permissions: List[str] = None,
                          custom_claims: Dict[str, Any] = None,
                          expires_in: int = None) -> TokenInfo:
        """Create JWT access token"""
        now = datetime.now()
        expires_in = expires_in or JWTConfig.ACCESS_TOKEN_LIFETIME
        expires_at = now + timedelta(seconds=expires_in)
        
        # Generate JWT ID
        jti = secrets.token_urlsafe(32)
        
        # Create payload
        payload = JWTPayload(
            iss=self.app.config.get('JWT_ISSUER', JWTConfig.ISSUER),
            sub=subject,
            aud=self.app.config.get('JWT_AUDIENCE', JWTConfig.AUDIENCE),
            exp=int(expires_at.timestamp()),
            iat=int(now.timestamp()),
            jti=jti,
            nbf=int(now.timestamp()),
            scope=scope,
            client_id=client_id,
            user_id=user_id,
            role=role,
            permissions=permissions,
            custom_claims=custom_claims
        )
        
        # Get signing key
        signing_key, key_id = self.key_manager.get_current_key()
        
        # Create token
        token_data = asdict(payload)
        
        # Add key ID to header
        headers = {'kid': key_id}
        
        # Remove None values from payload
        token_data = {k: v for k, v in token_data.items() if v is not None}
        
        # Add custom claims
        if custom_claims:
            token_data.update(custom_claims)
        
        # Sign token
        token = jwt.encode(
            token_data,
            signing_key,
            algorithm=JWTConfig.ALGORITHM,
            headers=headers
        )
        
        # Create token info
        token_info = TokenInfo(
            token=token,
            token_type='access_token',
            expires_at=expires_at,
            issued_at=now,
            payload=payload
        )
        
        self.logger.info(f"Created access token for subject: {subject}")
        return token_info
    
    def create_refresh_token(self, subject: str, access_token_jti: str,
                           client_id: str = None, expires_in: int = None) -> TokenInfo:
        """Create JWT refresh token"""
        now = datetime.now()
        expires_in = expires_in or JWTConfig.REFRESH_TOKEN_LIFETIME
        expires_at = now + timedelta(seconds=expires_in)
        
        # Generate JWT ID
        jti = secrets.token_urlsafe(32)
        
        # Create payload
        payload = JWTPayload(
            iss=self.app.config.get('JWT_ISSUER', JWTConfig.ISSUER),
            sub=subject,
            aud=self.app.config.get('JWT_AUDIENCE', JWTConfig.AUDIENCE),
            exp=int(expires_at.timestamp()),
            iat=int(now.timestamp()),
            jti=jti,
            nbf=int(now.timestamp()),
            client_id=client_id,
            custom_claims={'access_token_jti': access_token_jti, 'token_type': 'refresh'}
        )
        
        # Get signing key
        signing_key, key_id = self.key_manager.get_current_key()
        
        # Create token
        token_data = asdict(payload)
        token_data = {k: v for k, v in token_data.items() if v is not None}
        
        headers = {'kid': key_id}
        
        token = jwt.encode(
            token_data,
            signing_key,
            algorithm=JWTConfig.ALGORITHM,
            headers=headers
        )
        
        # Create token info
        token_info = TokenInfo(
            token=token,
            token_type='refresh_token',
            expires_at=expires_at,
            issued_at=now,
            payload=payload
        )
        
        self.logger.info(f"Created refresh token for subject: {subject}")
        return token_info
    
    def create_id_token(self, subject: str, user_info: Dict[str, Any],
                       nonce: str = None, client_id: str = None) -> TokenInfo:
        """Create JWT ID token (for OpenID Connect)"""
        now = datetime.now()
        expires_at = now + timedelta(seconds=JWTConfig.ID_TOKEN_LIFETIME)
        
        # Generate JWT ID
        jti = secrets.token_urlsafe(32)
        
        # Create payload with user info
        payload = JWTPayload(
            iss=self.app.config.get('JWT_ISSUER', JWTConfig.ISSUER),
            sub=subject,
            aud=client_id or self.app.config.get('JWT_AUDIENCE', JWTConfig.AUDIENCE),
            exp=int(expires_at.timestamp()),
            iat=int(now.timestamp()),
            jti=jti,
            nbf=int(now.timestamp()),
            custom_claims=user_info
        )
        
        # Add nonce if provided
        if nonce:
            if payload.custom_claims is None:
                payload.custom_claims = {}
            payload.custom_claims['nonce'] = nonce
        
        # Get signing key
        signing_key, key_id = self.key_manager.get_current_key()
        
        # Create token
        token_data = asdict(payload)
        token_data = {k: v for k, v in token_data.items() if v is not None}
        
        headers = {'kid': key_id}
        
        token = jwt.encode(
            token_data,
            signing_key,
            algorithm=JWTConfig.ALGORITHM,
            headers=headers
        )
        
        # Create token info
        token_info = TokenInfo(
            token=token,
            token_type='id_token',
            expires_at=expires_at,
            issued_at=now,
            payload=payload
        )
        
        self.logger.info(f"Created ID token for subject: {subject}")
        return token_info
    
    def validate_token(self, token: str, verify_signature: bool = True,
                      verify_exp: bool = True, verify_nbf: bool = True,
                      verify_iat: bool = True, verify_aud: bool = True) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Validate JWT token"""
        try:
            # Check if token is blacklisted
            if self._is_token_blacklisted(token):
                return False, None, "Token is blacklisted"
            
            # Decode token without verification first to get header
            unverified_header = jwt.get_unverified_header(token)
            key_id = unverified_header.get('kid')
            
            # Get appropriate key for verification
            if verify_signature:
                if key_id:
                    verification_key = self.key_manager.get_key_by_id(key_id)
                    if verification_key is None:
                        return False, None, "Invalid key ID"
                else:
                    verification_key, _ = self.key_manager.get_current_key()
            else:
                verification_key = None
            
            # Decode and verify token
            options = {
                'verify_signature': verify_signature,
                'verify_exp': verify_exp,
                'verify_nbf': verify_nbf,
                'verify_iat': verify_iat,
                'verify_aud': verify_aud,
                'require_exp': JWTConfig.REQUIRE_EXPIRATION,
                'require_iss': JWTConfig.REQUIRE_ISSUER,
                'require_aud': JWTConfig.REQUIRE_AUDIENCE
            }
            
            payload = jwt.decode(
                token,
                verification_key,
                algorithms=[JWTConfig.ALGORITHM],
                audience=self.app.config.get('JWT_AUDIENCE', JWTConfig.AUDIENCE),
                issuer=self.app.config.get('JWT_ISSUER', JWTConfig.ISSUER),
                options=options,
                leeway=JWTConfig.CLOCK_SKEW
            )
            
            # Check if token is revoked
            jti = payload.get('jti')
            if jti and self._is_token_revoked(jti):
                return False, None, "Token is revoked"
            
            return True, payload, None
            
        except jwt.ExpiredSignatureError:
            return False, None, "Token has expired"
        except jwt.InvalidTokenError as e:
            return False, None, f"Invalid token: {str(e)}"
        except Exception as e:
            self.logger.error(f"Token validation error: {str(e)}")
            return False, None, "Token validation failed"
    
    def refresh_access_token(self, refresh_token: str) -> Tuple[bool, Optional[TokenInfo], Optional[str]]:
        """Refresh access token using refresh token"""
        # Validate refresh token
        is_valid, payload, error = self.validate_token(refresh_token)
        if not is_valid:
            return False, None, error
        
        # Check if this is a refresh token
        custom_claims = payload.get('custom_claims', {})
        if custom_claims.get('token_type') != 'refresh':
            return False, None, "Invalid token type"
        
        # Get original access token JTI
        access_token_jti = custom_claims.get('access_token_jti')
        if access_token_jti:
            # Revoke original access token
            self.revoke_token(access_token_jti)
        
        # Create new access token
        subject = payload.get('sub')
        client_id = payload.get('client_id')
        
        new_token_info = self.create_access_token(
            subject=subject,
            client_id=client_id
        )
        
        # Revoke refresh token
        self.revoke_token(payload.get('jti'))
        
        self.logger.info(f"Refreshed access token for subject: {subject}")
        return True, new_token_info, None
    
    def revoke_token(self, jti: str, reason: str = None):
        """Revoke token by JWT ID"""
        self.revoked_tokens[jti] = {
            'revoked_at': datetime.now(),
            'reason': reason
        }
        self.logger.info(f"Revoked token: {jti}")
    
    def blacklist_token(self, token: str, reason: str = None):
        """Blacklist token (immediate invalidation)"""
        # Extract JTI from token
        try:
            payload = jwt.decode(token, options={'verify_signature': False})
            jti = payload.get('jti')
            if jti:
                self.token_blacklist[jti] = {
                    'blacklisted_at': datetime.now(),
                    'reason': reason
                }
                self.logger.info(f"Blacklisted token: {jti}")
        except Exception as e:
            self.logger.error(f"Failed to blacklist token: {str(e)}")
    
    def _is_token_revoked(self, jti: str) -> bool:
        """Check if token is revoked"""
        return jti in self.revoked_tokens
    
    def _is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        try:
            payload = jwt.decode(token, options={'verify_signature': False})
            jti = payload.get('jti')
            return jti in self.token_blacklist
        except:
            return False
    
    def cleanup_expired_tokens(self):
        """Clean up expired tokens from blacklist and revoked lists"""
        now = datetime.now()
        
        # Clean up blacklisted tokens (keep for 30 days)
        expired_blacklist = []
        for jti, data in self.token_blacklist.items():
            if now - data['blacklisted_at'] > timedelta(days=30):
                expired_blacklist.append(jti)
        
        for jti in expired_blacklist:
            del self.token_blacklist[jti]
        
        # Clean up revoked tokens (keep for 90 days)
        expired_revoked = []
        for jti, data in self.revoked_tokens.items():
            if now - data['revoked_at'] > timedelta(days=90):
                expired_revoked.append(jti)
        
        for jti in expired_revoked:
            del self.revoked_tokens[jti]
        
        if expired_blacklist or expired_revoked:
            self.logger.info(f"Cleaned up {len(expired_blacklist)} blacklisted and {len(expired_revoked)} revoked tokens")
    
    def get_token_info(self, token: str) -> Optional[TokenInfo]:
        """Get token information"""
        is_valid, payload, error = self.validate_token(token, verify_exp=False)
        if not is_valid:
            return None
        
        # Convert payload to JWTPayload
        jwt_payload = JWTPayload(
            iss=payload.get('iss'),
            sub=payload.get('sub'),
            aud=payload.get('aud'),
            exp=payload.get('exp'),
            iat=payload.get('iat'),
            jti=payload.get('jti'),
            nbf=payload.get('nbf'),
            scope=payload.get('scope'),
            client_id=payload.get('client_id'),
            user_id=payload.get('user_id'),
            role=payload.get('role'),
            permissions=payload.get('permissions'),
            custom_claims={k: v for k, v in payload.items() 
                         if k not in JWTConfig.STANDARD_CLAIMS + ['scope', 'client_id', 'user_id', 'role', 'permissions']}
        )
        
        expires_at = datetime.fromtimestamp(payload.get('exp'))
        issued_at = datetime.fromtimestamp(payload.get('iat'))
        
        return TokenInfo(
            token=token,
            token_type=payload.get('custom_claims', {}).get('token_type', 'access_token'),
            expires_at=expires_at,
            issued_at=issued_at,
            payload=jwt_payload,
            is_revoked=self._is_token_revoked(payload.get('jti')),
            is_blacklisted=self._is_token_blacklisted(token)
        )
    
    def rotate_keys(self):
        """Rotate JWT keys"""
        self.key_manager.rotate_key()
        self.logger.info("JWT keys rotated")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get token statistics"""
        return {
            'active_keys': len([k for k in self.key_manager.keys.values() if k['is_active']]),
            'total_keys': len(self.key_manager.keys),
            'blacklisted_tokens': len(self.token_blacklist),
            'revoked_tokens': len(self.revoked_tokens),
            'current_key_id': self.key_manager.current_key_id
        }


# Initialize global JWT token manager
jwt_token_manager = JWTTokenManager()
