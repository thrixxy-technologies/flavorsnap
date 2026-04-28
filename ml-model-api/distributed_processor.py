"""
Advanced Distributed Processor for FlavorSnap API
Implements distributed task processing with load balancing and fault tolerance
"""
import os
import json
import time
import uuid
import threading
import queue
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import logging
import redis
import requests
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing as mp


class TaskStatus(Enum):
    """Task status values"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class NodeStatus(Enum):
    """Node status values"""
    ACTIVE = "active"
    BUSY = "busy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


@dataclass
class Task:
    """Distributed task data structure"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    assigned_node: Optional[str]
    retry_count: int
    max_retries: int
    timeout: int
    result: Optional[Any]
    error: Optional[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data


@dataclass
class Node:
    """Distributed node data structure"""
    node_id: str
    host: str
    port: int
    status: NodeStatus
    last_heartbeat: datetime
    cpu_count: int
    memory_mb: int
    active_tasks: int
    max_tasks: int
    supported_task_types: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['status'] = self.status.value
        data['last_heartbeat'] = self.last_heartbeat.isoformat()
        return data


class DistributedConfig:
    """Distributed processing configuration"""
    
    # Task processing
    MAX_CONCURRENT_TASKS = 10
    TASK_TIMEOUT = 300  # 5 minutes
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    # Node management
    HEARTBEAT_INTERVAL = 30  # seconds
    NODE_TIMEOUT = 90  # seconds
    HEALTH_CHECK_INTERVAL = 60  # seconds
    
    # Load balancing
    LOAD_BALANCE_ALGORITHM = "round_robin"  # round_robin, least_loaded, weighted
    TASK_QUEUE_SIZE = 1000
    
    # Fault tolerance
    FAILOVER_ENABLED = True
    CIRCUIT_BREAKER_THRESHOLD = 5
    CIRCUIT_BREAKER_TIMEOUT = 60  # seconds
    
    # Communication
    REDIS_DB = 0
    COMMUNICATION_TIMEOUT = 10  # seconds
    MAX_REDIS_CONNECTIONS = 10


class TaskQueue:
    """Distributed task queue using Redis"""
    
    def __init__(self, redis_client: redis.Redis, queue_name: str = "distributed_tasks"):
        self.redis = redis_client
        self.queue_name = queue_name
        self.priority_queues = {
            TaskPriority.CRITICAL: f"{queue_name}:critical",
            TaskPriority.HIGH: f"{queue_name}:high",
            TaskPriority.NORMAL: f"{queue_name}:normal",
            TaskPriority.LOW: f"{queue_name}:low"
        }
        self.logger = logging.getLogger(__name__)
    
    def enqueue(self, task: Task) -> bool:
        """Enqueue task with priority"""
        try:
            queue_key = self.priority_queues[task.priority]
            
            # Serialize task
            task_data = json.dumps(task.to_dict())
            
            # Add to priority queue
            self.redis.lpush(queue_key, task_data)
            
            # Store task details
            task_key = f"task:{task.task_id}"
            self.redis.setex(task_key, 3600, task_data)  # Keep for 1 hour
            
            self.logger.debug(f"Task {task.task_id} enqueued to {queue_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enqueue task {task.task_id}: {str(e)}")
            return False
    
    def dequeue(self, node_id: str, supported_types: List[str]) -> Optional[Task]:
        """Dequeue highest priority task"""
        try:
            # Check queues in priority order
            for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]:
                queue_key = self.priority_queues[priority]
                
                # Get task from queue
                task_data = self.redis.brpop(queue_key, timeout=1)
                
                if task_data:
                    task_json = task_data[1]
                    task_dict = json.loads(task_json)
                    
                    # Check if node supports this task type
                    if task_dict['task_type'] in supported_types:
                        task = self._dict_to_task(task_dict)
                        
                        # Update task assignment
                        task.assigned_node = node_id
                        task.status = TaskStatus.RUNNING
                        task.started_at = datetime.now()
                        
                        # Store updated task
                        self._update_task(task)
                        
                        self.logger.debug(f"Task {task.task_id} dequeued by node {node_id}")
                        return task
                    else:
                        # Put task back if not supported
                        self.redis.lpush(queue_key, task_json)
                        continue
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to dequeue task: {str(e)}")
            return None
    
    def update_task_status(self, task: Task) -> bool:
        """Update task status"""
        return self._update_task(task)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        try:
            task_key = f"task:{task_id}"
            task_data = self.redis.get(task_key)
            
            if task_data:
                task_dict = json.loads(task_data)
                return self._dict_to_task(task_dict)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get task {task_id}: {str(e)}")
            return None
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        stats = {}
        
        for priority, queue_key in self.priority_queues.items():
            stats[priority.name] = self.redis.llen(queue_key)
        
        return stats
    
    def _update_task(self, task: Task) -> bool:
        """Update task in storage"""
        try:
            task_key = f"task:{task.task_id}"
            task_data = json.dumps(task.to_dict())
            self.redis.setex(task_key, 3600, task_data)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update task {task.task_id}: {str(e)}")
            return False
    
    def _dict_to_task(self, task_dict: Dict[str, Any]) -> Task:
        """Convert dictionary to Task"""
        return Task(
            task_id=task_dict['task_id'],
            task_type=task_dict['task_type'],
            payload=task_dict['payload'],
            priority=TaskPriority(task_dict['priority']),
            status=TaskStatus(task_dict['status']),
            created_at=datetime.fromisoformat(task_dict['created_at']),
            started_at=datetime.fromisoformat(task_dict['started_at']) if task_dict.get('started_at') else None,
            completed_at=datetime.fromisoformat(task_dict['completed_at']) if task_dict.get('completed_at') else None,
            assigned_node=task_dict.get('assigned_node'),
            retry_count=task_dict['retry_count'],
            max_retries=task_dict['max_retries'],
            timeout=task_dict['timeout'],
            result=task_dict.get('result'),
            error=task_dict.get('error'),
            metadata=task_dict.get('metadata', {})
        )


class NodeManager:
    """Manage distributed nodes"""
    
    def __init__(self, redis_client: redis.Redis, node_id: str = None):
        self.redis = redis_client
        self.node_id = node_id or f"node_{uuid.uuid4().hex[:8]}"
        self.nodes: Dict[str, Node] = {}
        self.logger = logging.getLogger(__name__)
        
        # Register this node
        self._register_self()
    
    def _register_self(self):
        """Register this node"""
        import psutil
        
        node = Node(
            node_id=self.node_id,
            host=os.getenv('NODE_HOST', 'localhost'),
            port=int(os.getenv('NODE_PORT', 8080)),
            status=NodeStatus.ACTIVE,
            last_heartbeat=datetime.now(),
            cpu_count=psutil.cpu_count(),
            memory_mb=psutil.virtual_memory().total // 1024 // 1024,
            active_tasks=0,
            max_tasks=DistributedConfig.MAX_CONCURRENT_TASKS,
            supported_task_types=['image_processing', 'model_inference', 'data_analysis'],
            metadata={
                'version': '1.0.0',
                'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}"
            }
        )
        
        self.nodes[self.node_id] = node
        self._update_node(node)
    
    def update_heartbeat(self):
        """Update heartbeat for this node"""
        if self.node_id in self.nodes:
            self.nodes[self.node_id].last_heartbeat = datetime.now()
            self._update_node(self.nodes[self.node_id])
    
    def register_node(self, node: Node) -> bool:
        """Register a new node"""
        try:
            self.nodes[node.node_id] = node
            self._update_node(node)
            self.logger.info(f"Node {node.node_id} registered")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register node {node.node_id}: {str(e)}")
            return False
    
    def unregister_node(self, node_id: str) -> bool:
        """Unregister a node"""
        try:
            if node_id in self.nodes:
                del self.nodes[node_id]
                
                # Remove from Redis
                node_key = f"node:{node_id}"
                self.redis.delete(node_key)
                
                self.logger.info(f"Node {node_id} unregistered")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to unregister node {node_id}: {str(e)}")
            return False
    
    def get_active_nodes(self) -> List[Node]:
        """Get list of active nodes"""
        self._refresh_nodes()
        
        cutoff_time = datetime.now() - timedelta(seconds=DistributedConfig.NODE_TIMEOUT)
        
        return [
            node for node in self.nodes.values()
            if node.last_heartbeat > cutoff_time and node.status == NodeStatus.ACTIVE
        ]
    
    def get_node_for_task(self, task_type: str) -> Optional[Node]:
        """Get best node for task based on load balancing"""
        active_nodes = [
            node for node in self.get_active_nodes()
            if task_type in node.supported_task_types
        ]
        
        if not active_nodes:
            return None
        
        algorithm = DistributedConfig.LOAD_BALANCE_ALGORITHM
        
        if algorithm == "least_loaded":
            return min(active_nodes, key=lambda n: n.active_tasks / n.max_tasks)
        elif algorithm == "weighted":
            return max(active_nodes, key=lambda n: (n.max_tasks - n.active_tasks) * n.cpu_count)
        else:  # round_robin
            # Simple round-robin based on node count
            return active_nodes[hash(task_type) % len(active_nodes)]
    
    def update_node_status(self, node_id: str, status: NodeStatus) -> bool:
        """Update node status"""
        if node_id in self.nodes:
            self.nodes[node_id].status = status
            self._update_node(self.nodes[node_id])
            return True
        return False
    
    def increment_active_tasks(self, node_id: str) -> bool:
        """Increment active task count for node"""
        if node_id in self.nodes:
            self.nodes[node_id].active_tasks += 1
            self._update_node(self.nodes[node_id])
            return True
        return False
    
    def decrement_active_tasks(self, node_id: str) -> bool:
        """Decrement active task count for node"""
        if node_id in self.nodes:
            self.nodes[node_id].active_tasks = max(0, self.nodes[node_id].active_tasks - 1)
            self._update_node(self.nodes[node_id])
            return True
        return False
    
    def _update_node(self, node: Node):
        """Update node in Redis"""
        try:
            node_key = f"node:{node.node_id}"
            node_data = json.dumps(node.to_dict())
            self.redis.setex(node_key, DistributedConfig.NODE_TIMEOUT * 2, node_data)
            
        except Exception as e:
            self.logger.error(f"Failed to update node {node.node_id}: {str(e)}")
    
    def _refresh_nodes(self):
        """Refresh node list from Redis"""
        try:
            node_keys = self.redis.keys("node:*")
            
            for node_key in node_keys:
                node_data = self.redis.get(node_key)
                if node_data:
                    node_dict = json.loads(node_data)
                    node = self._dict_to_node(node_dict)
                    self.nodes[node.node_id] = node
                    
        except Exception as e:
            self.logger.error(f"Failed to refresh nodes: {str(e)}")
    
    def _dict_to_node(self, node_dict: Dict[str, Any]) -> Node:
        """Convert dictionary to Node"""
        return Node(
            node_id=node_dict['node_id'],
            host=node_dict['host'],
            port=node_dict['port'],
            status=NodeStatus(node_dict['status']),
            last_heartbeat=datetime.fromisoformat(node_dict['last_heartbeat']),
            cpu_count=node_dict['cpu_count'],
            memory_mb=node_dict['memory_mb'],
            active_tasks=node_dict['active_tasks'],
            max_tasks=node_dict['max_tasks'],
            supported_task_types=node_dict['supported_task_types'],
            metadata=node_dict.get('metadata', {})
        )


class TaskExecutor:
    """Execute distributed tasks"""
    
    def __init__(self, node_manager: NodeManager, task_queue: TaskQueue):
        self.node_manager = node_manager
        self.task_queue = task_queue
        self.logger = logging.getLogger(__name__)
        self.task_handlers: Dict[str, Callable] = {}
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=DistributedConfig.MAX_CONCURRENT_TASKS)
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default task handlers"""
        self.register_handler('image_processing', self._handle_image_processing)
        self.register_handler('model_inference', self._handle_model_inference)
        self.register_handler('data_analysis', self._handle_data_analysis)
        self.register_handler('health_check', self._handle_health_check)
    
    def register_handler(self, task_type: str, handler: Callable):
        """Register task handler"""
        self.task_handlers[task_type] = handler
        self.logger.info(f"Registered handler for task type: {task_type}")
    
    def start_processing(self):
        """Start task processing"""
        if self.running:
            return
        
        self.running = True
        
        # Start worker threads
        for i in range(DistributedConfig.MAX_CONCURRENT_TASKS):
            thread = threading.Thread(target=self._worker_loop, daemon=True)
            thread.start()
        
        self.logger.info("Task processing started")
    
    def stop_processing(self):
        """Stop task processing"""
        self.running = False
        self.executor.shutdown(wait=True)
        self.logger.info("Task processing stopped")
    
    def _worker_loop(self):
        """Worker thread loop"""
        while self.running:
            try:
                # Get task from queue
                node = self.node_manager.nodes[self.node_manager.node_id]
                task = self.task_queue.dequeue(self.node_manager.node_id, node.supported_task_types)
                
                if task:
                    # Execute task
                    self.executor.submit(self._execute_task, task)
                else:
                    # No task available, wait a bit
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"Worker loop error: {str(e)}")
                time.sleep(1)
    
    def _execute_task(self, task: Task):
        """Execute a single task"""
        start_time = time.time()
        
        try:
            # Increment active tasks
            self.node_manager.increment_active_tasks(self.node_manager.node_id)
            
            # Check timeout
            if time.time() - start_time > task.timeout:
                raise TimeoutError(f"Task {task.task_id} timed out")
            
            # Get handler
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"No handler for task type: {task.task_type}")
            
            # Execute handler
            result = handler(task.payload)
            
            # Update task with result
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()
            
            self.logger.info(f"Task {task.task_id} completed successfully")
            
        except Exception as e:
            # Handle task failure
            task.error = str(e)
            task.completed_at = datetime.now()
            
            if task.retry_count < task.max_retries:
                # Retry task
                task.status = TaskStatus.RETRYING
                task.retry_count += 1
                
                # Add delay before retry
                time.sleep(DistributedConfig.RETRY_DELAY)
                
                # Re-queue task
                self.task_queue.enqueue(task)
                
                self.logger.warning(f"Task {task.task_id} failed, retrying ({task.retry_count}/{task.max_retries}): {str(e)}")
            else:
                # Mark as failed
                task.status = TaskStatus.FAILED
                self.logger.error(f"Task {task.task_id} failed permanently: {str(e)}")
        
        finally:
            # Update task status
            self.task_queue.update_task_status(task)
            
            # Decrement active tasks
            self.node_manager.decrement_active_tasks(self.node_manager.node_id)
    
    def _handle_image_processing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle image processing task"""
        # Simulate image processing
        time.sleep(2)
        
        return {
            'status': 'completed',
            'processed_image': f"processed_{payload.get('image_id', 'unknown')}.jpg",
            'processing_time': 2.0
        }
    
    def _handle_model_inference(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle model inference task"""
        # Simulate model inference
        time.sleep(1)
        
        return {
            'status': 'completed',
            'prediction': [0.1, 0.3, 0.6],  # Example probabilities
            'confidence': 0.6,
            'inference_time': 1.0
        }
    
    def _handle_data_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data analysis task"""
        # Simulate data analysis
        time.sleep(3)
        
        return {
            'status': 'completed',
            'analysis_results': {
                'mean': 42.5,
                'std': 15.2,
                'samples': len(payload.get('data', []))
            },
            'analysis_time': 3.0
        }
    
    def _handle_health_check(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check task"""
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'node_id': self.node_manager.node_id
        }


class DistributedProcessor:
    """Main distributed processor"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.redis_client = None
        self.node_manager = None
        self.task_queue = None
        self.task_executor = None
        
        self.processing_active = False
        self.heartbeat_thread = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize distributed processor with Flask app"""
        self.app = app
        
        # Initialize Redis
        redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = redis.from_url(redis_url, decode_responses=False)
        
        # Initialize components
        self.node_manager = NodeManager(self.redis_client)
        self.task_queue = TaskQueue(self.redis_client)
        self.task_executor = TaskExecutor(self.node_manager, self.task_queue)
        
        # Start processing
        self.start_processing()
        
        self.logger.info("Distributed processor initialized")
    
    def start_processing(self):
        """Start distributed processing"""
        if self.processing_active:
            return
        
        self.processing_active = True
        
        # Start task executor
        self.task_executor.start_processing()
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        self.logger.info("Distributed processing started")
    
    def stop_processing(self):
        """Stop distributed processing"""
        self.processing_active = False
        
        # Stop task executor
        self.task_executor.stop_processing()
        
        # Wait for heartbeat thread
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        
        self.logger.info("Distributed processing stopped")
    
    def submit_task(self, task_type: str, payload: Dict[str, Any], 
                   priority: TaskPriority = TaskPriority.NORMAL,
                   timeout: int = DistributedConfig.TASK_TIMEOUT,
                   max_retries: int = DistributedConfig.MAX_RETRIES) -> str:
        """Submit a task for distributed processing"""
        task = Task(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            payload=payload,
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            assigned_node=None,
            retry_count=0,
            max_retries=max_retries,
            timeout=timeout,
            result=None,
            error=None,
            metadata={}
        )
        
        if self.task_queue.enqueue(task):
            self.logger.info(f"Task {task.task_id} submitted for processing")
            return task.task_id
        else:
            raise RuntimeError("Failed to enqueue task")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        task = self.task_queue.get_task(task_id)
        return task.to_dict() if task else None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        task = self.task_queue.get_task(task_id)
        if task and task.status in [TaskStatus.PENDING, TaskStatus.RETRYING]:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            return self.task_queue.update_task_status(task)
        return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            'queue_stats': self.task_queue.get_queue_stats(),
            'active_nodes': len(self.node_manager.get_active_nodes()),
            'node_details': [node.to_dict() for node in self.node_manager.get_active_nodes()]
        }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        # Get task statistics from Redis
        try:
            task_keys = self.redis_client.keys("task:*")
            
            total_tasks = len(task_keys)
            status_counts = defaultdict(int)
            
            for task_key in task_keys:
                task_data = self.redis_client.get(task_key)
                if task_data:
                    task_dict = json.loads(task_data)
                    status_counts[task_dict['status']] += 1
            
            return {
                'total_tasks': total_tasks,
                'status_breakdown': dict(status_counts),
                'processing_active': self.processing_active,
                'node_count': len(self.node_manager.get_active_nodes())
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get processing stats: {str(e)}")
            return {}
    
    def _heartbeat_loop(self):
        """Heartbeat loop for node management"""
        while self.processing_active:
            try:
                # Update heartbeat
                self.node_manager.update_heartbeat()
                
                # Sleep until next heartbeat
                time.sleep(DistributedConfig.HEARTBEAT_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Heartbeat loop error: {str(e)}")
                time.sleep(DistributedConfig.HEARTBEAT_INTERVAL)


# Initialize global distributed processor
distributed_processor = DistributedProcessor()
