from flask import Blueprint, request, jsonify
import torch
import numpy as np
from PIL import Image
import io
import base64
from typing import Dict, Any, List
import traceback

from xai import ModelExplainer

# Create Blueprint
xai_bp = Blueprint('xai', __name__, url_prefix='/explain')

# Global explainer instance (will be initialized with the model)
explainer = None

def initialize_explainer(model, class_names: List[str]):
    """Initialize the XAI explainer with the trained model"""
    global explainer
    explainer = ModelExplainer(model)
    explainer.class_names = class_names

@xai_bp.route('/grad-cam', methods=['POST'])
def generate_grad_cam():
    """Generate Grad-CAM visualization for image classification"""
    try:
        if explainer is None:
            return jsonify({'error': 'Explainer not initialized'}), 500
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        class_idx = request.form.get('class_idx', type=int)
        
        if class_idx is None:
            return jsonify({'error': 'class_idx parameter is required'}), 400
        
        # Process image
        img_bytes = file.read()
        image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        # Preprocess (same as main prediction)
        preprocess = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        input_tensor = preprocess(image).unsqueeze(0)
        
        # Generate Grad-CAM
        heatmap = explainer.generate_grad_cam(input_tensor, class_idx)
        
        # Create overlay
        overlay_image = explainer.create_explanation_overlay(image, heatmap, 0.8)
        
        # Encode to base64
        heatmap_base64 = explainer.encode_image_to_base64(overlay_image)
        
        # Also return raw heatmap data
        heatmap_normalized = (heatmap * 255).astype(np.uint8).tolist()
        
        return jsonify({
            'success': True,
            'heatmap_overlay': f'data:image/png;base64,{heatmap_base64}',
            'heatmap_data': heatmap_normalized,
            'class_idx': class_idx,
            'class_name': explainer.class_names[class_idx] if class_idx < len(explainer.class_names) else f"Class_{class_idx}",
            'explanation': f'Grad-CAM visualization showing which regions of the image contributed most to the classification of {explainer.class_names[class_idx] if class_idx < len(explainer.class_names) else f"Class_{class_idx}"}.'
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate Grad-CAM',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500

@xai_bp.route('/feature-importance', methods=['POST'])
def generate_feature_importance():
    """Generate feature importance using integrated gradients"""
    try:
        if explainer is None:
            return jsonify({'error': 'Explainer not initialized'}), 500
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        top_k = request.form.get('top_k', 10, type=int)
        
        # Process image
        img_bytes = file.read()
        image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        # Preprocess
        preprocess = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        input_tensor = preprocess(image).unsqueeze(0)
        
        # Generate feature importance
        importance_scores = explainer.generate_feature_importance(input_tensor, top_k)
        
        return jsonify({
            'success': True,
            'feature_importance': importance_scores,
            'top_k': top_k,
            'explanation': 'Feature importance scores indicate which visual features (patterns, textures, shapes) contributed most to the classification decision.'
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate feature importance',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500

@xai_bp.route('/confidence-explanation', methods=['POST'])
def generate_confidence_explanation():
    """Generate detailed confidence explanation for predictions"""
    try:
        if explainer is None:
            return jsonify({'error': 'Explainer not initialized'}), 500
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        
        # Process image
        img_bytes = file.read()
        image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        # Preprocess
        preprocess = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        input_tensor = preprocess(image).unsqueeze(0)
        
        # Get model predictions
        with torch.no_grad():
            outputs = explainer.model(input_tensor)
            probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
        
        # Generate confidence explanation
        confidence_data = explainer.generate_confidence_explanation(probabilities, explainer.class_names)
        
        return jsonify({
            'success': True,
            'confidence_explanation': confidence_data,
            'explanation': 'Confidence explanation shows how certain the model is about its predictions and provides insights into the decision-making process.'
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate confidence explanation',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500

@xai_bp.route('/similar-images', methods=['POST'])
def find_similar_images():
    """Find similar images based on feature similarity"""
    try:
        if explainer is None:
            return jsonify({'error': 'Explainer not initialized'}), 500
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        top_k = request.form.get('top_k', 3, type=int)
        
        # Process image
        img_bytes = file.read()
        image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        # Preprocess
        preprocess = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        input_tensor = preprocess(image).unsqueeze(0)
        
        # Extract features (using the model's penultimate layer)
        with torch.no_grad():
            # Remove the final classification layer to get features
            features = explainer.model(input_tensor)
        
        # Find similar images
        similar_images = explainer.find_similar_images(features, top_k=top_k)
        
        return jsonify({
            'success': True,
            'similar_images': similar_images,
            'top_k': top_k,
            'explanation': 'Similar images are found by comparing visual features and patterns with previously seen examples.'
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to find similar images',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500

@xai_bp.route('/educational-tooltip', methods=['POST'])
def generate_educational_tooltip():
    """Generate educational tooltips and information"""
    try:
        if explainer is None:
            return jsonify({'error': 'Explainer not initialized'}), 500
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        class_name = data.get('class_name')
        confidence = data.get('confidence', 0.0)
        
        if not class_name:
            return jsonify({'error': 'class_name is required'}), 400
        
        # Generate educational tooltip
        tooltip_data = explainer.generate_educational_tooltip(class_name, confidence)
        
        return jsonify({
            'success': True,
            'tooltip_data': tooltip_data,
            'class_name': class_name,
            'confidence': confidence,
            'explanation': 'Educational tooltips provide additional context and learning information about the food classification.'
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate educational tooltip',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500

@xai_bp.route('/comprehensive-explanation', methods=['POST'])
def generate_comprehensive_explanation():
    """Generate comprehensive explanation combining all XAI methods"""
    try:
        if explainer is None:
            return jsonify({'error': 'Explainer not initialized'}), 500
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        top_k = request.form.get('top_k', 3, type=int)
        
        # Process image
        img_bytes = file.read()
        image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        # Preprocess
        preprocess = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        input_tensor = preprocess(image).unsqueeze(0)
        
        # Get model predictions
        with torch.no_grad():
            outputs = explainer.model(input_tensor)
            probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
            top_prob, top_idx = torch.topk(probabilities, min(top_k, len(probabilities)))
        
        # Generate all explanations
        main_class_idx = top_idx[0].item()
        main_confidence = top_prob[0].item()
        
        # Grad-CAM for top prediction
        heatmap = explainer.generate_grad_cam(input_tensor, main_class_idx)
        overlay_image = explainer.create_explanation_overlay(image, heatmap, main_confidence)
        heatmap_base64 = explainer.encode_image_to_base64(overlay_image)
        
        # Feature importance
        feature_importance = explainer.generate_feature_importance(input_tensor, 10)
        
        # Confidence explanation
        confidence_explanation = explainer.generate_confidence_explanation(probabilities, explainer.class_names)
        
        # Similar images
        similar_images = explainer.find_similar_images(probabilities, top_k=3)
        
        # Educational tooltip
        main_class_name = explainer.class_names[main_class_idx] if main_class_idx < len(explainer.class_names) else f"Class_{main_class_idx}"
        educational_tooltip = explainer.generate_educational_tooltip(main_class_name, main_confidence)
        
        # Compile comprehensive explanation
        comprehensive_data = {
            'success': True,
            'prediction': {
                'class_name': main_class_name,
                'class_idx': main_class_idx,
                'confidence': float(main_confidence),
                'confidence_percentage': f"{main_confidence * 100:.1f}%"
            },
            'grad_cam': {
                'heatmap_overlay': f'data:image/png;base64,{heatmap_base64}',
                'explanation': f'Grad-CAM highlights the regions that most influenced the classification of {main_class_name}. Brighter areas indicate higher importance.'
            },
            'feature_importance': {
                'importance_scores': feature_importance,
                'explanation': 'Feature importance shows which visual patterns and textures contributed most to the decision.'
            },
            'confidence_explanation': confidence_explanation,
            'similar_images': similar_images,
            'educational_tooltip': educational_tooltip,
            'overall_explanation': f'''
            The model classified this image as {main_class_name} with {main_confidence * 100:.1f}% confidence. 
            The Grad-CAM visualization shows that the model focused on specific regions of the image to make this decision.
            The feature importance analysis reveals which visual patterns were most influential.
            Similar images show examples of {main_class_name} that the model has learned from during training.
            '''
        }
        
        return jsonify(comprehensive_data)
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate comprehensive explanation',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500

@xai_bp.route('/methods', methods=['GET'])
def get_available_methods():
    """Get information about available XAI methods"""
    methods = {
        'grad_cam': {
            'name': 'Grad-CAM',
            'description': 'Gradient-weighted Class Activation Mapping - highlights regions of the image that contributed most to the classification',
            'use_case': 'Understanding which parts of the image the model focused on',
            'output': 'Heatmap overlay on original image'
        },
        'feature_importance': {
            'name': 'Feature Importance (Integrated Gradients)',
            'description': 'Measures how much each input feature contributes to the final prediction',
            'use_case': 'Understanding which visual patterns and textures are important',
            'output': 'Numerical importance scores for different features'
        },
        'confidence_explanation': {
            'name': 'Confidence Explanation',
            'description': 'Provides detailed breakdown of prediction confidence and uncertainty',
            'use_case': 'Understanding how certain the model is about its predictions',
            'output': 'Confidence scores, entropy, and explanatory text'
        },
        'similar_images': {
            'name': 'Similar Images',
            'description': 'Finds visually similar images from the training dataset',
            'use_case': 'Understanding what similar examples the model learned from',
            'output': 'List of similar images with similarity scores'
        },
        'educational_tooltip': {
            'name': 'Educational Tooltips',
            'description': 'Provides educational information about the predicted food category',
            'use_case': 'Learning more about the food and its characteristics',
            'output': 'Educational text and context information'
        }
    }
    
    return jsonify({
        'success': True,
        'available_methods': methods,
        'comprehensive_endpoint': '/explain/comprehensive-explanation',
        'note': 'Use the comprehensive endpoint to get all explanations at once, or individual endpoints for specific methods.'
    })
