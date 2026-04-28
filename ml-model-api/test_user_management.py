"""
Comprehensive Test Suite for User Management System
Tests authentication, authorization, profile management, and GDPR compliance
"""
import unittest
import json
from datetime import datetime, timedelta
from flask import Flask

# Import modules to test
from user_handlers import (
    user_manager, UserRole, UserStatus, Permission, PasswordPolicy
)
from auth_handlers import auth_manager, SessionConfig
from profile_handlers import profile_manager
from user_api_endpoints import register_user_management_routes


class TestPasswordPolicy(unittest.TestCase):
    """Test password policy enforcement"""
    
    def test_password_minimum_length(self):
        """Test minimum password length requirement"""
        is_valid, error = PasswordPolicy.validate_password("Short1!")
        self.assertFalse(is_valid)
        self.assertIn("at least", error.lower())
    
    def test_password_complexity(self):
        """Test password complexity requirements"""
        # Missing uppercase
        is_valid, error = PasswordPolicy.validate_password("lowercase123!")
        self.assertFalse(is_valid)
        
        # Missing lowercase
        is_valid, error = PasswordPolicy.validate_password("UPPERCASE123!")
        self.assertFalse(is_valid)
        
        # Missing digit
        is_valid, error = PasswordPolicy.validate_password("NoDigitsHere!")
        self.assertFalse(is_valid)
        
        # Missing special character
        is_valid, error = PasswordPolicy.validate_password("NoSpecialChar123")
        self.assertFalse(is_valid)
    
    def test_password_patterns(self):
        """Test prohibited password patterns"""
        # Repeated characters
        is_valid, error = PasswordPolicy.validate_password("Aaa123456789!")
        self.assertFalse(is_valid)
        
        # Sequential characters
        is_valid, error = PasswordPolicy.validate_password("Abc123456789!")
        self.assertFalse(is_valid)
    
    def test_valid_password(self):
        """Test valid password"""
        is_valid, error = PasswordPolicy.validate_password("SecurePass123!")
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "TestPassword123!"
        password_hash = PasswordPolicy.hash_password(password)
        
        # Verify correct password
        self.assertTrue(PasswordPolicy.verify_password(password, password_hash))
        
        # Verify incorrect password
        self.assertFalse(PasswordPolicy.verify_password("WrongPassword", password_hash))


class TestUserManagement(unittest.TestCase):
    """Test user CRUD operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        user_manager.init_app(self.app)
        
        # Clear existing users except admin
        user_manager.users = {
            uid: user for uid, user in user_manager.users.items()
            if user.username == 'admin'
        }
    
    def test_create_user(self):
        """Test user creation"""
        success, user, error = user_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            role=UserRole.USER
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.role, UserRole.USER)
        self.assertEqual(user.status, UserStatus.PENDING_VERIFICATION)
    
    def test_create_duplicate_username(self):
        """Test creating user with duplicate username"""
        # Create first user
        user_manager.create_user(
            username="duplicate",
            email="user1@example.com",
            password="TestPass123!"
        )
        
        # Try to create second user with same username
        success, user, error = user_manager.create_user(
            username="duplicate",
            email="user2@example.com",
            password="TestPass123!"
        )
        
        self.assertFalse(success)
        self.assertIn("already exists", error.lower())
    
    def test_create_duplicate_email(self):
        """Test creating user with duplicate email"""
        # Create first user
        user_manager.create_user(
            username="user1",
            email="duplicate@example.com",
            password="TestPass123!"
        )
        
        # Try to create second user with same email
        success, user, error = user_manager.create_user(
            username="user2",
            email="duplicate@example.com",
            password="TestPass123!"
        )
        
        self.assertFalse(success)
        self.assertIn("already exists", error.lower())
    
    def test_get_user(self):
        """Test retrieving user"""
        success, user, _ = user_manager.create_user(
            username="gettest",
            email="get@example.com",
            password="TestPass123!"
        )
        
        retrieved_user = user_manager.get_user(user.user_id)
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.username, "gettest")
    
    def test_update_user(self):
        """Test updating user information"""
        success, user, _ = user_manager.create_user(
            username="updatetest",
            email="update@example.com",
            password="TestPass123!"
        )
        
        # Update user
        success, updated_user, error = user_manager.update_user(
            user.user_id,
            {'username': 'updatedname', 'role': UserRole.PREMIUM}
        )
        
        self.assertTrue(success)
        self.assertEqual(updated_user.username, 'updatedname')
        self.assertEqual(updated_user.role, UserRole.PREMIUM)
    
    def test_delete_user_soft(self):
        """Test soft delete user"""
        success, user, _ = user_manager.create_user(
            username="deletetest",
            email="delete@example.com",
            password="TestPass123!"
        )
        
        # Soft delete
        success, error = user_manager.delete_user(user.user_id, soft_delete=True)
        
        self.assertTrue(success)
        
        # User should still exist but marked as deleted
        deleted_user = user_manager.get_user(user.user_id)
        self.assertIsNotNone(deleted_user)
        self.assertEqual(deleted_user.status, UserStatus.DELETED)
    
    def test_delete_user_hard(self):
        """Test hard delete user"""
        success, user, _ = user_manager.create_user(
            username="harddelete",
            email="harddelete@example.com",
            password="TestPass123!"
        )
        
        # Hard delete
        success, error = user_manager.delete_user(user.user_id, soft_delete=False)
        
        self.assertTrue(success)
        
        # User should not exist
        deleted_user = user_manager.get_user(user.user_id)
        self.assertIsNone(deleted_user)
    
    def test_change_password(self):
        """Test password change"""
        success, user, _ = user_manager.create_user(
            username="passtest",
            email="pass@example.com",
            password="OldPass123!"
        )
        
        # Change password
        success, error = user_manager.change_password(
            user.user_id,
            "OldPass123!",
            "NewPass123!"
        )
        
        self.assertTrue(success)
        
        # Verify new password works
        updated_user = user_manager.get_user(user.user_id)
        self.assertTrue(PasswordPolicy.verify_password("NewPass123!", updated_user.password_hash))
    
    def test_password_history(self):
        """Test password history prevents reuse"""
        success, user, _ = user_manager.create_user(
            username="historytest",
            email="history@example.com",
            password="FirstPass123!"
        )
        
        # Change password
        user_manager.change_password(user.user_id, "FirstPass123!", "SecondPass123!")
        
        # Try to reuse first password
        success, error = user_manager.change_password(
            user.user_id,
            "SecondPass123!",
            "FirstPass123!"
        )
        
        self.assertFalse(success)
        self.assertIn("recently", error.lower())


class TestAuthentication(unittest.TestCase):
    """Test authentication flows"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        auth_manager.init_app(self.app)
        user_manager.init_app(self.app)
        
        # Clear existing users except admin
        user_manager.users = {
            uid: user for uid, user in user_manager.users.items()
            if user.username == 'admin'
        }
        
        # Create test user
        user_manager.create_user(
            username="authtest",
            email="auth@example.com",
            password="TestPass123!",
            role=UserRole.USER
        )
        
        # Verify email
        user = user_manager.get_user_by_username("authtest")
        user_manager.verify_email(user.user_id)
    
    def test_successful_login(self):
        """Test successful login"""
        with self.app.test_request_context():
            success, result, error = auth_manager.login(
                username="authtest",
                password="TestPass123!"
            )
            
            self.assertTrue(success)
            self.assertIn('access_token', result)
            self.assertIn('refresh_token', result)
            self.assertIn('user', result)
    
    def test_failed_login_wrong_password(self):
        """Test failed login with wrong password"""
        with self.app.test_request_context():
            success, result, error = auth_manager.login(
                username="authtest",
                password="WrongPassword123!"
            )
            
            self.assertFalse(success)
            self.assertIn("invalid", error.lower())
    
    def test_failed_login_nonexistent_user(self):
        """Test failed login with nonexistent user"""
        with self.app.test_request_context():
            success, result, error = auth_manager.login(
                username="nonexistent",
                password="TestPass123!"
            )
            
            self.assertFalse(success)
            self.assertIn("invalid", error.lower())
    
    def test_account_lockout(self):
        """Test account lockout after failed attempts"""
        with self.app.test_request_context():
            # Make multiple failed login attempts
            for _ in range(PasswordPolicy.MAX_FAILED_ATTEMPTS):
                auth_manager.login("authtest", "WrongPassword")
            
            # Next attempt should be locked
            success, result, error = auth_manager.login(
                username="authtest",
                password="TestPass123!"
            )
            
            self.assertFalse(success)
            self.assertIn("locked", error.lower())
    
    def test_register(self):
        """Test user registration"""
        with self.app.test_request_context():
            success, result, error = auth_manager.register(
                username="newuser",
                email="newuser@example.com",
                password="NewPass123!"
            )
            
            self.assertTrue(success)
            self.assertIn('user', result)
            self.assertIn('verification_token', result)
    
    def test_email_verification(self):
        """Test email verification"""
        with self.app.test_request_context():
            # Register user
            success, result, _ = auth_manager.register(
                username="verifytest",
                email="verify@example.com",
                password="TestPass123!"
            )
            
            token = result['verification_token']
            
            # Verify email
            success, error = auth_manager.verify_email(token)
            
            self.assertTrue(success)
            
            # Check user is verified
            user = user_manager.get_user_by_username("verifytest")
            self.assertTrue(user.email_verified)
    
    def test_password_reset_flow(self):
        """Test password reset flow"""
        with self.app.test_request_context():
            # Request password reset
            success, reset_token, error = auth_manager.request_password_reset(
                "auth@example.com"
            )
            
            self.assertTrue(success)
            self.assertIsNotNone(reset_token)
            
            # Reset password
            success, error = auth_manager.reset_password(
                reset_token,
                "ResetPass123!"
            )
            
            self.assertTrue(success)
            
            # Verify new password works
            success, result, error = auth_manager.login(
                username="authtest",
                password="ResetPass123!"
            )
            
            self.assertTrue(success)


class TestAuthorization(unittest.TestCase):
    """Test role-based authorization"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        user_manager.init_app(self.app)
        
        # Clear existing users except admin
        user_manager.users = {
            uid: user for uid, user in user_manager.users.items()
            if user.username == 'admin'
        }
        
        # Create users with different roles
        for role in [UserRole.ADMIN, UserRole.MODERATOR, UserRole.USER, UserRole.GUEST]:
            user_manager.create_user(
                username=f"{role.value}_user",
                email=f"{role.value}@example.com",
                password="TestPass123!",
                role=role
            )
    
    def test_admin_permissions(self):
        """Test admin has all permissions"""
        admin = user_manager.get_user_by_username("admin_user")
        
        # Admin should have all permissions
        for permission in Permission:
            self.assertTrue(user_manager.has_permission(admin.user_id, permission))
    
    def test_user_permissions(self):
        """Test regular user permissions"""
        user = user_manager.get_user_by_username("user_user")
        
        # User should have read permissions
        self.assertTrue(user_manager.has_permission(user.user_id, Permission.USER_READ))
        self.assertTrue(user_manager.has_permission(user.user_id, Permission.CONTENT_READ))
        
        # User should not have admin permissions
        self.assertFalse(user_manager.has_permission(user.user_id, Permission.ADMIN_READ))
        self.assertFalse(user_manager.has_permission(user.user_id, Permission.USER_DELETE))
    
    def test_guest_permissions(self):
        """Test guest permissions"""
        guest = user_manager.get_user_by_username("guest_user")
        
        # Guest should only have content read permission
        self.assertTrue(user_manager.has_permission(guest.user_id, Permission.CONTENT_READ))
        
        # Guest should not have write permissions
        self.assertFalse(user_manager.has_permission(guest.user_id, Permission.CONTENT_WRITE))
        self.assertFalse(user_manager.has_permission(guest.user_id, Permission.USER_WRITE))


class TestProfileManagement(unittest.TestCase):
    """Test profile management"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['AVATAR_UPLOAD_FOLDER'] = '/tmp/avatars'
        self.app.config['COVER_UPLOAD_FOLDER'] = '/tmp/covers'
        
        profile_manager.init_app(self.app)
        user_manager.init_app(self.app)
        
        # Create test user
        success, self.user, _ = user_manager.create_user(
            username="profiletest",
            email="profile@example.com",
            password="TestPass123!"
        )
    
    def test_get_profile(self):
        """Test getting user profile"""
        profile = profile_manager.get_profile(self.user.user_id)
        
        self.assertIsNotNone(profile)
        self.assertEqual(profile.user_id, self.user.user_id)
    
    def test_update_profile(self):
        """Test updating profile"""
        success, profile, error = profile_manager.update_profile(
            self.user.user_id,
            {
                'display_name': 'Test User',
                'bio': 'This is a test bio',
                'location': 'Test City'
            }
        )
        
        self.assertTrue(success)
        self.assertEqual(profile.display_name, 'Test User')
        self.assertEqual(profile.bio, 'This is a test bio')
        self.assertEqual(profile.location, 'Test City')
    
    def test_get_preferences(self):
        """Test getting user preferences"""
        preferences = profile_manager.get_preferences(self.user.user_id)
        
        self.assertIsNotNone(preferences)
        self.assertIn('email', preferences.notifications)
        self.assertIn('profile_visibility', preferences.privacy)
    
    def test_update_preferences(self):
        """Test updating preferences"""
        success, preferences, error = profile_manager.update_preferences(
            self.user.user_id,
            {
                'theme': 'dark',
                'language': 'es',
                'notifications': {
                    'email': False,
                    'push': True
                }
            }
        )
        
        self.assertTrue(success)
        self.assertEqual(preferences.theme, 'dark')
        self.assertEqual(preferences.language, 'es')
        self.assertFalse(preferences.notifications['email'])
        self.assertTrue(preferences.notifications['push'])
    
    def test_get_statistics(self):
        """Test getting user statistics"""
        statistics = profile_manager.get_statistics(self.user.user_id)
        
        self.assertIsNotNone(statistics)
        self.assertEqual(statistics.user_id, self.user.user_id)
        self.assertEqual(statistics.total_predictions, 0)
    
    def test_update_statistics(self):
        """Test updating statistics"""
        profile_manager.update_statistics(
            self.user.user_id,
            {
                'total_predictions': 5,
                'total_uploads': 3,
                'food_prediction': 'Pizza'
            }
        )
        
        statistics = profile_manager.get_statistics(self.user.user_id)
        self.assertEqual(statistics.total_predictions, 5)
        self.assertEqual(statistics.total_uploads, 3)
        self.assertIn('Pizza', statistics.favorite_foods)


class TestUserAnalytics(unittest.TestCase):
    """Test user analytics"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        user_manager.init_app(self.app)
        
        # Create test user
        success, self.user, _ = user_manager.create_user(
            username="analyticstest",
            email="analytics@example.com",
            password="TestPass123!"
        )
    
    def test_user_analytics(self):
        """Test getting user analytics"""
        analytics = user_manager.get_user_analytics(self.user.user_id)
        
        self.assertIsNotNone(analytics)
        self.assertEqual(analytics['user_id'], self.user.user_id)
        self.assertIn('account_age_days', analytics)
        self.assertIn('total_activities', analytics)
    
    def test_system_analytics(self):
        """Test getting system analytics"""
        analytics = user_manager.get_system_analytics()
        
        self.assertIsNotNone(analytics)
        self.assertIn('total_users', analytics)
        self.assertIn('users_by_role', analytics)
        self.assertIn('users_by_status', analytics)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPasswordPolicy))
    suite.addTests(loader.loadTestsFromTestCase(TestUserManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestAuthentication))
    suite.addTests(loader.loadTestsFromTestCase(TestAuthorization))
    suite.addTests(loader.loadTestsFromTestCase(TestProfileManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestUserAnalytics))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
