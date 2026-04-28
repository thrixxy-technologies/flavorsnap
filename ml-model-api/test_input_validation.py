"""
Test suite for input validation functionality
Tests all acceptance criteria for the no-input-validation issue
"""
import pytest
import io
from PIL import Image
from werkzeug.datastructures import FileStorage
from security_config import InputValidator, SecurityConfig


class TestFileTypeValidation:
    """Test file type validation - only jpg, png, webp allowed"""
    
    def test_valid_jpg_extension(self):
        """Test that .jpg files are accepted"""
        assert InputValidator.validate_filename("test.jpg") == True
    
    def test_valid_jpeg_extension(self):
        """Test that .jpeg files are accepted"""
        assert InputValidator.validate_filename("test.jpeg") == True
    
    def test_valid_png_extension(self):
        """Test that .png files are accepted"""
        assert InputValidator.validate_filename("test.png") == True
    
    def test_valid_webp_extension(self):
        """Test that .webp files are accepted"""
        assert InputValidator.validate_filename("test.webp") == True
    
    def test_invalid_gif_extension(self):
        """Test that .gif files are rejected"""
        assert InputValidator.validate_filename("test.gif") == False
    
    def test_invalid_bmp_extension(self):
        """Test that .bmp files are rejected"""
        assert InputValidator.validate_filename("test.bmp") == False
    
    def test_invalid_svg_extension(self):
        """Test that .svg files are rejected"""
        assert InputValidator.validate_filename("test.svg") == False
    
    def test_invalid_exe_extension(self):
        """Test that .exe files are rejected"""
        assert InputValidator.validate_filename("test.exe") == False


class TestFileSizeValidation:
    """Test file size limits - max 10MB"""
    
    def create_test_image(self, size_bytes):
        """Helper to create test image of specific size"""
        img = Image.new('RGB', (200, 200), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # Pad to desired size if needed
        current_size = len(img_bytes.getvalue())
        if size_bytes > current_size:
            padding = b'\x00' * (size_bytes - current_size)
            img_bytes = io.BytesIO(img_bytes.getvalue() + padding)
        
        return img_bytes
    
    def test_file_size_within_limit(self):
        """Test that files under 10MB are accepted"""
        # 5MB file
        img_bytes = self.create_test_image(5 * 1024 * 1024)
        file = FileStorage(
            stream=img_bytes,
            filename="test.jpg",
            content_type="image/jpeg"
        )
        
        is_valid, error = InputValidator.validate_file_upload(file)
        assert is_valid == True or "too large" not in (error or "")
    
    def test_file_size_exceeds_limit(self):
        """Test that files over 10MB are rejected"""
        # 11MB file
        img_bytes = self.create_test_image(11 * 1024 * 1024)
        file = FileStorage(
            stream=img_bytes,
            filename="test.jpg",
            content_type="image/jpeg"
        )
        
        is_valid, error = InputValidator.validate_file_upload(file)
        assert is_valid == False
        assert "too large" in error.lower() or "10" in error
    
    def test_max_size_is_10mb(self):
        """Verify that MAX_CONTENT_LENGTH is set to 10MB"""
        assert SecurityConfig.MAX_CONTENT_LENGTH == 10 * 1024 * 1024


class TestImageDimensionValidation:
    """Test image dimension validation - min 100x100px"""
    
    def create_image_with_dimensions(self, width, height):
        """Helper to create image with specific dimensions"""
        img = Image.new('RGB', (width, height), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes
    
    def test_minimum_dimensions_accepted(self):
        """Test that 100x100px images are accepted"""
        img_bytes = self.create_image_with_dimensions(100, 100)
        file = FileStorage(
            stream=img_bytes,
            filename="test.jpg",
            content_type="image/jpeg"
        )
        
        is_valid, error = InputValidator.validate_file_upload(file)
        assert is_valid == True
    
    def test_dimensions_above_minimum_accepted(self):
        """Test that images larger than 100x100px are accepted"""
        img_bytes = self.create_image_with_dimensions(500, 500)
        file = FileStorage(
            stream=img_bytes,
            filename="test.jpg",
            content_type="image/jpeg"
        )
        
        is_valid, error = InputValidator.validate_file_upload(file)
        assert is_valid == True
    
    def test_width_below_minimum_rejected(self):
        """Test that images with width < 100px are rejected"""
        img_bytes = self.create_image_with_dimensions(50, 100)
        file = FileStorage(
            stream=img_bytes,
            filename="test.jpg",
            content_type="image/jpeg"
        )
        
        is_valid, error = InputValidator.validate_file_upload(file)
        assert is_valid == False
        assert "too small" in error.lower() or "100" in error
    
    def test_height_below_minimum_rejected(self):
        """Test that images with height < 100px are rejected"""
        img_bytes = self.create_image_with_dimensions(100, 50)
        file = FileStorage(
            stream=img_bytes,
            filename="test.jpg",
            content_type="image/jpeg"
        )
        
        is_valid, error = InputValidator.validate_file_upload(file)
        assert is_valid == False
        assert "too small" in error.lower() or "100" in error
    
    def test_both_dimensions_below_minimum_rejected(self):
        """Test that images with both dimensions < 100px are rejected"""
        img_bytes = self.create_image_with_dimensions(50, 50)
        file = FileStorage(
            stream=img_bytes,
            filename="test.jpg",
            content_type="image/jpeg"
        )
        
        is_valid, error = InputValidator.validate_file_upload(file)
        assert is_valid == False
        assert "too small" in error.lower()


class TestFilenameSanitization:
    """Test filename and path sanitization"""
    
    def test_path_traversal_attack_prevented(self):
        """Test that path traversal attempts are blocked"""
        dangerous_names = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "test/../../../secret.txt"
        ]
        
        for dangerous_name in dangerous_names:
            sanitized = InputValidator.secure_filename_custom(dangerous_name)
            assert ".." not in sanitized
            assert "/" not in sanitized
            assert "\\" not in sanitized
    
    def test_special_characters_removed(self):
        """Test that special characters are removed from filenames"""
        filename = "test<script>alert('xss')</script>.jpg"
        sanitized = InputValidator.secure_filename_custom(filename)
        
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert "script" not in sanitized or sanitized.startswith("script")
    
    def test_null_bytes_removed(self):
        """Test that null bytes are removed"""
        filename = "test\x00.jpg"
        sanitized = InputValidator.secure_filename_custom(filename)
        assert "\x00" not in sanitized
    
    def test_valid_filename_preserved(self):
        """Test that valid filenames are preserved (with timestamp)"""
        filename = "my_photo.jpg"
        sanitized = InputValidator.secure_filename_custom(filename)
        
        assert "my_photo" in sanitized
        assert sanitized.endswith(".jpg")
    
    def test_timestamp_added_to_filename(self):
        """Test that timestamp is added to prevent collisions"""
        filename = "test.jpg"
        sanitized1 = InputValidator.secure_filename_custom(filename)
        sanitized2 = InputValidator.secure_filename_custom(filename)
        
        # Both should contain timestamp pattern (YYYYMMDD_HHMMSS)
        assert "_" in sanitized1
        assert len(sanitized1) > len(filename)


class TestMaliciousFileDetection:
    """Test detection of malicious files"""
    
    def test_non_image_file_rejected(self):
        """Test that non-image files are rejected"""
        # Create a text file disguised as image
        fake_image = io.BytesIO(b"This is not an image file")
        file = FileStorage(
            stream=fake_image,
            filename="fake.jpg",
            content_type="image/jpeg"
        )
        
        is_valid, error = InputValidator.validate_file_upload(file)
        assert is_valid == False
        assert "invalid" in error.lower() or "corrupted" in error.lower()
    
    def test_corrupted_image_rejected(self):
        """Test that corrupted images are rejected"""
        # Create corrupted JPEG header
        corrupted = io.BytesIO(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        file = FileStorage(
            stream=corrupted,
            filename="corrupted.jpg",
            content_type="image/jpeg"
        )
        
        is_valid, error = InputValidator.validate_file_upload(file)
        assert is_valid == False
    
    def test_empty_file_rejected(self):
        """Test that empty files are rejected"""
        empty_file = io.BytesIO(b"")
        file = FileStorage(
            stream=empty_file,
            filename="empty.jpg",
            content_type="image/jpeg"
        )
        
        is_valid, error = InputValidator.validate_file_upload(file)
        assert is_valid == False
        assert "empty" in error.lower()
    
    def test_mime_type_mismatch_rejected(self):
        """Test that MIME type mismatches are rejected"""
        img_bytes = io.BytesIO()
        img = Image.new('RGB', (200, 200), color='green')
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # Claim it's a PNG but it's actually JPEG
        file = FileStorage(
            stream=img_bytes,
            filename="test.jpg",
            content_type="application/octet-stream"
        )
        
        is_valid, error = InputValidator.validate_file_upload(file)
        assert is_valid == False
        assert "unsupported" in error.lower() or "type" in error.lower()


class TestErrorResponses:
    """Test that proper error messages are returned"""
    
    def test_no_file_error_message(self):
        """Test error message when no file is provided"""
        is_valid, error = InputValidator.validate_file_upload(None)
        assert is_valid == False
        assert error == "No file provided"
    
    def test_empty_filename_error_message(self):
        """Test error message for empty filename"""
        file = FileStorage(
            stream=io.BytesIO(b"test"),
            filename="",
            content_type="image/jpeg"
        )
        
        is_valid, error = InputValidator.validate_file_upload(file)
        assert is_valid == False
        assert "empty" in error.lower() or "filename" in error.lower()
    
    def test_invalid_extension_error_message(self):
        """Test error message for invalid file extension"""
        file = FileStorage(
            stream=io.BytesIO(b"test"),
            filename="test.exe",
            content_type="image/jpeg"
        )
        
        is_valid, error = InputValidator.validate_file_upload(file)
        assert is_valid == False
        assert "invalid" in error.lower() or "unsupported" in error.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
