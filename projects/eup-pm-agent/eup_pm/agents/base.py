"""Khung chung cho mọi agent: vòng lặp tool-use với Claude, lớp policy, ngân sách, audit log.

Mỗi agent = system prompt + bộ tool riêng + một tool "nộp kết quả" (final tool).
Vòng lặp: gọi Claude → chạy các tool Claude yêu cầu → trả kết quả → lặp lại,
cho tới khi Claude gọi final tool hợp lệ, hoặc hết lượt / hết ngân sách.

Viết vòng lặp tay (thay vì tool runner của SDK) để kiểm soát 3 thứ ngay tại đây:
policy cho từng tool, ngân sách token, và nhật ký audit của mọi lần gọi tool.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("eup_pm.agents")


class ToolRejected(Exception):
    """Tool từ chối yêu cầu (sai quyền, sai dữ liệu). Nội dung được trả lại cho Claude để tự sửa."""


@dataclass
class Tool:
    name: str
    description: str
    properties: dict
    handler: Callable[[dict], Any]
    final: bool = False          # gọi tool này hợp lệ = agent hoàn thành
    writes: bool = False         # tool có ghi ERP / gửi tin (để audit)

    def spec(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "strict": True,
            "input_schema": {
                "type": "object",
                "properties": self.properties,
                "required": list(self.properties),
                "additionalProperties": False,
            },
        }


@dataclass
class AgentResult:
    agent: str
    run_id: str
    ok: bool
    final: Any = None
    text: str = ""
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    error: str = ""
    tool_calls: list[dict] = field(default_factory=list)


class Audit:
    """Ghi mỗi sự kiện của agent thành 1 dòng JSON trong logs/audit-YYYY-MM-DD.jsonl."""

    def __init__(self, log_dir: Path | None):
        self.log_dir = log_dir

    def write(self, **event):
        if not self.log_dir:
            return
        event["ts"] = datetime.now().isoformat(timespec="seconds")
        path = self.log_dir / f"audit-{datetime.now():%Y-%m-%d}.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


class Agent:
    name = "agent"
    system_prompt = ""

    def __init__(self, llm: Callable[..., Any], tools: list[Tool], *, max_turns: int = 12,
                 max_tokens_per_run: int = 300_000, effort: str = "medium",
                 audit: Audit | None = None):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.max_turns = max_turns
        self.max_tokens_per_run = max_tokens_per_run
        self.effort = effort
        self.audit = audit or Audit(None)
        self.seen: list[str] = []   # mọi dữ liệu agent đã nhận, dùng để kiểm tra con số

    # ------------------------------------------------------------------ chạy

    def run(self, task: str) -> AgentResult:
        run_id = uuid.uuid4().hex[:12]
        res = AgentResult(agent=self.name, run_id=run_id, ok=False)
        self.seen = [task]
        messages: list[dict] = [{"role": "user", "content": task}]
        specs = [t.spec() for t in self.tools.values()]
        self.audit.write(agent=self.name, run_id=run_id, event="start", task=task[:2000])
        nudged = False

        while res.turns < self.max_turns:
            res.turns += 1
            response = self.llm(
                system=self.system_prompt,
                messages=messages,
                tools=specs,
                max_tokens=16000,
                output_config={"effort": self.effort},
            )
            res.input_tokens += response.usage.input_tokens
            res.output_tokens += response.usage.output_tokens
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                res.error = "Claude từ chối thực hiện yêu cầu"
                break
            if response.stop_reason == "pause_turn":
                continue

            calls = [b for b in response.content if b.type == "tool_use"]
            texts = [b.text for b in response.content if b.type == "text"]
            if texts:
                res.text = "\n".join(texts).strip()

            if not calls:
                if self._has_final_tool() and not nudged:
                    # Agent dừng mà chưa nộp kết quả: nhắc 1 lần.
                    nudged = True
                    messages.append({"role": "user", "content":
                                     "Bạn chưa nộp kết quả. Hãy gọi tool nộp kết quả theo hướng dẫn."})
                    continue
                res.ok = not self._has_final_tool()
                if not res.ok:
                    res.error = "Agent dừng mà không nộp kết quả"
                break

            results, finished = [], False
            for call in calls:
                content, is_error, done = self._execute(call, res)
                results.append({"type": "tool_result", "tool_use_id": call.id,
                                "content": content, **({"is_error": True} if is_error else {})})
                finished = finished or done
            messages.append({"role": "user", "content": results})

            if finished:
                res.ok = True
                break
            if res.input_tokens + res.output_tokens > self.max_tokens_per_run:
                res.error = "Hết ngân sách token của phiên chạy"
                break
        else:
            res.error = res.error or f"Hết {self.max_turns} lượt mà chưa xong"

        self.audit.write(agent=self.name, run_id=run_id, event="end", ok=res.ok, error=res.error,
                         turns=res.turns, input_tokens=res.input_tokens, output_tokens=res.output_tokens)
        log.info("[%s] run %s: %s sau %d lượt (%d in / %d out tokens)%s", self.name, run_id,
                 "xong" if res.ok else "KHÔNG xong", res.turns, res.input_tokens, res.output_tokens,
                 f" — {res.error}" if res.error else "")
        return res

    def _has_final_tool(self) -> bool:
        return any(t.final for t in self.tools.values())

    def _execute(self, call, res: AgentResult) -> tuple[str, bool, bool]:
        tool = self.tools.get(call.name)
        entry = {"tool": call.name, "input": call.input}
        if tool is None:
            out, is_error, done = f"Không có tool tên {call.name}", True, False
        else:
            try:
                value = tool.handler(dict(call.input))
                out = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
                is_error, done = False, tool.final
            except ToolRejected as e:
                out, is_error, done = f"Bị từ chối: {e}", True, False
            except Exception as e:  # lỗi ERP, lỗi mạng: báo cho Claude, không làm sập vòng lặp
                log.exception("[%s] tool %s lỗi", self.name, call.name)
                out, is_error, done = f"Lỗi khi chạy tool: {e}", True, False
        if tool is not None and tool.final and done:
            res.final = call.input
        if not is_error and tool is not None and not tool.final:
            self.seen.append(out)
        entry.update(ok=not is_error, output=out[:3000])
        res.tool_calls.append(entry)
        self.audit.write(agent=self.name, run_id=res.run_id, event="tool", writes=bool(tool and tool.writes),
                         **entry)
        return out, is_error, done

    # ------------------------------------------------------------------ kiểm tra con số

    def check_numbers(self, *texts: str) -> None:
        """Từ chối kết quả nếu có con số không xuất hiện trong dữ liệu agent đã nhận."""
        unknown = unknown_numbers(" ".join(texts), "\n".join(self.seen))
        if unknown:
            raise ToolRejected(
                "các con số sau không có trong dữ liệu đã tra cứu: " + ", ".join(unknown)
                + ". Bỏ chúng đi, hoặc ghi [CẦN DỮ LIỆU] thay cho con số, rồi nộp lại.")


_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def unknown_numbers(text: str, source: str | dict) -> list[str]:
    """Các con số có trong `text` mà không có ở đâu trong `source`. Cho phép số đếm nhỏ (≤ 10)."""
    if not isinstance(source, str):
        source = json.dumps(source, ensure_ascii=False, default=str)
    known = set(_NUM.findall(source))
    for k in list(known):
        known.update(re.split(r"[.,/\-]", k))
    for iso in re.findall(r"\d{4}-\d{2}-\d{2}", source):  # 2026-11-12 -> 12/11/2026, 12/11
        y, m, d = iso.split("-")
        known.update({f"{d}/{m}/{y}", f"{d}/{m}", d, m, y})
    out = []
    for n in _NUM.findall(text):
        if n in known or (n.isdigit() and int(n) <= 10):
            continue
        out.append(n)
    return sorted(set(out))


def make_llm(settings, model: str | None = None, fallbacks: str | None = None) -> Callable[..., Any]:
    """Tạo hàm gọi Claude theo cấu hình .env. Test thay hàm này bằng LLM giả."""
    import anthropic

    model = model or settings.model
    fallbacks = fallbacks or settings.fallbacks
    if not model:
        raise RuntimeError("Chưa đặt EUP_AGENT_MODEL trong .env")
    client = anthropic.Anthropic()

    def call(**kwargs):
        try:
            if fallbacks == "default":
                return client.beta.messages.create(
                    model=model, betas=["server-side-fallback-2026-07-01"],
                    fallbacks="default", **kwargs)
            return client.messages.create(model=model, **kwargs)
        except anthropic.RateLimitError:
            log.warning("Claude API: vượt giới hạn, SDK đã tự thử lại nhưng vẫn lỗi")
            raise

    return call


def llm_for_agent(settings, agent: str) -> Callable[..., Any]:
    """Model riêng cho từng agent nếu .env có EUP_AGENT_MODEL_<AGENT> (VD EUP_AGENT_MODEL_TRACKER)."""
    import os

    key = agent.upper()
    override = os.getenv(f"EUP_AGENT_MODEL_{key}")
    if not override:
        return make_llm(settings)
    return make_llm(settings, override, os.getenv(f"EUP_AGENT_FALLBACKS_{key}", "off"))
