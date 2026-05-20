# backend/services/performance/async_queue.py
import asyncio
from typing import Dict, Any, Optional
from enum import Enum
import heapq
import time
import logging

logger = logging.getLogger(__name__)

class Priority(Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0

class PrioritizedTask:
    """Task with priority for queue"""

    def __init__(self, priority: Priority, task_id: str, data: Any, created_at: float = None):
        self.priority = priority.value
        self.task_id = task_id
        self.data = data
        self.created_at = created_at or time.time()

    def __lt__(self, other):
        # Higher priority (lower number) first, then older tasks
        if self.priority == other.priority:
            return self.created_at < other.created_at
        return self.priority < other.priority

class AsyncPriorityQueue:
    """Async queue with priority support and rate limiting"""

    def __init__(self, max_concurrent: int = 5, rate_limit_per_minute: int = 60):
        self.queue = []
        self.processing = set()
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit_per_minute
        self.request_timestamps = []
        self.lock = asyncio.Lock()

    async def add_task(self, task: PrioritizedTask):
        """Add task to priority queue"""
        async with self.lock:
            heapq.heappush(self.queue, task)
            logger.info(f"Added task {task.task_id} with priority {task.priority}")

    async def process_queue(self, handler_func):
        """Process tasks from queue with rate limiting"""
        while True:
            if len(self.processing) >= self.max_concurrent:
                await asyncio.sleep(0.1)
                continue

            # Rate limiting
            if not self._check_rate_limit():
                await asyncio.sleep(1)
                continue

            async with self.lock:
                if not self.queue:
                    await asyncio.sleep(0.1)
                    continue

                task = heapq.heappop(self.queue)
                self.processing.add(task.task_id)

            # Process task
            asyncio.create_task(self._process_task(task, handler_func))

    async def _process_task(self, task: PrioritizedTask, handler_func):
        """Process individual task"""
        try:
            start_time = time.time()
            result = await handler_func(task.data)
            processing_time = time.time() - start_time

            logger.info(f"Task {task.task_id} completed in {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
        finally:
            self.processing.remove(task.task_id)

    def _check_rate_limit(self) -> bool:
        """Check if within rate limit"""
        now = time.time()
        minute_ago = now - 60

        self.request_timestamps = [ts for ts in self.request_timestamps if ts > minute_ago]

        if len(self.request_timestamps) >= self.rate_limit:
            return False

        self.request_timestamps.append(now)
        return True