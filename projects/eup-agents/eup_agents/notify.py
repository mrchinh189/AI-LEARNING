"""Gửi tin cho người dùng: in màn hình, chuyển qua webhook (n8n → email/chat), hoặc chuông ERP."""

import logging

import requests

from .config import settings

log = logging.getLogger("eup_agents.notify")


def send(erp, user: str, subject: str, body: str, ref: tuple[str, str] | None = None) -> None:
    backend = "console" if settings.dry_run else settings.notify_backend
    if backend == "console":
        print(f"\n===== TIN GỬI {user} =====\n{subject}\n{body}\n")
    elif backend == "webhook":
        r = requests.post(settings.notify_webhook_url, timeout=20,
                          json={"to": user, "subject": subject, "body": body,
                                "ref_doctype": ref[0] if ref else None, "ref_name": ref[1] if ref else None})
        r.raise_for_status()
    elif backend == "erp_bell":
        erp.bell(user, subject, body, *(ref or (None, None)))
    else:
        raise ValueError(f"NOTIFY_BACKEND không hợp lệ: {backend}")
