"""
Additional API endpoints for model management, A/B testing, and deployment
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
    from storage_handlers import StorageHandler, get_storage_handler, StorageConfig, StorageProvider
    from cdn_integration import CDNManager, get_cdn_manager, CDNConfig, CDNProvider
    from model_inference import ModelInference, get_model_inference, create_inference_request, InferenceMode
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

# Add these endpoints to the existing app.py file

def register_management_endpoints(app, model_registry, ab_test_manager, deployment_manager, model_validator):
    """Register model management endpoints"""
    
    @app.route('/api/models', methods=['GET'])
    def list_models():
        """List all registered models"""
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        models = model_registry.list_models(active_only)
        
        return jsonify({
            'models': [
                {
                    'version': m.version,
                    'created_at': m.created_at,
                    'created_by': m.created_by,
                    'description': m.description,
                    'accuracy': m.accuracy,
                    'loss': m.loss,
                    'epochs_trained': m.epochs_trained,
                    'is_active': m.is_active,
                    'is_stable': m.is_stable,
                    'tags': m.tags,
                    'model_path': m.model_path
                }
                for m in models
            ]
        })
    
    @app.route('/api/models/<version>', methods=['GET'])
    def get_model(version):
        """Get specific model details"""
        model = model_registry.get_model(version)
        if not model:
            return jsonify({'error': 'Model not found'}), 404
        
        return jsonify({
            'version': model.version,
            'created_at': model.created_at,
            'created_by': model.created_by,
            'description': model.description,
            'accuracy': model.accuracy,
            'loss': model.loss,
            'epochs_trained': model.epochs_trained,
            'dataset_version': model.dataset_version,
            'is_active': model.is_active,
            'is_stable': model.is_stable,
            'tags': model.tags,
            'hyperparameters': model.hyperparameters,
            'model_path': model.model_path,
            'model_hash': model.model_hash
        })
    
    @app.route('/api/models/register', methods=['POST'])
    def register_model():
        """Register a new model version"""
        data = request.get_json()
        
        required_fields = ['version', 'model_path', 'created_by', 'description']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        success = model_registry.register_model(
            version=data['version'],
            model_path=data['model_path'],
            created_by=data['created_by'],
            description=data['description'],
            accuracy=data.get('accuracy'),
            loss=data.get('loss'),
            epochs_trained=data.get('epochs_trained'),
            dataset_version=data.get('dataset_version'),
            tags=data.get('tags', []),
            hyperparameters=data.get('hyperparameters', {})
        )
        
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
            
            return jsonify({
                'test_id': test_id,
                'message': 'A/B test created successfully'
            }), 201
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ab-tests/<test_id>', methods=['GET'])
    def get_ab_test(test_id):
        """Get A/B test details"""
        try:
            summary = ab_test_manager.get_test_summary(test_id)
            return jsonify(summary)
        except Exception as e:
            return jsonify({'error': str(e)}), 404
    
    @app.route('/api/ab-tests/<test_id>/end', methods=['POST'])
    def end_ab_test(test_id):
        """End an A/B test"""
        data = request.get_json() or {}
        winner = data.get('winner')
        
        success = ab_test_manager.end_test(test_id, winner)
        if success:
            return jsonify({'message': f'A/B test {test_id} ended successfully'})
        else:
            return jsonify({'error': 'Failed to end A/B test'}), 500
    
    @app.route('/api/ab-tests/<test_id>/metrics', methods=['GET'])
    def get_ab_test_metrics(test_id):
        """Get A/B test metrics"""
        try:
            metrics_a, metrics_b = ab_test_manager.get_test_metrics(test_id)
            return jsonify({
                'model_a_metrics': {
                    'model_version': metrics_a.model_version,
                    'total_predictions': metrics_a.total_predictions,
                    'correct_predictions': metrics_a.correct_predictions,
                    'accuracy': metrics_a.accuracy,
                    'avg_confidence': metrics_a.avg_confidence,
                    'avg_processing_time': metrics_a.avg_processing_time,
                    'predictions_by_class': metrics_a.predictions_by_class
                },
                'model_b_metrics': {
                    'model_version': metrics_b.model_version,
                    'total_predictions': metrics_b.total_predictions,
                    'correct_predictions': metrics_b.correct_predictions,
                    'accuracy': metrics_b.accuracy,
                    'avg_confidence': metrics_b.avg_confidence,
                    'avg_processing_time': metrics_b.avg_processing_time,
                    'predictions_by_class': metrics_b.predictions_by_class
                }
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

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

def register_storage_endpoints(app):
    """Register storage management endpoints"""
    
    @app.route('/api/storage/upload', methods=['POST'])
    def upload_file():
        """Upload file to advanced storage"""
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            storage_tier = request.form.get('storage_tier', 'standard')
            metadata = json.loads(request.form.get('metadata', '{}'))
            
            storage_handler = get_storage_handler()
            
            # Read file data
            file_data = file.read()
            
            # Upload to storage
            result = asyncio.run(storage_handler.upload_file(
                file_data=file_data,
                filename=file.filename,
                content_type=file.content_type,
                metadata=metadata,
                storage_tier=StorageTier(storage_tier) if storage_tier in [t.value for t in StorageTier] else StorageTier.STANDARD
            ))
            
            return jsonify({
                'success': True,
                'filename': result.filename,
                'size_bytes': result.size_bytes,
                'cdn_url': result.cdn_url,
                'storage_tier': result.storage_tier.value,
                'etag': result.etag
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/storage/download/<path:object_key>', methods=['GET'])
    def download_file(object_key):
        """Download file from storage"""
        try:
            storage_handler = get_storage_handler()
            
            # Handle range requests
            range_header = request.headers.get('Range')
            
            file_data, metadata = asyncio.run(storage_handler.download_file(object_key, range_header))
            
            # Create response
            response = make_response(file_data)
            response.headers['Content-Type'] = metadata.content_type
            response.headers['Content-Length'] = str(len(file_data))
            response.headers['ETag'] = metadata.etag
            
            if range_header:
                # Handle partial content
                response.status_code = 206
                # Would need proper range parsing here
            
            return response
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/storage/files', methods=['GET'])
    def list_files():
        """List files in storage"""
        try:
            prefix = request.args.get('prefix', '')
            limit = int(request.args.get('limit', 100))
            
            storage_handler = get_storage_handler()
            files = asyncio.run(storage_handler.list_files(prefix, limit))
            
            return jsonify({
                'files': [
                    {
                        'filename': f.filename,
                        'size_bytes': f.size_bytes,
                        'content_type': f.content_type,
                        'storage_tier': f.storage_tier.value,
                        'upload_time': f.upload_time.isoformat(),
                        'cdn_url': f.cdn_url,
                        'etag': f.etag
                    }
                    for f in files
                ],
                'count': len(files)
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/storage/stats', methods=['GET'])
    def get_storage_stats():
        """Get storage statistics"""
        try:
            storage_handler = get_storage_handler()
            stats = asyncio.run(storage_handler.get_storage_stats())
            
            return jsonify({
                'total_files': stats.total_files,
                'total_size_gb': stats.total_size_gb,
                'upload_count': stats.upload_count,
                'download_count': stats.download_count,
                'delete_count': stats.delete_count,
                'bandwidth_used_gb': stats.bandwidth_used_bytes / (1024**3),
                'cost_estimate': stats.cost_estimate,
                'cache_hit_rate': stats.cache_hit_rate,
                'storage_by_tier': stats.storage_by_tier
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/storage/delete/<path:object_key>', methods=['DELETE'])
    def delete_file(object_key):
        """Delete file from storage"""
        try:
            storage_handler = get_storage_handler()
            success = asyncio.run(storage_handler.delete_file(object_key))
            
            if success:
                return jsonify({'message': 'File deleted successfully'})
            else:
                return jsonify({'error': 'Failed to delete file'}), 500
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500

def register_cdn_endpoints(app):
    """Register CDN management endpoints"""
    
    @app.route('/api/cdn/purge', methods=['POST'])
    def purge_cdn_cache():
        """Purge CDN cache"""
        try:
            data = request.get_json() or {}
            urls = data.get('urls', [])
            patterns = data.get('patterns', [])
            purge_type = data.get('purge_type', 'invalidate')
            
            cdn_manager = get_cdn_manager()
            purge_request = asyncio.run(cdn_manager.purge_cache(urls, patterns, purge_type))
            
            return jsonify({
                'status': purge_request.status,
                'created_at': purge_request.created_at.isoformat(),
                'completed_at': purge_request.completed_at.isoformat() if purge_request.completed_at else None,
                'urls_purged': len(purge_request.urls),
                'patterns_purged': len(purge_request.patterns)
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/cdn/analytics', methods=['GET'])
    def get_cdn_analytics():
        """Get CDN analytics"""
        try:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            if start_date:
                start_date = datetime.fromisoformat(start_date)
            if end_date:
                end_date = datetime.fromisoformat(end_date)
            
            cdn_manager = get_cdn_manager()
            stats = asyncio.run(cdn_manager.get_analytics(start_date, end_date))
            
            return jsonify({
                'total_requests': stats.total_requests,
                'cache_hits': stats.cache_hits,
                'cache_misses': stats.cache_misses,
                'hit_rate': stats.hit_rate,
                'bandwidth_saved_gb': stats.bandwidth_saved_bytes / (1024**3),
                'bandwidth_served_gb': stats.bandwidth_served_bytes / (1024**3),
                'average_response_time': stats.average_response_time,
                'error_rate': stats.error_rate,
                'cost_savings': stats.cost_savings,
                'top_files': stats.top_files,
                'geographic_distribution': stats.geographic_distribution
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/cdn/optimize', methods=['POST'])
    def optimize_image_delivery():
        """Optimize image delivery"""
        try:
            data = request.get_json()
            image_url = data.get('image_url')
            device_type = data.get('device_type', 'desktop')
            
            if not image_url:
                return jsonify({'error': 'image_url is required'}), 400
            
            cdn_manager = get_cdn_manager()
            optimization = asyncio.run(cdn_manager.optimize_image_delivery(image_url, device_type))
            
            return jsonify(optimization)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/cdn/metrics', methods=['GET'])
    def get_real_time_metrics():
        """Get real-time CDN metrics"""
        try:
            cdn_manager = get_cdn_manager()
            metrics = asyncio.run(cdn_manager.get_real_time_metrics())
            
            return jsonify(metrics)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

def register_utility_endpoints(app):
    """Register utility endpoints"""
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Basic health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0'  # Updated version with model management
        })
    
    @app.route('/api/classes', methods=['GET'])
    def get_classes():
        """Get supported food classes"""
        return jsonify({
            'classes': ['Akara', 'Bread', 'Egusi', 'Moi Moi', 'Rice and Stew', 'Yam'],
            'count': 6
        })
    
    @app.route('/api/validation/history', methods=['GET'])
    def validation_history():
        """Get validation history"""
        model_version = request.args.get('model_version')
        limit = request.args.get('limit', 50, type=int)
        
        # This would need access to model_validator
        # For now, return empty response
        return jsonify({'history': []})

    @app.route('/api/history', methods=['GET'])
    def prediction_history():
        """Get prediction history with optional filters"""
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Database not configured'}), 503
        try:
            user_id = request.args.get('user_id')
            label = request.args.get('label')
            model_version = request.args.get('model_version')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            limit = request.args.get('limit', type=int) or 50
            offset = request.args.get('offset', type=int) or 0
            clauses = []
            params = []
            if user_id:
                clauses.append("user_id = %s")
                params.append(user_id)
            if label:
                clauses.append("label = %s")
                params.append(label)
            if model_version:
                clauses.append("model_version = %s")
                params.append(model_version)
            if start_date:
                clauses.append("created_at >= %s")
                params.append(start_date)
            if end_date:
                clauses.append("created_at <= %s")
                params.append(end_date)
            where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
            with conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        SELECT id::text, request_id, user_id, image_filename, label, confidence,
                               all_predictions::text, processing_time, model_version, success,
                               error_message, created_at
                        FROM prediction_history
                        {where}
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """, (*params, limit, offset))
                    rows = cur.fetchall() or []
            items = []
            for r in rows:
                items.append({
                    'id': r[0],
                    'request_id': r[1],
                    'user_id': r[2],
                    'image_filename': r[3],
                    'label': r[4],
                    'confidence': r[5],
                    'all_predictions': json.loads(r[6]) if r[6] else [],
                    'processing_time': r[7],
                    'model_version': r[8],
                    'success': r[9],
                    'error_message': r[10],
                    'created_at': r[11].isoformat() if r[11] else None
                })
            return jsonify({'items': items, 'count': len(items), 'limit': limit, 'offset': offset})
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @app.route('/api/history/<id>', methods=['GET'])
    def prediction_history_item(id):
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Database not configured'}), 503
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id::text, request_id, user_id, image_filename, label, confidence,
                               all_predictions::text, processing_time, model_version, success,
                               error_message, created_at
                        FROM prediction_history
                        WHERE id = %s
                        """, (id,))
                    r = cur.fetchone()
                    if not r:
                        return jsonify({'error': 'Not found'}), 404
            item = {
                'id': r[0],
                'request_id': r[1],
                'user_id': r[2],
                'image_filename': r[3],
                'label': r[4],
                'confidence': r[5],
                'all_predictions': json.loads(r[6]) if r[6] else [],
                'processing_time': r[7],
                'model_version': r[8],
                'success': r[9],
                'error_message': r[10],
                'created_at': r[11].isoformat() if r[11] else None
            }
            return jsonify(item)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @app.route('/api/metrics/model', methods=['GET'])
    def model_metrics():
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Database not configured'}), 503
        try:
            model_version = request.args.get('model_version')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            clauses = []
            params = []
            if model_version:
                clauses.append("model_version = %s")
                params.append(model_version)
            if start_date:
                clauses.append("metric_date >= %s")
                params.append(start_date)
            if end_date:
                clauses.append("metric_date <= %s")
                params.append(end_date)
            where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
            with conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        SELECT model_version, metric_date, total_predictions, avg_confidence, avg_processing_time
                        FROM model_performance_metrics
                        {where}
                        ORDER BY metric_date DESC, model_version
                    """, (*params,))
                    rows = cur.fetchall() or []
            items = []
            for r in rows:
                items.append({
                    'model_version': r[0],
                    'date': r[1].isoformat(),
                    'total_predictions': r[2],
                    'avg_confidence': float(r[3]) if r[3] is not None else None,
                    'avg_processing_time': float(r[4]) if r[4] is not None else None
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
    register_validation_endpoints(app)
    register_search_endpoints(app)
    register_storage_endpoints(app)
    register_cdn_endpoints(app)
    
    # Initialize search index on startup
    try:
        index_database_documents()
    except Exception as e:
        print(f"Warning: Failed to initialize search index: {e}")
