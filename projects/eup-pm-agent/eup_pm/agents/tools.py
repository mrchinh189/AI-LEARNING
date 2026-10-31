"""Tool đọc ERP dùng chung cho các agent. Tất cả chỉ đọc; tool ghi nằm trong từng agent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..config import ROOT, Settings
from ..engine import fmt_date, fmt_num, fmt_pct
from ..erp import ErpClient, ErpError
from ..loader import active_projects, parse_date
from .base import Tool, ToolRejected

KB_DIR = ROOT / "kb"

# Chứng từ agent được đọc. Muốn agent tra thêm loại nào thì thêm vào đây VÀ cấp quyền Read trên ERP.
READABLE_DOCTYPES = {
    "Material Request", "Purchase Order", "Purchase Receipt", "Purchase Invoice", "Payment Entry",
    "Sales Order", "Delivery Note", "Sales Invoice", "Stock Entry", "BOM",
    "Customs declaration", "Yeu cau san xuat", "De nghi thanh toan", "Nx Request For Advance",
    "Container Load Plan", "Nx Container", "Domestic Shipment",
}
# Chỉ trả các field này cho agent: đủ để biết trạng thái, không gửi đơn giá, công nợ ra ngoài.
DOC_FIELDS = (
    "name", "title", "docstatus", "workflow_state", "status", "company", "project",
    "transaction_date", "posting_date", "schedule_date", "delivery_date", "supplier", "supplier_name",
    "customer", "customer_name", "modified", "per_received", "per_billed", "per_delivered",
)
ITEM_FIELDS = ("item_code", "item_name", "qty", "received_qty", "delivered_qty", "schedule_date")


@dataclass
class Ctx:
    erp: ErpClient
    settings: Settings
    today: date


def _task_brief(d: dict) -> dict:
    rows = d.get("custom_evidence") or []
    return {
        "task": d["name"],
        "việc": d.get("subject"),
        "trạng_thái": d.get("status"),
        "tiến_độ": f"{fmt_num(float(d.get('progress') or 0))}%",
        "bắt_đầu": fmt_date(parse_date(d.get("exp_start_date"))),
        "hạn": fmt_date(parse_date(d.get("exp_end_date"))),
        "baseline_kết_thúc": fmt_date(parse_date(d.get("custom_baseline_end"))),
        "dự_kiến_xong": fmt_date(parse_date(d.get("custom_forecast_end"))),
        "vướng_mắc": d.get("custom_blocker") or "",
        "mốc": bool(d.get("is_milestone")),
        "phụ_thuộc": [x.get("task") for x in d.get("depends_on") or []],
        "người_phụ_trách": d.get("_assign") or "[]",
        "bằng_chứng": [{
            "chứng_từ": f"{r.get('reference_doctype')} {r.get('reference_name')}",
            "điều_kiện": f"{r.get('condition_field')} = {r.get('required_value')}",
            "đã_đạt": bool(r.get("is_met")), "bị_từ_chối": bool(r.get("is_rejected")),
        } for r in rows],
    }


def project_overview(ctx: Ctx, project: str) -> dict:
    from ..jobs import analyse_project  # tránh import vòng

    ps = active_projects(ctx.erp, project)
    if not ps:
        raise ToolRejected(f"Không có Project {project} đang Open và bật AI agent")
    p = ps[0]
    res, docs = analyse_project(ctx.erp, ctx.settings, p, ctx.today, verify=False)
    subj = {d["name"]: d.get("subject") for d in docs}
    return {
        "project": p["name"], "tên": p.get("project_name"), "loại": p.get("custom_eup_project_type"),
        "pm": p.get("custom_pmo_owner"), "rag": res.rag,
        "kế_hoạch": fmt_pct(res.planned_pct), "thực_tế": fmt_pct(res.actual_pct), "spi": fmt_num(res.spi, 2),
        "baseline_kết_thúc": fmt_date(res.deadline), "dự_báo_kết_thúc": fmt_date(res.forecast_end),
        "trễ_ngày_làm_việc": max(res.slip_wd or 0, 0),
        "đường_găng": [{"task": n, "việc": subj.get(n), "dự_báo_xong": fmt_date(t.early_finish)}
                       for n, t in res.tasks.items() if t.critical],
        "cảnh_báo": [{"mã": a.rule_code, "mức": a.severity, "task": a.task, "nội_dung": a.facts}
                     for a in res.alerts],
        "lỗi_dữ_liệu": res.data_errors,
    }


def read_tools(ctx: Ctx) -> dict[str, Tool]:
    erp = ctx.erp

    def get_project_overview(i):
        return project_overview(ctx, i["project"])

    def get_task(i):
        try:
            d = erp.get_doc("Task", i["task"])
        except ErpError as e:
            raise ToolRejected(str(e))
        out = _task_brief(d)
        comments = erp.get_list("Comment", filters=[["reference_doctype", "=", "Task"],
                                                     ["reference_name", "=", d["name"]],
                                                     ["comment_type", "=", "Comment"]],
                                fields=["content", "creation"], order_by="creation desc", limit=5)
        out["ghi_chú_gần_đây"] = [{"lúc": c.get("creation"), "nội_dung": (c.get("content") or "")[:500]}
                                  for c in comments]
        return out

    def get_predecessors(i):
        """Chuỗi việc phải xong trước task này, tối đa 5 tầng."""
        chain, frontier, seen = [], [i["task"]], set()
        for depth in range(5):
            nxt = []
            for name in frontier:
                if name in seen:
                    continue
                seen.add(name)
                d = erp.get_doc("Task", name)
                if name != i["task"]:
                    chain.append({"tầng": depth, **_task_brief(d)})
                nxt += [x.get("task") for x in d.get("depends_on") or [] if x.get("task")]
            frontier = nxt
            if not frontier:
                break
        return chain or "Task này không phụ thuộc việc nào."

    def get_document(i):
        if i["doctype"] not in READABLE_DOCTYPES:
            raise ToolRejected(f"Không được đọc doctype {i['doctype']}. Được đọc: {sorted(READABLE_DOCTYPES)}")
        try:
            d = erp.get_doc(i["doctype"], i["name"])
        except ErpError as e:
            raise ToolRejected(str(e))
        out = {k: d[k] for k in DOC_FIELDS if d.get(k) not in (None, "")}
        if d.get("items"):
            out["items"] = [{k: it.get(k) for k in ITEM_FIELDS if it.get(k) is not None}
                            for it in d["items"][:20]]
        out["link"] = erp.link(i["doctype"], d["name"])
        return out

    def find_documents(i):
        if i["doctype"] not in READABLE_DOCTYPES:
            raise ToolRejected(f"Không được đọc doctype {i['doctype']}")
        try:
            rows = erp.get_list(i["doctype"], filters=[["project", "=", i["project"]]],
                                fields=["name", "docstatus", "modified"], order_by="modified desc", limit=20)
        except ErpError as e:
            raise ToolRejected(f"{i['doctype']} không lọc được theo project: {e}")
        return rows or f"Không có {i['doctype']} nào gắn project {i['project']}"

    def list_alerts(i):
        return erp.get_list("Nx Project Alert",
                            filters=[["project", "=", i["project"]], ["status", "in", ["Mới", "Đã xem"]]],
                            fields=["name", "task", "severity", "rule_code", "facts", "status", "root_cause"],
                            order_by="creation desc", limit=30)

    def kb_list(_):
        return [{"tài_liệu": p.stem, "dòng_đầu": p.read_text(encoding="utf-8").splitlines()[0]}
                for p in sorted(KB_DIR.glob("*.md"))]

    def kb_read(i):
        path = (KB_DIR / f"{i['name']}.md").resolve()
        if path.parent != KB_DIR.resolve() or not path.exists():
            raise ToolRejected(f"Không có tài liệu {i['name']}. Dùng kb_list để xem danh sách.")
        return path.read_text(encoding="utf-8")

    s = {"type": "string"}
    return {
        "get_project_overview": Tool(
            "get_project_overview",
            "Tình hình dự án do engine tính: RAG, % kế hoạch/thực tế, SPI, dự báo kết thúc, đường găng, "
            "cảnh báo theo quy tắc, lỗi dữ liệu.", {"project": s}, get_project_overview),
        "get_task": Tool("get_task", "Chi tiết một Task: ngày, tiến độ, vướng mắc, phụ thuộc, "
                         "chứng từ bằng chứng, 5 ghi chú gần nhất.", {"task": s}, get_task),
        "get_predecessors": Tool("get_predecessors", "Chuỗi các việc phải xong trước Task này (tối đa 5 tầng), "
                                 "kèm trạng thái và chứng từ bằng chứng của từng việc.", {"task": s},
                                 get_predecessors),
        "get_document": Tool("get_document", "Đọc trạng thái một chứng từ ERP (chỉ đọc, không có đơn giá). "
                             "VD doctype='Purchase Order', name='PO-2611-0042'.",
                             {"doctype": s, "name": s}, get_document),
        "find_documents": Tool("find_documents", "Liệt kê tối đa 20 chứng từ của một doctype có gắn project.",
                               {"doctype": s, "project": s}, find_documents),
        "list_alerts": Tool("list_alerts", "Các Nx Project Alert đang mở của dự án.", {"project": s}, list_alerts),
        "kb_list": Tool("kb_list", "Danh sách tài liệu trong kho tri thức (WBS mẫu, lưu đồ ERP, bản đồ "
                        "chứng từ bằng chứng).", {}, kb_list),
        "kb_read": Tool("kb_read", "Đọc một tài liệu trong kho tri thức theo tên lấy từ kb_list.",
                        {"name": s}, kb_read),
    }


def pick(tools: dict[str, Tool], *names: str) -> list[Tool]:
    return [tools[n] for n in names]


def kb_dir() -> Path:
    return KB_DIR
