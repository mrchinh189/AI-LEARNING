"""Dr. X — bot chuyên "khám" các bot khác (ví dụ của Lauren Tan).

Đọc nhật ký làm việc của từng bot, chỉ ra bot nào yếu ở đâu, nên thêm skill gì,
bot nào ôm quá nhiều việc nên tách, rồi ghi báo cáo vào reports/.
Nên chạy định kỳ (cron) — ví dụ mỗi tuần một lần.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from .agent import Runtime

DOCTOR_SYSTEM = (
    "Bạn là Dr. X — chuyên gia thiết kế và tối ưu đội AI agent. Nhiệm vụ: khám từng bot dựa trên "
    "nhật ký làm việc thật, không phỏng đoán khi không có dữ liệu. Nguyên tắc thiết kế của đội: mỗi bot "
    "một vai trò hẹp (nhồi nhiều việc làm trí nhớ loãng); việc lặp lại phải thành skill; bot phải tự "
    "kiểm tra trước khi nộp; trưởng nhóm chỉ phân việc. Đề xuất phải cụ thể, làm được ngay."
)


class BotReview(BaseModel):
    bot: str
    verdict: str  # ví dụ: tốt / cần cải thiện / quá tải / ít được dùng / chưa có dữ liệu
    issues: list[str]
    suggested_skills: list[str]
    suggestions: list[str]


class DoctorReport(BaseModel):
    summary: str
    bots: list[BotReview]
    team_changes: list[str]  # tách bot, gộp bot, thêm bot mới, đổi người quản lý...


def collect_stats(runtime: Runtime, per_bot_entries: int = 10) -> dict:
    stats = {}
    for name, bot in runtime.team.bots.items():
        entries = runtime.ws.recent_logs(name, limit=10_000)
        graded = [e for e in entries if e.get("rubric")]
        stats[name] = {
            "title": bot.title,
            "role": bot.role,
            "tools": runtime.tool_names(bot),
            "delegates": bot.delegates,
            "delegate_only": bot.delegate_only,
            "runs": len(entries),
            "graded_runs": len(graded),
            "pass_rate": round(sum(1 for e in graded if e.get("passed")) / len(graded), 2) if graded else None,
            "avg_attempts": round(sum(e.get("attempts", 0) for e in graded) / len(graded), 2) if graded else None,
            "tool_usage": dict(Counter(t for e in entries for t in e.get("tools", []))),
            "callers": dict(Counter(str(e.get("parent")) for e in entries)),
            "memory_chars": len(runtime.ws.memory(name)),
            "recent": [
                {k: e.get(k) for k in ("ts", "task", "result", "passed", "score", "attempts")}
                for e in entries[-per_bot_entries:]
            ],
        }
    return stats


def examine(runtime: Runtime) -> tuple[DoctorReport, Path]:
    stats = collect_stats(runtime)
    prompt = (
        "Dữ liệu đội bot (cấu hình + thống kê + nhật ký gần đây):\n\n"
        f"<team_data>\n{json.dumps(stats, ensure_ascii=False, indent=1)}\n</team_data>\n\n"
        "Hãy khám từng bot và đề xuất thay đổi cho cả đội."
    )
    report = runtime.llm.parse(purpose="doctor", system=DOCTOR_SYSTEM, prompt=prompt, schema=DoctorReport, effort="high")
    path = runtime.ws.root / "reports" / f"doctor-{time.strftime('%Y%m%d-%H%M%S')}.md"
    path.write_text(render(report), encoding="utf-8")
    return report, path


def render(report: DoctorReport) -> str:
    out = [f"# Báo cáo Dr. X — {time.strftime('%Y-%m-%d %H:%M')}", "", report.summary, ""]
    for b in report.bots:
        out.append(f"## `{b.bot}` — {b.verdict}")
        for label, items in (("Vấn đề", b.issues), ("Skill nên thêm", b.suggested_skills), ("Đề xuất", b.suggestions)):
            if items:
                out.append(f"**{label}:**")
                out += [f"- {i}" for i in items]
        out.append("")
    if report.team_changes:
        out.append("## Thay đổi cho cả đội")
        out += [f"- {c}" for c in report.team_changes]
    return "\n".join(out) + "\n"
