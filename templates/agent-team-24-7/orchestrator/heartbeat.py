"""Chu kỳ điều phối: đưa task sẵn sàng vào hàng đợi, tái lập kế hoạch, đóng goal."""
from __future__ import annotations

import time

from board.models import GoalStatus, TaskStatus
from config import settings


def tick(board, planner, queue) -> None:
    for goal in list(board.goals.values()):
        if goal.status != GoalStatus.ACTIVE:
            continue
        new = planner.replan(goal, board.tasks_of(goal.id))
        if new:
            board.add_tasks(goal.id, planner.validate(new))
        for t in board.ready_tasks(goal.id):
            t.status = TaskStatus.QUEUED
            board.update_task(t)
            queue.push(t.id)
        tasks = board.tasks_of(goal.id)
        if tasks and all(t.status in (TaskStatus.DONE, TaskStatus.CANCELLED) for t in tasks):
            board.set_goal_status(goal.id, GoalStatus.DONE)


def run() -> None:  # pragma: no cover
    from agents.base import load_registry
    from board.repo import PostgresBoard
    from orchestrator.planner import Planner
    from runtime.queue import RedisQueue

    board = PostgresBoard(settings.database_url)
    planner = Planner(list(load_registry()))
    queue = RedisQueue(settings.redis_url)
    while True:
        tick(board, planner, queue)
        time.sleep(settings.heartbeat_minutes * 60)
