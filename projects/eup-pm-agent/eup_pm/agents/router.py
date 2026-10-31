"""Định tuyến sự kiện tới agent phù hợp. Quy tắc cố định, không dùng LLM.

Sự kiện là JSON, nhận từ dòng lệnh hoặc từ webhook (server.py, VD n8n gọi vào):
  {"type": "reply",       "from": "a@eup.vn", "text": "..."}   → ③ Thu thập tiến độ
  {"type": "alert",       "alert": "ALERT-2611-0003"}           → ⑤ Rủi ro
  {"type": "new_project", "project": "PROJ-0007"}               → ② Lập kế hoạch
  {"type": "ask",         "from": "pm@eup.vn", "text": "..."}   → ① Điều phối
"""

from __future__ import annotations

import html
import logging
from datetime import date

from ..config import Settings
from ..erp import ErpClient
from .base import Audit
from .tools import Ctx

log = logging.getLogger("eup_pm.router")


class Team:
    """Đội agent dùng chung một ERP client, một LLM, một audit log."""

    def __init__(self, erp: ErpClient, settings: Settings, llm, today: date | None = None,
                 llm_by_agent: dict | None = None):
        self.ctx = Ctx(erp, settings, today or date.today())
        self.llm = llm
        self.llm_by_agent = llm_by_agent or {}
        self.cfg = settings.rules.get("agents", {})
        self.audit = Audit(settings.log_dir)

    def enabled(self, name: str) -> bool:
        return self.cfg.get(name, {}).get("enabled", True)

    def handle(self, event: dict) -> dict:
        kind = event.get("type")
        log.info("Sự kiện %s", kind)
        if kind == "reply":
            from .tracker import handle_reply
            self._need("tracker")
            return handle_reply(self.ctx, self._llm("tracker"), self.cfg.get("tracker", {}), self.audit,
                                event["from"], event["text"])
        if kind == "alert":
            from .risk import analyse_alert
            self._need("risk")
            alert = self.ctx.erp.get_doc("Nx Project Alert", event["alert"])
            r = analyse_alert(self.ctx, self._llm("risk"), self.cfg.get("risk", {}), self.audit, alert)
            return {"ok": r.ok, "error": r.error, "analysis": r.final}
        if kind == "new_project":
            from .planner import make_plan
            self._need("planner")
            r, out = make_plan(self.ctx, self._llm("planner"), self.cfg.get("planner", {}), self.audit, event["project"])
            return {"ok": r.ok, "error": r.error, **out}
        if kind == "ask":
            from .orchestrator import ask
            self._need("orchestrator")
            answer = ask(self.ctx, self.llm, self.cfg, self.audit, event["text"], event.get("from", ""))
            if event.get("from") and event.get("reply_by_email"):
                self.ctx.erp.send_email([event["from"]], "Trả lời từ AI Agent PMO", f"<pre>{html.escape(answer)}</pre>")
            return {"ok": True, "answer": answer}
        raise ValueError(f"Không biết sự kiện loại {kind!r}")

    def analyse_new_red_alerts(self, project: str) -> int:
        """Gọi sau `daily`: Agent Rủi ro phân tích các cảnh báo Đỏ mới chưa có phân tích."""
        if not self.enabled("risk"):
            return 0
        from .risk import analyse_alert
        limit = self.cfg.get("risk", {}).get("max_alerts_per_run", 3)
        alerts = self.ctx.erp.get_list("Nx Project Alert", filters=[
            ["project", "=", project], ["severity", "=", "Đỏ"], ["status", "=", "Mới"],
            ["analysed_by_agent", "=", 0]], fields=["name", "project", "task", "severity", "rule_code", "facts"],
            order_by="creation asc", limit=limit)
        done = 0
        for a in alerts:
            if analyse_alert(self.ctx, self._llm("risk"), self.cfg.get("risk", {}), self.audit, a).ok:
                done += 1
        return done

    def _llm(self, name: str):
        return self.llm_by_agent.get(name, self.llm)

    def _need(self, name: str):
        if not self.enabled(name):
            raise RuntimeError(f"Agent {name} đang tắt trong config/rules.yaml (agents.{name}.enabled)")
