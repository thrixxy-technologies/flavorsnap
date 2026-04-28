"""
Advanced Network Analysis for FlavorSnap Graph Database
Implements complex network analysis algorithms and metrics
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import networkx as nx
from collections import defaultdict, Counter
from dataclasses import dataclass
from enum import Enum
import json
from scipy import stats
from sklearn.cluster import SpectralClustering, DBSCAN
from sklearn.metrics import modularity
import community as community_louvain

from .graph_db import GraphDatabaseManager, NodeType, RelationType

logger = logging.getLogger(__name__)

class AnalysisType(Enum):
    """Types of network analysis"""
    CENTRALITY = "centrality"
    COMMUNITY_DETECTION = "community_detection"
    INFLUENCE_PROPAGATION = "influence_propagation"
    SIMILARITY_ANALYSIS = "similarity_analysis"
    PREDICTION = "prediction"
    ANOMALY_DETECTION = "anomaly_detection"

class CentralityMetric(Enum):
    """Centrality metrics"""
    DEGREE = "degree"
    BETWEENNESS = "betweenness"
    CLOSENESS = "closeness"
    EIGENVECTOR = "eigenvector"
    PAGERANK = "pagerank"
    KATZ = "katz"

@dataclass
class NetworkMetrics:
    """Container for network analysis metrics"""
    node_id: str
    metrics: Dict[str, float]
    community: Optional[int] = None
    influence_score: Optional[float] = None
    anomaly_score: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class CommunityInfo:
    """Information about a detected community"""
    community_id: int
    size: int
    density: float
    modularity: float
    key_nodes: List[str]
    characteristics: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class NetworkAnalyzer:
    """Advanced network analysis engine"""
    
    def __init__(self, graph_db: GraphDatabaseManager):
        self.graph_db = graph_db
        self.networkx_graph = None
        self.node_attributes = {}
        self.edge_attributes = {}
        self.analysis_cache = {}
        self.cache_expiry_hours = 24
        
        # Analysis parameters
        self.min_community_size = 5
        self.anomaly_threshold = 2.0  # Standard deviations
        self.influence_decay_factor = 0.85
        self.max_iterations = 100
    
    def build_network_graph(self, node_types: List[NodeType] = None, 
                          relationship_types: List[RelationType] = None) -> nx.Graph:
        """Build NetworkX graph from Neo4j data"""
        logger.info("Building NetworkX graph from Neo4j data")
        
        # Create directed graph for influence analysis
        G = nx.DiGraph()
        
        # Get all nodes (filtered by type if specified)
        if node_types:
            nodes = []
            for node_type in node_types:
                query = f"MATCH (n:{node_type.value}) RETURN n"
                nodes.extend(self._execute_query(query))
        else:
            query = "MATCH (n) RETURN n"
            nodes = self._execute_query(query)
        
        # Add nodes to NetworkX graph
        for node_record in nodes:
            node_data = dict(node_record['n'])
            node_id = node_data['id']
            G.add_node(node_id, **node_data)
            self.node_attributes[node_id] = node_data
        
        # Get all relationships (filtered by type if specified)
        if relationship_types:
            relationships = []
            for rel_type in relationship_types:
                query = f"MATCH (a)-[r:{rel_type.value}]->(b) RETURN a, r, b"
                relationships.extend(self._execute_query(query))
        else:
            query = "MATCH (a)-[r]->(b) RETURN a, r, b"
            relationships = self._execute_query(query)
        
        # Add edges to NetworkX graph
        for rel_record in relationships:
            source_data = dict(rel_record['a'])
            target_data = dict(rel_record['b'])
            rel_data = dict(rel_record['r'])
            
            source_id = source_data['id']
            target_id = target_data['id']
            
            # Add edge with properties
            edge_props = {
                'type': rel_data.get('type'),
                'weight': rel_data.get('weight', 1.0),
                'timestamp': rel_data.get('timestamp'),
                **{k: v for k, v in rel_data.items() 
                   if k not in ['type', 'weight', 'timestamp']}
            }
            
            G.add_edge(source_id, target_id, **edge_props)
            self.edge_attributes[(source_id, target_id)] = edge_props
        
        self.networkx_graph = G
        logger.info(f"Built NetworkX graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        return G
    
    def analyze_centrality(self, node_id: str = None, metrics: List[CentralityMetric] = None) -> Dict[str, Any]:
        """Analyze centrality metrics for nodes"""
        if self.networkx_graph is None:
            self.build_network_graph()
        
        if metrics is None:
            metrics = list(CentralityMetric)
        
        results = {}
        
        # Calculate centrality metrics
        for metric in metrics:
            if metric == CentralityMetric.DEGREE:
                centrality = dict(self.networkx_graph.degree())
            elif metric == CentralityMetric.BETWEENNESS:
                centrality = nx.betweenness_centrality(self.networkx_graph, normalized=True)
            elif metric == CentralityMetric.CLOSENESS:
                centrality = nx.closeness_centrality(self.networkx_graph)
            elif metric == CentralityMetric.EIGENVECTOR:
                centrality = nx.eigenvector_centrality_numpy(self.networkx_graph, max_iter=1000)
            elif metric == CentralityMetric.PAGERANK:
                centrality = nx.pagerank(self.networkx_graph, alpha=0.85)
            elif metric == CentralityMetric.KATZ:
                centrality = nx.katz_centrality_numpy(self.networkx_graph, alpha=0.1)
            
            results[metric.value] = centrality
        
        # Filter for specific node if requested
        if node_id:
            filtered_results = {}
            for metric_name, centrality_dict in results.items():
                filtered_results[metric_name] = centrality_dict.get(node_id, 0.0)
            return filtered_results
        
        return results
    
    def detect_communities(self, algorithm: str = "louvain") -> List[CommunityInfo]:
        """Detect communities in the network"""
        if self.networkx_graph is None:
            self.build_network_graph()
        
        logger.info(f"Detecting communities using {algorithm} algorithm")
        
        communities = []
        
        if algorithm == "louvain":
            # Louvain method (best for large networks)
            partition = community_louvain.best_partition(self.networkx_graph.to_undirected())
            communities = self._process_louvain_communities(partition)
        
        elif algorithm == "spectral":
            # Spectral clustering
            n_clusters = min(10, self.networkx_graph.number_of_nodes() // self.min_community_size)
            if n_clusters > 1:
                adjacency_matrix = nx.to_numpy_array(self.networkx_graph)
                clustering = SpectralClustering(n_clusters=n_clusters, affinity='precomputed')
                labels = clustering.fit_predict(adjacency_matrix)
                communities = self._process_spectral_communities(labels)
        
        elif algorithm == "dbscan":
            # DBSCAN for density-based clustering
            adjacency_matrix = nx.to_numpy_array(self.networkx_graph)
            clustering = DBSCAN(eps=0.5, min_samples=self.min_community_size, metric='precomputed')
            labels = clustering.fit_predict(adjacency_matrix)
            communities = self._process_dbscan_communities(labels)
        
        logger.info(f"Detected {len(communities)} communities")
        return communities
    
    def analyze_influence_propagation(self, seed_nodes: List[str], 
                                   max_steps: int = 10) -> Dict[str, Any]:
        """Analyze influence propagation from seed nodes"""
        if self.networkx_graph is None:
            self.build_network_graph()
        
        logger.info(f"Analyzing influence propagation from {len(seed_nodes)} seed nodes")
        
        # Independent Cascade Model
        influenced_nodes = set(seed_nodes)
        newly_influenced = set(seed_nodes)
        propagation_history = []
        
        for step in range(max_steps):
            if not newly_influenced:
                break
            
            current_influenced = set()
            
            for node in newly_influenced:
                neighbors = list(self.networkx_graph.successors(node))
                
                for neighbor in neighbors:
                    if neighbor not in influenced_nodes:
                        # Calculate influence probability
                        edge_data = self.networkx_graph.get_edge_data(node, neighbor)
                        influence_prob = edge_data.get('weight', 0.1) if edge_data else 0.1
                        
                        # Apply influence decay
                        influence_prob *= (self.influence_decay_factor ** step)
                        
                        # Stochastic activation
                        if np.random.random() < influence_prob:
                            current_influenced.add(neighbor)
            
            newly_influenced = current_influenced
            influenced_nodes.update(newly_influenced)
            
            propagation_history.append({
                'step': step,
                'newly_influenced': list(newly_influenced),
                'total_influenced': len(influenced_nodes)
            })
        
        return {
            'seed_nodes': seed_nodes,
            'total_influenced': len(influenced_nodes),
            'influenced_nodes': list(influenced_nodes),
            'propagation_history': propagation_history,
            'influence_ratio': len(influenced_nodes) / self.networkx_graph.number_of_nodes()
        }
    
    def predict_missing_links(self, top_k: int = 50) -> List[Tuple[str, str, float]]:
        """Predict missing links using link prediction algorithms"""
        if self.networkx_graph is None:
            self.build_network_graph()
        
        logger.info("Predicting missing links")
        
        # Convert to undirected graph for link prediction
        undirected_graph = self.networkx_graph.to_undirected()
        
        # Calculate link prediction scores
        predictions = []
        
        # Jaccard coefficient
        jaccard_scores = list(nx.jaccard_coefficient(undirected_graph))
        for u, v, score in jaccard_scores:
            if not undirected_graph.has_edge(u, v):
                predictions.append((u, v, score * 0.3))  # Weight for Jaccard
        
        # Adamic-Adar index
        adamic_adar_scores = list(nx.adamic_adar_index(undirected_graph))
        for u, v, score in adamic_adar_scores:
            if not undirected_graph.has_edge(u, v):
                predictions.append((u, v, score * 0.4))  # Weight for Adamic-Adar
        
        # Preferential attachment
        pref_attach_scores = list(nx.preferential_attachment(undirected_graph))
        for u, v, score in pref_attach_scores:
            if not undirected_graph.has_edge(u, v):
                predictions.append((u, v, score * 0.3))  # Weight for Preferential Attachment
        
        # Combine and rank predictions
        combined_scores = defaultdict(float)
        for u, v, score in predictions:
            combined_scores[(u, v)] += score
        
        # Sort by score and return top predictions
        sorted_predictions = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        
        return [(u, v, score) for (u, v), score in sorted_predictions[:top_k]]
    
    def detect_anomalies(self, metric: str = "degree") -> List[NetworkMetrics]:
        """Detect anomalous nodes based on network metrics"""
        if self.networkx_graph is None:
            self.build_network_graph()
        
        logger.info(f"Detecting anomalies based on {metric} metric")
        
        # Calculate metric values
        centrality_results = self.analyze_centrality(metrics=[CentralityMetric(metric)])
        metric_values = centrality_results[metric]
        
        # Calculate statistics
        values = np.array(list(metric_values.values()))
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        # Detect anomalies (values beyond threshold standard deviations)
        anomalies = []
        for node_id, value in metric_values.items():
            z_score = abs(value - mean_val) / std_val if std_val > 0 else 0
            
            if z_score > self.anomaly_threshold:
                anomaly_metrics = NetworkMetrics(
                    node_id=node_id,
                    metrics={metric: value},
                    anomaly_score=z_score
                )
                anomalies.append(anomaly_metrics)
        
        logger.info(f"Detected {len(anomalies)} anomalous nodes")
        return anomalies
    
    def analyze_network_evolution(self, time_window_days: int = 30) -> Dict[str, Any]:
        """Analyze network evolution over time"""
        logger.info(f"Analyzing network evolution over {time_window_days} days")
        
        # Get time series data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=time_window_days)
        
        evolution_data = {
            'dates': [],
            'node_count': [],
            'edge_count': [],
            'density': [],
            'avg_clustering': [],
            'connected_components': []
        }
        
        # Sample data points (daily)
        current_date = start_date
        while current_date <= end_date:
            # Build graph for this time point
            snapshot_graph = self._build_time_snapshot(current_date)
            
            if snapshot_graph.number_of_nodes() > 0:
                evolution_data['dates'].append(current_date.isoformat())
                evolution_data['node_count'].append(snapshot_graph.number_of_nodes())
                evolution_data['edge_count'].append(snapshot_graph.number_of_edges())
                evolution_data['density'].append(nx.density(snapshot_graph))
                
                if snapshot_graph.number_of_nodes() > 1:
                    evolution_data['avg_clustering'].append(
                        nx.average_clustering(snapshot_graph.to_undirected())
                    )
                else:
                    evolution_data['avg_clustering'].append(0.0)
                
                evolution_data['connected_components'].append(
                    nx.number_connected_components(snapshot_graph.to_undirected())
                )
            
            current_date += timedelta(days=1)
        
        return evolution_data
    
    def calculate_network_robustness(self, attack_strategy: str = "betweenness") -> Dict[str, Any]:
        """Calculate network robustness under node removal"""
        if self.networkx_graph is None:
            self.build_network_graph()
        
        logger.info(f"Calculating network robustness using {attack_strategy} attack strategy")
        
        original_size = self.networkx_graph.number_of_nodes()
        largest_cc_size = len(max(nx.connected_components(self.networkx_graph.to_undirected()), key=len))
        
        robustness_data = {
            'fractions_removed': [],
            'largest_cc_sizes': [],
            'attack_strategy': attack_strategy
        }
        
        # Create copy for simulation
        graph_copy = self.networkx_graph.copy()
        
        # Determine removal order
        if attack_strategy == "betweenness":
            centrality = nx.betweenness_centrality(graph_copy)
            removal_order = sorted(centrality.keys(), key=centrality.get, reverse=True)
        elif attack_strategy == "degree":
            centrality = dict(graph_copy.degree())
            removal_order = sorted(centrality.keys(), key=centrality.get, reverse=True)
        else:  # random
            removal_order = list(graph_copy.nodes())
            np.random.shuffle(removal_order)
        
        # Simulate node removal
        for i, node in enumerate(removal_order):
            if graph_copy.has_node(node):
                graph_copy.remove_node(node)
                
                fraction_removed = (i + 1) / original_size
                current_largest_cc = len(max(nx.connected_components(graph_copy.to_undirected()), key=len))
                largest_cc_fraction = current_largest_cc / original_size
                
                robustness_data['fractions_removed'].append(fraction_removed)
                robustness_data['largest_cc_sizes'].append(largest_cc_fraction)
        
        return robustness_data
    
    def _execute_query(self, query: str) -> List[Any]:
        """Execute Neo4j query and return results"""
        try:
            with self.graph_db.driver.session() as session:
                result = session.run(query)
                return list(result)
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return []
    
    def _process_louvain_communities(self, partition: Dict[str, int]) -> List[CommunityInfo]:
        """Process Louvain community detection results"""
        communities = defaultdict(list)
        for node, community_id in partition.items():
            communities[community_id].append(node)
        
        community_infos = []
        for community_id, nodes in communities.items():
            if len(nodes) >= self.min_community_size:
                # Calculate community metrics
                subgraph = self.networkx_graph.subgraph(nodes)
                density = nx.density(subgraph)
                
                # Find key nodes (highest degree)
                degrees = dict(subgraph.degree())
                key_nodes = sorted(degrees.keys(), key=degrees.get, reverse=True)[:5]
                
                community_info = CommunityInfo(
                    community_id=community_id,
                    size=len(nodes),
                    density=density,
                    modularity=0.0,  # Would need to calculate globally
                    key_nodes=key_nodes,
                    characteristics=self._analyze_community_characteristics(nodes)
                )
                community_infos.append(community_info)
        
        return community_infos
    
    def _process_spectral_communities(self, labels: np.ndarray) -> List[CommunityInfo]:
        """Process spectral clustering results"""
        communities = defaultdict(list)
        node_list = list(self.networkx_graph.nodes())
        
        for i, label in enumerate(labels):
            if label != -1:  # Ignore noise points
                communities[label].append(node_list[i])
        
        community_infos = []
        for community_id, nodes in communities.items():
            if len(nodes) >= self.min_community_size:
                subgraph = self.networkx_graph.subgraph(nodes)
                density = nx.density(subgraph)
                degrees = dict(subgraph.degree())
                key_nodes = sorted(degrees.keys(), key=degrees.get, reverse=True)[:5]
                
                community_info = CommunityInfo(
                    community_id=community_id,
                    size=len(nodes),
                    density=density,
                    modularity=0.0,
                    key_nodes=key_nodes,
                    characteristics=self._analyze_community_characteristics(nodes)
                )
                community_infos.append(community_info)
        
        return community_infos
    
    def _process_dbscan_communities(self, labels: np.ndarray) -> List[CommunityInfo]:
        """Process DBSCAN clustering results"""
        communities = defaultdict(list)
        node_list = list(self.networkx_graph.nodes())
        
        for i, label in enumerate(labels):
            if label != -1:  # Ignore noise points
                communities[label].append(node_list[i])
        
        community_infos = []
        for community_id, nodes in communities.items():
            if len(nodes) >= self.min_community_size:
                subgraph = self.networkx_graph.subgraph(nodes)
                density = nx.density(subgraph)
                degrees = dict(subgraph.degree())
                key_nodes = sorted(degrees.keys(), key=degrees.get, reverse=True)[:5]
                
                community_info = CommunityInfo(
                    community_id=community_id,
                    size=len(nodes),
                    density=density,
                    modularity=0.0,
                    key_nodes=key_nodes,
                    characteristics=self._analyze_community_characteristics(nodes)
                )
                community_infos.append(community_info)
        
        return community_infos
    
    def _analyze_community_characteristics(self, nodes: List[str]) -> Dict[str, Any]:
        """Analyze characteristics of a community"""
        characteristics = {
            'node_types': Counter(),
            'avg_degree': 0,
            'clustering_coefficient': 0,
            'key_attributes': {}
        }
        
        if not nodes:
            return characteristics
        
        # Node type distribution
        for node in nodes:
            node_attrs = self.node_attributes.get(node, {})
            node_type = node_attrs.get('type', 'Unknown')
            characteristics['node_types'][node_type] += 1
        
        # Average degree
        subgraph = self.networkx_graph.subgraph(nodes)
        degrees = dict(subgraph.degree())
        characteristics['avg_degree'] = np.mean(list(degrees.values()))
        
        # Clustering coefficient
        if len(nodes) > 2:
            characteristics['clustering_coefficient'] = nx.average_clustering(subgraph.to_undirected())
        
        # Key attributes (most common values)
        all_attributes = defaultdict(list)
        for node in nodes:
            node_attrs = self.node_attributes.get(node, {})
            for attr, value in node_attrs.items():
                if attr not in ['id', 'type', 'created_at']:
                    all_attributes[attr].append(value)
        
        for attr, values in all_attributes.items():
            if values:
                try:
                    most_common = Counter(values).most_common(1)[0][0]
                    characteristics['key_attributes'][attr] = most_common
                except (IndexError, TypeError):
                    pass
        
        return characteristics
    
    def _build_time_snapshot(self, date: datetime) -> nx.Graph:
        """Build graph snapshot for specific date"""
        # This would typically query the database for data up to the specified date
        # For now, return the current graph
        return self.networkx_graph.copy() if self.networkx_graph else nx.Graph()

class NetworkVisualizationGenerator:
    """Generate network visualizations and reports"""
    
    def __init__(self, analyzer: NetworkAnalyzer):
        self.analyzer = analyzer
    
    def generate_centrality_report(self, top_n: int = 20) -> Dict[str, Any]:
        """Generate centrality analysis report"""
        centrality_results = self.analyzer.analyze_centrality()
        
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_nodes': len(list(centrality_results.values())[0]) if centrality_results else 0,
            'metrics': {}
        }
        
        for metric_name, centrality_dict in centrality_results.items():
            # Sort by centrality value
            sorted_nodes = sorted(centrality_dict.items(), key=lambda x: x[1], reverse=True)
            
            report['metrics'][metric_name] = {
                'top_nodes': sorted_nodes[:top_n],
                'statistics': {
                    'mean': np.mean(list(centrality_dict.values())),
                    'std': np.std(list(centrality_dict.values())),
                    'min': np.min(list(centrality_dict.values())),
                    'max': np.max(list(centrality_dict.values()))
                }
            }
        
        return report
    
    def generate_community_report(self, communities: List[CommunityInfo]) -> Dict[str, Any]:
        """Generate community analysis report"""
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_communities': len(communities),
            'communities': []
        }
        
        for community in communities:
            community_data = {
                'id': community.community_id,
                'size': community.size,
                'density': community.density,
                'modularity': community.modularity,
                'key_nodes': community.key_nodes,
                'characteristics': community.characteristics
            }
            report['communities'].append(community_data)
        
        return report
    
    def export_network_data(self, format: str = "json") -> Dict[str, Any]:
        """Export network data in various formats"""
        if self.analyzer.networkx_graph is None:
            return {}
        
        if format == "json":
            # Convert to JSON-serializable format
            nodes = []
            for node, attrs in self.analyzer.node_attributes.items():
                nodes.append({'id': node, **attrs})
            
            edges = []
            for (source, target), attrs in self.analyzer.edge_attributes.items():
                edges.append({'source': source, 'target': target, **attrs})
            
            return {
                'nodes': nodes,
                'edges': edges,
                'metadata': {
                    'total_nodes': len(nodes),
                    'total_edges': len(edges),
                    'export_timestamp': datetime.utcnow().isoformat()
                }
            }
        
        elif format == "adjacency":
            # Export adjacency matrix
            adjacency_matrix = nx.to_numpy_array(self.analyzer.networkx_graph)
            return {
                'adjacency_matrix': adjacency_matrix.tolist(),
                'node_order': list(self.analyzer.networkx_graph.nodes())
            }
        
        return {}

# Global network analyzer instance
network_analyzer = None

def get_network_analyzer(graph_db: GraphDatabaseManager = None) -> NetworkAnalyzer:
    """Get or create network analyzer instance"""
    global network_analyzer
    if network_analyzer is None:
        db = graph_db or GraphDatabaseManager()
        network_analyzer = NetworkAnalyzer(db)
    return network_analyzer
