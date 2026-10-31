"""ERP giả trong bộ nhớ để chạy thử toàn bộ luồng mà không cần erp.eup.vn."""

from __future__ import annotations

from datetime import date, timedelta

from eup_pm.erp import ErpClient, ErpError


class FakeErp(ErpClient):
    def __init__(self, docs: dict[str, dict[str, dict]]):
        super().__init__("https://erp.example", "k", "s", dry_run=True)
        self.docs = docs
        self.writes: list[tuple] = []
        self.emails: list[tuple] = []

    def get_doc(self, doctype, name):
        try:
            return dict(self.docs[doctype][name])
        except KeyError:
            raise ErpError(f"GET {doctype}/{name} -> HTTP 404: not found")

    def get_list(self, doctype, filters=None, fields=None, order_by=None, limit=0):
        out = []
        for d in self.docs.get(doctype, {}).values():
            if all(_match(d, f) for f in filters or []):
                out.append({k: d.get(k) for k in fields or ["name"]})
        return out

    def insert(self, doctype, data):
        self._check_write(doctype, data)
        self.writes.append(("insert", doctype, data))
        return {"name": f"NEW-{doctype}-{len(self.writes)}", **data}

    def update(self, doctype, name, data):
        self._check_write(doctype, data)
        self.writes.append(("update", doctype, name, data))
        return {"name": name, **data}

    def send_email(self, recipients, subject, html, ref_doctype=None, ref_name=None):
        self.emails.append((recipients, subject))


def _match(d, f):
    field, op, val = f
    v = d.get(field)
    if op == "=":
        return v == val
    if op == "in":
        return v in val
    if op == ">=":
        return v is not None and str(v) >= str(val)
    raise NotImplementedError(op)


def sample_docs(today: date) -> dict:
    """Dự án mẫu 'Lắp dây chuyền ép số 3' với 5 việc, 1 mốc, 2 chứng từ bằng chứng."""
    d = lambda n: (today + timedelta(days=n)).isoformat()  # noqa: E731
    task = lambda name, subject, start, end, **kw: {  # noqa: E731
        "name": name, "subject": subject, "project": "PROJ-0001", "status": "Open", "progress": 0,
        "exp_start_date": d(start), "exp_end_date": d(end),
        "custom_baseline_start": d(start), "custom_baseline_end": d(end),
        "modified": d(-1) + " 10:00:00", "_assign": '["kythuat@eup.vn"]', "depends_on": [],
        **kw,
    }
    return {
        "Project": {"PROJ-0001": {
            "name": "PROJ-0001", "project_name": "Lắp dây chuyền ép số 3", "status": "Open",
            "company": "EUP YB", "expected_end_date": d(20), "custom_baseline_end": d(20),
            "custom_agent_enabled": 1, "custom_pmo_owner": "pm@eup.vn", "custom_eup_project_type": "DT",
            "custom_report_emails": "bgd@eup.vn",
        }},
        "Company": {"EUP YB": {"name": "EUP YB", "default_holiday_list": "HL-2026"}},
        "Holiday List": {"HL-2026": {"name": "HL-2026", "holidays": []}},
        "Task": {
            "T1": task("T1", "Đặt mua máy ép", -10, -3, status="Working", progress=95,
                       custom_evidence=[{"name": "ev1", "reference_doctype": "Purchase Order",
                                         "reference_name": "PO-2611-0042", "condition_field": "workflow_state",
                                         "required_value": "Approved"}]),
            "T2": task("T2", "Hàng về kho", -2, 5, status="Working", progress=40,
                       custom_forecast_end=d(9), custom_blocker="Tờ khai đang chờ kiểm hóa",
                       depends_on=[{"task": "T1"}]),
            "T3": task("T3", "Lắp đặt khung máy", 6, 12, depends_on=[{"task": "T2"}]),
            "T4": task("T4", "Đào tạo vận hành", 6, 9, depends_on=[{"task": "T2"}]),
            "T5": task("T5", "Chạy thử không tải", 13, 15, is_milestone=1,
                       depends_on=[{"task": "T3"}, {"task": "T4"}]),
        },
        "Purchase Order": {"PO-2611-0042": {"name": "PO-2611-0042", "docstatus": 1,
                                            "workflow_state": "Approved", "status": "To Receive and Bill"}},
        "Nx Project Alert": {},
        "Nx Project Status Report": {},
    }
