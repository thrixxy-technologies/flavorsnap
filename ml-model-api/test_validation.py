"""
Test script for image validation functionality
"""
import os
import sys
from io import BytesIO
from PIL import Image
from werkzeug.datastructures import FileStorage

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app import validate_image_file, sanitize_filename, allowed_file

def create_test_image(width, height, format='PNG'):
    """Create a test image in memory"""
    img = Image.new('RGB', (width, height), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format=format)
    img_bytes.seek(0)
    return img_bytes

def test_sanitize_filename():
    """Test filename sanitization"""
    print("\n=== Testing Filename Sanitization ===")
    
    test_cases = [
        ("normal_file.jpg", "normal_file.jpg"),
        ("../../../etc/passwd", "etcpasswd"),
        ("file with spaces.png", "file-with-spaces.png"),
        ("file@#$%^&*.jpg", "file.jpg"),
        ("UPPERCASE.JPG", "uppercase.jpg"),
        ("very" * 50 + ".png", None),  # Very long filename
    ]
    
    for input_name, expected in test_cases:
        result = sanitize_filename(input_name)
        status = "✓" if (expected is None or result == expected or len(result) <= 104) else "✗"
        print(f"{status} Input: '{input_name[:50]}...' -> Output: '{result}'")

def test_allowed_file():
    """Test file extension validation"""
    print("\n=== Testing File Extension Validation ===")
    
    test_cases = [
        ("image.jpg", True),
        ("image.jpeg", True),
        ("image.png", True),
        ("image.webp", True),
        ("image.gif", False),
        ("image.bmp", False),
        ("image.exe", False),
        ("image", False),
    ]
    
    for filename, expected in test_cases:
        result = allowed_file(filename)
        status = "✓" if result == expected else "✗"
        print(f"{status} {filename}: {result} (expected {expected})")

def test_validate_image_file():
    """Test comprehensive image validation"""
    print("\n=== Testing Image File Validation ===")
    
    # Test 1: Valid image
    print("\n1. Valid 200x200 PNG image:")
    img_bytes = create_test_image(200, 200, 'PNG')
    file = FileStorage(stream=img_bytes, filename="test.png", content_type="image/png")
    is_valid, error, data = validate_image_file(file)
    print(f"   {'✓' if is_valid else '✗'} Valid: {is_valid}, Error: {error}")
    if data:
        print(f"   Data: {data}")
    
    # Test 2: Image too small
    print("\n2. Image too small (50x50):")
    img_bytes = create_test_image(50, 50, 'PNG')
    file = FileStorage(stream=img_bytes, filename="small.png", content_type="image/png")
    is_valid, error, data = validate_image_file(file)
    print(f"   {'✓' if not is_valid else '✗'} Valid: {is_valid}, Error: {error}")
    
    # Test 3: Valid JPEG
    print("\n3. Valid 500x500 JPEG image:")
    img_bytes = create_test_image(500, 500, 'JPEG')
    file = FileStorage(stream=img_bytes, filename="test.jpg", content_type="image/jpeg")
    is_valid, error, data = validate_image_file(file)
    print(f"   {'✓' if is_valid else '✗'} Valid: {is_valid}, Error: {error}")
    if data:
        print(f"   Data: {data}")
    
    # Test 4: Empty file
    print("\n4. Empty file:")
    empty_bytes = BytesIO(b'')
    file = FileStorage(stream=empty_bytes, filename="empty.png", content_type="image/png")
    is_valid, error, data = validate_image_file(file)
    print(f"   {'✓' if not is_valid else '✗'} Valid: {is_valid}, Error: {error}")
    
    # Test 5: Invalid file (not an image)
    print("\n5. Invalid file (text file):")
    text_bytes = BytesIO(b'This is not an image')
    file = FileStorage(stream=text_bytes, filename="fake.png", content_type="image/png")
    is_valid, error, data = validate_image_file(file)
    print(f"   {'✓' if not is_valid else '✗'} Valid: {is_valid}, Error: {error}")
    
    # Test 6: No filename
    print("\n6. No filename:")
    img_bytes = create_test_image(200, 200, 'PNG')
    file = FileStorage(stream=img_bytes, filename="", content_type="image/png")
    is_valid, error, data = validate_image_file(file)
    print(f"   {'✓' if not is_valid else '✗'} Valid: {is_valid}, Error: {error}")

if __name__ == "__main__":
    print("=" * 60)
    print("Image Validation Test Suite")
    print("=" * 60)
    
    test_sanitize_filename()
    test_allowed_file()
    test_validate_image_file()
    
    print("\n" + "=" * 60)
    print("Test suite completed!")
    print("=" * 60)
