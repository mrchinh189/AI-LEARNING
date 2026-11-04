"""Truy cập board. InMemoryBoard cho test; PostgresBoard cho production."""
from __future__ import annotations

from itertools import count

from .models import Goal, GoalStatus, Task, TaskDraft, TaskStatus


class InMemoryBoard:
    def __init__(self) -> None:
        self.goals: dict[int, Goal] = {}
        self.tasks: dict[int, Task] = {}
        self._gid = count(1)
        self._tid = count(1)

    # ---- goals ----
    def create_goal(self, owner_user_id: int, title: str, budget_usd: float = 5.0) -> Goal:
        g = Goal(id=next(self._gid), owner_user_id=owner_user_id, title=title, budget_usd=budget_usd)
        self.goals[g.id] = g
        return g

    def set_goal_status(self, goal_id: int, status: GoalStatus) -> None:
        self.goals[goal_id].status = status

    def add_cost(self, goal_id: int, usd: float) -> None:
        self.goals[goal_id].spent_usd += usd

    # ---- tasks ----
    def add_tasks(self, goal_id: int, drafts: list[TaskDraft]) -> list[Task]:
        created: list[Task] = []
        for d in drafts:
            t = Task(id=next(self._tid), goal_id=goal_id, title=d.title, instructions=d.instructions,
                     acceptance_criteria=d.acceptance_criteria, role=d.role)
            created.append(t)
        for d, t in zip(drafts, created):          # đổi chỉ số draft -> id thật
            t.depends_on = [created[i].id for i in d.depends_on]
            self.tasks[t.id] = t
        return created

    def tasks_of(self, goal_id: int) -> list[Task]:
        return [t for t in self.tasks.values() if t.goal_id == goal_id]

    def ready_tasks(self, goal_id: int) -> list[Task]:
        """Task todo có đủ phụ thuộc đã done."""
        return [
            t for t in self.tasks_of(goal_id)
            if t.status == TaskStatus.TODO
            and all(self.tasks[d].status == TaskStatus.DONE for d in t.depends_on)
        ]

    def update_task(self, task: Task) -> None:
        self.tasks[task.id] = task

    def progress(self, goal_id: int) -> dict[str, int]:
        out: dict[str, int] = {}
        for t in self.tasks_of(goal_id):
            out[t.status.value] = out.get(t.status.value, 0) + 1
        return out


class PostgresBoard(InMemoryBoard):
    """TODO: hiện thực cùng interface với psycopg dựa trên board/schema.sql."""

    def __init__(self, dsn: str) -> None:  # pragma: no cover
        raise NotImplementedError("Gắn psycopg tại đây")
