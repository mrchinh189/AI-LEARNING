"""Hàng đợi task. Có thể thay bằng Temporal/Celery khi cần độ bền cao hơn."""
from __future__ import annotations

from collections import deque


class MemoryQueue:
    def __init__(self) -> None:
        self._q: deque[int] = deque()

    def push(self, task_id: int) -> None:
        self._q.append(task_id)

    def pop(self, timeout: int = 5) -> int | None:
        return self._q.popleft() if self._q else None


class RedisQueue:  # pragma: no cover
    KEY = "agentteam:tasks"

    def __init__(self, url: str) -> None:
        import redis
        self.r = redis.Redis.from_url(url)

    def push(self, task_id: int) -> None:
        self.r.rpush(self.KEY, task_id)

    def pop(self, timeout: int = 5) -> int | None:
        item = self.r.blpop([self.KEY], timeout=timeout)
        return int(item[1]) if item else None
