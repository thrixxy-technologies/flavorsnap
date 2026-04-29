"""
Advanced Relationship Mapping for FlavorSnap Graph Database
Handles complex entity relationships and mapping logic
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import networkx as nx
from collections import defaultdict, Counter
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

from .graph_db import GraphDatabaseManager, NodeType, RelationType, GraphNode, GraphRelationship

logger = logging.getLogger(__name__)

class RelationshipStrength(Enum):
    """Relationship strength levels"""
    WEAK = 0.2
    MODERATE = 0.5
    STRONG = 0.8
    VERY_STRONG = 1.0

class MappingStrategy(Enum):
    """Relationship mapping strategies"""
    COLLABORATIVE_FILTERING = "collaborative_filtering"
    CONTENT_BASED = "content_based"
    HYBRID = "hybrid"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    SOCIAL_NETWORK = "social_network"

@dataclass
class RelationshipScore:
    """Represents a relationship score with metadata"""
    source_id: str
    target_id: str
    relationship_type: RelationType
    score: float
    confidence: float
    evidence: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_id': self.source_id,
            'target_id': self.target_id,
            'relationship_type': self.relationship_type.value,
            'score': self.score,
            'confidence': self.confidence,
            'evidence': self.evidence,
            'timestamp': self.timestamp.isoformat()
        }

class EntityRelationshipMapper:
    """Advanced entity relationship mapping system"""
    
    def __init__(self, graph_db: GraphDatabaseManager):
        self.graph_db = graph_db
        self.similarity_threshold = 0.3
        self.min_interaction_count = 3
        self.decay_factor = 0.95
        self.temporal_window_days = 30
        
        # Relationship weights for different strategies
        self.strategy_weights = {
            MappingStrategy.COLLABORATIVE_FILTERING: 0.4,
            MappingStrategy.CONTENT_BASED: 0.3,
            MappingStrategy.KNOWLEDGE_GRAPH: 0.2,
            MappingStrategy.SOCIAL_NETWORK: 0.1
        }
    
    def map_user_food_relationships(self, user_id: str) -> List[RelationshipScore]:
        """Map relationships between user and food items"""
        relationships = []
        
        # Get user interaction history
        user_interactions = self._get_user_interactions(user_id)
        if not user_interactions:
            return relationships
        
        # Collaborative filtering relationships
        cf_relationships = self._collaborative_filtering_mapping(user_id, user_interactions)
        relationships.extend(cf_relationships)
        
        # Content-based relationships
        cb_relationships = self._content_based_mapping(user_id, user_interactions)
        relationships.extend(cb_relationships)
        
        # Social network relationships
        sn_relationships = self._social_network_mapping(user_id, user_interactions)
        relationships.extend(sn_relationships)
        
        # Sort by score and return top relationships
        relationships.sort(key=lambda x: x.score, reverse=True)
        return relationships[:50]
    
    def map_food_similarity_relationships(self, food_id: str) -> List[RelationshipScore]:
        """Map similarity relationships between food items"""
        relationships = []
        
        # Get food item details
        food_node = self.graph_db.get_node(food_id)
        if not food_node:
            return relationships
        
        # Content-based similarity
        content_similarities = self._calculate_content_similarity(food_id)
        for similar_food, similarity in content_similarities:
            if similarity > self.similarity_threshold:
                relationships.append(RelationshipScore(
                    source_id=food_id,
                    target_id=similar_food,
                    relationship_type=RelationType.SIMILAR_TO,
                    score=similarity,
                    confidence=0.8,
                    evidence=['content_similarity']
                ))
        
        # Collaborative similarity (users who like this also like...)
        collaborative_similarities = self._calculate_collaborative_similarity(food_id)
        for similar_food, similarity in collaborative_similarities:
            if similarity > self.similarity_threshold:
                relationships.append(RelationshipScore(
                    source_id=food_id,
                    target_id=similar_food,
                    relationship_type=RelationType.SIMILAR_TO,
                    score=similarity,
                    confidence=0.7,
                    evidence=['collaborative_similarity']
                ))
        
        return sorted(relationships, key=lambda x: x.score, reverse=True)[:20]
    
    def map_category_relationships(self, category_id: str) -> List[RelationshipScore]:
        """Map relationships between categories"""
        relationships = []
        
        # Get category hierarchy
        category_hierarchy = self._get_category_hierarchy(category_id)
        
        # Parent-child relationships
        for parent_id in category_hierarchy.get('parents', []):
            relationships.append(RelationshipScore(
                source_id=category_id,
                target_id=parent_id,
                relationship_type=RelationType.BELONGS_TO,
                score=0.9,
                confidence=1.0,
                evidence=['hierarchy']
            ))
        
        # Sibling relationships (categories with same parent)
        for sibling_id in category_hierarchy.get('siblings', []):
            relationships.append(RelationshipScore(
                source_id=category_id,
                target_id=sibling_id,
                relationship_type=RelationType.SIMILAR_TO,
                score=0.6,
                confidence=0.8,
                evidence=['same_parent']
            ))
        
        return relationships
    
    def map_ingredient_relationships(self, ingredient_id: str) -> List[RelationshipScore]:
        """Map relationships between ingredients"""
        relationships = []
        
        # Get ingredient properties
        ingredient_node = self.graph_db.get_node(ingredient_id)
        if not ingredient_node:
            return relationships
        
        # Complementary ingredients (often used together)
        complementary = self._find_complementary_ingredients(ingredient_id)
        for comp_ingredient, score in complementary:
            relationships.append(RelationshipScore(
                source_id=ingredient_id,
                target_id=comp_ingredient,
                relationship_type=RelationType.SIMILAR_TO,
                score=score,
                confidence=0.7,
                evidence=['complementary']
            ))
        
        # Substitution relationships
        substitutions = self._find_substitute_ingredients(ingredient_id)
        for sub_ingredient, score in substitutions:
            relationships.append(RelationshipScore(
                source_id=ingredient_id,
                target_id=sub_ingredient,
                relationship_type=RelationType.SIMILAR_TO,
                score=score,
                confidence=0.6,
                evidence=['substitution']
            ))
        
        return relationships
    
    def _get_user_interactions(self, user_id: str) -> Dict[str, Any]:
        """Get user interaction history"""
        neighbors = self.graph_db.get_neighbors(user_id, "LIKES")
        
        interactions = {
            'liked_foods': [],
            'ratings': {},
            'timestamps': {},
            'categories': set(),
            'ingredients': set()
        }
        
        for neighbor in neighbors:
            food_id = neighbor['node']['id']
            interactions['liked_foods'].append(food_id)
            
            # Get rating if available
            rating = neighbor['relationship_properties'].get('rating', 5)
            interactions['ratings'][food_id] = rating
            
            # Get timestamp
            timestamp = neighbor['relationship_properties'].get('timestamp')
            if timestamp:
                interactions['timestamps'][food_id] = timestamp
            
            # Get food categories and ingredients
            food_neighbors = self.graph_db.get_neighbors(food_id)
            for food_neighbor in food_neighbors:
                rel_type = food_neighbor['relationship_type']
                if rel_type == 'BELONGS_TO':
                    interactions['categories'].add(food_neighbor['node']['id'])
                elif rel_type == 'CONTAINS':
                    interactions['ingredients'].add(food_neighbor['node']['id'])
        
        return interactions
    
    def _collaborative_filtering_mapping(self, user_id: str, interactions: Dict[str, Any]) -> List[RelationshipScore]:
        """Generate collaborative filtering relationships"""
        relationships = []
        liked_foods = interactions['liked_foods']
        
        if not liked_foods:
            return relationships
        
        # Find similar users
        similar_users = self._find_similar_users(user_id, liked_foods)
        
        # Get foods liked by similar users but not by current user
        for similar_user, similarity_score in similar_users[:10]:
            user_neighbors = self.graph_db.get_neighbors(similar_user, "LIKES")
            
            for neighbor in user_neighbors:
                food_id = neighbor['node']['id']
                if food_id not in liked_foods:
                    # Calculate recommendation score
                    rating = neighbor['relationship_properties'].get('rating', 5)
                    score = similarity_score * (rating / 5.0) * 0.8
                    
                    relationships.append(RelationshipScore(
                        source_id=user_id,
                        target_id=food_id,
                        relationship_type=RelationType.RECOMMENDED,
                        score=score,
                        confidence=similarity_score,
                        evidence=['collaborative_filtering', f'similar_user_{similar_user}']
                    ))
        
        return relationships
    
    def _content_based_mapping(self, user_id: str, interactions: Dict[str, Any]) -> List[RelationshipScore]:
        """Generate content-based relationships"""
        relationships = []
        
        # Build user profile based on liked categories and ingredients
        user_categories = interactions['categories']
        user_ingredients = interactions['ingredients']
        
        if not user_categories and not user_ingredients:
            return relationships
        
        # Find foods with similar content
        potential_foods = self._find_similar_content_foods(user_categories, user_ingredients)
        
        for food_id, similarity_score in potential_foods:
            if food_id not in interactions['liked_foods']:
                relationships.append(RelationshipScore(
                    source_id=user_id,
                    target_id=food_id,
                    relationship_type=RelationType.RECOMMENDED,
                    score=similarity_score * 0.6,
                    confidence=0.7,
                    evidence=['content_based']
                ))
        
        return relationships
    
    def _social_network_mapping(self, user_id: str, interactions: Dict[str, Any]) -> List[RelationshipScore]:
        """Generate social network relationships"""
        relationships = []
        
        # Get user's social connections
        social_connections = self._get_social_connections(user_id)
        
        # Get foods liked by social connections
        for connection_id in social_connections:
            connection_neighbors = self.graph_db.get_neighbors(connection_id, "LIKES")
            
            for neighbor in connection_neighbors:
                food_id = neighbor['node']['id']
                if food_id not in interactions['liked_foods']:
                    # Social influence score
                    rating = neighbor['relationship_properties'].get('rating', 5)
                    score = (rating / 5.0) * 0.4
                    
                    relationships.append(RelationshipScore(
                        source_id=user_id,
                        target_id=food_id,
                        relationship_type=RelationType.RECOMMENDED,
                        score=score,
                        confidence=0.5,
                        evidence=['social_network', f'connection_{connection_id}']
                    ))
        
        return relationships
    
    def _find_similar_users(self, user_id: str, liked_foods: List[str]) -> List[Tuple[str, float]]:
        """Find users with similar tastes"""
        similar_users = []
        
        # Get all users who liked the same foods
        for food_id in liked_foods:
            food_neighbors = self.graph_db.get_neighbors(food_id, "LIKES")
            
            for neighbor in food_neighbors:
                other_user_id = neighbor['node']['id']
                if other_user_id != user_id:
                    # Calculate similarity based on common liked foods
                    other_user_liked = self._get_user_liked_foods(other_user_id)
                    common_foods = set(liked_foods) & set(other_user_liked)
                    
                    if len(common_foods) >= self.min_interaction_count:
                        similarity = len(common_foods) / len(set(liked_foods) | set(other_user_liked))
                        similar_users.append((other_user_id, similarity))
        
        # Remove duplicates and sort by similarity
        unique_similar = list(set(similar_users))
        unique_similar.sort(key=lambda x: x[1], reverse=True)
        
        return unique_similar
    
    def _get_user_liked_foods(self, user_id: str) -> List[str]:
        """Get list of foods liked by user"""
        neighbors = self.graph_db.get_neighbors(user_id, "LIKES")
        return [neighbor['node']['id'] for neighbor in neighbors]
    
    def _find_similar_content_foods(self, categories: Set[str], ingredients: Set[str]) -> List[Tuple[str, float]]:
        """Find foods with similar categories and ingredients"""
        similar_foods = []
        
        # Query foods with matching categories or ingredients
        for category in categories:
            category_neighbors = self.graph_db.get_neighbors(category, "BELONGS_TO")
            for neighbor in category_neighbors:
                food_id = neighbor['node']['id']
                # Calculate similarity based on category match
                similarity = 0.5  # Base score for category match
                
                # Boost if ingredients also match
                food_ingredients = self._get_food_ingredients(food_id)
                ingredient_overlap = len(ingredients & set(food_ingredients))
                if ingredient_overlap > 0:
                    similarity += 0.3 * (ingredient_overlap / len(ingredients))
                
                similar_foods.append((food_id, min(similarity, 1.0)))
        
        return similar_foods
    
    def _get_food_ingredients(self, food_id: str) -> List[str]:
        """Get ingredients for a food item"""
        neighbors = self.graph_db.get_neighbors(food_id, "CONTAINS")
        return [neighbor['node']['id'] for neighbor in neighbors]
    
    def _get_social_connections(self, user_id: str) -> List[str]:
        """Get user's social connections"""
        # This could be implemented based on social graph relationships
        # For now, return empty list
        return []
    
    def _calculate_content_similarity(self, food_id: str) -> List[Tuple[str, float]]:
        """Calculate content-based similarity between foods"""
        similarities = []
        
        # Get food properties
        food_node = self.graph_db.get_node(food_id)
        if not food_node:
            return similarities
        
        # Get food categories and ingredients
        food_categories = set()
        food_ingredients = set()
        
        neighbors = self.graph_db.get_neighbors(food_id)
        for neighbor in neighbors:
            rel_type = neighbor['relationship_type']
            if rel_type == 'BELONGS_TO':
                food_categories.add(neighbor['node']['id'])
            elif rel_type == 'CONTAINS':
                food_ingredients.add(neighbor['node']['id'])
        
        # Find similar foods
        all_foods = self._get_all_foods()
        for other_food_id in all_foods:
            if other_food_id == food_id:
                continue
            
            # Calculate similarity based on categories and ingredients
            other_categories = set(self._get_food_categories(other_food_id))
            other_ingredients = set(self._get_food_ingredients(other_food_id))
            
            category_similarity = len(food_categories & other_categories) / len(food_categories | other_categories) if (food_categories | other_categories) else 0
            ingredient_similarity = len(food_ingredients & other_ingredients) / len(food_ingredients | other_ingredients) if (food_ingredients | other_ingredients) else 0
            
            # Weighted similarity
            total_similarity = (category_similarity * 0.6 + ingredient_similarity * 0.4)
            
            if total_similarity > self.similarity_threshold:
                similarities.append((other_food_id, total_similarity))
        
        return sorted(similarities, key=lambda x: x[1], reverse=True)
    
    def _calculate_collaborative_similarity(self, food_id: str) -> List[Tuple[str, float]]:
        """Calculate collaborative similarity between foods"""
        similarities = []
        
        # Get users who liked this food
        food_likers = self._get_food_likers(food_id)
        
        if not food_likers:
            return similarities
        
        # Find foods liked by similar users
        food_co_occurrence = defaultdict(int)
        
        for user_id in food_likers:
            user_liked_foods = self._get_user_liked_foods(user_id)
            for other_food_id in user_liked_foods:
                if other_food_id != food_id:
                    food_co_occurrence[other_food_id] += 1
        
        # Calculate similarity scores
        for other_food_id, co_occurrence in food_co_occurrence.items():
            similarity = co_occurrence / len(food_likers)
            if similarity > self.similarity_threshold:
                similarities.append((other_food_id, similarity))
        
        return sorted(similarities, key=lambda x: x[1], reverse=True)
    
    def _get_all_foods(self) -> List[str]:
        """Get all food item IDs"""
        # This would typically query the database for all food items
        # For now, return empty list
        return []
    
    def _get_food_categories(self, food_id: str) -> List[str]:
        """Get categories for a food item"""
        neighbors = self.graph_db.get_neighbors(food_id, "BELONGS_TO")
        return [neighbor['node']['id'] for neighbor in neighbors]
    
    def _get_food_likers(self, food_id: str) -> List[str]:
        """Get users who liked a food item"""
        neighbors = self.graph_db.get_neighbors(food_id, "LIKES")
        return [neighbor['node']['id'] for neighbor in neighbors]
    
    def _get_category_hierarchy(self, category_id: str) -> Dict[str, List[str]]:
        """Get category hierarchy relationships"""
        hierarchy = {
            'parents': [],
            'children': [],
            'siblings': []
        }
        
        # Get parent categories
        neighbors = self.graph_db.get_neighbors(category_id, "BELONGS_TO")
        for neighbor in neighbors:
            if neighbor['node'].get('type') == 'Category':
                hierarchy['parents'].append(neighbor['node']['id'])
        
        # Get child categories
        neighbors = self.graph_db.get_neighbors(category_id, "BELONGS_TO")
        for neighbor in neighbors:
            if neighbor['node'].get('type') == 'Category':
                hierarchy['children'].append(neighbor['node']['id'])
        
        # Get siblings (categories with same parent)
        if hierarchy['parents']:
            for parent_id in hierarchy['parents']:
                siblings = self.graph_db.get_neighbors(parent_id, "BELONGS_TO")
                for sibling in siblings:
                    sibling_id = sibling['node']['id']
                    if sibling_id != category_id and sibling_id not in hierarchy['siblings']:
                        hierarchy['siblings'].append(sibling_id)
        
        return hierarchy
    
    def _find_complementary_ingredients(self, ingredient_id: str) -> List[Tuple[str, float]]:
        """Find complementary ingredients based on co-occurrence"""
        complementary = []
        
        # Get recipes containing this ingredient
        recipes = self._get_recipes_with_ingredient(ingredient_id)
        
        # Find other ingredients in the same recipes
        ingredient_co_occurrence = defaultdict(int)
        
        for recipe_id in recipes:
            recipe_ingredients = self._get_recipe_ingredients(recipe_id)
            for other_ingredient in recipe_ingredients:
                if other_ingredient != ingredient_id:
                    ingredient_co_occurrence[other_ingredient] += 1
        
        # Calculate complementary scores
        for other_ingredient, co_occurrence in ingredient_co_occurrence.items():
            if co_occurrence >= 2:  # Minimum co-occurrence threshold
                score = min(co_occurrence / len(recipes), 1.0)
                complementary.append((other_ingredient, score))
        
        return sorted(complementary, key=lambda x: x[1], reverse=True)[:10]
    
    def _find_substitute_ingredients(self, ingredient_id: str) -> List[Tuple[str, float]]:
        """Find substitute ingredients based on properties"""
        substitutes = []
        
        # Get ingredient properties
        ingredient_node = self.graph_db.get_node(ingredient_id)
        if not ingredient_node:
            return substitutes
        
        # Find ingredients with similar properties
        properties = ingredient_node.get('properties', {})
        
        # This would typically use a more sophisticated similarity algorithm
        # For now, return empty list
        return substitutes
    
    def _get_recipes_with_ingredient(self, ingredient_id: str) -> List[str]:
        """Get recipes that contain an ingredient"""
        neighbors = self.graph_db.get_neighbors(ingredient_id, "CONTAINS")
        return [neighbor['node']['id'] for neighbor in neighbors if neighbor['node'].get('type') == 'Recipe']
    
    def _get_recipe_ingredients(self, recipe_id: str) -> List[str]:
        """Get ingredients in a recipe"""
        neighbors = self.graph_db.get_neighbors(recipe_id, "CONTAINS")
        return [neighbor['node']['id'] for neighbor in neighbors if neighbor['node'].get('type') == 'Ingredient']

class RelationshipPersistenceManager:
    """Manages persistence of relationship mappings"""
    
    def __init__(self, graph_db: GraphDatabaseManager):
        self.graph_db = graph_db
    
    def save_relationship_scores(self, scores: List[RelationshipScore]) -> int:
        """Save relationship scores to graph database"""
        saved_count = 0
        
        for score in scores:
            # Create or update relationship
            relationship = GraphRelationship(
                source_id=score.source_id,
                target_id=score.target_id,
                type=score.relationship_type,
                properties={
                    'score': score.score,
                    'confidence': score.confidence,
                    'evidence': score.evidence,
                    'timestamp': score.timestamp.isoformat()
                }
            )
            
            if self.graph_db.create_relationship(relationship):
                saved_count += 1
        
        return saved_count
    
    def load_relationship_scores(self, source_id: str, relationship_type: str = None) -> List[RelationshipScore]:
        """Load relationship scores from graph database"""
        scores = []
        
        neighbors = self.graph_db.get_neighbors(source_id, relationship_type)
        
        for neighbor in neighbors:
            props = neighbor['relationship_properties']
            score = RelationshipScore(
                source_id=source_id,
                target_id=neighbor['node']['id'],
                relationship_type=RelationType(neighbor['relationship_type']),
                score=props.get('score', 0.0),
                confidence=props.get('confidence', 0.0),
                evidence=props.get('evidence', []),
                timestamp=datetime.fromisoformat(props.get('timestamp', datetime.utcnow().isoformat()))
            )
            scores.append(score)
        
        return sorted(scores, key=lambda x: x.score, reverse=True)

# Global relationship mapper instance
relationship_mapper = None

def get_relationship_mapper(graph_db: GraphDatabaseManager = None) -> EntityRelationshipMapper:
    """Get or create relationship mapper instance"""
    global relationship_mapper
    if relationship_mapper is None:
        db = graph_db or GraphDatabaseManager()
        relationship_mapper = EntityRelationshipMapper(db)
    return relationship_mapper
