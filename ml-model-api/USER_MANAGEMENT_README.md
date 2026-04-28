# Advanced User Management System - FlavorSnap API

## Overview

This comprehensive user management system implements enterprise-grade authentication, authorization, and profile management for the FlavorSnap API. The system includes role-based access control (RBAC), multi-factor authentication (MFA), session management, GDPR compliance, and extensive user analytics.

## Features

### ✅ User Authentication System
- **Password-based authentication** with bcrypt hashing
- **JWT token-based authentication** with access and refresh tokens
- **OAuth2 support** for third-party authentication
- **Multi-factor authentication (2FA)** using TOTP
- **Session management** with configurable timeouts
- **Account lockout** after failed login attempts

### ✅ Role-Based Authorization
- **Five user roles**: Admin, Moderator, Premium, User, Guest
- **Granular permissions** system with 12+ permission types
- **Role-based access control** for all endpoints
- **Permission inheritance** and custom permission sets

### ✅ Profile Management
- **Extended user profiles** with customizable fields
- **Avatar and cover image** upload with automatic resizing
- **User preferences** for notifications, privacy, and accessibility
- **Social links** and personal information management
- **User statistics** and activity tracking

### ✅ Password Policies
- **Minimum length**: 12 characters
- **Complexity requirements**: uppercase, lowercase, digits, special characters
- **Password history**: prevents reuse of last 5 passwords
- **Password expiration**: 90-day expiry with forced reset
- **Account lockout**: 5 failed attempts = 30-minute lockout

### ✅ Session Management
- **Session lifetime**: 24 hours with idle timeout
- **Multiple sessions**: up to 5 concurrent sessions per user
- **Session tracking**: IP address, user agent, activity timestamps
- **Session revocation**: individual or bulk session termination
- **Secure cookies**: HttpOnly, Secure, SameSite attributes

### ✅ User Analytics
- **Individual user analytics**: activity tracking, usage patterns
- **System-wide analytics**: user distribution, verification rates
- **Login history**: successful and failed login attempts
- **Activity logs**: comprehensive audit trail
- **Statistics dashboard**: predictions, uploads, API calls

### ✅ GDPR Compliance
- **Data export**: complete user data in JSON format
- **Data deletion**: soft and hard delete options
- **Consent management**: granular consent tracking
- **Right to be forgotten**: automated data removal
- **Audit logging**: complete compliance trail

## Architecture

### Core Components

```
ml-model-api/
├── user_handlers.py          # User CRUD operations and management
├── auth_handlers.py           # Authentication and session management
├── profile_handlers.py        # Profile and preferences management
├── user_api_endpoints.py      # REST API endpoints
├── security_config.py         # Security policies and validation
├── jwt_handler.py             # JWT token management
├── oauth2_handler.py          # OAuth2 implementation
└── gdpr_compliance.py         # GDPR compliance features
```

### Data Models

#### User Model
```python
{
    "user_id": "uuid",
    "username": "string",
    "email": "string",
    "role": "admin|moderator|premium|user|guest",
    "status": "active|inactive|suspended|pending_verification|deleted",
    "email_verified": boolean,
    "two_factor_enabled": boolean,
    "created_at": "datetime",
    "last_login": "datetime"
}
```

#### Profile Model
```python
{
    "user_id": "uuid",
    "display_name": "string",
    "bio": "string",
    "avatar_url": "string",
    "location": "string",
    "website": "string",
    "social_links": {},
    "language": "string",
    "timezone": "string"
}
```

## API Endpoints

### Authentication Endpoints

#### Register User
```http
POST /api/v1/auth/register
Content-Type: application/json

{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "phone_number": "+1234567890"
}
```

**Response:**
```json
{
    "message": "Registration successful",
    "user": { ... },
    "verification_token": "token_here"
}
```

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
    "username": "johndoe",
    "password": "SecurePass123!",
    "two_factor_code": "123456"
}
```

**Response:**
```json
{
    "message": "Login successful",
    "user": { ... },
    "access_token": "jwt_token",
    "refresh_token": "refresh_token",
    "token_type": "Bearer",
    "expires_in": 86400
}
```

#### Logout
```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

#### Refresh Token
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
    "refresh_token": "refresh_token_here"
}
```

#### Verify Email
```http
POST /api/v1/auth/verify-email
Content-Type: application/json

{
    "token": "verification_token"
}
```

#### Request Password Reset
```http
POST /api/v1/auth/password-reset/request
Content-Type: application/json

{
    "email": "john@example.com"
}
```

#### Reset Password
```http
POST /api/v1/auth/password-reset/confirm
Content-Type: application/json

{
    "token": "reset_token",
    "new_password": "NewSecurePass123!"
}
```

#### Enable 2FA
```http
POST /api/v1/auth/2fa/enable
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "message": "2FA enabled successfully",
    "secret": "secret_key",
    "qr_code_uri": "otpauth://...",
    "backup_codes": ["code1", "code2", ...]
}
```

#### Disable 2FA
```http
POST /api/v1/auth/2fa/disable
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "password": "SecurePass123!"
}
```

#### Get Sessions
```http
GET /api/v1/auth/sessions
Authorization: Bearer <access_token>
```

#### Revoke Session
```http
DELETE /api/v1/auth/sessions/<session_id>
Authorization: Bearer <access_token>
```

#### Revoke All Sessions
```http
POST /api/v1/auth/sessions/revoke-all
Authorization: Bearer <access_token>
```

### User Management Endpoints

#### List Users
```http
GET /api/v1/users?page=1&page_size=20&role=user&status=active&search=john
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "users": [ ... ],
    "pagination": {
        "page": 1,
        "page_size": 20,
        "total_users": 100,
        "total_pages": 5
    }
}
```

#### Get User
```http
GET /api/v1/users/<user_id>
Authorization: Bearer <access_token>
```

#### Update User
```http
PUT /api/v1/users/<user_id>
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "username": "newusername",
    "email": "newemail@example.com",
    "role": "premium",
    "status": "active"
}
```

#### Delete User
```http
DELETE /api/v1/users/<user_id>?hard_delete=false
Authorization: Bearer <access_token>
```

#### Change Password
```http
PUT /api/v1/users/<user_id>/password
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "old_password": "OldPass123!",
    "new_password": "NewPass123!"
}
```

#### Get User Analytics
```http
GET /api/v1/users/<user_id>/analytics
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "user_id": "uuid",
    "username": "johndoe",
    "account_age_days": 365,
    "last_login": "2024-01-01T00:00:00",
    "total_activities": 1000,
    "activity_by_type": {
        "login": 50,
        "prediction": 800,
        "profile_update": 10
    }
}
```

#### Get System Analytics
```http
GET /api/v1/users/analytics/system
Authorization: Bearer <access_token>
```

### Profile Management Endpoints

#### Get Profile
```http
GET /api/v1/profile
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "user": { ... },
    "profile": { ... },
    "preferences": { ... },
    "statistics": { ... },
    "permissions": [ ... ]
}
```

#### Update Profile
```http
PUT /api/v1/profile
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "display_name": "John Doe",
    "bio": "Food enthusiast",
    "location": "New York, USA",
    "website": "https://johndoe.com",
    "social_links": {
        "twitter": "https://twitter.com/johndoe",
        "instagram": "https://instagram.com/johndoe"
    }
}
```

#### Upload Avatar
```http
POST /api/v1/profile/avatar
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

avatar: <file>
```

#### Upload Cover Image
```http
POST /api/v1/profile/cover
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

cover: <file>
```

#### Get Preferences
```http
GET /api/v1/profile/preferences
Authorization: Bearer <access_token>
```

#### Update Preferences
```http
PUT /api/v1/profile/preferences
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "notifications": {
        "email": true,
        "push": true,
        "marketing": false
    },
    "privacy": {
        "profile_visibility": "public",
        "email_visibility": "private"
    },
    "theme": "dark",
    "language": "en"
}
```

#### Get Statistics
```http
GET /api/v1/profile/statistics
Authorization: Bearer <access_token>
```

#### Export Profile Data (GDPR)
```http
GET /api/v1/profile/export
Authorization: Bearer <access_token>
```

#### Delete Profile Data (GDPR)
```http
POST /api/v1/profile/delete
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "password": "SecurePass123!",
    "confirmation": "DELETE"
}
```

## Security Features

### Password Policy
- **Minimum length**: 12 characters
- **Maximum length**: 128 characters
- **Required**: uppercase, lowercase, digits, special characters
- **Prohibited**: repeated characters, sequential patterns
- **History**: last 5 passwords cannot be reused
- **Expiration**: 90 days

### Account Lockout
- **Failed attempts**: 5 attempts
- **Lockout duration**: 30 minutes
- **Reset**: successful login or admin intervention

### Session Security
- **Lifetime**: 24 hours
- **Idle timeout**: 1 hour
- **Max sessions**: 5 per user
- **Secure cookies**: HttpOnly, Secure, SameSite

### Token Security
- **Access token**: 1 hour lifetime
- **Refresh token**: 30 days lifetime
- **Algorithm**: HS256 (configurable)
- **Key rotation**: 7 days
- **Blacklisting**: immediate revocation

## Role-Based Access Control

### Roles and Permissions

| Role | Permissions |
|------|-------------|
| **Admin** | All permissions (full system access) |
| **Moderator** | User read/write, content management, analytics read |
| **Premium** | User read/write, content read/write, analytics read |
| **User** | User read, content read/write |
| **Guest** | Content read only |

### Permission Types
- `user:read` - View user information
- `user:write` - Modify user information
- `user:delete` - Delete users
- `content:read` - View content
- `content:write` - Create/modify content
- `content:delete` - Delete content
- `admin:read` - View admin data
- `admin:write` - Modify admin settings
- `admin:delete` - Delete admin resources
- `analytics:read` - View analytics
- `analytics:write` - Modify analytics
- `system:config` - Configure system
- `system:monitor` - Monitor system

## Usage Examples

### Python Client Example

```python
import requests

BASE_URL = "http://localhost:5000/api/v1"

# Register user
response = requests.post(f"{BASE_URL}/auth/register", json={
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePass123!"
})
print(response.json())

# Login
response = requests.post(f"{BASE_URL}/auth/login", json={
    "username": "johndoe",
    "password": "SecurePass123!"
})
tokens = response.json()
access_token = tokens['access_token']

# Get profile
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(f"{BASE_URL}/profile", headers=headers)
print(response.json())

# Update profile
response = requests.put(f"{BASE_URL}/profile", headers=headers, json={
    "display_name": "John Doe",
    "bio": "Food enthusiast"
})
print(response.json())
```

### JavaScript Client Example

```javascript
const BASE_URL = 'http://localhost:5000/api/v1';

// Register user
const register = async () => {
    const response = await fetch(`${BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: 'johndoe',
            email: 'john@example.com',
            password: 'SecurePass123!'
        })
    });
    return response.json();
};

// Login
const login = async () => {
    const response = await fetch(`${BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: 'johndoe',
            password: 'SecurePass123!'
        })
    });
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    return data;
};

// Get profile
const getProfile = async () => {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${BASE_URL}/profile`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    return response.json();
};
```

## Integration with Main Application

To integrate the user management system with your main Flask application:

```python
from flask import Flask
from user_api_endpoints import register_user_management_routes
from auth_handlers import auth_manager
from user_handlers import user_manager
from profile_handlers import profile_manager

app = Flask(__name__)

# Initialize managers
auth_manager.init_app(app)
user_manager.init_app(app)
profile_manager.init_app(app)

# Register routes
register_user_management_routes(app)

if __name__ == '__main__':
    app.run(debug=True)
```

## Database Schema

While the current implementation uses in-memory storage, here's the recommended database schema for production:

```sql
-- Users table
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    status VARCHAR(30) NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    phone_number VARCHAR(20),
    phone_verified BOOLEAN DEFAULT FALSE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(255),
    failed_login_attempts INTEGER DEFAULT 0,
    account_locked_until TIMESTAMP,
    password_changed_at TIMESTAMP,
    must_change_password BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    metadata JSONB
);

-- Profiles table
CREATE TABLE profiles (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    display_name VARCHAR(100),
    bio TEXT,
    avatar_url VARCHAR(500),
    cover_image_url VARCHAR(500),
    location VARCHAR(100),
    website VARCHAR(500),
    social_links JSONB,
    date_of_birth DATE,
    gender VARCHAR(20),
    language VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Preferences table
CREATE TABLE preferences (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    notifications JSONB,
    privacy JSONB,
    email_frequency VARCHAR(20) DEFAULT 'daily',
    theme VARCHAR(20) DEFAULT 'light',
    language VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    accessibility JSONB,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sessions table
CREATE TABLE sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_activity TIMESTAMP
);

-- Activity logs table
CREATE TABLE activity_logs (
    activity_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,
    activity_data JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Password history table
CREATE TABLE password_history (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_timestamp ON activity_logs(timestamp);
```

## Testing

### Unit Tests Example

```python
import unittest
from user_handlers import user_manager, UserRole
from auth_handlers import auth_manager

class TestUserManagement(unittest.TestCase):
    
    def test_create_user(self):
        success, user, error = user_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            role=UserRole.USER
        )
        self.assertTrue(success)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")
    
    def test_login(self):
        # Create user first
        user_manager.create_user(
            username="logintest",
            email="login@example.com",
            password="TestPass123!"
        )
        
        # Test login
        success, result, error = auth_manager.login(
            username="logintest",
            password="TestPass123!"
        )
        self.assertTrue(success)
        self.assertIn('access_token', result)
    
    def test_password_policy(self):
        from user_handlers import PasswordPolicy
        
        # Test weak password
        is_valid, error = PasswordPolicy.validate_password("weak")
        self.assertFalse(is_valid)
        
        # Test strong password
        is_valid, error = PasswordPolicy.validate_password("StrongPass123!")
        self.assertTrue(is_valid)

if __name__ == '__main__':
    unittest.main()
```

## Monitoring and Logging

The system includes comprehensive logging for:
- User registration and login attempts
- Password changes and resets
- Profile updates
- Permission checks
- Session management
- Security events

All logs include:
- Timestamp
- User ID
- IP address
- User agent
- Action performed
- Result (success/failure)

## Best Practices

1. **Always use HTTPS** in production
2. **Store secrets securely** using environment variables
3. **Implement rate limiting** on authentication endpoints
4. **Monitor failed login attempts** for security threats
5. **Regularly rotate JWT keys** (every 7 days)
6. **Clean up expired sessions** periodically
7. **Backup user data** regularly
8. **Audit security logs** for suspicious activity
9. **Keep dependencies updated** for security patches
10. **Test authentication flows** thoroughly

## Troubleshooting

### Common Issues

**Issue**: "Account is locked"
- **Solution**: Wait for lockout duration (30 minutes) or contact admin

**Issue**: "Token has expired"
- **Solution**: Use refresh token to get new access token

**Issue**: "Invalid two-factor authentication code"
- **Solution**: Ensure device time is synchronized, use backup codes if needed

**Issue**: "Password does not meet requirements"
- **Solution**: Check password policy requirements (12+ chars, mixed case, digits, special chars)

## Support

For issues, questions, or contributions:
- GitHub Issues: [FlavorSnap Issues](https://github.com/flavorsnap/issues)
- Documentation: [FlavorSnap Docs](https://docs.flavorsnap.com)
- Email: support@flavorsnap.com

## License

This user management system is part of the FlavorSnap API and is licensed under the MIT License.
