"""
Recommendation API Endpoints for FlavorSnap

This module provides REST API endpoints for the recommendation system,
including user recommendations, feedback, A/B testing, and monitoring.
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import traceback
import uuid

# Import recommendation components
from recommendation_engine import HybridRecommendationEngine, RecommendationConfig
from realtime_recommendations import RealtimeRecommendationSystem, RealtimeConfig, create_view_event, create_like_event, create_rating_event
from recommendation_ab_testing import ABTestingFramework, ABTestConfig, MetricType, TestVariant
from recommendation_monitoring import RecommendationMonitoring, MonitoringConfig, record_recommendation_request, record_user_feedback
from user_profiling import UserProfilingSystem
from db_config import get_connection

logger = logging.getLogger(__name__)

class RecommendationAPI:
    """Main recommendation API class"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.recommendation_engine = None
        self.realtime_system = None
        self.ab_testing = None
        self.monitoring = None
        self.user_profiling = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize API with Flask app"""
        self.app = app
        
        # Initialize components
        db_connection = get_connection()
        
        self.recommendation_engine = HybridRecommendationEngine(db_connection=db_connection)
        self.realtime_system = RealtimeRecommendationSystem(db_connection=db_connection)
        self.ab_testing = ABTestingFramework(db_connection=db_connection)
        self.monitoring = RecommendationMonitoring(db_connection=db_connection)
        self.user_profiling = UserProfilingSystem(db_connection=db_connection)
        
        # Register routes
        self._register_routes()
        
        logger.info("Recommendation API initialized")
    
    def _register_routes(self):
        """Register API routes"""
        
        @self.app.route('/api/recommendations', methods=['GET'])
        def get_recommendations():
            """Get personalized recommendations for a user"""
            try:
                start_time = datetime.now()
                
                # Get parameters
                user_id = request.args.get('user_id')
                session_id = request.args.get('session_id', str(uuid.uuid4()))
                n_recommendations = int(request.args.get('n', 10))
                context = {}
                
                # Parse context parameters
                if 'meal_type' in request.args:
                    context['meal_type'] = request.args['meal_type']
                if 'time_of_day' in request.args:
                    context['time_of_day'] = request.args['time_of_day']
                if 'location' in request.args:
                    context['location'] = request.args['location']
                if 'occasion' in request.args:
                    context['occasion'] = request.args['occasion']
                
                # Validate parameters
                if not user_id:
                    return jsonify({'error': 'user_id is required'}), 400
                
                if n_recommendations < 1 or n_recommendations > 50:
                    return jsonify({'error': 'n must be between 1 and 50'}), 400
                
                # Check for A/B test assignment
                test_id = request.args.get('test_id')
                variant_id = None
                if test_id:
                    variant_id = self.ab_testing.assign_user_to_variant(test_id, user_id, context)
                    if variant_id:
                        # Get variant configuration
                        variant_config = self.ab_testing.get_variant_configuration(test_id, variant_id)
                        if variant_config:
                            # Apply variant configuration
                            config = RecommendationConfig(**variant_config.get('config', {}))
                            self.recommendation_engine.config = config
                
                # Get recommendations
                result = self.recommendation_engine.get_recommendations(
                    user_id, n_recommendations, context
                )
                
                # Record metrics
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                record_recommendation_request(
                    processing_time, True, result.cache_hit, user_id, len(result.recommendations)
                )
                
                # Record A/B test event
                if test_id and variant_id:
                    self.ab_testing.record_event(
                        test_id, user_id, session_id, 'impression',
                        {'response_time_ms': processing_time, 'recommendation_count': len(result.recommendations)}
                    )
                
                # Format response
                response = {
                    'user_id': user_id,
                    'session_id': session_id,
                    'recommendations': [
                        {
                            'item_id': rec.item_id,
                            'score': rec.score,
                            'explanation': rec.explanation,
                            'source': rec.source,
                            'metadata': rec.metadata
                        }
                        for rec in result.recommendations
                    ],
                    'algorithm_weights': result.algorithm_weights,
                    'diversity_score': result.diversity_score,
                    'novelty_score': result.novelty_score,
                    'processing_time_ms': result.processing_time_ms,
                    'cache_hit': result.cache_hit,
                    'explanation_summary': result.explanation_summary,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Add A/B test info if applicable
                if test_id and variant_id:
                    response['ab_test'] = {
                        'test_id': test_id,
                        'variant_id': variant_id
                    }
                
                return jsonify(response)
                
            except Exception as e:
                logger.error(f"Error in get_recommendations: {e}")
                record_recommendation_request(0, False, False, user_id, 0)
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/recommendations/realtime', methods=['GET'])
        def get_realtime_recommendations():
            """Get real-time recommendations"""
            try:
                start_time = datetime.now()
                
                # Get parameters
                user_id = request.args.get('user_id')
                session_id = request.args.get('session_id', str(uuid.uuid4()))
                n_recommendations = int(request.args.get('n', 10))
                context = {}
                
                # Parse context parameters
                for key in request.args:
                    if key not in ['user_id', 'session_id', 'n']:
                        context[key] = request.args[key]
                
                # Validate parameters
                if not user_id:
                    return jsonify({'error': 'user_id is required'}), 400
                
                if n_recommendations < 1 or n_recommendations > 50:
                    return jsonify({'error': 'n must be between 1 and 50'}), 400
                
                # Get real-time recommendations
                result = self.realtime_system.get_realtime_recommendations(
                    user_id, session_id, context, n_recommendations
                )
                
                # Record metrics
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                record_recommendation_request(
                    processing_time, True, result.cache_hit, user_id, len(result.recommendations)
                )
                
                # Format response
                response = {
                    'user_id': user_id,
                    'session_id': session_id,
                    'recommendations': [
                        {
                            'item_id': rec.item_id,
                            'score': rec.score,
                            'explanation': rec.explanation,
                            'source': rec.source,
                            'metadata': rec.metadata
                        }
                        for rec in result.recommendations
                    ],
                    'algorithm_weights': result.algorithm_weights,
                    'diversity_score': result.diversity_score,
                    'novelty_score': result.novelty_score,
                    'processing_time_ms': result.processing_time_ms,
                    'cache_hit': result.cache_hit,
                    'explanation_summary': result.explanation_summary,
                    'timestamp': datetime.now().isoformat(),
                    'realtime_features': {
                        'session_active': True,
                        'realtime_adjusted': True
                    }
                }
                
                return jsonify(response)
                
            except Exception as e:
                logger.error(f"Error in get_realtime_recommendations: {e}")
                record_recommendation_request(0, False, False, user_id, 0)
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/recommendations/feedback', methods=['POST'])
        def record_feedback():
            """Record user feedback on recommendations"""
            try:
                data = request.get_json()
                
                # Validate required fields
                required_fields = ['user_id', 'item_id', 'feedback_type']
                for field in required_fields:
                    if field not in data:
                        return jsonify({'error': f'{field} is required'}), 400
                
                user_id = data['user_id']
                item_id = data['item_id']
                feedback_type = data['feedback_type']
                rating = data.get('rating')
                feedback_score = data.get('feedback_score')
                session_id = data.get('session_id', str(uuid.uuid4()))
                metadata = data.get('metadata', {})
                
                # Validate feedback type
                valid_types = ['like', 'dislike', 'rating', 'purchase', 'click', 'view']
                if feedback_type not in valid_types:
                    return jsonify({'error': f'Invalid feedback_type. Must be one of: {valid_types}'}), 400
                
                # Record feedback in recommendation engine
                success = self.recommendation_engine.record_feedback(
                    user_id, item_id, feedback_type, rating or feedback_score or 0, metadata
                )
                
                if success:
                    # Record in monitoring
                    if rating:
                        record_user_feedback(user_id, item_id, rating, feedback_type)
                    
                    # Add real-time event if applicable
                    if feedback_type in ['like', 'dislike', 'rating', 'purchase']:
                        event_data = {
                            'user_id': user_id,
                            'item_id': item_id,
                            'session_id': session_id,
                            'context': metadata
                        }
                        
                        if feedback_type == 'like':
                            event = create_like_event(**event_data)
                        elif feedback_type == 'dislike':
                            event = create_like_event(**event_data)  # Use like event with negative score
                            event.metadata['feedback_score'] = -1.0
                        elif feedback_type == 'rating':
                            event = create_rating_event(user_id, item_id, rating, session_id, metadata)
                        elif feedback_type == 'purchase':
                            event = create_like_event(**event_data)
                            event.event_type = 'purchase'
                        
                        self.realtime_system.add_event(event)
                    
                    return jsonify({
                        'success': True,
                        'message': 'Feedback recorded successfully',
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({'error': 'Failed to record feedback'}), 500
                
            except Exception as e:
                logger.error(f"Error in record_feedback: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/recommendations/similar/<item_id>', methods=['GET'])
        def get_similar_items(item_id):
            """Get items similar to a given item"""
            try:
                n_similar = int(request.args.get('n', 10))
                algorithm = request.args.get('algorithm', 'content_based')
                
                if n_similar < 1 or n_similar > 50:
                    return jsonify({'error': 'n must be between 1 and 50'}), 400
                
                similar_items = []
                
                if algorithm == 'content_based':
                    similar_items = self.recommendation_engine.content_based.get_similar_items(item_id, n_similar)
                elif algorithm == 'collaborative':
                    similar_items = self.recommendation_engine.collaborative_filtering.get_similar_items(item_id, n_similar)
                else:
                    return jsonify({'error': 'Invalid algorithm. Use content_based or collaborative'}), 400
                
                response = {
                    'item_id': item_id,
                    'algorithm': algorithm,
                    'similar_items': [
                        {
                            'item_id': item_id,
                            'similarity_score': score
                        }
                        for item_id, score in similar_items
                    ],
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify(response)
                
            except Exception as e:
                logger.error(f"Error in get_similar_items: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/recommendations/users/<user_id>/profile', methods=['GET'])
        def get_user_profile(user_id):
            """Get user preference profile"""
            try:
                profile = self.user_profiling.get_user_profile(user_id)
                
                if not profile:
                    return jsonify({'error': 'User profile not found'}), 404
                
                # Get user statistics
                stats = self.user_profiling.get_user_statistics(user_id)
                
                response = {
                    'user_id': user_id,
                    'profile': {
                        'created_at': profile.created_at.isoformat(),
                        'updated_at': profile.updated_at.isoformat(),
                        'dietary_restrictions': profile.dietary_restrictions,
                        'cuisine_preferences': profile.cuisine_preferences,
                        'flavor_profile': profile.flavor_profile,
                        'total_interactions': len(profile.interaction_history)
                    },
                    'preferences': [
                        {
                            'category': category,
                            'preference_score': pref.preference_score,
                            'interaction_count': pref.interaction_count,
                            'avg_rating': pref.avg_rating
                        }
                        for category, pref in profile.preferences.items()
                    ],
                    'statistics': stats,
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify(response)
                
            except Exception as e:
                logger.error(f"Error in get_user_profile: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/recommendations/users/<user_id>/history', methods=['GET'])
        def get_user_history(user_id):
            """Get user interaction history"""
            try:
                limit = int(request.args.get('limit', 50))
                
                if limit < 1 or limit > 100:
                    return jsonify({'error': 'limit must be between 1 and 100'}), 400
                
                profile = self.user_profiling.get_user_profile(user_id)
                
                if not profile:
                    return jsonify({'error': 'User profile not found'}), 404
                
                # Get recent interactions
                recent_interactions = profile.interaction_history[:limit]
                
                response = {
                    'user_id': user_id,
                    'interactions': recent_interactions,
                    'total_interactions': len(profile.interaction_history),
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify(response)
                
            except Exception as e:
                logger.error(f"Error in get_user_history: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/ab-tests', methods=['GET'])
        def get_ab_tests():
            """Get all A/B tests"""
            try:
                tests = self.ab_testing.get_all_tests()
                
                response = {
                    'tests': tests,
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify(response)
                
            except Exception as e:
                logger.error(f"Error in get_ab_tests: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/ab-tests/<test_id>', methods=['GET'])
        def get_ab_test(test_id):
            """Get A/B test details and results"""
            try:
                summary = self.ab_testing.get_test_summary(test_id)
                
                if not summary:
                    return jsonify({'error': 'Test not found'}), 404
                
                return jsonify(summary)
                
            except Exception as e:
                logger.error(f"Error in get_ab_test: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/ab-tests', methods=['POST'])
        def create_ab_test():
            """Create a new A/B test"""
            try:
                data = request.get_json()
                
                # Validate required fields
                required_fields = ['name', 'description', 'hypothesis', 'variants', 'target_metrics']
                for field in required_fields:
                    if field not in data:
                        return jsonify({'error': f'{field} is required'}), 400
                
                # Create test variants
                variants = []
                for variant_data in data['variants']:
                    variant = TestVariant(
                        variant_id=str(uuid.uuid4()),
                        name=variant_data['name'],
                        description=variant_data.get('description', ''),
                        configuration=variant_data.get('configuration', {}),
                        traffic_allocation=variant_data.get('traffic_allocation', 0.5),
                        is_control=variant_data.get('is_control', False)
                    )
                    variants.append(variant)
                
                # Convert target metrics
                target_metrics = [MetricType(metric) for metric in data['target_metrics']]
                
                # Create test
                test_id = self.ab_testing.create_test(
                    name=data['name'],
                    description=data['description'],
                    hypothesis=data['hypothesis'],
                    variants=variants,
                    target_metrics=target_metrics,
                    duration_days=data.get('duration_days'),
                    sample_size=data.get('sample_size')
                )
                
                return jsonify({
                    'test_id': test_id,
                    'message': 'A/B test created successfully',
                    'timestamp': datetime.now().isoformat()
                }), 201
                
            except Exception as e:
                logger.error(f"Error in create_ab_test: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/ab-tests/<test_id>/start', methods=['POST'])
        def start_ab_test(test_id):
            """Start an A/B test"""
            try:
                success = self.ab_testing.start_test(test_id)
                
                if success:
                    return jsonify({
                        'message': 'A/B test started successfully',
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({'error': 'Failed to start test'}), 400
                
            except Exception as e:
                logger.error(f"Error in start_ab_test: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/ab-tests/<test_id>/stop', methods=['POST'])
        def stop_ab_test(test_id):
            """Stop an A/B test"""
            try:
                success = self.ab_testing.stop_test(test_id)
                
                if success:
                    return jsonify({
                        'message': 'A/B test stopped successfully',
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({'error': 'Failed to stop test'}), 400
                
            except Exception as e:
                logger.error(f"Error in stop_ab_test: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/monitoring/performance', methods=['GET'])
        def get_performance_summary():
            """Get performance monitoring summary"""
            try:
                hours = int(request.args.get('hours', 24))
                
                if hours < 1 or hours > 168:  # Max 7 days
                    return jsonify({'error': 'hours must be between 1 and 168'}), 400
                
                summary = self.monitoring.get_performance_summary(hours)
                
                return jsonify(summary)
                
            except Exception as e:
                logger.error(f"Error in get_performance_summary: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/monitoring/report', methods=['GET'])
        def get_performance_report():
            """Generate comprehensive performance report"""
            try:
                hours = int(request.args.get('hours', 24))
                
                if hours < 1 or hours > 168:
                    return jsonify({'error': 'hours must be between 1 and 168'}), 400
                
                report = self.monitoring.generate_performance_report(hours)
                
                return jsonify(report)
                
            except Exception as e:
                logger.error(f"Error in get_performance_report: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/monitoring/metrics/<metric_name>', methods=['GET'])
        def get_metric_history(metric_name):
            """Get historical data for a specific metric"""
            try:
                hours = int(request.args.get('hours', 24))
                
                if hours < 1 or hours > 168:
                    return jsonify({'error': 'hours must be between 1 and 168'}), 400
                
                history = self.monitoring.get_metric_history(metric_name, hours)
                
                response = {
                    'metric_name': metric_name,
                    'time_period_hours': hours,
                    'data': history,
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify(response)
                
            except Exception as e:
                logger.error(f"Error in get_metric_history: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/monitoring/top-items', methods=['GET'])
        def get_top_performing_items():
            """Get top performing items based on user feedback"""
            try:
                hours = int(request.args.get('hours', 24))
                limit = int(request.args.get('limit', 10))
                
                if hours < 1 or hours > 168:
                    return jsonify({'error': 'hours must be between 1 and 168'}), 400
                
                if limit < 1 or limit > 50:
                    return jsonify({'error': 'limit must be between 1 and 50'}), 400
                
                top_items = self.monitoring.get_top_performing_items(hours, limit)
                
                response = {
                    'time_period_hours': hours,
                    'top_items': top_items,
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify(response)
                
            except Exception as e:
                logger.error(f"Error in get_top_performing_items: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/recommendations/search', methods=['GET'])
        def search_items():
            """Search for food items by features"""
            try:
                # Get search parameters
                query = request.args.get('query', '')
                cuisine_type = request.args.get('cuisine_type')
                dietary_tags = request.args.getlist('dietary_tags')
                ingredients = request.args.getlist('ingredients')
                limit = int(request.args.get('limit', 20))
                
                if limit < 1 or limit > 50:
                    return jsonify({'error': 'limit must be between 1 and 50'}), 400
                
                # Search items
                matching_items = self.recommendation_engine.content_based.search_items_by_features(
                    cuisine_type=cuisine_type,
                    dietary_tags=dietary_tags,
                    ingredients=ingredients
                )
                
                # Limit results
                matching_items = matching_items[:limit]
                
                # Get item details
                items_with_details = []
                for item_id in matching_items:
                    item = self.recommendation_engine.content_based.get_item_details(item_id)
                    if item:
                        items_with_details.append({
                            'item_id': item.item_id,
                            'name': item.name,
                            'category': item.category,
                            'cuisine_type': item.cuisine_type,
                            'dietary_tags': item.dietary_tags,
                            'ingredients': item.ingredients,
                            'description': item.description
                        })
                
                response = {
                    'query': query,
                    'filters': {
                        'cuisine_type': cuisine_type,
                        'dietary_tags': dietary_tags,
                        'ingredients': ingredients
                    },
                    'items': items_with_details,
                    'total_count': len(items_with_details),
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify(response)
                
            except Exception as e:
                logger.error(f"Error in search_items: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/recommendations/items/<item_id>', methods=['GET'])
        def get_item_details(item_id):
            """Get detailed information about a specific item"""
            try:
                item = self.recommendation_engine.content_based.get_item_details(item_id)
                
                if not item:
                    return jsonify({'error': 'Item not found'}), 404
                
                response = {
                    'item_id': item.item_id,
                    'name': item.name,
                    'category': item.category,
                    'cuisine_type': item.cuisine_type,
                    'ingredients': item.ingredients,
                    'flavor_profile': item.flavor_profile,
                    'nutritional_info': item.nutritional_info,
                    'dietary_tags': item.dietary_tags,
                    'preparation_methods': item.preparation_methods,
                    'texture_profile': item.texture_profile,
                    'allergens': item.allergens,
                    'description': item.description,
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify(response)
                
            except Exception as e:
                logger.error(f"Error in get_item_details: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            try:
                # Check database connection
                db_available = get_connection() is not None
                
                # Check system components
                components = {
                    'recommendation_engine': self.recommendation_engine is not None,
                    'realtime_system': self.realtime_system is not None,
                    'ab_testing': self.ab_testing is not None,
                    'monitoring': self.monitoring is not None,
                    'user_profiling': self.user_profiling is not None,
                    'database': db_available
                }
                
                # Overall status
                all_healthy = all(components.values())
                
                response = {
                    'status': 'healthy' if all_healthy else 'unhealthy',
                    'timestamp': datetime.now().isoformat(),
                    'components': components,
                    'version': '1.0.0'
                }
                
                status_code = 200 if all_healthy else 503
                return jsonify(response), status_code
                
            except Exception as e:
                logger.error(f"Error in health_check: {e}")
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 503

# Flask app factory
def create_recommendation_app():
    """Create Flask app with recommendation API"""
    app = Flask(__name__)
    
    # Configure CORS
    CORS(app, 
         origins=['http://localhost:3000', 'https://yourdomain.com'],
         methods=['GET', 'POST', 'PUT', 'DELETE'],
         allow_headers=['Content-Type', 'Authorization'],
         supports_credentials=True)
    
    # Configure rate limiting
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        default_limits=["200 per minute", "1000 per hour"]
    )
    
    # Initialize API
    api = RecommendationAPI(app)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    return app

# Run the app
if __name__ == '__main__':
    app = create_recommendation_app()
    app.run(debug=True, host='0.0.0.0', port=5001)
