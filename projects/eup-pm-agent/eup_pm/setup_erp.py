"""Tạo doctype, custom field và role cần thiết trên ERP. Chạy 1 lần bằng tài khoản System Manager.

Chạy lại nhiều lần vẫn an toàn: cái gì đã có thì bỏ qua.
"""

from __future__ import annotations

import logging

from .erp import ErpClient

log = logging.getLogger("eup_pm.setup")

MODULE = "Projects"
AGENT_ROLE = "EuP Project Agent"


def _perms(*roles_full: str, read_write: tuple[str, ...] = ()) -> list[dict]:
    full = dict(read=1, write=1, create=1, delete=1, report=1, export=1, print=1, email=1, share=1)
    rows = [{"role": r, **full} for r in roles_full]
    rows += [{"role": r, "read": 1, "write": 1, "create": 1, "report": 1, "email": 1} for r in read_write]
    return rows


DOCTYPES = [
    {
        "name": "Nx Task Evidence",
        "istable": 1,
        "fields": [
            {"fieldname": "reference_doctype", "label": "Loại chứng từ", "fieldtype": "Link",
             "options": "DocType", "reqd": 1, "in_list_view": 1},
            {"fieldname": "reference_name", "label": "Số chứng từ", "fieldtype": "Dynamic Link",
             "options": "reference_doctype", "reqd": 1, "in_list_view": 1},
            {"fieldname": "condition_field", "label": "Trường kiểm tra", "fieldtype": "Select",
             "options": "workflow_state\ndocstatus\nstatus", "default": "workflow_state", "in_list_view": 1},
            {"fieldname": "required_value", "label": "Giá trị cần đạt", "fieldtype": "Data",
             "reqd": 1, "in_list_view": 1},
            {"fieldname": "is_met", "label": "Đã đạt", "fieldtype": "Check", "read_only": 1, "in_list_view": 1},
            {"fieldname": "is_rejected", "label": "Bị hủy/từ chối", "fieldtype": "Check", "read_only": 1},
            {"fieldname": "last_checked", "label": "Kiểm tra lần cuối", "fieldtype": "Datetime", "read_only": 1},
        ],
        "permissions": [],
    },
    {
        "name": "Nx Project Alert",
        "autoname": "format:ALERT-{YY}{MM}-{####}",
        "title_field": "rule_code",
        "fields": [
            {"fieldname": "project", "label": "Dự án", "fieldtype": "Link", "options": "Project",
             "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
            {"fieldname": "task", "label": "Việc", "fieldtype": "Link", "options": "Task", "in_list_view": 1},
            {"fieldname": "severity", "label": "Mức", "fieldtype": "Select", "options": "Vàng\nĐỏ",
             "in_list_view": 1, "in_standard_filter": 1},
            {"fieldname": "rule_code", "label": "Mã quy tắc", "fieldtype": "Data", "in_list_view": 1},
            {"fieldname": "status", "label": "Trạng thái", "fieldtype": "Select",
             "options": "Mới\nĐã xem\nĐã xử lý\nBỏ qua", "default": "Mới",
             "in_list_view": 1, "in_standard_filter": 1},
            {"fieldname": "facts", "label": "Dữ kiện", "fieldtype": "Small Text"},
            {"fieldname": "feedback", "label": "PM đánh giá", "fieldtype": "Select",
             "options": "\nĐúng\nSai\nThừa"},
            {"fieldname": "dismiss_reason", "label": "Lý do bỏ qua", "fieldtype": "Small Text",
             "depends_on": "eval:doc.status=='Bỏ qua'"},
            {"fieldname": "agent_section", "label": "Phân tích của Agent Rủi ro", "fieldtype": "Section Break"},
            {"fieldname": "root_cause", "label": "Nguyên nhân gốc", "fieldtype": "Small Text", "read_only": 1},
            {"fieldname": "impact", "label": "Tác động", "fieldtype": "Small Text", "read_only": 1},
            {"fieldname": "options", "label": "Phương án", "fieldtype": "Text", "read_only": 1},
            {"fieldname": "decision_owner", "label": "Người cần quyết (vai trò)", "fieldtype": "Data",
             "read_only": 1},
            {"fieldname": "decide_by_text", "label": "Hạn quyết định", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "data_gaps", "label": "Dữ liệu còn thiếu", "fieldtype": "Small Text", "read_only": 1},
            {"fieldname": "analysed_by_agent", "label": "Agent đã phân tích", "fieldtype": "Check",
             "read_only": 1},
        ],
        "permissions": _perms("System Manager", "Projects Manager", read_write=(AGENT_ROLE, "Projects User")),
    },
    {
        "name": "Nx Project Status Report",
        "autoname": "format:BC-{YY}{MM}-{####}",
        "title_field": "project",
        "fields": [
            {"fieldname": "project", "label": "Dự án", "fieldtype": "Link", "options": "Project",
             "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
            {"fieldname": "period_end", "label": "Số liệu đến ngày", "fieldtype": "Date", "in_list_view": 1},
            {"fieldname": "status", "label": "Trạng thái", "fieldtype": "Select",
             "options": "Nháp\nChờ PM duyệt\nĐã phát hành\nTừ chối", "default": "Nháp",
             "in_list_view": 1, "in_standard_filter": 1},
            {"fieldname": "rag", "label": "RAG", "fieldtype": "Select", "options": "Xanh\nVàng\nĐỏ",
             "in_list_view": 1},
            {"fieldname": "planned_pct", "label": "% kế hoạch", "fieldtype": "Percent"},
            {"fieldname": "actual_pct", "label": "% thực tế", "fieldtype": "Percent"},
            {"fieldname": "spi", "label": "SPI", "fieldtype": "Float", "precision": "2"},
            {"fieldname": "forecast_end", "label": "Dự báo kết thúc", "fieldtype": "Date"},
            {"fieldname": "body", "label": "Nội dung", "fieldtype": "Text Editor"},
            {"fieldname": "pm_comment", "label": "Ý kiến PM", "fieldtype": "Small Text"},
            {"fieldname": "sent", "label": "Đã gửi", "fieldtype": "Check", "read_only": 1},
            {"fieldname": "sent_on", "label": "Gửi lúc", "fieldtype": "Datetime", "read_only": 1},
        ],
        "permissions": _perms("System Manager", "Projects Manager", read_write=(AGENT_ROLE,)),
    },
    {
        "name": "Nx Plan Draft",
        "autoname": "format:KH-{YY}{MM}-{####}",
        "title_field": "project",
        "fields": [
            {"fieldname": "project", "label": "Dự án", "fieldtype": "Link", "options": "Project",
             "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
            {"fieldname": "status", "label": "Trạng thái", "fieldtype": "Select",
             "options": "Nháp\nĐã duyệt\nTừ chối\nĐã áp dụng", "default": "Nháp", "in_list_view": 1},
            {"fieldname": "task_count", "label": "Số việc", "fieldtype": "Int", "read_only": 1,
             "in_list_view": 1},
            {"fieldname": "forecast_end", "label": "Dự báo kết thúc", "fieldtype": "Date", "read_only": 1},
            {"fieldname": "summary", "label": "Tóm tắt", "fieldtype": "Text"},
            {"fieldname": "assumptions", "label": "Giả định", "fieldtype": "Text"},
            {"fieldname": "pm_comment", "label": "Ý kiến PM", "fieldtype": "Small Text"},
            {"fieldname": "plan_json", "label": "Kế hoạch (JSON)", "fieldtype": "Code", "options": "JSON",
             "read_only": 1},
        ],
        "permissions": _perms("System Manager", "Projects Manager", read_write=(AGENT_ROLE,)),
    },
]

PROJECT_TYPES = "\nDT\nERP\nXK\nSP\nIT"

CUSTOM_FIELDS = {
    "Project": [
        {"fieldname": "custom_ai_section", "label": "AI Agent", "fieldtype": "Section Break",
         "insert_after": "notes", "collapsible": 1},
        {"fieldname": "custom_agent_enabled", "label": "Bật AI agent", "fieldtype": "Check"},
        {"fieldname": "custom_eup_project_type", "label": "Loại dự án EuP", "fieldtype": "Select",
         "options": PROJECT_TYPES},
        {"fieldname": "custom_pmo_owner", "label": "PM phụ trách", "fieldtype": "Link", "options": "User"},
        {"fieldname": "custom_sponsor", "label": "Người bảo trợ", "fieldtype": "Link", "options": "User"},
        {"fieldname": "custom_report_emails", "label": "Email nhận báo cáo", "fieldtype": "Small Text",
         "description": "Các email cách nhau bằng dấu phẩy"},
        {"fieldname": "custom_ai_col", "fieldtype": "Column Break"},
        {"fieldname": "custom_baseline_end", "label": "Ngày kết thúc baseline", "fieldtype": "Date"},
        {"fieldname": "custom_rag", "label": "RAG", "fieldtype": "Select", "options": "\nXanh\nVàng\nĐỏ",
         "read_only": 1, "in_list_view": 1},
        {"fieldname": "custom_spi", "label": "SPI", "fieldtype": "Float", "precision": "2", "read_only": 1},
        {"fieldname": "custom_forecast_end", "label": "Dự báo kết thúc", "fieldtype": "Date", "read_only": 1},
        {"fieldname": "custom_last_agent_run", "label": "Agent chạy lần cuối", "fieldtype": "Datetime",
         "read_only": 1},
    ],
    "Task": [
        {"fieldname": "custom_ai_section", "label": "Theo dõi tiến độ", "fieldtype": "Section Break",
         "insert_after": "description", "collapsible": 1},
        {"fieldname": "custom_baseline_start", "label": "Bắt đầu baseline", "fieldtype": "Date"},
        {"fieldname": "custom_baseline_end", "label": "Kết thúc baseline", "fieldtype": "Date"},
        {"fieldname": "custom_forecast_end", "label": "Dự kiến xong", "fieldtype": "Date"},
        {"fieldname": "custom_ai_col", "fieldtype": "Column Break"},
        {"fieldname": "custom_progress_source", "label": "Nguồn tiến độ", "fieldtype": "Select",
         "options": "\nBằng chứng\nTự khai\nPM nhập"},
        {"fieldname": "custom_blocker", "label": "Vướng mắc", "fieldtype": "Small Text"},
        {"fieldname": "custom_last_checkin", "label": "Cập nhật lần cuối", "fieldtype": "Datetime",
         "read_only": 1},
        {"fieldname": "custom_evidence_section", "label": "Chứng từ bằng chứng", "fieldtype": "Section Break"},
        {"fieldname": "custom_evidence", "label": "Chứng từ bằng chứng", "fieldtype": "Table",
         "options": "Nx Task Evidence"},
    ],
}


def run_setup(erp: ErpClient):
    if not erp.exists("Role", AGENT_ROLE):
        erp.insert("Role", {"role_name": AGENT_ROLE, "desk_access": 1})
        log.info("Tạo Role %s", AGENT_ROLE)
    else:
        log.info("Đã có Role %s", AGENT_ROLE)

    for spec in DOCTYPES:
        if erp.exists("DocType", spec["name"]):
            _ensure_fields(erp, spec)
            continue
        data = {
            "doctype": "DocType",
            "name": spec["name"],
            "module": MODULE,
            "custom": 1,
            "istable": spec.get("istable", 0),
            "track_changes": 1,
            "fields": spec["fields"],
            "permissions": spec["permissions"],
        }
        for k in ("autoname", "title_field"):
            if k in spec:
                data[k] = spec[k]
        erp.insert("DocType", data)
        log.info("Tạo DocType %s", spec["name"])

    for dt, fields in CUSTOM_FIELDS.items():
        prev = None
        for f in fields:
            name = f"{dt}-{f['fieldname']}"
            data = {"dt": dt, **f}
            if "insert_after" not in data and prev:
                data["insert_after"] = prev
            prev = f["fieldname"]
            if erp.exists("Custom Field", name):
                log.info("Đã có Custom Field %s", name)
                continue
            erp.insert("Custom Field", data)
            log.info("Tạo Custom Field %s", name)


def _ensure_fields(erp: ErpClient, spec: dict):
    """DocType đã có (từ phiên bản cũ của bộ cài): thêm các field còn thiếu, không đụng field đang có."""
    doc = erp.get_doc("DocType", spec["name"])
    have = {f["fieldname"] for f in doc.get("fields", [])}
    missing = [f for f in spec["fields"] if f["fieldname"] not in have]
    if not missing:
        log.info("Đã có DocType %s, đủ field", spec["name"])
        return
    erp.update("DocType", spec["name"], {"fields": doc["fields"] + missing})
    log.info("DocType %s: thêm %d field (%s)", spec["name"], len(missing),
             ", ".join(f["fieldname"] for f in missing))
