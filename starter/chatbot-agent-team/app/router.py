"""Router: phân loại tin nhắn vào đường nhanh (FAQ), đường sâu (agent team) hoặc chuyển nhân viên."""
from . import config, llm

SCHEMA = {
    "type": "object",
    "properties": {
        "route": {"type": "string", "enum": ["fast", "deep", "human"]},
        "reason": {"type": "string"},
    },
    "required": ["route", "reason"],
    "additionalProperties": False,
}

SYSTEM = """Bạn là bộ định tuyến tin nhắn cho chatbot chăm sóc khách hàng. Chọn đúng một route:
- fast: chào hỏi, cảm ơn, hoặc câu hỏi ngắn có thể trả lời từ tài liệu nội bộ (FAQ, chính sách, giá, giờ làm việc, sản phẩm).
- deep: yêu cầu cần nhiều bước: tìm kiếm thông tin bên ngoài, so sánh, phân tích, viết báo cáo/kế hoạch,
  hoặc yêu cầu thực hiện hành động (tạo ticket, gửi email, đặt lịch).
- human: người dùng muốn gặp nhân viên thật, khiếu nại nghiêm trọng, hoặc vấn đề pháp lý/tài chính nhạy cảm.
Nếu phân vân giữa fast và deep, chọn fast. reason: một câu ngắn bằng tiếng Việt."""

_DEEP_HINTS = ("báo cáo", "so sánh", "phân tích", "nghiên cứu", "tìm hiểu", "ticket", "gửi email", "kế hoạch")
_HUMAN_HINTS = ("nhân viên", "người thật", "khiếu nại")


def _fake_route(text: str) -> dict:
    lower = text.lower()
    if any(h in lower for h in _HUMAN_HINTS):
        return {"route": "human", "reason": "[FAKE_LLM] từ khóa gặp nhân viên"}
    if any(h in lower for h in _DEEP_HINTS):
        return {"route": "deep", "reason": "[FAKE_LLM] từ khóa tác vụ nhiều bước"}
    return {"route": "fast", "reason": "[FAKE_LLM] mặc định"}


def route(text: str, history_text: str) -> dict:
    prompt = f"Lịch sử gần đây:\n{history_text or '(trống)'}\n\nTin nhắn mới: {text}"
    return llm.ask_json(config.MODEL_ROUTER, SYSTEM, prompt, SCHEMA, effort="low", max_tokens=1000,
                        fake=lambda: _fake_route(text))
