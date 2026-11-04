"""Planner: goal -> task drafts; heartbeat: bổ sung task còn thiếu."""
from __future__ import annotations

from board.models import Goal, Task, TaskDraft


class Planner:
    def __init__(self, roles: list[str]) -> None:
        self.roles = roles

    def plan(self, goal: Goal) -> list[TaskDraft]:
        """TODO: gọi model mạnh với agents/prompts/planner.md, parse JSON -> TaskDraft, validate role."""
        raise NotImplementedError

    def replan(self, goal: Goal, tasks: list[Task]) -> list[TaskDraft]:
        """TODO: chế độ heartbeat. Trả [] nếu không cần thêm việc."""
        return []

    def validate(self, drafts: list[TaskDraft]) -> list[TaskDraft]:
        for i, d in enumerate(drafts):
            if d.role not in self.roles:
                raise ValueError(f"Role không tồn tại: {d.role}")
            if any(j >= i for j in d.depends_on):
                raise ValueError(f"Task {i} phụ thuộc task phía sau (có thể tạo vòng)")
        return drafts
