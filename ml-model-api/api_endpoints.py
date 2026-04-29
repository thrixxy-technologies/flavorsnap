"""
Enhanced API Endpoints with Advanced Rate Limiting for FlavorSnap
Provides rate-limited endpoints with monitoring, analytics, and graceful degradation
"""

import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, g, current_app
from functools import wraps

from security_config import (
    get_rate_limiter, 
    rate_limit, 
    add_rate_limit_headers,
    AdvancedRateLimiter
)
from monitoring import QueueMonitor
from cache_manager import CacheManager
from logger_config import get_logger

logger = get_logger(__name__)

# Create API blueprint
api_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Rate limiting configurations for different endpoints
RATE_LIMIT_CONFIGS = {
    'predict': {
        'free': {'requests_per_minute': 5, 'burst_capacity': 3},
        'basic': {'requests_per_minute': 20, 'burst_capacity': 10},
        'premium': {'requests_per_minute': 100, 'burst_capacity': 20},
        'enterprise': {'requests_per_minute': 500, 'burst_capacity': 50}
    },
    'batch': {
        'free': {'requests_per_minute': 2, 'burst_capacity': 1},
        'basic': {'requests_per_minute': 10, 'burst_capacity': 5},
        'premium': {'requests_per_minute': 50, 'burst_capacity': 15},
        'enterprise': {'requests_per_minute': 200, 'burst_capacity': 40}
    },
    'analytics': {
        'free': {'requests_per_minute': 10, 'burst_capacity': 5},
        'basic': {'requests_per_minute': 30, 'burst_capacity': 15},
        'premium': {'requests_per_minute': 100, 'burst_capacity': 30},
        'enterprise': {'requests_per_minute': 500, 'burst_capacity': 100}
    },
    'queue_status': {
        'free': {'requests_per_minute': 20, 'burst_capacity': 10},
        'basic': {'requests_per_minute': 60, 'burst_capacity': 30},
        'premium': {'requests_per_minute': 200, 'burst_capacity': 50},
        'enterprise': {'requests_per_minute': 1000, 'burst_capacity': 200}
    }
}

def graceful_degradation(fallback_response: Optional[Dict] = None, fallback_status: int = 200):
    """Decorator for graceful degradation on system overload"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Check system load
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory_percent = psutil.virtual_memory().percent
                
                # Get rate limiter to update system load
                rate_limiter = get_rate_limiter()
                system_load = max(cpu_percent, memory_percent) / 100.0
                rate_limiter.update_system_load(system_load)
                
                # Graceful degradation thresholds
                if system_load > 0.95:  # Critical overload
                    logger.warning(f"System under critical load: {system_load:.2f}")
                    if fallback_response:
                        return jsonify(fallback_response), fallback_status
                    return jsonify({
                        'error': 'Service temporarily unavailable',
                        'message': 'System is experiencing high load. Please try again later.',
                        'retry_after': 60
                    }), 503
                
                elif system_load > 0.85:  # High load - reduce functionality
                    logger.info(f"System under high load: {system_load:.2f}")
                    # Add degradation header
                    response = f(*args, **kwargs)
                    if hasattr(response, 'headers'):
                        response.headers['X-System-Load'] = str(system_load)
                        response.headers['X-Service-Degraded'] = 'true'
                    return response
                
                # Normal operation
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in graceful degradation: {e}")
                # Fail open with fallback
                if fallback_response:
                    return jsonify(fallback_response), fallback_status
                return jsonify({'error': 'Internal server error'}), 500
        
        return decorated_function
    return decorator

def endpoint_rate_limit(endpoint_name: str):
    """Custom rate limiting for specific endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            limiter = get_rate_limiter()
            
            # Check rate limit with endpoint-specific configuration
            allowed, limit_info = limiter.check_rate_limit(request, endpoint_name)
            
            # Store limit info for response headers
            g.rate_limit_info = limit_info
            
            if not allowed:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Rate limit for {endpoint_name} exceeded. Try again in {limit_info.get("retry_after", 60)} seconds.',
                    'endpoint': endpoint_name,
                    'retry_after': limit_info.get('retry_after'),
                    'limit': limit_info.get('limit'),
                    'remaining': limit_info.get('remaining', 0),
                    'user_type': limit_info.get('user_type'),
                    'reset_time': limit_info.get('reset_time')
                }), 429
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

@api_bp.after_request
def after_request(response):
    """Add rate limit headers to all API responses"""
    return add_rate_limit_headers(response)

@api_bp.route('/predict', methods=['POST'])
@endpoint_rate_limit('predict')
@graceful_degradation(
    fallback_response={
        'error': 'Service temporarily unavailable',
        'message': 'Prediction service is under high load. Please try again later.',
        'cached_result_available': False
    },
    fallback_status=503
)
def predict():
    """Enhanced prediction endpoint with rate limiting"""
    try:
        from app import cache_manager, batch_processor, queue_persistence
        from batch_processor import TaskPriority
        from persistence import PersistentTask, TaskStatus
        from PIL import Image
        import hashlib
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400

        file = request.files['image']
        
        # Validate file
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
        
        # Generate image hash for caching
        image_bytes = file.stream.read()
        file.stream.seek(0)
        image_hash = hashlib.md5(image_bytes).hexdigest()
        
        # Check cache first
        if cache_manager:
            cached_result = cache_manager.get_cached_prediction(image_hash)
            if cached_result:
                logger.info(f"Cache hit for prediction: {file.filename}")
                return jsonify({
                    'label': cached_result['label'],
                    'confidence': cached_result['confidence'],
                    'cached': True,
                    'model_version': current_app.config.get('MODEL_VERSION', '1.0.0'),
                    'processing_time_ms': 0,
                    'rate_limit_info': getattr(g, 'rate_limit_info', {})
                })
        
        # Check if queue processing is requested
        use_queue = request.form.get('use_queue', 'false').lower() == 'true'
        
        if use_queue and batch_processor:
            priority_str = request.form.get('priority', 'normal')
            priority_map = {
                'low': TaskPriority.LOW,
                'normal': TaskPriority.NORMAL,
                'high': TaskPriority.HIGH,
                'critical': TaskPriority.CRITICAL
            }
            priority = priority_map.get(priority_str.lower(), TaskPriority.NORMAL)
            
            task_payload = {
                'image_data': image_bytes,
                'filename': file.filename,
                'metadata': {
                    'content_type': file.content_type,
                    'file_size': len(image_bytes),
                    'user_type': getattr(g, 'rate_limit_info', {}).get('user_type', 'free')
                }
            }
            
            task_id = batch_processor.submit_task(
                payload=task_payload,
                priority=priority,
                metadata={'filename': file.filename}
            )
            
            # Save to persistence
            if queue_persistence:
                persistent_task = PersistentTask(
                    id=task_id,
                    priority=priority.value,
                    status=TaskStatus.PENDING,
                    payload=task_payload,
                    created_at=datetime.now(),
                    metadata={'filename': file.filename}
                )
                queue_persistence.save_task(persistent_task)
            
            logger.info(f"Prediction task {task_id} submitted to queue")
            
            return jsonify({
                'task_id': task_id,
                'status': 'queued',
                'priority': priority.name,
                'message': 'Task submitted to queue for processing',
                'estimated_wait_time': batch_processor.get_estimated_wait_time(),
                'rate_limit_info': getattr(g, 'rate_limit_info', {})
            }), 202
        
        # Direct processing
        start_time = time.time()
        
        image = Image.open(file.stream)
        
        # TODO: Implement actual model prediction
        predicted_label = "Moi Moi"  # Dummy output
        confidence = 0.95
        
        processing_time = (time.time() - start_time) * 1000
        
        result = {
            'label': predicted_label,
            'confidence': confidence,
            'cached': False,
            'model_version': current_app.config.get('MODEL_VERSION', '1.0.0'),
            'processing_time_ms': processing_time,
            'rate_limit_info': getattr(g, 'rate_limit_info', {})
        }
        
        # Cache result
        if cache_manager:
            cache_manager.cache_prediction_result(image_hash, {
                'label': predicted_label,
                'confidence': confidence
            })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({'error': 'Prediction failed', 'message': str(e)}), 500

@api_bp.route('/batch', methods=['POST'])
@endpoint_rate_limit('batch')
@graceful_degradation()
def submit_batch():
    """Submit batch processing task with rate limiting"""
    try:
        from app import batch_processor, queue_persistence
        from batch_processor import TaskPriority
        from persistence import PersistentTask, TaskStatus
        
        if 'images' not in request.files:
            return jsonify({'error': 'No images uploaded'}), 400
        
        files = request.files.getlist('images')
        if not files:
            return jsonify({'error': 'No files selected'}), 400
        
        # Validate batch size
        max_batch_size = int(request.form.get('max_batch_size', 10))
        if len(files) > max_batch_size:
            return jsonify({
                'error': f'Batch size too large',
                'message': f'Maximum batch size is {max_batch_size} files',
                'provided_count': len(files)
            }), 400
        
        priority_str = request.form.get('priority', 'normal')
        priority_map = {
            'low': TaskPriority.LOW,
            'normal': TaskPriority.NORMAL,
            'high': TaskPriority.HIGH,
            'critical': TaskPriority.CRITICAL
        }
        priority = priority_map.get(priority_str.lower(), TaskPriority.NORMAL)
        
        # Process batch
        batch_tasks = []
        for file in files:
            if file.filename:
                image_bytes = file.stream.read()
                file.stream.seek(0)
                
                task_payload = {
                    'image_data': image_bytes,
                    'filename': file.filename,
                    'metadata': {
                        'content_type': file.content_type,
                        'file_size': len(image_bytes),
                        'batch_id': request.form.get('batch_id'),
                        'user_type': getattr(g, 'rate_limit_info', {}).get('user_type', 'free')
                    }
                }
                
                task_id = batch_processor.submit_task(
                    payload=task_payload,
                    priority=priority,
                    metadata={'filename': file.filename, 'batch': True}
                )
                
                batch_tasks.append({
                    'task_id': task_id,
                    'filename': file.filename
                })
        
        batch_id = f"batch_{int(time.time())}"
        
        # Save batch to persistence
        if queue_persistence:
            for task_data in batch_tasks:
                persistent_task = PersistentTask(
                    id=task_data['task_id'],
                    priority=priority.value,
                    status=TaskStatus.PENDING,
                    payload={'batch_id': batch_id},
                    created_at=datetime.now(),
                    metadata={'filename': task_data['filename'], 'batch': True}
                )
                queue_persistence.save_task(persistent_task)
        
        logger.info(f"Batch {batch_id} submitted with {len(batch_tasks)} tasks")
        
        return jsonify({
            'batch_id': batch_id,
            'status': 'queued',
            'task_count': len(batch_tasks),
            'tasks': batch_tasks,
            'priority': priority.name,
            'estimated_wait_time': batch_processor.get_estimated_wait_time(),
            'rate_limit_info': getattr(g, 'rate_limit_info', {})
        }), 202
        
    except Exception as e:
        logger.error(f"Batch submission error: {e}")
        return jsonify({'error': 'Batch submission failed', 'message': str(e)}), 500

@api_bp.route('/task/<task_id>', methods=['GET'])
@endpoint_rate_limit('queue_status')
def get_task_status(task_id: str):
    """Get task status with rate limiting"""
    try:
        from app import batch_processor, queue_persistence, cache_manager
        
        # Check cache first
        if cache_manager:
            cache_key = f"task_status:{task_id}"
            cached_status = cache_manager.queue_cache.get(cache_key)
            if cached_status:
                return jsonify({
                    **cached_status,
                    'cached': True,
                    'rate_limit_info': getattr(g, 'rate_limit_info', {})
                })
        
        # Get from batch processor
        task_info = batch_processor.get_task_info(task_id)
        if not task_info:
            return jsonify({'error': 'Task not found'}), 404
        
        # Get from persistence if available
        persistent_task = None
        if queue_persistence:
            persistent_task = queue_persistence.get_task(task_id)
        
        response_data = {
            'task_id': task_id,
            'status': task_info.get('status', 'unknown'),
            'created_at': task_info.get('created_at'),
            'started_at': task_info.get('started_at'),
            'completed_at': task_info.get('completed_at'),
            'result': task_info.get('result'),
            'error': task_info.get('error'),
            'priority': task_info.get('priority'),
            'cached': False,
            'rate_limit_info': getattr(g, 'rate_limit_info', {})
        }
        
        if persistent_task:
            response_data['persistent_status'] = persistent_task.status.value
            response_data['metadata'] = persistent_task.metadata
        
        # Cache status
        if cache_manager:
            cache_manager.queue_cache.set(cache_key, response_data, ttl_seconds=60)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Task status error: {e}")
        return jsonify({'error': 'Failed to get task status', 'message': str(e)}), 500

@api_bp.route('/queue/status', methods=['GET'])
@endpoint_rate_limit('queue_status')
def get_queue_status():
    """Get queue status with rate limiting"""
    try:
        from app import batch_processor, queue_monitor, cache_manager
        
        # Check cache first
        if cache_manager:
            cache_key = "queue_status:global"
            cached_status = cache_manager.queue_cache.get(cache_key)
            if cached_status:
                return jsonify({
                    **cached_status,
                    'cached': True,
                    'rate_limit_info': getattr(g, 'rate_limit_info', {})
                })
        
        # Get current queue status
        queue_stats = batch_processor.get_queue_stats()
        monitor_stats = queue_monitor.get_all_queue_metrics()
        
        response_data = {
            'queue_stats': queue_stats,
            'monitoring_stats': {
                name: {
                    'pending_tasks': metrics.pending_tasks,
                    'running_tasks': metrics.running_tasks,
                    'completed_tasks': metrics.completed_tasks,
                    'failed_tasks': metrics.failed_tasks,
                    'error_rate': metrics.error_rate,
                    'throughput': metrics.throughput,
                    'avg_processing_time': metrics.average_processing_time
                }
                for name, metrics in monitor_stats.items()
            },
            'system_load': {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            },
            'cached': False,
            'timestamp': datetime.now().isoformat(),
            'rate_limit_info': getattr(g, 'rate_limit_info', {})
        }
        
        # Cache status
        if cache_manager:
            cache_manager.queue_cache.set(cache_key, response_data, ttl_seconds=30)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Queue status error: {e}")
        return jsonify({'error': 'Failed to get queue status', 'message': str(e)}), 500

@api_bp.route('/analytics/rate-limits', methods=['GET'])
@endpoint_rate_limit('analytics')
def get_rate_limit_analytics():
    """Get rate limit analytics"""
    try:
        limiter = get_rate_limiter()
        hours = int(request.args.get('hours', 24))
        
        analytics = limiter.get_analytics(hours)
        
        return jsonify({
            'analytics': analytics,
            'rate_limit_info': getattr(g, 'rate_limit_info', {}),
            'request_params': {
                'hours': hours
            }
        })
        
    except Exception as e:
        logger.error(f"Rate limit analytics error: {e}")
        return jsonify({'error': 'Failed to get analytics', 'message': str(e)}), 500

@api_bp.route('/analytics/user/<user_id>', methods=['GET'])
@endpoint_rate_limit('analytics')
def get_user_analytics(user_id: str):
    """Get analytics for specific user"""
    try:
        limiter = get_rate_limiter()
        hours = int(request.args.get('hours', 24))
        
        analytics = limiter.get_user_analytics(user_id, hours)
        
        return jsonify({
            'user_analytics': analytics,
            'rate_limit_info': getattr(g, 'rate_limit_info', {}),
            'request_params': {
                'user_id': user_id,
                'hours': hours
            }
        })
        
    except Exception as e:
        logger.error(f"User analytics error: {e}")
        return jsonify({'error': 'Failed to get user analytics', 'message': str(e)}), 500

@api_bp.route('/admin/unblock-user/<user_id>', methods=['POST'])
@endpoint_rate_limit('analytics')
def unblock_user(user_id: str):
    """Unblock a user (admin endpoint)"""
    try:
        limiter = get_rate_limiter()
        
        # Check if user has admin privileges
        rate_limit_info = getattr(g, 'rate_limit_info', {})
        user_type = rate_limit_info.get('user_type', 'free')
        
        if user_type not in ['admin', 'enterprise']:
            return jsonify({
                'error': 'Insufficient privileges',
                'message': 'Only admin or enterprise users can unblock users'
            }), 403
        
        success = limiter.unblock_user(user_id)
        
        if success:
            return jsonify({
                'message': f'User {user_id} unblocked successfully',
                'unblocked_by': rate_limit_info.get('user_id', 'unknown'),
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'error': 'User not found or not blocked',
                'user_id': user_id
            }), 404
        
    except Exception as e:
        logger.error(f"Unblock user error: {e}")
        return jsonify({'error': 'Failed to unblock user', 'message': str(e)}), 500

@api_bp.route('/health/enhanced', methods=['GET'])
@graceful_degradation()
def enhanced_health_check():
    """Enhanced health check with rate limiting info"""
    try:
        from app import db_config, cache_manager, batch_processor
        
        # Basic health checks
        db_status = db_config.test_connection()
        cache_status = 'connected' if cache_manager else 'disconnected'
        queue_status = 'active' if batch_processor else 'inactive'
        
        # Rate limiter status
        limiter = get_rate_limiter()
        rate_limiter_stats = limiter.get_analytics(1)  # Last hour
        
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        overall_healthy = (
            db_status and 
            disk.free / disk.total > 0.1 and 
            memory.percent < 90 and
            cpu_percent < 95
        )
        
        health_data = {
            'status': 'healthy' if overall_healthy else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'database': 'connected' if db_status else 'disconnected',
                'cache': cache_status,
                'queue': queue_status,
                'rate_limiter': 'active',
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_free_percent': (disk.free / disk.total) * 100,
                    'load_average': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else None
                }
            },
            'rate_limiting': {
                'active_clients': rate_limiter_stats.get('active_clients', 0),
                'blocked_clients': rate_limiter_stats.get('blocked_clients', 0),
                'total_requests': rate_limiter_stats.get('rate_limit_analytics', {}).get('current_stats', {}).get('total_requests', 0),
                'blocked_requests': rate_limiter_stats.get('rate_limit_analytics', {}).get('current_stats', {}).get('blocked_requests', 0)
            },
            'version': current_app.config.get('VERSION', '1.0.0'),
            'environment': current_app.config.get('ENV', 'development'),
            'rate_limit_info': getattr(g, 'rate_limit_info', {})
        }
        
        status_code = 200 if overall_healthy else 503
        return jsonify(health_data), status_code
        
    except Exception as e:
        logger.error(f"Enhanced health check error: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'rate_limit_info': getattr(g, 'rate_limit_info', {})
        }), 500

# Error handlers
@api_bp.errorhandler(429)
def rate_limit_exceeded(e):
    """Handle rate limit exceeded errors"""
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please slow down.',
        'retry_after': getattr(e, 'retry_after', 60),
        'rate_limit_info': getattr(g, 'rate_limit_info', {})
    }), 429

@api_bp.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {e}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred. Please try again later.',
        'timestamp': datetime.now().isoformat(),
        'rate_limit_info': getattr(g, 'rate_limit_info', {})
    }), 500

@api_bp.errorhandler(503)
def service_unavailable(e):
    """Handle service unavailable errors"""
    return jsonify({
        'error': 'Service unavailable',
        'message': 'Service is temporarily unavailable due to high load.',
        'retry_after': 60,
        'timestamp': datetime.now().isoformat(),
        'rate_limit_info': getattr(g, 'rate_limit_info', {})
    }), 503

def register_api_endpoints(app):
    """Register all API endpoints with the Flask app"""
    app.register_blueprint(api_bp)
    logger.info("API endpoints registered successfully")
