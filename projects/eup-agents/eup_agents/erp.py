"""Client gọi REST API của Frappe/ERPNext (erp.eup.vn).

Đọc: /api/resource/<Doctype>. Ghi: luôn qua guard.check(); khi DRY_RUN thì không gửi gì lên ERP.
"""

import json
import logging
from typing import Any

import requests

from . import guard
from .config import Settings, settings as default_settings

log = logging.getLogger("eup_agents.erp")


class ERPError(RuntimeError):
    pass


class ERPClient:
    def __init__(self, cfg: Settings = default_settings, agent: str = "system"):
        self.cfg = cfg
        self.agent = agent
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"token {cfg.erp_api_key}:{cfg.erp_api_secret}",
            "Accept": "application/json",
        })

    def as_agent(self, agent: str) -> "ERPClient":
        c = ERPClient(self.cfg, agent)
        c.s = self.s
        return c

    # ---------- đọc ----------
    def _req(self, method: str, path: str, **kw) -> Any:
        try:
            r = self.s.request(method, self.cfg.erp_url + path, timeout=30, **kw)
        except requests.RequestException as e:
            raise ERPError(f"Không kết nối được {self.cfg.erp_url}: {type(e).__name__}") from e
        if r.status_code in (401, 403):
            raise ERPError(f"{method} {path} -> HTTP {r.status_code}: API key/secret sai hoặc user thiếu quyền")
        if r.status_code >= 400:
            raise ERPError(f"{method} {path} -> HTTP {r.status_code}: {r.text[:300]}")
        return r.json().get("data", r.json().get("message"))

    def ping(self) -> str:
        """Trả về user đang đăng nhập bằng API key — dùng để kiểm tra kết nối."""
        return self._req("GET", "/api/method/frappe.auth.get_logged_user")

    def get_list(self, doctype: str, filters: list | None = None, fields: list | None = None,
                 order_by: str | None = None, limit: int = 500) -> list[dict]:
        params = {
            "filters": json.dumps(filters or []),
            "fields": json.dumps(fields or ["name"]),
            "limit_page_length": limit,
        }
        if order_by:
            params["order_by"] = order_by
        return self._req("GET", f"/api/resource/{doctype}", params=params)

    def get_doc(self, doctype: str, name: str) -> dict:
        return self._req("GET", f"/api/resource/{doctype}/{requests.utils.quote(name, safe='')}")

    def exists(self, doctype: str, name: str) -> bool:
        try:
            self.get_doc(doctype, name)
            return True
        except ERPError:
            return False

    # ---------- ghi (qua Lớp Kiểm soát) ----------
    def _write(self, doctype: str, action: str, target: str, payload: dict, send) -> dict:
        guard.check(self.agent, doctype, action, payload)
        if self.cfg.dry_run:
            guard.record(self.agent, doctype, action, target, payload, "dry-run", True)
            print(f"[DRY-RUN] {self.agent}: {action} {doctype} {target} {json.dumps(payload, ensure_ascii=False)}")
            return {"name": f"DRY-{doctype}-{target}"}
        try:
            out = send()
        except ERPError as e:
            guard.record(self.agent, doctype, action, target, payload, f"error: {e}", False)
            raise
        guard.record(self.agent, doctype, action, target, payload, "ok", False)
        return out or {}

    def create_task(self, fields: dict) -> dict:
        body = {"doctype": "Task", **fields}
        return self._write("Task", "create", fields.get("subject", "")[:60], fields,
                           lambda: self._req("POST", "/api/resource/Task", json=body))

    def update_task(self, name: str, fields: dict) -> dict:
        return self._write("Task", "update", name, fields,
                           lambda: self._req("PUT", f"/api/resource/Task/{name}", json=fields))

    def assign_task(self, name: str, users: list[str]) -> dict:
        payload = {"doctype": "Task", "name": name, "assign_to": users}
        return self._write("Task", "assign", name, payload,
                           lambda: self._req("POST", "/api/method/frappe.desk.form.assign_to.add",
                                             json={**payload, "assign_to": json.dumps(users)}))

    def comment_task(self, name: str, text: str) -> dict:
        payload = {"comment_type": "Comment", "reference_doctype": "Task",
                   "reference_name": name, "content": text}
        return self._write("Comment", "create", name, payload,
                           lambda: self._req("POST", "/api/resource/Comment", json=payload))

    def bell(self, user: str, subject: str, body: str, ref_doctype: str | None = None,
             ref_name: str | None = None) -> dict:
        """Thông báo chuông trong ERP (Notification Log)."""
        payload = {"for_user": user, "subject": subject, "email_content": body, "type": "Alert",
                   "document_type": ref_doctype, "document_name": ref_name}
        return self._write("Notification Log", "create", user, payload,
                           lambda: self._req("POST", "/api/resource/Notification Log", json=payload))
