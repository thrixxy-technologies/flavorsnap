"""
Advanced Queue Persistence System for FlavorSnap
Handles durable storage of queue state, tasks, and recovery mechanisms
"""

import json
import pickle
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Task status for persistence"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class PersistentTask:
    """Task representation for persistence"""
    id: str
    priority: int
    status: TaskStatus
    payload: Any
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    worker_id: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert datetime objects to strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, Enum):
                data[key] = value.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersistentTask':
        """Create from dictionary"""
        # Convert string datetime back to datetime objects
        for key in ['created_at', 'started_at', 'completed_at']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        
        # Convert status string back to enum
        if isinstance(data.get('status'), str):
            data['status'] = TaskStatus(data['status'])
        
        return cls(**data)

class PersistenceBackend(ABC):
    """Abstract base class for persistence backends"""
    
    @abstractmethod
    def save_task(self, task: PersistentTask) -> bool:
        """Save task to persistent storage"""
        pass
    
    @abstractmethod
    def get_task(self, task_id: str) -> Optional[PersistentTask]:
        """Get task from persistent storage"""
        pass
    
    @abstractmethod
    def update_task(self, task: PersistentTask) -> bool:
        """Update task in persistent storage"""
        pass
    
    @abstractmethod
    def delete_task(self, task_id: str) -> bool:
        """Delete task from persistent storage"""
        pass
    
    @abstractmethod
    def get_tasks_by_status(self, status: TaskStatus, limit: int = 100) -> List[PersistentTask]:
        """Get tasks by status"""
        pass
    
    @abstractmethod
    def get_all_tasks(self, limit: int = 1000) -> List[PersistentTask]:
        """Get all tasks"""
        pass
    
    @abstractmethod
    def cleanup_old_tasks(self, days: int = 7) -> int:
        """Clean up old completed/failed tasks"""
        pass

class SQLitePersistence(PersistenceBackend):
    """SQLite-based persistence backend"""
    
    def __init__(self, db_path: str = "queue_persistence.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Create tasks table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        priority INTEGER,
                        status TEXT,
                        payload TEXT,
                        created_at TEXT,
                        started_at TEXT,
                        completed_at TEXT,
                        retry_count INTEGER,
                        max_retries INTEGER,
                        timeout_seconds INTEGER,
                        worker_id TEXT,
                        error_message TEXT,
                        metadata TEXT
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON tasks(created_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority ON tasks(priority)")
                
                conn.commit()
                logger.info(f"SQLite persistence initialized: {self.db_path}")
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to initialize SQLite database: {e}")
                raise
            finally:
                conn.close()
    
    def save_task(self, task: PersistentTask) -> bool:
        """Save task to SQLite database"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                data = task.to_dict()
                # Convert complex objects to JSON strings
                data['payload'] = json.dumps(data['payload'])
                data['metadata'] = json.dumps(data.get('metadata', {}))
                
                columns = list(data.keys())
                placeholders = ', '.join(['?' for _ in columns])
                values = list(data.values())
                
                cursor.execute(f"""
                    INSERT OR REPLACE INTO tasks ({', '.join(columns)})
                    VALUES ({placeholders})
                """, values)
                
                conn.commit()
                return True
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to save task {task.id}: {e}")
                return False
            finally:
                conn.close()
    
    def get_task(self, task_id: str) -> Optional[PersistentTask]:
        """Get task from SQLite database"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
                
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    data = dict(zip(columns, row))
                    
                    # Parse JSON fields
                    data['payload'] = json.loads(data['payload'])
                    data['metadata'] = json.loads(data['metadata'])
                    
                    return PersistentTask.from_dict(data)
                return None
                
            except Exception as e:
                logger.error(f"Failed to get task {task_id}: {e}")
                return None
            finally:
                conn.close()
    
    def update_task(self, task: PersistentTask) -> bool:
        """Update task in SQLite database"""
        return self.save_task(task)  # SQLite uses INSERT OR REPLACE
    
    def delete_task(self, task_id: str) -> bool:
        """Delete task from SQLite database"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                conn.commit()
                return cursor.rowcount > 0
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to delete task {task_id}: {e}")
                return False
            finally:
                conn.close()
    
    def get_tasks_by_status(self, status: TaskStatus, limit: int = 100) -> List[PersistentTask]:
        """Get tasks by status"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY created_at LIMIT ?",
                    (status.value, limit)
                )
                
                tasks = []
                for row in cursor.fetchall():
                    columns = [desc[0] for desc in cursor.description]
                    data = dict(zip(columns, row))
                    
                    # Parse JSON fields
                    data['payload'] = json.loads(data['payload'])
                    data['metadata'] = json.loads(data['metadata'])
                    
                    tasks.append(PersistentTask.from_dict(data))
                
                return tasks
                
            except Exception as e:
                logger.error(f"Failed to get tasks by status {status}: {e}")
                return []
            finally:
                conn.close()
    
    def get_all_tasks(self, limit: int = 1000) -> List[PersistentTask]:
        """Get all tasks"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tasks ORDER BY created_at LIMIT ?", (limit,))
                
                tasks = []
                for row in cursor.fetchall():
                    columns = [desc[0] for desc in cursor.description]
                    data = dict(zip(columns, row))
                    
                    # Parse JSON fields
                    data['payload'] = json.loads(data['payload'])
                    data['metadata'] = json.loads(data['metadata'])
                    
                    tasks.append(PersistentTask.from_dict(data))
                
                return tasks
                
            except Exception as e:
                logger.error(f"Failed to get all tasks: {e}")
                return []
            finally:
                conn.close()
    
    def cleanup_old_tasks(self, days: int = 7) -> int:
        """Clean up old completed/failed tasks"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                cursor.execute(
                    "DELETE FROM tasks WHERE status IN ('completed', 'failed') AND completed_at < ?",
                    (cutoff_date,)
                )
                
                conn.commit()
                deleted_count = cursor.rowcount
                logger.info(f"Cleaned up {deleted_count} old tasks")
                return deleted_count
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to cleanup old tasks: {e}")
                return 0
            finally:
                conn.close()

class FilePersistence(PersistenceBackend):
    """File-based persistence backend"""
    
    def __init__(self, storage_dir: str = "queue_storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self._lock = threading.RLock()
        logger.info(f"File persistence initialized: {self.storage_dir}")
    
    def _get_task_file(self, task_id: str) -> Path:
        """Get file path for task"""
        return self.storage_dir / f"{task_id}.json"
    
    def save_task(self, task: PersistentTask) -> bool:
        """Save task to file"""
        with self._lock:
            try:
                task_file = self._get_task_file(task.id)
                with open(task_file, 'w') as f:
                    json.dump(task.to_dict(), f, indent=2)
                return True
            except Exception as e:
                logger.error(f"Failed to save task {task.id}: {e}")
                return False
    
    def get_task(self, task_id: str) -> Optional[PersistentTask]:
        """Get task from file"""
        with self._lock:
            try:
                task_file = self._get_task_file(task_id)
                if not task_file.exists():
                    return None
                
                with open(task_file, 'r') as f:
                    data = json.load(f)
                return PersistentTask.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to get task {task_id}: {e}")
                return None
    
    def update_task(self, task: PersistentTask) -> bool:
        """Update task file"""
        return self.save_task(task)
    
    def delete_task(self, task_id: str) -> bool:
        """Delete task file"""
        with self._lock:
            try:
                task_file = self._get_task_file(task_id)
                if task_file.exists():
                    task_file.unlink()
                    return True
                return False
            except Exception as e:
                logger.error(f"Failed to delete task {task_id}: {e}")
                return False
    
    def get_tasks_by_status(self, status: TaskStatus, limit: int = 100) -> List[PersistentTask]:
        """Get tasks by status"""
        with self._lock:
            tasks = []
            try:
                for task_file in self.storage_dir.glob("*.json"):
                    if len(tasks) >= limit:
                        break
                    
                    try:
                        with open(task_file, 'r') as f:
                            data = json.load(f)
                        
                        if data.get('status') == status.value:
                            tasks.append(PersistentTask.from_dict(data))
                    except Exception:
                        continue  # Skip corrupted files
                
                # Sort by creation time
                tasks.sort(key=lambda t: t.created_at)
                return tasks
                
            except Exception as e:
                logger.error(f"Failed to get tasks by status {status}: {e}")
                return []
    
    def get_all_tasks(self, limit: int = 1000) -> List[PersistentTask]:
        """Get all tasks"""
        with self._lock:
            tasks = []
            try:
                for task_file in self.storage_dir.glob("*.json"):
                    if len(tasks) >= limit:
                        break
                    
                    try:
                        with open(task_file, 'r') as f:
                            data = json.load(f)
                        tasks.append(PersistentTask.from_dict(data))
                    except Exception:
                        continue  # Skip corrupted files
                
                # Sort by creation time
                tasks.sort(key=lambda t: t.created_at)
                return tasks
                
            except Exception as e:
                logger.error(f"Failed to get all tasks: {e}")
                return []
    
    def cleanup_old_tasks(self, days: int = 7) -> int:
        """Clean up old task files"""
        with self._lock:
            deleted_count = 0
            cutoff_date = datetime.now() - timedelta(days=days)
            
            try:
                for task_file in self.storage_dir.glob("*.json"):
                    try:
                        # Check file modification time
                        file_mtime = datetime.fromtimestamp(task_file.stat().st_mtime)
                        if file_mtime < cutoff_date:
                            # Check if task is completed or failed
                            with open(task_file, 'r') as f:
                                data = json.load(f)
                            
                            if data.get('status') in ['completed', 'failed']:
                                task_file.unlink()
                                deleted_count += 1
                    except Exception:
                        continue  # Skip problematic files
                
                logger.info(f"Cleaned up {deleted_count} old task files")
                return deleted_count
                
            except Exception as e:
                logger.error(f"Failed to cleanup old tasks: {e}")
                return 0

class QueuePersistence:
    """Queue persistence manager with recovery capabilities"""
    
    def __init__(self, backend: PersistenceBackend, recovery_enabled: bool = True):
        self.backend = backend
        self.recovery_enabled = recovery_enabled
        self._lock = threading.RLock()
        
        # Recovery statistics
        self.recovery_stats = {
            'last_recovery': None,
            'recovered_tasks': 0,
            'failed_recoveries': 0
        }
        
        # Auto-cleanup thread
        self._cleanup_active = False
        self._cleanup_thread = None
        
        if recovery_enabled:
            self._start_auto_cleanup()
    
    def save_task(self, task: PersistentTask) -> bool:
        """Save task to persistent storage"""
        return self.backend.save_task(task)
    
    def get_task(self, task_id: str) -> Optional[PersistentTask]:
        """Get task from persistent storage"""
        return self.backend.get_task(task_id)
    
    def update_task(self, task: PersistentTask) -> bool:
        """Update task in persistent storage"""
        return self.backend.update_task(task)
    
    def delete_task(self, task_id: str) -> bool:
        """Delete task from persistent storage"""
        return self.backend.delete_task(task_id)
    
    def get_pending_tasks(self, limit: int = 100) -> List[PersistentTask]:
        """Get pending tasks for recovery"""
        return self.backend.get_tasks_by_status(TaskStatus.PENDING, limit)
    
    def get_running_tasks(self, limit: int = 100) -> List[PersistentTask]:
        """Get running tasks (may need recovery)"""
        return self.backend.get_tasks_by_status(TaskStatus.RUNNING, limit)
    
    def recover_orphaned_tasks(self, timeout_minutes: int = 30) -> int:
        """Recover tasks that have been running too long"""
        if not self.recovery_enabled:
            return 0
        
        recovered_count = 0
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        
        with self._lock:
            running_tasks = self.get_running_tasks()
            
            for task in running_tasks:
                if task.started_at and task.started_at < cutoff_time:
                    # Task has been running too long, reset to pending
                    task.status = TaskStatus.PENDING
                    task.started_at = None
                    task.worker_id = None
                    task.error_message = "Recovery: task timeout"
                    
                    if self.update_task(task):
                        recovered_count += 1
                        logger.info(f"Recovered orphaned task: {task.id}")
                    else:
                        self.recovery_stats['failed_recoveries'] += 1
                        logger.error(f"Failed to recover task: {task.id}")
        
        self.recovery_stats['last_recovery'] = datetime.now()
        self.recovery_stats['recovered_tasks'] += recovered_count
        
        return recovered_count
    
    def backup_tasks(self, backup_path: str) -> bool:
        """Backup all tasks to file"""
        try:
            all_tasks = self.backend.get_all_tasks(limit=10000)  # Get all tasks
            
            backup_data = {
                'backup_time': datetime.now().isoformat(),
                'task_count': len(all_tasks),
                'tasks': [task.to_dict() for task in all_tasks]
            }
            
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info(f"Backed up {len(all_tasks)} tasks to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup tasks: {e}")
            return False
    
    def restore_tasks(self, backup_path: str) -> int:
        """Restore tasks from backup file"""
        try:
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            restored_count = 0
            for task_data in backup_data.get('tasks', []):
                task = PersistentTask.from_dict(task_data)
                if self.save_task(task):
                    restored_count += 1
                else:
                    logger.error(f"Failed to restore task: {task.id}")
            
            logger.info(f"Restored {restored_count} tasks from {backup_path}")
            return restored_count
            
        except Exception as e:
            logger.error(f"Failed to restore tasks: {e}")
            return 0
    
    def get_persistence_stats(self) -> Dict[str, Any]:
        """Get persistence statistics"""
        with self._lock:
            # Count tasks by status
            status_counts = {}
            for status in TaskStatus:
                tasks = self.backend.get_tasks_by_status(status, limit=10000)
                status_counts[status.value] = len(tasks)
            
            return {
                'status_counts': status_counts,
                'recovery_stats': self.recovery_stats.copy(),
                'backend_type': type(self.backend).__name__,
                'recovery_enabled': self.recovery_enabled
            }
    
    def _start_auto_cleanup(self):
        """Start automatic cleanup thread"""
        self._cleanup_active = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True
        )
        self._cleanup_thread.start()
        logger.info("Auto-cleanup started")
    
    def stop_auto_cleanup(self):
        """Stop automatic cleanup"""
        self._cleanup_active = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        logger.info("Auto-cleanup stopped")
    
    def _cleanup_loop(self):
        """Background cleanup loop"""
        while self._cleanup_active:
            try:
                # Recover orphaned tasks
                recovered = self.recover_orphaned_tasks()
                if recovered > 0:
                    logger.info(f"Recovered {recovered} orphaned tasks")
                
                # Cleanup old tasks
                deleted = self.backend.cleanup_old_tasks(days=7)
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} old tasks")
                
                # Sleep for 1 hour
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def shutdown(self):
        """Shutdown persistence manager"""
        logger.info("Shutting down queue persistence")
        self.stop_auto_cleanup()

# Factory function for creating persistence backends
def create_persistence_backend(backend_type: str, **kwargs) -> PersistenceBackend:
    """Create persistence backend based on type"""
    if backend_type.lower() == "sqlite":
        return SQLitePersistence(kwargs.get('db_path', 'queue_persistence.db'))
    elif backend_type.lower() == "file":
        return FilePersistence(kwargs.get('storage_dir', 'queue_storage'))
    else:
        raise ValueError(f"Unsupported persistence backend: {backend_type}")

# Utility functions for migration
def migrate_persistence(source_backend: PersistenceBackend, 
                      target_backend: PersistenceBackend) -> int:
    """Migrate tasks from one backend to another"""
    migrated_count = 0
    
    try:
        # Get all tasks from source
        tasks = source_backend.get_all_tasks(limit=10000)
        
        for task in tasks:
            if target_backend.save_task(task):
                migrated_count += 1
            else:
                logger.error(f"Failed to migrate task: {task.id}")
        
        logger.info(f"Migrated {migrated_count} tasks")
        return migrated_count
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 0
