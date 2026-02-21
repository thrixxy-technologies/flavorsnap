import os
import uuid
import logging
import psutil
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, 
    get_jwt_identity, verify_jwt_in_request
)
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['LEGACY_MODEL'] = os.environ.get('LEGACY_MODEL', 'false').lower() == 'true'

# Initialize Extensions
CORS(app, origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000")])
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Global state for model status (Mocked for now)
MODEL_LOADED = True

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
    start_time = time.time()
    
    if 'image' not in request.files:


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    logger.info("Health check requested")
    return jsonify({
        'status': 'healthy',
        'service': 'flavorsnap-ml-api',
        'timestamp': time.time()
    })

if __name__ == '__main__':
