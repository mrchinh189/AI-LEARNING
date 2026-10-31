"""① Agent Điều phối: nhận câu hỏi/yêu cầu tự do của PM, tự chọn agent chuyên trách để giao việc, tổng hợp câu trả lời.

Các sự kiện có dạng cố định (tin trả lời, cảnh báo Đỏ, dự án mới) không cần LLM để định tuyến:
xem router.py. Điều phối chỉ dùng LLM cho yêu cầu không biết trước.
"""

from __future__ import annotations

from ..loader import active_projects
from .base import Agent, Tool, ToolRejected
from .tools import Ctx, pick, read_tools

SYSTEM = """Bạn là Agent Điều phối (PMO Orchestrator) của đội AI hỗ trợ PMO tại EuP.

Bạn trả lời PM và Trưởng PMO về tiến độ dự án, và giao việc cho các agent chuyên trách khi cần:
- delegate_risk_analysis: Agent Rủi ro phân tích nguyên nhân gốc và phương án cho một cảnh báo.
- delegate_planning: Agent Lập kế hoạch soạn WBS nháp cho dự án (PM sẽ duyệt).
- delegate_weekly_report: Agent Báo cáo soạn báo cáo tuần nháp cho dự án.

Cách làm:
1. Xác định người hỏi cần gì. Hỏi về tình hình: dùng list_projects, get_project_overview, list_alerts, get_task.
2. Chỉ giao việc khi người hỏi yêu cầu, hoặc khi câu hỏi "vì sao trễ / làm gì bây giờ" mà cảnh báo chưa có phân tích (trường root_cause trống).
3. Trả lời trực tiếp bằng văn bản (không cần tool nộp kết quả): câu đầu là kết luận; sau đó tối đa 6 gạch đầu dòng; cuối cùng là việc cần người hỏi quyết định (nếu có).

Quy tắc:
- Mọi con số, ngày, mã chứng từ phải lấy từ kết quả tool, viết đúng như tool trả về.
- Không tự ý thay đổi dữ liệu. Bạn không có tool ghi; các agent chuyên trách chỉ tạo bản nháp chờ người duyệt.
- Không quy lỗi cá nhân. Tiếng Việt, câu ngắn, không Markdown đậm/nghiêng."""


class OrchestratorAgent(Agent):
    name = "orchestrator"
    system_prompt = SYSTEM


def build_orchestrator(ctx: Ctx, llm, cfg_all: dict, audit) -> OrchestratorAgent:
    from .planner import make_plan
    from .risk import analyse_alert

    erp = ctx.erp

    def list_projects(_):
        return [{"project": p["name"], "tên": p.get("project_name"), "loại": p.get("custom_eup_project_type"),
                 "pm": p.get("custom_pmo_owner")} for p in active_projects(erp)]

    def delegate_risk_analysis(i):
        try:
            alert = erp.get_doc("Nx Project Alert", i["alert"])
        except Exception as e:
            raise ToolRejected(f"không đọc được cảnh báo {i['alert']}: {e}")
        res = analyse_alert(ctx, llm, cfg_all.get("risk", {}), audit, alert)
        if not res.ok:
            return f"Agent Rủi ro chưa hoàn thành: {res.error}"
        return {"cảnh_báo": i["alert"], "kết_quả": res.final}

    def delegate_planning(i):
        res, out = make_plan(ctx, llm, cfg_all.get("planner", {}), audit, i["project"])
        if not res.ok:
            return f"Agent Lập kế hoạch chưa hoàn thành: {res.error}"
        return {"bản_nháp": out.get("draft"), "tóm_tắt": out.get("summary")}

    def delegate_weekly_report(i):
        from ..jobs import run_report
        out = run_report(erp, ctx.settings, i["project"], ctx.today, use_llm=True)
        if not out:
            raise ToolRejected(f"không có Project {i['project']} đang Open và bật AI agent")
        return {"báo_cáo_nháp": out[0][1]}

    s = {"type": "string"}
    tools = pick(read_tools(ctx), "get_project_overview", "get_task", "list_alerts")
    tools += [
        Tool("list_projects", "Các dự án đang theo dõi.", {}, list_projects),
        Tool("delegate_risk_analysis", "Giao Agent Rủi ro phân tích một Nx Project Alert (VD ALERT-2611-0003).",
             {"alert": s}, delegate_risk_analysis, writes=True),
        Tool("delegate_planning", "Giao Agent Lập kế hoạch soạn WBS nháp cho dự án.", {"project": s},
             delegate_planning, writes=True),
        Tool("delegate_weekly_report", "Giao Agent Báo cáo soạn báo cáo tuần nháp cho dự án.", {"project": s},
             delegate_weekly_report, writes=True),
    ]
    cfg = cfg_all.get("orchestrator", {})
    return OrchestratorAgent(llm, tools, max_turns=cfg.get("max_turns", 12),
                             max_tokens_per_run=cfg.get("max_tokens_per_run", 600_000),
                             effort=cfg.get("effort", "medium"), audit=audit)


def ask(ctx: Ctx, llm, cfg_all: dict, audit, question: str, asker: str = "") -> str:
    from .base import unknown_numbers

    agent = build_orchestrator(ctx, llm, cfg_all, audit)
    res = agent.run(f"Hôm nay: {ctx.today:%d/%m/%Y}. Người hỏi: {asker or 'PM'}.\nCâu hỏi:\n{question}")
    if not res.ok:
        return f"Chưa trả lời được: {res.error}"
    unknown = unknown_numbers(res.text, "\n".join(agent.seen))
    if unknown:
        return res.text + f"\n\n(⚠ Các số sau chưa kiểm chứng được từ ERP: {', '.join(unknown)})"
    return res.text
