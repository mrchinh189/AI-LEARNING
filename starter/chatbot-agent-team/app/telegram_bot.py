"""Kênh Telegram dùng long polling: không cần tên miền hay HTTPS, chạy được ngay trên máy cá nhân.

Chạy: python -m app.telegram_bot   (cần TELEGRAM_BOT_TOKEN trong .env)
"""
import logging
import threading
import time

import httpx

from . import config, core, db

log = logging.getLogger(__name__)
MAX_LEN = 4000  # Telegram giới hạn 4096 ký tự / tin nhắn
ICONS = {"progress": "⏳", "approval": "🔐", "action_result": "✅", "result": "📄", "error": "❌"}


class Telegram:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}"
        self.http = httpx.Client(timeout=45)

    def call(self, method: str, **params):
        resp = self.http.post(f"{self.base}/{method}", json=params)
        data = resp.json()
        if not data.get("ok"):
            log.warning("Telegram %s lỗi: %s", method, data.get("description"))
        return data.get("result")

    def send(self, chat_id: int | str, text: str, reply_markup: dict | None = None) -> None:
        chunks = [text[i:i + MAX_LEN] for i in range(0, len(text), MAX_LEN)] or [""]
        for i, chunk in enumerate(chunks):
            extra = {"reply_markup": reply_markup} if reply_markup and i == len(chunks) - 1 else {}
            self.call("sendMessage", chat_id=chat_id, text=chunk, **extra)


def handle_update(tg: Telegram, update: dict) -> None:
    if "callback_query" in update:
        cq = update["callback_query"]
        _, approval_id, choice = cq.get("data", "a::").split(":")
        chat_id = cq["message"]["chat"]["id"]
        result = core.decide("telegram", str(chat_id), approval_id, choice == "y")
        message = result["message"] if result else "Không tìm thấy yêu cầu duyệt."
        tg.call("answerCallbackQuery", callback_query_id=cq["id"], text=message[:200])
        if result and result["ok"]:
            tg.call("editMessageReplyMarkup", chat_id=chat_id, message_id=cq["message"]["message_id"],
                    reply_markup={"inline_keyboard": []})
            tg.send(chat_id, message)
        return

    msg = update.get("message") or {}
    text, chat_id = msg.get("text"), msg.get("chat", {}).get("id")
    if not text or chat_id is None:
        return
    tg.call("sendChatAction", chat_id=chat_id, action="typing")
    out = core.handle_message("telegram", str(chat_id), text)
    tg.send(chat_id, out["reply"])


def push_events_forever(token: str) -> None:
    """Gửi tiến độ / kết quả của agent team về đúng cuộc trò chuyện Telegram."""
    tg = Telegram(token)  # client riêng cho thread này
    while True:
        try:
            for ev in db.undelivered_events("telegram"):
                markup = None
                if ev["kind"] == "approval":
                    aid = ev["data"]["approval_id"]
                    markup = {"inline_keyboard": [[
                        {"text": "✅ Duyệt", "callback_data": f"a:{aid}:y"},
                        {"text": "✖ Hủy", "callback_data": f"a:{aid}:n"},
                    ]]}
                text = f"{ICONS.get(ev['kind'], '')} {ev['message']}"
                if ev["kind"] == "approval":
                    text = f"🔐 Cần bạn duyệt hành động:\n{ev['message']}\nChi tiết: {ev['data'].get('params')}"
                tg.send(ev["external_id"], text, markup)
                db.mark_delivered(ev["id"])
        except Exception:
            log.exception("Lỗi khi gửi sự kiện sang Telegram")
        time.sleep(2)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Thiếu TELEGRAM_BOT_TOKEN trong .env (lấy từ @BotFather).")
    db.init_db()
    tg = Telegram(config.TELEGRAM_BOT_TOKEN)
    me = tg.call("getMe")
    if not me:
        raise SystemExit("Token Telegram không hợp lệ.")
    log.info("Bot @%s đang chạy (FAKE_LLM=%s)", me["username"], config.FAKE_LLM)
    threading.Thread(target=push_events_forever, args=(config.TELEGRAM_BOT_TOKEN,), daemon=True).start()

    offset = None
    while True:
        try:
            updates = tg.call("getUpdates", timeout=30, offset=offset,
                              allowed_updates=["message", "callback_query"]) or []
        except httpx.HTTPError:
            log.warning("Mất kết nối Telegram, thử lại sau 5 giây")
            time.sleep(5)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            try:
                handle_update(tg, update)
            except Exception:
                log.exception("Lỗi khi xử lý update %s", update.get("update_id"))


if __name__ == "__main__":
    main()
