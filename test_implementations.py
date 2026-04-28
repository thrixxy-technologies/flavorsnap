#!/usr/bin/env python3
"""
Test script for all implemented features
Tests backup/recovery, network optimization, NFT integration, and federated learning
"""

import sys
import os
import unittest
import tempfile
import shutil
from unittest.mock import Mock, patch
import numpy as np

# Add ml-model-api to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'ml-model-api'))

class TestBackupRecovery(unittest.TestCase):
    """Test backup and recovery systems"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Import here to avoid path issues
        from backup_manager import BackupManager, BackupConfig
        from recovery_system import RecoverySystem, RecoveryConfig
        
        self.backup_config = BackupConfig(
            backup_path=self.temp_dir,
            storage_type='local',
            compression=True
        )
        
        self.recovery_config = RecoveryConfig(
            recovery_path=self.temp_dir,
            temp_path=os.path.join(self.temp_dir, 'temp')
        )
        
        self.backup_manager = BackupManager(self.backup_config)
        self.recovery_system = RecoverySystem(self.recovery_config)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_backup_manager_initialization(self):
        """Test backup manager initialization"""
        self.assertIsNotNone(self.backup_manager)
        self.assertEqual(self.backup_manager.config.backup_path, self.temp_dir)
    
    def test_create_full_backup(self):
        """Test creating a full backup"""
        # Create test files
        test_file = os.path.join(self.temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # Create backup
        metadata = self.backup_manager.create_full_backup()
        
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.backup_type, 'full')
        self.assertEqual(metadata.status, 'created')
    
    def test_recovery_system_initialization(self):
        """Test recovery system initialization"""
        self.assertIsNotNone(self.recovery_system)
        self.assertEqual(self.recovery_system.config.recovery_path, self.temp_dir)

class TestNetworkOptimization(unittest.TestCase):
    """Test network optimization systems"""
    
    def setUp(self):
        """Set up test environment"""
        from network_optimizer import NetworkOptimizer, NetworkConfig
        from connection_pool import AdvancedConnectionPool, ConnectionConfig, PoolConfig
        from compression_handler import CompressionHandler, CompressionConfig
        
        self.network_config = NetworkConfig(
            enable_connection_pooling=True,
            enable_compression=True,
            enable_protocol_optimization=True
        )
        
        self.connection_config = ConnectionConfig(
            host="httpbin.org",
            port=443,
            protocol="https"
        )
        
        self.pool_config = PoolConfig(
            min_size=2,
            max_size=5
        )
        
        self.compression_config = CompressionConfig(
            enable_adaptive_selection=True,
            enable_caching=True
        )
        
        self.network_optimizer = NetworkOptimizer(self.network_config)
        self.connection_pool = AdvancedConnectionPool(self.connection_config, self.pool_config)
        self.compression_handler = CompressionHandler(self.compression_config)
    
    def test_network_optimizer_initialization(self):
        """Test network optimizer initialization"""
        self.assertIsNotNone(self.network_optimizer)
        self.assertTrue(self.network_optimizer.config.enable_connection_pooling)
    
    def test_compression_handler(self):
        """Test compression handler"""
        test_data = b"test data for compression" * 100
        
        # Test compression
        compressed = self.compression_handler.compress(test_data)
        self.assertIsInstance(compressed, bytes)
        
        # Test decompression
        from compression_handler import CompressionAlgorithm
        decompressed = self.compression_handler.decompress(compressed, CompressionAlgorithm.GZIP)
        self.assertEqual(decompressed, test_data)
    
    def test_connection_pool_metrics(self):
        """Test connection pool metrics"""
        metrics = self.connection_pool.get_pool_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertIn('total_connections', metrics)

class TestNFTIntegration(unittest.TestCase):
    """Test NFT integration systems"""
    
    def setUp(self):
        """Set up test environment"""
        from nft_handlers import NFTHandler, NFTConfig, NFTMetadata, NFTType
        
        self.nft_config = NFTConfig(
            blockchain_network="polygon",
            enable_metadata_validation=True,
            enable_image_optimization=True
        )
        
        self.nft_handler = NFTHandler(self.nft_config)
        
        # Test metadata
        self.test_metadata = NFTMetadata(
            name="Test Food Item",
            description="A test food item for testing",
            food_type="pizza",
            ingredients=["flour", "tomato", "cheese"],
            rarity="common"
        )
    
    def test_nft_handler_initialization(self):
        """Test NFT handler initialization"""
        self.assertIsNotNone(self.nft_handler)
        self.assertEqual(self.nft_handler.config.blockchain_network, "polygon")
    
    def test_metadata_validation(self):
        """Test metadata validation"""
        # Valid metadata should pass
        self.nft_handler._validate_metadata(self.test_metadata)
        
        # Invalid metadata should fail
        invalid_metadata = NFTMetadata(
            name="",  # Empty name
            description="Invalid metadata"
        )
        with self.assertRaises(ValueError):
            self.nft_handler._validate_metadata(invalid_metadata)
    
    def test_image_optimization(self):
        """Test image optimization"""
        # Create test image data (simplified)
        test_image_data = b"fake_image_data" * 1000
        
        # Test optimization (will return original data for fake data)
        optimized = self.nft_handler._optimize_image(test_image_data)
        self.assertIsInstance(optimized, bytes)

class TestFederatedLearning(unittest.TestCase):
    """Test federated learning systems"""
    
    def setUp(self):
        """Set up test environment"""
        from federated_training import FederatedLearningCoordinator, FederatedConfig, PrivacyLevel
        from model_validation import ModelValidator, ValidationConfig, ValidationType
        
        self.federated_config = FederatedConfig(
            min_participants=2,
            max_participants=5,
            enable_differential_privacy=True,
            privacy_level=PrivacyLevel.STANDARD
        )
        
        self.validation_config = ValidationConfig(
            enable_blockchain_validation=False,  # Disabled for testing
            accuracy_threshold=0.7
        )
        
        self.federated_coordinator = FederatedLearningCoordinator(self.federated_config)
        self.model_validator = ModelValidator(self.validation_config)
    
    def test_federated_coordinator_initialization(self):
        """Test federated coordinator initialization"""
        self.assertIsNotNone(self.federated_coordinator)
        self.assertEqual(self.federated_coordinator.config.min_participants, 2)
    
    def test_participant_registration(self):
        """Test participant registration"""
        success = self.federated_coordinator.register_participant(
            "test_participant",
            "0x1234567890123456789012345678901234567890",
            1000,
            100.0
        )
        self.assertTrue(success)
        self.assertIn("test_participant", self.federated_coordinator.participants)
    
    def test_model_validation_initialization(self):
        """Test model validator initialization"""
        self.assertIsNotNone(self.model_validator)
        self.assertEqual(self.model_validator.config.accuracy_threshold, 0.7)
    
    def test_model_hash_calculation(self):
        """Test model hash calculation"""
        # Create test model weights
        test_weights = {
            'layer1.weight': np.random.randn(10, 5),
            'layer1.bias': np.random.randn(10)
        }
        
        # Calculate hash
        hash_value = self.model_validator._calculate_model_hash(test_weights)
        self.assertIsInstance(hash_value, str)
        self.assertEqual(len(hash_value), 64)  # SHA256 hex length

class TestIntegration(unittest.TestCase):
    """Test integration between systems"""
    
    def test_monitoring_integration(self):
        """Test monitoring system integration"""
        # Import monitoring components
        from monitoring import backup_monitoring_system
        
        # Test that monitoring system can record metrics
        backup_monitoring_system.record_backup_operation(
            "test_backup",
            "full",
            60.0,
            1024,
            "created"
        )
        
        # Get metrics
        metrics = backup_monitoring_system.get_backup_metrics_summary()
        self.assertIsInstance(metrics, dict)
    
    def test_config_compatibility(self):
        """Test configuration compatibility across systems"""
        # Test that all configs can be instantiated
        from backup_manager import BackupConfig
        from network_optimizer import NetworkConfig
        from nft_handlers import NFTConfig
        from federated_training import FederatedConfig
        
        # Create configs
        backup_config = BackupConfig()
        network_config = NetworkConfig()
        nft_config = NFTConfig()
        federated_config = FederatedConfig()
        
        # All should be instantiable
        self.assertIsNotNone(backup_config)
        self.assertIsNotNone(network_config)
        self.assertIsNotNone(nft_config)
        self.assertIsNotNone(federated_config)

def run_tests():
    """Run all tests"""
    print("Running implementation tests...")
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestBackupRecovery,
        TestNetworkOptimization,
        TestNFTIntegration,
        TestFederatedLearning,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\nTest Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
