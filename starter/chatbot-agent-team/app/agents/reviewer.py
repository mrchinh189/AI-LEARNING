"""Reviewer agent: kiểm tra bản nháp trước khi gửi cho người dùng."""
from .. import config, llm

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "revise"]},
        "feedback": {"type": "string"},
    },
    "required": ["verdict", "feedback"],
    "additionalProperties": False,
}

SYSTEM = """Bạn là Reviewer agent. Đánh giá BẢN NHÁP so với YÊU CẦU theo các tiêu chí:
1. Trả lời đúng và đủ yêu cầu.  2. Thông tin quan trọng có nguồn hoặc được ghi rõ là chưa chắc chắn.
3. Không hứa hẹn điều công ty chưa xác nhận.  4. Tiếng Việt rõ ràng, có cấu trúc.
Chỉ chọn 'revise' khi có lỗi thật sự cần sửa; feedback liệt kê ngắn gọn những gì cần sửa."""


def review(request: str, draft: str) -> dict:
    return llm.ask_json(config.MODEL_AGENT, SYSTEM, f"YÊU CẦU:\n{request}\n\nBẢN NHÁP:\n{draft}", SCHEMA,
                        effort="low", fake={"verdict": "pass", "feedback": "[FAKE_LLM] ổn"})
