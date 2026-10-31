"""Client REST cho ERP EuP (Frappe/ERPNext), có chế độ chạy thử và danh sách field được ghi."""

from __future__ import annotations

import json
import logging
from urllib.parse import quote

import requests

log = logging.getLogger("eup_pm.erp")

# Agent chỉ được ghi vào các doctype và field dưới đây. None = được ghi mọi field của doctype đó.
# Chứng từ nghiệp vụ (Purchase Order, Sales Order, Payment Entry...) không có ở đây nên luôn chỉ đọc.
WRITE_ALLOWLIST: dict[str, set[str] | None] = {
    "Task": {
        "status", "progress", "completed_on", "custom_forecast_end", "custom_blocker",
        "custom_last_checkin", "custom_progress_source", "custom_evidence",
    },
    "Project": {"custom_rag", "custom_spi", "custom_forecast_end", "custom_last_agent_run"},
    "Comment": None,
    "Nx Project Alert": None,
    "Nx Project Status Report": None,
}
# Chỉ lệnh setup-erp được ghi các doctype này.
SCHEMA_DOCTYPES = {"DocType", "Custom Field", "Role"}


class ErpError(RuntimeError):
    pass


class ErpClient:
    def __init__(self, base_url: str, api_key: str, api_secret: str,
                 dry_run: bool = True, allow_schema: bool = False, timeout: int = 30):
        if not base_url or not api_key or not api_secret:
            raise ErpError("Thiếu ERP_URL, ERP_API_KEY hoặc ERP_API_SECRET trong .env")
        self.base_url = base_url
        self.dry_run = dry_run
        self.allow_schema = allow_schema
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {api_key}:{api_secret}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    # ---------- đọc ----------

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        r = self.session.request(method, url, timeout=self.timeout, **kwargs)
        if r.status_code >= 400:
            raise ErpError(f"{method} {path} -> HTTP {r.status_code}: {_error_text(r)}")
        return r.json()

    def get_list(self, doctype: str, filters=None, fields=None, order_by: str | None = None,
                 limit: int = 0) -> list[dict]:
        params = {
            "fields": json.dumps(fields or ["name"]),
            "limit_page_length": limit,
        }
        if filters:
            params["filters"] = json.dumps(filters)
        if order_by:
            params["order_by"] = order_by
        return self._request("GET", f"/api/resource/{quote(doctype)}", params=params)["data"]

    def get_doc(self, doctype: str, name: str) -> dict:
        return self._request("GET", f"/api/resource/{quote(doctype)}/{quote(name, safe='')}")["data"]

    def exists(self, doctype: str, name: str) -> bool:
        try:
            self.get_doc(doctype, name)
            return True
        except ErpError as e:
            if "HTTP 404" in str(e):
                return False
            raise

    def whoami(self) -> str:
        return self._request("GET", "/api/method/frappe.auth.get_logged_user")["message"]

    # ---------- ghi (có kiểm soát) ----------

    def _check_write(self, doctype: str, data: dict):
        if doctype in SCHEMA_DOCTYPES:
            if not self.allow_schema:
                raise ErpError(f"Không được ghi {doctype} ngoài lệnh setup-erp")
            return
        if doctype not in WRITE_ALLOWLIST:
            raise ErpError(f"Agent không có quyền ghi doctype {doctype}")
        allowed = WRITE_ALLOWLIST[doctype]
        if allowed is not None:
            bad = set(data) - allowed
            if bad:
                raise ErpError(f"Agent không được ghi các field {sorted(bad)} của {doctype}")

    def insert(self, doctype: str, data: dict) -> dict:
        self._check_write(doctype, data)
        if self.dry_run:
            log.info("[CHẠY THỬ] tạo %s: %s", doctype, _short(data))
            return {"name": f"(chạy thử) {doctype}", **data}
        return self._request("POST", f"/api/resource/{quote(doctype)}", json=data)["data"]

    def update(self, doctype: str, name: str, data: dict) -> dict:
        self._check_write(doctype, data)
        if self.dry_run:
            log.info("[CHẠY THỬ] sửa %s %s: %s", doctype, name, _short(data))
            return {"name": name, **data}
        return self._request("PUT", f"/api/resource/{quote(doctype)}/{quote(name, safe='')}",
                             json=data)["data"]

    def add_comment(self, doctype: str, name: str, text: str) -> dict:
        return self.insert("Comment", {
            "comment_type": "Comment",
            "reference_doctype": doctype,
            "reference_name": name,
            "content": f"[AI-Agent] {text}",
        })

    def send_email(self, recipients: list[str], subject: str, html: str,
                   ref_doctype: str | None = None, ref_name: str | None = None):
        """Gửi email qua Email Account mặc định của ERP."""
        if self.dry_run:
            log.info("[CHẠY THỬ] gửi email tới %s: %s", ", ".join(recipients), subject)
            return None
        payload = {
            "recipients": ", ".join(recipients),
            "subject": subject,
            "content": html,
            "send_email": 1,
        }
        if ref_doctype and ref_name:
            payload.update({"doctype": ref_doctype, "name": ref_name})
        return self._request("POST", "/api/method/frappe.core.doctype.communication.email.make",
                             json=payload)

    def link(self, doctype: str, name: str) -> str:
        slug = doctype.lower().replace(" ", "-")
        return f"{self.base_url}/app/{slug}/{quote(name, safe='')}"


def _error_text(r: requests.Response) -> str:
    try:
        body = r.json()
    except ValueError:
        return r.text[:300]
    msg = body.get("exception") or body.get("message") or body.get("_server_messages") or body
    return str(msg)[:300]


def _short(data: dict) -> str:
    s = json.dumps(data, ensure_ascii=False, default=str)
    return s if len(s) < 400 else s[:400] + "…"
