"""A2 — Theo dõi & nhắc việc.

Chạy theo luật, không cần LLM: so hạn với ngày làm việc, tính mức leo thang,
gộp mọi việc của một người vào một tin.
"""

from collections import defaultdict

from .. import notify
from ..config import settings
from ..workdays import Calendar
from .common import UNCONFIRMED, as_date, assignees, open_tasks, task_link, today

LEVEL_TEXT = {
    0: "Sắp đến hạn",
    1: "Đến hạn hôm nay",
    2: "Trễ hạn",
    3: "Trễ hạn — đã báo người giao việc",
}


def level_for(task: dict, cal: Calendar, d0) -> int | None:
    """Trả mức 0–3, hoặc None nếu chưa cần nhắc."""
    due = as_date(task.get("exp_end_date"))
    if not due or task.get("status") == "Pending Review":
        return None
    if due > d0:
        return 0 if cal.workdays_between(d0, due) <= 2 else None
    if due == d0:
        return 1
    late = cal.workdays_between(due, d0)  # số ngày làm việc đã trễ
    if late == 0:  # hạn rơi vào ngày nghỉ vừa qua
        return 1
    if late >= 3 or (task.get("priority") == "Urgent" and late >= 1):
        return 3
    return 2


def recipients(task: dict, level: int, org: dict) -> set[str]:
    people = set(assignees(task)) or {org.get("unassigned_fallback") or task.get("owner")}
    if level >= 2:
        head = (org.get("department_heads") or {}).get(task.get("department") or "")
        if head:
            people.add(head)
    if level >= 3:
        people.add(task.get("eup_assigned_by") or task.get("owner"))
    return {p for p in people if p}


def run(erp, slot: str = "morning") -> dict:
    """slot='afternoon' chỉ nhắc việc đến hạn/trễ (mức ≥ 1) để mỗi người không nhận quá nhiều tin."""
    erp = erp.as_agent("A2-nhac-viec")
    org = settings.org()
    d0 = today()
    calendars: dict[str, Calendar] = {}
    inbox: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    escalated = 0

    for t in open_tasks(erp):
        if t.get("eup_confirm_state") == UNCONFIRMED:
            continue
        company = t.get("company") or ""
        if company not in calendars:
            calendars[company] = Calendar.from_erp(erp, company)
        lv = level_for(t, calendars[company], d0)
        if lv is None or (slot == "afternoon" and lv < 1):
            continue
        for user in recipients(t, lv, org):
            inbox[user].append((lv, t))
        if lv >= 2 and lv > int(t.get("eup_escalation_level") or 0):
            erp.update_task(t["name"], {"eup_escalation_level": lv})
            erp.comment_task(t["name"], f"[Agent nhắc việc] {LEVEL_TEXT[lv]} — đã báo: "
                                        f"{', '.join(sorted(recipients(t, lv, org)))}")
            escalated += 1

    for user, items in inbox.items():
        items.sort(key=lambda x: (-x[0], str(x[1].get("exp_end_date"))))
        lines = [f"- [{LEVEL_TEXT[lv]}] {t['subject']} · hạn {t.get('exp_end_date')} · {task_link(t['name'])}"
                 for lv, t in items]
        body = ("Anh/chị có các việc cần chú ý:\n" + "\n".join(lines) +
                "\n\nVui lòng cập nhật tiến độ trên ERP (Đang làm / Chờ duyệt) hoặc ghi lý do nếu cần đổi hạn.")
        notify.send(erp, user, f"Nhắc việc {d0:%d/%m/%Y}: {len(items)} việc", body)

    return {"people_notified": len(inbox), "items": sum(len(v) for v in inbox.values()),
            "escalated": escalated}
