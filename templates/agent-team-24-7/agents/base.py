"""Base agent và nạp registry."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from board.models import Task

HERE = Path(__file__).parent


@dataclass
class AgentResult:
    output: str
    cost_usd: float = 0.0
    needs_approval: dict | None = None   # {"action": ..., "payload": {...}} nếu muốn làm việc rủi ro


@dataclass
class AgentSpec:
    role: str
    description: str
    model: str
    prompt: str
    tools: list[str]

    @property
    def system_prompt(self) -> str:
        return (HERE / self.prompt).read_text(encoding="utf-8")


def load_registry(path: Path = HERE / "registry.yaml") -> dict[str, AgentSpec]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))["agents"]
    return {role: AgentSpec(role=role, **cfg) for role, cfg in data.items()}


class Agent:
    def __init__(self, spec: AgentSpec) -> None:
        self.spec = spec

    def run(self, task: Task, context: str = "") -> AgentResult:
        """TODO: gọi LLM/framework (LangGraph, Claude Agent SDK, OpenAI Agents SDK...).

        Đầu vào: self.spec.system_prompt, task.instructions, task.acceptance_criteria,
        task.review_feedback (nếu làm lại), context từ memory. Tool lấy theo self.spec.tools
        và PHẢI đi qua policy.guard.Guard trước khi thực thi.
        """
        raise NotImplementedError
