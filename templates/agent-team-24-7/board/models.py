"""Model dữ liệu dùng chung giữa các lớp."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    TODO = "todo"
    QUEUED = "queued"
    DOING = "doing"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class GoalStatus(str, Enum):
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    ACTIVE = "active"
    PAUSED = "paused"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class Goal:
    id: int
    owner_user_id: int
    title: str
    description: str = ""
    status: GoalStatus = GoalStatus.PLANNING
    priority: str = "normal"
    budget_usd: float = 5.0
    spent_usd: float = 0.0


@dataclass
class TaskDraft:
    """Planner sinh ra; chỉ số trong depends_on là vị trí trong cùng danh sách draft."""
    title: str
    instructions: str
    acceptance_criteria: str
    role: str
    depends_on: list[int] = field(default_factory=list)


@dataclass
class Task:
    id: int
    goal_id: int
    title: str
    instructions: str
    acceptance_criteria: str
    role: str
    status: TaskStatus = TaskStatus.TODO
    depends_on: list[int] = field(default_factory=list)
    attempts: int = 0
    result: str | None = None
    review_feedback: str | None = None
