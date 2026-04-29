"""
OAuth2 Authentication Handler for FlavorSnap API
Implements OAuth2 flows, token management, and secure authentication
"""
import os
import json
import time
import secrets
import hashlib
import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlencode, parse_qs
import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import jwt
from flask import request, current_app


class OAuth2Config:
    """OAuth2 configuration settings"""
    
    # OAuth2 endpoints
    AUTHORIZATION_ENDPOINT = "/oauth/authorize"
    TOKEN_ENDPOINT = "/oauth/token"
    USERINFO_ENDPOINT = "/oauth/userinfo"
    REVOCATION_ENDPOINT = "/oauth/revoke"
    
    # OAuth2 scopes
    SCOPES = {
        'read': 'Read access to resources',
        'write': 'Write access to resources',
        'admin': 'Administrative access',
        'profile': 'Access to user profile',
        'email': 'Access to user email'
    }
    
    # Grant types
    GRANT_TYPES = [
        'authorization_code',
        'client_credentials',
        'refresh_token',
        'implicit'
    ]
    
    # Token settings
    ACCESS_TOKEN_LIFETIME = 3600  # 1 hour
    REFRESH_TOKEN_LIFETIME = 86400 * 30  # 30 days
    AUTH_CODE_LIFETIME = 600  # 10 minutes
    
    # Security settings
    PKCE_REQUIRED = True
    STATE_REQUIRED = True
    NONCE_LENGTH = 32


class OAuth2Client:
    """OAuth2 client representation"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uris: List[str], 
                 scopes: List[str], grant_types: List[str]):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uris = redirect_uris
        self.scopes = scopes
        self.grant_types = grant_types
        self.created_at = datetime.now()
        self.is_active = True
    
    def validate_redirect_uri(self, redirect_uri: str) -> bool:
        """Validate redirect URI against registered URIs"""
        return redirect_uri in self.redirect_uris
    
    def validate_scope(self, requested_scopes: List[str]) -> List[str]:
        """Validate and return allowed scopes"""
        return [scope for scope in requested_scopes if scope in self.scopes]
    
    def validate_grant_type(self, grant_type: str) -> bool:
        """Validate grant type"""
        return grant_type in self.grant_types


class OAuth2Token:
    """OAuth2 token representation"""
    
    def __init__(self, token_type: str, access_token: str, refresh_token: str = None,
                 expires_in: int = None, scope: str = None, client_id: str = None):
        self.token_type = token_type
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.scope = scope
        self.client_id = client_id
        self.created_at = datetime.now()
        self.is_revoked = False
    
    def is_expired(self) -> bool:
        """Check if token is expired"""
        if self.expires_in is None:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.expires_in)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary representation"""
        result = {
            'token_type': self.token_type,
            'access_token': self.access_token,
            'expires_in': self.expires_in,
            'scope': self.scope
        }
        if self.refresh_token:
            result['refresh_token'] = self.refresh_token
        return result


class PKCEManager:
    """PKCE (Proof Key for Code Exchange) manager"""
    
    @staticmethod
    def generate_code_verifier() -> str:
        """Generate PKCE code verifier"""
        return secrets.token_urlsafe(64)
    
    @staticmethod
    def generate_code_challenge(code_verifier: str) -> str:
        """Generate PKCE code challenge from verifier"""
        digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
    
    @staticmethod
    def verify_code_challenge(code_verifier: str, code_challenge: str) -> bool:
        """Verify PKCE code challenge"""
        expected_challenge = PKCEManager.generate_code_challenge(code_verifier)
        return secrets.compare_digest(expected_challenge, code_challenge)


class OAuth2Handler:
    """Main OAuth2 handler class"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.clients: Dict[str, OAuth2Client] = {}
        self.authorization_codes: Dict[str, Dict[str, Any]] = {}
        self.tokens: Dict[str, OAuth2Token] = {}
        self.refresh_tokens: Dict[str, str] = {}  # refresh_token -> access_token mapping
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize OAuth2 handler with Flask app"""
        self.app = app
        app.config.setdefault('OAUTH2_TOKEN_SECRET', os.urandom(32))
        app.config.setdefault('OAUTH2_ISSUER', 'https://api.flavorsnap.com')
        
        # Register OAuth2 routes
        self._register_routes()
        
        # Initialize default clients
        self._initialize_default_clients()
    
    def _register_routes(self):
        """Register OAuth2 routes"""
        if self.app:
            self.app.add_url_rule(
                OAuth2Config.AUTHORIZATION_ENDPOINT,
                'oauth_authorize',
                self.authorization_endpoint,
                methods=['GET', 'POST']
            )
            self.app.add_url_rule(
                OAuth2Config.TOKEN_ENDPOINT,
                'oauth_token',
                self.token_endpoint,
                methods=['POST']
            )
            self.app.add_url_rule(
                OAuth2Config.USERINFO_ENDPOINT,
                'oauth_userinfo',
                self.userinfo_endpoint,
                methods=['GET']
            )
            self.app.add_url_rule(
                OAuth2Config.REVOCATION_ENDPOINT,
                'oauth_revoke',
                self.revocation_endpoint,
                methods=['POST']
            )
    
    def _initialize_default_clients(self):
        """Initialize default OAuth2 clients"""
        # Web application client
        web_client = OAuth2Client(
            client_id="web_app_client",
            client_secret=secrets.token_urlsafe(32),
            redirect_uris=["http://localhost:3000/callback", "https://app.flavorsnap.com/callback"],
            scopes=["read", "write", "profile", "email"],
            grant_types=["authorization_code", "refresh_token"]
        )
        self.clients[web_client.client_id] = web_client
        
        # Mobile application client
        mobile_client = OAuth2Client(
            client_id="mobile_app_client",
            client_secret=secrets.token_urlsafe(32),
            redirect_uris=["flavorsnap://callback"],
            scopes=["read", "write", "profile"],
            grant_types=["authorization_code", "refresh_token"]
        )
        self.clients[mobile_client.client_id] = mobile_client
        
        # Service/machine-to-machine client
        service_client = OAuth2Client(
            client_id="service_client",
            client_secret=secrets.token_urlsafe(32),
            redirect_uris=[],
            scopes=["read", "write", "admin"],
            grant_types=["client_credentials"]
        )
        self.clients[service_client.client_id] = service_client
    
    def register_client(self, client_id: str, client_secret: str, redirect_uris: List[str],
                       scopes: List[str], grant_types: List[str]) -> OAuth2Client:
        """Register a new OAuth2 client"""
        client = OAuth2Client(client_id, client_secret, redirect_uris, scopes, grant_types)
        self.clients[client_id] = client
        self.logger.info(f"Registered OAuth2 client: {client_id}")
        return client
    
    def authorization_endpoint(self):
        """OAuth2 authorization endpoint"""
        if request.method == 'GET':
            return self._handle_authorization_request()
        else:
            return self._handle_authorization_approval()
    
    def _handle_authorization_request(self) -> Dict[str, Any]:
        """Handle authorization request"""
        # Validate required parameters
        required_params = ['response_type', 'client_id', 'redirect_uri', 'scope']
        for param in required_params:
            if param not in request.args:
                return {'error': 'invalid_request', 'error_description': f'Missing required parameter: {param}'}
        
        response_type = request.args['response_type']
        client_id = request.args['client_id']
        redirect_uri = request.args['redirect_uri']
        scope = request.args['scope']
        state = request.args.get('state')
        code_challenge = request.args.get('code_challenge')
        code_challenge_method = request.args.get('code_challenge_method', 'S256')
        
        # Validate response type
        if response_type != 'code':
            return {'error': 'unsupported_response_type', 'error_description': 'Only authorization code flow is supported'}
        
        # Validate client
        if client_id not in self.clients:
            return {'error': 'invalid_client', 'error_description': 'Invalid client_id'}
        
        client = self.clients[client_id]
        if not client.is_active:
            return {'error': 'invalid_client', 'error_description': 'Client is inactive'}
        
        # Validate redirect URI
        if not client.validate_redirect_uri(redirect_uri):
            return {'error': 'invalid_redirect_uri', 'error_description': 'Invalid redirect URI'}
        
        # Validate scope
        requested_scopes = scope.split()
        valid_scopes = client.validate_scope(requested_scopes)
        if not valid_scopes:
            return {'error': 'invalid_scope', 'error_description': 'No valid scopes requested'}
        
        # Validate PKCE
        if OAuth2Config.PKCE_REQUIRED and not code_challenge:
            return {'error': 'invalid_request', 'error_description': 'PKCE is required'}
        
        # Validate state
        if OAuth2Config.STATE_REQUIRED and not state:
            return {'error': 'invalid_request', 'error_description': 'State parameter is required'}
        
        # Store authorization request
        auth_request = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(valid_scopes),
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': code_challenge_method,
            'created_at': datetime.now()
        }
        
        # Generate authorization code
        auth_code = secrets.token_urlsafe(32)
        self.authorization_codes[auth_code] = auth_request
        
        # In a real implementation, you would redirect to a login page
        # For this demo, we'll auto-approve
        return self._generate_authorization_response(auth_code, redirect_uri, state)
    
    def _handle_authorization_approval(self) -> Dict[str, Any]:
        """Handle authorization approval (POST)"""
        # This would handle user approval in a real implementation
        pass
    
    def _generate_authorization_response(self, auth_code: str, redirect_uri: str, state: str = None) -> Dict[str, Any]:
        """Generate authorization response"""
        params = {'code': auth_code}
        if state:
            params['state'] = state
        
        redirect_url = f"{redirect_uri}?{urlencode(params)}"
        return {'redirect_to': redirect_url}
    
    def token_endpoint(self) -> Dict[str, Any]:
        """OAuth2 token endpoint"""
        # Validate request
        if not request.is_json:
            data = request.form.to_dict()
        else:
            data = request.get_json()
        
        grant_type = data.get('grant_type')
        
        if grant_type == 'authorization_code':
            return self._handle_authorization_code_grant(data)
        elif grant_type == 'client_credentials':
            return self._handle_client_credentials_grant(data)
        elif grant_type == 'refresh_token':
            return self._handle_refresh_token_grant(data)
        else:
            return {'error': 'unsupported_grant_type', 'error_description': 'Invalid grant type'}
    
    def _handle_authorization_code_grant(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle authorization code grant"""
        required_params = ['code', 'client_id', 'redirect_uri']
        for param in required_params:
            if param not in data:
                return {'error': 'invalid_request', 'error_description': f'Missing required parameter: {param}'}
        
        code = data['code']
        client_id = data['client_id']
        redirect_uri = data['redirect_uri']
        code_verifier = data.get('code_verifier')
        
        # Validate authorization code
        if code not in self.authorization_codes:
            return {'error': 'invalid_grant', 'error_description': 'Invalid authorization code'}
        
        auth_request = self.authorization_codes[code]
        
        # Check if code is expired
        if datetime.now() > auth_request['created_at'] + timedelta(seconds=OAuth2Config.AUTH_CODE_LIFETIME):
            del self.authorization_codes[code]
            return {'error': 'invalid_grant', 'error_description': 'Authorization code expired'}
        
        # Validate client
        if auth_request['client_id'] != client_id:
            return {'error': 'invalid_client', 'error_description': 'Client ID mismatch'}
        
        # Validate redirect URI
        if auth_request['redirect_uri'] != redirect_uri:
            return {'error': 'invalid_grant', 'error_description': 'Redirect URI mismatch'}
        
        # Validate PKCE if required
        if auth_request['code_challenge'] and not code_verifier:
            return {'error': 'invalid_request', 'error_description': 'Code verifier is required'}
        
        if auth_request['code_challenge'] and not PKCEManager.verify_code_challenge(
            code_verifier, auth_request['code_challenge']
        ):
            return {'error': 'invalid_grant', 'error_description': 'Invalid code verifier'}
        
        # Generate tokens
        access_token = self._generate_access_token(client_id, auth_request['scope'])
        refresh_token = self._generate_refresh_token()
        
        token = OAuth2Token(
            token_type='Bearer',
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=OAuth2Config.ACCESS_TOKEN_LIFETIME,
            scope=auth_request['scope'],
            client_id=client_id
        )
        
        self.tokens[access_token] = token
        self.refresh_tokens[refresh_token] = access_token
        
        # Clean up authorization code
        del self.authorization_codes[code]
        
        self.logger.info(f"Generated tokens for client: {client_id}")
        return token.to_dict()
    
    def _handle_client_credentials_grant(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle client credentials grant"""
        required_params = ['client_id', 'client_secret', 'scope']
        for param in required_params:
            if param not in data:
                return {'error': 'invalid_request', 'error_description': f'Missing required parameter: {param}'}
        
        client_id = data['client_id']
        client_secret = data['client_secret']
        scope = data['scope']
        
        # Validate client
        if client_id not in self.clients:
            return {'error': 'invalid_client', 'error_description': 'Invalid client credentials'}
        
        client = self.clients[client_id]
        if not secrets.compare_digest(client.client_secret, client_secret):
            return {'error': 'invalid_client', 'error_description': 'Invalid client credentials'}
        
        if not client.is_active:
            return {'error': 'invalid_client', 'error_description': 'Client is inactive'}
        
        # Validate scope
        requested_scopes = scope.split()
        valid_scopes = client.validate_scope(requested_scopes)
        if not valid_scopes:
            return {'error': 'invalid_scope', 'error_description': 'No valid scopes requested'}
        
        # Generate access token (no refresh token for client credentials)
        access_token = self._generate_access_token(client_id, ' '.join(valid_scopes))
        
        token = OAuth2Token(
            token_type='Bearer',
            access_token=access_token,
            expires_in=OAuth2Config.ACCESS_TOKEN_LIFETIME,
            scope=' '.join(valid_scopes),
            client_id=client_id
        )
        
        self.tokens[access_token] = token
        
        self.logger.info(f"Generated client credentials token for: {client_id}")
        return token.to_dict()
    
    def _handle_refresh_token_grant(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle refresh token grant"""
        required_params = ['refresh_token', 'client_id']
        for param in required_params:
            if param not in data:
                return {'error': 'invalid_request', 'error_description': f'Missing required parameter: {param}'}
        
        refresh_token = data['refresh_token']
        client_id = data['client_id']
        scope = data.get('scope')
        
        # Validate refresh token
        if refresh_token not in self.refresh_tokens:
            return {'error': 'invalid_grant', 'error_description': 'Invalid refresh token'}
        
        access_token = self.refresh_tokens[refresh_token]
        if access_token not in self.tokens:
            del self.refresh_tokens[refresh_token]
            return {'error': 'invalid_grant', 'error_description': 'Access token not found'}
        
        token = self.tokens[access_token]
        
        # Validate client
        if token.client_id != client_id:
            return {'error': 'invalid_client', 'error_description': 'Client ID mismatch'}
        
        # Check if token is revoked
        if token.is_revoked:
            return {'error': 'invalid_grant', 'error_description': 'Token has been revoked'}
        
        # Generate new tokens
        new_access_token = self._generate_access_token(client_id, token.scope)
        new_refresh_token = self._generate_refresh_token()
        
        new_token = OAuth2Token(
            token_type='Bearer',
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=OAuth2Config.ACCESS_TOKEN_LIFETIME,
            scope=token.scope,
            client_id=client_id
        )
        
        # Revoke old tokens
        token.is_revoked = True
        del self.tokens[access_token]
        del self.refresh_tokens[refresh_token]
        
        self.tokens[new_access_token] = new_token
        self.refresh_tokens[new_refresh_token] = new_access_token
        
        self.logger.info(f"Refreshed tokens for client: {client_id}")
        return new_token.to_dict()
    
    def _generate_access_token(self, client_id: str, scope: str) -> str:
        """Generate JWT access token"""
        now = datetime.now()
        payload = {
            'iss': self.app.config.get('OAUTH2_ISSUER', 'https://api.flavorsnap.com'),
            'sub': client_id,
            'aud': 'flavorsnap-api',
            'exp': now + timedelta(seconds=OAuth2Config.ACCESS_TOKEN_LIFETIME),
            'iat': now,
            'scope': scope,
            'client_id': client_id,
            'token_type': 'access'
        }
        
        secret = self.app.config.get('OAUTH2_TOKEN_SECRET')
        return jwt.encode(payload, secret, algorithm='HS256')
    
    def _generate_refresh_token(self) -> str:
        """Generate refresh token"""
        return secrets.token_urlsafe(64)
    
    def userinfo_endpoint(self) -> Dict[str, Any]:
        """OAuth2 userinfo endpoint"""
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return {'error': 'invalid_token', 'error_description': 'Missing or invalid authorization header'}
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Validate access token
        if token not in self.tokens:
            return {'error': 'invalid_token', 'error_description': 'Invalid access token'}
        
        token_obj = self.tokens[token]
        
        # Check if token is expired or revoked
        if token_obj.is_expired() or token_obj.is_revoked:
            return {'error': 'invalid_token', 'error_description': 'Token is expired or revoked'}
        
        # Return user information based on scopes
        userinfo = {
            'sub': token_obj.client_id,
            'client_id': token_obj.client_id,
            'scope': token_obj.scope
        }
        
        # Add additional info based on scopes
        if 'profile' in token_obj.scope:
            userinfo.update({
                'name': f'Client {token_obj.client_id}',
                'created_at': self.clients[token_obj.client_id].created_at.isoformat()
            })
        
        return userinfo
    
    def revocation_endpoint(self) -> Dict[str, Any]:
        """OAuth2 token revocation endpoint"""
        if not request.is_json:
            data = request.form.to_dict()
        else:
            data = request.get_json()
        
        token = data.get('token')
        token_type_hint = data.get('token_type_hint', 'access_token')
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        
        if not token:
            return {'error': 'invalid_request', 'error_description': 'Missing token parameter'}
        
        # Validate client if provided
        if client_id and client_secret:
            if client_id not in self.clients:
                return {'error': 'invalid_client', 'error_description': 'Invalid client credentials'}
            
            client = self.clients[client_id]
            if not secrets.compare_digest(client.client_secret, client_secret):
                return {'error': 'invalid_client', 'error_description': 'Invalid client credentials'}
        
        # Revoke token
        revoked = False
        
        if token_type_hint == 'access_token' or token_type_hint is None:
            if token in self.tokens:
                self.tokens[token].is_revoked = True
                revoked = True
        
        if token_type_hint == 'refresh_token' or token_type_hint is None:
            if token in self.refresh_tokens:
                access_token = self.refresh_tokens[token]
                if access_token in self.tokens:
                    self.tokens[access_token].is_revoked = True
                del self.refresh_tokens[token]
                revoked = True
        
        if revoked:
            self.logger.info(f"Token revoked: {token_type_hint}")
            return {}
        else:
            return {'error': 'invalid_request', 'error_description': 'Token not found'}
    
    def validate_access_token(self, token: str) -> Optional[OAuth2Token]:
        """Validate access token and return token object"""
        if token not in self.tokens:
            return None
        
        token_obj = self.tokens[token]
        
        # Check if token is expired or revoked
        if token_obj.is_expired() or token_obj.is_revoked:
            return None
        
        return token_obj
    
    def cleanup_expired_tokens(self):
        """Clean up expired tokens"""
        now = datetime.now()
        expired_tokens = []
        
        for token, token_obj in self.tokens.items():
            if token_obj.is_expired():
                expired_tokens.append(token)
        
        for token in expired_tokens:
            token_obj = self.tokens[token]
            if token_obj.refresh_token and token_obj.refresh_token in self.refresh_tokens:
                del self.refresh_tokens[token_obj.refresh_token]
            del self.tokens[token]
        
        if expired_tokens:
            self.logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")


# Initialize global OAuth2 handler
oauth2_handler = OAuth2Handler()
