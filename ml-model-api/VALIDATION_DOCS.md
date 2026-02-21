# Image Upload Validation Documentation

## Overview

This document describes the comprehensive input validation implemented for the FlavorSnap API to ensure security, reliability, and proper handling of uploaded images.

## Validation Features

### 1. File Type Validation

**Allowed Formats:**

- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- WebP (`.webp`)

**Implementation:**

- Extension checking via `allowed_file()` function
- MIME type verification using PIL/Pillow
- File signature validation to prevent spoofing

**Rejected Formats:**

- GIF, BMP, TIFF, SVG
- Executable files (.exe, .sh, .bat)
- Archive files (.zip, .tar, .gz)
- Any other non-image formats

### 2. File Size Limits

**Maximum Size:** 10MB (10,485,760 bytes)

**Rationale:**

- Prevents memory exhaustion attacks
- Ensures reasonable processing times
- Balances quality with performance

**Error Response:**

```json
{
  "error": "File size exceeds maximum limit of 10.0MB",
  "code": "INVALID_FILE"
}
```

### 3. Image Dimension Validation

**Minimum Dimensions:** 100x100 pixels
**Maximum Dimensions:** 10,000x10,000 pixels

**Rationale:**

- Minimum: Ensures sufficient detail for ML model
- Maximum: Prevents memory exhaustion and DoS attacks

**Error Responses:**

```json
{
  "error": "Image dimensions too small. Minimum size is 100x100px",
  "code": "INVALID_FILE"
}
```

### 4. Filename Sanitization

**Security Measures:**

- Path traversal prevention (removes `../`, absolute paths)
- Special character removal
- Whitespace normalization
- Length limitation (100 characters for name)
- Lowercase conversion

**Examples:**

```python
"../../../etc/passwd" → "etcpasswd"
"file with spaces.png" → "file-with-spaces.png"
"file@#$%^&*.jpg" → "file.jpg"
"UPPERCASE.JPG" → "uppercase.jpg"
```

### 5. Malicious Content Detection

**Security Checks:**

- Image integrity verification using PIL's `verify()` method
- Valid image mode checking (RGB, RGBA, L, P only)
- Animated image rejection (prevents GIF bombs)
- File signature validation (prevents file type spoofing)
- Corrupted image detection

**Prevented Attacks:**

- Zip bombs / Decompression bombs
- Polyglot files (files valid as multiple formats)
- Steganography payloads
- Buffer overflow attempts

## API Endpoint

### POST /predict

**Request:**

```bash
curl -X POST http://localhost:5000/predict \
  -H "X-API-KEY: your-api-key" \
  -F "image=@/path/to/food.jpg"
```

**Success Response (200):**

```json
{
  "label": "Moi Moi",
  "confidence": 85.7,
  "all_predictions": [
    { "label": "Moi Moi", "confidence": 85.7 },
    { "label": "Akara", "confidence": 9.2 },
    { "label": "Bread", "confidence": 3.1 }
  ],
  "processing_time": 0.234,
  "metadata": {
    "filename": "food-image.jpg",
    "original_filename": "Food Image.jpg",
    "size_bytes": 2458624,
    "dimensions": {
      "width": 1920,
      "height": 1080
    },
    "format": "jpeg"
  }
}
```

**Error Responses:**

**Missing File (400):**

```json
{
  "error": "No image provided",
  "code": "MISSING_FILE",
  "message": "Please upload an image file"
}
```

**Invalid File Type (400):**

```json
{
  "error": "Invalid file type. Only jpg, jpeg, png, webp files are allowed",
  "code": "INVALID_FILE",
  "message": "Invalid file type. Only jpg, jpeg, png, webp files are allowed"
}
```

**File Too Large (400):**

```json
{
  "error": "File size exceeds maximum limit of 10.0MB",
  "code": "INVALID_FILE",
  "message": "File size exceeds maximum limit of 10.0MB"
}
```

**Invalid Dimensions (400):**

```json
{
  "error": "Image dimensions too small. Minimum size is 100x100px",
  "code": "INVALID_FILE",
  "message": "Image dimensions too small. Minimum size is 100x100px"
}
```

**Corrupted Image (400):**

```json
{
  "error": "Invalid or corrupted image file",
  "code": "INVALID_FILE",
  "message": "Invalid or corrupted image file"
}
```

## Configuration

All validation parameters are configurable in `app.py`:

```python
# Validation Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MIN_IMAGE_WIDTH = 100
MIN_IMAGE_HEIGHT = 100
MAX_IMAGE_WIDTH = 10000
MAX_IMAGE_HEIGHT = 10000
```

## Testing

Run the validation test suite:

```bash
cd ml-model-api
python test_validation.py
```

**Test Coverage:**

- Filename sanitization
- File extension validation
- Image dimension validation
- File size validation
- Corrupted file detection
- Empty file handling
- Invalid format detection

## Security Considerations

### Implemented Protections

1. **Path Traversal:** Prevented via `secure_filename()` and path sanitization
2. **File Type Spoofing:** Detected via PIL signature verification
3. **Zip Bombs:** Prevented via file size limits and dimension checks
4. **Memory Exhaustion:** Prevented via size and dimension limits
5. **Code Injection:** Prevented via filename sanitization
6. **DoS Attacks:** Rate limiting via authentication required

### Additional Recommendations

1. **Rate Limiting:** Implement per-user upload limits
2. **Virus Scanning:** Integrate ClamAV or similar for production
3. **Content Moderation:** Add NSFW/inappropriate content detection
4. **Logging:** Monitor validation failures for attack patterns
5. **CDN/WAF:** Use CloudFlare or AWS WAF for additional protection

## Dependencies

Required Python packages:

```
flask==3.0.0
pillow>=10.0.0
werkzeug>=3.0.0
```

## Performance Impact

**Validation Overhead:**

- File size check: ~1ms
- Extension validation: <1ms
- Image loading & verification: 10-50ms (depends on image size)
- Dimension check: <1ms
- Total: ~15-60ms per upload

**Memory Usage:**

- Peak memory: ~2x file size during validation
- Released immediately after validation

## Changelog

### Version 1.1.0 (Current)

- ✅ Added file type validation (jpg, png, webp only)
- ✅ Implemented file size limit (10MB max)
- ✅ Added image dimension validation (100x100 min)
- ✅ Implemented filename sanitization
- ✅ Added malicious file detection
- ✅ Enhanced error responses with codes
- ✅ Added metadata in success responses

### Version 1.0.0

- Basic file upload without validation

## Support

For issues or questions:

- GitHub Issues: https://github.com/your-username/flavorsnap/issues
- Telegram: https://t.me/+Tf3Ll4oRiGk5ZTM0
