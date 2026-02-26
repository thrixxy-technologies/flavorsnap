from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from functools import wraps

from category_management import CategoryManager, CategoryStatus, VoteType

# Create Blueprint
category_bp = Blueprint('category_management', __name__, url_prefix='/categories')

# Initialize Category Manager
category_manager = CategoryManager()

def validate_json(required_fields: List[str]):
    """Decorator to validate required JSON fields"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'error': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def allowed_file(filename: str, allowed_extensions: set = None) -> bool:
    """Check if file has allowed extension"""
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

@category_bp.route('/submit', methods=['POST'])
def submit_category():
    """Submit a new food category for review"""
    try:
        # Handle form data
        if 'name' not in request.form or 'description' not in request.form:
            return jsonify({'error': 'Name and description are required'}), 400
        
        if 'submitted_by' not in request.form:
            return jsonify({'error': 'Submitted by field is required'}), 400
        
        name = request.form['name'].strip()
        description = request.form['description'].strip()
        submitted_by = request.form['submitted_by'].strip()
        
        if not name or not description or not submitted_by:
            return jsonify({'error': 'All fields are required and cannot be empty'}), 400
        
        # Handle image uploads
        images = []
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename and allowed_file(file.filename):
                    # Generate secure filename
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    
                    # Save file
                    upload_path = os.path.join(category_manager.upload_folder, unique_filename)
                    file.save(upload_path)
                    
                    images.append(unique_filename)
        
        if not images:
            return jsonify({'error': 'At least one image is required'}), 400
        
        # Submit category
        result = category_manager.submit_category(name, description, submitted_by, images)
        
        if result['success']:
            return jsonify({
                'success': True,
                'category_id': result['category_id'],
                'message': result['message'],
                'submitted_at': datetime.now(timezone.utc).isoformat()
            }), 201
        else:
            return jsonify({'error': result.get('error', 'Submission failed')}), 400
            
    except Exception as e:
        current_app.logger.error(f"Category submission error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@category_bp.route('', methods=['GET'])
def get_categories():
    """Get categories with optional filtering"""
    try:
        # Query parameters
        status = request.args.get('status')
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100
        offset = max(int(request.args.get('offset', 0)), 0)
        
        # Validate status
        category_status = None
        if status:
            try:
                category_status = CategoryStatus(status.lower())
            except ValueError:
                return jsonify({'error': f'Invalid status: {status}'}), 400
        
        categories = category_manager.get_categories(category_status, limit, offset)
        
        return jsonify({
            'categories': categories,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total': len(categories)
            }
        })
        
    except ValueError as e:
        return jsonify({'error': 'Invalid limit or offset parameter'}), 400
    except Exception as e:
        current_app.logger.error(f"Get categories error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@category_bp.route('/<category_id>', methods=['GET'])
def get_category(category_id: str):
    """Get a specific category by ID"""
    try:
        category = category_manager.get_category(category_id)
        
        if not category:
            return jsonify({'error': 'Category not found'}), 404
        
        return jsonify(category)
        
    except Exception as e:
        current_app.logger.error(f"Get category error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@category_bp.route('/<category_id>/vote', methods=['POST'])
@validate_json(['user_id', 'vote_type'])
def vote_category(category_id: str):
    """Vote on a category submission"""
    try:
        data = request.get_json()
        user_id = data['user_id'].strip()
        vote_type_str = data['vote_type'].lower()
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Validate vote type
        try:
            vote_type = VoteType(vote_type_str)
        except ValueError:
            return jsonify({'error': f'Invalid vote type: {vote_type_str}'}), 400
        
        result = category_manager.vote_category(category_id, user_id, vote_type)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message']
            })
        else:
            return jsonify({'error': result.get('error', 'Vote failed')}), 400
            
    except Exception as e:
        current_app.logger.error(f"Vote category error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@category_bp.route('/<category_id>/moderate', methods=['POST'])
@validate_json(['moderator_id', 'action'])
def moderate_category(category_id: str):
    """Moderate a category submission (approve/reject)"""
    try:
        data = request.get_json()
        moderator_id = data['moderator_id'].strip()
        action = data['action'].lower()
        notes = data.get('notes', '').strip()
        
        if not moderator_id:
            return jsonify({'error': 'Moderator ID is required'}), 400
        
        result = category_manager.moderate_category(category_id, moderator_id, action, notes)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'status': result['status']
            })
        else:
            return jsonify({'error': result.get('error', 'Moderation failed')}), 400
            
    except Exception as e:
        current_app.logger.error(f"Moderate category error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@category_bp.route('/popular', methods=['GET'])
def get_popular_categories():
    """Get popular categories based on votes"""
    try:
        min_votes = max(int(request.args.get('min_votes', 10)), 1)
        limit = min(int(request.args.get('limit', 20)), 50)
        
        categories = category_manager.get_popular_categories(min_votes, limit)
        
        return jsonify({
            'categories': categories,
            'filters': {
                'min_votes': min_votes,
                'limit': limit
            }
        })
        
    except ValueError as e:
        return jsonify({'error': 'Invalid parameters'}), 400
    except Exception as e:
        current_app.logger.error(f"Get popular categories error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@category_bp.route('/training/queue', methods=['GET'])
def get_training_queue():
    """Get the training queue for approved categories"""
    try:
        queue = category_manager.get_training_queue()
        
        return jsonify({
            'training_queue': queue,
            'total_items': len(queue)
        })
        
    except Exception as e:
        current_app.logger.error(f"Get training queue error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@category_bp.route('/training/<training_id>/status', methods=['PUT'])
@validate_json(['status'])
def update_training_status(training_id: str):
    """Update the status of a training job"""
    try:
        data = request.get_json()
        status = data['status'].strip()
        error_message = data.get('error_message', '').strip()
        
        if not status:
            return jsonify({'error': 'Status is required'}), 400
        
        valid_statuses = ['queued', 'training', 'completed', 'failed']
        if status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
        
        result = category_manager.update_training_status(training_id, status, error_message)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message']
            })
        else:
            return jsonify({'error': result.get('error', 'Status update failed')}), 400
            
    except Exception as e:
        current_app.logger.error(f"Update training status error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@category_bp.route('/stats', methods=['GET'])
def get_category_stats():
    """Get statistics about category submissions"""
    try:
        conn = category_manager
        categories = conn.get_categories()
        
        stats = {
            'total_submissions': len(categories),
            'pending': len([c for c in categories if c['status'] == 'pending']),
            'approved': len([c for c in categories if c['status'] == 'approved']),
            'rejected': len([c for c in categories if c['status'] == 'rejected']),
            'in_training': len([c for c in categories if c['status'] == 'in_training']),
            'total_votes_up': sum(c['votes_up'] for c in categories),
            'total_votes_down': sum(c['votes_down'] for c in categories),
        }
        
        # Get training queue stats
        training_queue = conn.get_training_queue()
        stats['training_queue_size'] = len(training_queue)
        
        return jsonify(stats)
        
    except Exception as e:
        current_app.logger.error(f"Get category stats error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
