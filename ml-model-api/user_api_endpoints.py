"""
User Management API Endpoints for FlavorSnap
Comprehensive REST API for user management, authentication, and profile operations
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, make_response

# Import handlers
from user_handlers import (
    user_manager, UserRole, UserStatus, Permission
)
from auth_handlers import (
    auth_manager, require_auth, require_role, require_permission,
    SessionConfig
)
from profile_handlers import profile_manager
from security_config import InputValidator, RateLimitManager

# Create blueprint
user_api = Blueprint('user_api', __name__, url_prefix='/api/v1/users')
auth_api = Blueprint('auth_api', __name__, url_prefix='/api/v1/auth')
profile_api = Blueprint('profile_api', __name__, url_prefix='/api/v1/profile')

logger = logging.getLogger(__name__)


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@auth_api.route('/register', methods=['POST'])
def register():
    """
    Register new user
    ---
    POST /api/v1/auth/register
    Body:
        username: string (required)
        email: string (required)
        password: string (required)
        phone_number: string (optional)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        phone_number = data.get('phone_number')
        
        if not username or not email or not password:
            return jsonify({'error': 'Username, email, and password are required'}), 400
        
        # Register user
        success, result, error = auth_manager.register(
            username=username,
            email=email,
            password=password,
            phone_number=phone_number
        )
        
        if not success:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'message': 'Registration successful',
            'user': result['user'],
            'verification_token': result['verification_token']
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_api.route('/login', methods=['POST'])
def login():
    """
    User login
    ---
    POST /api/v1/auth/login
    Body:
        username: string (required)
        password: string (required)
        two_factor_code: string (optional, required if 2FA enabled)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        username = data.get('username')
        password = data.get('password')
        two_factor_code = data.get('two_factor_code')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        # Login user
        success, result, error = auth_manager.login(
            username=username,
            password=password,
            two_factor_code=two_factor_code
        )
        
        if not success:
            return jsonify({'error': error}), 401
        
        # Set session cookie
        response = make_response(jsonify({
            'message': 'Login successful',
            'user': result['user'],
            'access_token': result['access_token'],
            'refresh_token': result['refresh_token'],
            'token_type': result['token_type'],
            'expires_in': result['expires_in']
        }))
        
        response.set_cookie(
            SessionConfig.SESSION_COOKIE_NAME,
            result['session']['session_id'],
            max_age=SessionConfig.SESSION_LIFETIME,
            secure=SessionConfig.SESSION_COOKIE_SECURE,
            httponly=SessionConfig.SESSION_COOKIE_HTTPONLY,
            samesite=SessionConfig.SESSION_COOKIE_SAMESITE
        )
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_api.route('/logout', methods=['POST'])
@require_auth
def logout():
    """
    User logout
    ---
    POST /api/v1/auth/logout
    Headers:
        Authorization: Bearer <token>
    """
    try:
        # Get session ID from cookie
        session_id = request.cookies.get(SessionConfig.SESSION_COOKIE_NAME)
        
        # Get access token from header
        auth_header = request.headers.get('Authorization')
        access_token = None
        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header[7:]
        
        # Logout
        success, error = auth_manager.logout(
            session_id=session_id,
            access_token=access_token
        )
        
        if not success:
            return jsonify({'error': error}), 400
        
        # Clear session cookie
        response = make_response(jsonify({'message': 'Logout successful'}))
        response.set_cookie(SessionConfig.SESSION_COOKIE_NAME, '', max_age=0)
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_api.route('/refresh', methods=['POST'])
def refresh_token():
    """
    Refresh access token
    ---
    POST /api/v1/auth/refresh
    Body:
        refresh_token: string (required)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({'error': 'Refresh token is required'}), 400
        
        # Refresh token
        success, result, error = auth_manager.refresh_token(refresh_token)
        
        if not success:
            return jsonify({'error': error}), 401
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_api.route('/verify-email', methods=['POST'])
def verify_email():
    """
    Verify email with token
    ---
    POST /api/v1/auth/verify-email
    Body:
        token: string (required)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Verification token is required'}), 400
        
        # Verify email
        success, error = auth_manager.verify_email(token)
        
        if not success:
            return jsonify({'error': error}), 400
        
        return jsonify({'message': 'Email verified successfully'}), 200
        
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_api.route('/password-reset/request', methods=['POST'])
def request_password_reset():
    """
    Request password reset
    ---
    POST /api/v1/auth/password-reset/request
    Body:
        email: string (required)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Request password reset
        success, reset_token, error = auth_manager.request_password_reset(email)
        
        # Always return success to prevent email enumeration
        return jsonify({
            'message': 'If the email exists, a password reset link has been sent',
            'reset_token': reset_token  # In production, send via email
        }), 200
        
    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_api.route('/password-reset/confirm', methods=['POST'])
def reset_password():
    """
    Reset password with token
    ---
    POST /api/v1/auth/password-reset/confirm
    Body:
        token: string (required)
        new_password: string (required)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        token = data.get('token')
        new_password = data.get('new_password')
        
        if not token or not new_password:
            return jsonify({'error': 'Token and new password are required'}), 400
        
        # Reset password
        success, error = auth_manager.reset_password(token, new_password)
        
        if not success:
            return jsonify({'error': error}), 400
        
        return jsonify({'message': 'Password reset successfully'}), 200
        
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_api.route('/2fa/enable', methods=['POST'])
@require_auth
def enable_two_factor():
    """
    Enable two-factor authentication
    ---
    POST /api/v1/auth/2fa/enable
    Headers:
        Authorization: Bearer <token>
    """
    try:
        user = request.current_user
        
        # Enable 2FA
        success, result, error = auth_manager.enable_two_factor(user.user_id)
        
        if not success:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'message': '2FA enabled successfully',
            'secret': result['secret'],
            'qr_code_uri': result['qr_code_uri'],
            'backup_codes': result['backup_codes']
        }), 200
        
    except Exception as e:
        logger.error(f"2FA enable error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_api.route('/2fa/disable', methods=['POST'])
@require_auth
def disable_two_factor():
    """
    Disable two-factor authentication
    ---
    POST /api/v1/auth/2fa/disable
    Headers:
        Authorization: Bearer <token>
    Body:
        password: string (required)
    """
    try:
        user = request.current_user
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        password = data.get('password')
        
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        
        # Disable 2FA
        success, error = auth_manager.disable_two_factor(user.user_id, password)
        
        if not success:
            return jsonify({'error': error}), 400
        
        return jsonify({'message': '2FA disabled successfully'}), 200
        
    except Exception as e:
        logger.error(f"2FA disable error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_api.route('/sessions', methods=['GET'])
@require_auth
def get_sessions():
    """
    Get all active sessions
    ---
    GET /api/v1/auth/sessions
    Headers:
        Authorization: Bearer <token>
    """
    try:
        user = request.current_user
        sessions = auth_manager.get_user_sessions(user.user_id)
        
        return jsonify({
            'sessions': sessions,
            'total': len(sessions)
        }), 200
        
    except Exception as e:
        logger.error(f"Get sessions error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_api.route('/sessions/<session_id>', methods=['DELETE'])
@require_auth
def revoke_session(session_id):
    """
    Revoke specific session
    ---
    DELETE /api/v1/auth/sessions/<session_id>
    Headers:
        Authorization: Bearer <token>
    """
    try:
        success, error = auth_manager.revoke_session(session_id)
        
        if not success:
            return jsonify({'error': error}), 404
        
        return jsonify({'message': 'Session revoked successfully'}), 200
        
    except Exception as e:
        logger.error(f"Revoke session error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_api.route('/sessions/revoke-all', methods=['POST'])
@require_auth
def revoke_all_sessions():
    """
    Revoke all sessions except current
    ---
    POST /api/v1/auth/sessions/revoke-all
    Headers:
        Authorization: Bearer <token>
    """
    try:
        user = request.current_user
        current_session_id = request.cookies.get(SessionConfig.SESSION_COOKIE_NAME)
        
        count = auth_manager.revoke_all_sessions(user.user_id, except_session_id=current_session_id)
        
        return jsonify({
            'message': f'Revoked {count} sessions',
            'count': count
        }), 200
        
    except Exception as e:
        logger.error(f"Revoke all sessions error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# USER MANAGEMENT ENDPOINTS
# ============================================================================

@user_api.route('', methods=['GET'])
@require_auth
@require_permission(Permission.USER_READ)
def list_users():
    """
    List all users with pagination and filtering
    ---
    GET /api/v1/users
    Query Parameters:
        page: int (default: 1)
        page_size: int (default: 20)
        role: string (optional)
        status: string (optional)
        search: string (optional)
    """
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        filters = {}
        if request.args.get('role'):
            try:
                filters['role'] = UserRole(request.args.get('role'))
            except ValueError:
                pass
        
        if request.args.get('status'):
            try:
                filters['status'] = UserStatus(request.args.get('status'))
            except ValueError:
                pass
        
        if request.args.get('search'):
            filters['search'] = request.args.get('search')
        
        result = user_manager.list_users(filters=filters, page=page, page_size=page_size)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"List users error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@user_api.route('/<user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    """
    Get user by ID
    ---
    GET /api/v1/users/<user_id>
    """
    try:
        current_user = request.current_user
        
        # Users can view their own profile, admins can view any profile
        if current_user.user_id != user_id and not user_manager.has_permission(current_user.user_id, Permission.USER_READ):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        user = user_manager.get_user(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@user_api.route('/<user_id>', methods=['PUT'])
@require_auth
def update_user(user_id):
    """
    Update user information
    ---
    PUT /api/v1/users/<user_id>
    Body:
        username: string (optional)
        email: string (optional)
        phone_number: string (optional)
        role: string (optional, admin only)
        status: string (optional, admin only)
    """
    try:
        current_user = request.current_user
        
        # Users can update their own profile, admins can update any profile
        if current_user.user_id != user_id and not user_manager.has_permission(current_user.user_id, Permission.USER_WRITE):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Only admins can change role and status
        if 'role' in data or 'status' in data:
            if not user_manager.has_permission(current_user.user_id, Permission.ADMIN_WRITE):
                return jsonify({'error': 'Insufficient permissions to change role or status'}), 403
        
        # Convert role and status strings to enums
        if 'role' in data:
            try:
                data['role'] = UserRole(data['role'])
            except ValueError:
                return jsonify({'error': 'Invalid role'}), 400
        
        if 'status' in data:
            try:
                data['status'] = UserStatus(data['status'])
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400
        
        success, user, error = user_manager.update_user(user_id, data)
        
        if not success:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Update user error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@user_api.route('/<user_id>', methods=['DELETE'])
@require_auth
@require_permission(Permission.USER_DELETE)
def delete_user(user_id):
    """
    Delete user
    ---
    DELETE /api/v1/users/<user_id>
    Query Parameters:
        hard_delete: bool (default: false)
    """
    try:
        hard_delete = request.args.get('hard_delete', 'false').lower() == 'true'
        
        success, error = user_manager.delete_user(user_id, soft_delete=not hard_delete)
        
        if not success:
            return jsonify({'error': error}), 404
        
        return jsonify({'message': 'User deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Delete user error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@user_api.route('/<user_id>/password', methods=['PUT'])
@require_auth
def change_password(user_id):
    """
    Change user password
    ---
    PUT /api/v1/users/<user_id>/password
    Body:
        old_password: string (required)
        new_password: string (required)
    """
    try:
        current_user = request.current_user
        
        # Users can only change their own password
        if current_user.user_id != user_id:
            return jsonify({'error': 'Cannot change another user\'s password'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not old_password or not new_password:
            return jsonify({'error': 'Old password and new password are required'}), 400
        
        success, error = user_manager.change_password(user_id, old_password, new_password)
        
        if not success:
            return jsonify({'error': error}), 400
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@user_api.route('/<user_id>/analytics', methods=['GET'])
@require_auth
def get_user_analytics(user_id):
    """
    Get user analytics
    ---
    GET /api/v1/users/<user_id>/analytics
    """
    try:
        current_user = request.current_user
        
        # Users can view their own analytics, admins can view any analytics
        if current_user.user_id != user_id and not user_manager.has_permission(current_user.user_id, Permission.ANALYTICS_READ):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        analytics = user_manager.get_user_analytics(user_id)
        
        if not analytics:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(analytics), 200
        
    except Exception as e:
        logger.error(f"Get user analytics error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@user_api.route('/analytics/system', methods=['GET'])
@require_auth
@require_permission(Permission.ANALYTICS_READ)
def get_system_analytics():
    """
    Get system-wide user analytics
    ---
    GET /api/v1/users/analytics/system
    """
    try:
        analytics = user_manager.get_system_analytics()
        
        return jsonify(analytics), 200
        
    except Exception as e:
        logger.error(f"Get system analytics error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# PROFILE MANAGEMENT ENDPOINTS
# ============================================================================

@profile_api.route('', methods=['GET'])
@require_auth
def get_profile():
    """
    Get current user's profile
    ---
    GET /api/v1/profile
    """
    try:
        user = request.current_user
        complete_profile = profile_manager.get_complete_profile(user.user_id)
        
        return jsonify(complete_profile), 200
        
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@profile_api.route('', methods=['PUT'])
@require_auth
def update_profile():
    """
    Update current user's profile
    ---
    PUT /api/v1/profile
    Body:
        display_name: string (optional)
        bio: string (optional)
        location: string (optional)
        website: string (optional)
        social_links: object (optional)
        date_of_birth: string (optional)
        gender: string (optional)
        language: string (optional)
        timezone: string (optional)
    """
    try:
        user = request.current_user
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        success, profile, error = profile_manager.update_profile(user.user_id, data)
        
        if not success:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'message': 'Profile updated successfully',
            'profile': profile.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Update profile error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@profile_api.route('/avatar', methods=['POST'])
@require_auth
def upload_avatar():
    """
    Upload user avatar
    ---
    POST /api/v1/profile/avatar
    Content-Type: multipart/form-data
    Body:
        avatar: file (required)
    """
    try:
        user = request.current_user
        
        if 'avatar' not in request.files:
            return jsonify({'error': 'Avatar file is required'}), 400
        
        file = request.files['avatar']
        
        success, avatar_url, error = profile_manager.upload_avatar(user.user_id, file)
        
        if not success:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'message': 'Avatar uploaded successfully',
            'avatar_url': avatar_url
        }), 200
        
    except Exception as e:
        logger.error(f"Upload avatar error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@profile_api.route('/cover', methods=['POST'])
@require_auth
def upload_cover():
    """
    Upload cover image
    ---
    POST /api/v1/profile/cover
    Content-Type: multipart/form-data
    Body:
        cover: file (required)
    """
    try:
        user = request.current_user
        
        if 'cover' not in request.files:
            return jsonify({'error': 'Cover file is required'}), 400
        
        file = request.files['cover']
        
        success, cover_url, error = profile_manager.upload_cover_image(user.user_id, file)
        
        if not success:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'message': 'Cover image uploaded successfully',
            'cover_url': cover_url
        }), 200
        
    except Exception as e:
        logger.error(f"Upload cover error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@profile_api.route('/preferences', methods=['GET'])
@require_auth
def get_preferences():
    """
    Get user preferences
    ---
    GET /api/v1/profile/preferences
    """
    try:
        user = request.current_user
        preferences = profile_manager.get_preferences(user.user_id)
        
        return jsonify(preferences.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Get preferences error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@profile_api.route('/preferences', methods=['PUT'])
@require_auth
def update_preferences():
    """
    Update user preferences
    ---
    PUT /api/v1/profile/preferences
    Body:
        notifications: object (optional)
        privacy: object (optional)
        email_frequency: string (optional)
        theme: string (optional)
        language: string (optional)
        timezone: string (optional)
        accessibility: object (optional)
    """
    try:
        user = request.current_user
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        success, preferences, error = profile_manager.update_preferences(user.user_id, data)
        
        if not success:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'message': 'Preferences updated successfully',
            'preferences': preferences.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Update preferences error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@profile_api.route('/statistics', methods=['GET'])
@require_auth
def get_statistics():
    """
    Get user statistics
    ---
    GET /api/v1/profile/statistics
    """
    try:
        user = request.current_user
        statistics = profile_manager.get_statistics(user.user_id)
        
        return jsonify(statistics.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Get statistics error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@profile_api.route('/export', methods=['GET'])
@require_auth
def export_profile_data():
    """
    Export all profile data (GDPR compliance)
    ---
    GET /api/v1/profile/export
    """
    try:
        user = request.current_user
        export_data = profile_manager.export_profile_data(user.user_id)
        
        return jsonify(export_data), 200
        
    except Exception as e:
        logger.error(f"Export profile data error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@profile_api.route('/delete', methods=['POST'])
@require_auth
def delete_profile_data():
    """
    Delete all profile data (GDPR compliance)
    ---
    POST /api/v1/profile/delete
    Body:
        password: string (required)
        confirmation: string (required, must be "DELETE")
    """
    try:
        user = request.current_user
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        password = data.get('password')
        confirmation = data.get('confirmation')
        
        if not password or confirmation != 'DELETE':
            return jsonify({'error': 'Password and confirmation required'}), 400
        
        # Verify password
        from user_handlers import PasswordPolicy
        if not PasswordPolicy.verify_password(password, user.password_hash):
            return jsonify({'error': 'Invalid password'}), 401
        
        # Delete profile data
        success, error = profile_manager.delete_profile_data(user.user_id)
        
        if not success:
            return jsonify({'error': error}), 400
        
        # Delete user account
        user_manager.delete_user(user.user_id, soft_delete=True)
        
        # Logout user
        session_id = request.cookies.get(SessionConfig.SESSION_COOKIE_NAME)
        auth_manager.logout(session_id=session_id)
        
        return jsonify({'message': 'Profile data deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Delete profile data error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


def register_user_management_routes(app):
    """Register all user management routes with Flask app"""
    app.register_blueprint(auth_api)
    app.register_blueprint(user_api)
    app.register_blueprint(profile_api)
    
    logger.info("User management routes registered")
