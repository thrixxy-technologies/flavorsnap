from flask import Flask, request, jsonify, g
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
from security_config import init_rate_limiter, add_rate_limit_headers
from api_endpoints import register_api_endpoints

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

# Initialize rate limiting system
try:
    rate_limit_config = get_config_value('rate_limiting', {})
    rate_limiter = init_rate_limiter(rate_limit_config)
    logger.info("Rate limiting system initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize rate limiting: {e}")
    rate_limiter = None

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

# Register API endpoints with rate limiting
register_api_endpoints(app)

# Add rate limit headers to all responses
@app.after_request
def after_request(response):
    """Add rate limit headers to all responses"""
    return add_rate_limit_headers(response)

@app.route('/health', methods=['GET'])
def health_check():
    """Enhanced health check endpoint for deployment monitoring"""
    try:
        # Check database connection
        db_status = db_config.test_connection()
        
        # Check cache status
        cache_status = 'connected' if cache_manager else 'disconnected'
        
        # Check queue status
        queue_status = 'active' if batch_processor else 'inactive'
        
        # Check disk space
        import shutil
        disk_usage = shutil.disk_usage('/')
        disk_free_percent = (disk_usage.free / disk_usage.total) * 100
        
        # Check memory usage
        import psutil
        memory = psutil.virtual_memory()
        memory_usage_percent = memory.percent
        
        # Overall health determination
        overall_healthy = (
            db_status and 
            disk_free_percent > 10 and 
            memory_usage_percent < 90
        )
        
        health_data = {
            'status': 'healthy' if overall_healthy else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'database': 'connected' if db_status else 'disconnected',
                'cache': cache_status,
                'queue': queue_status,
                'disk_space': {
                    'free_percent': round(disk_free_percent, 2),
                    'free_gb': round(disk_usage.free / (1024**3), 2),
                    'total_gb': round(disk_usage.total / (1024**3), 2)
                },
                'memory': {
                    'usage_percent': memory_usage_percent,
                    'available_gb': round(memory.available / (1024**3), 2),
                    'total_gb': round(memory.total / (1024**3), 2)
                }
            },
            'version': get_config_value('app.version', '1.0.0'),
            'environment': config.environment,
            'deployment_color': os.getenv('DEPLOYMENT_COLOR', 'unknown'),
            'deployment_id': os.getenv('DEPLOYMENT_ID', 'unknown')
        }
        
        status_code = 200 if overall_healthy else 503
        return jsonify(health_data), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'version': get_config_value('app.version', '1.0.0'),
            'environment': config.environment
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

# Note: The /predict endpoint is now handled by api_endpoints.py with rate limiting
# This route is kept for backward compatibility but redirects to the new endpoint
@app.route('/predict', methods=['POST'])
def predict_legacy():
    """Legacy prediction endpoint - redirects to new rate-limited endpoint"""
    return jsonify({
        'message': 'This endpoint is deprecated. Please use /api/v1/predict instead.',
        'new_endpoint': '/api/v1/predict',
        'documentation': 'See API documentation for rate limiting details'
    }), 301

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

# Deployment monitoring endpoints
@app.route('/deployment/status', methods=['GET'])
def deployment_status():
    """Get deployment status information"""
    try:
        import psutil
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get application metrics
        queue_stats = batch_processor.get_queue_stats() if batch_processor else {}
        cache_stats = cache_manager.get_comprehensive_stats() if cache_manager else {}
        
        deployment_info = {
            'deployment': {
                'id': os.getenv('DEPLOYMENT_ID', 'unknown'),
                'color': os.getenv('DEPLOYMENT_COLOR', 'unknown'),
                'environment': config.environment,
                'version': get_config_value('app.version', '1.0.0'),
                'start_time': datetime.now().isoformat(),
                'uptime_seconds': time.time() - psutil.boot_time()
            },
            'system': {
                'cpu_percent': cpu_percent,
                'memory': {
                    'total_gb': round(memory.total / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'usage_percent': memory.percent,
                    'used_gb': round(memory.used / (1024**3), 2)
                },
                'disk': {
                    'total_gb': round(disk.total / (1024**3), 2),
                    'free_gb': round(disk.free / (1024**3), 2),
                    'usage_percent': round((disk.used / disk.total) * 100, 2),
                    'used_gb': round(disk.used / (1024**3), 2)
                }
            },
            'application': {
                'queue_stats': queue_stats,
                'cache_stats': cache_stats,
                'database_connected': db_config.test_connection() if db_config else False
            }
        }
        
        return jsonify(deployment_info), 200
        
    except Exception as e:
        logger.error(f"Failed to get deployment status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/deployment/metrics', methods=['GET'])
def deployment_metrics():
    """Get detailed deployment metrics for monitoring"""
    try:
        import psutil
        
        # Process-specific metrics
        process = psutil.Process()
        
        metrics = {
            'flask_http_request_duration_seconds': [
                {
                    'quantile': '0.5',
                    'value': 0.1  # Placeholder - would need actual timing
                },
                {
                    'quantile': '0.95',
                    'value': 0.3  # Placeholder - would need actual timing
                },
                {
                    'quantile': '0.99',
                    'value': 0.5  # Placeholder - would need actual timing
                }
            ],
            'flask_http_request_total': [
                {
                    'method': 'GET',
                    'endpoint': '/health',
                    'status': '200',
                    'value': 100  # Placeholder - would need actual counter
                }
            ],
            'flask_http_request_exceptions_total': [
                {
                    'method': 'POST',
                    'endpoint': '/predict',
                    'status': '500',
                    'value': 5  # Placeholder - would need actual counter
                }
            ],
            'flask_database_connections': 1 if db_config and db_config.test_connection() else 0,
            'flask_database_query_duration_seconds': [
                {
                    'quantile': '0.95',
                    'value': 0.05  # Placeholder
                }
            ],
            'cache_hits_total': cache_stats.get('hits', 0) if cache_manager else 0,
            'cache_misses_total': cache_stats.get('misses', 0) if cache_manager else 0,
            'queue_pending_tasks': queue_stats.get('pending_tasks', 0) if batch_processor else 0,
            'queue_running_tasks': queue_stats.get('running_tasks', 0) if batch_processor else 0,
            'queue_completed_tasks': queue_stats.get('completed_tasks', 0) if batch_processor else 0,
            'queue_failed_tasks': queue_stats.get('failed_tasks', 0) if batch_processor else 0,
            'process_resident_memory_bytes': process.memory_info().rss,
            'process_cpu_seconds_total': process.cpu_times().user + process.cpu_times().system,
            'process_num_threads': process.num_threads(),
            'up': 1,  # Application is up
            'flask_health_check_status': 1 if db_config and db_config.test_connection() else 0
        }
        
        return jsonify(metrics), 200
        
    except Exception as e:
        logger.error(f"Failed to get deployment metrics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/deployment/ready', methods=['GET'])
def readiness_check():
    """Readiness check for Kubernetes"""
    try:
        # Check if application is ready to serve traffic
        db_ready = db_config.test_connection() if db_config else False
        cache_ready = cache_manager is not None
        queue_ready = batch_processor is not None
        
        ready = db_ready and cache_ready and queue_ready
        
        if ready:
            return jsonify({
                'status': 'ready',
                'checks': {
                    'database': db_ready,
                    'cache': cache_ready,
                    'queue': queue_ready
                }
            }), 200
        else:
            return jsonify({
                'status': 'not_ready',
                'checks': {
                    'database': db_ready,
                    'cache': cache_ready,
                    'queue': queue_ready
                }
            }), 503
            
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({
            'status': 'not_ready',
            'error': str(e)
        }), 503

@app.route('/deployment/live', methods=['GET'])
def liveness_check():
    """Liveness check for Kubernetes"""
    try:
        # Simple liveness check - if we can respond, we're alive
        return jsonify({
            'status': 'alive',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return jsonify({
            'status': 'dead',
            'error': str(e)
        }), 500

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

@app.teardown_appcontext
def teardown_appcontext(exception=None):
    """Clean up resources when app context ends"""
    pass

# Register shutdown handlers
import atexit

def cleanup_resources():
    """Clean up all resources on shutdown"""
    logger.info("Cleaning up application resources...")
    
    # Shutdown rate limiter
    if rate_limiter:
        try:
            rate_limiter.shutdown()
            logger.info("Rate limiter shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down rate limiter: {e}")
    
    # Shutdown queue monitor
    if queue_monitor:
        try:
            queue_monitor.stop_monitoring()
            logger.info("Queue monitor shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down queue monitor: {e}")
    
    # Shutdown cache manager
    if cache_manager:
        try:
            cache_manager.shutdown()
            logger.info("Cache manager shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down cache manager: {e}")
    
    logger.info("Application cleanup complete")

# Register cleanup function
atexit.register(cleanup_resources)

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
