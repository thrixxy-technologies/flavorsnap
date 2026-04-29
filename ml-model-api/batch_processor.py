"""
Advanced Batch Processor with Priority Queue Management for FlavorSnap
Handles batch processing with priority queues, load balancing, and failure recovery
"""

import asyncio
import heapq
import threading
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0

class TaskStatus(Enum):
    """Task status tracking"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"

@dataclass
class BatchTask:
    """Individual batch task with metadata"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    payload: Any = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    worker_id: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """For priority queue ordering"""
        return (self.priority.value, self.created_at) < (other.priority.value, other.created_at)

class DeadLetterQueue:
    """Dead letter queue for failed tasks"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._tasks: List[BatchTask] = []
        self._lock = threading.Lock()
    
    def add_task(self, task: BatchTask):
        """Add failed task to dead letter queue"""
        with self._lock:
            if len(self._tasks) >= self.max_size:
                # Remove oldest task
                self._tasks.pop(0)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            self._tasks.append(task)
            logger.warning(f"Task {task.id} moved to dead letter queue: {task.error_message}")
    
    def get_tasks(self, limit: int = 100) -> List[BatchTask]:
        """Get tasks from dead letter queue"""
        with self._lock:
            return self._tasks[-limit:]
    
    def retry_task(self, task_id: str) -> Optional[BatchTask]:
        """Remove task from dead letter queue for retry"""
        with self._lock:
            for i, task in enumerate(self._tasks):
                if task.id == task_id:
                    task.retry_count = 0
                    task.error_message = None
                    task.status = TaskStatus.PENDING
                    return self._tasks.pop(i)
            return None
    
    def clear_old_tasks(self, days: int = 7):
        """Clear old tasks from dead letter queue"""
        cutoff_date = datetime.now() - timedelta(days=days)
        with self._lock:
            self._tasks = [task for task in self._tasks 
                          if task.completed_at and task.completed_at > cutoff_date]

class LoadBalancer:
    """Load balancer for worker distribution"""
    
    def __init__(self, workers: List[str]):
        self.workers = workers
        self.current_index = 0
        self.worker_loads: Dict[str, int] = {worker: 0 for worker in workers}
        self._lock = threading.Lock()
    
    def get_next_worker(self) -> str:
        """Get next available worker using round-robin with load awareness"""
        with self._lock:
            # Find worker with minimum load
            min_load = min(self.worker_loads.values())
            available_workers = [w for w, load in self.worker_loads.items() if load == min_load]
            
            if available_workers:
                worker = available_workers[0]
                self.worker_loads[worker] += 1
                return worker
            else:
                # Fallback to round-robin
                worker = self.workers[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.workers)
                return worker
    
    def release_worker(self, worker_id: str):
        """Release worker from task"""
        with self._lock:
            if worker_id in self.worker_loads:
                self.worker_loads[worker_id] = max(0, self.worker_loads[worker_id] - 1)

class BatchProcessor:
    """Advanced batch processor with priority queues and monitoring"""
    
    def __init__(self, max_workers: int = 4, queue_size: int = 10000):
        self.max_workers = max_workers
        self.queue_size = queue_size
        
        # Priority queues
        self._priority_queues: Dict[TaskPriority, List[BatchTask]] = {
            priority: [] for priority in TaskPriority
        }
        
        # Task tracking
        self._running_tasks: Dict[str, BatchTask] = {}
        self._completed_tasks: Dict[str, BatchTask] = {}
        
        # Components
        self.dead_letter_queue = DeadLetterQueue()
        self.load_balancer = LoadBalancer([f"worker_{i}" for i in range(max_workers)])
        
        # Threading and synchronization
        self._queue_lock = threading.Lock()
        self._task_lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Statistics
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'average_processing_time': 0.0,
            'queue_sizes': {priority.name: 0 for priority in TaskPriority}
        }
        
        # Start processing threads
        self._processing_threads = []
        self._start_processors()
    
    def _start_processors(self):
        """Start worker threads for processing tasks"""
        for i in range(self.max_workers):
            thread = threading.Thread(target=self._process_tasks, args=(f"worker_{i}",))
            thread.daemon = True
            thread.start()
            self._processing_threads.append(thread)
    
    def submit_task(self, 
                   payload: Any,
                   priority: TaskPriority = TaskPriority.NORMAL,
                   max_retries: int = 3,
                   timeout_seconds: int = 300,
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """Submit a new task for processing"""
        
        # Check queue size limits
        total_queue_size = sum(len(queue) for queue in self._priority_queues.values())
        if total_queue_size >= self.queue_size:
            raise RuntimeError("Queue is full")
        
        task = BatchTask(
            priority=priority,
            payload=payload,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            metadata=metadata or {}
        )
        
        with self._queue_lock:
            heapq.heappush(self._priority_queues[priority], task)
            self.stats['total_tasks'] += 1
            self.stats['queue_sizes'][priority.name] = len(self._priority_queues[priority])
        
        logger.info(f"Task {task.id} submitted with priority {priority.name}")
        return task.id
    
    def _process_tasks(self, worker_id: str):
        """Worker thread main processing loop"""
        logger.info(f"Worker {worker_id} started")
        
        while not self._shutdown_event.is_set():
            task = self._get_next_task()
            if task is None:
                time.sleep(0.1)  # No tasks available, wait
                continue
            
            # Assign task to worker
            task.worker_id = worker_id
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            with self._task_lock:
                self._running_tasks[task.id] = task
            
            try:
                # Process task with timeout
                future = self._executor.submit(self._execute_task, task)
                try:
                    result = future.result(timeout=task.timeout_seconds)
                    self._handle_task_completion(task, TaskStatus.COMPLETED, result)
                except asyncio.TimeoutError:
                    self._handle_task_completion(task, TaskStatus.FAILED, None, "Task timeout")
                except Exception as e:
                    self._handle_task_completion(task, TaskStatus.FAILED, None, str(e))
                    
            except Exception as e:
                logger.error(f"Worker {worker_id} error processing task {task.id}: {e}")
                self._handle_task_completion(task, TaskStatus.FAILED, None, str(e))
            finally:
                with self._task_lock:
                    self._running_tasks.pop(task.id, None)
                self.load_balancer.release_worker(worker_id)
    
    def _get_next_task(self) -> Optional[BatchTask]:
        """Get next task from priority queues"""
        with self._queue_lock:
            # Check queues in priority order
            for priority in sorted(TaskPriority, key=lambda p: p.value):
                if self._priority_queues[priority]:
                    task = heapq.heappop(self._priority_queues[priority])
                    self.stats['queue_sizes'][priority.name] = len(self._priority_queues[priority])
                    return task
            return None
    
    def _execute_task(self, task: BatchTask) -> Any:
        """Execute individual task - to be overridden by subclasses"""
        # Default implementation - just return the payload
        # In practice, this would contain the actual processing logic
        time.sleep(0.1)  # Simulate processing
        return f"Processed: {task.payload}"
    
    def _handle_task_completion(self, task: BatchTask, status: TaskStatus, result: Any, error: str = None):
        """Handle task completion or failure"""
        task.status = status
        task.completed_at = datetime.now()
        
        if status == TaskStatus.COMPLETED:
            self.stats['completed_tasks'] += 1
            processing_time = (task.completed_at - task.started_at).total_seconds()
            self._update_average_processing_time(processing_time)
            logger.info(f"Task {task.id} completed successfully")
        else:
            task.error_message = error
            if task.retry_count < task.max_retries:
                # Retry the task
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                task.started_at = None
                task.completed_at = None
                
                with self._queue_lock:
                    heapq.heappush(self._priority_queues[task.priority], task)
                    self.stats['queue_sizes'][task.priority.name] += 1
                
                logger.warning(f"Task {task.id} failed, retrying ({task.retry_count}/{task.max_retries})")
            else:
                # Move to dead letter queue
                self.stats['failed_tasks'] += 1
                self.dead_letter_queue.add_task(task)
                logger.error(f"Task {task.id} failed permanently: {error}")
        
        with self._task_lock:
            self._completed_tasks[task.id] = task
    
    def _update_average_processing_time(self, processing_time: float):
        """Update average processing time"""
        total_completed = self.stats['completed_tasks']
        if total_completed == 1:
            self.stats['average_processing_time'] = processing_time
        else:
            current_avg = self.stats['average_processing_time']
            self.stats['average_processing_time'] = (
                (current_avg * (total_completed - 1) + processing_time) / total_completed
            )
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        with self._task_lock:
            # Check running tasks
            if task_id in self._running_tasks:
                task = self._running_tasks[task_id]
                return self._task_to_dict(task)
            
            # Check completed tasks
            if task_id in self._completed_tasks:
                task = self._completed_tasks[task_id]
                return self._task_to_dict(task)
        
        # Check dead letter queue
        for task in self.dead_letter_queue.get_tasks():
            if task.id == task_id:
                return self._task_to_dict(task)
        
        return None
    
    def _task_to_dict(self, task: BatchTask) -> Dict[str, Any]:
        """Convert task to dictionary representation"""
        return {
            'id': task.id,
            'priority': task.priority.name,
            'status': task.status.value,
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'retry_count': task.retry_count,
            'max_retries': task.max_retries,
            'worker_id': task.worker_id,
            'error_message': task.error_message,
            'metadata': task.metadata
        }
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics"""
        with self._queue_lock, self._task_lock:
            return {
                'total_tasks': self.stats['total_tasks'],
                'completed_tasks': self.stats['completed_tasks'],
                'failed_tasks': self.stats['failed_tasks'],
                'running_tasks': len(self._running_tasks),
                'average_processing_time': self.stats['average_processing_time'],
                'queue_sizes': self.stats['queue_sizes'].copy(),
                'dead_letter_queue_size': len(self.dead_letter_queue._tasks),
                'worker_loads': self.load_balancer.worker_loads.copy()
            }
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        with self._queue_lock:
            for priority_queue in self._priority_queues.values():
                for i, task in enumerate(priority_queue):
                    if task.id == task_id:
                        task.status = TaskStatus.CANCELLED
                        priority_queue.pop(i)
                        self.stats['queue_sizes'][task.priority.name] = len(priority_queue)
                        logger.info(f"Task {task_id} cancelled")
                        return True
        return False
    
    def retry_failed_task(self, task_id: str) -> bool:
        """Retry a failed task from dead letter queue"""
        task = self.dead_letter_queue.retry_task(task_id)
        if task:
            with self._queue_lock:
                heapq.heappush(self._priority_queues[task.priority], task)
                self.stats['queue_sizes'][task.priority.name] += 1
            logger.info(f"Task {task_id} requeued for retry")
            return True
        return False
    
    def shutdown(self, wait: bool = True):
        """Shutdown the batch processor"""
        logger.info("Shutting down batch processor")
        self._shutdown_event.set()
        
        if wait:
            for thread in self._processing_threads:
                thread.join(timeout=5)
        
        self._executor.shutdown(wait=wait)
        logger.info("Batch processor shutdown complete")

class MLBatchProcessor(BatchProcessor):
    """Specialized batch processor for ML model inference"""
    
    def __init__(self, model, max_workers: int = 4, queue_size: int = 10000):
        super().__init__(max_workers, queue_size)
        self.model = model
    
    def _execute_task(self, task: BatchTask) -> Any:
        """Execute ML inference task"""
        try:
            # Extract image data from payload
            image_data = task.payload.get('image_data')
            if not image_data:
                raise ValueError("No image data in payload")
            
            # Perform inference (placeholder - actual implementation would use the model)
            # result = self.model.predict(image_data)
            
            # Simulate ML processing
            time.sleep(0.5)
            result = {
                'label': 'Sample Food',
                'confidence': 0.95,
                'processing_time': 0.5
            }
            
            return result
            
        except Exception as e:
            logger.error(f"ML inference failed for task {task.id}: {e}")
            raise
