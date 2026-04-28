# Quick Start Guide - User Management System

## 🚀 Get Started in 5 Minutes

This guide will help you quickly set up and test the user management system.

## Prerequisites

- Python 3.8+
- PostgreSQL 12+ (optional, can use in-memory storage for testing)
- pip package manager

## Step 1: Install Dependencies (1 minute)

```bash
cd flavorsnap/ml-model-api
pip install -r requirements.txt
```

**New dependencies added:**
- `bcrypt` - Password hashing
- `PyJWT` - JWT token management
- `cryptography` - Encryption utilities
- `pyotp` - Two-factor authentication
- `qrcode` - QR code generation for 2FA

## Step 2: Quick Test (1 minute)

Run the test suite to verify everything works:

```bash
python test_user_management.py
```

You should see output like:
```
test_password_minimum_length ... ok
test_password_complexity ... ok
test_create_user ... ok
test_successful_login ... ok
...
----------------------------------------------------------------------
Ran 40 tests in 2.345s

OK
```

## Step 3: Start the API (1 minute)

### Option A: Standalone Testing

Create a simple test file `test_api.py`:

```python
from flask import Flask
from user_api_endpoints import register_user_management_routes
from auth_handlers import auth_manager
from user_handlers import user_manager
from profile_handlers import profile_manager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-secret-key-change-in-production'
app.config['TESTING'] = False

# Initialize managers
auth_manager.init_app(app)
user_manager.init_app(app)
profile_manager.init_app(app)

# Register routes
register_user_management_routes(app)

if __name__ == '__main__':
    print("🚀 User Management API running on http://localhost:5000")
    print("📚 Default admin credentials:")
    print("   Username: admin")
    print("   Password: Admin@123456")
    app.run(debug=True, port=5000)
```

Run it:
```bash
python test_api.py
```

### Option B: Integrate with Existing App

Add to your existing `app.py`:

```python
# Add these imports at the top
from user_api_endpoints import register_user_management_routes
from auth_handlers import auth_manager
from user_handlers import user_manager
from profile_handlers import profile_manager

# After creating your Flask app
auth_manager.init_app(app)
user_manager.init_app(app)
profile_manager.init_app(app)
register_user_management_routes(app)
```

## Step 4: Test the API (2 minutes)

### Using cURL

**1. Register a new user:**
```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

**2. Login:**
```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPass123!"
  }'
```

Save the `access_token` from the response.

**3. Get your profile:**
```bash
curl -X GET http://localhost:5000/api/v1/profile \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**4. Update your profile:**
```bash
curl -X PUT http://localhost:5000/api/v1/profile \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Test User",
    "bio": "I love food!",
    "location": "New York"
  }'
```

### Using Python

```python
import requests

BASE_URL = "http://localhost:5000/api/v1"

# Register
response = requests.post(f"{BASE_URL}/auth/register", json={
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPass123!"
})
print("Register:", response.json())

# Login
response = requests.post(f"{BASE_URL}/auth/login", json={
    "username": "testuser",
    "password": "TestPass123!"
})
data = response.json()
token = data['access_token']
print("Login successful!")

# Get profile
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(f"{BASE_URL}/profile", headers=headers)
print("Profile:", response.json())

# Update profile
response = requests.put(f"{BASE_URL}/profile", headers=headers, json={
    "display_name": "Test User",
    "bio": "I love food!"
})
print("Updated:", response.json())
```

### Using JavaScript/Node.js

```javascript
const BASE_URL = 'http://localhost:5000/api/v1';

async function testAPI() {
    // Register
    let response = await fetch(`${BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: 'testuser',
            email: 'test@example.com',
            password: 'TestPass123!'
        })
    });
    console.log('Register:', await response.json());

    // Login
    response = await fetch(`${BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: 'testuser',
            password: 'TestPass123!'
        })
    });
    const data = await response.json();
    const token = data.access_token;
    console.log('Login successful!');

    // Get profile
    response = await fetch(`${BASE_URL}/profile`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    console.log('Profile:', await response.json());

    // Update profile
    response = await fetch(`${BASE_URL}/profile`, {
        method: 'PUT',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            display_name: 'Test User',
            bio: 'I love food!'
        })
    });
    console.log('Updated:', await response.json());
}

testAPI();
```

## Common Use Cases

### 1. User Registration Flow

```python
# 1. Register user
register_response = requests.post(f"{BASE_URL}/auth/register", json={
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "SecurePass123!"
})
verification_token = register_response.json()['verification_token']

# 2. Verify email
verify_response = requests.post(f"{BASE_URL}/auth/verify-email", json={
    "token": verification_token
})

# 3. Login
login_response = requests.post(f"{BASE_URL}/auth/login", json={
    "username": "newuser",
    "password": "SecurePass123!"
})
```

### 2. Password Reset Flow

```python
# 1. Request password reset
reset_request = requests.post(f"{BASE_URL}/auth/password-reset/request", json={
    "email": "user@example.com"
})
reset_token = reset_request.json()['reset_token']

# 2. Reset password
reset_response = requests.post(f"{BASE_URL}/auth/password-reset/confirm", json={
    "token": reset_token,
    "new_password": "NewSecurePass123!"
})
```

### 3. Enable Two-Factor Authentication

```python
# 1. Enable 2FA
headers = {"Authorization": f"Bearer {access_token}"}
enable_2fa = requests.post(f"{BASE_URL}/auth/2fa/enable", headers=headers)
data = enable_2fa.json()

print("Secret:", data['secret'])
print("QR Code URI:", data['qr_code_uri'])
print("Backup Codes:", data['backup_codes'])

# 2. Login with 2FA
login_with_2fa = requests.post(f"{BASE_URL}/auth/login", json={
    "username": "user",
    "password": "password",
    "two_factor_code": "123456"  # From authenticator app
})
```

### 4. Admin Operations

```python
# Login as admin
admin_login = requests.post(f"{BASE_URL}/auth/login", json={
    "username": "admin",
    "password": "Admin@123456"
})
admin_token = admin_login.json()['access_token']
admin_headers = {"Authorization": f"Bearer {admin_token}"}

# List all users
users = requests.get(f"{BASE_URL}/users?page=1&page_size=20", 
                     headers=admin_headers)
print("Users:", users.json())

# Update user role
update_user = requests.put(f"{BASE_URL}/users/{user_id}", 
                           headers=admin_headers,
                           json={"role": "premium"})

# Get system analytics
analytics = requests.get(f"{BASE_URL}/users/analytics/system",
                        headers=admin_headers)
print("Analytics:", analytics.json())
```

## Default Credentials

The system comes with a default admin account:

- **Username:** `admin`
- **Email:** `admin@flavorsnap.com`
- **Password:** `Admin@123456`

⚠️ **IMPORTANT:** Change the admin password immediately in production!

```python
# Change admin password
requests.put(f"{BASE_URL}/users/{admin_user_id}/password",
            headers=admin_headers,
            json={
                "old_password": "Admin@123456",
                "new_password": "NewSecureAdminPass123!"
            })
```

## Password Requirements

When creating passwords, ensure they meet these requirements:

✅ Minimum 12 characters
✅ At least one uppercase letter
✅ At least one lowercase letter
✅ At least one digit
✅ At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
❌ No repeated characters (aaa)
❌ No sequential characters (abc, 123)

**Valid examples:**
- `SecurePass123!`
- `MyP@ssw0rd2024`
- `Fl@v0rSn@p!23`

**Invalid examples:**
- `short` (too short)
- `nouppercase123!` (no uppercase)
- `NOLOWERCASE123!` (no lowercase)
- `NoDigitsHere!` (no digits)
- `NoSpecialChar123` (no special character)

## API Response Format

### Success Response
```json
{
    "message": "Operation successful",
    "data": { ... }
}
```

### Error Response
```json
{
    "error": "Error message describing what went wrong"
}
```

### Authentication Response
```json
{
    "message": "Login successful",
    "user": { ... },
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "Bearer",
    "expires_in": 3600
}
```

## Troubleshooting

### Issue: "Module not found" errors
**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "Invalid password" on login
**Solution:** Check password meets requirements (12+ chars, mixed case, digits, special chars)

### Issue: "Token has expired"
**Solution:** Use refresh token to get new access token
```python
requests.post(f"{BASE_URL}/auth/refresh", json={
    "refresh_token": refresh_token
})
```

### Issue: "Account is locked"
**Solution:** Wait 30 minutes or contact admin to unlock

### Issue: "Insufficient permissions"
**Solution:** Check user role and required permissions for the endpoint

## Next Steps

1. **Read the full documentation:** `USER_MANAGEMENT_README.md`
2. **Review API endpoints:** See all 30+ endpoints in the README
3. **Set up database:** Run `migrations/001_create_user_tables.sql`
4. **Configure production:** Set environment variables for secrets
5. **Enable HTTPS:** Configure SSL certificates for production
6. **Set up monitoring:** Integrate with your monitoring system
7. **Customize:** Extend the system for your specific needs

## Quick Reference

### Key Endpoints
- Register: `POST /api/v1/auth/register`
- Login: `POST /api/v1/auth/login`
- Logout: `POST /api/v1/auth/logout`
- Profile: `GET /api/v1/profile`
- Update Profile: `PUT /api/v1/profile`
- List Users: `GET /api/v1/users`
- User Analytics: `GET /api/v1/users/{id}/analytics`

### Key Files
- `user_handlers.py` - User management logic
- `auth_handlers.py` - Authentication logic
- `profile_handlers.py` - Profile management logic
- `user_api_endpoints.py` - API endpoints
- `test_user_management.py` - Test suite

### Environment Variables
```bash
export SECRET_KEY="your-secret-key"
export ADMIN_PASSWORD="secure-admin-password"
export JWT_SECRET_KEY="your-jwt-secret"
export FLASK_ENV="production"
```

## Support

Need help? Check these resources:
- 📚 Full Documentation: `USER_MANAGEMENT_README.md`
- 📋 Implementation Details: `IMPLEMENTATION_SUMMARY.md`
- 🧪 Test Examples: `test_user_management.py`
- 🗄️ Database Schema: `migrations/001_create_user_tables.sql`

---

**Happy coding! 🎉**

If you encounter any issues, please review the full documentation or check the test suite for examples.
