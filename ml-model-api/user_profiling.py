"""
User Profiling System for FlavorSnap Recommendation Engine

This module handles user profile creation, management, and analysis
for personalized food recommendations.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import sqlite3
import hashlib
from db_config import get_connection

logger = logging.getLogger(__name__)

@dataclass
class UserPreference:
    """User food preference data structure"""
    food_category: str
    preference_score: float  # 0.0 to 1.0
    interaction_count: int
    last_interaction: datetime
    avg_rating: Optional[float] = None
    tags: List[str] = None

@dataclass
class UserProfile:
    """Complete user profile"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    preferences: Dict[str, UserPreference]
    dietary_restrictions: List[str]
    cuisine_preferences: List[str]
    flavor_profile: Dict[str, float]  # sweet, sour, salty, bitter, umami
    interaction_history: List[Dict]
    recommendation_feedback: Dict[str, float]  # item_id -> feedback_score
    
class UserProfilingSystem:
    """Main user profiling system"""
    
    def __init__(self, db_connection=None):
        self.db_connection = db_connection or get_connection()
        self.flavor_dimensions = ['sweet', 'sour', 'salty', 'bitter', 'umami', 'spicy']
        self._init_database()
    
    def _init_database(self):
        """Initialize user profiling database tables"""
        if not self.db_connection:
            logger.warning("No database connection available for user profiling")
            return
            
        try:
            cursor = self.db_connection.cursor()
            
            # User profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    dietary_restrictions TEXT,
                    cuisine_preferences TEXT,
                    flavor_profile TEXT,
                    profile_data TEXT
                )
            """)
            
            # User preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    food_category TEXT,
                    preference_score REAL,
                    interaction_count INTEGER,
                    last_interaction TIMESTAMP,
                    avg_rating REAL,
                    tags TEXT,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id),
                    UNIQUE(user_id, food_category)
                )
            """)
            
            # Interaction history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    food_category TEXT,
                    interaction_type TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rating REAL,
                    feedback_score REAL,
                    metadata TEXT,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                )
            """)
            
            # Recommendation feedback table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendation_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    item_id TEXT,
                    feedback_score REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    feedback_type TEXT,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                )
            """)
            
            self.db_connection.commit()
            logger.info("User profiling database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize user profiling database: {e}")
    
    def create_user_profile(self, user_id: str, dietary_restrictions: List[str] = None,
                          cuisine_preferences: List[str] = None) -> UserProfile:
        """Create a new user profile"""
        try:
            profile = UserProfile(
                user_id=user_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                preferences={},
                dietary_restrictions=dietary_restrictions or [],
                cuisine_preferences=cuisine_preferences or [],
                flavor_profile={dim: 0.5 for dim in self.flavor_dimensions},
                interaction_history=[],
                recommendation_feedback={}
            )
            
            self._save_profile(profile)
            logger.info(f"Created user profile for {user_id}")
            return profile
            
        except Exception as e:
            logger.error(f"Failed to create user profile for {user_id}: {e}")
            raise
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Retrieve user profile from database"""
        try:
            if not self.db_connection:
                return None
                
            cursor = self.db_connection.cursor()
            
            # Get main profile
            cursor.execute("""
                SELECT created_at, updated_at, dietary_restrictions, 
                       cuisine_preferences, flavor_profile, profile_data
                FROM user_profiles WHERE user_id = ?
            """, (user_id,))
            
            profile_data = cursor.fetchone()
            if not profile_data:
                return None
            
            # Get preferences
            cursor.execute("""
                SELECT food_category, preference_score, interaction_count,
                       last_interaction, avg_rating, tags
                FROM user_preferences WHERE user_id = ?
            """, (user_id,))
            
            preferences_data = cursor.fetchall()
            preferences = {}
            for pref in preferences_data:
                preferences[pref[0]] = UserPreference(
                    food_category=pref[0],
                    preference_score=pref[1],
                    interaction_count=pref[2],
                    last_interaction=datetime.fromisoformat(pref[3]) if pref[3] else datetime.now(),
                    avg_rating=pref[4],
                    tags=json.loads(pref[5]) if pref[5] else []
                )
            
            # Get interaction history
            cursor.execute("""
                SELECT food_category, interaction_type, timestamp, rating, 
                       feedback_score, metadata
                FROM user_interactions WHERE user_id = ?
                ORDER BY timestamp DESC LIMIT 100
            """, (user_id,))
            
            interactions_data = cursor.fetchall()
            interaction_history = []
            for interaction in interactions_data:
                interaction_history.append({
                    'food_category': interaction[0],
                    'interaction_type': interaction[1],
                    'timestamp': interaction[2],
                    'rating': interaction[3],
                    'feedback_score': interaction[4],
                    'metadata': json.loads(interaction[5]) if interaction[5] else {}
                })
            
            # Get recommendation feedback
            cursor.execute("""
                SELECT item_id, feedback_score FROM recommendation_feedback WHERE user_id = ?
            """, (user_id,))
            
            feedback_data = cursor.fetchall()
            recommendation_feedback = {item[0]: item[1] for item in feedback_data}
            
            return UserProfile(
                user_id=user_id,
                created_at=datetime.fromisoformat(profile_data[0]),
                updated_at=datetime.fromisoformat(profile_data[1]),
                preferences=preferences,
                dietary_restrictions=json.loads(profile_data[2]) if profile_data[2] else [],
                cuisine_preferences=json.loads(profile_data[3]) if profile_data[3] else [],
                flavor_profile=json.loads(profile_data[4]) if profile_data[4] else {},
                interaction_history=interaction_history,
                recommendation_feedback=recommendation_feedback
            )
            
        except Exception as e:
            logger.error(f"Failed to get user profile for {user_id}: {e}")
            return None
    
    def update_user_interaction(self, user_id: str, food_category: str, 
                              interaction_type: str, rating: Optional[float] = None,
                              feedback_score: Optional[float] = None,
                              metadata: Dict = None) -> bool:
        """Update user interaction and preferences"""
        try:
            if not self.db_connection:
                return False
                
            cursor = self.db_connection.cursor()
            
            # Record interaction
            cursor.execute("""
                INSERT INTO user_interactions 
                (user_id, food_category, interaction_type, rating, feedback_score, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, food_category, interaction_type, rating, feedback_score, 
                  json.dumps(metadata) if metadata else None))
            
            # Update or create preference
            cursor.execute("""
                SELECT preference_score, interaction_count, last_interaction, avg_rating, tags
                FROM user_preferences WHERE user_id = ? AND food_category = ?
            """, (user_id, food_category))
            
            existing_pref = cursor.fetchone()
            
            if existing_pref:
                # Update existing preference
                current_score = existing_pref[0]
                interaction_count = existing_pref[1] + 1
                
                # Calculate new preference score based on interaction
                if rating is not None:
                    weight = min(0.1, 1.0 / interaction_count)
                    new_score = current_score * (1 - weight) + (rating / 5.0) * weight
                elif feedback_score is not None:
                    weight = min(0.1, 1.0 / interaction_count)
                    new_score = current_score * (1 - weight) + max(0, feedback_score) * weight
                else:
                    # Simple interaction boost
                    new_score = min(1.0, current_score + 0.01)
                
                # Update average rating
                avg_rating = existing_pref[3]
                if rating is not None:
                    if avg_rating is None:
                        avg_rating = rating
                    else:
                        avg_rating = (avg_rating * (interaction_count - 1) + rating) / interaction_count
                
                cursor.execute("""
                    UPDATE user_preferences 
                    SET preference_score = ?, interaction_count = ?, 
                        last_interaction = CURRENT_TIMESTAMP, avg_rating = ?
                    WHERE user_id = ? AND food_category = ?
                """, (new_score, interaction_count, avg_rating, user_id, food_category))
                
            else:
                # Create new preference
                initial_score = 0.5
                if rating is not None:
                    initial_score = rating / 5.0
                elif feedback_score is not None:
                    initial_score = max(0, feedback_score)
                
                cursor.execute("""
                    INSERT INTO user_preferences 
                    (user_id, food_category, preference_score, interaction_count, 
                     last_interaction, avg_rating, tags)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
                """, (user_id, food_category, initial_score, 1, rating, '[]'))
            
            # Update profile timestamp
            cursor.execute("""
                UPDATE user_profiles SET updated_at = CURRENT_TIMESTAMP WHERE user_id = ?
            """, (user_id,))
            
            self.db_connection.commit()
            logger.info(f"Updated interaction for user {user_id} with {food_category}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update user interaction: {e}")
            return False
    
    def update_recommendation_feedback(self, user_id: str, item_id: str, 
                                     feedback_score: float, feedback_type: str = 'explicit') -> bool:
        """Update feedback on recommendations"""
        try:
            if not self.db_connection:
                return False
                
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO recommendation_feedback 
                (user_id, item_id, feedback_score, feedback_type)
                VALUES (?, ?, ?, ?)
            """, (user_id, item_id, feedback_score, feedback_type))
            
            # Update profile timestamp
            cursor.execute("""
                UPDATE user_profiles SET updated_at = CURRENT_TIMESTAMP WHERE user_id = ?
            """, (user_id,))
            
            self.db_connection.commit()
            logger.info(f"Updated recommendation feedback for user {user_id}, item {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update recommendation feedback: {e}")
            return False
    
    def get_user_preferences_summary(self, user_id: str, top_n: int = 10) -> List[Tuple[str, float]]:
        """Get top user preferences"""
        try:
            if not self.db_connection:
                return []
                
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                SELECT food_category, preference_score 
                FROM user_preferences 
                WHERE user_id = ? AND interaction_count > 0
                ORDER BY preference_score DESC, interaction_count DESC
                LIMIT ?
            """, (user_id, top_n))
            
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Failed to get user preferences summary: {e}")
            return []
    
    def calculate_user_similarity(self, user_id1: str, user_id2: str) -> float:
        """Calculate similarity between two users based on preferences"""
        try:
            profile1 = self.get_user_profile(user_id1)
            profile2 = self.get_user_profile(user_id2)
            
            if not profile1 or not profile2:
                return 0.0
            
            # Get common categories
            categories1 = set(profile1.preferences.keys())
            categories2 = set(profile2.preferences.keys())
            common_categories = categories1.intersection(categories2)
            
            if not common_categories:
                return 0.0
            
            # Calculate cosine similarity
            similarity = 0.0
            for category in common_categories:
                pref1 = profile1.preferences[category].preference_score
                pref2 = profile2.preferences[category].preference_score
                similarity += pref1 * pref2
            
            # Normalize
            norm1 = sum(p.preference_score ** 2 for p in profile1.preferences.values()) ** 0.5
            norm2 = sum(p.preference_score ** 2 for p in profile2.preferences.values()) ** 0.5
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return similarity / (norm1 * norm2)
            
        except Exception as e:
            logger.error(f"Failed to calculate user similarity: {e}")
            return 0.0
    
    def get_similar_users(self, user_id: str, limit: int = 10) -> List[Tuple[str, float]]:
        """Find similar users based on preferences"""
        try:
            if not self.db_connection:
                return []
                
            cursor = self.db_connection.cursor()
            
            # Get all users except the target user
            cursor.execute("""
                SELECT user_id FROM user_profiles WHERE user_id != ?
            """, (user_id,))
            
            other_users = [row[0] for row in cursor.fetchall()]
            
            # Calculate similarities
            similarities = []
            for other_user in other_users:
                similarity = self.calculate_user_similarity(user_id, other_user)
                if similarity > 0:
                    similarities.append((other_user, similarity))
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get similar users: {e}")
            return []
    
    def update_flavor_profile(self, user_id: str, food_category: str, 
                            flavor_adjustments: Dict[str, float]) -> bool:
        """Update user's flavor profile based on interaction"""
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return False
            
            # Apply flavor adjustments with learning rate
            learning_rate = 0.1
            for flavor, adjustment in flavor_adjustments.items():
                if flavor in profile.flavor_profile:
                    current_value = profile.flavor_profile[flavor]
                    profile.flavor_profile[flavor] = max(0, min(1, 
                        current_value + learning_rate * (adjustment - current_value)))
            
            profile.updated_at = datetime.now()
            self._save_profile(profile)
            
            logger.info(f"Updated flavor profile for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update flavor profile: {e}")
            return False
    
    def _save_profile(self, profile: UserProfile) -> bool:
        """Save user profile to database"""
        try:
            if not self.db_connection:
                return False
                
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_profiles 
                (user_id, created_at, updated_at, dietary_restrictions, 
                 cuisine_preferences, flavor_profile, profile_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.user_id,
                profile.created_at.isoformat(),
                profile.updated_at.isoformat(),
                json.dumps(profile.dietary_restrictions),
                json.dumps(profile.cuisine_preferences),
                json.dumps(profile.flavor_profile),
                json.dumps(asdict(profile))
            ))
            
            self.db_connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save user profile: {e}")
            return False
    
    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return {}
            
            # Calculate statistics
            total_interactions = len(profile.interaction_history)
            unique_categories = len(profile.preferences)
            avg_preference_score = sum(p.preference_score for p in profile.preferences.values()) / max(1, len(profile.preferences))
            
            # Recent activity (last 30 days)
            cutoff_date = datetime.now() - timedelta(days=30)
            recent_interactions = [i for i in profile.interaction_history 
                                if datetime.fromisoformat(i['timestamp']) > cutoff_date]
            
            # Top categories
            top_categories = sorted(profile.preferences.items(), 
                                 key=lambda x: x[1].preference_score, reverse=True)[:5]
            
            return {
                'user_id': user_id,
                'total_interactions': total_interactions,
                'unique_categories': unique_categories,
                'avg_preference_score': avg_preference_score,
                'recent_interactions_30d': len(recent_interactions),
                'top_categories': [(cat, pref.preference_score) for cat, pref in top_categories],
                'dietary_restrictions': profile.dietary_restrictions,
                'cuisine_preferences': profile.cuisine_preferences,
                'flavor_profile': profile.flavor_profile,
                'profile_age_days': (datetime.now() - profile.created_at).days
            }
            
        except Exception as e:
            logger.error(f"Failed to get user statistics: {e}")
            return {}

# Utility functions
def generate_user_id(email: str = None) -> str:
    """Generate unique user ID"""
    if email:
        return hashlib.md5(email.encode()).hexdigest()[:16]
    else:
        return hashlib.md5(datetime.now().isoformat().encode()).hexdigest()[:16]

def map_rating_to_preference_score(rating: float) -> float:
    """Convert 1-5 rating to 0-1 preference score"""
    return max(0, min(1, (rating - 1) / 4))

def map_feedback_to_preference_score(feedback: float) -> float:
    """Convert feedback score (-1 to 1) to preference score (0 to 1)"""
    return max(0, min(1, (feedback + 1) / 2))
