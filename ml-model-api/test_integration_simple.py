"""
Simple Integration Test to Verify User Management System Works
This tests basic functionality without requiring a full Flask app
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    try:
        from user_handlers import user_manager, UserRole, UserStatus, PasswordPolicy
        print("✓ user_handlers imported successfully")
        
        from auth_handlers import auth_manager, SessionConfig
        print("✓ auth_handlers imported successfully")
        
        from profile_handlers import profile_manager
        print("✓ profile_handlers imported successfully")
        
        from user_api_endpoints import register_user_management_routes
        print("✓ user_api_endpoints imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_password_policy():
    """Test password policy validation"""
    print("\nTesting password policy...")
    try:
        from user_handlers import PasswordPolicy
        
        # Test weak password
        is_valid, error = PasswordPolicy.validate_password("weak")
        assert not is_valid, "Weak password should fail"
        print("✓ Weak password rejected")
        
        # Test strong password
        is_valid, error = PasswordPolicy.validate_password("StrongPass123!")
        assert is_valid, f"Strong password should pass: {error}"
        print("✓ Strong password accepted")
        
        # Test password hashing
        password = "TestPassword123!"
        hash1 = PasswordPolicy.hash_password(password)
        hash2 = PasswordPolicy.hash_password(password)
        assert hash1 != hash2, "Hashes should be different (salt)"
        assert PasswordPolicy.verify_password(password, hash1), "Password verification failed"
        print("✓ Password hashing and verification works")
        
        return True
    except Exception as e:
        print(f"✗ Password policy test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_user_creation():
    """Test basic user creation"""
    print("\nTesting user creation...")
    try:
        from user_handlers import user_manager, UserRole
        from flask import Flask
        
        # Create minimal Flask app
        app = Flask(__name__)
        app.config['TESTING'] = True
        user_manager.init_app(app)
        
        # Clear test users
        user_manager.users = {
            uid: user for uid, user in user_manager.users.items()
            if user.username == 'admin'
        }
        
        # Create user
        success, user, error = user_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            role=UserRole.USER
        )
        
        assert success, f"User creation failed: {error}"
        assert user is not None, "User object is None"
        assert user.username == "testuser", "Username mismatch"
        print("✓ User created successfully")
        
        # Test duplicate username
        success, user, error = user_manager.create_user(
            username="testuser",
            email="test2@example.com",
            password="TestPass123!"
        )
        assert not success, "Duplicate username should fail"
        print("✓ Duplicate username rejected")
        
        return True
    except Exception as e:
        print(f"✗ User creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_authentication():
    """Test authentication flow"""
    print("\nTesting authentication...")
    try:
        from user_handlers import user_manager, UserRole
        from auth_handlers import auth_manager
        from flask import Flask
        
        # Create minimal Flask app
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        user_manager.init_app(app)
        auth_manager.init_app(app)
        
        # Clear test users
        user_manager.users = {
            uid: user for uid, user in user_manager.users.items()
            if user.username == 'admin'
        }
        
        # Create and verify user
        success, user, _ = user_manager.create_user(
            username="authtest",
            email="auth@example.com",
            password="TestPass123!"
        )
        user_manager.verify_email(user.user_id)
        
        # Test login with app context
        with app.test_request_context():
            success, result, error = auth_manager.login(
                username="authtest",
                password="TestPass123!"
            )
            
            assert success, f"Login failed: {error}"
            assert 'access_token' in result, "No access token in result"
            assert 'refresh_token' in result, "No refresh token in result"
            print("✓ Login successful")
            
            # Test wrong password
            success, result, error = auth_manager.login(
                username="authtest",
                password="WrongPassword"
            )
            assert not success, "Login with wrong password should fail"
            print("✓ Wrong password rejected")
        
        return True
    except Exception as e:
        print(f"✗ Authentication test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_profile_management():
    """Test profile management"""
    print("\nTesting profile management...")
    try:
        from user_handlers import user_manager
        from profile_handlers import profile_manager
        from flask import Flask
        
        # Create minimal Flask app
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['AVATAR_UPLOAD_FOLDER'] = '/tmp/avatars'
        app.config['COVER_UPLOAD_FOLDER'] = '/tmp/covers'
        
        user_manager.init_app(app)
        profile_manager.init_app(app)
        
        # Create user
        success, user, _ = user_manager.create_user(
            username="profiletest",
            email="profile@example.com",
            password="TestPass123!"
        )
        
        # Get profile
        profile = profile_manager.get_profile(user.user_id)
        assert profile is not None, "Profile is None"
        print("✓ Profile retrieved")
        
        # Update profile
        success, updated_profile, error = profile_manager.update_profile(
            user.user_id,
            {
                'display_name': 'Test User',
                'bio': 'Test bio',
                'location': 'Test City'
            }
        )
        assert success, f"Profile update failed: {error}"
        assert updated_profile.display_name == 'Test User', "Display name not updated"
        print("✓ Profile updated")
        
        # Get preferences
        preferences = profile_manager.get_preferences(user.user_id)
        assert preferences is not None, "Preferences is None"
        print("✓ Preferences retrieved")
        
        return True
    except Exception as e:
        print(f"✗ Profile management test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_permissions():
    """Test role-based permissions"""
    print("\nTesting permissions...")
    try:
        from user_handlers import user_manager, UserRole, Permission
        from flask import Flask
        
        # Create minimal Flask app
        app = Flask(__name__)
        app.config['TESTING'] = True
        user_manager.init_app(app)
        
        # Clear test users
        user_manager.users = {
            uid: user for uid, user in user_manager.users.items()
            if user.username == 'admin'
        }
        
        # Create users with different roles
        success, admin_user, _ = user_manager.create_user(
            username="admin_test",
            email="admin@example.com",
            password="TestPass123!",
            role=UserRole.ADMIN
        )
        
        success, regular_user, _ = user_manager.create_user(
            username="user_test",
            email="user@example.com",
            password="TestPass123!",
            role=UserRole.USER
        )
        
        # Test admin permissions
        assert user_manager.has_permission(admin_user.user_id, Permission.ADMIN_WRITE), \
            "Admin should have admin write permission"
        print("✓ Admin has admin permissions")
        
        # Test user permissions
        assert user_manager.has_permission(regular_user.user_id, Permission.CONTENT_READ), \
            "User should have content read permission"
        assert not user_manager.has_permission(regular_user.user_id, Permission.ADMIN_WRITE), \
            "User should not have admin write permission"
        print("✓ Regular user has correct permissions")
        
        return True
    except Exception as e:
        print(f"✗ Permissions test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all integration tests"""
    print("="*70)
    print("SIMPLE INTEGRATION TEST - USER MANAGEMENT SYSTEM")
    print("="*70)
    
    tests = [
        ("Import Test", test_imports),
        ("Password Policy Test", test_password_policy),
        ("User Creation Test", test_user_creation),
        ("Authentication Test", test_authentication),
        ("Profile Management Test", test_profile_management),
        ("Permissions Test", test_permissions),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("="*70)
    print(f"Results: {passed}/{total} tests passed")
    print("="*70)
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
