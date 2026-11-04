"""Chốt chặn: allowlist tool, duyệt hành động rủi ro, ngân sách."""
from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path

import yaml

HERE = Path(__file__).parent


class Guard:
    def __init__(self, path: Path = HERE / "policy.yaml") -> None:
        self.cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.pending: dict[str, dict] = {}

    def is_denied(self, action: str) -> bool:
        return any(fnmatch.fnmatch(action, p) for p in self.cfg.get("deny", []))

    def needs_approval(self, action: str) -> bool:
        return any(fnmatch.fnmatch(action, p) for p in self.cfg.get("require_approval", []))

    @staticmethod
    def within_budget(goal) -> bool:
        return goal.spent_usd < goal.budget_usd

    @staticmethod
    def idempotency_key(task_id: int, action: str, payload: dict) -> str:
        raw = json.dumps([task_id, action, payload], sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def request_approval(self, task, req: dict, notify) -> str:
        key = self.idempotency_key(task.id, req["action"], req.get("payload", {}))
        if key not in self.pending:                 # retry không tạo yêu cầu trùng
            self.pending[key] = {"task_id": task.id, **req, "status": "pending"}
            notify(None, f"Cần duyệt: {req['action']} (task #{task.id}). /approve {key} hoặc /reject {key}")
        return key
