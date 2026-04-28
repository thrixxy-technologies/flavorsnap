import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import io
import os
import sys

# Add the parent directory to the path to import config modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import get_config, get_config_value
from logger_config import get_logger
from db_config import db_config, init_database

import hashlib
from datetime import datetime

# Add the parent directory to the path to import config modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import get_config, get_config_value
from logger_config import get_logger
from db_config import db_config, init_database
from batch_processor import MLBatchProcessor, TaskPriority
from cache_manager import CacheManager, DistributedCacheManager
from monitoring import QueueMonitor, console_alert_handler, log_alert_handler
from persistence import QueuePersistence, create_persistence_backend

# Initialize configuration
config = get_config()
logger = get_logger(__name__)

# Create Flask app with configuration
app = Flask(__name__)

# Configure Flask app from config
app.config['SECRET_KEY'] = get_config_value('app.secret_key')
app.config['DEBUG'] = get_config_value('app.debug', False)
app.config['MAX_CONTENT_LENGTH'] = get_config_value('file_storage.max_file_size', 16777216)

# Initialize database
try:
    init_database()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")

# Initialize queue management components
try:
    # Initialize persistence backend
    persistence_type = get_config_value('queue.persistence.backend', 'sqlite')
    persistence_config = get_config_value('queue.persistence', {})
    
    if persistence_type == 'sqlite':
        persistence_backend = create_persistence_backend(
            'sqlite', 
            db_path=persistence_config.get('db_path', 'queue_persistence.db')
        )
    else:
        persistence_backend = create_persistence_backend('file')
    
    queue_persistence = QueuePersistence(persistence_backend)
    
    # Initialize cache manager
    cache_config = get_config_value('cache', {})
    if cache_config.get('type') == 'redis':
        cache_manager = DistributedCacheManager(cache_config)
    else:
        cache_manager = CacheManager(cache_config)
    
    # Initialize queue monitor
    queue_monitor = QueueMonitor(get_config_value('queue.monitoring', {}))
    
    # Add alert handlers
    queue_monitor.alert_manager.add_alert_handler(console_alert_handler)
    queue_monitor.alert_manager.add_alert_handler(log_alert_handler)
    
    # Initialize batch processor
    max_workers = get_config_value('queue.max_workers', 4)
    queue_size = get_config_value('queue.max_size', 10000)
    batch_processor = MLBatchProcessor(None, max_workers, queue_size)  # Model will be set later
    
    # Start monitoring
    queue_monitor.start_monitoring(get_config_value('queue.monitoring.interval', 30))
    
    logger.info("Queue management components initialized successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize queue management: {e}")
    # Set components to None to prevent errors
    queue_persistence = None
    cache_manager = None
    queue_monitor = None
    batch_processor = None

# Configuration change callback
def on_config_change(new_config, old_config):
    """Handle configuration changes"""
    logger.info("Configuration changed, updating Flask app settings")
    app.config['SECRET_KEY'] = new_config.get('app', {}).get('secret_key')
    app.config['DEBUG'] = new_config.get('app', {}).get('debug', False)
    app.config['MAX_CONTENT_LENGTH'] = new_config.get('file_storage', {}).get('max_file_size', 16777216)

# Register configuration change callback
config.add_change_callback(on_config_change)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_status = db_config.test_connection()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': config.get('monitoring.health_check_interval'),
            'database': 'connected' if db_status else 'disconnected',
            'version': get_config_value('app.version', '1.0.0'),
            'environment': config.environment
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/config', methods=['GET'])
def get_config_info():
    """Get configuration information (non-sensitive)"""
    try:
        monitoring_info = config.get_monitoring_info()
        
        # Remove sensitive information
        safe_info = {
            'environment': monitoring_info['environment'],
            'last_reload': monitoring_info['last_reload'],
            'version_count': monitoring_info['version_count'],
            'watcher_active': monitoring_info['watcher_active'],
            'backup_count': monitoring_info['backup_count'],
            'validation_status': monitoring_info['validation_status']
        }
        
        return jsonify(safe_info), 200
    except Exception as e:
        logger.error(f"Failed to get config info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/config/reload', methods=['POST'])
def reload_config():
    """Reload configuration"""
    try:
        config.reload_config()
        logger.info("Configuration reloaded via API")
        return jsonify({'message': 'Configuration reloaded successfully'}), 200
    except Exception as e:
        logger.error(f"Failed to reload config: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/predict', methods=['POST'])
@tiered_rate_limit('predict')
@require_api_key
def predict():
    """Food classification prediction endpoint"""
    """Food classification prediction endpoint with queue support"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    
    # Validate file extension
    allowed_extensions = get_config_value('file_storage.allowed_extensions', ['jpg', 'jpeg', 'png', 'gif', 'bmp'])
    if file.filename and '.' in file.filename:
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'File extension not allowed. Allowed: {allowed_extensions}'}), 400

    try:
        # Log prediction request
        logger.info(f"Processing image: {file.filename}")
        
        # Placeholder for preprocessing & prediction
        image = Image.open(file.stream)
        
        # TODO: Implement actual model prediction
        # model_path = get_config_value('ml_model.model_path')
        # classes_file = get_config_value('ml_model.classes_file')
        # input_size = get_config_value('ml_model.input_size', [224, 224])
        
        predicted_label = "Moi Moi"  # Dummy output for now
        confidence = 0.95  # Dummy confidence
        
        logger.info(f"Prediction completed: {predicted_label} (confidence: {confidence})")
        
        return jsonify({
            'label': predicted_label,
            'confidence': confidence,
            'model_version': get_config_value('app.version', '1.0.0')
        })
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
    
    # Validate file extension
    allowed_extensions = get_config_value('file_storage.allowed_extensions', ['jpg', 'jpeg', 'png', 'gif', 'bmp'])
    if file.filename and '.' in file.filename:
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'File extension not allowed. Allowed: {allowed_extensions}'}), 400

    try:
        # Generate image hash for caching
        image_bytes = file.stream.read()
        file.stream.seek(0)  # Reset stream position
        image_hash = hashlib.md5(image_bytes).hexdigest()
        
        # Check cache first
        if cache_manager:
            cached_result = cache_manager.get_cached_prediction(image_hash)
            if cached_result:
                logger.info(f"Cache hit for image: {file.filename}")
                return jsonify({
                    'label': cached_result['label'],
                    'confidence': cached_result['confidence'],
                    'cached': True,
                    'model_version': get_config_value('app.version', '1.0.0')
                })
        
        # Check if we should use queue processing
        use_queue = request.form.get('use_queue', 'false').lower() == 'true'
        priority_str = request.form.get('priority', 'normal')
        
        if use_queue and batch_processor:
            # Submit to queue
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
                    'file_size': len(image_bytes)
                }
            }
            
            task_id = batch_processor.submit_task(
                payload=task_payload,
                priority=priority,
                metadata={'filename': file.filename}
            )
            
            # Save to persistence
            if queue_persistence:
                from persistence import PersistentTask, TaskStatus
                persistent_task = PersistentTask(
                    id=task_id,
                    priority=priority.value,
                    status=TaskStatus.PENDING,
                    payload=task_payload,
                    created_at=datetime.now(),
                    metadata={'filename': file.filename}
                )
                queue_persistence.save_task(persistent_task)
            
            logger.info(f"Task {task_id} submitted to queue with priority {priority.name}")
            
            return jsonify({
                'task_id': task_id,
                'status': 'queued',
                'priority': priority.name,
                'message': 'Task submitted to queue for processing'
            }), 202
        
        # Direct processing (original behavior)
        logger.info(f"Processing image directly: {file.filename}")
        
        image = Image.open(file.stream)
        
        # TODO: Implement actual model prediction
        # model_path = get_config_value('ml_model.model_path')
        # classes_file = get_config_value('ml_model.classes_file')
        # input_size = get_config_value('ml_model.input_size', [224, 224])
        
        predicted_label = "Moi Moi"  # Dummy output for now
        confidence = 0.95  # Dummy confidence
        
        result = {
            'label': predicted_label,
            'confidence': confidence,
            'model_version': get_config_value('app.version', '1.0.0')
        }
        
        # Cache result
        if cache_manager:
            cache_manager.cache_prediction_result(image_hash, result)
        
        logger.info(f"Prediction completed: {predicted_label} (confidence: {confidence})")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return jsonify({'error': str(e)}), 500

# Queue management endpoints
@app.route('/queue/status', methods=['GET'])
def queue_status():
    """Get queue status and statistics"""
    if not batch_processor:
        return jsonify({'error': 'Queue system not initialized'}), 503
    
    try:
        stats = batch_processor.get_queue_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/queue/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get status of a specific task"""
    if not batch_processor:
        return jsonify({'error': 'Queue system not initialized'}), 503
    
    try:
        task_status = batch_processor.get_task_status(task_id)
        if task_status:
            return jsonify(task_status), 200
        else:
            return jsonify({'error': 'Task not found'}), 404
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/queue/task/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """Cancel a pending task"""
    if not batch_processor:
        return jsonify({'error': 'Queue system not initialized'}), 503
    
    try:
        success = batch_processor.cancel_task(task_id)
        if success:
            return jsonify({'message': 'Task cancelled successfully'}), 200
        else:
            return jsonify({'error': 'Task not found or cannot be cancelled'}), 404
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/queue/retry/<task_id>', methods=['POST'])
def retry_task(task_id):
    """Retry a failed task"""
    if not batch_processor:
        return jsonify({'error': 'Queue system not initialized'}), 503
    
    try:
        success = batch_processor.retry_failed_task(task_id)
        if success:
            return jsonify({'message': 'Task requeued for retry'}), 200
        else:
            return jsonify({'error': 'Task not found in dead letter queue'}), 404
    except Exception as e:
        logger.error(f"Failed to retry task: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/queue/monitoring', methods=['GET'])
def get_monitoring_data():
    """Get queue monitoring data"""
    if not queue_monitor:
        return jsonify({'error': 'Monitoring system not initialized'}), 503
    
    try:
        # Get all queue metrics
        queue_metrics = queue_monitor.get_all_queue_metrics()
        
        # Get performance summary
        performance_summary = queue_monitor.get_performance_summary()
        
        # Get cache stats
        cache_stats = cache_manager.get_comprehensive_stats() if cache_manager else {}
        
        return jsonify({
            'queue_metrics': {name: {
                'pending_tasks': metrics.pending_tasks,
                'running_tasks': metrics.running_tasks,
                'completed_tasks': metrics.completed_tasks,
                'failed_tasks': metrics.failed_tasks,
                'error_rate': metrics.error_rate,
                'throughput': metrics.throughput,
                'avg_processing_time': metrics.average_processing_time,
                'last_updated': metrics.last_updated.isoformat()
            } for name, metrics in queue_metrics.items()},
            'performance_summary': performance_summary,
            'cache_stats': cache_stats,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Failed to get monitoring data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/queue/analytics', methods=['GET'])
def get_queue_analytics():
    """Get detailed queue analytics"""
    if not queue_monitor:
        return jsonify({'error': 'Monitoring system not initialized'}), 503
    
    try:
        queue_name = request.args.get('queue', 'default')
        hours = int(request.args.get('hours', 24))
        
        analytics = queue_monitor.get_queue_analytics(queue_name, hours)
        return jsonify(analytics), 200
    except Exception as e:
        logger.error(f"Failed to get queue analytics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/queue/export', methods=['GET'])
def export_metrics():
    """Export metrics in specified format"""
    if not queue_monitor:
        return jsonify({'error': 'Monitoring system not initialized'}), 503
    
    try:
        format_type = request.args.get('format', 'json')
        
        if format_type == 'prometheus':
            metrics_data = queue_monitor.export_metrics('prometheus')
            return metrics_data, 200, {'Content-Type': 'text/plain'}
        else:
            metrics_data = queue_monitor.export_metrics('json')
            return jsonify(json.loads(metrics_data)), 200
    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({'error': 'File too large'}), 413

@app.errorhandler(404)
def not_found(e):
    """Handle not found error"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server error"""
    logger.error(f"Internal server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    try:
        # Get server configuration
        host = get_config_value('app.host', '0.0.0.0')
        port = get_config_value('app.port', 5000)
        debug = get_config_value('app.debug', False)
        
        logger.info(f"Starting FlavorSnap ML API on {host}:{port}")
        logger.info(f"Environment: {config.environment}")
        logger.info(f"Debug mode: {debug}")
        
        # Start Flask application
        app.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)
    finally:
        # Cleanup resources
        config.cleanup()
        # Cleanup queue management resources
        logger.info("Shutting down queue management components")
        
        if batch_processor:
            batch_processor.shutdown()
        
        if queue_monitor:
            queue_monitor.stop_monitoring()
        
        if queue_persistence:
            queue_persistence.shutdown()
        
        if cache_manager:
            cache_manager.shutdown()
        
        # Cleanup other resources
        config.cleanup()
        logger.info("Application shutdown complete")
