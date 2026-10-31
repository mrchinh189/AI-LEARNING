"""Xử lý tin nhắn dùng chung cho mọi kênh (web, Telegram...): định tuyến và trả lời / giao việc."""
import logging

from . import config, db, faq, router

log = logging.getLogger(__name__)

HELP = (f"Xin chào, tôi là {config.BOT_NAME}.\n"
        "- Hỏi trực tiếp để được trả lời nhanh từ tài liệu của công ty.\n"
        "- Gõ \"/sau <yêu cầu>\" để nhóm AI agent tìm hiểu sâu, làm báo cáo hoặc tạo ticket.\n"
        "- Gõ \"gặp nhân viên\" để chuyển cho nhân viên hỗ trợ.")


def _history_text(conversation_id: str) -> str:
    lines = []
    for m in db.recent_messages(conversation_id):
        who = "Người dùng" if m["role"] == "user" else "Trợ lý"
        lines.append(f"{who}: {m['content'][:500]}")
    return "\n".join(lines)


def handle_message(channel: str, external_id: str, text: str) -> dict:
    """Trả về {reply, route, task_id?}. Hàm chạy đồng bộ, mất khoảng 1-5 giây ở đường nhanh."""
    text = text.strip()
    conv = db.get_or_create_conversation(channel, external_id)

    if text in ("/start", "/help"):
        return {"route": "help", "reply": HELP}
    if text == "/bot":
        db.set_conversation_status(conv["id"], "bot")
        return {"route": "help", "reply": "Đã quay lại trợ lý tự động. " + HELP}
    if conv["status"] == "human":
        db.add_message(conv["id"], "user", text, route="human")
        return {"route": "human", "reply": "Nhân viên đã nhận tin nhắn và sẽ phản hồi sớm. Gõ /bot để quay lại trợ lý tự động."}

    history = _history_text(conv["id"])
    db.add_message(conv["id"], "user", text)
    try:
        if text.startswith("/sau"):
            text = text[len("/sau"):].strip() or "Hãy tìm hiểu sâu hơn câu hỏi trước của tôi"
            decision = {"route": "deep", "reason": "người dùng yêu cầu"}
        else:
            decision = router.route(text, history)

        if decision["route"] == "human":
            db.set_conversation_status(conv["id"], "human")
            reply = "Tôi đã chuyển cuộc trò chuyện cho nhân viên hỗ trợ. Bạn vui lòng chờ trong giây lát."
            result = {"route": "human", "reply": reply}
        elif decision["route"] == "deep":
            task_id = db.create_task(conv["id"], text, history)
            reply = f"Đã nhận yêu cầu (mã {task_id}). Nhóm AI agent đang xử lý, tôi sẽ báo tiến độ tại đây."
            result = {"route": "deep", "reply": reply, "task_id": task_id}
        else:
            reply = faq.answer(text, history)
            result = {"route": "fast", "reply": reply}
    except Exception:
        log.exception("Lỗi khi xử lý tin nhắn")
        reply = "Xin lỗi, hệ thống đang gặp sự cố. Bạn thử lại sau ít phút hoặc gõ \"gặp nhân viên\"."
        result = {"route": "error", "reply": reply}

    db.add_message(conv["id"], "assistant", reply, route=result["route"])
    return result


def task_visible_to(task_id: str, channel: str, external_id: str) -> bool:
    conv = db.conversation_for_task(task_id)
    return bool(conv) and conv["channel"] == channel and conv["external_id"] == external_id


def decide(channel: str, external_id: str, approval_id: str, approve: bool) -> dict | None:
    """Người dùng duyệt / từ chối một hành động. Trả None nếu không tồn tại hoặc không thuộc người này."""
    appr = db.get_approval(approval_id)
    if not appr or not task_visible_to(appr["task_id"], channel, external_id):
        return None
    if not db.decide_approval(approval_id, approve):
        return {"ok": False, "message": "Yêu cầu này đã được xử lý trước đó."}
    if approve:
        return {"ok": True, "message": "Đã duyệt. Hành động sẽ được thực hiện trong giây lát."}
    db.finish_approval(approval_id, "rejected", "Người dùng từ chối")
    db.add_event(appr["task_id"], "action_result", f"Đã hủy: {appr['summary']}", {"approval_id": approval_id})
    return {"ok": True, "message": "Đã hủy hành động."}
