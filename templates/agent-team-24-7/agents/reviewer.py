"""Reviewer tách riêng khỏi worker."""
from __future__ import annotations

from dataclasses import dataclass

from board.models import Task


@dataclass
class Review:
    passed: bool
    feedback: str = ""


class Reviewer:
    def review(self, task: Task) -> Review:
        """TODO: gọi LLM với prompts/reviewer.md; có thể bổ sung kiểm tra tự động (test, lint, link check)."""
        raise NotImplementedError
