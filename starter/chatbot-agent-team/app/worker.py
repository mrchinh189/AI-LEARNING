"""Worker: lấy tác vụ từ hàng đợi, chạy agent team, và thực thi các hành động đã được duyệt.

Chạy: python -m app.worker   (có thể chạy nhiều tiến trình song song để xử lý nhanh hơn)
"""
import json
import logging
import time
from functools import partial

from . import config, db
from .agents import action, orchestrator

log = logging.getLogger(__name__)


def process_task(task: dict) -> None:
    log.info("Bắt đầu tác vụ %s: %s", task["id"], task["request"][:80])
    emit = partial(db.add_event, task["id"])
    try:
        result = orchestrator.run(task, emit)
    except Exception as exc:
        log.exception("Tác vụ %s lỗi", task["id"])
        db.finish_task(task["id"], "failed", error=str(exc))
        emit("error", "Xin lỗi, tác vụ gặp lỗi và chưa hoàn thành. Bạn thử lại sau hoặc gõ \"gặp nhân viên\".")
        return
    db.finish_task(task["id"], "done", result=result)
    emit("result", result)
    db.add_message(task["conversation_id"], "assistant", result[:2000], route="deep")
    log.info("Xong tác vụ %s", task["id"])


def process_approval(appr: dict) -> None:
    emit = partial(db.add_event, appr["task_id"])
    try:
        output = action.execute(appr["action"], json.loads(appr["params"]))
    except Exception as exc:
        log.exception("Hành động %s lỗi", appr["id"])
        db.finish_approval(appr["id"], "failed", str(exc))
        emit("action_result", f"Thực hiện thất bại: {appr['summary']} ({exc})", {"approval_id": appr["id"]})
        return
    db.finish_approval(appr["id"], "done", output)
    emit("action_result", f"Đã thực hiện: {appr['summary']}\nKết quả: {output}", {"approval_id": appr["id"]})


def run_once() -> bool:
    """Xử lý tối đa một hành động đã duyệt và một tác vụ. Trả True nếu có việc đã làm."""
    did_work = False
    appr = db.claim_approved_action()
    if appr:
        process_approval(appr)
        did_work = True
    task = db.claim_next_task()
    if task:
        process_task(task)
        did_work = True
    return did_work


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db.init_db()
    stale = db.requeue_stale_tasks()
    if stale:
        log.info("Đưa lại %d tác vụ dở dang vào hàng đợi", stale)
    log.info("Worker sẵn sàng (FAKE_LLM=%s)", config.FAKE_LLM)
    while True:
        if not run_once():
            time.sleep(config.WORKER_POLL_SECONDS)


if __name__ == "__main__":
    main()
