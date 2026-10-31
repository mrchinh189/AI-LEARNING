# Chatbot + AI Agent Team — bộ mã khởi đầu

Bản hiện thực tối thiểu, chạy được, của thiết kế [Chatbot kết hợp AI Agent Team](../../docs/solution-design/chatbot-agent-team.md).

**Hướng dẫn từng bước cho người mới:** [docs/huong-dan-trien-khai/chatbot-agent-team.md](../../docs/huong-dan-trien-khai/chatbot-agent-team.md)

## Chạy nhanh (5 phút, chế độ giả lập, không cần API key)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
pytest -q
python -m app.ingest kb --reset
uvicorn app.main:app --port 8000      # terminal 1
python -m app.worker                  # terminal 2
```

Mở http://localhost:8000. Muốn dùng AI thật: điền `ANTHROPIC_API_KEY` và đặt `FAKE_LLM=0` trong `.env`.

## Cấu trúc

| File | Vai trò |
|---|---|
| `app/main.py` | Gateway HTTP (FastAPI) + trang chat web |
| `app/telegram_bot.py` | Kênh Telegram (long polling) |
| `app/core.py` | Xử lý tin nhắn dùng chung cho mọi kênh, chuyển nhân viên, duyệt hành động |
| `app/router.py` | Phân loại: `fast` / `deep` / `human` (model nhỏ) |
| `app/faq.py` | Đường nhanh: tìm tài liệu (SQLite FTS5) + trả lời có trích dẫn |
| `app/worker.py` | Lấy tác vụ từ hàng đợi, chạy agent team, thực thi hành động đã duyệt |
| `app/agents/orchestrator.py` | Lập kế hoạch, giao việc song song, tổng hợp, vòng review |
| `app/agents/research.py` | Tìm kiếm và đọc web (web search / web fetch phía server) |
| `app/agents/action.py` | Đề xuất hành động; chỉ chạy sau khi duyệt, qua webhook n8n |
| `app/agents/reviewer.py` | Kiểm tra bản nháp trước khi gửi |
| `app/llm.py` | Một chỗ duy nhất gọi Claude API (structured outputs, fallback, pause_turn, chế độ giả lập) |
| `app/db.py` | SQLite: hội thoại, hàng đợi tác vụ, sự kiện, duyệt, kho tri thức |
| `app/ingest.py` | Nạp tài liệu `kb/` vào kho tri thức |
