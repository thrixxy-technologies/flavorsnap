"""
Content-Based Recommendation Engine for FlavorSnap

This module implements content-based filtering using food item features,
user preferences, and similarity matching algorithms.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict, Counter
import logging
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import json
import re
from db_config import get_connection

logger = logging.getLogger(__name__)

@dataclass
class FoodItem:
    """Food item with features"""
    item_id: str
    name: str
    category: str
    cuisine_type: str
    ingredients: List[str]
    flavor_profile: Dict[str, float]  # sweet, sour, salty, bitter, umami, spicy
    nutritional_info: Dict[str, float]  # calories, protein, carbs, fat, etc.
    dietary_tags: List[str]  # vegetarian, vegan, gluten-free, etc.
    preparation_methods: List[str]
    texture_profile: List[str]
    allergens: List[str]
    description: str

@dataclass
class ContentBasedConfig:
    """Configuration for content-based filtering"""
    min_similarity_threshold: float = 0.1
    max_recommendations: int = 50
    flavor_weight: float = 0.3
    cuisine_weight: float = 0.2
    ingredient_weight: float = 0.25
    dietary_weight: float = 0.15
    texture_weight: float = 0.1
    tfidf_max_features: int = 5000
    tfidf_min_df: int = 2

class ContentBasedEngine:
    """Main content-based recommendation engine"""
    
    def __init__(self, config: ContentBasedConfig = None, db_connection=None):
        self.config = config or ContentBasedConfig()
        self.db_connection = db_connection or get_connection()
        self.food_items: Dict[str, FoodItem] = {}
        self.feature_matrix = None
        self.item_indices = {}
        self.tfidf_vectorizer = None
        self.scaler = StandardScaler()
        self._init_database()
        self._load_food_items()
    
    def _init_database(self):
        """Initialize content-based filtering database tables"""
        if not self.db_connection:
            logger.warning("No database connection available for content-based filtering")
            return
            
        try:
            cursor = self.db_connection.cursor()
            
            # Food items table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS food_items (
                    item_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT,
                    cuisine_type TEXT,
                    ingredients TEXT,
                    flavor_profile TEXT,
                    nutritional_info TEXT,
                    dietary_tags TEXT,
                    preparation_methods TEXT,
                    texture_profile TEXT,
                    allergens TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Feature vectors cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content_feature_cache (
                    item_id TEXT PRIMARY KEY,
                    feature_vector BLOB,
                    feature_version INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (item_id) REFERENCES food_items (item_id)
                )
            """)
            
            # Similarity cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content_similarity_cache (
                    item1_id TEXT,
                    item2_id TEXT,
                    similarity_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (item1_id, item2_id),
                    FOREIGN KEY (item1_id) REFERENCES food_items (item_id),
                    FOREIGN KEY (item2_id) REFERENCES food_items (item_id)
                )
            """)
            
            self.db_connection.commit()
            logger.info("Content-based filtering database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize content-based filtering database: {e}")
    
    def _load_food_items(self):
        """Load food items from database"""
        try:
            if not self.db_connection:
                return
                
            cursor = self.db_connection.cursor()
            
            # Load sample food items if table is empty
            cursor.execute("SELECT COUNT(*) FROM food_items")
            if cursor.fetchone()[0] == 0:
                self._load_sample_food_items()
            
            # Load all food items
            cursor.execute("""
                SELECT item_id, name, category, cuisine_type, ingredients,
                       flavor_profile, nutritional_info, dietary_tags,
                       preparation_methods, texture_profile, allergens, description
                FROM food_items
            """)
            
            rows = cursor.fetchall()
            
            for row in rows:
                food_item = FoodItem(
                    item_id=row[0],
                    name=row[1],
                    category=row[2],
                    cuisine_type=row[3],
                    ingredients=json.loads(row[4]) if row[4] else [],
                    flavor_profile=json.loads(row[5]) if row[5] else {},
                    nutritional_info=json.loads(row[6]) if row[6] else {},
                    dietary_tags=json.loads(row[7]) if row[7] else [],
                    preparation_methods=json.loads(row[8]) if row[8] else [],
                    texture_profile=json.loads(row[9]) if row[9] else [],
                    allergens=json.loads(row[10]) if row[10] else [],
                    description=row[11] or ""
                )
                self.food_items[row[0]] = food_item
            
            logger.info(f"Loaded {len(self.food_items)} food items")
            
        except Exception as e:
            logger.error(f"Failed to load food items: {e}")
    
    def _load_sample_food_items(self):
        """Load sample food items for testing"""
        try:
            if not self.db_connection:
                return
                
            cursor = self.db_connection.cursor()
            
            sample_items = [
                {
                    'item_id': 'akara_001',
                    'name': 'Akara (Bean Cake)',
                    'category': 'Akara',
                    'cuisine_type': 'Nigerian',
                    'ingredients': ['beans', 'onions', 'pepper', 'oil', 'salt'],
                    'flavor_profile': {'savory': 0.7, 'spicy': 0.3, 'salty': 0.5},
                    'nutritional_info': {'calories': 200, 'protein': 8, 'carbs': 15, 'fat': 12},
                    'dietary_tags': ['vegetarian', 'gluten-free'],
                    'preparation_methods': ['fried', 'deep-fried'],
                    'texture_profile': ['crispy', 'soft'],
                    'allergens': [],
                    'description': 'Traditional Nigerian bean cakes made from black-eyed peas'
                },
                {
                    'item_id': 'bread_001',
                    'name': 'Sourdough Bread',
                    'category': 'Bread',
                    'cuisine_type': 'International',
                    'ingredients': ['flour', 'water', 'salt', 'sourdough starter'],
                    'flavor_profile': {'sour': 0.6, 'salty': 0.3, 'savory': 0.4},
                    'nutritional_info': {'calories': 250, 'protein': 10, 'carbs': 50, 'fat': 1},
                    'dietary_tags': ['vegetarian'],
                    'preparation_methods': ['baked'],
                    'texture_profile': ['chewy', 'crusty'],
                    'allergens': ['gluten'],
                    'description': 'Artisanal sourdough bread with natural fermentation'
                },
                {
                    'item_id': 'egusi_001',
                    'name': 'Egusi Soup',
                    'category': 'Egusi',
                    'cuisine_type': 'Nigerian',
                    'ingredients': ['egusi seeds', 'palm oil', 'vegetables', 'meat', 'spices'],
                    'flavor_profile': {'savory': 0.8, 'spicy': 0.4, 'rich': 0.7},
                    'nutritional_info': {'calories': 350, 'protein': 20, 'carbs': 10, 'fat': 28},
                    'dietary_tags': [],
                    'preparation_methods': ['boiled', 'simmered'],
                    'texture_profile': ['thick', 'creamy'],
                    'allergens': [],
                    'description': 'Rich Nigerian soup made from melon seeds'
                },
                {
                    'item_id': 'moimoi_001',
                    'name': 'Moi Moi (Bean Pudding)',
                    'category': 'Moi Moi',
                    'cuisine_type': 'Nigerian',
                    'ingredients': ['beans', 'pepper', 'onions', 'oil', 'eggs'],
                    'flavor_profile': {'savory': 0.6, 'mild': 0.4, 'spicy': 0.2},
                    'nutritional_info': {'calories': 180, 'protein': 12, 'carbs': 12, 'fat': 8},
                    'dietary_tags': ['vegetarian', 'gluten-free'],
                    'preparation_methods': ['steamed'],
                    'texture_profile': ['soft', 'smooth'],
                    'allergens': [],
                    'description': 'Steamed bean pudding, a Nigerian delicacy'
                }
            ]
            
            for item in sample_items:
                cursor.execute("""
                    INSERT INTO food_items 
                    (item_id, name, category, cuisine_type, ingredients,
                     flavor_profile, nutritional_info, dietary_tags,
                     preparation_methods, texture_profile, allergens, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item['item_id'], item['name'], item['category'], item['cuisine_type'],
                    json.dumps(item['ingredients']), json.dumps(item['flavor_profile']),
                    json.dumps(item['nutritional_info']), json.dumps(item['dietary_tags']),
                    json.dumps(item['preparation_methods']), json.dumps(item['texture_profile']),
                    json.dumps(item['allergens']), item['description']
                ))
            
            self.db_connection.commit()
            logger.info("Loaded sample food items")
            
        except Exception as e:
            logger.error(f"Failed to load sample food items: {e}")
    
    def extract_features(self, food_item: FoodItem) -> np.ndarray:
        """Extract feature vector from food item"""
        try:
            features = []
            
            # Flavor profile features
            flavor_dims = ['sweet', 'sour', 'salty', 'bitter', 'umami', 'spicy', 'savory', 'rich', 'mild']
            flavor_features = [food_item.flavor_profile.get(dim, 0.0) for dim in flavor_dims]
            features.extend(flavor_features)
            
            # Cuisine type (one-hot encoding)
            cuisine_types = ['Nigerian', 'International', 'Asian', 'European', 'American', 'Mediterranean']
            cuisine_features = [1.0 if food_item.cuisine_type == cuisine else 0.0 for cuisine in cuisine_types]
            features.extend(cuisine_features)
            
            # Dietary tags (multi-hot encoding)
            dietary_tags = ['vegetarian', 'vegan', 'gluten-free', 'dairy-free', 'nut-free', 'halal', 'kosher']
            dietary_features = [1.0 if tag in food_item.dietary_tags else 0.0 for tag in dietary_tags]
            features.extend(dietary_features)
            
            # Preparation methods (multi-hot encoding)
            prep_methods = ['fried', 'baked', 'grilled', 'boiled', 'steamed', 'roasted', 'simmered']
            prep_features = [1.0 if method in food_item.preparation_methods else 0.0 for method in prep_methods]
            features.extend(prep_features)
            
            # Texture profile (multi-hot encoding)
            textures = ['crispy', 'soft', 'chewy', 'crusty', 'smooth', 'thick', 'creamy']
            texture_features = [1.0 if texture in food_item.texture_profile else 0.0 for texture in textures]
            features.extend(texture_features)
            
            # Nutritional features (normalized)
            nutritional_features = [
                food_item.nutritional_info.get('calories', 0) / 500,  # Normalize to 0-1
                food_item.nutritional_info.get('protein', 0) / 50,
                food_item.nutritional_info.get('carbs', 0) / 100,
                food_item.nutritional_info.get('fat', 0) / 50
            ]
            features.extend(nutritional_features)
            
            # Text features (TF-IDF)
            text_content = f"{food_item.name} {food_item.description} {' '.join(food_item.ingredients)}"
            
            return np.array(features)
            
        except Exception as e:
            logger.error(f"Failed to extract features for {food_item.item_id}: {e}")
            return np.zeros(50)  # Return zero vector as fallback
    
    def build_feature_matrix(self) -> bool:
        """Build feature matrix for all food items"""
        try:
            if not self.food_items:
                logger.warning("No food items available for feature matrix")
                return False
            
            # Extract features for all items
            item_ids = list(self.food_items.keys())
            feature_vectors = []
            
            for item_id in item_ids:
                features = self.extract_features(self.food_items[item_id])
                feature_vectors.append(features)
            
            # Create feature matrix
            self.feature_matrix = np.array(feature_vectors)
            
            # Create item index mapping
            self.item_indices = {item_id: idx for idx, item_id in enumerate(item_ids)}
            
            # Normalize features
            self.feature_matrix = self.scaler.fit_transform(self.feature_matrix)
            
            logger.info(f"Built feature matrix: {len(item_ids)} items, {self.feature_matrix.shape[1]} features")
            return True
            
        except Exception as e:
            logger.error(f"Failed to build feature matrix: {e}")
            return False
    
    def calculate_item_similarity(self, item1_id: str, item2_id: str) -> float:
        """Calculate similarity between two food items"""
        try:
            if item1_id not in self.item_indices or item2_id not in self.item_indices:
                return 0.0
            
            if self.feature_matrix is None:
                if not self.build_feature_matrix():
                    return 0.0
            
            idx1 = self.item_indices[item1_id]
            idx2 = self.item_indices[item2_id]
            
            # Calculate cosine similarity
            vector1 = self.feature_matrix[idx1].reshape(1, -1)
            vector2 = self.feature_matrix[idx2].reshape(1, -1)
            
            similarity = cosine_similarity(vector1, vector2)[0, 0]
            
            return max(0, similarity)  # Ensure non-negative
            
        except Exception as e:
            logger.error(f"Failed to calculate item similarity: {e}")
            return 0.0
    
    def get_similar_items(self, item_id: str, n_similar: int = 10) -> List[Tuple[str, float]]:
        """Get similar items for a given food item"""
        try:
            if item_id not in self.item_indices:
                return []
            
            if self.feature_matrix is None:
                if not self.build_feature_matrix():
                    return []
            
            item_idx = self.item_indices[item_id]
            item_vector = self.feature_matrix[item_idx].reshape(1, -1)
            
            # Calculate similarities with all items
            similarities = cosine_similarity(item_vector, self.feature_matrix)[0]
            
            # Get top similar items (excluding the item itself)
            similar_indices = np.argsort(similarities)[::-1][1:n_similar+1]
            
            similar_items = []
            for idx in similar_indices:
                similar_item_id = list(self.item_indices.keys())[idx]
                similarity_score = similarities[idx]
                if similarity_score >= self.config.min_similarity_threshold:
                    similar_items.append((similar_item_id, similarity_score))
            
            return similar_items
            
        except Exception as e:
            logger.error(f"Failed to get similar items: {e}")
            return []
    
    def get_user_based_recommendations(self, user_preferences: Dict[str, float], 
                                     user_history: List[str], 
                                     dietary_restrictions: List[str] = None,
                                     n_recommendations: int = 10) -> List[Tuple[str, float]]:
        """Get content-based recommendations based on user preferences"""
        try:
            if self.feature_matrix is None:
                if not self.build_feature_matrix():
                    return []
            
            # Build user profile from preferences and history
            user_profile_vector = self._build_user_profile_vector(user_preferences, user_history)
            
            # Calculate similarities with all items
            similarities = cosine_similarity(user_profile_vector.reshape(1, -1), self.feature_matrix)[0]
            
            # Filter out items the user has already interacted with
            user_history_set = set(user_history)
            
            # Filter by dietary restrictions
            recommendations = []
            for idx, similarity_score in enumerate(similarities):
                if similarity_score < self.config.min_similarity_threshold:
                    continue
                
                item_id = list(self.item_indices.keys())[idx]
                
                if item_id in user_history_set:
                    continue
                
                # Check dietary restrictions
                if dietary_restrictions:
                    item = self.food_items.get(item_id)
                    if item:
                        for restriction in dietary_restrictions:
                            if restriction.lower() in ['vegetarian'] and 'vegetarian' not in item.dietary_tags:
                                break
                            elif restriction.lower() in ['vegan'] and 'vegan' not in item.dietary_tags:
                                break
                            elif restriction.lower() in ['gluten-free'] and 'gluten-free' not in item.dietary_tags:
                                break
                        else:
                            recommendations.append((item_id, similarity_score))
                else:
                    recommendations.append((item_id, similarity_score))
            
            # Sort by similarity and return top recommendations
            recommendations.sort(key=lambda x: x[1], reverse=True)
            return recommendations[:n_recommendations]
            
        except Exception as e:
            logger.error(f"Failed to get user-based recommendations: {e}")
            return []
    
    def _build_user_profile_vector(self, user_preferences: Dict[str, float], 
                                 user_history: List[str]) -> np.ndarray:
        """Build user profile vector from preferences and history"""
        try:
            # Start with zero vector
            profile_vector = np.zeros(self.feature_matrix.shape[1])
            
            # Weight history items more heavily
            history_weight = 0.7
            preference_weight = 0.3
            
            # Add contribution from user history
            for item_id in user_history:
                if item_id in self.item_indices:
                    item_idx = self.item_indices[item_id]
                    profile_vector += history_weight * self.feature_matrix[item_idx]
            
            # Add contribution from user preferences
            for category, preference_score in user_preferences.items():
                # Find items in this category
                category_items = [item_id for item_id, item in self.food_items.items() 
                                if item.category == category and item_id in self.item_indices]
                
                if category_items:
                    # Average features of items in this category
                    category_vectors = [self.feature_matrix[self.item_indices[item_id]] 
                                     for item_id in category_items]
                    if category_vectors:
                        avg_category_vector = np.mean(category_vectors, axis=0)
                        profile_vector += preference_weight * preference_score * avg_category_vector
            
            # Normalize the profile vector
            norm = np.linalg.norm(profile_vector)
            if norm > 0:
                profile_vector = profile_vector / norm
            
            return profile_vector
            
        except Exception as e:
            logger.error(f"Failed to build user profile vector: {e}")
            return np.zeros(self.feature_matrix.shape[1] if self.feature_matrix is not None else 50)
    
    def get_explanation_for_recommendation(self, user_id: str, item_id: str, 
                                         user_preferences: Dict[str, float],
                                         user_history: List[str]) -> Dict[str, Any]:
        """Generate explanation for why an item was recommended"""
        try:
            if item_id not in self.food_items:
                return {}
            
            item = self.food_items[item_id]
            
            # Find similar items in user history
            similar_history_items = []
            for history_item_id in user_history:
                if history_item_id in self.food_items:
                    similarity = self.calculate_item_similarity(item_id, history_item_id)
                    if similarity > 0.3:
                        similar_history_items.append((history_item_id, similarity))
            
            # Find matching preferences
            matching_preferences = []
            for category, score in user_preferences.items():
                if item.category == category and score > 0.5:
                    matching_preferences.append((category, score))
            
            # Generate explanation
            explanation = {
                'item_name': item.name,
                'category_match': item.category in user_preferences,
                'cuisine_match': item.cuisine_type,
                'similar_history_items': similar_history_items[:3],
                'matching_preferences': matching_preferences[:3],
                'key_features': {
                    'flavor_profile': item.flavor_profile,
                    'dietary_tags': item.dietary_tags,
                    'preparation_methods': item.preparation_methods[:3]
                },
                'reasoning': []
            }
            
            # Build reasoning
            if similar_history_items:
                explanation['reasoning'].append(
                    f"Similar to items you've liked: {', '.join([self.food_items[item[0]].name for item in similar_history_items[:2]])}"
                )
            
            if matching_preferences:
                explanation['reasoning'].append(
                    f"Matches your preference for {matching_preferences[0][0]} food"
                )
            
            if item.dietary_tags:
                explanation['reasoning'].append(
                    f"Suitable for {', '.join(item.dietary_tags[:2])} diet"
                )
            
            return explanation
            
        except Exception as e:
            logger.error(f"Failed to generate explanation: {e}")
            return {}
    
    def update_food_item(self, food_item: FoodItem) -> bool:
        """Update or add a food item"""
        try:
            if not self.db_connection:
                return False
                
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO food_items 
                (item_id, name, category, cuisine_type, ingredients,
                 flavor_profile, nutritional_info, dietary_tags,
                 preparation_methods, texture_profile, allergens, description,
                 updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                food_item.item_id, food_item.name, food_item.category, food_item.cuisine_type,
                json.dumps(food_item.ingredients), json.dumps(food_item.flavor_profile),
                json.dumps(food_item.nutritional_info), json.dumps(food_item.dietary_tags),
                json.dumps(food_item.preparation_methods), json.dumps(food_item.texture_profile),
                json.dumps(food_item.allergens), food_item.description
            ))
            
            self.db_connection.commit()
            
            # Update in-memory food items
            self.food_items[food_item.item_id] = food_item
            
            # Rebuild feature matrix
            self.build_feature_matrix()
            
            logger.info(f"Updated food item: {food_item.item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update food item: {e}")
            return False
    
    def get_item_details(self, item_id: str) -> Optional[FoodItem]:
        """Get detailed information about a food item"""
        return self.food_items.get(item_id)
    
    def search_items_by_features(self, flavor_profile: Dict[str, float] = None,
                                cuisine_type: str = None,
                                dietary_tags: List[str] = None,
                                ingredients: List[str] = None) -> List[str]:
        """Search for items by specific features"""
        try:
            matching_items = []
            
            for item_id, item in self.food_items.items():
                match = True
                
                # Check flavor profile
                if flavor_profile:
                    for flavor, target_value in flavor_profile.items():
                        item_value = item.flavor_profile.get(flavor, 0)
                        if abs(item_value - target_value) > 0.3:
                            match = False
                            break
                
                # Check cuisine type
                if cuisine_type and item.cuisine_type != cuisine_type:
                    match = False
                
                # Check dietary tags
                if dietary_tags:
                    if not all(tag in item.dietary_tags for tag in dietary_tags):
                        match = False
                
                # Check ingredients
                if ingredients:
                    if not all(ingredient.lower() in [ing.lower() for ing in item.ingredients] 
                             for ingredient in ingredients):
                        match = False
                
                if match:
                    matching_items.append(item_id)
            
            return matching_items
            
        except Exception as e:
            logger.error(f"Failed to search items by features: {e}")
            return []
    
    def get_recommendation_diversity_score(self, recommendations: List[Tuple[str, float]]) -> float:
        """Calculate diversity score for a set of recommendations"""
        try:
            if len(recommendations) < 2:
                return 0.0
            
            item_ids = [item_id for item_id, _ in recommendations]
            
            # Calculate pairwise similarities
            total_similarity = 0
            pair_count = 0
            
            for i in range(len(item_ids)):
                for j in range(i + 1, len(item_ids)):
                    similarity = self.calculate_item_similarity(item_ids[i], item_ids[j])
                    total_similarity += similarity
                    pair_count += 1
            
            # Diversity = 1 - average similarity
            avg_similarity = total_similarity / pair_count if pair_count > 0 else 0
            diversity = 1 - avg_similarity
            
            return diversity
            
        except Exception as e:
            logger.error(f"Failed to calculate diversity score: {e}")
            return 0.0
