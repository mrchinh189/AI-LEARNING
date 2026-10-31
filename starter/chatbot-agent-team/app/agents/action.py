"""Action agent: đề xuất hành động ghi (tạo ticket, gửi email). Hành động chỉ chạy sau khi người dùng duyệt,
và được thực thi qua một webhook n8n để agent không giữ thông tin đăng nhập của hệ thống ngoài."""
import httpx

from .. import config, llm

ACTIONS = {
    "create_ticket": "Tạo ticket hỗ trợ. Dùng title, description, priority (low|normal|high).",
    "send_email": "Gửi email. Dùng to, subject, body.",
}

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": [*ACTIONS, "none"]},
        "params": {
            "type": "object",
            "properties": {k: {"type": "string"} for k in
                           ("title", "description", "priority", "to", "subject", "body")},
            "required": ["title", "description", "priority", "to", "subject", "body"],
            "additionalProperties": False,
        },
        "summary": {"type": "string"},
    },
    "required": ["action", "params", "summary"],
    "additionalProperties": False,
}

SYSTEM = "Bạn là Action agent. Chọn MỘT hành động phù hợp nhất với mục tiêu, hoặc 'none' nếu không cần.\n" + \
    "\n".join(f"- {name}: {desc}" for name, desc in ACTIONS.items()) + \
    "\nĐiền các trường không dùng bằng chuỗi rỗng. summary: một câu tiếng Việt mô tả hành động để người dùng duyệt." + \
    "\nKhông bịa địa chỉ email; nếu thiếu thông tin bắt buộc thì chọn 'none' và nêu thông tin còn thiếu trong summary."


def _fake_proposal(goal: str) -> dict:
    params = dict.fromkeys(("title", "description", "priority", "to", "subject", "body"), "")
    params.update(title=goal[:80], description=goal, priority="normal")
    return {"action": "create_ticket", "params": params, "summary": f"Tạo ticket: {goal[:80]}"}


def propose(goal: str, context: str) -> dict:
    return llm.ask_json(config.MODEL_AGENT, SYSTEM, f"MỤC TIÊU: {goal}\n\nBỐI CẢNH: {context or '(không có)'}",
                        SCHEMA, effort="low", fake=lambda: _fake_proposal(goal))


def execute(action: str, params: dict) -> str:
    if action not in ACTIONS:
        raise ValueError(f"Hành động không được phép: {action}")
    clean = {k: v for k, v in params.items() if v}
    if not config.N8N_WEBHOOK_URL:
        return f"Chế độ thử (chưa cấu hình N8N_WEBHOOK_URL), không gửi đi: {action} {clean}"
    resp = httpx.post(config.N8N_WEBHOOK_URL, json={"action": action, "params": clean}, timeout=30)
    resp.raise_for_status()
    return resp.text[:500] or f"HTTP {resp.status_code}"
