"""
Unit tests for the batch processor module
"""

import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from batch_processor import (
    MLBatchProcessor, BatchTask, TaskPriority, TaskStatus,
    TaskTimeoutError, QueueFullError, WorkerPoolExhaustedError
)

@pytest.mark.unit
class TestBatchTask:
    """Test cases for BatchTask class"""

    def test_batch_task_creation(self):
        """Test BatchTask creation with default values"""
        task = BatchTask()
        
        assert task.id is not None
        assert len(task.id) > 0
        assert task.priority == TaskPriority.NORMAL
        assert task.status == TaskStatus.PENDING
        assert task.payload is None
        assert task.created_at is not None
        assert task.started_at is None
        assert task.completed_at is None
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.timeout_seconds == 300
        assert task.worker_id is None
        assert task.error_message is None

    def test_batch_task_with_custom_values(self):
        """Test BatchTask creation with custom values"""
        payload = {"test": "data"}
        task = BatchTask(
            priority=TaskPriority.HIGH,
            payload=payload,
            max_retries=5,
            timeout_seconds=600
        )
        
        assert task.priority == TaskPriority.HIGH
        assert task.payload == payload
        assert task.max_retries == 5
        assert task.timeout_seconds == 600

    def test_task_status_transitions(self):
        """Test task status transitions"""
        task = BatchTask()
        
        # Initial status
        assert task.status == TaskStatus.PENDING
        
        # Start task
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None
        
        # Complete task
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None

@pytest.mark.unit
class TestMLBatchProcessor:
    """Test cases for MLBatchProcessor class"""

    @pytest.fixture
    def mock_model(self):
        """Create a mock model for testing"""
        model = MagicMock()
        model.predict.return_value = {"label": "test", "confidence": 0.95}
        return model

    @pytest.fixture
    def processor(self, mock_model):
        """Create a batch processor instance for testing"""
        return MLBatchProcessor(mock_model, max_workers=2, queue_size=10)

    def test_processor_initialization(self, processor):
        """Test processor initialization"""
        assert processor.model is not None
        assert processor.max_workers == 2
        assert processor.queue_size == 10
        assert processor.task_queue.empty()
        assert len(processor.active_tasks) == 0
        assert len(processor.completed_tasks) == 0

    def test_processor_initialization_without_model(self):
        """Test processor initialization without model"""
        processor = MLBatchProcessor(None, max_workers=2, queue_size=10)
        assert processor.model is None

    def test_submit_task_success(self, processor):
        """Test successful task submission"""
        payload = {"test": "data"}
        task_id = processor.submit_task(payload)
        
        assert task_id is not None
        assert len(task_id) > 0
        assert not processor.task_queue.empty()

    def test_submit_task_with_priority(self, processor):
        """Test task submission with priority"""
        high_priority_payload = {"priority": "high"}
        low_priority_payload = {"priority": "low"}
        
        # Submit low priority first
        low_task_id = processor.submit_task(low_priority_payload, TaskPriority.LOW)
        
        # Submit high priority - should be processed first
        high_task_id = processor.submit_task(high_priority_payload, TaskPriority.HIGH)
        
        # Check queue ordering (high priority should be at front)
        high_task = processor.task_queue.get()
        low_task = processor.task_queue.get()
        
        assert high_task.priority == TaskPriority.HIGH
        assert low_task.priority == TaskPriority.LOW

    def test_submit_task_queue_full(self, processor):
        """Test task submission when queue is full"""
        # Fill the queue
        for i in range(processor.queue_size):
            processor.submit_task({"data": i})
        
        # Next submission should raise QueueFullError
        with pytest.raises(QueueFullError):
            processor.submit_task({"overflow": "data"})

    def test_submit_task_with_metadata(self, processor):
        """Test task submission with metadata"""
        payload = {"test": "data"}
        metadata = {"source": "test", "user_id": "123"}
        
        task_id = processor.submit_task(payload, metadata=metadata)
        
        task_status = processor.get_task_status(task_id)
        assert task_status is not None
        assert task_status['metadata'] == metadata

    def test_get_task_status_existing(self, processor):
        """Test getting status of existing task"""
        payload = {"test": "data"}
        task_id = processor.submit_task(payload)
        
        status = processor.get_task_status(task_id)
        
        assert status is not None
        assert status['id'] == task_id
        assert status['status'] == TaskStatus.PENDING.value
        assert status['priority'] == TaskPriority.NORMAL.value
        assert 'created_at' in status

    def test_get_task_status_nonexistent(self, processor):
        """Test getting status of non-existent task"""
        status = processor.get_task_status("non-existent-id")
        assert status is None

    def test_cancel_task_pending(self, processor):
        """Test cancelling a pending task"""
        payload = {"test": "data"}
        task_id = processor.submit_task(payload)
        
        success = processor.cancel_task(task_id)
        assert success is True
        
        status = processor.get_task_status(task_id)
        assert status['status'] == TaskStatus.CANCELLED.value

    def test_cancel_task_running(self, processor):
        """Test cancelling a running task"""
        payload = {"test": "data"}
        task_id = processor.submit_task(payload)
        
        # Mock task as running
        task = None
        for queued_task in processor.task_queue.queue:
            if queued_task.id == task_id:
                task = queued_task
                break
        
        if task:
            task.status = TaskStatus.RUNNING
            task.worker_id = "worker-1"
            
            success = processor.cancel_task(task_id)
            assert success is False  # Cannot cancel running task

    def test_cancel_task_nonexistent(self, processor):
        """Test cancelling non-existent task"""
        success = processor.cancel_task("non-existent-id")
        assert success is False

    def test_get_queue_stats(self, processor):
        """Test getting queue statistics"""
        # Submit some tasks
        processor.submit_task({"data": 1}, TaskPriority.HIGH)
        processor.submit_task({"data": 2}, TaskPriority.NORMAL)
        processor.submit_task({"data": 3}, TaskPriority.LOW)
        
        stats = processor.get_queue_stats()
        
        assert stats['pending_tasks'] == 3
        assert stats['running_tasks'] == 0
        assert stats['completed_tasks'] == 0
        assert stats['failed_tasks'] == 0
        assert 'queue_size' in stats
        assert 'max_workers' in stats

    @patch('batch_processor.threading.Thread')
    def test_start_workers(self, mock_thread, processor):
        """Test starting worker threads"""
        processor.start_workers()
        
        # Verify threads were created
        assert mock_thread.call_count == processor.max_workers
        assert processor.workers_running is True

    def test_shutdown(self, processor):
        """Test processor shutdown"""
        # Start workers first
        processor.start_workers()
        
        # Submit a task to ensure workers are active
        processor.submit_task({"test": "data"})
        
        # Shutdown
        processor.shutdown()
        
        assert processor.workers_running is False
        assert processor.task_queue.empty()

    def test_process_task_success(self, processor, mock_model):
        """Test successful task processing"""
        task = BatchTask(
            payload={"image_data": b"test_image"},
            priority=TaskPriority.NORMAL
        )
        
        # Mock the image processing
        with patch('batch_processor.Image.open') as mock_image:
            mock_image.return_value = MagicMock()
            
            result = processor._process_task(task)
            
            assert result is not None
            assert task.status == TaskStatus.COMPLETED
            assert task.completed_at is not None
            assert task.error_message is None

    def test_process_task_model_error(self, processor, mock_model):
        """Test task processing with model error"""
        mock_model.predict.side_effect = Exception("Model error")
        
        task = BatchTask(
            payload={"image_data": b"test_image"},
            priority=TaskPriority.NORMAL
        )
        
        with patch('batch_processor.Image.open'):
            result = processor._process_task(task)
            
            assert result is None
            assert task.status == TaskStatus.FAILED
            assert task.error_message is not None

    def test_process_task_timeout(self, processor, mock_model):
        """Test task processing with timeout"""
        # Make model prediction take too long
        mock_model.predict.side_effect = lambda x: time.sleep(10)
        
        task = BatchTask(
            payload={"image_data": b"test_image"},
            priority=TaskPriority.NORMAL,
            timeout_seconds=1  # Very short timeout
        )
        
        with patch('batch_processor.Image.open'):
            with pytest.raises(TaskTimeoutError):
                processor._process_task(task)

    def test_retry_failed_task(self, processor):
        """Test retrying failed tasks"""
        payload = {"test": "data"}
        task_id = processor.submit_task(payload)
        
        # Simulate task failure
        task = None
        for queued_task in processor.task_queue.queue:
            if queued_task.id == task_id:
                task = queued_task
                break
        
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = "Test error"
            processor.dead_letter_queue.append(task)
            
            success = processor.retry_failed_task(task_id)
            assert success is True
            
            # Task should be back in the main queue
            assert len(processor.dead_letter_queue) == 0

    def test_retry_failed_task_not_found(self, processor):
        """Test retrying non-existent failed task"""
        success = processor.retry_failed_task("non-existent-id")
        assert success is False

    def test_cleanup_old_tasks(self, processor):
        """Test cleanup of old completed tasks"""
        # Add some old completed tasks
        old_time = datetime.now() - timedelta(hours=2)
        
        for i in range(5):
            task = BatchTask(
                payload={"data": i},
                priority=TaskPriority.NORMAL
            )
            task.status = TaskStatus.COMPLETED
            task.completed_at = old_time
            processor.completed_tasks.append(task)
        
        # Add recent task
        recent_task = BatchTask(
            payload={"recent": True},
            priority=TaskPriority.NORMAL
        )
        recent_task.status = TaskStatus.COMPLETED
        recent_task.completed_at = datetime.now()
        processor.completed_tasks.append(recent_task)
        
        # Cleanup (default retention is 1 hour)
        processor.cleanup_old_tasks()
        
        # Should only have the recent task
        assert len(processor.completed_tasks) == 1
        assert processor.completed_tasks[0].payload["recent"] is True

    def test_worker_thread_execution(self, processor, mock_model):
        """Test worker thread execution"""
        # Submit a task
        task_id = processor.submit_task({"test": "data"})
        
        # Start workers
        processor.start_workers()
        
        # Wait a bit for processing
        time.sleep(0.1)
        
        # Check task status
        status = processor.get_task_status(task_id)
        
        # Should be processed (or at least started)
        assert status is not None
        
        # Shutdown
        processor.shutdown()

    def test_priority_ordering(self, processor):
        """Test that tasks are processed in priority order"""
        # Submit tasks in mixed priority order
        tasks = [
            processor.submit_task({"data": 1}, TaskPriority.LOW),
            processor.submit_task({"data": 2}, TaskPriority.CRITICAL),
            processor.submit_task({"data": 3}, TaskPriority.NORMAL),
            processor.submit_task({"data": 4}, TaskPriority.HIGH),
        ]
        
        # Extract tasks from queue to check ordering
        queued_tasks = []
        while not processor.task_queue.empty():
            queued_tasks.append(processor.task_queue.get())
        
        # Should be ordered by priority (0 = highest priority)
        priorities = [task.priority for task in queued_tasks]
        expected_order = [TaskPriority.CRITICAL, TaskPriority.HIGH, 
                          TaskPriority.NORMAL, TaskPriority.LOW]
        
        assert priorities == expected_order

    def test_max_retries_exceeded(self, processor):
        """Test task that exceeds max retries"""
        payload = {"test": "data"}
        task_id = processor.submit_task(payload)
        
        # Find the task
        task = None
        for queued_task in processor.task_queue.queue:
            if queued_task.id == task_id:
                task = queued_task
                break
        
        if task:
            task.max_retries = 2
            task.retry_count = 2
            
            # Simulate another failure
            task.status = TaskStatus.FAILED
            task.error_message = "Final failure"
            
            # Should not be retried again
            success = processor.retry_failed_task(task_id)
            assert success is False

    @pytest.mark.parametrize("priority_value,expected_enum", [
        (0, TaskPriority.CRITICAL),
        (1, TaskPriority.HIGH),
        (2, TaskPriority.NORMAL),
        (3, TaskPriority.LOW),
    ])
    def test_task_priority_values(self, priority_value, expected_enum):
        """Test task priority enum values"""
        assert expected_enum.value == priority_value

    def test_task_status_values(self):
        """Test task status enum values"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.RETRYING.value == "retrying"
        assert TaskStatus.CANCELLED.value == "cancelled"
