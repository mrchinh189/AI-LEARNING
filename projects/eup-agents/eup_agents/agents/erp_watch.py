"""A3 — Giám sát chứng từ ERP (chỉ đọc chứng từ, chỉ tạo Task nháp).

Luật bật trong pilot:
  R1  Chứng từ Nháp (docstatus = 0) quá N ngày
  R3  Phiếu nhập đã Submit quá N ngày nhưng chưa lập đủ hóa đơn mua (per_billed < 100)
Ngưỡng và danh sách doctype nằm trong config/org.json → "erp_watch".
"""

from datetime import timedelta

from ..config import settings
from .common import UNCONFIRMED, company_filter, today

DEFAULT_RULES = {
    "draft_days": 3,
    "draft_doctypes": ["Purchase Order", "Sales Order", "Purchase Invoice", "Sales Invoice", "Journal Entry"],
    "receipt_unbilled_days": 7,
    "task_due_days": 2,
    "department": None,
}


def _existing_refs(erp) -> set[str]:
    """Chứng từ đã có Task đang mở → không tạo trùng."""
    rows = erp.get_list("Task", [["eup_source", "=", "ERP tự sinh"], ["status", "not in", ["Completed", "Cancelled"]]],
                        ["eup_source_ref"], limit=5000)
    return {r["eup_source_ref"] for r in rows if r.get("eup_source_ref")}


def findings(erp, rules: dict) -> list[dict]:
    d0 = today()
    out = []
    scope = company_filter()
    cutoff = str(d0 - timedelta(days=rules["draft_days"]))
    for dt in rules["draft_doctypes"]:
        for r in erp.get_list(dt, [["docstatus", "=", 0], ["creation", "<", cutoff], *scope],
                              ["name", "owner", "company", "creation"], limit=500):
            out.append({"rule": "R1", "doctype": dt, "doc": r,
                        "subject": f"Hoàn tất hoặc hủy {dt} nháp {r['name']} (tạo {str(r['creation'])[:10]})",
                        "owner": r["owner"]})
    cutoff = str(d0 - timedelta(days=rules["receipt_unbilled_days"]))
    for r in erp.get_list("Purchase Receipt", [["docstatus", "=", 1], ["per_billed", "<", 100],
                                                ["posting_date", "<", cutoff], *scope],
                          ["name", "owner", "company", "posting_date", "supplier", "per_billed"], limit=500):
        out.append({"rule": "R3", "doctype": "Purchase Receipt", "doc": r,
                    "subject": f"Lập hóa đơn mua cho phiếu nhập {r['name']} ({r.get('supplier')}, "
                               f"đã lập {r.get('per_billed', 0):.0f}%)",
                    "owner": r["owner"]})
    return out


def run(erp) -> dict:
    erp = erp.as_agent("A3-giam-sat-erp")
    rules = {**DEFAULT_RULES, **(settings.org().get("erp_watch") or {})}
    seen = _existing_refs(erp)
    created = skipped = 0
    for f in findings(erp, rules):
        ref = f"{f['doctype']}::{f['doc']['name']}"
        if ref in seen:
            skipped += 1
            continue
        res = erp.create_task({
            "subject": f["subject"][:140],
            "company": f["doc"].get("company"),
            "department": rules.get("department"),
            "priority": "Medium",
            "exp_end_date": str(today() + timedelta(days=rules["task_due_days"])),
            "description": f"Luật {f['rule']} · {settings.erp_url}/app/"
                           f"{f['doctype'].lower().replace(' ', '-')}/{f['doc']['name']}",
            "eup_source": "ERP tự sinh",
            "eup_source_ref": ref,
            "eup_confirm_state": UNCONFIRMED,
            "eup_agent_created": 1,
        })
        if f.get("owner") and res.get("name"):
            erp.assign_task(res["name"], [f["owner"]])
        seen.add(ref)
        created += 1
    return {"created": created, "skipped_existing": skipped}
