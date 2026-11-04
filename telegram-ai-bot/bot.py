"""Bot Telegram trò chuyện bằng Claude hoặc Gemini.

Lệnh:
  /start          giới thiệu
  /model          xem model đang dùng
  /model claude   chuyển sang Claude
  /model gemini   chuyển sang Gemini
  /reset          xoá lịch sử hội thoại
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from providers import build_providers

load_dotenv()
logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("bot")

SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Bạn là trợ lý AI thân thiện trên Telegram. Trả lời ngắn gọn, rõ ràng, "
    "bằng ngôn ngữ người dùng đang dùng.",
)
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))  # số tin nhắn giữ lại mỗi chat
ALLOWED_USERS = {int(x) for x in os.getenv("ALLOWED_USER_IDS", "").replace(" ", "").split(",") if x}
TELEGRAM_LIMIT = 4096

PROVIDERS = build_providers()
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", next(iter(PROVIDERS)))
if DEFAULT_PROVIDER not in PROVIDERS:
    DEFAULT_PROVIDER = next(iter(PROVIDERS))


def allowed(update: Update) -> bool:
    return not ALLOWED_USERS or (update.effective_user and update.effective_user.id in ALLOWED_USERS)


def current_provider(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.chat_data.get("provider", DEFAULT_PROVIDER)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    await update.message.reply_text(
        f"Xin chào! Mình là bot AI (đang dùng: {current_provider(context)}).\n"
        f"Model có sẵn: {', '.join(PROVIDERS)}\n\n"
        "/model <tên> – đổi model\n/reset – xoá lịch sử hội thoại"
    )


async def model_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    if not context.args:
        await update.message.reply_text(
            f"Đang dùng: {current_provider(context)}. Có sẵn: {', '.join(PROVIDERS)}"
        )
        return
    name = context.args[0].lower()
    if name not in PROVIDERS:
        await update.message.reply_text(f"Không có '{name}'. Có sẵn: {', '.join(PROVIDERS)}")
        return
    context.chat_data["provider"] = name
    context.chat_data["history"] = []
    await update.message.reply_text(f"Đã chuyển sang {name} và xoá lịch sử.")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    context.chat_data["history"] = []
    await update.message.reply_text("Đã xoá lịch sử hội thoại.")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        await update.message.reply_text("Bạn không có quyền dùng bot này.")
        return

    history: list[dict] = context.chat_data.setdefault("history", [])
    history.append({"role": "user", "text": update.message.text})

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    provider = PROVIDERS[current_provider(context)]
    try:
        answer = await provider.reply(SYSTEM_PROMPT, history)
    except Exception:
        log.exception("Lỗi khi gọi %s", provider.name)
        history.pop()  # bỏ tin nhắn lỗi để lịch sử vẫn xen kẽ user/assistant
        await update.message.reply_text("Có lỗi khi gọi AI, vui lòng thử lại sau.")
        return

    history.append({"role": "assistant", "text": answer})
    # Giữ lại MAX_HISTORY tin nhắn gần nhất, luôn bắt đầu bằng tin của user.
    if len(history) > MAX_HISTORY:
        del history[: len(history) - MAX_HISTORY]
        while history and history[0]["role"] != "user":
            history.pop(0)

    for i in range(0, len(answer), TELEGRAM_LIMIT):
        await update.message.reply_text(answer[i : i + TELEGRAM_LIMIT])


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Thiếu TELEGRAM_BOT_TOKEN trong .env")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("model", model_cmd))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    log.info("Bot đang chạy với provider: %s (mặc định: %s)", ", ".join(PROVIDERS), DEFAULT_PROVIDER)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
