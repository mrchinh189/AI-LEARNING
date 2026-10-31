"""Orchestrator: lập kế hoạch, giao việc cho các agent chuyên trách, tổng hợp và cho Reviewer kiểm tra.

Luồng được điều khiển bằng code (supervisor) để dễ đoán, dễ debug và giới hạn được chi phí.
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from .. import config, db, llm
from . import action, research, reviewer

log = logging.getLogger(__name__)

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "plan_summary": {"type": "string"},
        "subtasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string", "enum": ["research", "action"]},
                    "goal": {"type": "string"},
                },
                "required": ["agent", "goal"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["plan_summary", "subtasks"],
    "additionalProperties": False,
}

PLAN_SYSTEM = """Bạn là Orchestrator của một nhóm AI agent. Lập kế hoạch cho YÊU CẦU bằng cách giao việc cho:
- research: tìm hiểu thông tin trên web về một chủ đề cụ thể (tối đa 3 việc, mỗi việc một hướng riêng, chạy song song).
- action: thực hiện một hành động ghi như tạo ticket hoặc gửi email (tối đa 1 việc; người dùng sẽ duyệt trước khi chạy).
Chỉ tạo việc thật sự cần. Câu hỏi đơn giản có thể không cần việc nào.
plan_summary: một câu tiếng Việt cho người dùng biết bạn sẽ làm gì."""

WRITE_SYSTEM = """Bạn là Orchestrator, viết câu trả lời cuối cùng cho người dùng bằng tiếng Việt dựa trên KẾT QUẢ của các agent.
- Mở đầu bằng kết luận chính, sau đó là chi tiết có cấu trúc (tiêu đề ngắn, gạch đầu dòng, bảng nếu cần).
- Giữ lại đường link nguồn từ kết quả nghiên cứu. Không bịa thông tin không có trong kết quả.
- Nếu có hành động đang chờ duyệt, nhắc người dùng duyệt."""


def _fake_plan(request: str) -> dict:
    lower = request.lower()
    agent = "action" if any(k in lower for k in ("ticket", "email")) else "research"
    return {"plan_summary": f"[FAKE_LLM] Giao cho {agent} agent.", "subtasks": [{"agent": agent, "goal": request}]}


def _write(request: str, findings: list[tuple[str, str]], pending: list[str], feedback: str = "",
           previous: str = "") -> str:
    parts = [f"YÊU CẦU:\n{request}"]
    parts += [f"KẾT QUẢ NGHIÊN CỨU — {goal}:\n{result}" for goal, result in findings]
    if pending:
        parts.append("HÀNH ĐỘNG ĐANG CHỜ NGƯỜI DÙNG DUYỆT:\n" + "\n".join(f"- {p}" for p in pending))
    if feedback:
        parts.append(f"BẢN NHÁP TRƯỚC:\n{previous}\n\nGÓP Ý CỦA REVIEWER (hãy sửa theo):\n{feedback}")
    return llm.ask_text(
        config.MODEL_ORCHESTRATOR, WRITE_SYSTEM, "\n\n".join(parts), effort="medium",
        fake=lambda: "[FAKE_LLM] Báo cáo tổng hợp.\n\n" + "\n".join(r for _, r in findings)
        + ("\n\nĐang chờ bạn duyệt: " + "; ".join(pending) if pending else ""),
    ).text


def run(task: dict, emit) -> str:
    """emit(kind, message, data=None) ghi sự kiện tiến độ để gateway gửi về cho người dùng."""
    request, context = task["request"], task.get("context") or ""

    plan = llm.ask_json(config.MODEL_ORCHESTRATOR, PLAN_SYSTEM,
                        f"BỐI CẢNH HỘI THOẠI:\n{context or '(trống)'}\n\nYÊU CẦU: {request}",
                        PLAN_SCHEMA, effort="medium", fake=lambda: _fake_plan(request))
    emit("progress", "Kế hoạch: " + plan["plan_summary"])
    research_goals = [s["goal"] for s in plan["subtasks"] if s["agent"] == "research"][:3]
    action_goals = [s["goal"] for s in plan["subtasks"] if s["agent"] == "action"][:1]

    findings: list[tuple[str, str]] = []
    if research_goals:
        emit("progress", f"Research agent đang tìm hiểu {len(research_goals)} hướng song song...")

        def _safe_research(goal: str) -> str:
            try:
                return research.run(goal, context)
            except Exception as exc:  # một nhánh lỗi không làm hỏng cả tác vụ
                log.exception("Research lỗi: %s", goal)
                return f"(Không hoàn thành được phần này: {exc})"

        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(_safe_research, research_goals))
        findings = list(zip(research_goals, results))
        emit("progress", "Đã có kết quả nghiên cứu, đang tổng hợp...")

    pending: list[str] = []
    for goal in action_goals:
        proposal = action.propose(goal, f"{context}\n{request}")
        if proposal["action"] == "none":
            pending.append(f"Chưa thực hiện được hành động: {proposal['summary']}")
            continue
        approval_id = db.create_approval(task["id"], proposal["action"], proposal["params"], proposal["summary"])
        emit("approval", proposal["summary"], {
            "approval_id": approval_id, "action": proposal["action"],
            "params": {k: v for k, v in proposal["params"].items() if v},
        })
        pending.append(proposal["summary"])

    draft = _write(request, findings, pending)
    for _ in range(config.MAX_REVIEW_ROUNDS):
        verdict = reviewer.review(request, draft)
        if verdict["verdict"] == "pass":
            break
        emit("progress", "Reviewer yêu cầu chỉnh sửa, đang sửa bản nháp...")
        draft = _write(request, findings, pending, feedback=verdict["feedback"], previous=draft)
    return draft
