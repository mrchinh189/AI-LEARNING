# Telegram AI Bot (Claude / Gemini)

Bot Telegram trò chuyện bằng **Claude** (Anthropic) hoặc **Gemini** (Google), có nhớ ngữ cảnh hội thoại và đổi model ngay trong chat.

## 1. Chuẩn bị

1. **Tạo bot Telegram**: nhắn `@BotFather` → `/newbot` → đặt tên → nhận `TELEGRAM_BOT_TOKEN`.
2. **Lấy API key** (ít nhất một):
   - Claude: <https://console.anthropic.com/settings/keys> → `ANTHROPIC_API_KEY`
   - Gemini: <https://aistudio.google.com/apikey> → `GEMINI_API_KEY`
3. Cần Python 3.10+.

## 2. Cài đặt

```bash
cd telegram-ai-bot
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # rồi mở .env điền token và key
```

## 3. Chạy

```bash
python bot.py
```

Mở bot trên Telegram và chat.

| Lệnh | Tác dụng |
|---|---|
| `/start` | Giới thiệu, xem model có sẵn |
| `/model` | Xem model đang dùng |
| `/model claude` / `/model gemini` | Đổi model (xoá lịch sử) |
| `/reset` | Xoá lịch sử hội thoại |

## 4. Cấu hình (`.env`)

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `DEFAULT_PROVIDER` | provider đầu tiên có key | `claude` hoặc `gemini` |
| `CLAUDE_MODEL` | `claude-opus-5-5` | Model Claude |
| `CLAUDE_EFFORT` | `low` | `low`/`medium`/`high` – càng cao trả lời càng kỹ nhưng chậm và tốn hơn |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model Gemini |
| `MAX_HISTORY` | `20` | Số tin nhắn nhớ lại mỗi chat |
| `ALLOWED_USER_IDS` | trống | Giới hạn người dùng (ID Telegram, cách nhau dấu phẩy). Nên đặt để tránh người lạ tiêu tốn API |
| `SYSTEM_PROMPT` | trợ lý thân thiện | Tính cách/hướng dẫn cho bot |

Lấy ID Telegram của bạn bằng cách nhắn `@userinfobot`.

## 5. Chạy 24/7 (tuỳ chọn)

Bot dùng long polling nên chỉ cần một máy chạy liên tục (VPS, Raspberry Pi…). Ví dụ systemd:

```ini
# /etc/systemd/system/telegram-ai-bot.service
[Service]
WorkingDirectory=/duong/dan/telegram-ai-bot
ExecStart=/duong/dan/telegram-ai-bot/.venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now telegram-ai-bot
```

## Ghi chú

- Lịch sử hội thoại lưu trong RAM, mất khi khởi động lại bot.
- Với Claude, bot bật `fallbacks: "default"`: nếu yêu cầu bị bộ lọc an toàn từ chối, API tự chạy lại trên model dự phòng.
- Không commit file `.env` (đã có trong `.gitignore`).
