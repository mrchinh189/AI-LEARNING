"""Bộ nhớ dài hạn: fact, bài học (lesson) và skill tích lũy sau mỗi goal."""
from __future__ import annotations


class MemoryStore:
    def add(self, kind: str, content: str, goal_id: int | None = None) -> None:
        """TODO: tạo embedding, ghi vào bảng memories (pgvector)."""
        raise NotImplementedError

    def search(self, query: str, k: int = 5) -> list[str]:
        """TODO: tìm theo cosine similarity; trả nội dung để chèn vào context agent."""
        raise NotImplementedError
