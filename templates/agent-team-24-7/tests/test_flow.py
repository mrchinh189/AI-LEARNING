"""Kiểm tra luồng goal -> task -> worker -> review mà không cần LLM."""
import os

os.environ.setdefault("ALLOWED_USER_IDS", "1")

from agents.base import AgentResult, load_registry
from agents.reviewer import Review
from board.models import GoalStatus, TaskDraft, TaskStatus
from board.repo import InMemoryBoard
from gateway.commands import parse
from orchestrator.heartbeat import tick
from orchestrator.planner import Planner
from policy.guard import Guard
from runtime.queue import MemoryQueue
from runtime.worker import process
from supervisor.watchdog import check


class FakeAgent:
    def run(self, task, context=""):
        return AgentResult(output=f"done: {task.title}", cost_usd=0.1)


class FlakyReviewer:
    """Lần đầu trả fail, lần sau pass."""
    def __init__(self):
        self.seen = set()

    def review(self, task):
        if task.id in self.seen:
            return Review(True)
        self.seen.add(task.id)
        return Review(False, "thiếu nguồn")


def drain(board, queue, agents, reviewer, guard, notes):
    while (tid := queue.pop()) is not None:
        process(tid, board, agents, reviewer, guard, lambda u, m: notes.append(m))


def test_parse_commands():
    assert parse("/goal Viết 3 bài").name == "goal"
    assert parse("/status@MyBot").name == "status"
    assert parse("xin chào").name == "chat"


def test_registry_and_validation():
    roles = list(load_registry())
    assert {"planner", "researcher", "reviewer"} <= set(roles)
    p = Planner(roles)
    try:
        p.validate([TaskDraft("a", "x", "y", "researcher", depends_on=[0])])
        raise AssertionError("phải lỗi vì tự phụ thuộc")
    except ValueError:
        pass


def test_goal_runs_to_done_with_retry():
    board, queue, guard = InMemoryBoard(), MemoryQueue(), Guard()
    planner = Planner(list(load_registry()))
    goal = board.create_goal(1, "Viết bài blog", budget_usd=5)
    board.add_tasks(goal.id, planner.validate([
        TaskDraft("Research", "tìm tài liệu", "có 3 nguồn", "researcher"),
        TaskDraft("Viết", "viết bài", "800 chữ", "writer", depends_on=[0]),
    ]))
    board.set_goal_status(goal.id, GoalStatus.ACTIVE)
    agents = {r: FakeAgent() for r in load_registry()}
    reviewer, notes = FlakyReviewer(), []

    for _ in range(6):                      # mô phỏng nhiều chu kỳ heartbeat
        tick(board, planner, queue)
        drain(board, queue, agents, reviewer, guard, notes)

    assert all(t.status == TaskStatus.DONE for t in board.tasks_of(goal.id))
    assert board.goals[goal.id].status == GoalStatus.DONE
    assert board.goals[goal.id].spent_usd > 0


def test_budget_blocks_and_watchdog_alerts():
    board, guard = InMemoryBoard(), Guard()
    goal = board.create_goal(1, "x", budget_usd=0.1)
    (t,) = board.add_tasks(goal.id, [TaskDraft("a", "b", "c", "writer")])
    board.set_goal_status(goal.id, GoalStatus.ACTIVE)
    board.add_cost(goal.id, 0.1)
    notes = []
    process(t.id, board, {"writer": FakeAgent()}, FlakyReviewer(), guard, lambda u, m: notes.append(m))
    assert board.tasks[t.id].status == TaskStatus.BLOCKED
    assert notes and check(board)


def test_policy_and_idempotent_approval():
    g = Guard()
    assert g.needs_approval("payment.transfer") and g.is_denied("shell.host")
    board = InMemoryBoard()
    goal = board.create_goal(1, "x")
    (t,) = board.add_tasks(goal.id, [TaskDraft("a", "b", "c", "writer")])
    sent = []
    req = {"action": "social.publish", "payload": {"post": 1}}
    k1 = g.request_approval(t, req, lambda u, m: sent.append(m))
    k2 = g.request_approval(t, req, lambda u, m: sent.append(m))
    assert k1 == k2 and len(sent) == 1
