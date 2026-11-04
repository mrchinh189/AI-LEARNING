# Kiến trúc mã nguồn và cách mở rộng

Đọc file này khi cần sửa code của dự án (thêm tool, nối API thật, đổi cơ chế duyệt, đổi model).

## Module

| File | Vai trò |
|---|---|
| `ai_team/llm.py` | Lớp `LLM` bọc Anthropic SDK. Model mặc định `claude-opus-5-5` (đổi bằng biến `AI_TEAM_MODEL`). Bật refusal fallback (`fallbacks="default"`, beta `server-side-fallback-2026-07-01`). `create()` cho vòng lặp agent, `parse()` cho structured output. |
| `ai_team/config.py` | `BotConfig`, `Team`, `load_team()` — kiểm tra delegates tồn tại, `delegate_only` không có tool làm việc. |
| `ai_team/store.py` | `Workspace`: `memory/`, `skills/` (ghi đè `team/skills/`), `logs/*.jsonl`, `rooms/*.json`, `outputs/` (sandbox chống path traversal), `reports/`. |
| `ai_team/agent.py` | `Runtime.run()` — vòng lặp; `TOOL_SPECS`; `APPROVAL_REQUIRED`; `Operator` (`CLIOperator`, `AutoOperator`); các hàm `_tool_<tên>`. |
| `ai_team/grader.py` | `grade()` → `Grade(passed, score, criteria, feedback)` qua structured output. |
| `ai_team/room.py` | Phòng chat: `@tên`, `PASS`, bot @nhắc nhau, ngân sách 2 × số thành viên lượt nói. |
| `ai_team/doctor.py` | Dr. X: thống kê nhật ký → `DoctorReport` → `reports/doctor-*.md`. |
| `ai_team/cli.py` | Lệnh `ask`, `chat`, `doctor`, `skills`, `memory`. |

## Vòng lặp `Runtime.run`

1. Nếu có `skill`: nối toàn văn skill vào task, dùng "Tiêu chí đạt" làm rubric.
2. System prompt = hiến chương → danh tính → đồng đội → quy tắc delegate_only → danh sách skill → trí nhớ → 5 việc gần nhất.
3. Gọi model; **nối nguyên `response.content`** (kể cả thinking block) — lịch sử chỉ thêm, không sửa.
4. `tool_use` → thực thi mọi tool, trả tất cả `tool_result` trong một tin `user`. `pause_turn` → gọi lại. `refusal` → dừng.
5. Kết thúc → nếu có rubric: grader chấm; chưa đạt và còn lượt → gửi phản hồi, quay lại 3.
6. Ghi nhật ký.

Giới hạn: `max_turns=30`, `max_depth=3`, `max_attempts=3`, `max_tokens=16000`.

## Thêm tool

Ví dụ thêm `send_email` cần duyệt:

```python
# agent.py
APPROVAL_REQUIRED = {"publish", "purchase", "save_skill", "send_email"}

TOOL_SPECS["send_email"] = {
    "description": "Gửi email. Cần người vận hành duyệt. Luôn trình bản nháp trước.",
    "input_schema": _schema({"to": _S, "subject": _S, "body": _S}),
}

class Runtime:
    def _tool_send_email(self, ctx, to: str, subject: str, body: str) -> str:
        ...  # gọi API email thật
        return f"Đã gửi tới {to}"
```

Rồi: thêm `"send_email"` vào `WORK_TOOLS` trong `config.py` (để `delegate_only` chặn được) và trong `scripts/validate_team.py` của skill; cấp tool cho bot trong `team.json`; viết test với `FakeLLM` (xem `test_publish_requires_human_approval`).

Quy ước: mọi tham số là bắt buộc (`strict: true`); tham số tuỳ chọn nhận chuỗi rỗng. Lỗi trong hàm tool cứ ném ngoại lệ — `_execute` bắt và trả cho model với `is_error`.

## Nối API thật cho `publish` / `purchase`

Sửa thân `_tool_publish` / `_tool_purchase`. Giữ nguyên cổng duyệt. Nên thêm: danh sách kênh cho phép, hạn mức chi tiêu mỗi lần/mỗi ngày (kiểm tra trong hàm tool, ném lỗi nếu vượt), ghi sổ mọi giao dịch. Từ lúc này **không dùng `--auto-approve`**.

## Duyệt khi chạy theo lịch (cron)

`CLIOperator` gọi `input()`; không có terminal thì `EOFError` bị `_execute` bắt và trả về model như lỗi tool — hành động không chạy (an toàn) nhưng thông báo chung chung. Cách tốt hơn: thêm `QueueOperator` trả `False` và ghi đề xuất vào `outputs/pending/` để người vận hành xem sau; chọn operator này trong `cli.py` khi `not sys.stdin.isatty()`.

## Đổi model / chi phí

- Đổi toàn bộ: `AI_TEAM_MODEL=<model-id>`.
- Giảm chi phí: hạ `effort` cho bot đơn giản; chỉ dùng rubric cho việc quan trọng; giao thẳng `--bot` thay vì qua bot quản lý; bật prompt caching cho phần system prompt ổn định.
- Ghi `response.usage` vào nhật ký nếu cần theo dõi chi phí từng bot.

## Kiểm thử

`tests/test_team.py` dùng `FakeLLM` (kịch bản phản hồi theo từng bot) và đội cố định ở `tests/fixtures/` — nên người dùng sửa `team/` không làm hỏng test. Khi thêm tính năng, viết test cùng kiểu: kịch bản `tool(...)` rồi `text(...)`, kiểm tra file sinh ra và nội dung `tool_result`.
