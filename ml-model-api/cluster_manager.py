"""
Advanced Cluster Manager for FlavorSnap API
Implements distributed cluster management with node orchestration and resource coordination
"""
import os
import time
import json
import uuid
import threading
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import logging
import redis
import requests
import psutil
from distributed_processor import Node, NodeStatus, distributed_processor
from advanced_load_balancer import AdvancedLoadBalancer, Backend, LoadBalancingStrategy


class ClusterRole(Enum):
    """Cluster node roles"""
    MASTER = "master"
    WORKER = "worker"
    COORDINATOR = "coordinator"
    STORAGE = "storage"
    GATEWAY = "gateway"


class ClusterState(Enum):
    """Cluster states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    SHUTTING_DOWN = "shutting_down"
    FAILED = "failed"


class ResourceType(Enum):
    """Resource types"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"


@dataclass
class ClusterNode:
    """Cluster node information"""
    node_id: str
    host: str
    port: int
    role: ClusterRole
    status: NodeStatus
    last_heartbeat: datetime
    cpu_cores: int
    memory_mb: int
    disk_gb: int
    network_mbps: int
    gpu_count: int
    current_load: Dict[ResourceType, float]
    max_capacity: Dict[ResourceType, float]
    supported_services: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['role'] = self.role.value
        data['status'] = self.status.value
        data['last_heartbeat'] = self.last_heartbeat.isoformat()
        data['current_load'] = {rt.value: load for rt, load in self.current_load.items()}
        data['max_capacity'] = {rt.value: cap for rt, cap in self.max_capacity.items()}
        return data


@dataclass
class ClusterMetrics:
    """Cluster metrics"""
    timestamp: datetime
    total_nodes: int
    active_nodes: int
    total_cpu_cores: int
    total_memory_mb: int
    total_disk_gb: int
    avg_cpu_usage: float
    avg_memory_usage: float
    avg_disk_usage: float
    network_throughput: float
    request_rate: float
    error_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class ServiceDeployment:
    """Service deployment information"""
    service_id: str
    service_name: str
    version: str
    deployed_nodes: List[str]
    required_resources: Dict[ResourceType, float]
    health_check_url: str
    status: str
    deployment_time: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['required_resources'] = {rt.value: req for rt, req in self.required_resources.items()}
        data['deployment_time'] = self.deployment_time.isoformat()
        return data


class ClusterConfig:
    """Cluster manager configuration"""
    
    # Cluster settings
    CLUSTER_NAME = "flavorsnap-cluster"
    MASTER_ELECTION_TIMEOUT = 30  # seconds
    NODE_TIMEOUT = 90  # seconds
    HEARTBEAT_INTERVAL = 10  # seconds
    
    # Resource thresholds
    CPU_WARNING_THRESHOLD = 80.0  # percent
    CPU_CRITICAL_THRESHOLD = 90.0  # percent
    MEMORY_WARNING_THRESHOLD = 85.0  # percent
    MEMORY_CRITICAL_THRESHOLD = 95.0  # percent
    DISK_WARNING_THRESHOLD = 80.0  # percent
    DISK_CRITICAL_THRESHOLD = 90.0  # percent
    
    # Auto-scaling
    AUTO_SCALING_ENABLED = True
    SCALE_UP_THRESHOLD = 80.0  # percent
    SCALE_DOWN_THRESHOLD = 30.0  # percent
    MIN_NODES = 3
    MAX_NODES = 20
    
    # Health checks
    HEALTH_CHECK_INTERVAL = 30  # seconds
    SERVICE_HEALTH_TIMEOUT = 5  # seconds
    
    # Failover
    FAILOVER_ENABLED = True
    FAILOVER_TIMEOUT = 60  # seconds


class ResourceManager:
    """Manage cluster resources"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.node_resources: Dict[str, ClusterNode] = {}
        self.resource_allocations: Dict[str, Dict[ResourceType, float]] = defaultdict(dict)
    
    def update_node_resources(self, node_id: str, resources: Dict[ResourceType, float]):
        """Update node resource usage"""
        if node_id in self.node_resources:
            self.node_resources[node_id].current_load = resources
    
    def get_cluster_resources(self) -> Dict[str, Any]:
        """Get cluster-wide resource summary"""
        if not self.node_resources:
            return {}
        
        total_capacity = defaultdict(float)
        total_used = defaultdict(float)
        
        for node in self.node_resources.values():
            for resource_type, capacity in node.max_capacity.items():
                total_capacity[resource_type] += capacity
                total_used[resource_type] += node.current_load.get(resource_type, 0)
        
        usage_summary = {}
        for resource_type in ResourceType:
            used = total_used[resource_type]
            capacity = total_capacity[resource_type]
            usage_percent = (used / capacity * 100) if capacity > 0 else 0
            
            usage_summary[resource_type.value] = {
                'used': used,
                'capacity': capacity,
                'usage_percent': usage_percent,
                'status': self._get_resource_status(usage_percent)
            }
        
        return usage_summary
    
    def _get_resource_status(self, usage_percent: float) -> str:
        """Get resource status based on usage"""
        if usage_percent >= ClusterConfig.CRITICAL_THRESHOLD:
            return "critical"
        elif usage_percent >= ClusterConfig.WARNING_THRESHOLD:
            return "warning"
        else:
            return "healthy"
    
    def can_allocate_resources(self, node_id: str, required_resources: Dict[ResourceType, float]) -> bool:
        """Check if node can accommodate required resources"""
        if node_id not in self.node_resources:
            return False
        
        node = self.node_resources[node_id]
        
        for resource_type, required_amount in required_resources.items():
            current_usage = node.current_load.get(resource_type, 0)
            capacity = node.max_capacity.get(resource_type, 0)
            
            if current_usage + required_amount > capacity:
                return False
        
        return True
    
    def allocate_resources(self, node_id: str, service_id: str, required_resources: Dict[ResourceType, float]) -> bool:
        """Allocate resources to service on node"""
        if not self.can_allocate_resources(node_id, required_resources):
            return False
        
        # Update allocation
        self.resource_allocations[service_id] = required_resources
        
        # Update node usage
        node = self.node_resources[node_id]
        for resource_type, amount in required_resources.items():
            node.current_load[resource_type] = node.current_load.get(resource_type, 0) + amount
        
        return True
    
    def deallocate_resources(self, node_id: str, service_id: str):
        """Deallocate resources from service"""
        if service_id not in self.resource_allocations:
            return
        
        allocated_resources = self.resource_allocations[service_id]
        node = self.node_resources[node_id]
        
        # Update node usage
        for resource_type, amount in allocated_resources.items():
            node.current_load[resource_type] = max(0, node.current_load.get(resource_type, 0) - amount)
        
        # Remove allocation
        del self.resource_allocations[service_id]


class ServiceManager:
    """Manage services in the cluster"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.deployed_services: Dict[str, ServiceDeployment] = {}
        self.service_health: Dict[str, bool] = {}
    
    def deploy_service(self, service_name: str, version: str, required_resources: Dict[ResourceType, float],
                      health_check_url: str, target_nodes: List[str] = None) -> str:
        """Deploy service to cluster"""
        service_id = str(uuid.uuid4())
        
        # Select target nodes if not specified
        if not target_nodes:
            target_nodes = self._select_nodes_for_service(required_resources)
        
        if not target_nodes:
            raise ValueError("No suitable nodes available for service deployment")
        
        # Create deployment
        deployment = ServiceDeployment(
            service_id=service_id,
            service_name=service_name,
            version=version,
            deployed_nodes=target_nodes,
            required_resources=required_resources,
            health_check_url=health_check_url,
            status="deploying",
            deployment_time=datetime.now(),
            metadata={}
        )
        
        self.deployed_services[service_id] = deployment
        
        # Deploy to nodes (simplified)
        for node_id in target_nodes:
            self._deploy_to_node(node_id, service_id, deployment)
        
        deployment.status = "active"
        
        self.logger.info(f"Service {service_name} deployed to {len(target_nodes)} nodes")
        return service_id
    
    def _select_nodes_for_service(self, required_resources: Dict[ResourceType, float]) -> List[str]:
        """Select suitable nodes for service deployment"""
        suitable_nodes = []
        
        # This would integrate with the resource manager
        # For now, return empty list (would be implemented with actual node selection logic)
        
        return suitable_nodes
    
    def _deploy_to_node(self, node_id: str, service_id: str, deployment: ServiceDeployment):
        """Deploy service to specific node"""
        # This would contain actual deployment logic
        # For now, just log the deployment
        self.logger.info(f"Deploying service {deployment.service_name} to node {node_id}")
    
    def undeploy_service(self, service_id: str) -> bool:
        """Undeploy service from cluster"""
        if service_id not in self.deployed_services:
            return False
        
        deployment = self.deployed_services[service_id]
        
        # Undeploy from nodes
        for node_id in deployment.deployed_nodes:
            self._undeploy_from_node(node_id, service_id)
        
        # Remove deployment
        del self.deployed_services[service_id]
        
        self.logger.info(f"Service {deployment.service_name} undeployed")
        return True
    
    def _undeploy_from_node(self, node_id: str, service_id: str):
        """Undeploy service from specific node"""
        # This would contain actual undeployment logic
        self.logger.info(f"Undeploying service from node {node_id}")
    
    def check_service_health(self, service_id: str) -> bool:
        """Check health of deployed service"""
        if service_id not in self.deployed_services:
            return False
        
        deployment = self.deployed_services[service_id]
        
        # Check health on all deployed nodes
        healthy_nodes = 0
        
        for node_id in deployment.deployed_nodes:
            if self._check_node_service_health(node_id, deployment):
                healthy_nodes += 1
        
        # Service is healthy if at least 50% of nodes are healthy
        is_healthy = healthy_nodes >= len(deployment.deployed_nodes) // 2
        self.service_health[service_id] = is_healthy
        
        return is_healthy
    
    def _check_node_service_health(self, node_id: str, deployment: ServiceDeployment) -> bool:
        """Check service health on specific node"""
        try:
            # This would make actual health check request
            # For now, return True
            return True
        except:
            return False
    
    def get_service_status(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get service deployment status"""
        if service_id not in self.deployed_services:
            return None
        
        deployment = self.deployed_services[service_id]
        is_healthy = self.check_service_health(service_id)
        
        return {
            'deployment': deployment.to_dict(),
            'healthy': is_healthy,
            'health_check_time': datetime.now().isoformat()
        }


class MasterElection:
    """Master node election using consensus algorithm"""
    
    def __init__(self, node_id: str, redis_client: redis.Redis):
        self.node_id = node_id
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        self.is_master = False
        self.master_key = "cluster:master"
        self.election_thread = None
        self.election_active = False
    
    def start_election(self):
        """Start master election process"""
        if self.election_active:
            return
        
        self.election_active = True
        self.election_thread = threading.Thread(target=self._election_loop, daemon=True)
        self.election_thread.start()
        
        self.logger.info("Master election started")
    
    def stop_election(self):
        """Stop master election process"""
        self.election_active = False
        
        if self.election_thread:
            self.election_thread.join(timeout=5)
        
        # Resign if master
        if self.is_master:
            self.redis.delete(self.master_key)
            self.is_master = False
        
        self.logger.info("Master election stopped")
    
    def _election_loop(self):
        """Election loop"""
        while self.election_active:
            try:
                # Try to become master
                current_master = self.redis.get(self.master_key)
                
                if not current_master:
                    # No master, try to become master
                    success = self.redis.setnx(
                        self.master_key,
                        self.node_id,
                        ex=ClusterConfig.MASTER_ELECTION_TIMEOUT
                    )
                    
                    if success:
                        self.is_master = True
                        self.logger.info(f"Node {self.node_id} became master")
                    else:
                        self.is_master = False
                else:
                    # Check if current master is still alive
                    if current_master.decode() == self.node_id:
                        # We are master, refresh lease
                        self.redis.expire(self.master_key, ClusterConfig.MASTER_ELECTION_TIMEOUT)
                        self.is_master = True
                    else:
                        self.is_master = False
                
                # Sleep until next check
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Election loop error: {str(e)}")
                time.sleep(5)


class ClusterManager:
    """Main cluster manager"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.redis_client = None
        
        self.cluster_name = ClusterConfig.CLUSTER_NAME
        self.cluster_state = ClusterState.INITIALIZING
        self.current_master = None
        self.local_node_id = None
        
        self.nodes: Dict[str, ClusterNode] = {}
        self.resource_manager = ResourceManager()
        self.service_manager = ServiceManager()
        self.master_election = None
        
        self.metrics_history: deque = deque(maxlen=1440)  # 24 hours of minute data
        
        self.management_active = False
        self.heartbeat_thread = None
        self.metrics_thread = None
        self.health_check_thread = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize cluster manager with Flask app"""
        self.app = app
        
        # Initialize Redis
        redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = redis.from_url(redis_url, decode_responses=False)
        
        # Get local node information
        self.local_node_id = self._get_local_node_id()
        
        # Initialize master election
        self.master_election = MasterElection(self.local_node_id, self.redis_client)
        
        # Register local node
        self._register_local_node()
        
        # Start cluster management
        self.start_management()
        
        self.logger.info(f"Cluster manager initialized for node {self.local_node_id}")
    
    def _get_local_node_id(self) -> str:
        """Get local node ID"""
        node_id = os.getenv('NODE_ID')
        if not node_id:
            # Generate based on hostname and port
            hostname = os.getenv('NODE_HOST', 'localhost')
            port = os.getenv('NODE_PORT', '8080')
            node_id = f"{hostname}_{port}"
        
        return node_id
    
    def _register_local_node(self):
        """Register this node in the cluster"""
        import psutil
        
        # Get system information
        cpu_cores = psutil.cpu_count()
        memory_mb = psutil.virtual_memory().total // 1024 // 1024
        disk_gb = psutil.disk_usage('/').total // 1024 // 1024 // 1024
        
        # Create node
        node = ClusterNode(
            node_id=self.local_node_id,
            host=os.getenv('NODE_HOST', 'localhost'),
            port=int(os.getenv('NODE_PORT', 8080)),
            role=ClusterRole.WORKER,  # Default role
            status=NodeStatus.ACTIVE,
            last_heartbeat=datetime.now(),
            cpu_cores=cpu_cores,
            memory_mb=memory_mb,
            disk_gb=disk_gb,
            network_mbps=1000,  # Would need actual network measurement
            gpu_count=0,  # Would need GPU detection
            current_load={
                ResourceType.CPU: 0.0,
                ResourceType.MEMORY: 0.0,
                ResourceType.DISK: 0.0,
                ResourceType.NETWORK: 0.0,
                ResourceType.GPU: 0.0
            },
            max_capacity={
                ResourceType.CPU: float(cpu_cores),
                ResourceType.MEMORY: float(memory_mb),
                ResourceType.DISK: float(disk_gb),
                ResourceType.NETWORK: 1000.0,
                ResourceType.GPU: 0.0
            },
            supported_services=['api', 'processing', 'storage'],
            metadata={
                'version': '1.0.0',
                'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
                'started_at': datetime.now().isoformat()
            }
        )
        
        self.nodes[self.local_node_id] = node
        self._store_node(node)
        
        self.logger.info(f"Local node {self.local_node_id} registered")
    
    def start_management(self):
        """Start cluster management"""
        if self.management_active:
            return
        
        self.management_active = True
        
        # Start master election
        self.master_election.start_election()
        
        # Start management threads
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        self.metrics_thread = threading.Thread(target=self._metrics_loop, daemon=True)
        self.metrics_thread.start()
        
        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()
        
        self.cluster_state = ClusterState.ACTIVE
        
        self.logger.info("Cluster management started")
    
    def stop_management(self):
        """Stop cluster management"""
        self.management_active = False
        self.cluster_state = ClusterState.SHUTTING_DOWN
        
        # Stop master election
        self.master_election.stop_election()
        
        # Wait for threads
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        if self.metrics_thread:
            self.metrics_thread.join(timeout=5)
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
        
        self.logger.info("Cluster management stopped")
    
    def _heartbeat_loop(self):
        """Heartbeat loop for node management"""
        while self.management_active:
            try:
                # Update local node heartbeat
                if self.local_node_id in self.nodes:
                    self.nodes[self.local_node_id].last_heartbeat = datetime.now()
                    self._store_node(self.nodes[self.local_node_id])
                
                # Refresh node list from Redis
                self._refresh_nodes()
                
                # Check for offline nodes
                self._check_offline_nodes()
                
                # Sleep until next heartbeat
                time.sleep(ClusterConfig.HEARTBEAT_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Heartbeat loop error: {str(e)}")
                time.sleep(ClusterConfig.HEARTBEAT_INTERVAL)
    
    def _metrics_loop(self):
        """Metrics collection loop"""
        while self.management_active:
            try:
                # Collect cluster metrics
                metrics = self._collect_cluster_metrics()
                self.metrics_history.append(metrics)
                
                # Store in Redis
                self._store_metrics(metrics)
                
                # Sleep until next collection
                time.sleep(60)  # Collect every minute
                
            except Exception as e:
                self.logger.error(f"Metrics loop error: {str(e)}")
                time.sleep(60)
    
    def _health_check_loop(self):
        """Health check loop"""
        while self.management_active:
            try:
                # Check service health
                for service_id in list(self.service_manager.deployed_services.keys()):
                    self.service_manager.check_service_health(service_id)
                
                # Check cluster health
                self._check_cluster_health()
                
                # Sleep until next check
                time.sleep(ClusterConfig.HEALTH_CHECK_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Health check loop error: {str(e)}")
                time.sleep(ClusterConfig.HEALTH_CHECK_INTERVAL)
    
    def _collect_cluster_metrics(self) -> ClusterMetrics:
        """Collect cluster metrics"""
        active_nodes = [node for node in self.nodes.values() if node.status == NodeStatus.ACTIVE]
        
        total_cpu = sum(node.cpu_cores for node in active_nodes)
        total_memory = sum(node.memory_mb for node in active_nodes)
        total_disk = sum(node.disk_gb for node in active_nodes)
        
        # Calculate average usage
        avg_cpu = 0.0
        avg_memory = 0.0
        avg_disk = 0.0
        
        if active_nodes:
            cpu_usages = [node.current_load.get(ResourceType.CPU, 0) for node in active_nodes]
            memory_usages = [node.current_load.get(ResourceType.MEMORY, 0) for node in active_nodes]
            disk_usages = [node.current_load.get(ResourceType.DISK, 0) for node in active_nodes]
            
            avg_cpu = statistics.mean(cpu_usages) if cpu_usages else 0
            avg_memory = statistics.mean(memory_usages) if memory_usages else 0
            avg_disk = statistics.mean(disk_usages) if disk_usages else 0
        
        return ClusterMetrics(
            timestamp=datetime.now(),
            total_nodes=len(self.nodes),
            active_nodes=len(active_nodes),
            total_cpu_cores=total_cpu,
            total_memory_mb=total_memory,
            total_disk_gb=total_disk,
            avg_cpu_usage=avg_cpu,
            avg_memory_usage=avg_memory,
            avg_disk_usage=avg_disk,
            network_throughput=0.0,  # Would need actual measurement
            request_rate=0.0,        # Would need actual measurement
            error_rate=0.0           # Would need actual measurement
        )
    
    def _store_node(self, node: ClusterNode):
        """Store node information in Redis"""
        try:
            node_key = f"cluster:node:{node.node_id}"
            node_data = json.dumps(node.to_dict())
            self.redis_client.setex(node_key, ClusterConfig.NODE_TIMEOUT * 2, node_data)
        except Exception as e:
            self.logger.error(f"Failed to store node {node.node_id}: {str(e)}")
    
    def _store_metrics(self, metrics: ClusterMetrics):
        """Store metrics in Redis"""
        try:
            metrics_key = f"cluster:metrics:{int(metrics.timestamp.timestamp())}"
            metrics_data = json.dumps(metrics.to_dict())
            self.redis_client.setex(metrics_key, 86400, metrics_data)  # Keep for 24 hours
        except Exception as e:
            self.logger.error(f"Failed to store metrics: {str(e)}")
    
    def _refresh_nodes(self):
        """Refresh node list from Redis"""
        try:
            node_keys = self.redis_client.keys("cluster:node:*")
            
            for node_key in node_keys:
                node_data = self.redis_client.get(node_key)
                if node_data:
                    node_dict = json.loads(node_data)
                    node = self._dict_to_node(node_dict)
                    self.nodes[node.node_id] = node
                    
        except Exception as e:
            self.logger.error(f"Failed to refresh nodes: {str(e)}")
    
    def _check_offline_nodes(self):
        """Check for offline nodes"""
        cutoff_time = datetime.now() - timedelta(seconds=ClusterConfig.NODE_TIMEOUT)
        
        for node_id, node in list(self.nodes.items()):
            if node.last_heartbeat < cutoff_time:
                node.status = NodeStatus.OFFLINE
                self.logger.warning(f"Node {node_id} is offline")
    
    def _check_cluster_health(self):
        """Check overall cluster health"""
        active_nodes = [node for node in self.nodes.values() if node.status == NodeStatus.ACTIVE]
        
        if len(active_nodes) == 0:
            self.cluster_state = ClusterState.FAILED
        elif len(active_nodes) < len(self.nodes) // 2:
            self.cluster_state = ClusterState.DEGRADED
        else:
            self.cluster_state = ClusterState.ACTIVE
    
    def _dict_to_node(self, node_dict: Dict[str, Any]) -> ClusterNode:
        """Convert dictionary to ClusterNode"""
        return ClusterNode(
            node_id=node_dict['node_id'],
            host=node_dict['host'],
            port=node_dict['port'],
            role=ClusterRole(node_dict['role']),
            status=NodeStatus(node_dict['status']),
            last_heartbeat=datetime.fromisoformat(node_dict['last_heartbeat']),
            cpu_cores=node_dict['cpu_cores'],
            memory_mb=node_dict['memory_mb'],
            disk_gb=node_dict['disk_gb'],
            network_mbps=node_dict['network_mbps'],
            gpu_count=node_dict['gpu_count'],
            current_load={ResourceType(rt): load for rt, load in node_dict['current_load'].items()},
            max_capacity={ResourceType(rt): cap for rt, cap in node_dict['max_capacity'].items()},
            supported_services=node_dict['supported_services'],
            metadata=node_dict.get('metadata', {})
        )
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status"""
        return {
            'cluster_name': self.cluster_name,
            'cluster_state': self.cluster_state.value,
            'local_node_id': self.local_node_id,
            'is_master': self.master_election.is_master if self.master_election else False,
            'total_nodes': len(self.nodes),
            'active_nodes': len([n for n in self.nodes.values() if n.status == NodeStatus.ACTIVE]),
            'node_roles': {role.value: len([n for n in self.nodes.values() if n.role == role]) for role in ClusterRole},
            'resource_summary': self.resource_manager.get_cluster_resources(),
            'deployed_services': len(self.service_manager.deployed_services),
            'management_active': self.management_active
        }
    
    def get_node_details(self, node_id: str = None) -> Dict[str, Any]:
        """Get node details"""
        if node_id:
            if node_id in self.nodes:
                return self.nodes[node_id].to_dict()
            else:
                return {}
        else:
            return {node_id: node.to_dict() for node_id, node in self.nodes.items()}
    
    def deploy_service(self, service_name: str, version: str, required_resources: Dict[str, float],
                      health_check_url: str, target_nodes: List[str] = None) -> str:
        """Deploy service to cluster"""
        # Convert resource dict
        resources = {ResourceType(rt): amount for rt, amount in required_resources.items()}
        
        return self.service_manager.deploy_service(
            service_name, version, resources, health_check_url, target_nodes
        )
    
    def get_cluster_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get cluster metrics history"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            metrics.to_dict() for metrics in self.metrics_history
            if metrics.timestamp >= cutoff_time
        ]


# Initialize global cluster manager
cluster_manager = ClusterManager()
