"""
Async Task Queue
================

Background task processing with priority queues and worker pools.
"""

from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import uuid
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class TaskPriority(int, Enum):
    """Task priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class Task:
    """A queued task."""
    task_id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    timeout_seconds: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """Compare tasks by priority (for priority queue)."""
        return self.priority.value > other.priority.value  # Higher priority first


class AsyncTaskQueue:
    """
    Async task queue with priority and concurrency control.

    Features:
    - Priority-based execution
    - Configurable worker pool
    - Task timeout
    - Result storage
    - Status tracking
    """

    def __init__(
        self,
        max_workers: int = 5,
        max_queue_size: int = 1000,
        default_timeout: int = 300
    ):
        """
        Initialize task queue.

        Args:
            max_workers: Maximum concurrent workers
            max_queue_size: Maximum queue size
            default_timeout: Default task timeout in seconds
        """
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.default_timeout = default_timeout

        # Priority queue (using asyncio.PriorityQueue)
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue(
            maxsize=max_queue_size
        )

        # Task storage
        self.tasks: Dict[str, Task] = {}

        # Worker tasks
        self.workers: List[asyncio.Task] = []

        # Statistics
        self.stats = {
            "total_queued": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_cancelled": 0,
            "total_timeout": 0,
        }

        # Running flag
        self.running = False

        logger.info(
            f"AsyncTaskQueue initialized "
            f"(workers={max_workers}, queue_size={max_queue_size})"
        )

    async def submit(
        self,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Submit a task to the queue.

        Args:
            func: Async function to execute
            *args: Positional arguments
            priority: Task priority
            timeout: Task timeout in seconds
            metadata: Optional metadata
            **kwargs: Keyword arguments

        Returns:
            Task ID
        """
        # Generate task ID
        task_id = str(uuid.uuid4())

        # Create task
        task = Task(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout_seconds=timeout or self.default_timeout,
            metadata=metadata or {}
        )

        # Store task
        self.tasks[task_id] = task

        # Add to queue
        await self.queue.put(task)

        self.stats["total_queued"] += 1

        logger.info(
            f"Task {task_id[:8]} queued "
            f"(priority={priority.name}, queue_size={self.queue.qsize()})"
        )

        return task_id

    async def start(self):
        """Start worker pool."""
        if self.running:
            logger.warning("Queue already running")
            return

        self.running = True

        # Start workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)

        logger.info(f"Started {self.max_workers} workers")

    async def stop(self, timeout: int = 30):
        """
        Stop worker pool.

        Args:
            timeout: Timeout for graceful shutdown
        """
        if not self.running:
            return

        logger.info("Stopping queue...")

        self.running = False

        # Wait for workers to finish
        try:
            await asyncio.wait_for(
                asyncio.gather(*self.workers, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Shutdown timeout after {timeout}s")

        self.workers.clear()
        logger.info("Queue stopped")

    async def _worker(self, worker_id: int):
        """
        Worker coroutine.

        Args:
            worker_id: Worker identifier
        """
        logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                # Get task from queue (with timeout)
                task = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                # No task available, continue
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} queue error: {e}")
                continue

            # Execute task
            await self._execute_task(task, worker_id)

            # Mark task done
            self.queue.task_done()

        logger.info(f"Worker {worker_id} stopped")

    async def _execute_task(self, task: Task, worker_id: int):
        """
        Execute a single task.

        Args:
            task: Task to execute
            worker_id: Worker identifier
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()

        logger.info(
            f"Worker {worker_id} executing task {task.task_id[:8]} "
            f"(priority={task.priority.name})"
        )

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                task.func(*task.args, **task.kwargs),
                timeout=task.timeout_seconds
            )

            # Task succeeded
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.utcnow()

            self.stats["total_completed"] += 1

            duration_ms = (
                (task.completed_at - task.started_at).total_seconds() * 1000
            )

            logger.info(
                f"Task {task.task_id[:8]} completed in {duration_ms:.1f}ms"
            )

        except asyncio.TimeoutError:
            # Task timed out
            task.status = TaskStatus.TIMEOUT
            task.error = f"Timeout after {task.timeout_seconds}s"
            task.completed_at = datetime.utcnow()

            self.stats["total_timeout"] += 1

            logger.warning(
                f"Task {task.task_id[:8]} timeout after {task.timeout_seconds}s"
            )

        except asyncio.CancelledError:
            # Task cancelled
            task.status = TaskStatus.CANCELLED
            task.error = "Task cancelled"
            task.completed_at = datetime.utcnow()

            self.stats["total_cancelled"] += 1

            logger.info(f"Task {task.task_id[:8]} cancelled")

        except Exception as e:
            # Task failed
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()

            self.stats["total_failed"] += 1

            logger.error(
                f"Task {task.task_id[:8]} failed: {e}",
                exc_info=True
            )

    async def get_result(
        self,
        task_id: str,
        timeout: Optional[int] = None
    ) -> Any:
        """
        Get task result (blocks until complete).

        Args:
            task_id: Task identifier
            timeout: Wait timeout in seconds

        Returns:
            Task result

        Raises:
            ValueError: If task not found
            TimeoutError: If timeout exceeded
            RuntimeError: If task failed
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task not found: {task_id}")

        task = self.tasks[task_id]

        # Wait for completion
        start = datetime.utcnow()
        while task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            await asyncio.sleep(0.1)

            if timeout:
                elapsed = (datetime.utcnow() - start).total_seconds()
                if elapsed > timeout:
                    raise TimeoutError(f"Result wait timeout: {task_id}")

        # Check status
        if task.status == TaskStatus.COMPLETED:
            return task.result
        elif task.status == TaskStatus.FAILED:
            raise RuntimeError(f"Task failed: {task.error}")
        elif task.status == TaskStatus.TIMEOUT:
            raise TimeoutError(f"Task timeout: {task.error}")
        elif task.status == TaskStatus.CANCELLED:
            raise RuntimeError(f"Task cancelled: {task.error}")

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status.

        Args:
            task_id: Task identifier

        Returns:
            Task status dict or None if not found
        """
        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]

        status = {
            "task_id": task.task_id,
            "status": task.status.value,
            "priority": task.priority.name,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "metadata": task.metadata,
        }

        if task.status == TaskStatus.COMPLETED:
            status["result"] = task.result
        elif task.status in [TaskStatus.FAILED, TaskStatus.TIMEOUT, TaskStatus.CANCELLED]:
            status["error"] = task.error

        return status

    async def cancel(self, task_id: str) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task identifier

        Returns:
            True if cancelled, False if already completed
        """
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]

        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT]:
            return False

        task.status = TaskStatus.CANCELLED
        task.error = "Cancelled by user"
        task.completed_at = datetime.utcnow()

        self.stats["total_cancelled"] += 1

        logger.info(f"Task {task_id[:8]} cancelled")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "queue_size": self.queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "workers": len(self.workers),
            "max_workers": self.max_workers,
            "running": self.running,
            **self.stats
        }

    def clear_completed(self, older_than_minutes: int = 60):
        """
        Clear completed tasks older than specified time.

        Args:
            older_than_minutes: Clear tasks older than this many minutes
        """
        cutoff = datetime.utcnow() - timedelta(minutes=older_than_minutes)

        task_ids_to_remove = [
            task_id for task_id, task in self.tasks.items()
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT, TaskStatus.CANCELLED]
            and task.completed_at and task.completed_at < cutoff
        ]

        for task_id in task_ids_to_remove:
            del self.tasks[task_id]

        if task_ids_to_remove:
            logger.info(f"Cleared {len(task_ids_to_remove)} old tasks")


class BatchProcessor:
    """
    Batch processor for efficiently processing multiple similar tasks.

    Groups tasks into batches for efficient processing.
    """

    def __init__(
        self,
        queue: AsyncTaskQueue,
        batch_size: int = 10,
        max_wait_seconds: float = 1.0
    ):
        """
        Initialize batch processor.

        Args:
            queue: Task queue to use
            batch_size: Maximum batch size
            max_wait_seconds: Maximum wait time to accumulate batch
        """
        self.queue = queue
        self.batch_size = batch_size
        self.max_wait_seconds = max_wait_seconds

        # Pending items by batch key
        self.batches: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        logger.info(
            f"BatchProcessor initialized "
            f"(batch_size={batch_size}, max_wait={max_wait_seconds}s)"
        )

    async def submit_batch_item(
        self,
        batch_key: str,
        item: Any,
        process_func: Callable
    ) -> str:
        """
        Submit an item to be batched.

        Args:
            batch_key: Key to group batches
            item: Item to process
            process_func: Function to process batch

        Returns:
            Task ID
        """
        # Add to batch
        self.batches[batch_key].append(item)

        # Check if batch is full
        if len(self.batches[batch_key]) >= self.batch_size:
            return await self._process_batch(batch_key, process_func)

        # Set timer to process batch
        asyncio.create_task(
            self._delayed_batch_process(batch_key, process_func)
        )

        return None  # Will be processed in batch

    async def _delayed_batch_process(
        self,
        batch_key: str,
        process_func: Callable
    ):
        """Process batch after delay."""
        await asyncio.sleep(self.max_wait_seconds)

        if batch_key in self.batches and self.batches[batch_key]:
            await self._process_batch(batch_key, process_func)

    async def _process_batch(
        self,
        batch_key: str,
        process_func: Callable
    ) -> str:
        """Process a batch."""
        if batch_key not in self.batches or not self.batches[batch_key]:
            return None

        # Get batch items
        items = self.batches[batch_key]
        self.batches[batch_key] = []

        # Submit batch task
        task_id = await self.queue.submit(
            process_func,
            items,
            priority=TaskPriority.NORMAL,
            metadata={"batch_key": batch_key, "batch_size": len(items)}
        )

        logger.info(
            f"Processing batch {batch_key} with {len(items)} items "
            f"(task_id={task_id[:8]})"
        )

        return task_id


# Fix missing import
from datetime import timedelta

# Global task queue
task_queue = AsyncTaskQueue(
    max_workers=5,
    max_queue_size=1000,
    default_timeout=300
)
