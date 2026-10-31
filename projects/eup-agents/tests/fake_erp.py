"""ERP giả lập trong bộ nhớ, thay cho erp.eup.vn khi chạy test."""

import json
from urllib.parse import unquote

from eup_agents.erp import ERPClient, ERPError


def _match(row: dict, flt: list) -> bool:
    field, op, val = flt
    v = row.get(field)
    if op == "=":
        return v == val
    if op == "in":
        return v in val
    if op == "not in":
        return v not in val
    if v is None:
        return False
    if op == "<":
        return str(v) < str(val) if isinstance(val, str) else v < val
    if op == ">=":
        return str(v) >= str(val) if isinstance(val, str) else v >= val
    raise NotImplementedError(op)


class FakeERP(ERPClient):
    def __init__(self, cfg, db: dict[str, list[dict]], agent: str = "test"):
        super().__init__(cfg, agent)
        self.db = db
        self.calls: list[tuple] = []

    def as_agent(self, agent):
        c = FakeERP(self.cfg, self.db, agent)
        c.calls = self.calls
        return c

    def _req(self, method, path, **kw):
        self.calls.append((method, path, kw.get("json")))
        if path == "/api/method/frappe.auth.get_logged_user":
            return "agent@eup.vn"
        if path == "/api/method/frappe.desk.form.assign_to.add":
            body = kw["json"]
            task = self._find("Task", body["name"])
            task["_assign"] = body["assign_to"]
            return {}
        parts = path.removeprefix("/api/resource/").split("/")
        doctype = unquote(parts[0])
        rows = self.db.setdefault(doctype, [])
        if method == "GET" and len(parts) == 1:
            filters = json.loads(kw["params"]["filters"])
            return [dict(r) for r in rows if all(_match(r, f) for f in filters)]
        if method == "GET":
            return self._find(doctype, unquote(parts[1]))
        if method == "POST":
            doc = {k: v for k, v in kw["json"].items() if k != "doctype"}
            doc.setdefault("name", f"{doctype.upper()[:4]}-{len(rows) + 1:04d}")
            rows.append(doc)
            return doc
        if method == "PUT":
            doc = self._find(doctype, parts[1])
            doc.update(kw["json"])
            return doc
        raise NotImplementedError(method)

    def _find(self, doctype, name):
        for r in self.db.get(doctype, []):
            if r.get("name") == name:
                return r
        raise ERPError(f"{doctype} {name} không tồn tại")
