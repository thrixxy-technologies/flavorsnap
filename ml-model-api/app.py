import os
import uuid
import logging
import psutil
import re
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, 
    get_jwt_identity, verify_jwt_in_request
)
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from PIL import Image
from io import BytesIO
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Extensions
CORS(app, origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000")])
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Global state for model status (Mocked for now)
MODEL_LOADED = True

# --- Validation Configuration ---
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MIN_IMAGE_WIDTH = 100
MIN_IMAGE_HEIGHT = 100
MAX_IMAGE_WIDTH = 10000  # Prevent extremely large images
MAX_IMAGE_HEIGHT = 10000

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='user') # user, admin
    api_key = db.Column(db.String(64), unique=True, nullable=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def generate_api_key(self):
        self.api_key = str(uuid.uuid4())

# --- Decorators ---
def api_key_or_jwt_required(fn):
    @wraps(fn)
    def decorator(*args, **kwargs):
        # 1. Check API Key
        api_key = request.headers.get('X-API-KEY')
        if api_key:
            user = User.query.filter_by(api_key=api_key).first()
            if user:
                return fn(*args, **kwargs)
        
        # 2. Check JWT
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except:
            return jsonify({"error": "Authentication required (API Key or JWT)"}), 401
    return decorator

def role_required(role):
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user or (user.role != role and user.role != 'admin'):
                return jsonify({"error": "Insufficient permissions"}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

# --- Validation Helpers ---
def sanitize_filename(filename):
    """
    Sanitize filename to prevent path traversal and malicious names.
    """
    # Remove any path components
    filename = os.path.basename(filename)
    # Use werkzeug's secure_filename
    filename = secure_filename(filename)
    # Remove any remaining special characters except dots, dashes, and underscores
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    # Replace multiple spaces with single dash
    filename = re.sub(r'\s+', '-', filename)
    # Limit filename length
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    return f"{name}{ext}".lower()

def allowed_file(filename):
    """
    Check if file extension is allowed.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image_file(file):
    """
    Comprehensive validation of uploaded image file.
    Returns (is_valid, error_message, image_data)
    """
    # Check if file exists
    if not file:
        return False, "No file provided", None
    
    # Check filename
    if not file.filename:
        return False, "No filename provided", None
    
    # Validate file extension
    if not allowed_file(file.filename):
        return False, f"Invalid file type. Only {', '.join(ALLOWED_EXTENSIONS).upper()} files are allowed", None
    
    # Read file content
    try:
        file_content = file.read()
        file.seek(0)  # Reset file pointer for potential re-reading
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        return False, "Error reading file", None
    
    # Check file size
    file_size = len(file_content)
    if file_size == 0:
        return False, "File is empty", None
    
    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        return False, f"File size exceeds maximum limit of {max_mb}MB", None
    
    # Validate MIME type by checking file signature
    try:
        image = Image.open(BytesIO(file_content))
        
        # Verify image format matches allowed types
        image_format = image.format.lower() if image.format else None
        if image_format not in ['jpeg', 'png', 'webp']:
            return False, f"Invalid image format. Only JPEG, PNG, and WebP are supported", None
        
        # Check image dimensions
        width, height = image.size
        
        if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
            return False, f"Image dimensions too small. Minimum size is {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT}px", None
        
        if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
            return False, f"Image dimensions too large. Maximum size is {MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT}px", None
        
        # Verify image integrity by attempting to load it
        image.verify()
        
        # Re-open image after verify (verify closes the file)
        image = Image.open(BytesIO(file_content))
        
        # Check for potential malicious content
        # Ensure image mode is valid
        if image.mode not in ['RGB', 'RGBA', 'L', 'P']:
            return False, "Unsupported image mode", None
        
        # Additional security: Check for excessively large number of frames (for animated images)
        if hasattr(image, 'n_frames') and image.n_frames > 1:
            return False, "Animated images are not supported", None
        
        return True, None, {
            'format': image_format,
            'size': file_size,
            'dimensions': (width, height),
            'mode': image.mode
        }
        
    except Image.UnidentifiedImageError:
        return False, "File is not a valid image or format is not supported", None
    except Exception as e:
        logger.error(f"Error validating image: {str(e)}")
        return False, "Invalid or corrupted image file", None

# --- Routes ---
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"error": "Username and password required"}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already exists"}), 400
    
    user = User(username=data['username'], role=data.get('role', 'user'))
    user.set_password(data['password'])
    user.generate_api_key()
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        "message": "User registered successfully",
        "api_key": user.api_key
    }), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    
    if user and user.check_password(data.get('password')):
        token = create_access_token(identity=user.id)
        return jsonify({
            "access_token": token,
            "api_key": user.api_key,
            "role": user.role
        }), 200
    
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/predict', methods=['POST'])
@api_key_or_jwt_required
def predict():
    # Check if image file is present in request
    if 'image' not in request.files:
        return jsonify({
            "error": "No image provided",
            "code": "MISSING_FILE",
            "message": "Please upload an image file"
        }), 400
    
    file = request.files['image']
    
    # Validate the uploaded file
    is_valid, error_message, image_data = validate_image_file(file)
    
    if not is_valid:
        return jsonify({
            "error": error_message,
            "code": "INVALID_FILE",
            "message": error_message
        }), 400
    
    # Sanitize filename
    original_filename = file.filename
    safe_filename = sanitize_filename(original_filename)
    
    logger.info(f"Valid image uploaded: {safe_filename}, "
                f"size: {image_data['size']} bytes, "
                f"dimensions: {image_data['dimensions']}, "
                f"format: {image_data['format']}")
    
    # Mock response preserving existing API contract
    # In production, this would process the image with the ML model
    return jsonify({
        "label": "Moi Moi",
        "confidence": 85.7,
        "all_predictions": [
            { "label": "Moi Moi", "confidence": 85.7 },
            { "label": "Akara", "confidence": 9.2 },
            { "label": "Bread", "confidence": 3.1 }
        ],
        "processing_time": 0.234,
        "metadata": {
            "filename": safe_filename,
            "original_filename": original_filename,
            "size_bytes": image_data['size'],
            "dimensions": {
                "width": image_data['dimensions'][0],
                "height": image_data['dimensions'][1]
            },
            "format": image_data['format']
        }
    })

@app.route('/health', methods=['GET'])
def health():
    process = psutil.Process(os.getpid())
    return jsonify({
        "status": "healthy", 
        "auth_enabled": True, 
        "version": "1.1.0",
        "model_loaded": MODEL_LOADED,
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_usage_mb": process.memory_info().rss / 1024 / 1024
        }
    })

@app.route('/health/liveness', methods=['GET'])
def liveness():
    return jsonify({"status": "alive"}), 200

@app.route('/health/readiness', methods=['GET'])
def readiness():
    return jsonify({"status": "ready" if MODEL_LOADED else "loading"}), 200 if MODEL_LOADED else 503

@app.route('/classes', methods=['GET'])
def get_classes():
    return jsonify({
        "classes": ["Akara", "Bread", "Egusi", "Moi Moi", "Rice and Stew", "Yam"],
        "count": 6
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)