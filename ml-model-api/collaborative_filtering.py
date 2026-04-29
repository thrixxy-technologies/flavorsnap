"""
Collaborative Filtering Recommendation Engine for FlavorSnap

This module implements user-based and item-based collaborative filtering
algorithms for food recommendations.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
import logging
from datetime import datetime, timedelta
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
import pickle
import os
from db_config import get_connection

logger = logging.getLogger(__name__)

@dataclass
class CollaborativeFilteringConfig:
    """Configuration for collaborative filtering"""
    min_user_interactions: int = 5
    min_item_interactions: int = 3
    similarity_threshold: float = 0.1
    max_neighbors: int = 50
    n_components: int = 50  # For matrix factorization
    learning_rate: float = 0.01
    regularization: float = 0.01
    n_epochs: int = 100

class CollaborativeFilteringEngine:
    """Main collaborative filtering engine"""
    
    def __init__(self, config: CollaborativeFilteringConfig = None, db_connection=None):
        self.config = config or CollaborativeFilteringConfig()
        self.db_connection = db_connection or get_connection()
        self.user_item_matrix = None
        self.user_similarity_matrix = None
        self.item_similarity_matrix = None
        self.user_to_index = {}
        self.item_to_index = {}
        self.index_to_user = {}
        self.index_to_item = {}
        self.svd_model = None
        self.user_factors = None
        self.item_factors = None
        self._init_database()
    
    def _init_database(self):
        """Initialize collaborative filtering database tables"""
        if not self.db_connection:
            logger.warning("No database connection available for collaborative filtering")
            return
            
        try:
            cursor = self.db_connection.cursor()
            
            # User-item interactions matrix cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cf_user_item_matrix (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    matrix_data BLOB,
                    user_mapping BLOB,
                    item_mapping BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 1
                )
            """)
            
            # Similarity matrices cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cf_similarity_matrices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    matrix_type TEXT,
                    matrix_data BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 1
                )
            """)
            
            # Model factors cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cf_model_factors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_factors BLOB,
                    item_factors BLOB,
                    model_config BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 1
                )
            """)
            
            self.db_connection.commit()
            logger.info("Collaborative filtering database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize collaborative filtering database: {e}")
    
    def build_user_item_matrix(self) -> bool:
        """Build user-item interaction matrix from database"""
        try:
            if not self.db_connection:
                return False
                
            cursor = self.db_connection.cursor()
            
            # Get user interactions with ratings
            cursor.execute("""
                SELECT user_id, food_category, AVG(CASE 
                    WHEN rating IS NOT NULL THEN rating 
                    WHEN feedback_score IS NOT NULL THEN (feedback_score + 1) * 2.5
                    ELSE 3.0
                END) as avg_rating,
                COUNT(*) as interaction_count
                FROM user_interactions 
                WHERE user_id IS NOT NULL AND food_category IS NOT NULL
                GROUP BY user_id, food_category
                HAVING interaction_count >= ?
            """, (self.config.min_user_interactions,))
            
            interactions = cursor.fetchall()
            
            if not interactions:
                logger.warning("No sufficient user interactions found")
                return False
            
            # Create mappings
            users = list(set(row[0] for row in interactions))
            items = list(set(row[1] for row in interactions))
            
            self.user_to_index = {user: idx for idx, user in enumerate(users)}
            self.item_to_index = {item: idx for idx, item in enumerate(items)}
            self.index_to_user = {idx: user for user, idx in self.user_to_index.items()}
            self.index_to_item = {idx: item for item, idx in self.item_to_index.items()}
            
            # Build sparse matrix
            rows = []
            cols = []
            data = []
            
            for user_id, item_id, rating, count in interactions:
                if user_id in self.user_to_index and item_id in self.item_to_index:
                    rows.append(self.user_to_index[user_id])
                    cols.append(self.item_to_index[item_id])
                    data.append(rating)
            
            self.user_item_matrix = csr_matrix((data, (rows, cols)), 
                                             shape=(len(users), len(items)))
            
            logger.info(f"Built user-item matrix: {len(users)} users, {len(items)} items, {len(data)} interactions")
            return True
            
        except Exception as e:
            logger.error(f"Failed to build user-item matrix: {e}")
            return False
    
    def compute_user_similarity(self) -> bool:
        """Compute user-user similarity matrix"""
        try:
            if self.user_item_matrix is None:
                if not self.build_user_item_matrix():
                    return False
            
            # Compute cosine similarity between users
            self.user_similarity_matrix = cosine_similarity(self.user_item_matrix)
            
            # Set diagonal to 0 (users are not similar to themselves)
            np.fill_diagonal(self.user_similarity_matrix, 0)
            
            # Apply similarity threshold
            self.user_similarity_matrix[self.user_similarity_matrix < self.config.similarity_threshold] = 0
            
            logger.info("Computed user similarity matrix")
            return True
            
        except Exception as e:
            logger.error(f"Failed to compute user similarity: {e}")
            return False
    
    def compute_item_similarity(self) -> bool:
        """Compute item-item similarity matrix"""
        try:
            if self.user_item_matrix is None:
                if not self.build_user_item_matrix():
                    return False
            
            # Compute cosine similarity between items (transpose matrix)
            self.item_similarity_matrix = cosine_similarity(self.user_item_matrix.T)
            
            # Set diagonal to 0
            np.fill_diagonal(self.item_similarity_matrix, 0)
            
            # Apply similarity threshold
            self.item_similarity_matrix[self.item_similarity_matrix < self.config.similarity_threshold] = 0
            
            logger.info("Computed item similarity matrix")
            return True
            
        except Exception as e:
            logger.error(f"Failed to compute item similarity: {e}")
            return False
    
    def train_matrix_factorization(self) -> bool:
        """Train matrix factorization model using SVD"""
        try:
            if self.user_item_matrix is None:
                if not self.build_user_item_matrix():
                    return False
            
            # Use Truncated SVD for matrix factorization
            self.svd_model = TruncatedSVD(n_components=self.config.n_components, 
                                         random_state=42)
            self.user_factors = self.svd_model.fit_transform(self.user_item_matrix)
            self.item_factors = self.svd_model.components_.T
            
            logger.info(f"Trained matrix factorization with {self.config.n_components} components")
            return True
            
        except Exception as e:
            logger.error(f"Failed to train matrix factorization: {e}")
            return False
    
    def get_user_based_recommendations(self, user_id: str, n_recommendations: int = 10) -> List[Tuple[str, float]]:
        """Get user-based collaborative filtering recommendations"""
        try:
            if user_id not in self.user_to_index:
                logger.warning(f"User {user_id} not found in user-item matrix")
                return []
            
            if self.user_similarity_matrix is None:
                if not self.compute_user_similarity():
                    return []
            
            user_idx = self.user_to_index[user_id]
            
            # Get similar users
            user_similarities = self.user_similarity_matrix[user_idx]
            similar_users = np.argsort(user_similarities)[::-1][:self.config.max_neighbors]
            
            # Get items the user hasn't interacted with
            user_ratings = self.user_item_matrix[user_idx].toarray().flatten()
            unrated_items = np.where(user_ratings == 0)[0]
            
            recommendations = []
            
            for item_idx in unrated_items:
                # Calculate predicted rating
                numerator = 0
                denominator = 0
                
                for similar_user_idx in similar_users:
                    similarity = user_similarities[similar_user_idx]
                    if similarity > 0:
                        rating = self.user_item_matrix[similar_user_idx, item_idx].toarray()[0, 0]
                        if rating > 0:
                            numerator += similarity * rating
                            denominator += similarity
                
                if denominator > 0:
                    predicted_rating = numerator / denominator
                    item_id = self.index_to_item[item_idx]
                    recommendations.append((item_id, predicted_rating))
            
            # Sort by predicted rating and return top recommendations
            recommendations.sort(key=lambda x: x[1], reverse=True)
            return recommendations[:n_recommendations]
            
        except Exception as e:
            logger.error(f"Failed to get user-based recommendations: {e}")
            return []
    
    def get_item_based_recommendations(self, user_id: str, n_recommendations: int = 10) -> List[Tuple[str, float]]:
        """Get item-based collaborative filtering recommendations"""
        try:
            if user_id not in self.user_to_index:
                logger.warning(f"User {user_id} not found in user-item matrix")
                return []
            
            if self.item_similarity_matrix is None:
                if not self.compute_item_similarity():
                    return []
            
            user_idx = self.user_to_index[user_id]
            
            # Get items the user has rated
            user_ratings = self.user_item_matrix[user_idx].toarray().flatten()
            rated_items = np.where(user_ratings > 0)[0]
            
            # Get items the user hasn't interacted with
            unrated_items = np.where(user_ratings == 0)[0]
            
            recommendations = []
            
            for item_idx in unrated_items:
                # Calculate predicted rating based on similar items
                numerator = 0
                denominator = 0
                
                for rated_item_idx in rated_items:
                    similarity = self.item_similarity_matrix[item_idx, rated_item_idx]
                    if similarity > 0:
                        rating = user_ratings[rated_item_idx]
                        numerator += similarity * rating
                        denominator += similarity
                
                if denominator > 0:
                    predicted_rating = numerator / denominator
                    item_id = self.index_to_item[item_idx]
                    recommendations.append((item_id, predicted_rating))
            
            # Sort by predicted rating and return top recommendations
            recommendations.sort(key=lambda x: x[1], reverse=True)
            return recommendations[:n_recommendations]
            
        except Exception as e:
            logger.error(f"Failed to get item-based recommendations: {e}")
            return []
    
    def get_matrix_factorization_recommendations(self, user_id: str, n_recommendations: int = 10) -> List[Tuple[str, float]]:
        """Get recommendations using matrix factorization"""
        try:
            if user_id not in self.user_to_index:
                logger.warning(f"User {user_id} not found in user-item matrix")
                return []
            
            if self.user_factors is None or self.item_factors is None:
                if not self.train_matrix_factorization():
                    return []
            
            user_idx = self.user_to_index[user_id]
            
            # Get items the user hasn't interacted with
            user_ratings = self.user_item_matrix[user_idx].toarray().flatten()
            unrated_items = np.where(user_ratings == 0)[0]
            
            # Calculate predicted ratings
            user_factor = self.user_factors[user_idx]
            predicted_ratings = np.dot(user_factor, self.item_factors.T)
            
            recommendations = []
            for item_idx in unrated_items:
                predicted_rating = predicted_ratings[item_idx]
                item_id = self.index_to_item[item_idx]
                recommendations.append((item_id, predicted_rating))
            
            # Sort by predicted rating and return top recommendations
            recommendations.sort(key=lambda x: x[1], reverse=True)
            return recommendations[:n_recommendations]
            
        except Exception as e:
            logger.error(f"Failed to get matrix factorization recommendations: {e}")
            return []
    
    def get_hybrid_cf_recommendations(self, user_id: str, n_recommendations: int = 10,
                                    user_weight: float = 0.4, item_weight: float = 0.4,
                                    mf_weight: float = 0.2) -> List[Tuple[str, float]]:
        """Get hybrid collaborative filtering recommendations"""
        try:
            # Get recommendations from different methods
            user_based_recs = self.get_user_based_recommendations(user_id, n_recommendations * 2)
            item_based_recs = self.get_item_based_recommendations(user_id, n_recommendations * 2)
            mf_recs = self.get_matrix_factorization_recommendations(user_id, n_recommendations * 2)
            
            # Combine recommendations
            combined_scores = defaultdict(float)
            
            # Add user-based recommendations
            for item_id, score in user_based_recs:
                combined_scores[item_id] += user_weight * score
            
            # Add item-based recommendations
            for item_id, score in item_based_recs:
                combined_scores[item_id] += item_weight * score
            
            # Add matrix factorization recommendations
            for item_id, score in mf_recs:
                combined_scores[item_id] += mf_weight * score
            
            # Sort and return top recommendations
            recommendations = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
            return recommendations[:n_recommendations]
            
        except Exception as e:
            logger.error(f"Failed to get hybrid CF recommendations: {e}")
            return []
    
    def get_similar_users(self, user_id: str, n_similar: int = 10) -> List[Tuple[str, float]]:
        """Get similar users for a given user"""
        try:
            if user_id not in self.user_to_index:
                return []
            
            if self.user_similarity_matrix is None:
                if not self.compute_user_similarity():
                    return []
            
            user_idx = self.user_to_index[user_id]
            user_similarities = self.user_similarity_matrix[user_idx]
            
            similar_users = []
            for idx, similarity in enumerate(user_similarities):
                if similarity > 0:
                    similar_user_id = self.index_to_user[idx]
                    similar_users.append((similar_user_id, similarity))
            
            # Sort by similarity and return top results
            similar_users.sort(key=lambda x: x[1], reverse=True)
            return similar_users[:n_similar]
            
        except Exception as e:
            logger.error(f"Failed to get similar users: {e}")
            return []
    
    def get_similar_items(self, item_id: str, n_similar: int = 10) -> List[Tuple[str, float]]:
        """Get similar items for a given item"""
        try:
            if item_id not in self.item_to_index:
                return []
            
            if self.item_similarity_matrix is None:
                if not self.compute_item_similarity():
                    return []
            
            item_idx = self.item_to_index[item_id]
            item_similarities = self.item_similarity_matrix[item_idx]
            
            similar_items = []
            for idx, similarity in enumerate(item_similarities):
                if similarity > 0:
                    similar_item_id = self.index_to_item[idx]
                    similar_items.append((similar_item_id, similarity))
            
            # Sort by similarity and return top results
            similar_items.sort(key=lambda x: x[1], reverse=True)
            return similar_items[:n_similar]
            
        except Exception as e:
            logger.error(f"Failed to get similar items: {e}")
            return []
    
    def evaluate_recommendations(self, test_users: List[str], n_recommendations: int = 10) -> Dict[str, float]:
        """Evaluate recommendation quality using test users"""
        try:
            precision_scores = []
            recall_scores = []
            f1_scores = []
            
            for user_id in test_users:
                if user_id not in self.user_to_index:
                    continue
                
                # Get recommendations
                recommendations = self.get_hybrid_cf_recommendations(user_id, n_recommendations)
                recommended_items = set(item_id for item_id, _ in recommendations)
                
                # Get actual items the user liked (rating >= 4)
                user_idx = self.user_to_index[user_id]
                user_ratings = self.user_item_matrix[user_idx].toarray().flatten()
                liked_items = set(self.index_to_item[idx] for idx, rating in enumerate(user_ratings) if rating >= 4)
                
                # Calculate metrics
                if len(recommended_items) > 0:
                    precision = len(recommended_items.intersection(liked_items)) / len(recommended_items)
                    precision_scores.append(precision)
                
                if len(liked_items) > 0:
                    recall = len(recommended_items.intersection(liked_items)) / len(liked_items)
                    recall_scores.append(recall)
                
                if precision_scores and recall_scores:
                    precision = precision_scores[-1]
                    recall = recall_scores[-1]
                    if precision + recall > 0:
                        f1 = 2 * (precision * recall) / (precision + recall)
                        f1_scores.append(f1)
            
            return {
                'precision': np.mean(precision_scores) if precision_scores else 0,
                'recall': np.mean(recall_scores) if recall_scores else 0,
                'f1_score': np.mean(f1_scores) if f1_scores else 0,
                'coverage': len(set().union(*[set(rec.get_hybrid_cf_recommendations(user, n_recommendations)) for user in test_users])) / len(self.item_to_index) if test_users else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate recommendations: {e}")
            return {'precision': 0, 'recall': 0, 'f1_score': 0, 'coverage': 0}
    
    def save_model(self, filepath: str) -> bool:
        """Save trained model to file"""
        try:
            model_data = {
                'user_item_matrix': self.user_item_matrix,
                'user_similarity_matrix': self.user_similarity_matrix,
                'item_similarity_matrix': self.item_similarity_matrix,
                'user_to_index': self.user_to_index,
                'item_to_index': self.item_to_index,
                'index_to_user': self.index_to_user,
                'index_to_item': self.index_to_item,
                'svd_model': self.svd_model,
                'user_factors': self.user_factors,
                'item_factors': self.item_factors,
                'config': self.config
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model saved to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False
    
    def load_model(self, filepath: str) -> bool:
        """Load trained model from file"""
        try:
            if not os.path.exists(filepath):
                logger.warning(f"Model file {filepath} does not exist")
                return False
            
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.user_item_matrix = model_data['user_item_matrix']
            self.user_similarity_matrix = model_data['user_similarity_matrix']
            self.item_similarity_matrix = model_data['item_similarity_matrix']
            self.user_to_index = model_data['user_to_index']
            self.item_to_index = model_data['item_to_index']
            self.index_to_user = model_data['index_to_user']
            self.index_to_item = model_data['index_to_item']
            self.svd_model = model_data['svd_model']
            self.user_factors = model_data['user_factors']
            self.item_factors = model_data['item_factors']
            self.config = model_data['config']
            
            logger.info(f"Model loaded from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    def update_with_new_interaction(self, user_id: str, item_id: str, rating: float) -> bool:
        """Update model with new user interaction"""
        try:
            # This is a simplified update - in production, you'd want more sophisticated incremental updates
            if user_id in self.user_to_index and item_id in self.item_to_index:
                user_idx = self.user_to_index[user_id]
                item_idx = self.item_to_index[item_id]
                
                # Update the user-item matrix
                current_rating = self.user_item_matrix[user_idx, item_idx].toarray()[0, 0]
                if current_rating == 0:
                    # New interaction
                    self.user_item_matrix[user_idx, item_idx] = rating
                else:
                    # Update existing interaction (simple average)
                    self.user_item_matrix[user_idx, item_idx] = (current_rating + rating) / 2
                
                logger.info(f"Updated interaction for user {user_id}, item {item_id}")
                return True
            else:
                # New user or item - would need to rebuild matrix
                logger.warning(f"New user or item detected - matrix rebuild required")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update with new interaction: {e}")
            return False
