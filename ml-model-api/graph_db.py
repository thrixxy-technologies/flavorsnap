"""
Advanced Graph Database Integration for FlavorSnap
Implements Neo4j integration for complex relationships and network analysis
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
from neo4j import GraphDatabase, Driver, Session, Record
from neo4j.exceptions import ServiceUnavailable, AuthError
import networkx as nx
import pandas as pd
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class NodeType(Enum):
    """Graph node types for FlavorSnap entities"""
    USER = "User"
    FOOD_ITEM = "FoodItem"
    CATEGORY = "Category"
    INGREDIENT = "Ingredient"
    RECIPE = "Recipe"
    REVIEW = "Review"
    PREFERENCE = "Preference"
    NUTRITION = "Nutrition"

class RelationType(Enum):
    """Graph relationship types"""
    LIKES = "LIKES"
    CONTAINS = "CONTAINS"
    BELONGS_TO = "BELONGS_TO"
    REVIEWED = "REVIEWED"
    SIMILAR_TO = "SIMILAR_TO"
    RECOMMENDED = "RECOMMENDED"
    HAS_ALLERGY = "HAS_ALLERGY"
    PREFERRED = "PREFERRED"

@dataclass
class GraphNode:
    """Represents a graph node"""
    id: str
    type: NodeType
    properties: Dict[str, Any]
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

@dataclass
class GraphRelationship:
    """Represents a graph relationship"""
    source_id: str
    target_id: str
    type: RelationType
    properties: Dict[str, Any]
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

class GraphDatabaseManager:
    """Advanced graph database manager for FlavorSnap"""
    
    def __init__(self, uri: str = None, username: str = None, password: str = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver: Optional[Driver] = None
        self._connection_pool_size = 50
        self._max_retry_attempts = 3
        
    def connect(self) -> bool:
        """Establish connection to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password),
                max_connection_lifetime=3600,
                max_connection_pool_size=self._connection_pool_size,
                connection_acquisition_timeout=60
            )
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
            logger.info("Successfully connected to Neo4j database")
            return True
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()
            logger.info("Disconnected from Neo4j database")
    
    def create_node(self, node: GraphNode) -> bool:
        """Create a new node in the graph"""
        if not self.driver:
            logger.error("Database not connected")
            return False
            
        cypher_query = f"""
        CREATE (n:{node.type.value} {{id: $id, created_at: $created_at}})
        SET n += $properties
        RETURN n
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, {
                    'id': node.id,
                    'created_at': node.created_at.isoformat(),
                    'properties': node.properties
                })
                return result.single() is not None
        except Exception as e:
            logger.error(f"Failed to create node {node.id}: {e}")
            return False
    
    def create_relationship(self, relationship: GraphRelationship) -> bool:
        """Create a new relationship in the graph"""
        if not self.driver:
            logger.error("Database not connected")
            return False
            
        cypher_query = f"""
        MATCH (a), (b)
        WHERE a.id = $source_id AND b.id = $target_id
        CREATE (a)-[r:{relationship.type.value} {{created_at: $created_at}}]->(b)
        SET r += $properties
        RETURN r
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, {
                    'source_id': relationship.source_id,
                    'target_id': relationship.target_id,
                    'created_at': relationship.created_at.isoformat(),
                    'properties': relationship.properties
                })
                return result.single() is not None
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a node by ID"""
        if not self.driver:
            return None
            
        cypher_query = "MATCH (n {id: $id}) RETURN n"
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, {'id': node_id})
                record = result.single()
                if record:
                    node = record['n']
                    return dict(node)
                return None
        except Exception as e:
            logger.error(f"Failed to get node {node_id}: {e}")
            return None
    
    def get_neighbors(self, node_id: str, relationship_type: str = None) -> List[Dict[str, Any]]:
        """Get neighboring nodes with optional relationship type filter"""
        if not self.driver:
            return []
            
        rel_filter = f":{relationship_type}" if relationship_type else ""
        cypher_query = f"""
        MATCH (n {{id: $id}})-[r{rel_filter}]-(neighbor)
        RETURN neighbor, type(r) as relationship_type, properties(r) as rel_properties
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, {'id': node_id})
                neighbors = []
                for record in result:
                    neighbors.append({
                        'node': dict(record['neighbor']),
                        'relationship_type': record['relationship_type'],
                        'relationship_properties': dict(record['rel_properties'])
                    })
                return neighbors
        except Exception as e:
            logger.error(f"Failed to get neighbors for {node_id}: {e}")
            return []
    
    def find_shortest_path(self, source_id: str, target_id: str) -> List[Dict[str, Any]]:
        """Find shortest path between two nodes"""
        if not self.driver:
            return []
            
        cypher_query = """
        MATCH (start {id: $source_id}), (end {id: $target_id})
        MATCH path = shortestPath((start)-[*]-(end))
        RETURN path
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, {
                    'source_id': source_id,
                    'target_id': target_id
                })
                record = result.single()
                if record:
                    path = record['path']
                    return [dict(node) for node in path.nodes]
                return []
        except Exception as e:
            logger.error(f"Failed to find shortest path: {e}")
            return []
    
    def get_recommendations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get food recommendations based on collaborative filtering"""
        if not self.driver:
            return []
            
        cypher_query = """
        MATCH (user:User {id: $user_id})-[:LIKES]->(food:FoodItem)<-[:LIKES]-(similar_user:User)
        WHERE user <> similar_user
        WITH similar_user, COUNT(DISTINCT food) as common_likes
        ORDER BY common_likes DESC
        LIMIT 100
        MATCH (similar_user)-[:LIKES]->(recommended:FoodItem)
        WHERE NOT (user)-[:LIKES]->(recommended)
        RETURN recommended.id as food_id, recommended.name as food_name, 
               recommended.properties as food_properties, COUNT(*) as recommendation_score
        ORDER BY recommendation_score DESC
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, {'user_id': user_id, 'limit': limit})
                recommendations = []
                for record in result:
                    recommendations.append({
                        'food_id': record['food_id'],
                        'food_name': record['food_name'],
                        'food_properties': dict(record['food_properties']),
                        'score': record['recommendation_score']
                    })
                return recommendations
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return []
    
    def analyze_network_metrics(self) -> Dict[str, Any]:
        """Analyze network metrics and statistics"""
        if not self.driver:
            return {}
            
        queries = {
            'total_nodes': "MATCH (n) RETURN count(n) as count",
            'total_relationships': "MATCH ()-[r]->() RETURN count(r) as count",
            'node_types': "MATCH (n) RETURN labels(n) as type, count(n) as count",
            'relationship_types': "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count",
            'avg_degree': "MATCH (n) OPTIONAL MATCH (n)-[r]-() WITH n, count(r) as degree RETURN avg(degree) as avg_degree",
            'connected_components': "CALL gds.wcc.stream() YIELD nodeId, componentId RETURN count(DISTINCT componentId) as components"
        }
        
        metrics = {}
        try:
            with self.driver.session() as session:
                for metric_name, query in queries.items():
                    try:
                        result = session.run(query)
                        if metric_name in ['node_types', 'relationship_types']:
                            metrics[metric_name] = [dict(record) for record in result]
                        else:
                            record = result.single()
                            metrics[metric_name] = record[0] if record else 0
                    except Exception as e:
                        logger.warning(f"Failed to get metric {metric_name}: {e}")
                        metrics[metric_name] = 0
        except Exception as e:
            logger.error(f"Failed to analyze network metrics: {e}")
        
        return metrics
    
    def bulk_import_nodes(self, nodes: List[GraphNode]) -> int:
        """Bulk import nodes for better performance"""
        if not self.driver or not nodes:
            return 0
            
        # Group nodes by type for efficient batching
        nodes_by_type = {}
        for node in nodes:
            if node.type not in nodes_by_type:
                nodes_by_type[node.type] = []
            nodes_by_type[node.type].append(node)
        
        total_imported = 0
        with self.driver.session() as session:
            for node_type, type_nodes in nodes_by_type.items():
                batch_size = 1000
                for i in range(0, len(type_nodes), batch_size):
                    batch = type_nodes[i:i+batch_size]
                    cypher_query = f"""
                    UNWIND $batch AS node_data
                    CREATE (n:{node_type.value} {{id: node_data.id, created_at: node_data.created_at}})
                    SET n += node_data.properties
                    RETURN count(n) as imported
                    """
                    
                    batch_data = [
                        {
                            'id': node.id,
                            'created_at': node.created_at.isoformat(),
                            'properties': node.properties
                        }
                        for node in batch
                    ]
                    
                    try:
                        result = session.run(cypher_query, {'batch': batch_data})
                        total_imported += result.single()['imported']
                    except Exception as e:
                        logger.error(f"Failed to import batch: {e}")
        
        return total_imported
    
    def create_similarity_index(self) -> bool:
        """Create similarity index for faster recommendations"""
        if not self.driver:
            return False
            
        cypher_queries = [
            "CREATE INDEX food_name_index IF NOT EXISTS FOR (f:FoodItem) ON (f.name)",
            "CREATE INDEX user_id_index IF NOT EXISTS FOR (u:User) ON (u.id)",
            "CREATE CONSTRAINT food_id_unique IF NOT EXISTS FOR (f:FoodItem) REQUIRE f.id IS UNIQUE",
            "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE"
        ]
        
        try:
            with self.driver.session() as session:
                for query in cypher_queries:
                    session.run(query)
            logger.info("Successfully created similarity indexes")
            return True
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            return False

class GraphQueryOptimizer:
    """Optimize graph queries for better performance"""
    
    @staticmethod
    def optimize_recommendation_query(user_preferences: Dict[str, Any]) -> str:
        """Generate optimized recommendation query based on user preferences"""
        base_query = """
        MATCH (user:User {id: $user_id})
        MATCH (user)-[:PREFERRED]->(pref:Category)
        WITH user, collect(pref.name) as preferred_categories
        """
        
        if user_preferences.get('allergies'):
            base_query += """
            MATCH (user)-[:HAS_ALLERGY]->(allergy:Ingredient)
            WITH user, preferred_categories, collect(allergy.name) as allergies
            """
        
        base_query += """
        MATCH (food:FoodItem)-[:BELONGS_TO]->(cat:Category)
        WHERE cat.name IN preferred_categories
        """
        
        if user_preferences.get('allergies'):
            base_query += """
            AND NOT (food)-[:CONTAINS]->(allergy_ingredient:Ingredient)
            WHERE allergy_ingredient.name IN allergies
            """
        
        base_query += """
        OPTIONAL MATCH (food)<-[like:LIKES]-(other_user:User)
        WHERE NOT (user)-[:LIKES]->(food)
        WITH food, count(like) as like_count
        ORDER BY like_count DESC
        LIMIT $limit
        RETURN food
        """
        
        return base_query

# Global graph database instance
graph_db = GraphDatabaseManager()
