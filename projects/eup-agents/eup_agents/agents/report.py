"""A5 — Báo cáo tuần theo phòng ban.

Số liệu tính bằng code (không để LLM tự tính). LLM chỉ viết phần "Nhận định & đề xuất".
"""

from collections import Counter, defaultdict
from datetime import timedelta

from .. import llm, notify
from ..config import settings
from .common import TASK_FIELDS, as_date, assignees, company_filter, open_tasks, task_link, today

SYSTEM = """Bạn là Agent Báo cáo của EuP Group. Viết phần "Nhận định & đề xuất" cho báo cáo tuần
của một phòng ban, dựa DUY NHẤT trên số liệu được cung cấp.
- Viết tiếng Việt, kết luận trước, mỗi ý ≤ 25 chữ, có số.
- 3 nhận định + tối đa 3 đề xuất; mỗi đề xuất ghi: làm gì — ai (vai trò) — trước ngày nào.
- Không bịa số liệu, không nêu tên người ngoài danh sách được cung cấp.
- Định dạng số kiểu Việt Nam (82%, 1.240)."""


def build_stats(open_list: list[dict], done_list: list[dict], new_list: list[dict], d0) -> dict[str, dict]:
    stats: dict[str, dict] = defaultdict(lambda: {
        "open": 0, "overdue": 0, "no_due": 0, "no_owner": 0, "unconfirmed": 0,
        "done": 0, "done_on_time": 0, "new": 0, "top_overdue": [], "overdue_by_owner": Counter()})
    for t in open_list:
        s = stats[t.get("department") or "(Chưa gán phòng)"]
        s["open"] += 1
        due = as_date(t.get("exp_end_date"))
        if t.get("eup_confirm_state") == "Chờ xác nhận":
            s["unconfirmed"] += 1
        if not due:
            s["no_due"] += 1
        if not assignees(t):
            s["no_owner"] += 1
        if due and due < d0:
            s["overdue"] += 1
            s["top_overdue"].append(((d0 - due).days, t))
            for u in assignees(t) or ["(chưa giao)"]:
                s["overdue_by_owner"][u] += 1
    for t in done_list:
        s = stats[t.get("department") or "(Chưa gán phòng)"]
        s["done"] += 1
        due, done = as_date(t.get("exp_end_date")), as_date(t.get("completed_on"))
        if due and done and done <= due:
            s["done_on_time"] += 1
    for t in new_list:
        stats[t.get("department") or "(Chưa gán phòng)"]["new"] += 1
    for s in stats.values():
        s["top_overdue"].sort(key=lambda x: -x[0])
        s["top_overdue"] = s["top_overdue"][:5]
    return stats


def render(dept: str, s: dict, d0, insight: str | None) -> str:
    rate = f"{round(100 * s['done_on_time'] / s['done'])}%" if s["done"] else "—"
    lines = [
        f"# Báo cáo tuần — {dept} — tuần kết thúc {d0:%d/%m/%Y}",
        "",
        "| Chỉ số | Giá trị |",
        "|---|---|",
        f"| Việc mới trong tuần | {s['new']} |",
        f"| Việc hoàn thành trong tuần | {s['done']} (đúng hạn {rate}) |",
        f"| Việc đang mở | {s['open']} |",
        f"| Việc trễ hạn đang mở | {s['overdue']} |",
        f"| Việc thiếu hạn / thiếu người phụ trách | {s['no_due']} / {s['no_owner']} |",
        f"| Việc agent tạo đang chờ xác nhận | {s['unconfirmed']} |",
        "",
        "## Top việc trễ hạn",
    ]
    if s["top_overdue"]:
        for days, t in s["top_overdue"]:
            who = ", ".join(assignees(t)) or "(chưa giao)"
            lines.append(f"- Trễ {days} ngày · {t['subject']} · {who} · {task_link(t['name'])}")
    else:
        lines.append("- Không có việc trễ hạn.")
    if insight:
        lines += ["", "## Nhận định & đề xuất (AI soạn — trưởng phòng duyệt trước khi gửi)", insight]
    return "\n".join(lines) + "\n"


def run(erp, send: bool = False) -> dict:
    erp = erp.as_agent("A5-bao-cao")
    d0 = today()
    week_start = d0 - timedelta(days=6)
    scope = company_filter()
    open_list = open_tasks(erp)
    done_list = erp.get_list("Task", [["status", "=", "Completed"], ["completed_on", ">=", str(week_start)], *scope],
                             TASK_FIELDS, limit=2000)
    new_list = erp.get_list("Task", [["creation", ">=", str(week_start)], *scope], ["name", "department"], limit=2000)
    stats = build_stats(open_list, done_list, new_list, d0)

    settings.report_dir.mkdir(parents=True, exist_ok=True)
    heads = settings.org().get("department_heads") or {}
    files = []
    for dept, s in sorted(stats.items()):
        facts = {k: v for k, v in s.items() if k not in ("top_overdue", "overdue_by_owner")}
        facts["top_overdue"] = [{"subject": t["subject"], "days_late": d} for d, t in s["top_overdue"]]
        facts["overdue_by_owner"] = dict(s["overdue_by_owner"])
        insight = llm.ask(SYSTEM, f"Phòng: {dept}\nTuần kết thúc: {d0:%d/%m/%Y}\nSố liệu: {facts}")
        md = render(dept, s, d0, insight)
        path = settings.report_dir / f"bao-cao-tuan-{d0:%Y%m%d}-{dept.replace('/', '-').replace(' ', '_')}.md"
        path.write_text(md, encoding="utf-8")
        files.append(str(path))
        # Gửi bản nháp cho trưởng phòng duyệt; không gửi thẳng BGĐ.
        if send and heads.get(dept):
            notify.send(erp, heads[dept], f"[Nháp] Báo cáo tuần {dept} {d0:%d/%m}", md)
    return {"departments": len(stats), "files": files}
