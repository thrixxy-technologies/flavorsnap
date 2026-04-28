"""
Comprehensive Input Validation Tests
Tests for security_config.py and image_optimizer.py modules
"""

import unittest
import tempfile
import os
import io
from unittest.mock import Mock, patch, MagicMock
from werkzeug.datastructures import FileStorage
import json

# Import modules to test
from security_config import InputValidator, ValidationLevel, ValidationResult, SecurityMiddleware
from image_optimizer import ImageOptimizer, ImageFormat, OptimizationResult

class TestInputValidator(unittest.TestCase):
    """Test cases for InputValidator class"""
    
    def setUp(self):
        self.validator = InputValidator(ValidationLevel.MODERATE)
    
    def test_text_validation_valid_input(self):
        """Test valid text input"""
        result = self.validator.validate_text_input("Hello, world!", "test_field")
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertIsInstance(result.sanitized_data, str)
        self.assertGreater(result.security_score, 0)
    
    def test_text_validation_xss_attempt(self):
        """Test XSS attempt detection"""
        malicious_input = "<script>alert('xss')</script>"
        result = self.validator.validate_text_input(malicious_input, "test_field")
        
        # Should be valid but with warnings
        self.assertTrue(result.is_valid)
        self.assertGreater(len(result.warnings), 0)
        self.assertNotIn('<script>', result.sanitized_data)
    
    def test_text_validation_sql_injection(self):
        """Test SQL injection attempt detection"""
        malicious_input = "'; DROP TABLE users; --"
        result = self.validator.validate_text_input(malicious_input, "test_field")
        
        # Should be valid but with warnings
        self.assertTrue(result.is_valid)
        self.assertGreater(len(result.warnings), 0)
    
    def test_text_validation_null_bytes(self):
        """Test null byte injection detection"""
        malicious_input = "Hello\x00World"
        result = self.validator.validate_text_input(malicious_input, "test_field")
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_text_validation_length_limit(self):
        """Test length limit enforcement"""
        long_input = "a" * 1001  # Exceeds default limit of 1000
        result = self.validator.validate_text_input(long_input, "test_field", max_length=1000)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_text_validation_non_string_input(self):
        """Test non-string input validation"""
        result = self.validator.validate_text_input(123, "test_field")
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_file_validation_valid_image(self):
        """Test valid image file validation"""
        # Create a mock image file
        image_data = b'\xff\xd8\xff\xe0\x00\x10JFIF'  # JPEG header
        file_mock = Mock(spec=FileStorage)
        file_mock.filename = "test.jpg"
        file_mock.content_type = "image/jpeg"
        file_mock.tell.return_value = len(image_data)
        file_mock.seek = Mock()
        file_mock.read.return_value = image_data
        
        with patch('magic.from_buffer', return_value='image/jpeg'):
            with patch('PIL.Image.open') as mock_image:
                mock_image_instance = Mock()
                mock_image_instance.size = (100, 100)
                mock_image_instance.format = 'JPEG'
                mock_image_instance.mode = 'RGB'
                mock_image_instance.verify.return_value = None
                mock_image.return_value = mock_image_instance
                
                result = self.validator.validate_file_upload(file_mock, "test_file")
                
                self.assertTrue(result.is_valid)
                self.assertEqual(len(result.errors), 0)
    
    def test_file_validation_invalid_extension(self):
        """Test invalid file extension"""
        file_mock = Mock(spec=FileStorage)
        file_mock.filename = "test.exe"
        file_mock.content_type = "application/octet-stream"
        file_mock.tell.return_value = 100
        file_mock.seek = Mock()
        
        result = self.validator.validate_file_upload(file_mock, "test_file")
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_file_validation_size_limit(self):
        """Test file size limit enforcement"""
        file_mock = Mock(spec=FileStorage)
        file_mock.filename = "test.jpg"
        file_mock.content_type = "image/jpeg"
        file_mock.tell.return_value = 15 * 1024 * 1024  # 15MB, exceeds limit
        file_mock.seek = Mock()
        
        result = self.validator.validate_file_upload(file_mock, "test_file")
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_file_validation_empty_file(self):
        """Test empty file validation"""
        file_mock = Mock(spec=FileStorage)
        file_mock.filename = "test.jpg"
        file_mock.content_type = "image/jpeg"
        file_mock.tell.return_value = 0  # Empty file
        file_mock.seek = Mock()
        
        result = self.validator.validate_file_upload(file_mock, "test_file")
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_json_validation_valid_input(self):
        """Test valid JSON input"""
        json_data = {"name": "test", "value": 123, "active": True}
        result = self.validator.validate_json_input(json_data)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertIsInstance(result.sanitized_data, dict)
    
    def test_json_validation_dangerous_keys(self):
        """Test dangerous key detection"""
        json_data = {"__proto__": "dangerous", "name": "test"}
        result = self.validator.validate_json_input(json_data)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_json_validation_depth_limit(self):
        """Test JSON depth limit"""
        # Create deeply nested JSON
        deep_json = {}
        current = deep_json
        for i in range(15):  # Exceeds max depth of 10
            current["level"] = {}
            current = current["level"]
        
        result = self.validator.validate_json_input(deep_json)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_json_validation_schema(self):
        """Test JSON schema validation"""
        json_data = {"name": "test", "age": 25}
        schema = {
            "type": "object",
            "required": ["name", "email"],
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "age": {"type": "number"}
            }
        }
        
        result = self.validator.validate_json_input(json_data, schema)
        
        self.assertFalse(result.is_valid)  # Missing required 'email' field
        self.assertGreater(len(result.errors), 0)

class TestImageOptimizer(unittest.TestCase):
    """Test cases for ImageOptimizer class"""
    
    def setUp(self):
        self.optimizer = ImageOptimizer()
    
    def test_image_info_extraction(self):
        """Test image information extraction"""
        # Create a simple test image
        from PIL import Image
        import io
        
        # Create a test image
        test_image = Image.new('RGB', (100, 100), color='red')
        image_data = io.BytesIO()
        test_image.save(image_data, format='JPEG')
        image_bytes = image_data.getvalue()
        
        with patch('magic.from_buffer', return_value='image/jpeg'):
            info = self.optimizer.get_image_info(image_bytes)
            
            self.assertNotIn('error', info)
            self.assertEqual(info['format'], 'JPEG')
            self.assertEqual(info['size'], (100, 100))
            self.assertEqual(info['mode'], 'RGB')
    
    def test_image_optimization(self):
        """Test image optimization"""
        from PIL import Image
        import io
        
        # Create a test image
        test_image = Image.new('RGB', (500, 500), color='blue')
        image_data = io.BytesIO()
        test_image.save(image_data, format='JPEG', quality=95)
        image_bytes = image_data.getvalue()
        
        with patch('magic.from_buffer', return_value='image/jpeg'):
            result = self.optimizer.optimize_image(image_bytes, output_format='JPEG')
            
            self.assertTrue(result.success)
            self.assertGreater(result.original_size, 0)
            self.assertGreater(result.optimized_size, 0)
            self.assertGreater(result.compression_ratio, 0)
    
    def test_thumbnail_creation(self):
        """Test thumbnail creation"""
        from PIL import Image
        import io
        
        # Create a test image
        test_image = Image.new('RGB', (500, 500), color='green')
        image_data = io.BytesIO()
        test_image.save(image_data, format='JPEG')
        image_bytes = image_data.getvalue()
        
        with patch('magic.from_buffer', return_value='image/jpeg'):
            thumbnail = self.optimizer.create_thumbnail(image_bytes, size=(50, 50))
            
            self.assertGreater(len(thumbnail), 0)
            
            # Verify thumbnail size
            thumb_image = Image.open(io.BytesIO(thumbnail))
            self.assertEqual(thumb_image.size, (50, 50))
    
    def test_optimization_presets(self):
        """Test different optimization presets"""
        from PIL import Image
        import io
        
        # Create a test image
        test_image = Image.new('RGB', (2000, 2000), color='purple')
        image_data = io.BytesIO()
        test_image.save(image_data, format='JPEG')
        image_bytes = image_data.getvalue()
        
        with patch('magic.from_buffer', return_value='image/jpeg'):
            # Test web preset
            result_web = self.optimizer.optimize_image(image_bytes, preset='web')
            self.assertTrue(result_web.success)
            
            # Test mobile preset
            result_mobile = self.optimizer.optimize_image(image_bytes, preset='mobile')
            self.assertTrue(result_mobile.success)
            
            # Test thumbnail preset
            result_thumb = self.optimizer.optimize_image(image_bytes, preset='thumbnail')
            self.assertTrue(result_thumb.success)
            
            # Mobile should be smaller than web
            self.assertLessEqual(result_mobile.optimized_size, result_web.optimized_size)
    
    def test_optimization_suggestions(self):
        """Test optimization suggestions"""
        from PIL import Image
        import io
        
        # Create a large test image
        test_image = Image.new('RGB', (3000, 3000), color='orange')
        image_data = io.BytesIO()
        test_image.save(image_data, format='JPEG', quality=100)
        image_bytes = image_data.getvalue()
        
        with patch('magic.from_buffer', return_value='image/jpeg'):
            suggestions = self.optimizer.get_optimization_suggestions(image_bytes)
            
            self.assertNotIn('error', suggestions)
            self.assertIn('image_info', suggestions)
            self.assertIn('suggestions', suggestions)
            self.assertIn('recommended_preset', suggestions)
    
    def test_batch_optimization(self):
        """Test batch image optimization"""
        from PIL import Image
        import io
        
        # Create multiple test images
        images = []
        for i in range(3):
            test_image = Image.new('RGB', (200, 200), color=(i*50, i*50, i*50))
            image_data = io.BytesIO()
            test_image.save(image_data, format='JPEG')
            images.append(image_data.getvalue())
        
        with patch('magic.from_buffer', return_value='image/jpeg'):
            results = self.optimizer.batch_optimize(images, output_format='JPEG')
            
            self.assertEqual(len(results), 3)
            for result in results:
                self.assertTrue(result.success)
                self.assertIn('batch_index', result.metadata)

class TestSecurityMiddleware(unittest.TestCase):
    """Test cases for SecurityMiddleware"""
    
    def setUp(self):
        self.validator = InputValidator(ValidationLevel.MODERATE)
        self.middleware = SecurityMiddleware(validator=self.validator)
    
    def test_middleware_initialization(self):
        """Test middleware initialization"""
        self.assertIsNotNone(self.middleware.validator)
        self.assertIsInstance(self.validator, InputValidator)
    
    def test_security_report_summary(self):
        """Test security report summary generation"""
        # Mock Flask app with validation reports
        mock_app = Mock()
        mock_app.validation_reports = {
            'req1': {
                'validations': {
                    'json': {'is_valid': True, 'security_score': 90},
                    'form': {'field1': {'is_valid': True, 'security_score': 85}}
                }
            },
            'req2': {
                'validations': {
                    'json': {'is_valid': False, 'security_score': 30},
                    'files': {'file1': {'is_valid': True, 'security_score': 95}}
                }
            }
        }
        
        from security_config import create_security_report_summary
        summary = create_security_report_summary(mock_app)
        
        self.assertEqual(summary['total_requests'], 2)
        self.assertEqual(summary['valid_requests'], 1)
        self.assertEqual(summary['invalid_requests'], 1)
        self.assertGreater(summary['average_security_score'], 0)

class TestValidationResult(unittest.TestCase):
    """Test cases for ValidationResult dataclass"""
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation"""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["test warning"],
            sanitized_data="clean data",
            security_score=95.0,
            metadata={"test": "value"}
        )
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(result.sanitized_data, "clean data")
        self.assertEqual(result.security_score, 95.0)
        self.assertEqual(result.metadata["test"], "value")

class TestOptimizationResult(unittest.TestCase):
    """Test cases for OptimizationResult dataclass"""
    
    def test_optimization_result_creation(self):
        """Test OptimizationResult creation"""
        result = OptimizationResult(
            success=True,
            original_size=1000,
            optimized_size=500,
            compression_ratio=0.5,
            format="JPEG",
            dimensions=(100, 100),
            processing_time=0.1,
            errors=[],
            warnings=["test warning"],
            metadata={"optimized": True}
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.original_size, 1000)
        self.assertEqual(result.optimized_size, 500)
        self.assertEqual(result.compression_ratio, 0.5)
        self.assertEqual(result.format, "JPEG")
        self.assertEqual(result.dimensions, (100, 100))
        self.assertEqual(result.processing_time, 0.1)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 1)

class TestIntegration(unittest.TestCase):
    """Integration tests for the validation system"""
    
    def test_end_to_end_validation(self):
        """Test end-to-end validation process"""
        validator = InputValidator(ValidationLevel.STRICT)
        
        # Test text validation
        text_result = validator.validate_text_input("Hello, world!", "message")
        self.assertTrue(text_result.is_valid)
        
        # Test JSON validation
        json_data = {"message": "Hello, world!", "timestamp": "2023-01-01"}
        json_result = validator.validate_json_input(json_data)
        self.assertTrue(json_result.is_valid)
        
        # Test file validation with mock
        from PIL import Image
        import io
        
        test_image = Image.new('RGB', (100, 100), color='red')
        image_data = io.BytesIO()
        test_image.save(image_data, format='JPEG')
        image_bytes = image_data.getvalue()
        
        file_mock = Mock(spec=FileStorage)
        file_mock.filename = "test.jpg"
        file_mock.content_type = "image/jpeg"
        file_mock.tell.return_value = len(image_bytes)
        file_mock.seek = Mock()
        file_mock.read.return_value = image_bytes
        
        with patch('magic.from_buffer', return_value='image/jpeg'):
            file_result = validator.validate_file_upload(file_mock, "image")
            self.assertTrue(file_result.is_valid)
    
    def test_image_processing_chain(self):
        """Test complete image processing chain"""
        from PIL import Image
        import io
        
        # Create test image
        test_image = Image.new('RGB', (1000, 1000), color='blue')
        image_data = io.BytesIO()
        test_image.save(image_data, format='JPEG', quality=95)
        image_bytes = image_data.getvalue()
        
        optimizer = ImageOptimizer()
        
        # Test info extraction
        with patch('magic.from_buffer', return_value='image/jpeg'):
            info = optimizer.get_image_info(image_bytes)
            self.assertNotIn('error', info)
            
            # Test optimization
            result = optimizer.optimize_image(image_bytes)
            self.assertTrue(result.success)
            
            # Test thumbnail creation
            thumbnail = optimizer.create_thumbnail(image_bytes)
            self.assertGreater(len(thumbnail), 0)
            
            # Test suggestions
            suggestions = optimizer.get_optimization_suggestions(image_bytes)
            self.assertNotIn('error', suggestions)

def run_validation_tests():
    """Run all validation tests"""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestInputValidator,
        TestImageOptimizer,
        TestSecurityMiddleware,
        TestValidationResult,
        TestOptimizationResult,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()

def run_performance_tests():
    """Run performance benchmarks"""
    import time
    from PIL import Image
    import io
    
    print("Running performance tests...")
    
    validator = InputValidator()
    optimizer = ImageOptimizer()
    
    # Test text validation performance
    start_time = time.time()
    for i in range(1000):
        validator.validate_text_input(f"Test message {i}", "test")
    text_time = time.time() - start_time
    print(f"Text validation (1000 iterations): {text_time:.3f}s")
    
    # Test JSON validation performance
    start_time = time.time()
    for i in range(1000):
        json_data = {"message": f"Test {i}", "value": i}
        validator.validate_json_input(json_data)
    json_time = time.time() - start_time
    print(f"JSON validation (1000 iterations): {json_time:.3f}s")
    
    # Test image optimization performance
    test_image = Image.new('RGB', (500, 500), color='red')
    image_data = io.BytesIO()
    test_image.save(image_data, format='JPEG')
    image_bytes = image_data.getvalue()
    
    start_time = time.time()
    for i in range(10):
        with patch('magic.from_buffer', return_value='image/jpeg'):
            optimizer.optimize_image(image_bytes)
    image_time = time.time() - start_time
    print(f"Image optimization (10 iterations): {image_time:.3f}s")

if __name__ == '__main__':
    print("Running Input Validation Tests...")
    print("=" * 50)
    
    # Run unit tests
    success = run_validation_tests()
    
    if success:
        print("\nAll tests passed! ✅")
        
        # Run performance tests
        print("\n" + "=" * 50)
        run_performance_tests()
        
    else:
        print("\nSome tests failed! ❌")
        exit(1)
