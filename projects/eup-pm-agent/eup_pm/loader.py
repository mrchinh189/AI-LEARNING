"""Đọc Project, Task và lịch làm việc từ ERP rồi chuyển thành dữ liệu cho engine."""

from __future__ import annotations

import json
from datetime import date

from .engine import TaskData, WorkCalendar
from .erp import ErpClient, ErpError

PROJECT_FIELDS = [
    "name", "project_name", "status", "company", "expected_start_date", "expected_end_date",
    "custom_eup_project_type", "custom_pmo_owner", "custom_sponsor", "custom_baseline_end",
    "custom_report_emails", "custom_agent_enabled",
]

_calendar_cache: dict[str, WorkCalendar] = {}


def parse_date(v) -> date | None:
    if not v:
        return None
    return date.fromisoformat(str(v)[:10])


def active_projects(erp: ErpClient, only: str | None = None) -> list[dict]:
    filters = [["status", "=", "Open"], ["custom_agent_enabled", "=", 1]]
    if only:
        filters.append(["name", "=", only])
    return erp.get_list("Project", filters=filters, fields=PROJECT_FIELDS)


def calendar_for(erp: ErpClient, company: str | None) -> WorkCalendar:
    """Nghỉ Chủ nhật + các ngày trong Holiday List mặc định của Company."""
    key = company or ""
    if key in _calendar_cache:
        return _calendar_cache[key]
    holidays: set[date] = set()
    if company:
        try:
            hl_name = erp.get_doc("Company", company).get("default_holiday_list")
            if hl_name:
                for h in erp.get_doc("Holiday List", hl_name).get("holidays", []):
                    holidays.add(parse_date(h["holiday_date"]))
        except ErpError:
            pass
    cal = WorkCalendar(holidays)
    _calendar_cache[key] = cal
    return cal


def load_task_docs(erp: ErpClient, project: str) -> list[dict]:
    names = erp.get_list("Task", filters=[["project", "=", project]], fields=["name"])
    return [erp.get_doc("Task", n["name"]) for n in names]


def to_task_data(doc: dict, evidence_override: dict[str, tuple[bool, bool]] | None = None) -> TaskData:
    rows = doc.get("custom_evidence") or []
    met = bool(rows) and all(r.get("is_met") for r in rows)
    rejected = any(r.get("is_rejected") for r in rows)
    if evidence_override and doc["name"] in evidence_override:
        met, rejected = evidence_override[doc["name"]]
    try:
        owners = json.loads(doc.get("_assign") or "[]")
    except ValueError:
        owners = []
    last = parse_date(doc.get("custom_last_checkin")) or parse_date(doc.get("modified"))
    return TaskData(
        name=doc["name"],
        subject=doc.get("subject") or doc["name"],
        status=doc.get("status") or "Open",
        progress=float(doc.get("progress") or 0),
        exp_start=parse_date(doc.get("exp_start_date")),
        exp_end=parse_date(doc.get("exp_end_date")),
        baseline_start=parse_date(doc.get("custom_baseline_start")),
        baseline_end=parse_date(doc.get("custom_baseline_end")),
        forecast_end=parse_date(doc.get("custom_forecast_end")),
        weight=float(doc["task_weight"]) if doc.get("task_weight") else None,
        is_milestone=bool(doc.get("is_milestone")),
        is_group=bool(doc.get("is_group")),
        depends_on=[d["task"] for d in doc.get("depends_on") or [] if d.get("task")],
        last_update=last,
        blocker=doc.get("custom_blocker") or "",
        owners=owners,
        has_evidence=bool(rows),
        evidence_met=met,
        evidence_rejected=rejected,
    )
