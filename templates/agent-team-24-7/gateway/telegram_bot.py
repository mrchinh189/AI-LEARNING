"""Telegram gateway: xác thực allowlist, chuyển lệnh tới board/planner."""
from __future__ import annotations

from config import settings
from gateway.commands import HELP, parse


def handle(user_id: int, text: str, board, planner) -> str:
    if user_id not in settings.allowed_user_ids:
        return "Bạn không có quyền điều khiển đội agent này."
    cmd = parse(text)
    if cmd.name == "goal" and cmd.args:
        goal = board.create_goal(user_id, cmd.args)
        # TODO: drafts = planner.validate(planner.plan(goal)); gửi kế hoạch kèm nút Duyệt/Sửa/Hủy
        return f"Đã tạo goal #{goal.id}. Planner đang lập kế hoạch..."
    if cmd.name == "status":
        lines = [f"#{g.id} [{g.status.value}] {g.title} — {g.spent_usd:.2f}/{g.budget_usd:.2f} USD "
                 f"{board.progress(g.id)}" for g in board.goals.values() if g.owner_user_id == user_id]
        return "\n".join(lines) or "Chưa có goal nào."
    if cmd.name in ("help", "unknown"):
        return HELP
    # TODO: tasks, approve, reject, priority, budget, pause/resume/stop, agents, chat tự do
    return f"Lệnh /{cmd.name} chưa được hiện thực."


def run() -> None:  # pragma: no cover
    from telegram import Update
    from telegram.ext import Application, ContextTypes, MessageHandler, filters

    from agents.base import load_registry
    from board.repo import PostgresBoard
    from orchestrator.planner import Planner

    board = PostgresBoard(settings.database_url)
    planner = Planner(list(load_registry()))

    async def on_message(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        reply = handle(update.effective_user.id, update.message.text or "", board, planner)
        await update.message.reply_text(reply)

    app = Application.builder().token(settings.telegram_token).build()
    app.add_handler(MessageHandler(filters.TEXT, on_message))
    app.run_polling()
