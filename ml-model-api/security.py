"""
security.py — Comprehensive security middleware for FlavorSnap ML API.

This module is purely additive; it does not modify any existing files.
It provides:
  - Security response headers (HSTS, CSP, XFO, etc.)
  - API key authentication decorator (opt-in via API_KEY env var)
  - Input sanitization helpers
  - Image file validation (type + size)
  - CORS configuration builder
"""
import os
import re
from functools import wraps
from typing import Tuple, Dict, Any
from flask import request, jsonify

# bleach is optional — provides better HTML sanitization when installed.
# Falls back to a lightweight regex strip if not available.
try:
    import bleach as _bleach
    _BLEACH_AVAILABLE = True
except ImportError:
    _bleach = None
    _BLEACH_AVAILABLE = False

_HTML_TAG_RE = re.compile(r"<[^>]+>")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Allowed origins for CORS. Comma-separated list in env var, e.g.:
#   ALLOWED_ORIGINS=https://app.flavorsnap.io,https://www.flavorsnap.io
# Falls back to "*" when not set (development-friendly).
_RAW_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = (
    [o.strip() for o in _RAW_ORIGINS.split(",") if o.strip()]
    if _RAW_ORIGINS != "*"
    else "*"
)

# Maximum accepted file size in bytes (10 MB)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Permitted image MIME types
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

# API key (absent or empty string → auth disabled / development mode)
_API_KEY = os.environ.get("API_KEY", "").strip()


# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------

def add_security_headers(response):
    """
    After-request hook that attaches security headers to every response.

    Register with Flask:
        app.after_request(security.add_security_headers)
    """
    # Prevent MIME-type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Deny embedding in iframes (clickjacking protection)
    response.headers["X-Frame-Options"] = "DENY"

    # Legacy XSS filter for older browsers
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Enforce HTTPS for 1 year (only relevant when served over TLS)
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )

    # Control referrer information
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Restrict powerful browser features
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=()"
    )

    # Content-Security-Policy — strict for an API (no HTML served)
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; frame-ancestors 'none'"
    )

    # Remove the default "Server" header to avoid leaking stack info
    response.headers.pop("Server", None)

    return response


# ---------------------------------------------------------------------------
# API Key Authentication
# ---------------------------------------------------------------------------

def require_api_key(f):
    """
    Decorator that enforces bearer-token API key authentication.

    Behaviour:
      - If the API_KEY environment variable is not set (or empty), this
        decorator is a **no-op** — useful for local development.
      - If API_KEY is set, the request must include:
            Authorization: Bearer <key>
        Any missing, malformed, or incorrect key returns HTTP 401.

    Usage:
        @app.route('/predict', methods=['POST'])
        @limiter.limit("100 per minute")
        @require_api_key
        def predict():
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _API_KEY:
            # Auth disabled — pass through
            return f(*args, **kwargs)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return (
                jsonify({
                    "error": "Unauthorized",
                    "message": "Missing or invalid Authorization header. "
                               "Expected: Authorization: Bearer <api_key>",
                }),
                401,
            )

        provided_key = auth_header[len("Bearer "):].strip()
        # Use constant-time comparison to prevent timing attacks
        if not _safe_compare(provided_key, _API_KEY):
            return (
                jsonify({
                    "error": "Unauthorized",
                    "message": "Invalid API key.",
                }),
                401,
            )

        return f(*args, **kwargs)

    return decorated


def _safe_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing-based side channels.
    Equivalent to hmac.compare_digest but works on plain strings.
    """
    import hmac
    return hmac.compare_digest(a.encode(), b.encode())


# ---------------------------------------------------------------------------
# Input Sanitization
# ---------------------------------------------------------------------------

def sanitize_string(value: Any) -> str:
    """
    Strip all HTML tags and dangerous characters from a string value.

    Uses bleach when available (best-effort; strips tags + attributes).
    Falls back to a regex-based HTML tag stripper when bleach is not installed.
    Returns an empty string for non-string inputs.
    """
    if not isinstance(value, str):
        return ""
    if _BLEACH_AVAILABLE:
        cleaned = _bleach.clean(value, tags=[], attributes={}, strip=True)
    else:
        # Regex fallback: strip all HTML/XML tags
        cleaned = _HTML_TAG_RE.sub("", value)
    return cleaned.strip()


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize all string values in a dictionary.
    Non-string leaf values (int, float, bool, None) are passed through.
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = sanitize_string(value)
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_string(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


# ---------------------------------------------------------------------------
# Image File Validation
# ---------------------------------------------------------------------------

def validate_image_file(file) -> Tuple[bool, str]:
    """
    Validate an uploaded image file object (from request.files).

    Checks:
      1. Content-Type / MIME type is in ALLOWED_IMAGE_TYPES.
      2. File size does not exceed MAX_FILE_SIZE_BYTES (10 MB).

    Returns:
        (True, "")            — file is valid
        (False, error_message) — file is invalid, with the reason

    Note: This reads file.read() to check size, then seeks back to start
    so subsequent code can still read the file normally.
    """
    # 1. MIME type check (from the multipart Content-Type header for this part)
    content_type = file.content_type or ""
    # Normalise: strip parameters like "; charset=..."
    mime = content_type.split(";")[0].strip().lower()
    if mime not in ALLOWED_IMAGE_TYPES:
        return (
            False,
            f"Invalid file type '{mime}'. Allowed types: "
            + ", ".join(sorted(ALLOWED_IMAGE_TYPES)),
        )

    # 2. Size check — read into memory, then seek back
    data = file.read()
    file.seek(0)  # Reset so the route handler can read the file again

    if len(data) == 0:
        return False, "Uploaded file is empty."

    if len(data) > MAX_FILE_SIZE_BYTES:
        size_mb = len(data) / (1024 * 1024)
        return (
            False,
            f"File too large ({size_mb:.1f} MB). Maximum allowed size is "
            f"{MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    return True, ""


# ---------------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------------

def get_cors_config() -> Dict[str, Any]:
    """
    Return a dictionary of CORS settings to pass to flask_cors.CORS().

    Reads ALLOWED_ORIGINS from the environment (default: "*").

    Usage:
        from flask_cors import CORS
        CORS(app, **security.get_cors_config())
    """
    return {
        "origins": ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "X-Api-Key",
        ],
        "expose_headers": [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-Request-ID",
        ],
        "max_age": 600,           # Browser can cache preflight for 10 minutes
        "supports_credentials": False,
    }
