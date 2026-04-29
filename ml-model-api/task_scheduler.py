"""
Advanced Task Scheduler for FlavorSnap API
Implements intelligent task scheduling with priority management and resource optimization
"""
import os
import time
import json
import uuid
import threading
import heapq
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import logging
import redis
from distributed_processor import Task, TaskStatus, TaskPriority, distributed_processor


class ScheduleType(Enum):
    """Schedule types"""
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    RECURRING = "recurring"
    CRON = "cron"
    DEPENDENT = "dependent"


class TaskDependencyType(Enum):
    """Task dependency types"""
    SUCCESS = "success"
    COMPLETION = "completion"
    FAILURE = "failure"


@dataclass
class ScheduledTask:
    """Scheduled task data structure"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: TaskPriority
    schedule_type: ScheduleType
    scheduled_time: datetime
    created_at: datetime
    dependencies: List[str]  # Task IDs this task depends on
    dependency_type: TaskDependencyType
    retry_policy: Dict[str, Any]
    max_retries: int
    timeout: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['schedule_type'] = self.schedule_type.value
        data['dependency_type'] = self.dependency_type.value
        data['scheduled_time'] = self.scheduled_time.isoformat()
        data['created_at'] = self.created_at.isoformat()
        return data


@dataclass
class ScheduleResult:
    """Schedule execution result"""
    schedule_id: str
    task_id: str
    executed_at: datetime
    success: bool
    result: Any
    error: Optional[str]
    execution_time: float
    next_run: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['executed_at'] = self.executed_at.isoformat()
        if self.next_run:
            data['next_run'] = self.next_run.isoformat()
        return data


class SchedulerConfig:
    """Task scheduler configuration"""
    
    # Scheduling
    MAX_CONCURRENT_SCHEDULES = 50
    SCHEDULE_CHECK_INTERVAL = 1  # seconds
    TASK_QUEUE_SIZE = 1000
    
    # Retry policies
    DEFAULT_RETRY_DELAY = 60  # seconds
    MAX_RETRY_DELAY = 3600  # seconds
    RETRY_BACKOFF_MULTIPLIER = 2.0
    
    # Dependencies
    MAX_DEPENDENCY_DEPTH = 10
    DEPENDENCY_CHECK_INTERVAL = 5  # seconds
    
    # Resource limits
    MAX_MEMORY_PER_TASK = 1024  # MB
    MAX_CPU_PER_TASK = 2.0  # cores
    
    # Cleanup
    COMPLETED_TASK_RETENTION = 3600  # seconds
    FAILED_TASK_RETENTION = 7200   # seconds


class TaskQueue:
    """Priority-based task queue"""
    
    def __init__(self):
        self.queue = []
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def enqueue(self, task: ScheduledTask) -> bool:
        """Add task to queue"""
        with self.lock:
            try:
                # Priority queue uses (priority, timestamp, task)
                # Lower priority number = higher priority
                priority_value = -task.priority.value  # Negative for max-heap behavior
                heapq.heappush(self.queue, (priority_value, task.scheduled_time.timestamp(), task))
                self.logger.debug(f"Task {task.task_id} enqueued")
                return True
            except Exception as e:
                self.logger.error(f"Failed to enqueue task {task.task_id}: {str(e)}")
                return False
    
    def dequeue(self) -> Optional[ScheduledTask]:
        """Get next task from queue"""
        with self.lock:
            while self.queue:
                priority, timestamp, task = heapq.heappop(self.queue)
                
                # Check if task is ready to run
                if datetime.now() >= task.scheduled_time:
                    return task
                else:
                    # Put task back and break (not ready yet)
                    heapq.heappush(self.queue, (priority, timestamp, task))
                    break
            
            return None
    
    def peek(self) -> Optional[ScheduledTask]:
        """Peek at next task without removing"""
        with self.lock:
            if self.queue:
                priority, timestamp, task = self.queue[0]
                
                if datetime.now() >= task.scheduled_time:
                    return task
            
            return None
    
    def size(self) -> int:
        """Get queue size"""
        with self.lock:
            return len(self.queue)
    
    def get_tasks_by_priority(self) -> Dict[TaskPriority, List[ScheduledTask]]:
        """Get tasks grouped by priority"""
        with self.lock:
            grouped = defaultdict(list)
            
            for priority, timestamp, task in self.queue:
                grouped[task.priority].append(task)
            
            return dict(grouped)


class DependencyManager:
    """Manage task dependencies"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.task_dependencies: Dict[str, List[str]] = defaultdict(list)
        self.dependency_graph: Dict[str, List[str]] = defaultdict(list)
        self.completed_tasks: Dict[str, bool] = {}
        self.failed_tasks: Dict[str, bool] = {}
    
    def add_dependency(self, task_id: str, depends_on: str, dependency_type: TaskDependencyType):
        """Add task dependency"""
        self.task_dependencies[task_id].append(depends_on)
        self.dependency_graph[depends_on].append(task_id)
        self.logger.debug(f"Added dependency: {task_id} depends on {depends_on}")
    
    def can_execute(self, task_id: str, dependency_type: TaskDependencyType) -> bool:
        """Check if task can be executed based on dependencies"""
        dependencies = self.task_dependencies.get(task_id, [])
        
        if not dependencies:
            return True
        
        for dep_task_id in dependencies:
            if dependency_type == TaskDependencyType.SUCCESS:
                if not self.completed_tasks.get(dep_task_id, False):
                    return False
            elif dependency_type == TaskDependencyType.COMPLETION:
                if not (self.completed_tasks.get(dep_task_id, False) or self.failed_tasks.get(dep_task_id, False)):
                    return False
            elif dependency_type == TaskDependencyType.FAILURE:
                if not self.failed_tasks.get(dep_task_id, False):
                    return False
        
        return True
    
    def mark_completed(self, task_id: str):
        """Mark task as completed"""
        self.completed_tasks[task_id] = True
        self.logger.debug(f"Task {task_id} marked as completed")
    
    def mark_failed(self, task_id: str):
        """Mark task as failed"""
        self.failed_tasks[task_id] = True
        self.logger.debug(f"Task {task_id} marked as failed")
    
    def get_dependent_tasks(self, task_id: str) -> List[str]:
        """Get tasks that depend on this task"""
        return self.dependency_graph.get(task_id, [])
    
    def check_circular_dependency(self, task_id: str, dependencies: List[str]) -> bool:
        """Check for circular dependencies"""
        visited = set()
        
        def dfs(current_id: str) -> bool:
            if current_id in visited:
                return True  # Circular dependency detected
            
            if current_id == task_id:
                return True
            
            visited.add(current_id)
            
            for dep in self.dependency_graph.get(current_id, []):
                if dfs(dep):
                    return True
            
            visited.remove(current_id)
            return False
        
        for dep in dependencies:
            if dfs(dep):
                return True
        
        return False


class RetryPolicy:
    """Retry policy management"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_retry_delay(self, retry_count: int, policy: Dict[str, Any]) -> int:
        """Calculate retry delay based on policy"""
        retry_type = policy.get('type', 'exponential')
        base_delay = policy.get('base_delay', SchedulerConfig.DEFAULT_RETRY_DELAY)
        max_delay = policy.get('max_delay', SchedulerConfig.MAX_RETRY_DELAY)
        multiplier = policy.get('multiplier', SchedulerConfig.RETRY_BACKOFF_MULTIPLIER)
        
        if retry_type == 'exponential':
            delay = base_delay * (multiplier ** retry_count)
        elif retry_type == 'linear':
            delay = base_delay * (retry_count + 1)
        elif retry_type == 'fixed':
            delay = base_delay
        else:
            delay = base_delay
        
        return min(delay, max_delay)
    
    def should_retry(self, retry_count: int, max_retries: int, error: str = None) -> bool:
        """Determine if task should be retried"""
        if retry_count >= max_retries:
            return False
        
        # Check for non-retryable errors
        non_retryable_errors = [
            'authentication_failed',
            'permission_denied',
            'invalid_input',
            'not_found'
        ]
        
        if error:
            for non_retryable in non_retryable_errors:
                if non_retryable in error.lower():
                    return False
        
        return True


class TaskScheduler:
    """Advanced task scheduler"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.redis_client = None
        
        self.task_queue = TaskQueue()
        self.dependency_manager = DependencyManager()
        self.retry_policy = RetryPolicy()
        
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.execution_history: deque = deque(maxlen=1000)
        
        self.scheduler_active = False
        self.scheduler_thread = None
        self.dependency_thread = None
        
        self.task_handlers: Dict[str, Callable] = {}
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize task scheduler with Flask app"""
        self.app = app
        
        # Initialize Redis
        redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = redis.from_url(redis_url, decode_responses=False)
        
        # Load scheduled tasks from Redis
        self._load_scheduled_tasks()
        
        # Register default handlers
        self._register_default_handlers()
        
        # Start scheduler
        self.start_scheduler()
        
        self.logger.info("Task scheduler initialized")
    
    def _register_default_handlers(self):
        """Register default task handlers"""
        self.register_handler('data_cleanup', self._handle_data_cleanup)
        self.register_handler('report_generation', self._handle_report_generation)
        self.register_handler('system_maintenance', self._handle_system_maintenance)
        self.register_handler('backup_creation', self._handle_backup_creation)
    
    def register_handler(self, task_type: str, handler: Callable):
        """Register task handler"""
        self.task_handlers[task_type] = handler
        self.logger.info(f"Registered handler for task type: {task_type}")
    
    def start_scheduler(self):
        """Start task scheduler"""
        if self.scheduler_active:
            return
        
        self.scheduler_active = True
        
        # Start main scheduler thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        # Start dependency checker thread
        self.dependency_thread = threading.Thread(target=self._dependency_loop, daemon=True)
        self.dependency_thread.start()
        
        self.logger.info("Task scheduler started")
    
    def stop_scheduler(self):
        """Stop task scheduler"""
        self.scheduler_active = False
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        if self.dependency_thread:
            self.dependency_thread.join(timeout=5)
        
        self.logger.info("Task scheduler stopped")
    
    def schedule_task(self, task_type: str, payload: Dict[str, Any],
                     priority: TaskPriority = TaskPriority.NORMAL,
                     schedule_type: ScheduleType = ScheduleType.IMMEDIATE,
                     scheduled_time: datetime = None,
                     dependencies: List[str] = None,
                     dependency_type: TaskDependencyType = TaskDependencyType.SUCCESS,
                     retry_policy: Dict[str, Any] = None,
                     max_retries: int = 3,
                     timeout: int = 300,
                     metadata: Dict[str, Any] = None) -> str:
        """Schedule a task"""
        task_id = str(uuid.uuid4())
        
        # Set default scheduled time
        if schedule_type == ScheduleType.IMMEDIATE:
            scheduled_time = datetime.now()
        elif schedule_type == ScheduleType.DELAYED and scheduled_time is None:
            scheduled_time = datetime.now() + timedelta(minutes=5)
        elif scheduled_time is None:
            scheduled_time = datetime.now()
        
        # Set default retry policy
        if retry_policy is None:
            retry_policy = {
                'type': 'exponential',
                'base_delay': SchedulerConfig.DEFAULT_RETRY_DELAY,
                'max_delay': SchedulerConfig.MAX_RETRY_DELAY,
                'multiplier': SchedulerConfig.RETRY_BACKOFF_MULTIPLIER
            }
        
        # Create scheduled task
        scheduled_task = ScheduledTask(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
            schedule_type=schedule_type,
            scheduled_time=scheduled_time,
            created_at=datetime.now(),
            dependencies=dependencies or [],
            dependency_type=dependency_type,
            retry_policy=retry_policy,
            max_retries=max_retries,
            timeout=timeout,
            metadata=metadata or {}
        )
        
        # Check dependencies
        if dependencies:
            if self.dependency_manager.check_circular_dependency(task_id, dependencies):
                raise ValueError(f"Circular dependency detected for task {task_id}")
            
            for dep in dependencies:
                self.dependency_manager.add_dependency(task_id, dep, dependency_type)
        
        # Store task
        self.scheduled_tasks[task_id] = scheduled_task
        
        # Add to queue if ready
        if self.dependency_manager.can_execute(task_id, dependency_type):
            self.task_queue.enqueue(scheduled_task)
        
        # Store in Redis
        self._store_scheduled_task(scheduled_task)
        
        self.logger.info(f"Task {task_id} scheduled for {scheduled_time}")
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task"""
        if task_id in self.scheduled_tasks:
            del self.scheduled_tasks[task_id]
            
            # Remove from Redis
            task_key = f"scheduled_task:{task_id}"
            self.redis_client.delete(task_key)
            
            self.logger.info(f"Task {task_id} cancelled")
            return True
        
        return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        if task_id in self.scheduled_tasks:
            return self.scheduled_tasks[task_id].to_dict()
        
        # Check execution history
        for result in self.execution_history:
            if result.task_id == task_id:
                return result.to_dict()
        
        return None
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.scheduler_active:
            try:
                # Get next task
                task = self.task_queue.dequeue()
                
                if task:
                    # Check dependencies again
                    if self.dependency_manager.can_execute(task.task_id, task.dependency_type):
                        # Execute task
                        threading.Thread(target=self._execute_task, args=(task,), daemon=True).start()
                    else:
                        # Put task back in queue
                        self.task_queue.enqueue(task)
                else:
                    # No tasks ready, sleep briefly
                    time.sleep(SchedulerConfig.SCHEDULE_CHECK_INTERVAL)
                    
            except Exception as e:
                self.logger.error(f"Scheduler loop error: {str(e)}")
                time.sleep(SchedulerConfig.SCHEDULE_CHECK_INTERVAL)
    
    def _dependency_loop(self):
        """Dependency checking loop"""
        while self.scheduler_active:
            try:
                # Check for tasks that can now be executed
                for task_id, task in self.scheduled_tasks.items():
                    if (task_id not in [t.task_id for t in self.task_queue.queue] and
                        self.dependency_manager.can_execute(task_id, task.dependency_type)):
                        self.task_queue.enqueue(task)
                
                # Sleep until next check
                time.sleep(SchedulerConfig.DEPENDENCY_CHECK_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Dependency loop error: {str(e)}")
                time.sleep(SchedulerConfig.DEPENDENCY_CHECK_INTERVAL)
    
    def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task"""
        start_time = time.time()
        
        try:
            # Get handler
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"No handler for task type: {task.task_type}")
            
            # Execute handler
            result = handler(task.payload)
            
            # Record success
            execution_result = ScheduleResult(
                schedule_id=str(uuid.uuid4()),
                task_id=task.task_id,
                executed_at=datetime.now(),
                success=True,
                result=result,
                error=None,
                execution_time=time.time() - start_time,
                next_run=self._calculate_next_run(task) if task.schedule_type == ScheduleType.RECURRING else None
            )
            
            self.execution_history.append(execution_result)
            self.dependency_manager.mark_completed(task.task_id)
            
            # Schedule next run if recurring
            if execution_result.next_run:
                next_task = ScheduledTask(
                    task_id=str(uuid.uuid4()),
                    task_type=task.task_type,
                    payload=task.payload,
                    priority=task.priority,
                    schedule_type=task.schedule_type,
                    scheduled_time=execution_result.next_run,
                    created_at=datetime.now(),
                    dependencies=task.dependencies,
                    dependency_type=task.dependency_type,
                    retry_policy=task.retry_policy,
                    max_retries=task.max_retries,
                    timeout=task.timeout,
                    metadata=task.metadata
                )
                
                self.scheduled_tasks[next_task.task_id] = next_task
                self.task_queue.enqueue(next_task)
            
            self.logger.info(f"Task {task.task_id} executed successfully")
            
        except Exception as e:
            # Handle task failure
            error_msg = str(e)
            
            # Check if should retry
            if self.retry_policy.should_retry(0, task.max_retries, error_msg):
                # Calculate retry delay
                retry_delay = self.retry_policy.calculate_retry_delay(0, task.retry_policy)
                retry_time = datetime.now() + timedelta(seconds=retry_delay)
                
                # Schedule retry
                retry_task = ScheduledTask(
                    task_id=str(uuid.uuid4()),
                    task_type=task.task_type,
                    payload=task.payload,
                    priority=task.priority,
                    schedule_type=ScheduleType.DELAYED,
                    scheduled_time=retry_time,
                    created_at=datetime.now(),
                    dependencies=task.dependencies,
                    dependency_type=task.dependency_type,
                    retry_policy=task.retry_policy,
                    max_retries=task.max_retries - 1,
                    timeout=task.timeout,
                    metadata=task.metadata
                )
                
                self.scheduled_tasks[retry_task.task_id] = retry_task
                self.task_queue.enqueue(retry_task)
                
                self.logger.warning(f"Task {task.task_id} failed, retry scheduled in {retry_delay}s: {error_msg}")
            else:
                # Mark as failed
                execution_result = ScheduleResult(
                    schedule_id=str(uuid.uuid4()),
                    task_id=task.task_id,
                    executed_at=datetime.now(),
                    success=False,
                    result=None,
                    error=error_msg,
                    execution_time=time.time() - start_time,
                    next_run=None
                )
                
                self.execution_history.append(execution_result)
                self.dependency_manager.mark_failed(task.task_id)
                
                self.logger.error(f"Task {task.task_id} failed permanently: {error_msg}")
        
        finally:
            # Clean up completed task
            if task.task_id in self.scheduled_tasks:
                del self.scheduled_tasks[task.task_id]
    
    def _calculate_next_run(self, task: ScheduledTask) -> Optional[datetime]:
        """Calculate next run time for recurring tasks"""
        if task.schedule_type != ScheduleType.RECURRING:
            return None
        
        # Get recurrence pattern from metadata
        pattern = task.metadata.get('recurrence_pattern')
        if not pattern:
            return None
        
        if pattern['type'] == 'interval':
            # Simple interval
            interval_seconds = pattern.get('interval_seconds', 3600)  # Default 1 hour
            return task.scheduled_time + timedelta(seconds=interval_seconds)
        
        elif pattern['type'] == 'daily':
            # Daily at specific time
            hour = pattern.get('hour', 0)
            minute = pattern.get('minute', 0)
            
            next_run = task.scheduled_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= task.scheduled_time:
                next_run += timedelta(days=1)
            
            return next_run
        
        elif pattern['type'] == 'weekly':
            # Weekly on specific day
            day_of_week = pattern.get('day_of_week', 0)  # Monday = 0
            hour = pattern.get('hour', 0)
            minute = pattern.get('minute', 0)
            
            days_ahead = day_of_week - task.scheduled_time.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            
            next_run = task.scheduled_time + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            return next_run
        
        return None
    
    def _store_scheduled_task(self, task: ScheduledTask):
        """Store scheduled task in Redis"""
        try:
            task_key = f"scheduled_task:{task.task_id}"
            task_data = json.dumps(task.to_dict())
            
            # Store with expiration
            expiration = 86400  # 24 hours
            self.redis_client.setex(task_key, expiration, task_data)
            
        except Exception as e:
            self.logger.error(f"Failed to store scheduled task {task.task_id}: {str(e)}")
    
    def _load_scheduled_tasks(self):
        """Load scheduled tasks from Redis"""
        try:
            task_keys = self.redis_client.keys("scheduled_task:*")
            
            for task_key in task_keys:
                task_data = self.redis_client.get(task_key)
                if task_data:
                    task_dict = json.loads(task_data)
                    task = self._dict_to_scheduled_task(task_dict)
                    
                    # Only load tasks that haven't expired
                    if task.scheduled_time > datetime.now():
                        self.scheduled_tasks[task.task_id] = task
                        
                        # Add to queue if ready
                        if self.dependency_manager.can_execute(task.task_id, task.dependency_type):
                            self.task_queue.enqueue(task)
            
            self.logger.info(f"Loaded {len(self.scheduled_tasks)} scheduled tasks from Redis")
            
        except Exception as e:
            self.logger.error(f"Failed to load scheduled tasks: {str(e)}")
    
    def _dict_to_scheduled_task(self, task_dict: Dict[str, Any]) -> ScheduledTask:
        """Convert dictionary to ScheduledTask"""
        return ScheduledTask(
            task_id=task_dict['task_id'],
            task_type=task_dict['task_type'],
            payload=task_dict['payload'],
            priority=TaskPriority(task_dict['priority']),
            schedule_type=ScheduleType(task_dict['schedule_type']),
            scheduled_time=datetime.fromisoformat(task_dict['scheduled_time']),
            created_at=datetime.fromisoformat(task_dict['created_at']),
            dependencies=task_dict.get('dependencies', []),
            dependency_type=TaskDependencyType(task_dict.get('dependency_type', 'success')),
            retry_policy=task_dict.get('retry_policy', {}),
            max_retries=task_dict.get('max_retries', 3),
            timeout=task_dict.get('timeout', 300),
            metadata=task_dict.get('metadata', {})
        )
    
    # Default task handlers
    def _handle_data_cleanup(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data cleanup task"""
        # Simulate cleanup
        time.sleep(2)
        
        return {
            'status': 'completed',
            'files_deleted': payload.get('max_files', 100),
            'space_freed': '1.2GB'
        }
    
    def _handle_report_generation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle report generation task"""
        # Simulate report generation
        time.sleep(5)
        
        return {
            'status': 'completed',
            'report_type': payload.get('report_type', 'daily'),
            'report_path': f"/reports/{payload.get('report_type', 'daily')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        }
    
    def _handle_system_maintenance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system maintenance task"""
        # Simulate maintenance
        time.sleep(10)
        
        return {
            'status': 'completed',
            'maintenance_type': payload.get('maintenance_type', 'routine'),
            'actions_performed': ['cache_clear', 'log_rotation', 'health_check']
        }
    
    def _handle_backup_creation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle backup creation task"""
        # Simulate backup
        time.sleep(15)
        
        return {
            'status': 'completed',
            'backup_type': payload.get('backup_type', 'full'),
            'backup_path': f"/backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz",
            'size': '2.5GB'
        }
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            'scheduler_active': self.scheduler_active,
            'queue_size': self.task_queue.size(),
            'scheduled_tasks': len(self.scheduled_tasks),
            'execution_history_size': len(self.execution_history),
            'registered_handlers': list(self.task_handlers.keys()),
            'dependency_graph_size': len(self.dependency_manager.dependency_graph)
        }


# Initialize global task scheduler
task_scheduler = TaskScheduler()
