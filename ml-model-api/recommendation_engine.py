"""
Hybrid Recommendation Engine for FlavorSnap

This module combines collaborative filtering, content-based filtering,
and user profiling to provide comprehensive food recommendations.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict
import json
import numpy as np
from db_config import get_connection

# Import recommendation components
from user_profiling import UserProfilingSystem, UserProfile
from collaborative_filtering import CollaborativeFilteringEngine, CollaborativeFilteringConfig
from content_based import ContentBasedEngine, ContentBasedConfig, FoodItem

logger = logging.getLogger(__name__)

@dataclass
class RecommendationConfig:
    """Configuration for hybrid recommendation system"""
    # Weight configuration
    collaborative_weight: float = 0.4
    content_based_weight: float = 0.3
    user_profile_weight: float = 0.2
    popularity_weight: float = 0.1
    
    # Collaborative filtering weights
    cf_user_weight: float = 0.4
    cf_item_weight: float = 0.4
    cf_matrix_factorization_weight: float = 0.2
    
    # Diversity and novelty settings
    diversity_threshold: float = 0.3
    novelty_boost: float = 0.1
    serendipity_weight: float = 0.05
    
    # Recommendation limits
    max_recommendations: int = 50
    min_recommendations: int = 5
    fallback_recommendations: int = 10
    
    # Performance settings
    cache_duration_minutes: int = 30
    enable_caching: bool = True
    parallel_processing: bool = True

@dataclass
class Recommendation:
    """Recommendation data structure"""
    item_id: str
    score: float
    explanation: Dict[str, Any]
    source: str  # collaborative, content_based, hybrid, popularity
    timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class RecommendationResult:
    """Complete recommendation result"""
    user_id: str
    recommendations: List[Recommendation]
    algorithm_weights: Dict[str, float]
    diversity_score: float
    novelty_score: float
    processing_time_ms: float
    cache_hit: bool
    explanation_summary: str

class HybridRecommendationEngine:
    """Main hybrid recommendation engine"""
    
    def __init__(self, config: RecommendationConfig = None, db_connection=None):
        self.config = config or RecommendationConfig()
        self.db_connection = db_connection or get_connection()
        
        # Initialize component engines
        self.user_profiling = UserProfilingSystem(self.db_connection)
        self.collaborative_filtering = CollaborativeFilteringEngine(
            CollaborativeFilteringConfig(), self.db_connection
        )
        self.content_based = ContentBasedEngine(
            ContentBasedConfig(), self.db_connection
        )
        
        # Cache for recommendations
        self.recommendation_cache = {}
        self._init_database()
        
        # Pre-train models
        self._initialize_models()
    
    def _init_database(self):
        """Initialize recommendation engine database tables"""
        if not self.db_connection:
            logger.warning("No database connection available for recommendation engine")
            return
            
        try:
            cursor = self.db_connection.cursor()
            
            # Recommendations cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendation_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    recommendations BLOB,
                    algorithm_weights BLOB,
                    diversity_score REAL,
                    novelty_score REAL,
                    processing_time_ms REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    UNIQUE(user_id)
                )
            """)
            
            # Recommendation feedback table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendation_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    item_id TEXT,
                    recommendation_id TEXT,
                    feedback_type TEXT,
                    feedback_score REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # Algorithm performance tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS algorithm_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    algorithm_name TEXT,
                    user_id TEXT,
                    precision_score REAL,
                    recall_score REAL,
                    f1_score REAL,
                    diversity_score REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.db_connection.commit()
            logger.info("Recommendation engine database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize recommendation engine database: {e}")
    
    def _initialize_models(self):
        """Initialize and pre-train recommendation models"""
        try:
            logger.info("Initializing recommendation models...")
            
            # Build collaborative filtering matrices
            self.collaborative_filtering.build_user_item_matrix()
            self.collaborative_filtering.compute_user_similarity()
            self.collaborative_filtering.compute_item_similarity()
            self.collaborative_filtering.train_matrix_factorization()
            
            # Build content-based feature matrix
            self.content_based.build_feature_matrix()
            
            logger.info("Recommendation models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize recommendation models: {e}")
    
    def get_recommendations(self, user_id: str, n_recommendations: int = 10,
                           context: Dict[str, Any] = None) -> RecommendationResult:
        """Get hybrid recommendations for a user"""
        start_time = datetime.now()
        
        try:
            # Check cache first
            if self.config.enable_caching:
                cached_result = self._get_cached_recommendations(user_id, n_recommendations)
                if cached_result:
                    cached_result.cache_hit = True
                    return cached_result
            
            # Get user profile
            user_profile = self.user_profiling.get_user_profile(user_id)
            if not user_profile:
                # Create new user profile
                user_profile = self.user_profiling.create_user_profile(user_id)
            
            # Get recommendations from different algorithms
            cf_recs = self._get_collaborative_recommendations(user_id, n_recommendations * 2)
            cb_recs = self._get_content_based_recommendations(user_profile, n_recommendations * 2)
            profile_recs = self._get_profile_based_recommendations(user_profile, n_recommendations * 2)
            popularity_recs = self._get_popularity_recommendations(n_recommendations)
            
            # Combine recommendations using weighted approach
            combined_recs = self._combine_recommendations(
                cf_recs, cb_recs, profile_recs, popularity_recs, user_profile
            )
            
            # Apply diversity and novelty adjustments
            diversified_recs = self._apply_diversity_boost(combined_recs, user_profile)
            final_recs = self._apply_novelty_boost(diversified_recs, user_profile)
            
            # Generate explanations
            explained_recs = self._generate_explanations(final_recs, user_profile, context)
            
            # Calculate metrics
            diversity_score = self._calculate_diversity_score(explained_recs)
            novelty_score = self._calculate_novelty_score(explained_recs, user_profile)
            
            # Create recommendation objects
            recommendations = []
            for item_id, score, explanation in explained_recs[:n_recommendations]:
                recommendation = Recommendation(
                    item_id=item_id,
                    score=score,
                    explanation=explanation,
                    source=self._determine_primary_source(item_id, cf_recs, cb_recs, profile_recs),
                    timestamp=datetime.now(),
                    metadata={'context': context or {}}
                )
                recommendations.append(recommendation)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Create result
            result = RecommendationResult(
                user_id=user_id,
                recommendations=recommendations,
                algorithm_weights={
                    'collaborative': self.config.collaborative_weight,
                    'content_based': self.config.content_based_weight,
                    'user_profile': self.config.user_profile_weight,
                    'popularity': self.config.popularity_weight
                },
                diversity_score=diversity_score,
                novelty_score=novelty_score,
                processing_time_ms=processing_time,
                cache_hit=False,
                explanation_summary=self._generate_explanation_summary(recommendations)
            )
            
            # Cache the result
            if self.config.enable_caching:
                self._cache_recommendations(result)
            
            logger.info(f"Generated {len(recommendations)} recommendations for user {user_id} in {processing_time:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get recommendations for user {user_id}: {e}")
            return self._get_fallback_recommendations(user_id, n_recommendations)
    
    def _get_collaborative_recommendations(self, user_id: str, n_recommendations: int) -> List[Tuple[str, float]]:
        """Get collaborative filtering recommendations"""
        try:
            # Get hybrid CF recommendations
            cf_recs = self.collaborative_filtering.get_hybrid_cf_recommendations(
                user_id, n_recommendations,
                self.config.cf_user_weight,
                self.config.cf_item_weight,
                self.config.cf_matrix_factorization_weight
            )
            return cf_recs
            
        except Exception as e:
            logger.error(f"Failed to get collaborative recommendations: {e}")
            return []
    
    def _get_content_based_recommendations(self, user_profile: UserProfile, n_recommendations: int) -> List[Tuple[str, float]]:
        """Get content-based recommendations"""
        try:
            # Extract user preferences
            user_preferences = {cat: pref.preference_score 
                             for cat, pref in user_profile.preferences.items()}
            
            # Get user history
            user_history = [interaction['food_category'] 
                           for interaction in user_profile.interaction_history 
                           if interaction['food_category']]
            
            # Get content-based recommendations
            cb_recs = self.content_based.get_user_based_recommendations(
                user_preferences, user_history, 
                user_profile.dietary_restrictions, n_recommendations
            )
            return cb_recs
            
        except Exception as e:
            logger.error(f"Failed to get content-based recommendations: {e}")
            return []
    
    def _get_profile_based_recommendations(self, user_profile: UserProfile, n_recommendations: int) -> List[Tuple[str, float]]:
        """Get recommendations based on user profile preferences"""
        try:
            # Sort user preferences by score
            sorted_preferences = sorted(user_profile.preferences.items(), 
                                      key=lambda x: x[1].preference_score, reverse=True)
            
            recommendations = []
            for category, preference in sorted_preferences[:n_recommendations]:
                # Find items in this category
                category_items = self.content_based.search_items_by_features(cuisine_type=category)
                
                for item_id in category_items:
                    score = preference.preference_score * self.config.user_profile_weight
                    recommendations.append((item_id, score))
            
            return recommendations[:n_recommendations]
            
        except Exception as e:
            logger.error(f"Failed to get profile-based recommendations: {e}")
            return []
    
    def _get_popularity_recommendations(self, n_recommendations: int) -> List[Tuple[str, float]]:
        """Get popularity-based recommendations"""
        try:
            if not self.db_connection:
                return []
            
            cursor = self.db_connection.cursor()
            
            # Get most popular items by interaction count
            cursor.execute("""
                SELECT food_category, COUNT(*) as interaction_count,
                       AVG(CASE 
                           WHEN rating IS NOT NULL THEN rating 
                           WHEN feedback_score IS NOT NULL THEN (feedback_score + 1) * 2.5
                           ELSE 3.0
                       END) as avg_rating
                FROM user_interactions 
                WHERE food_category IS NOT NULL
                GROUP BY food_category
                ORDER BY interaction_count DESC, avg_rating DESC
                LIMIT ?
            """, (n_recommendations,))
            
            popular_items = cursor.fetchall()
            
            recommendations = []
            for item_id, count, avg_rating in popular_items:
                # Calculate popularity score
                score = (count / 1000) * 0.7 + (avg_rating / 5) * 0.3
                recommendations.append((item_id, score * self.config.popularity_weight))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get popularity recommendations: {e}")
            return []
    
    def _combine_recommendations(self, cf_recs: List[Tuple[str, float]], 
                                cb_recs: List[Tuple[str, float]],
                                profile_recs: List[Tuple[str, float]],
                                popularity_recs: List[Tuple[str, float]],
                                user_profile: UserProfile) -> List[Tuple[str, float]]:
        """Combine recommendations from different algorithms"""
        try:
            combined_scores = defaultdict(float)
            
            # Add collaborative filtering recommendations
            for item_id, score in cf_recs:
                combined_scores[item_id] += score * self.config.collaborative_weight
            
            # Add content-based recommendations
            for item_id, score in cb_recs:
                combined_scores[item_id] += score * self.config.content_based_weight
            
            # Add profile-based recommendations
            for item_id, score in profile_recs:
                combined_scores[item_id] += score * self.config.user_profile_weight
            
            # Add popularity recommendations
            for item_id, score in popularity_recs:
                combined_scores[item_id] += score * self.config.popularity_weight
            
            # Remove items the user has already interacted with
            user_history = set(interaction['food_category'] 
                             for interaction in user_profile.interaction_history 
                             if interaction['food_category'])
            
            for item_id in user_history:
                combined_scores.pop(item_id, None)
            
            # Sort by combined score
            sorted_recommendations = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
            
            return sorted_recommendations
            
        except Exception as e:
            logger.error(f"Failed to combine recommendations: {e}")
            return []
    
    def _apply_diversity_boost(self, recommendations: List[Tuple[str, float]], 
                            user_profile: UserProfile) -> List[Tuple[str, float]]:
        """Apply diversity boost to recommendations"""
        try:
            if len(recommendations) < 2:
                return recommendations
            
            # Calculate diversity for each item
            diversified_recs = []
            used_categories = set()
            
            for item_id, score in recommendations:
                item = self.content_based.get_item_details(item_id)
                if item and item.category not in used_categories:
                    # Boost diverse items
                    boosted_score = score * (1 + self.config.diversity_threshold)
                    diversified_recs.append((item_id, boosted_score))
                    used_categories.add(item.category)
                else:
                    diversified_recs.append((item_id, score))
            
            # Re-sort by boosted scores
            diversified_recs.sort(key=lambda x: x[1], reverse=True)
            return diversified_recs
            
        except Exception as e:
            logger.error(f"Failed to apply diversity boost: {e}")
            return recommendations
    
    def _apply_novelty_boost(self, recommendations: List[Tuple[str, float]], 
                           user_profile: UserProfile) -> List[Tuple[str, float]]:
        """Apply novelty boost to recommendations"""
        try:
            # Calculate novelty for each item based on how rarely it's been tried
            user_history = set(interaction['food_category'] 
                             for interaction in user_profile.interaction_history 
                             if interaction['food_category'])
            
            novelty_recs = []
            
            for item_id, score in recommendations:
                # Calculate novelty (inverse of popularity in user's history)
                if item_id in user_history:
                    novelty_factor = 0.5  # Penalize already tried items
                else:
                    # Check if similar items have been tried
                    similar_items = self.content_based.get_similar_items(item_id, 5)
                    similar_tried = sum(1 for sim_item_id, _ in similar_items if sim_item_id in user_history)
                    novelty_factor = 1 - (similar_tried / 5) * 0.3
                
                # Apply novelty boost
                boosted_score = score * (1 + self.config.novelty_boost * novelty_factor)
                novelty_recs.append((item_id, boosted_score))
            
            # Re-sort by boosted scores
            novelty_recs.sort(key=lambda x: x[1], reverse=True)
            return novelty_recs
            
        except Exception as e:
            logger.error(f"Failed to apply novelty boost: {e}")
            return recommendations
    
    def _generate_explanations(self, recommendations: List[Tuple[str, float]], 
                             user_profile: UserProfile, context: Dict[str, Any]) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Generate explanations for recommendations"""
        try:
            explained_recs = []
            
            user_preferences = {cat: pref.preference_score 
                             for cat, pref in user_profile.preferences.items()}
            user_history = [interaction['food_category'] 
                           for interaction in user_profile.interaction_history 
                           if interaction['food_category']]
            
            for item_id, score in recommendations:
                explanation = self.content_based.get_explanation_for_recommendation(
                    user_profile.user_id, item_id, user_preferences, user_history
                )
                
                # Add context-specific explanations
                if context:
                    if 'meal_type' in context:
                        explanation['meal_suitability'] = self._check_meal_suitability(item_id, context['meal_type'])
                    if 'occasion' in context:
                        explanation['occasion_suitability'] = self._check_occasion_suitability(item_id, context['occasion'])
                
                explained_recs.append((item_id, score, explanation))
            
            return explained_recs
            
        except Exception as e:
            logger.error(f"Failed to generate explanations: {e}")
            return [(item_id, score, {}) for item_id, score in recommendations]
    
    def _determine_primary_source(self, item_id: str, cf_recs: List[Tuple[str, float]], 
                                cb_recs: List[Tuple[str, float]], 
                                profile_recs: List[Tuple[str, float]]) -> str:
        """Determine the primary source of a recommendation"""
        cf_items = set(item_id for item_id, _ in cf_recs)
        cb_items = set(item_id for item_id, _ in cb_recs)
        profile_items = set(item_id for item_id, _ in profile_recs)
        
        if item_id in cf_items and item_id in cb_items:
            return 'hybrid'
        elif item_id in cf_items:
            return 'collaborative'
        elif item_id in cb_items:
            return 'content_based'
        elif item_id in profile_items:
            return 'profile_based'
        else:
            return 'popularity'
    
    def _calculate_diversity_score(self, recommendations: List[Tuple[str, float, Dict[str, Any]]]) -> float:
        """Calculate diversity score for recommendations"""
        try:
            if len(recommendations) < 2:
                return 0.0
            
            item_ids = [item_id for item_id, _, _ in recommendations]
            return self.content_based.get_recommendation_diversity_score(
                [(item_id, score) for item_id, score, _ in recommendations]
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate diversity score: {e}")
            return 0.0
    
    def _calculate_novelty_score(self, recommendations: List[Tuple[str, float, Dict[str, Any]]], 
                               user_profile: UserProfile) -> float:
        """Calculate novelty score for recommendations"""
        try:
            user_history = set(interaction['food_category'] 
                             for interaction in user_profile.interaction_history 
                             if interaction['food_category'])
            
            if not recommendations:
                return 0.0
            
            novel_items = sum(1 for item_id, _, _ in recommendations if item_id not in user_history)
            return novel_items / len(recommendations)
            
        except Exception as e:
            logger.error(f"Failed to calculate novelty score: {e}")
            return 0.0
    
    def _generate_explanation_summary(self, recommendations: List[Recommendation]) -> str:
        """Generate a summary explanation for all recommendations"""
        try:
            if not recommendations:
                return "No recommendations available."
            
            sources = defaultdict(int)
            for rec in recommendations:
                sources[rec.source] += 1
            
            summary_parts = []
            if sources['collaborative'] > 0:
                summary_parts.append(f"{sources['collaborative']} based on similar users")
            if sources['content_based'] > 0:
                summary_parts.append(f"{sources['content_based']} matching your taste profile")
            if sources['profile_based'] > 0:
                summary_parts.append(f"{sources['profile_based']} based on your preferences")
            if sources['popularity'] > 0:
                summary_parts.append(f"{sources['popularity']} popular choices")
            
            if summary_parts:
                return "Recommendations include: " + ", ".join(summary_parts) + "."
            else:
                return "Personalized recommendations based on your preferences."
                
        except Exception as e:
            logger.error(f"Failed to generate explanation summary: {e}")
            return "Personalized recommendations."
    
    def _check_meal_suitability(self, item_id: str, meal_type: str) -> str:
        """Check if an item is suitable for a specific meal type"""
        try:
            item = self.content_based.get_item_details(item_id)
            if not item:
                return "Unknown suitability"
            
            # Simple meal type logic
            if meal_type.lower() in ['breakfast', 'brunch']:
                if 'bread' in item.category.lower() or 'breakfast' in item.name.lower():
                    return "Great for breakfast"
                else:
                    return "Not typical for breakfast"
            elif meal_type.lower() in ['lunch', 'dinner']:
                return "Suitable for main meal"
            elif meal_type.lower() in ['snack']:
                return "Good for snacking"
            else:
                return "Suitable for any meal"
                
        except Exception as e:
            logger.error(f"Failed to check meal suitability: {e}")
            return "Unknown suitability"
    
    def _check_occasion_suitability(self, item_id: str, occasion: str) -> str:
        """Check if an item is suitable for a specific occasion"""
        try:
            item = self.content_based.get_item_details(item_id)
            if not item:
                return "Unknown suitability"
            
            # Simple occasion logic
            if occasion.lower() in ['casual', 'everyday']:
                return "Perfect for casual dining"
            elif occasion.lower() in ['formal', 'special']:
                if item.cuisine_type == 'Nigerian':
                    return "Great for special occasions"
                else:
                    return "Suitable for formal dining"
            elif occasion.lower() in ['quick', 'fast']:
                return "Quick and convenient"
            else:
                return "Suitable for this occasion"
                
        except Exception as e:
            logger.error(f"Failed to check occasion suitability: {e}")
            return "Unknown suitability"
    
    def _get_cached_recommendations(self, user_id: str, n_recommendations: int) -> Optional[RecommendationResult]:
        """Get cached recommendations if available and not expired"""
        try:
            if not self.db_connection:
                return None
                
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                SELECT recommendations, algorithm_weights, diversity_score, 
                       novelty_score, processing_time_ms, created_at, expires_at
                FROM recommendation_cache 
                WHERE user_id = ? AND expires_at > CURRENT_TIMESTAMP
            """, (user_id,))
            
            result = cursor.fetchone()
            if result:
                # Deserialize cached data
                recommendations_data = json.loads(result[0])
                algorithm_weights = json.loads(result[1])
                
                recommendations = []
                for rec_data in recommendations_data:
                    recommendation = Recommendation(
                        item_id=rec_data['item_id'],
                        score=rec_data['score'],
                        explanation=rec_data['explanation'],
                        source=rec_data['source'],
                        timestamp=datetime.fromisoformat(rec_data['timestamp']),
                        metadata=rec_data['metadata']
                    )
                    recommendations.append(recommendation)
                
                return RecommendationResult(
                    user_id=user_id,
                    recommendations=recommendations,
                    algorithm_weights=algorithm_weights,
                    diversity_score=result[2],
                    novelty_score=result[3],
                    processing_time_ms=result[4],
                    cache_hit=True,
                    explanation_summary=self._generate_explanation_summary(recommendations)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached recommendations: {e}")
            return None
    
    def _cache_recommendations(self, result: RecommendationResult):
        """Cache recommendations for future use"""
        try:
            if not self.db_connection:
                return
                
            cursor = self.db_connection.cursor()
            
            # Serialize recommendations
            recommendations_data = []
            for rec in result.recommendations:
                rec_data = {
                    'item_id': rec.item_id,
                    'score': rec.score,
                    'explanation': rec.explanation,
                    'source': rec.source,
                    'timestamp': rec.timestamp.isoformat(),
                    'metadata': rec.metadata
                }
                recommendations_data.append(rec_data)
            
            # Calculate expiry time
            expires_at = datetime.now() + timedelta(minutes=self.config.cache_duration_minutes)
            
            cursor.execute("""
                INSERT OR REPLACE INTO recommendation_cache 
                (user_id, recommendations, algorithm_weights, diversity_score, 
                 novelty_score, processing_time_ms, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                result.user_id,
                json.dumps(recommendations_data),
                json.dumps(result.algorithm_weights),
                result.diversity_score,
                result.novelty_score,
                result.processing_time_ms,
                expires_at
            ))
            
            self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to cache recommendations: {e}")
    
    def _get_fallback_recommendations(self, user_id: str, n_recommendations: int) -> RecommendationResult:
        """Get fallback recommendations when main system fails"""
        try:
            # Use popularity-based recommendations as fallback
            popularity_recs = self._get_popularity_recommendations(n_recommendations)
            
            recommendations = []
            for item_id, score in popularity_recs:
                recommendation = Recommendation(
                    item_id=item_id,
                    score=score,
                    explanation={'reasoning': ['Popular choice among users']},
                    source='popularity',
                    timestamp=datetime.now(),
                    metadata={'fallback': True}
                )
                recommendations.append(recommendation)
            
            return RecommendationResult(
                user_id=user_id,
                recommendations=recommendations,
                algorithm_weights={'popularity': 1.0},
                diversity_score=0.0,
                novelty_score=0.0,
                processing_time_ms=0.0,
                cache_hit=False,
                explanation_summary="Fallback recommendations based on popularity."
            )
            
        except Exception as e:
            logger.error(f"Failed to get fallback recommendations: {e}")
            # Return empty result as last resort
            return RecommendationResult(
                user_id=user_id,
                recommendations=[],
                algorithm_weights={},
                diversity_score=0.0,
                novelty_score=0.0,
                processing_time_ms=0.0,
                cache_hit=False,
                explanation_summary="No recommendations available."
            )
    
    def record_feedback(self, user_id: str, item_id: str, feedback_type: str, 
                       feedback_score: float, metadata: Dict[str, Any] = None) -> bool:
        """Record user feedback on recommendations"""
        try:
            if not self.db_connection:
                return False
                
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                INSERT INTO recommendation_feedback 
                (user_id, item_id, feedback_type, feedback_score, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, item_id, feedback_type, feedback_score, json.dumps(metadata) if metadata else None))
            
            self.db_connection.commit()
            
            # Update user profile with feedback
            if feedback_type == 'rating':
                self.user_profiling.update_user_interaction(user_id, item_id, 'rating', feedback_score)
            elif feedback_type == 'explicit_feedback':
                self.user_profiling.update_recommendation_feedback(user_id, item_id, feedback_score)
            
            logger.info(f"Recorded feedback for user {user_id}, item {item_id}: {feedback_score}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")
            return False
    
    def get_recommendation_statistics(self) -> Dict[str, Any]:
        """Get recommendation system statistics"""
        try:
            if not self.db_connection:
                return {}
            
            cursor = self.db_connection.cursor()
            
            # Get total recommendations
            cursor.execute("SELECT COUNT(*) FROM recommendation_cache")
            total_cached = cursor.fetchone()[0]
            
            # Get feedback statistics
            cursor.execute("""
                SELECT feedback_type, AVG(feedback_score), COUNT(*) 
                FROM recommendation_feedback 
                GROUP BY feedback_type
            """)
            feedback_stats = cursor.fetchall()
            
            # Get algorithm performance
            cursor.execute("""
                SELECT algorithm_name, AVG(precision_score), AVG(recall_score), AVG(f1_score)
                FROM algorithm_performance 
                GROUP BY algorithm_name
            """)
            performance_stats = cursor.fetchall()
            
            return {
                'total_cached_recommendations': total_cached,
                'feedback_statistics': {
                    feedback_type: {
                        'avg_score': avg_score,
                        'count': count
                    }
                    for feedback_type, avg_score, count in feedback_stats
                },
                'algorithm_performance': {
                    algorithm: {
                        'avg_precision': avg_precision,
                        'avg_recall': avg_recall,
                        'avg_f1': avg_f1
                    }
                    for algorithm, avg_precision, avg_recall, avg_f1 in performance_stats
                },
                'cache_hit_rate': getattr(self, '_cache_hits', 0) / max(1, getattr(self, '_cache_requests', 1)),
                'average_processing_time_ms': getattr(self, '_avg_processing_time', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get recommendation statistics: {e}")
            return {}
    
    def update_models(self) -> bool:
        """Update recommendation models with new data"""
        try:
            logger.info("Updating recommendation models...")
            
            # Rebuild collaborative filtering models
            self.collaborative_filtering.build_user_item_matrix()
            self.collaborative_filtering.compute_user_similarity()
            self.collaborative_filtering.compute_item_similarity()
            self.collaborative_filtering.train_matrix_factorization()
            
            # Rebuild content-based models
            self.content_based.build_feature_matrix()
            
            # Clear cache to force fresh recommendations
            if self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute("DELETE FROM recommendation_cache")
                self.db_connection.commit()
            
            logger.info("Recommendation models updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update recommendation models: {e}")
            return False
