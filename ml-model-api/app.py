import os
import time
import uuid
import base64
import io
import torch
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
from functools import wraps
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from marshmallow import Schema, fields, validate
from monitoring import MonitoringMiddleware, track_inference, update_model_accuracy
from swagger_setup import setup_swagger
from category_routes import category_bp
from xai_routes import xai_bp, initialize_explainer
from social_routes import social_bp

# Attempt to import custom logger, fallback to default if missing
try:
    from logger_config import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize monitoring
monitoring = MonitoringMiddleware(app)

# Initialize Swagger UI
setup_swagger(app)

# Register category management blueprint
app.register_blueprint(category_bp)

# Register XAI blueprint
app.register_blueprint(xai_bp)

# Register social sharing blueprint
app.register_blueprint(social_bp)

# --- ML MODEL SETUP ---
# Path logic: model.pth is in the parent directory of ml-model-api/
MODEL_PATH = os.path.join(os.getcwd(), '..', 'model.pth')
CLASSES_PATH = os.path.join(os.getcwd(), '..', 'food_classes.txt')

def load_ml_components():
    # 1. Load Labels
    with open(CLASSES_PATH, 'r') as f:
        labels = [line.strip() for line in f if line.strip()]
    
    # 2. Initialize ResNet18
    model = models.resnet18()
    model.fc = torch.nn.Linear(model.fc.in_features, len(labels))
    
    # 3. Load Weights
    if os.path.exists(MODEL_PATH):
        model.load_state_dict(torch.load(MODEL_PATH, map_location='cpu'))
        logger.info(f"Model loaded successfully from {MODEL_PATH}")
    else:
        logger.warning(f"Model file not found at {MODEL_PATH}. Using untrained weights.")
    
    model.eval()
    return model, labels

# Load once on startup
ML_MODEL, FOOD_LABELS = load_ml_components()

# Initialize XAI explainer after model is loaded
initialize_explainer(ML_MODEL, FOOD_LABELS)

# Image Preprocessing Transform
preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# --- UTILS & MIDDLEWARE ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

def get_request_id() -> str:
    return request.headers.get("X-Request-ID", uuid.uuid4().hex)

def make_success_response(data: Dict[str, Any], status_code: int = 200):
    body = dict(data)
    body["request_id"] = get_request_id()
    return jsonify(body), status_code

# In-memory store (placeholder for DB)
_predictions_store = []

# --- ROUTES ---
@app.route('/predict', methods=['POST'])
@limiter.limit("10 per minute")
@track_inference
def predict():
    start_time = time.time()
    
    # 1. Validation
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    
    try:
        # 2. Inference Logic
        img_bytes = file.read()
        image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        # Preprocess -> Tensor -> Model
        input_tensor = preprocess(image).unsqueeze(0)
        with torch.no_grad():
            outputs = ML_MODEL(input_tensor)
            probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
            
            # Get Top 3 Predictions
            top3_prob, top3_idx = torch.topk(probabilities, 3)
        
        # 3. Format Response
        main_label = FOOD_LABELS[top3_idx[0].item()]
        main_conf = float(top3_prob[0].item())
        
        all_predictions = [
            {"label": FOOD_LABELS[idx.item()], "confidence": float(prob.item())}
            for prob, idx in zip(top3_prob, top3_idx)
        ]

        processing_time = round(time.time() - start_time, 4)
        pred_id = str(uuid.uuid4())
        
        response_data = {
            "id": pred_id,
            "label": main_label,
            "confidence": main_conf,
            "all_predictions": all_predictions,
            "processing_time": processing_time,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # 4. Save to History
        _predictions_store.append(response_data)
        
        return make_success_response(response_data)

    except Exception as e:
        logger.error(f"Inference error: {str(e)}")
        return jsonify({'error': 'Inference failed', 'details': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'model_loaded': ML_MODEL is not None,
        'classes_count': len(FOOD_LABELS),
        'timestamp': time.time()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)