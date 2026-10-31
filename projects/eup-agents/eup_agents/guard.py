"""Lớp Kiểm soát: mọi lệnh ghi lên ERP phải đi qua đây.

Agent chỉ được ghi đúng các thao tác trong WRITE_ALLOWLIST. Không có đường nào để
Submit, Cancel, Amend hay Delete chứng từ.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from .config import ROOT

log = logging.getLogger("eup_agents.guard")

WRITE_ALLOWLIST = {
    ("Task", "create"),
    ("Task", "update"),
    ("Task", "assign"),
    ("Comment", "create"),
    ("Notification Log", "create"),
}

# Trường của Task mà agent được phép sửa sau khi tạo.
TASK_UPDATABLE_FIELDS = {"eup_escalation_level"}

ACTION_LOG = ROOT / "logs" / "agent_actions.jsonl"


class GuardError(PermissionError):
    pass


def check(agent: str, doctype: str, action: str, payload: dict) -> None:
    if (doctype, action) not in WRITE_ALLOWLIST:
        raise GuardError(f"{agent} không được '{action}' trên {doctype}")
    if doctype == "Task" and action == "update":
        extra = set(payload) - TASK_UPDATABLE_FIELDS
        if extra:
            raise GuardError(f"{agent} không được sửa trường {sorted(extra)} của Task")
    if doctype == "Task" and action == "create":
        if payload.get("eup_confirm_state") != "Chờ xác nhận" or not payload.get("eup_agent_created"):
            raise GuardError("Task do agent tạo phải có eup_agent_created=1 và ở trạng thái 'Chờ xác nhận'")
    if doctype == "Comment" and payload.get("reference_doctype") != "Task":
        raise GuardError("Agent chỉ được comment trên Task")


def record(agent: str, doctype: str, action: str, target: str, payload: dict, result: str, dry_run: bool) -> None:
    """Ghi nhật ký hành động (file JSONL, chỉ thêm, không sửa)."""
    ACTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "agent": agent,
        "doctype": doctype,
        "action": action,
        "target": target,
        "dry_run": dry_run,
        "result": result,
        "payload": payload,
    }
    with Path(ACTION_LOG).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    log.info("%s %s %s %s -> %s", agent, action, doctype, target, result)
