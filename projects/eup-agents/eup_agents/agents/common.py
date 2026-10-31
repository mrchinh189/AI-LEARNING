"""Hàm dùng chung: đọc danh sách Task và chuẩn hóa dữ liệu."""

import json
from datetime import date, datetime

from ..config import settings

TASK_FIELDS = [
    "name", "subject", "status", "priority", "exp_end_date", "completed_on", "creation",
    "owner", "_assign", "company", "department", "project",
    "eup_assigned_by", "eup_confirm_state", "eup_escalation_level", "eup_source", "eup_source_ref",
]

OPEN_STATUSES = ["Open", "Working", "Overdue", "Pending Review"]
UNCONFIRMED = "Chờ xác nhận"


def today() -> date:
    return datetime.now(settings.timezone).date()


def assignees(task: dict) -> list[str]:
    """_assign của Frappe là chuỗi JSON dạng '["a@eup.vn"]'."""
    raw = task.get("_assign") or "[]"
    try:
        return [u for u in json.loads(raw) if u]
    except (TypeError, json.JSONDecodeError):
        return []


def as_date(v) -> date | None:
    if not v:
        return None
    return v if isinstance(v, date) else date.fromisoformat(str(v)[:10])


def company_filter() -> list:
    """Giới hạn phạm vi theo các công ty pilot trong config/org.json (để trống = tất cả)."""
    companies = settings.org().get("pilot_companies") or []
    return [["company", "in", companies]] if companies else []


def open_tasks(erp) -> list[dict]:
    return erp.get_list("Task", [["status", "in", OPEN_STATUSES], *company_filter()], TASK_FIELDS,
                        order_by="exp_end_date asc", limit=2000)


def task_link(name: str) -> str:
    return f"{settings.erp_url}/app/task/{name}"
