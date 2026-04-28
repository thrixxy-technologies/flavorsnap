from flask import Blueprint, request, jsonify
from PIL import Image
import io
import base64
from typing import Dict, Any, List
import traceback

from social_sharing import SocialShareGenerator
from security_config import InputValidator, validate_json_input

# Create Blueprint
social_bp = Blueprint('social', __name__, url_prefix='/social')

# Initialize social share generator
share_generator = SocialShareGenerator()

@social_bp.route('/generate-shareable', methods=['POST'])
def generate_shareable_content():
    """Generate shareable content for social media platforms"""
    try:
        # Validate and sanitize JSON input if present
        if request.is_json:
            json_data = request.get_json()
            is_valid, error_msg = validate_json_input(json_data)
            if not is_valid:
                return jsonify({'error': error_msg}), 400

        # Get and sanitize form data
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        
        # Sanitize filename
        if file.filename:
            file.filename = InputValidator.sanitize_filename(file.filename)
        
        prediction = InputValidator.sanitize_string(request.form.get('prediction', ''), max_length=100)
        confidence = request.form.get('confidence', type=float, default=0.0)
        platforms = request.form.getlist('platforms')
        template = InputValidator.sanitize_string(request.form.get('template', 'default'), max_length=50)
        
        if not prediction:
            return jsonify({'error': 'prediction is required'}), 400
        
        if confidence < 0 or confidence > 1:
            return jsonify({'error': 'confidence must be between 0 and 1'}), 400
        
        # Sanitize platforms list
        sanitized_platforms = []
        allowed_platforms = ['twitter', 'facebook', 'instagram', 'linkedin', 'whatsapp']
        for platform in platforms[:10]:  # Limit to 10 platforms
            sanitized_platform = InputValidator.sanitize_string(str(platform), max_length=50)
            if sanitized_platform in allowed_platforms:
                sanitized_platforms.append(sanitized_platform)
        
        # Process image
        img_bytes = file.read()
        original_image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        # Generate shareable content
        shareable_data = share_generator.create_shareable_response(
            original_image, prediction, confidence, sanitized_platforms
        )
        
        return jsonify({
            'success': True,
            'data': shareable_data,
            'message': 'Shareable content generated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate shareable content',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500

@social_bp.route('/share-text', methods=['POST'])
def generate_share_text():
    """Generate share text for specific platform"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate and sanitize JSON input
        is_valid, error_msg = validate_json_input(data)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        prediction = InputValidator.sanitize_string(data.get('prediction', ''), max_length=100)
        confidence = data.get('confidence', 0.0)
        platform = InputValidator.sanitize_string(data.get('platform', 'twitter'), max_length=50)
        
        if not prediction:
            return jsonify({'error': 'prediction is required'}), 400
        
        if confidence < 0 or confidence > 1:
            return jsonify({'error': 'confidence must be between 0 and 1'}), 400
        
        # Validate platform
        allowed_platforms = ['twitter', 'facebook', 'instagram', 'linkedin', 'whatsapp']
        if platform not in allowed_platforms:
            platform = 'twitter'  # Default fallback
        
        # Generate share text
        share_text = share_generator.generate_share_text(prediction, confidence, platform)
        
        return jsonify({
            'success': True,
            'platform': platform,
            'share_text': share_text,
            'character_count': len(share_text)
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate share text',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500

@social_bp.route('/share-image', methods=['POST'])
def generate_share_image():
    """Generate shareable image with overlay"""
    try:
        # Validate and sanitize JSON input if present
        if request.is_json:
            json_data = request.get_json()
            is_valid, error_msg = validate_json_input(json_data)
            if not is_valid:
                return jsonify({'error': error_msg}), 400

        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        
        # Sanitize filename
        if file.filename:
            file.filename = InputValidator.sanitize_filename(file.filename)
        
        prediction = InputValidator.sanitize_string(request.form.get('prediction', ''), max_length=100)
        confidence = request.form.get('confidence', type=float, default=0.0)
        template = InputValidator.sanitize_string(request.form.get('template', 'default'), max_length=50)
        
        if not prediction:
            return jsonify({'error': 'prediction is required'}), 400
        
        if confidence < 0 or confidence > 1:
            return jsonify({'error': 'confidence must be between 0 and 1'}), 400
        
        # Validate template
        allowed_templates = ['default', 'modern', 'classic', 'minimal']
        if template not in allowed_templates:
            template = 'default'
        
        # Process image
        img_bytes = file.read()
        original_image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        # Generate shareable image
        shareable_image = share_generator.generate_shareable_image(
            original_image, prediction, confidence, template
        )
        
        return jsonify({
            'success': True,
            'shareable_image': shareable_image,
            'template_used': template,
            'prediction': prediction,
            'confidence': confidence
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate shareable image',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500

@social_bp.route('/open-graph-metadata', methods=['POST'])
def generate_open_graph_metadata():
    """Generate OpenGraph metadata for social sharing"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        prediction = data.get('prediction', '')
        confidence = data.get('confidence', 0.0)
        image_url = data.get('image_url', '')
        
        if not prediction:
            return jsonify({'error': 'prediction is required'}), 400
        
        if confidence < 0 or confidence > 1:
            return jsonify({'error': 'confidence must be between 0 and 1'}), 400
        
        # Generate OpenGraph metadata
        og_metadata = share_generator.generate_open_graph_metadata(
            prediction, confidence, image_url
        )
        
        return jsonify({
            'success': True,
            'open_graph_metadata': og_metadata,
            'html_tags': _generate_html_tags(og_metadata)
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate OpenGraph metadata',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500

@social_bp.route('/track-share', methods=['POST'])
def track_sharing_analytics():
    """Track social sharing analytics"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        prediction = data.get('prediction', '')
        platform = data.get('platform', '')
        user_id = data.get('user_id')
        
        if not prediction:
            return jsonify({'error': 'prediction is required'}), 400
        
        if not platform:
            return jsonify({'error': 'platform is required'}), 400
        
        # Track analytics
        analytics_result = share_generator.track_sharing_analytics(
            prediction, platform, user_id
        )
        
        return jsonify(analytics_result)
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to track sharing analytics',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500

@social_bp.route('/platforms', methods=['GET'])
def get_supported_platforms():
    """Get list of supported social media platforms"""
    platforms = {
        'twitter': {
            'name': 'Twitter',
            'character_limit': 280,
            'supported_features': ['text', 'image', 'hashtags'],
            'share_url_template': 'https://twitter.com/intent/tweet?text={text}'
        },
        'facebook': {
            'name': 'Facebook',
            'character_limit': None,
            'supported_features': ['text', 'image', 'link'],
            'share_url_template': 'https://www.facebook.com/sharer/sharer.php?u={url}'
        },
        'instagram': {
            'name': 'Instagram',
            'character_limit': 2200,
            'supported_features': ['image', 'hashtags'],
            'share_url_template': 'https://www.instagram.com/',
            'note': 'Instagram does not support direct URL sharing'
        },
        'linkedin': {
            'name': 'LinkedIn',
            'character_limit': None,
            'supported_features': ['text', 'image', 'link'],
            'share_url_template': 'https://www.linkedin.com/sharing/share-offsite/?url={url}'
        }
    }
    
    return jsonify({
        'success': True,
        'supported_platforms': platforms,
        'default_platforms': ['twitter', 'facebook', 'instagram'],
        'templates': ['default', 'minimal', 'colorful']
    })

@social_bp.route('/templates', methods=['GET'])
def get_available_templates():
    """Get list of available image templates"""
    templates = {
        'default': {
            'name': 'Default',
            'description': 'Standard FlavorSnap template with confidence display',
            'preview': '/templates/preview/default.png'
        },
        'minimal': {
            'name': 'Minimal',
            'description': 'Clean, minimal design with essential information',
            'preview': '/templates/preview/minimal.png'
        },
        'colorful': {
            'name': 'Colorful',
            'description': 'Vibrant, eye-catching design with gradient effects',
            'preview': '/templates/preview/colorful.png'
        }
    }
    
    return jsonify({
        'success': True,
        'available_templates': templates,
        'default_template': 'default'
    })

def _generate_html_tags(og_metadata: Dict[str, str]) -> str:
    """Generate HTML meta tags from OpenGraph metadata"""
    tags = []
    
    for key, value in og_metadata.items():
        if key.startswith('og:'):
            tags.append(f'<meta property="{key}" content="{value}" />')
        elif key.startswith('twitter:'):
            tags.append(f'<meta name="{key}" content="{value}" />')
    
    return '\n'.join(tags)
