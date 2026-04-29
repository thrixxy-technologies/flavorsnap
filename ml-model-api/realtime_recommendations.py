"""
Real-time Recommendation System for FlavorSnap

This module provides real-time recommendation capabilities using
streaming data, incremental updates, and live personalization.
"""

import asyncio
import logging
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import numpy as np
from threading import Thread, Lock
import time
from queue import Queue, Empty
from db_config import get_connection

from recommendation_engine import HybridRecommendationEngine, RecommendationResult, Recommendation

logger = logging.getLogger(__name__)

@dataclass
class RealtimeEvent:
    """Real-time user interaction event"""
    user_id: str
    event_type: str  # 'view', 'like', 'dislike', 'rating', 'purchase', 'search'
    item_id: str
    timestamp: datetime
    session_id: str
    context: Dict[str, Any]
    metadata: Dict[str, Any]

@dataclass
class RealtimeConfig:
    """Configuration for real-time recommendations"""
    # Update settings
    batch_size: int = 100
    update_interval_seconds: int = 30
    max_events_in_memory: int = 10000
    
    # Real-time scoring
    realtime_weight: float = 0.3
    historical_weight: float = 0.7
    session_decay_rate: float = 0.95
    
    # Performance settings
    max_processing_time_ms: int = 100
    enable_async_processing: bool = True
    cache_size: int = 1000
    
    # Session settings
    session_timeout_minutes: int = 30
    min_session_interactions: int = 3

class RealtimeRecommendationSystem:
    """Real-time recommendation system"""
    
    def __init__(self, config: RealtimeConfig = None, db_connection=None):
        self.config = config or RealtimeConfig()
        self.db_connection = db_connection or get_connection()
        
        # Initialize recommendation engine
        self.recommendation_engine = HybridRecommendationEngine(db_connection=self.db_connection)
        
        # Real-time data structures
        self.event_queue = Queue()
        self.user_sessions = defaultdict(dict)
        self.recent_events = deque(maxlen=self.config.max_events_in_memory)
        self.realtime_cache = {}
        self.cache_lock = Lock()
        
        # Processing state
        self.is_running = False
        self.processing_thread = None
        self.update_thread = None
        
        # Event handlers
        self.event_handlers = {
            'view': self._handle_view_event,
            'like': self._handle_like_event,
            'dislike': self._handle_dislike_event,
            'rating': self._handle_rating_event,
            'purchase': self._handle_purchase_event,
            'search': self._handle_search_event
        }
        
        self._init_database()
        self._start_processing()
    
    def _init_database(self):
        """Initialize real-time recommendation database tables"""
        if not self.db_connection:
            logger.warning("No database connection available for real-time recommendations")
            return
            
        try:
            cursor = self.db_connection.cursor()
            
            # Real-time events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS realtime_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    event_type TEXT,
                    item_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    context TEXT,
                    metadata TEXT,
                    processed BOOLEAN DEFAULT FALSE
                )
            """)
            
            # User sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    interaction_count INTEGER DEFAULT 0,
                    session_data TEXT,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Real-time recommendations cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS realtime_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    session_id TEXT,
                    recommendations BLOB,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    UNIQUE(user_id, session_id)
                )
            """)
            
            self.db_connection.commit()
            logger.info("Real-time recommendation database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize real-time recommendation database: {e}")
    
    def _start_processing(self):
        """Start background processing threads"""
        try:
            self.is_running = True
            
            # Start event processing thread
            self.processing_thread = Thread(target=self._process_events_loop, daemon=True)
            self.processing_thread.start()
            
            # Start periodic update thread
            self.update_thread = Thread(target=self._periodic_update_loop, daemon=True)
            self.update_thread.start()
            
            logger.info("Real-time recommendation processing started")
            
        except Exception as e:
            logger.error(f"Failed to start real-time processing: {e}")
    
    def add_event(self, event: RealtimeEvent) -> bool:
        """Add a real-time event to the processing queue"""
        try:
            # Add to queue for processing
            self.event_queue.put(event)
            
            # Add to recent events
            self.recent_events.append(event)
            
            # Update session
            self._update_session(event)
            
            # Store in database
            if self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute("""
                    INSERT INTO realtime_events 
                    (user_id, event_type, item_id, timestamp, session_id, context, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.user_id, event.event_type, event.item_id,
                    event.timestamp.isoformat(), event.session_id,
                    json.dumps(event.context), json.dumps(event.metadata)
                ))
                self.db_connection.commit()
            
            logger.debug(f"Added real-time event: {event.event_type} for user {event.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add real-time event: {e}")
            return False
    
    def get_realtime_recommendations(self, user_id: str, session_id: str = None,
                                   context: Dict[str, Any] = None,
                                   n_recommendations: int = 10) -> RecommendationResult:
        """Get real-time recommendations for a user"""
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = f"{user_id}:{session_id or 'default'}"
            with self.cache_lock:
                if cache_key in self.realtime_cache:
                    cached_result = self.realtime_cache[cache_key]
                    if datetime.now() < cached_result['expires_at']:
                        cached_result['cache_hit'] = True
                        return cached_result['result']
            
            # Get session information
            session_data = self._get_session_data(user_id, session_id)
            
            # Get base recommendations
            base_result = self.recommendation_engine.get_recommendations(
                user_id, n_recommendations * 2, context
            )
            
            # Apply real-time adjustments
            realtime_adjusted = self._apply_realtime_adjustments(
                base_result, user_id, session_data, context
            )
            
            # Apply session-based personalization
            session_personalized = self._apply_session_personalization(
                realtime_adjusted, session_data
            )
            
            # Limit to requested number
            final_recommendations = session_personalized.recommendations[:n_recommendations]
            
            # Create result
            result = RecommendationResult(
                user_id=user_id,
                recommendations=final_recommendations,
                algorithm_weights={
                    **base_result.algorithm_weights,
                    'realtime': self.config.realtime_weight
                },
                diversity_score=session_personalized.diversity_score,
                novelty_score=session_personalized.novelty_score,
                processing_time_ms=(time.time() - start_time) * 1000,
                cache_hit=False,
                explanation_summary=self._generate_realtime_explanation_summary(
                    final_recommendations, session_data
                )
            )
            
            # Cache the result
            with self.cache_lock:
                self.realtime_cache[cache_key] = {
                    'result': result,
                    'expires_at': datetime.now() + timedelta(minutes=5)
                }
            
            logger.info(f"Generated real-time recommendations for user {user_id} in {(time.time() - start_time) * 1000:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get real-time recommendations for user {user_id}: {e}")
            return self.recommendation_engine.get_recommendations(user_id, n_recommendations, context)
    
    def _process_events_loop(self):
        """Process events from the queue"""
        while self.is_running:
            try:
                # Get batch of events
                events = []
                try:
                    for _ in range(self.config.batch_size):
                        event = self.event_queue.get(timeout=1.0)
                        events.append(event)
                except Empty:
                    continue
                
                # Process events
                self._process_events_batch(events)
                
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                time.sleep(1.0)
    
    def _process_events_batch(self, events: List[RealtimeEvent]):
        """Process a batch of real-time events"""
        try:
            for event in events:
                # Get appropriate handler
                handler = self.event_handlers.get(event.event_type)
                if handler:
                    handler(event)
                else:
                    logger.warning(f"No handler for event type: {event.event_type}")
            
            # Update user profiles incrementally
            self._update_user_profiles_incremental(events)
            
            # Invalidate relevant cache entries
            self._invalidate_cache_for_events(events)
            
            logger.debug(f"Processed batch of {len(events)} events")
            
        except Exception as e:
            logger.error(f"Failed to process events batch: {e}")
    
    def _handle_view_event(self, event: RealtimeEvent):
        """Handle view event"""
        try:
            # Update user interaction
            self.recommendation_engine.user_profiling.update_user_interaction(
                event.user_id, event.item_id, 'view', metadata=event.context
            )
            
            # Update collaborative filtering model
            self.recommendation_engine.collaborative_filtering.update_with_new_interaction(
                event.user_id, event.item_id, 3.0  # Neutral rating for view
            )
            
        except Exception as e:
            logger.error(f"Failed to handle view event: {e}")
    
    def _handle_like_event(self, event: RealtimeEvent):
        """Handle like event"""
        try:
            # Update user interaction with positive feedback
            self.recommendation_engine.user_profiling.update_user_interaction(
                event.user_id, event.item_id, 'like', feedback_score=1.0, metadata=event.context
            )
            
            # Update collaborative filtering model
            self.recommendation_engine.collaborative_filtering.update_with_new_interaction(
                event.user_id, event.item_id, 4.5
            )
            
        except Exception as e:
            logger.error(f"Failed to handle like event: {e}")
    
    def _handle_dislike_event(self, event: RealtimeEvent):
        """Handle dislike event"""
        try:
            # Update user interaction with negative feedback
            self.recommendation_engine.user_profiling.update_user_interaction(
                event.user_id, event.item_id, 'dislike', feedback_score=-1.0, metadata=event.context
            )
            
            # Update collaborative filtering model
            self.recommendation_engine.collaborative_filtering.update_with_new_interaction(
                event.user_id, event.item_id, 1.5
            )
            
        except Exception as e:
            logger.error(f"Failed to handle dislike event: {e}")
    
    def _handle_rating_event(self, event: RealtimeEvent):
        """Handle rating event"""
        try:
            rating = event.metadata.get('rating', 3.0)
            
            # Update user interaction
            self.recommendation_engine.user_profiling.update_user_interaction(
                event.user_id, event.item_id, 'rating', rating=rating, metadata=event.context
            )
            
            # Update collaborative filtering model
            self.recommendation_engine.collaborative_filtering.update_with_new_interaction(
                event.user_id, event.item_id, rating
            )
            
        except Exception as e:
            logger.error(f"Failed to handle rating event: {e}")
    
    def _handle_purchase_event(self, event: RealtimeEvent):
        """Handle purchase event"""
        try:
            # Update user interaction with strong positive feedback
            self.recommendation_engine.user_profiling.update_user_interaction(
                event.user_id, event.item_id, 'purchase', feedback_score=1.0, metadata=event.context
            )
            
            # Update collaborative filtering model
            self.recommendation_engine.collaborative_filtering.update_with_new_interaction(
                event.user_id, event.item_id, 5.0
            )
            
        except Exception as e:
            logger.error(f"Failed to handle purchase event: {e}")
    
    def _handle_search_event(self, event: RealtimeEvent):
        """Handle search event"""
        try:
            # Update user interaction
            self.recommendation_engine.user_profiling.update_user_interaction(
                event.user_id, event.item_id, 'search', metadata=event.context
            )
            
            # Update session search history
            if event.session_id:
                session = self.user_sessions[event.session_id]
                if 'search_history' not in session:
                    session['search_history'] = []
                session['search_history'].append({
                    'query': event.metadata.get('query', ''),
                    'item_id': event.item_id,
                    'timestamp': event.timestamp
                })
            
        except Exception as e:
            logger.error(f"Failed to handle search event: {e}")
    
    def _update_session(self, event: RealtimeEvent):
        """Update user session information"""
        try:
            session = self.user_sessions[event.session_id]
            
            # Update basic session info
            session['user_id'] = event.user_id
            session['last_activity'] = event.timestamp
            session['interaction_count'] = session.get('interaction_count', 0) + 1
            
            # Update session-specific data
            if 'interactions' not in session:
                session['interactions'] = []
            session['interactions'].append({
                'event_type': event.event_type,
                'item_id': event.item_id,
                'timestamp': event.timestamp,
                'context': event.context
            })
            
            # Store in database
            if self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO user_sessions 
                    (session_id, user_id, last_activity, interaction_count, session_data)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    event.session_id, event.user_id, event.timestamp.isoformat(),
                    session['interaction_count'], json.dumps(session)
                ))
                self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
    
    def _get_session_data(self, user_id: str, session_id: str = None) -> Dict[str, Any]:
        """Get session data for a user"""
        try:
            if session_id and session_id in self.user_sessions:
                return self.user_sessions[session_id]
            
            # Get most recent session for user
            recent_sessions = []
            for session_id, session in self.user_sessions.items():
                if session.get('user_id') == user_id:
                    recent_sessions.append((session_id, session))
            
            if recent_sessions:
                # Sort by last activity
                recent_sessions.sort(key=lambda x: x[1].get('last_activity', datetime.min), reverse=True)
                return recent_sessions[0][1]
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get session data: {e}")
            return {}
    
    def _apply_realtime_adjustments(self, base_result: RecommendationResult, 
                                  user_id: str, session_data: Dict[str, Any],
                                  context: Dict[str, Any]) -> RecommendationResult:
        """Apply real-time adjustments to base recommendations"""
        try:
            adjusted_recommendations = []
            
            for recommendation in base_result.recommendations:
                adjusted_score = recommendation.score
                adjustments = []
                
                # Apply session-based adjustments
                if session_data:
                    # Boost items related to recent searches
                    search_history = session_data.get('search_history', [])
                    for search in search_history[-5:]:  # Last 5 searches
                        if self._is_item_related_to_search(recommendation.item_id, search['query']):
                            adjusted_score *= 1.2
                            adjustments.append('recent_search_related')
                            break
                    
                    # Boost items in same category as recent interactions
                    recent_interactions = session_data.get('interactions', [])
                    for interaction in recent_interactions[-10:]:  # Last 10 interactions
                        if self._is_item_in_same_category(recommendation.item_id, interaction['item_id']):
                            adjusted_score *= 1.1
                            adjustments.append('category_consistency')
                            break
                
                # Apply context-based adjustments
                if context:
                    if 'time_of_day' in context:
                        adjusted_score *= self._get_time_of_day_multiplier(
                            recommendation.item_id, context['time_of_day']
                        )
                        adjustments.append('time_of_day')
                    
                    if 'location' in context:
                        adjusted_score *= self._get_location_multiplier(
                            recommendation.item_id, context['location']
                        )
                        adjustments.append('location')
                
                # Create adjusted recommendation
                adjusted_recommendation = Recommendation(
                    item_id=recommendation.item_id,
                    score=adjusted_score,
                    explanation={
                        **recommendation.explanation,
                        'realtime_adjustments': adjustments,
                        'adjustment_factor': adjusted_score / recommendation.score
                    },
                    source=recommendation.source,
                    timestamp=datetime.now(),
                    metadata={
                        **recommendation.metadata,
                        'realtime_adjusted': True,
                        'adjustments': adjustments
                    }
                )
                adjusted_recommendations.append(adjusted_recommendation)
            
            # Re-sort by adjusted scores
            adjusted_recommendations.sort(key=lambda x: x.score, reverse=True)
            
            # Create adjusted result
            adjusted_result = RecommendationResult(
                user_id=base_result.user_id,
                recommendations=adjusted_recommendations,
                algorithm_weights={
                    **base_result.algorithm_weights,
                    'realtime_adjustments': 0.1
                },
                diversity_score=base_result.diversity_score,
                novelty_score=base_result.novelty_score,
                processing_time_ms=base_result.processing_time_ms,
                cache_hit=False,
                explanation_summary=base_result.explanation_summary
            )
            
            return adjusted_result
            
        except Exception as e:
            logger.error(f"Failed to apply real-time adjustments: {e}")
            return base_result
    
    def _apply_session_personalization(self, result: RecommendationResult, 
                                    session_data: Dict[str, Any]) -> RecommendationResult:
        """Apply session-based personalization"""
        try:
            if not session_data or session_data.get('interaction_count', 0) < self.config.min_session_interactions:
                return result
            
            personalized_recommendations = []
            session_profile = self._build_session_profile(session_data)
            
            for recommendation in result.recommendations:
                # Calculate session compatibility
                compatibility_score = self._calculate_session_compatibility(
                    recommendation.item_id, session_profile
                )
                
                # Apply session personalization weight
                session_weight = min(0.3, session_data.get('interaction_count', 0) / 20)
                personalized_score = (
                    recommendation.score * (1 - session_weight) +
                    compatibility_score * session_weight
                )
                
                personalized_recommendation = Recommendation(
                    item_id=recommendation.item_id,
                    score=personalized_score,
                    explanation={
                        **recommendation.explanation,
                        'session_compatibility': compatibility_score,
                        'session_weight': session_weight
                    },
                    source=recommendation.source,
                    timestamp=datetime.now(),
                    metadata={
                        **recommendation.metadata,
                        'session_personalized': True
                    }
                )
                personalized_recommendations.append(personalized_recommendation)
            
            # Re-sort by personalized scores
            personalized_recommendations.sort(key=lambda x: x.score, reverse=True)
            
            # Create personalized result
            personalized_result = RecommendationResult(
                user_id=result.user_id,
                recommendations=personalized_recommendations,
                algorithm_weights={
                    **result.algorithm_weights,
                    'session_personalization': session_weight
                },
                diversity_score=result.diversity_score,
                novelty_score=result.novelty_score,
                processing_time_ms=result.processing_time_ms,
                cache_hit=False,
                explanation_summary=result.explanation_summary
            )
            
            return personalized_result
            
        except Exception as e:
            logger.error(f"Failed to apply session personalization: {e}")
            return result
    
    def _build_session_profile(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build user profile from session data"""
        try:
            profile = {
                'categories': defaultdict(int),
                'items': defaultdict(int),
                'search_terms': defaultdict(int),
                'interaction_types': defaultdict(int)
            }
            
            # Analyze interactions
            for interaction in session_data.get('interactions', []):
                item_id = interaction['item_id']
                event_type = interaction['event_type']
                
                profile['items'][item_id] += 1
                profile['interaction_types'][event_type] += 1
                
                # Get item category
                item = self.recommendation_engine.content_based.get_item_details(item_id)
                if item:
                    profile['categories'][item.category] += 1
            
            # Analyze search history
            for search in session_data.get('search_history', []):
                query = search.get('query', '')
                if query:
                    profile['search_terms'][query.lower()] += 1
            
            return profile
            
        except Exception as e:
            logger.error(f"Failed to build session profile: {e}")
            return {}
    
    def _calculate_session_compatibility(self, item_id: str, session_profile: Dict[str, Any]) -> float:
        """Calculate compatibility between item and session profile"""
        try:
            score = 0.0
            
            # Category compatibility
            item = self.recommendation_engine.content_based.get_item_details(item_id)
            if item:
                category_score = session_profile['categories'].get(item.category, 0)
                score += category_score * 0.4
            
            # Item compatibility (if previously interacted)
            item_score = session_profile['items'].get(item_id, 0)
            score += item_score * 0.3
            
            # Search term compatibility
            if item:
                for search_term, count in session_profile['search_terms'].items():
                    if search_term in item.name.lower() or search_term in item.description.lower():
                        score += count * 0.2
            
            # Interaction type compatibility
            positive_interactions = (
                session_profile['interaction_types'].get('like', 0) +
                session_profile['interaction_types'].get('purchase', 0) +
                session_profile['interaction_types'].get('rating', 0)
            )
            score += positive_interactions * 0.1
            
            # Normalize score
            total_interactions = sum(session_profile['interaction_types'].values())
            if total_interactions > 0:
                score = score / total_interactions
            
            return min(1.0, score)
            
        except Exception as e:
            logger.error(f"Failed to calculate session compatibility: {e}")
            return 0.0
    
    def _is_item_related_to_search(self, item_id: str, search_query: str) -> bool:
        """Check if item is related to search query"""
        try:
            item = self.recommendation_engine.content_based.get_item_details(item_id)
            if not item:
                return False
            
            search_terms = search_query.lower().split()
            
            # Check name
            for term in search_terms:
                if term in item.name.lower():
                    return True
            
            # Check description
            for term in search_terms:
                if term in item.description.lower():
                    return True
            
            # Check ingredients
            for term in search_terms:
                for ingredient in item.ingredients:
                    if term in ingredient.lower():
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check item-search relation: {e}")
            return False
    
    def _is_item_in_same_category(self, item_id1: str, item_id2: str) -> bool:
        """Check if two items are in the same category"""
        try:
            item1 = self.recommendation_engine.content_based.get_item_details(item_id1)
            item2 = self.recommendation_engine.content_based.get_item_details(item_id2)
            
            if item1 and item2:
                return item1.category == item2.category
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check category relation: {e}")
            return False
    
    def _get_time_of_day_multiplier(self, item_id: str, time_of_day: str) -> float:
        """Get time-of-day based multiplier for item"""
        try:
            # Simple time-of-day logic
            time_multipliers = {
                'morning': {'bread': 1.3, 'breakfast': 1.5},
                'afternoon': {'snack': 1.2, 'light': 1.1},
                'evening': {'dinner': 1.3, 'heavy': 1.2},
                'night': {'snack': 1.1, 'light': 1.0}
            }
            
            item = self.recommendation_engine.content_based.get_item_details(item_id)
            if not item:
                return 1.0
            
            multipliers = time_multipliers.get(time_of_day.lower(), {})
            
            for keyword, multiplier in multipliers.items():
                if keyword in item.name.lower() or keyword in item.category.lower():
                    return multiplier
            
            return 1.0
            
        except Exception as e:
            logger.error(f"Failed to get time-of-day multiplier: {e}")
            return 1.0
    
    def _get_location_multiplier(self, item_id: str, location: str) -> float:
        """Get location-based multiplier for item"""
        try:
            # Simple location logic
            location_multipliers = {
                'nigeria': {'nigerian': 1.5, 'akara': 1.4, 'egusi': 1.4, 'moi moi': 1.4},
                'international': {'international': 1.3, 'bread': 1.2},
                'default': {}
            }
            
            item = self.recommendation_engine.content_based.get_item_details(item_id)
            if not item:
                return 1.0
            
            multipliers = location_multipliers.get(location.lower(), {})
            
            for keyword, multiplier in multipliers.items():
                if keyword in item.cuisine_type.lower() or keyword in item.category.lower():
                    return multiplier
            
            return 1.0
            
        except Exception as e:
            logger.error(f"Failed to get location multiplier: {e}")
            return 1.0
    
    def _generate_realtime_explanation_summary(self, recommendations: List[Recommendation], 
                                              session_data: Dict[str, Any]) -> str:
        """Generate explanation summary for real-time recommendations"""
        try:
            base_summary = self.recommendation_engine._generate_explanation_summary(recommendations)
            
            # Add real-time context
            if session_data and session_data.get('interaction_count', 0) >= self.config.min_session_interactions:
                recent_interactions = session_data.get('interactions', [])[-3:]
                if recent_interactions:
                    base_summary += f" Personalized based on your recent activity in this session."
            
            return base_summary
            
        except Exception as e:
            logger.error(f"Failed to generate realtime explanation summary: {e}")
            return "Real-time personalized recommendations."
    
    def _periodic_update_loop(self):
        """Periodic update loop for model maintenance"""
        while self.is_running:
            try:
                # Clean up expired sessions
                self._cleanup_expired_sessions()
                
                # Clean up expired cache entries
                self._cleanup_expired_cache()
                
                # Update models periodically
                if datetime.now().minute % 30 == 0:  # Every 30 minutes
                    self.recommendation_engine.update_models()
                
                # Sleep until next update
                time.sleep(self.config.update_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in periodic update loop: {e}")
                time.sleep(60)
    
    def _cleanup_expired_sessions(self):
        """Clean up expired user sessions"""
        try:
            current_time = datetime.now()
            expired_sessions = []
            
            for session_id, session in self.user_sessions.items():
                last_activity = session.get('last_activity', datetime.min)
                if current_time - last_activity > timedelta(minutes=self.config.session_timeout_minutes):
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.user_sessions[session_id]
            
            # Also clean up database
            if self.db_connection and expired_sessions:
                cursor = self.db_connection.cursor()
                cursor.execute("""
                    DELETE FROM user_sessions 
                    WHERE session_id IN ({}) OR 
                          last_activity < datetime('now', '-{} minutes')
                """.format(','.join(['?' for _ in expired_sessions]), self.config.session_timeout_minutes),
                           expired_sessions)
                self.db_connection.commit()
            
            if expired_sessions:
                logger.debug(f"Cleaned up {len(expired_sessions)} expired sessions")
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
    
    def _cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        try:
            current_time = datetime.now()
            expired_keys = []
            
            with self.cache_lock:
                for key, value in self.realtime_cache.items():
                    if current_time > value['expires_at']:
                        expired_keys.append(key)
            
            for key in expired_keys:
                del self.realtime_cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired cache: {e}")
    
    def _update_user_profiles_incremental(self, events: List[RealtimeEvent]):
        """Incrementally update user profiles based on events"""
        try:
            # Group events by user
            user_events = defaultdict(list)
            for event in events:
                user_events[event.user_id].append(event)
            
            # Process each user's events
            for user_id, user_event_list in user_events.items():
                # Batch update user profile
                for event in user_event_list:
                    if event.event_type in ['like', 'dislike', 'rating', 'purchase']:
                        self.recommendation_engine.user_profiling.update_user_interaction(
                            user_id, event.item_id, event.event_type,
                            rating=event.metadata.get('rating'),
                            feedback_score=event.metadata.get('feedback_score'),
                            metadata=event.context
                        )
            
        except Exception as e:
            logger.error(f"Failed to update user profiles incrementally: {e}")
    
    def _invalidate_cache_for_events(self, events: List[RealtimeEvent]):
        """Invalidate cache entries affected by events"""
        try:
            affected_users = set(event.user_id for event in events)
            
            with self.cache_lock:
                keys_to_remove = []
                for key in self.realtime_cache:
                    user_id = key.split(':')[0]
                    if user_id in affected_users:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self.realtime_cache[key]
            
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
    
    def get_realtime_statistics(self) -> Dict[str, Any]:
        """Get real-time recommendation system statistics"""
        try:
            current_time = datetime.now()
            
            # Active sessions
            active_sessions = sum(1 for session in self.user_sessions.values()
                                if current_time - session.get('last_activity', datetime.min) < timedelta(minutes=30))
            
            # Recent events
            recent_events = sum(1 for event in self.recent_events
                              if current_time - event.timestamp < timedelta(hours=1))
            
            # Queue size
            queue_size = self.event_queue.qsize()
            
            # Cache statistics
            with self.cache_lock:
                cache_size = len(self.realtime_cache)
            
            return {
                'active_sessions': active_sessions,
                'recent_events_1h': recent_events,
                'event_queue_size': queue_size,
                'cache_size': cache_size,
                'is_running': self.is_running,
                'config': asdict(self.config)
            }
            
        except Exception as e:
            logger.error(f"Failed to get real-time statistics: {e}")
            return {}
    
    def shutdown(self):
        """Shutdown the real-time recommendation system"""
        try:
            logger.info("Shutting down real-time recommendation system...")
            
            self.is_running = False
            
            # Wait for threads to finish
            if self.processing_thread:
                self.processing_thread.join(timeout=5.0)
            
            if self.update_thread:
                self.update_thread.join(timeout=5.0)
            
            # Process remaining events
            remaining_events = []
            try:
                while True:
                    event = self.event_queue.get_nowait()
                    remaining_events.append(event)
            except Empty:
                pass
            
            if remaining_events:
                self._process_events_batch(remaining_events)
            
            logger.info("Real-time recommendation system shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Utility functions for creating real-time events
def create_view_event(user_id: str, item_id: str, session_id: str, 
                     context: Dict[str, Any] = None) -> RealtimeEvent:
    """Create a view event"""
    return RealtimeEvent(
        user_id=user_id,
        event_type='view',
        item_id=item_id,
        timestamp=datetime.now(),
        session_id=session_id,
        context=context or {},
        metadata={}
    )

def create_like_event(user_id: str, item_id: str, session_id: str,
                     context: Dict[str, Any] = None) -> RealtimeEvent:
    """Create a like event"""
    return RealtimeEvent(
        user_id=user_id,
        event_type='like',
        item_id=item_id,
        timestamp=datetime.now(),
        session_id=session_id,
        context=context or {},
        metadata={}
    )

def create_rating_event(user_id: str, item_id: str, rating: float, session_id: str,
                       context: Dict[str, Any] = None) -> RealtimeEvent:
    """Create a rating event"""
    return RealtimeEvent(
        user_id=user_id,
        event_type='rating',
        item_id=item_id,
        timestamp=datetime.now(),
        session_id=session_id,
        context=context or {},
        metadata={'rating': rating}
    )

def create_search_event(user_id: str, item_id: str, query: str, session_id: str,
                       context: Dict[str, Any] = None) -> RealtimeEvent:
    """Create a search event"""
    return RealtimeEvent(
        user_id=user_id,
        event_type='search',
        item_id=item_id,
        timestamp=datetime.now(),
        session_id=session_id,
        context=context or {},
        metadata={'query': query}
    )
