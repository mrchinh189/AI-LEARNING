"""Vòng lặp làm việc của một bot và cơ chế phối hợp giữa các bot.

Ánh xạ tới 6 nguyên tắc:
1. Bot quản lý nhận cả chuỗi việc  -> tool `delegate`, bot `chief_of_staff`
2. Bot có tên, vai trò, trí nhớ     -> system prompt dựng từ team.json + memory/ + logs/
3. Việc lặp lại thành quy trình     -> skill (`load_skill`, `save_skill`, `--skill`)
4. Tự kiểm tra trước khi nộp        -> rubric + grader, tự sửa tối đa N lần
5. Trưởng nhóm chỉ phân việc        -> `delegate_only` (không được cấp tool làm việc)
6. Trao quyền từng bước             -> tool rủi ro (publish/purchase/save_skill) phải được người duyệt
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from .config import BotConfig, Team
from .grader import grade
from .llm import LLM
from .store import Workspace

# Tool có tác động ra bên ngoài hoặc thay đổi quy trình của đội: luôn hỏi người.
APPROVAL_REQUIRED = {"publish", "purchase", "save_skill"}


# --------------------------------------------------------------------------
# Người vận hành (human in the loop)
# --------------------------------------------------------------------------
class Operator(Protocol):
    def approve(self, bot: str, action: str, details: str) -> bool: ...
    def answer(self, bot: str, question: str) -> str: ...


class CLIOperator:
    def approve(self, bot: str, action: str, details: str) -> bool:
        print(f"\n[DUYỆT] {bot} muốn thực hiện: {action}\n{details}")
        return input("Đồng ý? [y/N] ").strip().lower() in {"y", "yes", "c", "có"}

    def answer(self, bot: str, question: str) -> str:
        print(f"\n[HỎI] {bot}: {question}")
        return input("> ").strip() or "(người dùng không trả lời — tự quyết định hợp lý và ghi rõ giả định)"


@dataclass
class AutoOperator:
    """Dùng cho test/demo: tự trả lời mọi yêu cầu duyệt."""

    approve_all: bool = False
    reply: str = "(không có câu trả lời — tự quyết định hợp lý và ghi rõ giả định)"
    requests: list[tuple[str, str]] = field(default_factory=list)

    def approve(self, bot: str, action: str, details: str) -> bool:
        self.requests.append((bot, action))
        return self.approve_all

    def answer(self, bot: str, question: str) -> str:
        return self.reply


# --------------------------------------------------------------------------
# Định nghĩa tool
# --------------------------------------------------------------------------
def _schema(props: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


_S = {"type": "string"}

TOOL_SPECS: dict[str, dict[str, Any]] = {
    "remember": {
        "description": "Ghi một điều cần nhớ lâu dài vào trí nhớ của chính bạn (sở thích, văn phong, quy ước, bài học). Chỉ ghi điều sẽ còn hữu ích ở các việc sau.",
        "input_schema": _schema({"note": _S}),
    },
    "load_skill": {
        "description": "Nạp toàn văn một skill (quy trình chuẩn + tiêu chí đạt) theo tên. Nạp skill trước khi làm việc thuộc quy trình đó; tiêu chí đạt của skill sẽ được dùng để chấm bài bạn nộp.",
        "input_schema": _schema({"name": _S}),
    },
    "ask_human": {
        "description": "Hỏi người vận hành khi thiếu thông tin mà không thể tự suy ra hợp lý. Đừng hỏi những gì có thể tự quyết.",
        "input_schema": _schema({"question": _S}),
    },
    "delegate": {
        "description": "Giao một việc cho đồng đội và nhận lại kết quả. Viết `task` đầy đủ bối cảnh vì đồng đội không thấy cuộc hội thoại của bạn. `rubric`: tiêu chí đạt (để trống nếu không cần). `skill`: tên skill đồng đội nên áp dụng (để trống nếu không có).",
        "input_schema": _schema({"bot": _S, "task": _S, "rubric": _S, "skill": _S}),
    },
    "write_file": {
        "description": "Ghi file văn bản vào thư mục outputs/ (đường dẫn tương đối).",
        "input_schema": _schema({"path": _S, "content": _S}),
    },
    "read_file": {
        "description": "Đọc file văn bản trong thư mục outputs/.",
        "input_schema": _schema({"path": _S}),
    },
    "publish": {
        "description": "Đăng nội dung ra kênh bên ngoài (website, mạng xã hội, chợ online). Cần người vận hành duyệt. Bản prototype ghi vào outputs/published/ thay vì đăng thật.",
        "input_schema": _schema({"channel": _S, "title": _S, "content": _S}),
    },
    "purchase": {
        "description": "Đặt mua / thanh toán. Cần người vận hành duyệt. Luôn đề xuất phương án và giá trước. Bản prototype chỉ ghi sổ vào outputs/purchases.jsonl.",
        "input_schema": _schema({"item": _S, "vendor": _S, "price": {"type": "number"}, "currency": _S, "reason": _S}),
    },
    "save_skill": {
        "description": "Đóng gói một quy trình đã làm tốt thành skill tái sử dụng. Cần người vận hành duyệt. `content` là Markdown gồm các mục '## Mô tả', '## Các bước', '## Tiêu chí đạt'.",
        "input_schema": _schema({"name": _S, "content": _S}),
    },
}

WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}


@dataclass
class RunResult:
    bot: str
    text: str
    passed: bool | None = None  # None = không có rubric
    score: int | None = None
    attempts: int = 0
    tools_used: list[str] = field(default_factory=list)


class Runtime:
    def __init__(
        self,
        team: Team,
        workspace: Workspace,
        llm: LLM,
        operator: Operator,
        *,
        max_depth: int = 3,
        max_turns: int = 30,
        max_attempts: int = 3,
        verbose: bool = False,
    ):
        self.team = team
        self.ws = workspace
        self.llm = llm
        self.operator = operator
        self.max_depth = max_depth
        self.max_turns = max_turns
        self.max_attempts = max_attempts
        self.verbose = verbose

    # ---- Dựng ngữ cảnh -----------------------------------------------------
    def tool_names(self, bot: BotConfig) -> list[str]:
        names = ["remember", "load_skill", "ask_human"]
        if bot.delegates:
            names.append("delegate")
        names += [t for t in bot.tools if t in TOOL_SPECS and t not in names]
        return names

    def tools_for(self, bot: BotConfig) -> list[dict[str, Any]]:
        tools = [{"name": n, "strict": True, **TOOL_SPECS[n]} for n in self.tool_names(bot)]
        if "web_search" in bot.tools:
            tools.append(WEB_SEARCH_TOOL)
        return tools

    def system_prompt(self, bot: BotConfig) -> str:
        parts = [self.team.charter.strip(), f"## Danh tính\nTên: {bot.name} — {bot.title}\nVai trò: {bot.role}"]
        if bot.delegates:
            roster = "\n".join(
                f"- `{d}`: {self.team.bots[d].title} — {self.team.bots[d].role.split('.')[0]}." for d in bot.delegates
            )
            parts.append(f"## Đồng đội bạn có thể giao việc (tool `delegate`)\n{roster}")
        if bot.delegate_only:
            parts.append(
                "## Quy tắc cứng\nBạn KHÔNG tự làm phần việc chuyên môn. Hãy chia nhỏ, giao cho đồng đội "
                "kèm tiêu chí đạt, kiểm tra kết quả họ trả về, yêu cầu làm lại nếu chưa đạt, rồi tổng hợp."
            )
        skills = self.ws.list_skills()
        if skills:
            parts.append("## Skill có sẵn (tool `load_skill`)\n" + "\n".join(f"- `{s.name}`: {s.description}" for s in skills))
        parts.append("## Trí nhớ dài hạn của bạn\n" + (self.ws.memory(bot.name).strip() or "(trống)"))
        recent = self.ws.recent_logs(bot.name)
        if recent:
            lines = [f"- [{e['ts']}] {_short(e.get('task', ''), 120)} → {_short(e.get('result', ''), 160)}" for e in recent]
            parts.append("## Việc bạn làm gần đây (ở mọi dự án/phòng chat)\n" + "\n".join(lines))
        return "\n\n".join(parts)

    # ---- Vòng lặp chính ----------------------------------------------------
    def run(
        self,
        bot_name: str,
        task: str,
        *,
        rubric: str = "",
        skill: str = "",
        depth: int = 0,
        parent: str | None = None,
    ) -> RunResult:
        bot = self.team.get(bot_name)
        if skill:
            s = self.ws.get_skill(skill)
            if s is None:
                raise KeyError(f"Không có skill '{skill}'")
            task = f"{task}\n\n---\nÁp dụng skill `{s.name}`:\n\n{s.text}"
            rubric = rubric or s.rubric

        ctx = _RunContext(bot=bot, depth=depth, rubric=rubric)
        messages: list[dict[str, Any]] = [{"role": "user", "content": task}]
        system = self.system_prompt(bot)
        tools = self.tools_for(bot)
        result = RunResult(bot=bot.name, text="")
        self._say(depth, f"▶ {bot.name}: {_short(task, 100)}")

        for _ in range(self.max_turns):
            response = self.llm.create(
                bot=bot.name, system=system, messages=messages, tools=tools, effort=bot.effort
            )
            # Luôn nối nguyên response.content (kể cả thinking block) — chỉ thêm, không sửa lịch sử.
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                result.text = f"[{bot.name} từ chối yêu cầu này]"
                break
            if response.stop_reason == "pause_turn":
                continue

            tool_uses = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
            if response.stop_reason == "tool_use" and tool_uses:
                results = [self._execute(ctx, b) for b in tool_uses]
                messages.append({"role": "user", "content": results})
                continue

            text = "\n".join(b.text for b in response.content if getattr(b, "type", None) == "text").strip()
            if response.stop_reason == "max_tokens":
                text += "\n\n[cảnh báo: câu trả lời bị cắt do vượt max_tokens]"
            result.text = text

            if not ctx.rubric:
                break
            g = grade(self.llm, task=task, rubric=ctx.rubric, answer=text)
            result.attempts += 1
            result.passed, result.score = g.passed, g.score
            self._say(depth, f"  ✔ tự chấm {bot.name}: {'ĐẠT' if g.passed else 'CHƯA ĐẠT'} ({g.score}/10)")
            if g.passed or result.attempts >= self.max_attempts:
                break
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Bài tự kiểm tra chưa đạt (lần {result.attempts}/{self.max_attempts}, điểm {g.score}/10).\n"
                        f"Phản hồi của người chấm:\n{g.feedback}\n\n"
                        "Hãy sửa và nộp lại TOÀN BỘ bản hoàn chỉnh (không chỉ phần sửa)."
                    ),
                }
            )
        else:
            result.text = result.text or f"[{bot.name} dừng vì vượt {self.max_turns} lượt]"

        result.tools_used = ctx.tools_used
        self.ws.log(
            bot.name,
            {
                "parent": parent,
                "task": _short(task, 2000),
                "result": _short(result.text, 2000),
                "rubric": bool(ctx.rubric),
                "passed": result.passed,
                "score": result.score,
                "attempts": result.attempts,
                "tools": ctx.tools_used,
            },
        )
        return result

    # ---- Thực thi tool -----------------------------------------------------
    def _execute(self, ctx: "_RunContext", block: Any) -> dict[str, Any]:
        name, args = block.name, block.input if isinstance(block.input, dict) else {}
        ctx.tools_used.append(name)
        try:
            if name not in self.tool_names(ctx.bot):
                raise PermissionError(f"Bạn không được cấp tool '{name}'")
            if name in APPROVAL_REQUIRED:
                details = json.dumps(args, ensure_ascii=False, indent=2)
                if not self.operator.approve(ctx.bot.name, name, details):
                    return _tool_result(block.id, f"Người vận hành KHÔNG duyệt '{name}'. Không thực hiện. Hãy báo lại phương án và chờ chỉ dẫn.")
            content = getattr(self, f"_tool_{name}")(ctx, **args)
            return _tool_result(block.id, content)
        except Exception as exc:  # lỗi tool được trả lại cho model, không làm sập vòng lặp
            return _tool_result(block.id, f"Lỗi: {exc}", is_error=True)

    def _tool_remember(self, ctx, note: str) -> str:
        self.ws.remember(ctx.bot.name, note)
        return "Đã ghi nhớ."

    def _tool_load_skill(self, ctx, name: str) -> str:
        s = self.ws.get_skill(name)
        if s is None:
            raise KeyError(f"Không có skill '{name}'")
        if s.rubric and not ctx.rubric:
            ctx.rubric = s.rubric  # bài nộp cuối sẽ được chấm theo tiêu chí của skill
        return s.text

    def _tool_ask_human(self, ctx, question: str) -> str:
        return self.operator.answer(ctx.bot.name, question)

    def _tool_delegate(self, ctx, bot: str, task: str, rubric: str, skill: str) -> str:
        if bot not in ctx.bot.delegates:
            raise PermissionError(f"Bạn chỉ được giao việc cho: {', '.join(ctx.bot.delegates)}")
        if ctx.depth + 1 > self.max_depth:
            raise RuntimeError("Chuỗi giao việc quá sâu — hãy tự tổng hợp với những gì đang có")
        sub = self.run(bot, task, rubric=rubric, skill=skill, depth=ctx.depth + 1, parent=ctx.bot.name)
        return json.dumps(
            {"from": bot, "passed": sub.passed, "score": sub.score, "attempts": sub.attempts, "result": sub.text},
            ensure_ascii=False,
        )

    def _tool_write_file(self, ctx, path: str, content: str) -> str:
        p = self.ws.write_output(path, content)
        return f"Đã ghi {p.relative_to(self.ws.root)} ({len(content)} ký tự)"

    def _tool_read_file(self, ctx, path: str) -> str:
        return self.ws.read_output(path)

    def _tool_publish(self, ctx, channel: str, title: str, content: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "post"
        rel = f"published/{re.sub(r'[^a-z0-9-]+', '-', channel.lower())}/{time.strftime('%Y%m%d-%H%M%S')}-{slug}.md"
        self.ws.write_output(rel, f"# {title}\n\n{content}\n")
        return f"(Mô phỏng) Đã đăng lên {channel}: outputs/{rel}"

    def _tool_purchase(self, ctx, item: str, vendor: str, price: float, currency: str, reason: str) -> str:
        entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "bot": ctx.bot.name, "item": item, "vendor": vendor,
                 "price": price, "currency": currency, "reason": reason}
        path = self.ws.output_path("purchases.jsonl")
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return f"(Mô phỏng) Đã đặt mua {item} từ {vendor} giá {price} {currency}"

    def _tool_save_skill(self, ctx, name: str, content: str) -> str:
        p = self.ws.save_skill(name, content)
        return f"Đã lưu skill {name} vào {p.relative_to(self.ws.root)}"

    def _say(self, depth: int, msg: str) -> None:
        if self.verbose:
            print("  " * depth + msg)


@dataclass
class _RunContext:
    bot: BotConfig
    depth: int
    rubric: str
    tools_used: list[str] = field(default_factory=list)


def _tool_result(tool_use_id: str, content: str, is_error: bool = False) -> dict[str, Any]:
    r: dict[str, Any] = {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}
    if is_error:
        r["is_error"] = True
    return r


def _short(s: str, n: int) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"
