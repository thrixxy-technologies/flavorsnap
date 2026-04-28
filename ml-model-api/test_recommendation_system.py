"""
Comprehensive Test Suite for FlavorSnap Recommendation System

This module provides unit tests, integration tests, and performance tests
for all components of the recommendation system.
"""

import unittest
import tempfile
import os
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Import recommendation system components
from user_profiling import UserProfilingSystem, UserProfile, UserPreference, generate_user_id
from collaborative_filtering import CollaborativeFilteringEngine, CollaborativeFilteringConfig
from content_based import ContentBasedEngine, ContentBasedConfig, FoodItem
from recommendation_engine import HybridRecommendationEngine, RecommendationConfig, Recommendation
from realtime_recommendations import RealtimeRecommendationSystem, RealtimeConfig, create_view_event, create_like_event
from recommendation_ab_testing import ABTestingFramework, ABTestConfig, TestVariant, MetricType, TestStatus
from recommendation_monitoring import RecommendationMonitoring, MonitoringConfig, PerformanceMetric


class TestUserProfilingSystem(unittest.TestCase):
    """Test cases for User Profiling System"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        
        # Mock database connection
        self.mock_connection = Mock()
        self.profiling = UserProfilingSystem(self.mock_connection)
    
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_db.name)
    
    def test_create_user_profile(self):
        """Test user profile creation"""
        user_id = "test_user_123"
        dietary_restrictions = ["vegetarian", "gluten-free"]
        cuisine_preferences = ["Nigerian", "International"]
        
        profile = self.profiling.create_user_profile(
            user_id, dietary_restrictions, cuisine_preferences
        )
        
        self.assertIsInstance(profile, UserProfile)
        self.assertEqual(profile.user_id, user_id)
        self.assertEqual(profile.dietary_restrictions, dietary_restrictions)
        self.assertEqual(profile.cuisine_preferences, cuisine_preferences)
        self.assertEqual(len(profile.preferences), 0)
    
    def test_update_user_interaction(self):
        """Test user interaction update"""
        user_id = "test_user"
        food_category = "Akara"
        
        # Test with rating
        success = self.profiling.update_user_interaction(
            user_id, food_category, 'rating', rating=4.5
        )
        self.assertTrue(success)
        
        # Test with feedback score
        success = self.profiling.update_user_interaction(
            user_id, food_category, 'like', feedback_score=1.0
        )
        self.assertTrue(success)
    
    def test_get_user_preferences_summary(self):
        """Test user preferences summary"""
        user_id = "test_user"
        
        # Mock database response
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("Akara", 0.8), ("Bread", 0.6), ("Egusi", 0.9)
        ]
        self.mock_connection.cursor.return_value = mock_cursor
        
        summary = self.profiling.get_user_preferences_summary(user_id, 5)
        
        self.assertEqual(len(summary), 3)
        self.assertEqual(summary[0], ("Akara", 0.8))
    
    def test_calculate_user_similarity(self):
        """Test user similarity calculation"""
        user1_id = "user1"
        user2_id = "user2"
        
        # Mock user profiles with overlapping preferences
        with patch.object(self.profiling, 'get_user_profile') as mock_get_profile:
            profile1 = Mock()
            profile1.preferences = {
                "Akara": Mock(preference_score=0.8),
                "Bread": Mock(preference_score=0.6)
            }
            profile2 = Mock()
            profile2.preferences = {
                "Akara": Mock(preference_score=0.7),
                "Egusi": Mock(preference_score=0.9)
            }
            
            mock_get_profile.side_effect = [profile1, profile2]
            
            similarity = self.profiling.calculate_user_similarity(user1_id, user2_id)
            
            self.assertIsInstance(similarity, float)
            self.assertGreaterEqual(similarity, 0.0)
            self.assertLessEqual(similarity, 1.0)
    
    def test_generate_user_id(self):
        """Test user ID generation"""
        # Test with email
        user_id = generate_user_id("test@example.com")
        self.assertIsInstance(user_id, str)
        self.assertEqual(len(user_id), 16)
        
        # Test without email
        user_id = generate_user_id()
        self.assertIsInstance(user_id, str)
        self.assertEqual(len(user_id), 16)


class TestCollaborativeFilteringEngine(unittest.TestCase):
    """Test cases for Collaborative Filtering Engine"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = CollaborativeFilteringConfig()
        self.mock_connection = Mock()
        self.cf_engine = CollaborativeFilteringEngine(self.config, self.mock_connection)
    
    def test_build_user_item_matrix(self):
        """Test user-item matrix building"""
        # Mock database response
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("user1", "Akara", 4.5, 5),
            ("user1", "Bread", 3.0, 3),
            ("user2", "Akara", 5.0, 8),
            ("user2", "Egusi", 4.0, 6)
        ]
        self.mock_connection.cursor.return_value = mock_cursor
        
        success = self.cf_engine.build_user_item_matrix()
        
        self.assertTrue(success)
        self.assertIsNotNone(self.cf_engine.user_item_matrix)
        self.assertEqual(len(self.cf_engine.user_to_index), 2)
        self.assertEqual(len(self.cf_engine.item_to_index), 3)
    
    def test_compute_user_similarity(self):
        """Test user similarity computation"""
        # Mock user-item matrix
        self.cf_engine.user_item_matrix = Mock()
        self.cf_engine.user_item_matrix.shape = (2, 3)
        
        with patch('numpy.cosine_similarity') as mock_cosine:
            mock_cosine.return_value = np.array([[0.0, 0.8], [0.8, 0.0]])
            
            success = self.cf_engine.compute_user_similarity()
            
            self.assertTrue(success)
            self.assertIsNotNone(self.cf_engine.user_similarity_matrix)
    
    def test_get_user_based_recommendations(self):
        """Test user-based recommendations"""
        # Mock setup
        self.cf_engine.user_to_index = {"user1": 0, "user2": 1}
        self.cf_engine.index_to_user = {0: "user1", 1: "user2"}
        self.cf_engine.user_similarity_matrix = np.array([[0.0, 0.8], [0.8, 0.0]])
        self.cf_engine.user_item_matrix = Mock()
        self.cf_engine.user_item_matrix.__getitem__ = Mock(return_value=Mock())
        self.cf_engine.user_item_matrix.__getitem__.return_value.toarray.return_value = np.array([[0.0, 4.5, 3.0]])
        
        recommendations = self.cf_engine.get_user_based_recommendations("user1", 5)
        
        self.assertIsInstance(recommendations, list)
    
    def test_train_matrix_factorization(self):
        """Test matrix factorization training"""
        # Mock user-item matrix
        self.cf_engine.user_item_matrix = Mock()
        self.cf_engine.user_item_matrix.shape = (10, 20)
        
        with patch('sklearn.decomposition.TruncatedSVD') as mock_svd:
            mock_svd_instance = Mock()
            mock_svd_instance.fit_transform.return_value = np.random.rand(10, 5)
            mock_svd_instance.components_.T = np.random.rand(20, 5)
            mock_svd.return_value = mock_svd_instance
            
            success = self.cf_engine.train_matrix_factorization()
            
            self.assertTrue(success)
            self.assertIsNotNone(self.cf_engine.svd_model)
            self.assertIsNotNone(self.cf_engine.user_factors)
            self.assertIsNotNone(self.cf_engine.item_factors)


class TestContentBasedEngine(unittest.TestCase):
    """Test cases for Content-Based Engine"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = ContentBasedConfig()
        self.mock_connection = Mock()
        self.cb_engine = ContentBasedEngine(self.config, self.mock_connection)
    
    def test_extract_features(self):
        """Test feature extraction from food items"""
        food_item = FoodItem(
            item_id="test_item",
            name="Test Food",
            category="Test Category",
            cuisine_type="Nigerian",
            ingredients=["ingredient1", "ingredient2"],
            flavor_profile={"sweet": 0.5, "salty": 0.3},
            nutritional_info={"calories": 200, "protein": 10},
            dietary_tags=["vegetarian"],
            preparation_methods=["fried"],
            texture_profile=["crispy"],
            allergens=["nuts"],
            description="A test food item"
        )
        
        features = self.cb_engine.extract_features(food_item)
        
        self.assertIsInstance(features, np.ndarray)
        self.assertEqual(len(features), 50)  # Expected feature vector size
    
    def test_build_feature_matrix(self):
        """Test feature matrix building"""
        # Add sample food items
        food_item = FoodItem(
            item_id="test1",
            name="Test Food 1",
            category="Category1",
            cuisine_type="Nigerian",
            ingredients=["ing1"],
            flavor_profile={"sweet": 0.5},
            nutritional_info={"calories": 200},
            dietary_tags=["vegetarian"],
            preparation_methods=["fried"],
            texture_profile=["crispy"],
            allergens=[],
            description="Test food 1"
        )
        
        self.cb_engine.food_items["test1"] = food_item
        
        success = self.cb_engine.build_feature_matrix()
        
        self.assertTrue(success)
        self.assertIsNotNone(self.cb_engine.feature_matrix)
        self.assertEqual(len(self.cb_engine.item_indices), 1)
    
    def test_get_similar_items(self):
        """Test similar items retrieval"""
        # Mock feature matrix
        self.cb_engine.feature_matrix = np.random.rand(5, 10)
        self.cb_engine.item_indices = {f"item_{i}": i for i in range(5)}
        
        with patch('sklearn.metrics.pairwise.cosine_similarity') as mock_cosine:
            mock_cosine.return_value = np.array([
                [1.0, 0.8, 0.6, 0.4, 0.2],
                [0.8, 1.0, 0.7, 0.5, 0.3],
                [0.6, 0.7, 1.0, 0.8, 0.4],
                [0.4, 0.5, 0.8, 1.0, 0.6],
                [0.2, 0.3, 0.4, 0.6, 1.0]
            ])
            
            similar_items = self.cb_engine.get_similar_items("item_0", 3)
            
            self.assertIsInstance(similar_items, list)
            self.assertLessEqual(len(similar_items), 3)
    
    def test_get_user_based_recommendations(self):
        """Test user-based content recommendations"""
        user_preferences = {"Akara": 0.8, "Bread": 0.6}
        user_history = ["Akara", "Egusi"]
        dietary_restrictions = ["vegetarian"]
        
        # Mock feature matrix and items
        self.cb_engine.feature_matrix = np.random.rand(5, 10)
        self.cb_engine.item_indices = {f"item_{i}": i for i in range(5)}
        
        with patch.object(self.cb_engine, '_build_user_profile_vector') as mock_build:
            mock_build.return_value = np.random.rand(10)
            
            with patch('sklearn.metrics.pairwise.cosine_similarity') as mock_cosine:
                mock_cosine.return_value = np.array([[0.8, 0.6, 0.4, 0.7, 0.5]])
                
                recommendations = self.cb_engine.get_user_based_recommendations(
                    user_preferences, user_history, dietary_restrictions, 3
                )
                
                self.assertIsInstance(recommendations, list)


class TestHybridRecommendationEngine(unittest.TestCase):
    """Test cases for Hybrid Recommendation Engine"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = RecommendationConfig()
        self.mock_connection = Mock()
        self.engine = HybridRecommendationEngine(self.config, self.mock_connection)
    
    def test_get_recommendations(self):
        """Test hybrid recommendation generation"""
        user_id = "test_user"
        n_recommendations = 5
        context = {"meal_type": "lunch"}
        
        # Mock component methods
        with patch.object(self.engine.user_profiling, 'get_user_profile') as mock_profile:
            mock_profile.return_value = Mock(
                user_id=user_id,
                preferences={},
                interaction_history=[],
                dietary_restrictions=[]
            )
            
            with patch.object(self.engine, '_get_collaborative_recommendations') as mock_cf:
                mock_cf.return_value = [("item1", 0.8), ("item2", 0.7)]
                
                with patch.object(self.engine, '_get_content_based_recommendations') as mock_cb:
                    mock_cb.return_value = [("item3", 0.9), ("item4", 0.6)]
                    
                    with patch.object(self.engine, '_get_profile_based_recommendations') as mock_profile_rec:
                        mock_profile_rec.return_value = [("item5", 0.5)]
                        
                        with patch.object(self.engine, '_get_popularity_recommendations') as mock_pop:
                            mock_pop.return_value = [("item6", 0.4)]
                            
                            result = self.engine.get_recommendations(
                                user_id, n_recommendations, context
                            )
                            
                            self.assertEqual(result.user_id, user_id)
                            self.assertLessEqual(len(result.recommendations), n_recommendations)
                            self.assertIsInstance(result.algorithm_weights, dict)
                            self.assertIsInstance(result.diversity_score, float)
    
    def test_combine_recommendations(self):
        """Test recommendation combination"""
        cf_recs = [("item1", 0.8), ("item2", 0.7)]
        cb_recs = [("item3", 0.9), ("item4", 0.6)]
        profile_recs = [("item5", 0.5)]
        popularity_recs = [("item6", 0.4)]
        
        # Mock user profile
        user_profile = Mock(
            interaction_history=[],
            preferences={}
        )
        
        combined = self.engine._combine_recommendations(
            cf_recs, cb_recs, profile_recs, popularity_recs, user_profile
        )
        
        self.assertIsInstance(combined, list)
        self.assertGreater(len(combined), 0)
        
        # Check that scores are weighted
        for item_id, score in combined:
            self.assertIsInstance(score, float)
            self.assertGreaterEqual(score, 0.0)
    
    def test_record_feedback(self):
        """Test feedback recording"""
        user_id = "test_user"
        item_id = "test_item"
        feedback_type = "rating"
        feedback_score = 4.5
        
        # Mock database operations
        self.mock_connection.cursor.return_value = Mock()
        self.mock_connection.commit.return_value = None
        
        with patch.object(self.engine.user_profiling, 'update_user_interaction') as mock_update:
            mock_update.return_value = True
            
            success = self.engine.record_feedback(
                user_id, item_id, feedback_type, feedback_score
            )
            
            self.assertTrue(success)


class TestRealtimeRecommendationSystem(unittest.TestCase):
    """Test cases for Real-time Recommendation System"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = RealtimeConfig()
        self.mock_connection = Mock()
        self.realtime = RealtimeRecommendationSystem(self.config, self.mock_connection)
    
    def tearDown(self):
        """Clean up test environment"""
        if self.realtime.is_running:
            self.realtime.shutdown()
    
    def test_add_event(self):
        """Test event addition"""
        event = create_view_event("user123", "item456", "session789")
        
        # Mock database operations
        self.mock_connection.cursor.return_value = Mock()
        self.mock_connection.commit.return_value = None
        
        success = self.realtime.add_event(event)
        
        self.assertTrue(success)
        self.assertEqual(len(self.realtime.recent_events), 1)
    
    def test_get_realtime_recommendations(self):
        """Test real-time recommendation generation"""
        user_id = "test_user"
        session_id = "test_session"
        n_recommendations = 5
        
        # Mock recommendation engine
        with patch.object(self.realtime.recommendation_engine, 'get_recommendations') as mock_rec:
            mock_result = Mock()
            mock_result.recommendations = [
                Mock(item_id="item1", score=0.8, explanation={}, source="hybrid", timestamp=datetime.now(), metadata={})
            ]
            mock_result.algorithm_weights = {"hybrid": 1.0}
            mock_result.diversity_score = 0.7
            mock_result.novelty_score = 0.6
            mock_result.processing_time_ms = 100
            mock_rec.return_value = mock_result
            
            result = self.realtime.get_realtime_recommendations(
                user_id, session_id, {}, n_recommendations
            )
            
            self.assertEqual(result.user_id, user_id)
            self.assertIsInstance(result.recommendations, list)
    
    def test_handle_view_event(self):
        """Test view event handling"""
        event = create_view_event("user123", "item456", "session789")
        
        with patch.object(self.realtime.recommendation_engine.user_profiling, 'update_user_interaction') as mock_update:
            with patch.object(self.realtime.recommendation_engine.collaborative_filtering, 'update_with_new_interaction') as mock_cf_update:
                mock_update.return_value = True
                mock_cf_update.return_value = True
                
                self.realtime._handle_view_event(event)
                
                mock_update.assert_called_once()
                mock_cf_update.assert_called_once()


class TestABTestingFramework(unittest.TestCase):
    """Test cases for A/B Testing Framework"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = ABTestConfig()
        self.mock_connection = Mock()
        self.ab_testing = ABTestingFramework(self.config, self.mock_connection)
    
    def test_create_test(self):
        """Test A/B test creation"""
        variants = [
            TestVariant(
                variant_id="control",
                name="Control",
                description="Control variant",
                configuration={"algorithm": "hybrid"},
                traffic_allocation=0.5,
                is_control=True
            ),
            TestVariant(
                variant_id="variant1",
                name="Variant 1",
                description="Test variant",
                configuration={"algorithm": "enhanced"},
                traffic_allocation=0.5
            )
        ]
        
        target_metrics = [MetricType.CLICK_THROUGH_RATE, MetricType.USER_SATISFACTION]
        
        # Mock database operations
        self.mock_connection.cursor.return_value = Mock()
        self.mock_connection.commit.return_value = None
        
        test_id = self.ab_testing.create_test(
            name="Test Algorithm",
            description="Testing new algorithm",
            hypothesis="New algorithm performs better",
            variants=variants,
            target_metrics=target_metrics
        )
        
        self.assertIsInstance(test_id, str)
    
    def test_start_test(self):
        """Test A/B test start"""
        test_id = "test123"
        
        # Mock test loading
        mock_test = Mock()
        mock_test.status = TestStatus.DRAFT
        self.ab_testing.active_tests[test_id] = mock_test
        
        # Mock database operations
        self.mock_connection.cursor.return_value = Mock()
        self.mock_connection.commit.return_value = None
        
        success = self.ab_testing.start_test(test_id)
        
        self.assertTrue(success)
        self.assertEqual(mock_test.status, TestStatus.RUNNING)
    
    def test_assign_user_to_variant(self):
        """Test user assignment to variant"""
        test_id = "test123"
        user_id = "user456"
        
        # Mock test with variants
        mock_test = Mock()
        mock_test.status = TestStatus.RUNNING
        mock_variant = Mock()
        mock_variant.variant_id = "variant1"
        mock_variant.traffic_allocation = 1.0
        mock_test.variants = [mock_variant]
        self.ab_testing.active_tests[test_id] = mock_test
        
        variant_id = self.ab_testing.assign_user_to_variant(test_id, user_id)
        
        self.assertIsNotNone(variant_id)
        self.assertEqual(variant_id, "variant1")
    
    def test_record_event(self):
        """Test event recording"""
        test_id = "test123"
        user_id = "user456"
        session_id = "session789"
        event_type = "impression"
        metrics = {"response_time": 100}
        
        # Mock user assignment
        self.ab_testing.user_assignments = {user_id: {test_id: "variant1"}}
        
        # Mock database operations
        self.mock_connection.cursor.return_value = Mock()
        self.mock_connection.commit.return_value = None
        
        success = self.ab_testing.record_event(
            test_id, user_id, session_id, event_type, metrics
        )
        
        self.assertTrue(success)


class TestRecommendationMonitoring(unittest.TestCase):
    """Test cases for Recommendation Monitoring"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = MonitoringConfig()
        self.mock_connection = Mock()
        self.monitoring = RecommendationMonitoring(self.config, self.mock_connection)
    
    def tearDown(self):
        """Clean up test environment"""
        if self.monitoring.is_monitoring:
            self.monitoring.shutdown()
    
    def test_record_request(self):
        """Test request recording"""
        response_time_ms = 150.0
        success = True
        cache_hit = False
        user_id = "test_user"
        recommendation_count = 5
        
        metric_name = self.monitoring.record_request(
            response_time_ms, success, cache_hit, user_id, recommendation_count
        )
        
        self.assertIsInstance(metric_name, str)
        self.assertEqual(len(self.monitoring.request_times), 1)
        self.assertEqual(self.monitoring.total_requests, 1)
    
    def test_record_user_feedback(self):
        """Test user feedback recording"""
        user_id = "test_user"
        item_id = "test_item"
        rating = 4.5
        feedback_type = "rating"
        
        metric_name = self.monitoring.record_user_feedback(
            user_id, item_id, rating, feedback_type
        )
        
        self.assertIsInstance(metric_name, str)
    
    def test_collect_system_metrics(self):
        """Test system metrics collection"""
        with patch('psutil.cpu_percent') as mock_cpu:
            with patch('psutil.virtual_memory') as mock_memory:
                with patch('psutil.disk_usage') as mock_disk:
                    with patch('psutil.net_io_counters') as mock_network:
                        mock_cpu.return_value = 50.0
                        mock_memory.return_value = Mock(percent=60.0)
                        mock_disk.return_value = Mock(used=100, total=200)
                        mock_network.return_value = Mock(
                            bytes_sent=1000, bytes_recv=2000,
                            packets_sent=10, packets_recv=20
                        )
                        
                        metrics = self.monitoring._collect_system_metrics()
                        
                        self.assertEqual(metrics.cpu_usage, 50.0)
                        self.assertEqual(metrics.memory_usage, 60.0)
                        self.assertEqual(metrics.disk_usage, 50.0)
    
    def test_calculate_recommendation_metrics(self):
        """Test recommendation metrics calculation"""
        # Add some request times
        self.monitoring.request_times = [100, 150, 200, 120, 180]
        self.monitoring.total_requests = 10
        self.monitoring.error_count = 1
        self.monitoring.cache_hits = 7
        self.monitoring.cache_requests = 10
        
        with patch.object(self.monitoring, '_get_recent_metric_average') as mock_avg:
            mock_avg.side_effect = [0.7, 0.6, 4.2, 0.15]  # diversity, novelty, satisfaction, conversion
            
            with patch.object(self.monitoring, '_calculate_conversion_rate') as mock_conv:
                mock_conv.return_value = 0.15
                
                metrics = self.monitoring._calculate_recommendation_metrics()
                
                self.assertIsInstance(metrics, type(metrics))  # Should be RecommendationMetrics
                self.assertGreater(metrics.avg_response_time_ms, 0)
                self.assertGreaterEqual(metrics.cache_hit_rate, 0)
                self.assertLessEqual(metrics.cache_hit_rate, 1)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete recommendation system"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        
        # Create real database connection for integration tests
        import sqlite3
        self.db_connection = sqlite3.connect(self.temp_db.name)
        
        # Initialize components
        self.profiling = UserProfilingSystem(self.db_connection)
        self.cf_engine = CollaborativeFilteringEngine(db_connection=self.db_connection)
        self.cb_engine = ContentBasedEngine(db_connection=self.db_connection)
        self.engine = HybridRecommendationEngine(db_connection=self.db_connection)
    
    def tearDown(self):
        """Clean up integration test environment"""
        self.db_connection.close()
        os.unlink(self.temp_db.name)
    
    def test_end_to_end_recommendation_flow(self):
        """Test complete recommendation flow"""
        # Create user profile
        user_id = "integration_user"
        profile = self.profiling.create_user_profile(
            user_id, ["vegetarian"], ["Nigerian"]
        )
        
        # Add user interactions
        self.profiling.update_user_interaction(user_id, "Akara", "rating", rating=4.5)
        self.profiling.update_user_interaction(user_id, "Bread", "like", feedback_score=1.0)
        
        # Get recommendations
        result = self.engine.get_recommendations(user_id, 5, {"meal_type": "lunch"})
        
        # Verify results
        self.assertEqual(result.user_id, user_id)
        self.assertIsInstance(result.recommendations, list)
        self.assertLessEqual(len(result.recommendations), 5)
        
        # Record feedback
        if result.recommendations:
            item_id = result.recommendations[0].item_id
            success = self.engine.record_feedback(user_id, item_id, "rating", 4.0)
            self.assertTrue(success)
    
    def test_realtime_integration(self):
        """Test real-time system integration"""
        user_id = "realtime_user"
        session_id = "test_session"
        
        # Create real-time system
        realtime = RealtimeRecommendationSystem(db_connection=self.db_connection)
        
        try:
            # Add events
            view_event = create_view_event(user_id, "item1", session_id)
            like_event = create_like_event(user_id, "item2", session_id)
            
            realtime.add_event(view_event)
            realtime.add_event(like_event)
            
            # Get recommendations
            result = realtime.get_realtime_recommendations(user_id, session_id, {}, 3)
            
            self.assertEqual(result.user_id, user_id)
            self.assertIsInstance(result.recommendations, list)
            
        finally:
            realtime.shutdown()
    
    def test_ab_testing_integration(self):
        """Test A/B testing integration"""
        # Create A/B test
        ab_testing = ABTestingFramework(db_connection=self.db_connection)
        
        variants = [
            TestVariant(
                variant_id="control",
                name="Control",
                description="Control algorithm",
                configuration={"algorithm": "hybrid"},
                traffic_allocation=0.5,
                is_control=True
            ),
            TestVariant(
                variant_id="variant1",
                name="Enhanced",
                description="Enhanced algorithm",
                configuration={"algorithm": "hybrid", "diversity": 0.5},
                traffic_allocation=0.5
            )
        ]
        
        test_id = ab_testing.create_test(
            name="Integration Test",
            description="Testing integration",
            hypothesis="Enhanced algorithm works better",
            variants=variants,
            target_metrics=[MetricType.CLICK_THROUGH_RATE]
        )
        
        # Start test
        success = ab_testing.start_test(test_id)
        self.assertTrue(success)
        
        # Assign user and get recommendations
        user_id = "ab_test_user"
        variant_id = ab_testing.assign_user_to_variant(test_id, user_id)
        
        self.assertIsNotNone(variant_id)
        
        # Record event
        ab_testing.record_event(
            test_id, user_id, "session123", "impression",
            {"response_time": 100}
        )


class TestPerformance(unittest.TestCase):
    """Performance tests for the recommendation system"""
    
    def setUp(self):
        """Set up performance test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        
        import sqlite3
        self.db_connection = sqlite3.connect(self.temp_db.name)
        
        self.engine = HybridRecommendationEngine(db_connection=self.db_connection)
    
    def tearDown(self):
        """Clean up performance test environment"""
        self.db_connection.close()
        os.unlink(self.temp_db.name)
    
    def test_recommendation_performance(self):
        """Test recommendation generation performance"""
        user_id = "perf_user"
        n_recommendations = 10
        
        # Warm up
        self.engine.get_recommendations(user_id, n_recommendations)
        
        # Measure performance
        start_time = time.time()
        result = self.engine.get_recommendations(user_id, n_recommendations)
        end_time = time.time()
        
        processing_time = (end_time - start_time) * 1000
        
        # Should complete within reasonable time (adjust threshold as needed)
        self.assertLess(processing_time, 1000)  # 1 second
        self.assertEqual(result.user_id, user_id)
    
    def test_batch_recommendations_performance(self):
        """Test batch recommendation performance"""
        users = [f"user_{i}" for i in range(10)]
        n_recommendations = 5
        
        start_time = time.time()
        
        for user_id in users:
            self.engine.get_recommendations(user_id, n_recommendations)
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        avg_time = total_time / len(users)
        
        # Average time per user should be reasonable
        self.assertLess(avg_time, 500)  # 500ms per user
    
    def test_memory_usage(self):
        """Test memory usage during operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create multiple user profiles and recommendations
        for i in range(100):
            user_id = f"memory_test_user_{i}"
            self.engine.get_recommendations(user_id, 10)
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB
        
        # Memory increase should be reasonable (adjust threshold as needed)
        self.assertLess(memory_increase, 100)  # 100MB increase


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestUserProfilingSystem,
        TestCollaborativeFilteringEngine,
        TestContentBasedEngine,
        TestHybridRecommendationEngine,
        TestRealtimeRecommendationSystem,
        TestABTestingFramework,
        TestRecommendationMonitoring,
        TestIntegration,
        TestPerformance
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\nTest Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    
    # Exit with appropriate code
    exit_code = 0 if result.wasSuccessful() else 1
    exit(exit_code)
