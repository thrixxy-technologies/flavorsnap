"""
Comprehensive tests for FlavorSnap Configuration Management System
"""

import os
import sys
import unittest
import tempfile
import shutil
import yaml
import json
import time
import threading
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import (
    ConfigManager, ConfigValidator, ConfigSecurity, ConfigBackup,
    ConfigFileWatcher, ConfigVersion, get_config, get_config_value
)
from db_config import DatabaseConfig
from logger_config import LoggingConfig

class TestConfigValidator(unittest.TestCase):
    """Test configuration validation functionality"""
    
    def setUp(self):
        self.validator = ConfigValidator()
    
    def test_validate_app_config_valid(self):
        """Test validation of valid app configuration"""
        config = {
            'name': 'test-app',
            'version': '1.0.0',
            'debug': True,
            'host': 'localhost',
            'port': 5000,
            'secret_key': 'test-secret'
        }
        
        is_valid, errors = self.validator.validate_section('app', config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_app_config_missing_required(self):
        """Test validation with missing required fields"""
        config = {
            'name': 'test-app',
            'version': '1.0.0'
            # Missing debug, host, port
        }
        
        is_valid, errors = self.validator.validate_section('app', config)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('debug' in error for error in errors))
        self.assertTrue(any('host' in error for error in errors))
        self.assertTrue(any('port' in error for error in errors))
    
    def test_validate_app_config_invalid_port(self):
        """Test validation with invalid port number"""
        config = {
            'name': 'test-app',
            'version': '1.0.0',
            'debug': True,
            'host': 'localhost',
            'port': 70000,  # Invalid port
            'secret_key': 'test-secret'
        }
        
        is_valid, errors = self.validator.validate_section('app', config)
        self.assertFalse(is_valid)
        self.assertTrue(any('port' in error and 'between' in error for error in errors))
    
    def test_validate_database_config_valid(self):
        """Test validation of valid database configuration"""
        config = {
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'name': 'testdb',
            'user': 'testuser',
            'password': 'testpass',
            'pool_size': 10,
            'max_overflow': 20
        }
        
        is_valid, errors = self.validator.validate_section('database', config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_logging_config_valid(self):
        """Test validation of valid logging configuration"""
        config = {
            'level': 'INFO',
            'format': '%(asctime)s - %(message)s',
            'file': './logs/test.log',
            'max_bytes': 10485760,
            'backup_count': 5,
            'enable_console': True
        }
        
        is_valid, errors = self.validator.validate_section('logging', config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_logging_config_invalid_level(self):
        """Test validation with invalid log level"""
        config = {
            'level': 'INVALID_LEVEL',
            'format': '%(asctime)s - %(message)s'
        }
        
        is_valid, errors = self.validator.validate_section('logging', config)
        self.assertFalse(is_valid)
        self.assertTrue(any('level' in error for error in errors))

class TestConfigSecurity(unittest.TestCase):
    """Test configuration security functionality"""
    
    def setUp(self):
        # Generate a test encryption key
        from cryptography.fernet import Fernet
        self.test_key = Fernet.generate_key().decode()
        self.security = ConfigSecurity(self.test_key)
    
    def test_encrypt_decrypt_value(self):
        """Test value encryption and decryption"""
        original_value = "sensitive_password"
        
        encrypted = self.security.encrypt_value(original_value)
        self.assertNotEqual(encrypted, original_value)
        
        decrypted = self.security.decrypt_value(encrypted)
        self.assertEqual(decrypted, original_value)
    
    def test_encrypt_without_key(self):
        """Test encryption without key (should return plain text)"""
        security_no_key = ConfigSecurity(None)
        original_value = "plain_text"
        
        encrypted = security_no_key.encrypt_value(original_value)
        self.assertEqual(encrypted, original_value)
        
        decrypted = security_no_key.decrypt_value(encrypted)
        self.assertEqual(decrypted, original_value)
    
    def test_encrypt_sensitive_fields(self):
        """Test encryption of sensitive fields in configuration"""
        config = {
            'app': {
                'secret_key': 'app-secret'
            },
            'database': {
                'password': 'db-password',
                'host': 'localhost'
            }
        }
        
        sensitive_fields = ['app.secret_key', 'database.password']
        encrypted_config = self.security.encrypt_sensitive_fields(config, sensitive_fields)
        
        # Check that sensitive fields are encrypted
        self.assertNotEqual(encrypted_config['app']['secret_key'], 'app-secret')
        self.assertNotEqual(encrypted_config['database']['password'], 'db-password')
        
        # Check that non-sensitive fields are not encrypted
        self.assertEqual(encrypted_config['database']['host'], 'localhost')

class TestConfigBackup(unittest.TestCase):
    """Test configuration backup functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.backup = ConfigBackup(self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_create_backup(self):
        """Test creating a configuration backup"""
        config = {'app': {'name': 'test'}, 'database': {'host': 'localhost'}}
        description = "Test backup"
        
        backup_file = self.backup.create_backup(config, description)
        
        self.assertTrue(os.path.exists(backup_file))
        self.assertTrue(backup_file.endswith('.yaml'))
        
        # Verify backup content
        with open(backup_file, 'r') as f:
            backup_data = yaml.safe_load(f)
        
        self.assertEqual(backup_data['description'], description)
        self.assertEqual(backup_data['config'], config)
        self.assertIn('timestamp', backup_data)
    
    def test_list_backups(self):
        """Test listing available backups"""
        config = {'app': {'name': 'test'}}
        
        # Create multiple backups
        self.backup.create_backup(config, "Backup 1")
        time.sleep(0.1)  # Ensure different timestamps
        self.backup.create_backup(config, "Backup 2")
        
        backups = self.backup.list_backups()
        self.assertEqual(len(backups), 2)
        
        # Check that backups are sorted by timestamp (newest first)
        self.assertEqual(backups[0]['description'], "Backup 2")
        self.assertEqual(backups[1]['description'], "Backup 1")
    
    def test_restore_backup(self):
        """Test restoring configuration from backup"""
        original_config = {
            'app': {'name': 'test-app', 'version': '1.0.0'},
            'database': {'host': 'localhost', 'port': 5432}
        }
        
        backup_file = self.backup.create_backup(original_config, "Test backup")
        restored_config = self.backup.restore_backup(backup_file)
        
        self.assertEqual(restored_config, original_config)
    
    def test_cleanup_old_backups(self):
        """Test cleanup of old backup files"""
        config = {'app': {'name': 'test'}}
        
        # Create a backup
        self.backup.create_backup(config, "Test backup")
        
        # Mock an old timestamp by modifying file modification time
        backup_files = list(self.backup.backup_dir.glob("config_backup_*.yaml"))
        if backup_files:
            old_time = time.time() - (35 * 24 * 60 * 60)  # 35 days ago
            os.utime(backup_files[0], (old_time, old_time))
        
        # Clean up backups older than 30 days
        self.backup.cleanup_old_backups(days_to_keep=30)
        
        # Check that old backup was deleted
        remaining_backups = list(self.backup.backup_dir.glob("config_backup_*.yaml"))
        self.assertEqual(len(remaining_backups), 0)

class TestConfigManager(unittest.TestCase):
    """Test main configuration manager functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'config.yaml')
        
        # Create test configuration
        self.test_config = {
            'app': {
                'name': 'flavorsnap',
                'version': '1.0.0',
                'debug': True,
                'host': 'localhost',
                'port': 5000,
                'secret_key': 'test-secret'
            },
            'database': {
                'type': 'postgresql',
                'host': 'localhost',
                'port': 5432,
                'name': 'testdb',
                'user': 'testuser',
                'password': 'testpass'
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(message)s',
                'enable_console': True
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(self.test_config, f)
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'ENVIRONMENT': 'testing',
            'DB_HOST': 'test-host',
            'LOG_LEVEL': 'DEBUG'
        })
        self.env_patcher.start()
        
        self.config_manager = ConfigManager(self.config_file, 'testing')
    
    def tearDown(self):
        self.env_patcher.stop()
        self.config_manager.cleanup()
        shutil.rmtree(self.temp_dir)
    
    def test_load_config(self):
        """Test configuration loading"""
        self.assertIsNotNone(self.config_manager.config)
        self.assertEqual(self.config_manager.config['app']['name'], 'flavorsnap')
        self.assertEqual(self.config_manager.environment, 'testing')
    
    def test_get_config_value(self):
        """Test getting configuration values"""
        # Test existing value
        app_name = self.config_manager.get('app.name')
        self.assertEqual(app_name, 'flavorsnap')
        
        # Test nested value
        db_host = self.config_manager.get('database.host')
        self.assertEqual(db_host, 'test-host')  # Should be from env var
        
        # Test default value
        non_existent = self.config_manager.get('non.existent.key', 'default')
        self.assertEqual(non_existent, 'default')
    
    def test_get_config_section(self):
        """Test getting configuration sections"""
        app_section = self.config_manager.get_section('app')
        self.assertIn('name', app_section)
        self.assertIn('version', app_section)
        
        non_existent_section = self.config_manager.get_section('non_existent')
        self.assertEqual(non_existent_section, {})
    
    def test_environment_variable_substitution(self):
        """Test environment variable substitution"""
        # Test simple substitution
        db_host = self.config_manager.get('database.host')
        self.assertEqual(db_host, 'test-host')
        
        # Test substitution with default
        log_level = self.config_manager.get('logging.level')
        self.assertEqual(log_level, 'DEBUG')
    
    def test_environment_specific_config(self):
        """Test loading environment-specific configuration"""
        # Create environment-specific config
        env_config_file = os.path.join(self.temp_dir, 'config.testing.yaml')
        env_config = {
            'app': {
                'debug': False,
                'port': 8000
            },
            'logging': {
                'level': 'ERROR'
            }
        }
        
        with open(env_config_file, 'w') as f:
            yaml.dump(env_config, f)
        
        # Reload config to test environment override
        self.config_manager._load_config()
        
        # Check that environment overrides are applied
        self.assertFalse(self.config_manager.get('app.debug'))
        self.assertEqual(self.config_manager.get('app.port'), 8000)
        self.assertEqual(self.config_manager.get('logging.level'), 'ERROR')
        
        # Check that base config values are still present
        self.assertEqual(self.config_manager.get('app.name'), 'flavorsnap')
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Valid config should pass
        self.config_manager._load_config()  # Should not raise exception
        
        # Invalid config should fail
        invalid_config_file = os.path.join(self.temp_dir, 'invalid_config.yaml')
        invalid_config = {
            'app': {
                'name': 'test'
                # Missing required fields
            }
        }
        
        with open(invalid_config_file, 'w') as f:
            yaml.dump(invalid_config, f)
        
        with self.assertRaises(ValueError):
            ConfigManager(invalid_config_file, 'testing')
    
    def test_change_callbacks(self):
        """Test configuration change callbacks"""
        callback_called = threading.Event()
        callback_args = {}
        
        def test_callback(new_config, old_config):
            callback_args['new'] = new_config
            callback_args['old'] = old_config
            callback_called.set()
        
        self.config_manager.add_change_callback(test_callback)
        
        # Modify config file
        modified_config = self.test_config.copy()
        modified_config['app']['port'] = 6000
        
        with open(self.config_file, 'w') as f:
            yaml.dump(modified_config, f)
        
        # Reload config
        self.config_manager.reload_config()
        
        # Check that callback was called
        self.assertTrue(callback_called.wait(timeout=5))
        self.assertIn('new', callback_args)
        self.assertIn('old', callback_args)
    
    def test_version_history(self):
        """Test configuration versioning"""
        initial_versions = len(self.config_manager.get_version_history())
        
        # Modify config and reload
        modified_config = self.test_config.copy()
        modified_config['app']['port'] = 6000
        
        with open(self.config_file, 'w') as f:
            yaml.dump(modified_config, f)
        
        self.config_manager.reload_config()
        
        # Check that version was created
        versions = self.config_manager.get_version_history()
        self.assertEqual(len(versions), initial_versions + 1)
        
        # Check version metadata
        latest_version = versions[-1]
        self.assertIn('version', latest_version)
        self.assertIn('timestamp', latest_version)
        self.assertIn('checksum', latest_version)
        self.assertEqual(latest_version['environment'], 'testing')
    
    def test_monitoring_info(self):
        """Test configuration monitoring information"""
        monitoring_info = self.config_manager.get_monitoring_info()
        
        self.assertIn('environment', monitoring_info)
        self.assertIn('config_path', monitoring_info)
        self.assertIn('version_count', monitoring_info)
        self.assertIn('checksum', monitoring_info)
        self.assertIn('watcher_active', monitoring_info)
        self.assertIn('backup_count', monitoring_info)
        self.assertIn('validation_status', monitoring_info)
        
        self.assertEqual(monitoring_info['environment'], 'testing')
        self.assertTrue(monitoring_info['watcher_active'])
        self.assertEqual(monitoring_info['validation_status'], 'valid')

class TestDatabaseConfig(unittest.TestCase):
    """Test database configuration functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'db_config.yaml')
        
        db_config = {
            'database': {
                'type': 'postgresql',
                'host': 'localhost',
                'port': 5432,
                'name': 'testdb',
                'user': 'testuser',
                'password': 'testpass',
                'pool_size': 10,
                'max_overflow': 20,
                'pool_timeout': 30,
                'pool_recycle': 3600
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(db_config, f)
        
        self.db_config = DatabaseConfig(self.config_file)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_load_database_config(self):
        """Test loading database configuration"""
        self.assertIsNotNone(self.db_config.config)
        self.assertEqual(self.db_config.config['type'], 'postgresql')
        self.assertEqual(self.db_config.config['host'], 'localhost')
    
    def test_validate_database_config(self):
        """Test database configuration validation"""
        self.assertTrue(self.db_config.validate_config())
        
        # Test invalid config
        self.db_config.config = {'type': 'postgresql'}  # Missing required fields
        self.assertFalse(self.db_config.validate_config())
    
    def test_get_connection_string(self):
        """Test database connection string generation"""
        connection_string = self.db_config.get_connection_string()
        self.assertIn('postgresql://', connection_string)
        self.assertIn('testuser', connection_string)
        self.assertIn('testpass', connection_string)
        self.assertIn('localhost', connection_string)
        self.assertIn('5432', connection_string)
        self.assertIn('testdb', connection_string)
    
    def test_get_connection_info(self):
        """Test getting connection information"""
        info = self.db_config.get_connection_info()
        
        self.assertIn('type', info)
        self.assertIn('host', info)
        self.assertIn('port', info)
        self.assertIn('name', info)
        self.assertIn('user', info)
        self.assertNotIn('password', info)  # Password should be excluded
    
    @patch('psycopg2.connect')
    def test_test_connection(self, mock_connect):
        """Test database connection testing"""
        # Mock successful connection
        mock_connect.return_value.__enter__.return_value.cursor.return_value.execute.return_value = None
        
        self.assertTrue(self.db_config.test_connection())
        mock_connect.assert_called_once()
    
    def test_reload_config(self):
        """Test database configuration reload"""
        old_config = self.db_config.config.copy()
        
        # Modify config file
        new_config = {
            'database': {
                'type': 'postgresql',
                'host': 'new-host',
                'port': 5432,
                'name': 'testdb',
                'user': 'testuser',
                'password': 'testpass'
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(new_config, f)
        
        self.db_config.reload_config()
        
        # Check that config was reloaded
        self.assertEqual(self.db_config.config['host'], 'new-host')
        self.assertNotEqual(self.db_config.config['host'], old_config['host'])

class TestLoggingConfig(unittest.TestCase):
    """Test logging configuration functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'logging_config.yaml')
        
        logging_config = {
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': os.path.join(self.temp_dir, 'test.log'),
                'max_bytes': 1048576,
                'backup_count': 3,
                'enable_console': True
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(logging_config, f)
        
        self.logging_config = LoggingConfig(self.config_file)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_load_logging_config(self):
        """Test loading logging configuration"""
        self.assertIsNotNone(self.logging_config.config)
        self.assertEqual(self.logging_config.config['level'], 'INFO')
        self.assertTrue(self.logging_config.config['enable_console'])
    
    def test_validate_logging_config(self):
        """Test logging configuration validation"""
        self.assertTrue(self.logging_config.validate_config())
        
        # Test invalid log level
        self.logging_config.config['level'] = 'INVALID'
        self.assertFalse(self.logging_config.validate_config())
        
        # Reset to valid
        self.logging_config.config['level'] = 'INFO'
        self.assertTrue(self.logging_config.validate_config())
    
    def test_get_logger(self):
        """Test getting logger instance"""
        logger = self.logging_config.get_logger('test_logger')
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, 'test_logger')
    
    def test_set_level(self):
        """Test changing log level"""
        logger = self.logging_config.get_logger('test_logger')
        
        # Change to DEBUG level
        self.logging_config.set_level('DEBUG', 'test_logger')
        self.assertEqual(logger.level, 10)  # DEBUG level value
        
        # Test invalid level
        with self.assertRaises(ValueError):
            self.logging_config.set_level('INVALID_LEVEL')
    
    def test_get_log_stats(self):
        """Test getting logging statistics"""
        stats = self.logging_config.get_log_stats()
        
        self.assertIn('config', stats)
        self.assertIn('loggers', stats)
        self.assertIn('level', stats['config'])
        self.assertIn('enable_console', stats['config'])
    
    def test_structured_logging(self):
        """Test structured JSON logging setup"""
        self.logging_config.setup_structured_logging('test_structured')
        
        logger = self.logging_config.get_logger('test_structured')
        self.assertIsNotNone(logger)
        
        # Test that handlers were added
        self.assertGreater(len(logger.handlers), 0)

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete configuration system"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'integration_config.yaml')
        
        # Create comprehensive test configuration
        self.full_config = {
            'app': {
                'name': 'flavorsnap-test',
                'version': '1.0.0',
                'debug': False,
                'host': '0.0.0.0',
                'port': 5000,
                'secret_key': 'integration-test-secret'
            },
            'database': {
                'type': 'postgresql',
                'host': '${DB_HOST:localhost}',
                'port': '${DB_PORT:5432}',
                'name': '${DB_NAME:flavorsnap_test}',
                'user': '${DB_USER:testuser}',
                'password': '${DB_PASSWORD:testpass}',
                'pool_size': 5,
                'max_overflow': 10
            },
            'logging': {
                'level': '${LOG_LEVEL:INFO}',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': f'{self.temp_dir}/test.log',
                'max_bytes': 1048576,
                'backup_count': 3,
                'enable_console': False
            },
            'security': {
                'jwt_secret_key': '${JWT_SECRET:jwt-test-secret}',
                'jwt_expiration_hours': 24,
                'bcrypt_rounds': 12
            },
            'features': {
                'enable_hot_reload': True,
                'enable_config_validation': True,
                'enable_backup': True,
                'enable_versioning': True
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(self.full_config, f)
        
        # Set up environment
        self.env_patcher = patch.dict(os.environ, {
            'ENVIRONMENT': 'test',
            'DB_HOST': 'test-db-host',
            'LOG_LEVEL': 'DEBUG',
            'CONFIG_ENCRYPTION_KEY': 'test-encryption-key-for-testing-only'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        self.env_patcher.stop()
        shutil.rmtree(self.temp_dir)
    
    def test_full_config_integration(self):
        """Test complete configuration system integration"""
        # Initialize all components
        config_manager = ConfigManager(self.config_file, 'test')
        db_config = DatabaseConfig(self.config_file)
        logging_config = LoggingConfig(self.config_file)
        
        try:
            # Test configuration loading
            self.assertIsNotNone(config_manager.config)
            self.assertEqual(config_manager.get('app.name'), 'flavorsnap-test')
            self.assertEqual(config_manager.get('database.host'), 'test-db-host')
            self.assertEqual(config_manager.get('logging.level'), 'DEBUG')
            
            # Test validation
            is_valid, errors = config_manager.validator.validate_all(config_manager.config)
            self.assertTrue(is_valid, f"Validation failed: {errors}")
            
            # Test database configuration
            self.assertTrue(db_config.validate_config())
            connection_string = db_config.get_connection_string()
            self.assertIn('test-db-host', connection_string)
            
            # Test logging configuration
            self.assertTrue(logging_config.validate_config())
            logger = logging_config.get_logger('integration_test')
            self.assertIsNotNone(logger)
            
            # Test security features
            sensitive_fields = ['app.secret_key', 'database.password', 'security.jwt_secret_key']
            encrypted_config = config_manager.security.encrypt_sensitive_fields(
                config_manager.config, sensitive_fields
            )
            
            # Verify sensitive fields are encrypted
            self.assertNotEqual(
                encrypted_config['app']['secret_key'],
                config_manager.config['app']['secret_key']
            )
            
            # Test backup functionality
            backup_file = config_manager.backup.create_backup(
                config_manager.config, "Integration test backup"
            )
            self.assertTrue(os.path.exists(backup_file))
            
            # Test versioning
            initial_versions = len(config_manager.get_version_history())
            
            # Modify config and reload
            modified_config = self.full_config.copy()
            modified_config['app']['port'] = 6000
            
            with open(self.config_file, 'w') as f:
                yaml.dump(modified_config, f)
            
            config_manager.reload_config()
            
            # Check version was created
            versions = config_manager.get_version_history()
            self.assertEqual(len(versions), initial_versions + 1)
            
            # Test monitoring
            monitoring_info = config_manager.get_monitoring_info()
            self.assertEqual(monitoring_info['environment'], 'test')
            self.assertTrue(monitoring_info['watcher_active'])
            self.assertEqual(monitoring_info['validation_status'], 'valid')
            
        finally:
            config_manager.cleanup()
    
    def test_hot_reload_integration(self):
        """Test hot reload functionality integration"""
        config_manager = ConfigManager(self.config_file, 'test')
        
        try:
            callback_called = threading.Event()
            
            def reload_callback(new_config, old_config):
                callback_called.set()
            
            config_manager.add_change_callback(reload_callback)
            
            # Modify configuration file
            modified_config = self.full_config.copy()
            modified_config['app']['port'] = 7000
            
            with open(self.config_file, 'w') as f:
                yaml.dump(modified_config, f)
            
            # Wait for hot reload (with timeout)
            self.assertTrue(callback_called.wait(timeout=10))
            
            # Verify configuration was updated
            self.assertEqual(config_manager.get('app.port'), 7000)
            
        finally:
            config_manager.cleanup()

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestConfigValidator,
        TestConfigSecurity,
        TestConfigBackup,
        TestConfigManager,
        TestDatabaseConfig,
        TestLoggingConfig,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
