"""
Test suite for Advanced Response Caching and File Storage features
"""

import unittest
import asyncio
import tempfile
import os
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Import the modules we're testing
from cache_manager import CacheManager, CacheEntry, CacheStrategy
from storage_handlers import StorageHandler, StorageConfig, StorageProvider, StorageTier
from cdn_integration import CDNManager, CDNConfig, CDNProvider
from model_inference import ModelInference, InferenceRequest, InferenceMode
import monitoring

class TestAdvancedCaching(unittest.TestCase):
    """Test advanced response caching features"""
    
    def setUp(self):
        """Set up test cache manager"""
        self.cache_manager = CacheManager()
    
    def test_cache_entry_creation(self):
        """Test cache entry creation"""
        entry = CacheEntry(
            key="test_key",
            value={"data": "test"},
            etag="test_etag",
            content_type="application/json",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            access_count=0,
            last_accessed=datetime.now(),
            size_bytes=100,
            compressed=False,
            tags=["test"],
            metadata={}
        )
        
        self.assertEqual(entry.key, "test_key")
        self.assertEqual(entry.etag, "test_etag")
        self.assertEqual(entry.content_type, "application/json")
    
    def test_cache_set_and_get(self):
        """Test cache set and get operations"""
        # Test setting cache
        success = self.cache_manager.set(
            key="test_key",
            value={"data": "test_value"},
            content_type="application/json",
            ttl=timedelta(minutes=30)
        )
        self.assertTrue(success)
        
        # Test getting cache
        entry = self.cache_manager.get("test_key")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.value["data"], "test_value")
    
    def test_etag_generation(self):
        """Test ETag generation"""
        test_data = b"test data for etag"
        etag = self.cache_manager._generate_etag(test_data)
        
        self.assertTrue(etag.startswith('"'))
        self.assertTrue(etag.endswith('"'))
        self.assertEqual(len(etag), 34)  # 32 chars + quotes
    
    def test_cache_invalidation_by_tags(self):
        """Test cache invalidation by tags"""
        # Set cache entries with different tags
        self.cache_manager.set("key1", {"data": "value1"}, tags=["tag1", "common"])
        self.cache_manager.set("key2", {"data": "value2"}, tags=["tag2", "common"])
        self.cache_manager.set("key3", {"data": "value3"}, tags=["tag3"])
        
        # Invalidate by tag
        invalidated = self.cache_manager.invalidate_by_tags(["common"])
        
        # Check that entries with common tag are invalidated
        self.assertIsNone(self.cache_manager.get("key1"))
        self.assertIsNone(self.cache_manager.get("key2"))
        self.assertIsNotNone(self.cache_manager.get("key3"))
    
    def test_cache_compression(self):
        """Test cache compression"""
        large_data = "x" * 2000  # Data larger than compression threshold
        
        success = self.cache_manager.set(
            key="large_key",
            value=large_data,
            content_type="text/plain"
        )
        
        self.assertTrue(success)
        entry = self.cache_manager.get("large_key")
        self.assertIsNotNone(entry)
        self.assertTrue(entry.compressed)
    
    def test_cache_stats(self):
        """Test cache statistics"""
        # Perform some cache operations
        self.cache_manager.set("key1", {"data": "value1"})
        self.cache_manager.get("key1")  # Hit
        self.cache_manager.get("nonexistent")  # Miss
        
        stats = self.cache_manager.get_cache_stats()
        
        self.assertEqual(stats.hits, 1)
        self.assertEqual(stats.misses, 1)
        self.assertEqual(stats.sets, 1)
        self.assertGreater(stats.hit_rate, 0)

class TestAdvancedStorage(unittest.TestCase):
    """Test advanced file storage features"""
    
    def setUp(self):
        """Set up test storage handler"""
        self.config = StorageConfig(
            provider=StorageProvider.LOCAL,
            bucket_name=tempfile.mkdtemp(),
            region="us-east-1"
        )
        self.storage_handler = StorageHandler(self.config)
    
    def tearDown(self):
        """Clean up test storage"""
        import shutil
        shutil.rmtree(self.config.bucket_name, ignore_errors=True)
    
    def test_storage_config_creation(self):
        """Test storage configuration"""
        self.assertEqual(self.config.provider, StorageProvider.LOCAL)
        self.assertEqual(self.config.region, "us-east-1")
        self.assertTrue(self.config.encryption_enabled)
        self.assertTrue(self.config.compression_enabled)
    
    def test_file_upload_and_download(self):
        """Test file upload and download"""
        test_data = b"test file content"
        filename = "test_file.txt"
        
        # Upload file
        async def test_upload():
            metadata = asyncio.run(self.storage_handler.upload_file(
                file_data=test_data,
                filename=filename,
                content_type="text/plain"
            ))
            
            self.assertIsNotNone(metadata)
            self.assertEqual(metadata.filename, filename)
            self.assertEqual(metadata.content_type, "text/plain")
            self.assertEqual(metadata.size_bytes, len(test_data))
            
            # Download file
            downloaded_data, downloaded_metadata = asyncio.run(
                self.storage_handler.download_file(metadata.hash_md5 + ".txt")
            )
            
            self.assertEqual(downloaded_data, test_data)
            self.assertEqual(downloaded_metadata.filename, filename)
            
            return metadata
        
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            metadata = loop.run_until_complete(test_upload())
        finally:
            loop.close()
    
    def test_storage_tier_mapping(self):
        """Test storage tier mapping"""
        # Test tier to storage class mapping
        storage_class = self.storage_handler._map_tier_to_storage_class(StorageTier.STANDARD)
        self.assertEqual(storage_class, 'STANDARD')
        
        storage_class = self.storage_handler._map_tier_to_storage_class(StorageTier.ARCHIVE)
        self.assertEqual(storage_class, 'GLACIER')
        
        # Test storage class to tier mapping
        tier = self.storage_handler._map_storage_class_to_tier('STANDARD_IA')
        self.assertEqual(tier, StorageTier.INFREQUENT_ACCESS)
    
    def test_object_key_generation(self):
        """Test object key generation"""
        filename = "test_image.jpg"
        file_hash = "abcd1234567890"
        
        object_key = self.storage_handler._generate_object_key(filename, file_hash)
        
        # Should include date prefix and hash
        self.assertIn(datetime.now().strftime('%Y/%m/%d'), object_key)
        self.assertIn(file_hash, object_key)
        self.assertTrue(object_key.endswith('.jpg'))
    
    def test_storage_stats(self):
        """Test storage statistics"""
        async def test_stats():
            stats = await self.storage_handler.get_storage_stats()
            
            self.assertIsInstance(stats.total_files, int)
            self.assertIsInstance(stats.total_size_bytes, int)
            self.assertIsInstance(stats.upload_count, int)
            self.assertIsInstance(stats.download_count, int)
            
            return stats
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            stats = loop.run_until_complete(test_stats())
        finally:
            loop.close()

class TestCDNIntegration(unittest.TestCase):
    """Test CDN integration features"""
    
    def setUp(self):
        """Set up test CDN manager"""
        self.config = CDNConfig(
            provider=CDNProvider.CLOUDFLARE,
            domain="test.cdn.com",
            zone_id="test_zone",
            api_token="test_token"
        )
        self.cdn_manager = CDNManager(self.config)
    
    def test_cdn_config_creation(self):
        """Test CDN configuration"""
        self.assertEqual(self.config.provider, CDNProvider.CLOUDFLARE)
        self.assertEqual(self.config.domain, "test.cdn.com")
        self.assertTrue(self.config.compression_enabled)
        self.assertTrue(self.config.image_optimization)
    
    def test_cache_rule_creation(self):
        """Test cache rule creation"""
        from cdn_integration import CacheRule
        
        rule = CacheRule(
            pattern="*.jpg",
            ttl=86400,
            browser_ttl=3600,
            edge_ttl=86400,
            cache_key="url",
            respect_query_params=True
        )
        
        self.assertEqual(rule.pattern, "*.jpg")
        self.assertEqual(rule.ttl, 86400)
        self.assertTrue(rule.respect_query_params)
    
    def test_image_optimization(self):
        """Test image optimization recommendations"""
        async def test_optimization():
            optimization = await self.cdn_manager.optimize_image_delivery(
                image_url="https://example.com/image.jpg",
                device_type="mobile"
            )
            
            self.assertIn('original_url', optimization)
            self.assertIn('optimized_url', optimization)
            self.assertIn('device_type', optimization)
            self.assertIn('config', optimization)
            
            return optimization
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            optimization = loop.run_until_complete(test_optimization())
        finally:
            loop.close()
    
    def test_bandwidth_savings_estimation(self):
        """Test bandwidth savings estimation"""
        config = {
            'max_width': 750,
            'quality': 75,
            'format': 'webp'
        }
        
        savings = self.cdn_manager._estimate_bandwidth_savings(config)
        
        self.assertIsInstance(savings, float)
        self.assertGreaterEqual(savings, 0)
        self.assertLessEqual(savings, 100)

class TestModelInference(unittest.TestCase):
    """Test model inference with caching"""
    
    def setUp(self):
        """Set up test model inference"""
        # Mock model loading
        with patch('torch.load') as mock_load:
            mock_model = Mock()
            mock_model.eval.return_value = None
            mock_model.to.return_value = None
            mock_load.return_value = mock_model
            
            self.model_inference = ModelInference()
    
    def test_inference_request_creation(self):
        """Test inference request creation"""
        from model_inference import create_inference_request
        
        request = create_inference_request(
            image_data=b"test_image_data",
            user_id="test_user",
            mode=InferenceMode.SINGLE
        )
        
        self.assertIsInstance(request, InferenceRequest)
        self.assertEqual(request.user_id, "test_user")
        self.assertEqual(request.mode, InferenceMode.SINGLE)
        self.assertIsNotNone(request.request_id)
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        request = InferenceRequest(
            request_id="test_req",
            image_data=b"test_image_data",
            model_version="1.0.0",
            mode=InferenceMode.SINGLE,
            timestamp=datetime.now()
        )
        
        cache_key = self.model_inference._generate_cache_key(request)
        
        self.assertIsInstance(cache_key, str)
        self.assertEqual(len(cache_key), 64)  # SHA256 hash length
    
    def test_metrics_update(self):
        """Test metrics update"""
        from model_inference import InferenceResult, ModelMetrics
        
        result = InferenceResult(
            request_id="test_req",
            predictions=[],
            confidence_scores=[],
            processing_time=0.5,
            model_version="1.0.0",
            cache_hit=False,
            timestamp=datetime.now()
        )
        
        initial_inferences = self.model_inference.metrics.total_inferences
        self.model_inference._update_metrics(result, False)
        
        self.assertEqual(
            self.model_inference.metrics.total_inferences,
            initial_inferences + 1
        )
    
    def test_model_status(self):
        """Test model status"""
        status = self.model_inference.get_status()
        
        self.assertIn('status', status)
        self.assertIn('model_version', status)
        self.assertIn('device', status)
        self.assertIn('classes_count', status)
        self.assertIn('cache_size', status)
        self.assertIn('metrics', status)

class TestMonitoringIntegration(unittest.TestCase):
    """Test monitoring integration with new features"""
    
    def test_storage_metrics_tracking(self):
        """Test storage metrics tracking"""
        # Test storage operation tracking
        monitoring.infrastructure_monitor.track_storage_operation(
            operation="upload",
            status="success",
            size_bytes=1024
        )
        
        # Test storage cost update
        monitoring.infrastructure_monitor.update_storage_cost(25.50)
        
        # These should not raise exceptions
        self.assertTrue(True)
    
    def test_cdn_metrics_tracking(self):
        """Test CDN metrics tracking"""
        # Test CDN request tracking
        monitoring.infrastructure_monitor.track_cdn_request(
            status="200",
            cache_hit=True,
            bandwidth_saved=512
        )
        
        # Test CDN cost savings update
        monitoring.infrastructure_monitor.update_cdn_cost_savings(15.75)
        
        # These should not raise exceptions
        self.assertTrue(True)

def run_integration_tests():
    """Run all integration tests"""
    print("Running Advanced Features Integration Tests...")
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestAdvancedCaching,
        TestAdvancedStorage,
        TestCDNIntegration,
        TestModelInference,
        TestMonitoringIntegration
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
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)
