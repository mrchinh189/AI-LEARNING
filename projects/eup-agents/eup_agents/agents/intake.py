"""A1 — Tiếp nhận việc: bóc tách email/tin nhắn thành Task nháp chờ xác nhận."""

from datetime import timedelta

from .. import llm
from ..config import settings
from .common import UNCONFIRMED, today

SYSTEM = """Bạn là Agent Tiếp nhận việc của EuP Group (tập đoàn đa ngành, nhiều pháp nhân, dùng ERP erp.eup.vn).
Đọc một email/tin nhắn/công văn và bóc tách các ĐẦU VIỆC cần làm.

Quy tắc:
1. Chỉ lấy yêu cầu hành động rõ ràng. Thông báo, cảm ơn, CC để biết → trả danh sách rỗng.
2. subject: động từ + đối tượng + kết quả, ≤ 120 ký tự, tiếng Việt.
3. owner: email người phải làm nếu nội dung nêu rõ; không rõ → chuỗi rỗng. KHÔNG đoán.
4. due_date: YYYY-MM-DD nếu nội dung có hạn (quy đổi "thứ Sáu này", "cuối tháng" theo ngày hôm nay
   được cung cấp); không có hạn → chuỗi rỗng.
5. company: tên pháp nhân nếu nêu rõ; không chắc → chuỗi rỗng.
6. definition_of_done: kết quả đầu ra cụ thể để biết việc đã xong.
7. Không chép số CCCD, số tài khoản, mức lương vào bất kỳ trường nào.
8. confidence: 0–1, mức chắc chắn rằng đây là việc thật và các trường đúng."""

SCHEMA = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "owner": {"type": "string"},
                    "due_date": {"type": "string"},
                    "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Urgent"]},
                    "company": {"type": "string"},
                    "definition_of_done": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["subject", "owner", "due_date", "priority", "company",
                             "definition_of_done", "confidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["tasks"],
    "additionalProperties": False,
}

DEFAULT_DUE_DAYS = 5


def extract(text: str, sender: str) -> list[dict]:
    out = llm.ask(SYSTEM, f"Hôm nay: {today():%Y-%m-%d} ({today():%A})\nNgười gửi: {sender}\n\n---\n{text}",
                  schema=SCHEMA)
    return (out or {}).get("tasks", []) if isinstance(out, dict) else []


def run(erp, text: str, sender: str, source: str = "Email", source_ref: str = "") -> dict:
    if not settings.llm_enabled:
        return {"created": [], "note": "LLM_ENABLED=false — A1 cần LLM để bóc tách việc"}
    erp = erp.as_agent("A1-tiep-nhan")
    drafts = extract(text, sender)
    created = []
    for d in drafts:
        owner = d["owner"].strip().lower()
        if owner and not erp.exists("User", owner):
            owner = ""  # email không có trên ERP → để trưởng phòng phân công
        due_by_agent = not d["due_date"]
        due = d["due_date"] or str(today() + timedelta(days=DEFAULT_DUE_DAYS))
        company = d["company"] if d["company"] and erp.exists("Company", d["company"]) else None
        note = []
        if due_by_agent:
            note.append(f"Hạn do agent đề xuất (+{DEFAULT_DUE_DAYS} ngày).")
        if not owner:
            note.append("Chưa xác định người phụ trách — cần phân công.")
        if d["confidence"] < 0.7:
            note.append(f"Độ tin cậy thấp ({d['confidence']:.2f}) — kiểm tra kỹ.")
        res = erp.create_task({
            "subject": d["subject"][:140],
            "priority": d["priority"],
            "exp_end_date": due,
            "company": company,
            "description": f"{d['definition_of_done']}\n\n{' '.join(note)}".strip(),
            "eup_definition_of_done": d["definition_of_done"],
            "eup_assigned_by": sender if erp.exists("User", sender) else None,
            "eup_source": source,
            "eup_source_ref": source_ref[:140],
            "eup_confirm_state": UNCONFIRMED,
            "eup_agent_created": 1,
        })
        if owner and res.get("name"):
            erp.assign_task(res["name"], [owner])
        created.append({"name": res.get("name"), "subject": d["subject"], "owner": owner or None, "due": due})
    return {"created": created}
