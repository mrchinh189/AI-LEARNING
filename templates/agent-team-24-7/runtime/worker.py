"""Worker: lấy task -> kiểm tra ngân sách -> agent chạy -> reviewer chấm -> cập nhật board."""
from __future__ import annotations

from board.models import TaskStatus
from config import settings


def process(task_id: int, board, agents: dict, reviewer, guard, notify) -> None:
    task = board.tasks[task_id]
    goal = board.goals[task.goal_id]
    if not guard.within_budget(goal):
        task.status = TaskStatus.BLOCKED
        board.update_task(task)
        notify(goal.owner_user_id, f"Goal #{goal.id} đã chạm trần ngân sách, task #{task.id} tạm dừng.")
        return

    task.status = TaskStatus.DOING
    task.attempts += 1
    result = agents[task.role].run(task)
    board.add_cost(goal.id, result.cost_usd)

    if result.needs_approval:
        guard.request_approval(task, result.needs_approval, notify)

    task.result = result.output
    task.status = TaskStatus.REVIEW
    review = reviewer.review(task)
    if review.passed:
        task.status = TaskStatus.DONE
    elif task.attempts >= settings.max_task_attempts:
        task.status = TaskStatus.BLOCKED
        notify(goal.owner_user_id, f"Task #{task.id} '{task.title}' bị chặn sau {task.attempts} lần: {review.feedback}")
    else:
        task.status = TaskStatus.TODO            # heartbeat sẽ đưa lại vào hàng đợi
        task.review_feedback = review.feedback
    board.update_task(task)


def run() -> None:  # pragma: no cover
    raise NotImplementedError("Khởi tạo PostgresBoard, RedisQueue, agents, Reviewer, Guard rồi lặp queue.pop() -> process()")
