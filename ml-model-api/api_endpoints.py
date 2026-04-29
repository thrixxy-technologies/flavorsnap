"""
Enhanced API Endpoints with Advanced Rate Limiting for FlavorSnap
Provides rate-limited endpoints with monitoring, analytics, and graceful degradation
"""

from flask import Flask, request, jsonify
import json
from datetime import datetime
try:
    from db_config import get_connection
    from persistence import purge_old_history
    from security_config import (
        InputValidator, 
        FileValidator, 
        JSONValidator,
        SecurityMiddleware,
        ValidationReport,
        SecurityScore
    )
    from image_optimizer import (
        ImageProcessor,
        ImageOptimizer,
        ImageEnhancer,
        ThumbnailGenerator,
        BatchProcessor,
        ImageMetadata
    )
    from test_input_validation import (
        TestInputValidation,
        TestImageOptimization
    )
    from search_handlers import (
        SearchIndexer,
        SearchAnalytics,
        register_search_endpoints,
        index_database_documents
    )
except ImportError as e:
    print(f"Warning: Could not import new modules: {e}")
    # Fallback classes
    InputValidator = object
    FileValidator = object
    JSONValidator = object
    SecurityMiddleware = object
    ValidationReport = object
    SecurityScore = object
    ImageProcessor = object
    ImageOptimizer = object
    ImageEnhancer = object
    ThumbnailGenerator = object
    BatchProcessor = object
    ImageMetadata = object
    TestInputValidation = object
    TestImageOptimization = object
    SearchIndexer = object
    SearchAnalytics = object
    register_search_endpoints = lambda app: None
    index_database_documents = lambda: None

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
        
        if success:
            return jsonify({'message': f'Model {data["version"]} registered successfully'}), 201
        else:
            return jsonify({'error': 'Failed to register model'}), 500
    
    @app.route('/api/models/<version>/activate', methods=['POST'])
    def activate_model(version):
        """Activate a model version"""
        success = model_registry.activate_model(version)
        if success:
            return jsonify({'message': f'Model {version} activated successfully'})
        else:
            return jsonify({'error': 'Failed to activate model'}), 500
    
    @app.route('/api/models/<version>/validate', methods=['POST'])
    def validate_model(version):
        """Validate a model version"""
        try:
            result = model_validator.validate_model(version)
            return jsonify({
                'model_version': result.model_version,
                'validation_timestamp': result.validation_timestamp,
                'passed': result.passed,
                'overall_score': result.overall_score,
                'accuracy': result.accuracy,
                'precision': result.precision,
                'recall': result.recall,
                'f1_score': result.f1_score,
                'avg_inference_time': result.avg_inference_time,
                'avg_confidence': result.avg_confidence,
                'model_integrity_passed': result.model_integrity_passed,
                'performance_regression_detected': result.performance_regression_detected,
                'error_messages': result.error_messages,
                'detailed_metrics': result.detailed_metrics,
                'confusion_matrix_path': result.confusion_matrix_path
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/models/<version>/deploy', methods=['POST'])
    def deploy_model(version):
        """Deploy a model version"""
        force = request.json.get('force', False) if request.json else False
        
        success = deployment_manager.deploy_model(version, force)
        if success:
            return jsonify({'message': f'Model {version} deployed successfully'})
        else:
            return jsonify({'error': 'Failed to deploy model'}), 500
    
    @app.route('/api/deployment/rollback', methods=['POST'])
    def rollback_model():
        """Rollback to a previous model version"""
        data = request.get_json()
        target_version = data.get('target_version')
        reason = data.get('reason', 'Manual rollback')
        
        if not target_version:
            return jsonify({'error': 'target_version is required'}), 400
        
        success = deployment_manager.rollback_model(target_version, reason)
        if success:
            return jsonify({'message': f'Rolled back to model {target_version}'})
        else:
            return jsonify({'error': 'Failed to rollback model'}), 500
    
    @app.route('/api/deployment/health', methods=['GET'])
    def deployment_health():
        """Get deployment health status"""
        model_version = request.args.get('model_version')
        health = deployment_manager.health_check(model_version)
        return jsonify(health)
    
    @app.route('/api/deployment/history', methods=['GET'])
    def deployment_history():
        """Get deployment history"""
        limit = request.args.get('limit', 50, type=int)
        history = deployment_manager.get_deployment_history(limit)
        return jsonify({'history': history})
    
    @app.route('/api/deployment/rollback-versions', methods=['GET'])
    def available_rollback_versions():
        """Get available rollback versions"""
        versions = deployment_manager.get_available_rollback_versions()
        return jsonify({'versions': versions})

def register_ab_testing_endpoints(app, ab_test_manager):
    """Register A/B testing endpoints"""
    
    @app.route('/api/ab-tests', methods=['GET'])
    def list_ab_tests():
        """List all A/B tests"""
        status = request.args.get('status')
        tests = ab_test_manager.list_tests(status)
        return jsonify({'tests': tests})
    
    @app.route('/api/ab-tests', methods=['POST'])
    def create_ab_test():
        """Create a new A/B test"""
        data = request.get_json()
        
        required_fields = ['model_a_version', 'model_b_version']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        try:
            test_id = ab_test_manager.create_test(
                model_a_version=data['model_a_version'],
                model_b_version=data['model_b_version'],
                traffic_split=data.get('traffic_split', 0.5),
                description=data.get('description', ''),
                min_sample_size=data.get('min_sample_size', 100),
                confidence_threshold=data.get('confidence_threshold', 0.95)
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

def register_validation_endpoints(app):
    """Register input validation and security endpoints"""
    
    if InputValidator and ImageOptimizer:
        validator = InputValidator(ValidationLevel.MODERATE)
        optimizer = ImageOptimizer()
        
        @app.route('/api/validate/text', methods=['POST'])
        def validate_text():
            """Validate text input"""
            data = request.get_json()
            if not data or 'text' not in data:
                return jsonify({'error': 'text field is required'}), 400
            
            field_name = data.get('field_name', 'input')
            max_length = data.get('max_length', 1000)
            allow_html = data.get('allow_html', False)
            
            result = validator.validate_text_input(
                data['text'], field_name, max_length, allow_html
            )
            
            return jsonify({
                'is_valid': result.is_valid,
                'errors': result.errors,
                'warnings': result.warnings,
                'sanitized_data': result.sanitized_data,
                'security_score': result.security_score,
                'metadata': result.metadata
            })
        
        @app.route('/api/validate/file', methods=['POST'])
        def validate_file():
            """Validate file upload"""
            if 'file' not in request.files:
                return jsonify({'error': 'file is required'}), 400
            
            file = request.files['file']
            field_name = request.form.get('field_name', 'file')
            
            result = validator.validate_file_upload(file, field_name)
            
            return jsonify({
                'is_valid': result.is_valid,
                'errors': result.errors,
                'warnings': result.warnings,
                'security_score': result.security_score,
                'metadata': result.metadata
            })
        
        @app.route('/api/validate/json', methods=['POST'])
        def validate_json():
            """Validate JSON input"""
            data = request.get_json()
            if not data:
                return jsonify({'error': 'JSON data is required'}), 400
            
            schema = data.get('schema')
            json_data = data.get('data', data)
            
            result = validator.validate_json_input(json_data, schema)
            
            return jsonify({
                'is_valid': result.is_valid,
                'errors': result.errors,
                'warnings': result.warnings,
                'sanitized_data': result.sanitized_data,
                'security_score': result.security_score,
                'metadata': result.metadata
            })
        
        @app.route('/api/optimize/image', methods=['POST'])
        def optimize_image():
            """Optimize uploaded image"""
            if 'image' not in request.files:
                return jsonify({'error': 'image file is required'}), 400
            
            file = request.files['image']
            output_format = request.form.get('format', 'JPEG')
            preset = request.form.get('preset', 'web')
            
            # Read image data
            image_data = file.read()
            
            result = optimizer.optimize_image(
                image_data, output_format, preset
            )
            
            if result.success:
                response = jsonify({
                    'success': True,
                    'original_size': result.original_size,
                    'optimized_size': result.optimized_size,
                    'compression_ratio': result.compression_ratio,
                    'format': result.format,
                    'dimensions': result.dimensions,
                    'processing_time': result.processing_time,
                    'errors': result.errors,
                    'warnings': result.warnings,
                    'metadata': result.metadata
                })
                
                # Add optimized image as base64 if requested
                if request.form.get('include_data') == 'true':
                    import base64
                    optimized_data = result.metadata.get('optimized_data')
                    if optimized_data:
                        response.json['optimized_data'] = base64.b64encode(optimized_data).decode()
                
                return response
            else:
                return jsonify({
                    'success': False,
                    'errors': result.errors,
                    'warnings': result.warnings,
                    'metadata': result.metadata
                }), 400
        
        @app.route('/api/image/info', methods=['POST'])
        def get_image_info():
            """Get image information"""
            if 'image' not in request.files:
                return jsonify({'error': 'image file is required'}), 400
            
            file = request.files['image']
            image_data = file.read()
            
            info = optimizer.get_image_info(image_data)
            
            return jsonify(info)
        
        @app.route('/api/image/thumbnail', methods=['POST'])
        def create_thumbnail():
            """Create thumbnail from image"""
            if 'image' not in request.files:
                return jsonify({'error': 'image file is required'}), 400
            
            file = request.files['image']
            image_data = file.read()
            
            width = int(request.form.get('width', 150))
            height = int(request.form.get('height', 150))
            crop_to_fit = request.form.get('crop_to_fit', 'true').lower() == 'true'
            
            try:
                thumbnail_data = optimizer.create_thumbnail(
                    image_data, (width, height), crop_to_fit
                )
                
                import base64
                return jsonify({
                    'success': True,
                    'thumbnail_data': base64.b64encode(thumbnail_data).decode(),
                    'size': len(thumbnail_data)
                })
            
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/api/image/suggestions', methods=['POST'])
        def get_optimization_suggestions():
            """Get optimization suggestions for image"""
            if 'image' not in request.files:
                return jsonify({'error': 'image file is required'}), 400
            
            file = request.files['image']
            image_data = file.read()
            
            suggestions = optimizer.get_optimization_suggestions(image_data)
            
            return jsonify(suggestions)
        
        @app.route('/api/security/report', methods=['GET'])
        def get_security_report():
            """Get security validation report summary"""
            from security_config import create_security_report_summary
            summary = create_security_report_summary(app)
            return jsonify(summary)

def register_utility_endpoints(app):
    """Register utility endpoints"""
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Basic health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0',  # Updated version with model management
            'gateway_enabled': GATEWAY_AVAILABLE
        })
    
    @app.route('/api/classes', methods=['GET'])
    def get_classes():
        """Get supported food classes"""
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
            return jsonify({'items': items, 'count': len(items)})
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @app.route('/admin/retention/run', methods=['POST'])
    def run_retention():
        days = request.args.get('days', type=int) or 90
        try:
            deleted = purge_old_history(days)
            return jsonify({'status': 'ok', 'deleted': deleted, 'days': days})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# Function to register all endpoints
def register_all_endpoints(app, model_registry=None, ab_test_manager=None, deployment_manager=None, model_validator=None):
    """Register all endpoints"""
    if model_registry and deployment_manager and model_validator:
        register_management_endpoints(app, model_registry, ab_test_manager, deployment_manager, model_validator)
    if ab_test_manager:
        register_ab_testing_endpoints(app, ab_test_manager)
    register_utility_endpoints(app)
    
    # Register gateway endpoints if available
    if GATEWAY_AVAILABLE:
        register_gateway_endpoints(app)

def register_gateway_endpoints(app):
    """Register gateway management endpoints"""
    
    @app.route('/gateway/config', methods=['GET'])
    def get_gateway_config():
        """Get gateway configuration"""
        if not hasattr(app, 'gateway_instance'):
            return jsonify({'error': 'Gateway not configured'}), 503
        
        gateway = app.gateway_instance
        return jsonify({
            'name': gateway.config.name,
            'version': gateway.config.version,
            'debug': gateway.config.debug,
            'enable_cors': gateway.config.enable_cors,
            'cors_origins': gateway.config.cors_origins,
            'routes_count': len(gateway.routes),
            'services_count': len(gateway.services),
            'middleware_count': len(gateway.middleware_manager.middleware_registry)
        })
    
    @app.route('/gateway/routes', methods=['GET'])
    def list_gateway_routes():
        """List all gateway routes"""
        if not hasattr(app, 'gateway_instance'):
            return jsonify({'error': 'Gateway not configured'}), 503
        
        gateway = app.gateway_instance
        routes_data = []
        for route_id, route in gateway.routes.items():
            route_info = {
                'id': route_id,
                'path': route.path,
                'method': route.method.value,
                'backend_service': route.backend_service,
                'version': route.version,
                'deprecated': route.deprecated,
                'middleware_chain': route.middleware_chain,
                'auth_required': route.auth_required
            }
            routes_data.append(route_info)
        
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
