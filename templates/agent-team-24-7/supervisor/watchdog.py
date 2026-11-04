"""Watchdog: phát hiện bất thường và gửi báo cáo định kỳ qua chat."""
from __future__ import annotations

from board.models import GoalStatus, TaskStatus


def check(board) -> list[str]:
    alerts: list[str] = []
    for g in board.goals.values():
        if g.status != GoalStatus.ACTIVE:
            continue
        if g.spent_usd >= 0.8 * g.budget_usd:
            alerts.append(f"Goal #{g.id} đã dùng {g.spent_usd / g.budget_usd:.0%} ngân sách.")
        blocked = [t for t in board.tasks_of(g.id) if t.status == TaskStatus.BLOCKED]
        if blocked:
            alerts.append(f"Goal #{g.id} có {len(blocked)} task bị chặn: " + ", ".join(f"#{t.id}" for t in blocked))
        # TODO: task ở trạng thái doing quá lâu (cần cột updated_at) -> đưa lại hàng đợi
    return alerts


def daily_report(board) -> str:
    return "\n".join(f"#{g.id} {g.title}: {board.progress(g.id)}" for g in board.goals.values())


def run() -> None:  # pragma: no cover
    raise NotImplementedError("Lặp mỗi 10 phút: check() -> notify; 8h sáng: daily_report() -> notify")
