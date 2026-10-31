"""Webhook nhận sự kiện cho đội agent (VD n8n chuyển tin Zalo/email tới). Chỉ dùng thư viện chuẩn.

POST /event  với header  X-Agent-Token: <EUP_WEBHOOK_TOKEN>  và body JSON như router.py mô tả.
Mặc định chỉ nghe 127.0.0.1: n8n phải chạy cùng máy, hoặc đặt sau reverse proxy có HTTPS.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("eup_pm.server")


def serve(team_factory, host: str = "127.0.0.1", port: int = 8787):
    token = os.getenv("EUP_WEBHOOK_TOKEN", "")
    if len(token) < 24:
        raise RuntimeError("Đặt EUP_WEBHOOK_TOKEN (ít nhất 24 ký tự ngẫu nhiên) trong .env trước khi chạy serve")

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: dict):
            data = json.dumps(body, ensure_ascii=False, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._send(200, {"ok": True}) if self.path == "/health" else self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/event":
                return self._send(404, {"error": "not found"})
            if not hmac.compare_digest(self.headers.get("X-Agent-Token", ""), token):
                return self._send(401, {"error": "sai token"})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if n > 64_000:
                    return self._send(413, {"error": "quá lớn"})
                event = json.loads(self.rfile.read(n) or b"{}")
                result = team_factory().handle(event)
                self._send(200, result)
            except (ValueError, KeyError) as e:
                self._send(400, {"error": str(e)})
            except Exception as e:
                log.exception("Lỗi xử lý sự kiện")
                self._send(500, {"error": str(e)})

        def log_message(self, fmt, *args):
            log.info("%s %s", self.address_string(), fmt % args)

    log.info("Đội agent nghe sự kiện tại http://%s:%d/event", host, port)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
