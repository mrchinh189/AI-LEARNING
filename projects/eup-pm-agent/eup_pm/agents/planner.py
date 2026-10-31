"""② Agent Lập kế hoạch: sinh WBS nháp cho dự án mới từ kho tri thức, PM duyệt rồi mới tạo Task."""

from __future__ import annotations

import json
import logging
from datetime import date

from ..engine import TaskData, WorkCalendar, critical_path, fmt_date
from ..erp import ErpClient, ErpError
from ..loader import calendar_for, parse_date
from .base import Agent, Tool, ToolRejected
from .tools import Ctx, pick, read_tools

log = logging.getLogger("eup_pm.planner")

SYSTEM = """Bạn là Agent Lập kế hoạch trong đội AI hỗ trợ PMO của EuP, tập đoàn sản xuất và thương mại chạy ERP EuP.

Nhiệm vụ: lập kế hoạch nháp (WBS) cho một dự án để PM duyệt.

Cách làm:
1. get_project_info để biết loại dự án, mốc, phạm vi PM đã ghi.
2. kb_list rồi kb_read WBS mẫu đúng loại dự án và bản đồ chứng từ bằng chứng.
3. Cụ thể hóa WBS cho dự án này:
   - Mỗi việc có một vai trò chịu trách nhiệm, dài 1–10 ngày làm việc, có tiêu chí xong rõ ràng.
   - key ngắn, duy nhất (VD "A1", "A2"); depends_on là danh sách key phải xong trước.
   - Mốc quan trọng là việc 1 ngày, is_milestone = true.
   - evidence: chứng từ ERP chứng minh việc xong, dạng "Doctype · trường = giá trị" lấy từ bản đồ chứng từ; không có thì "".
4. Gọi check_schedule để engine tính ngày bắt đầu/kết thúc và đường găng. Nếu không kịp hạn, điều chỉnh (làm song song, tách việc) và kiểm tra lại, tối đa 3 lần.
5. Nộp bằng submit_plan. summary nêu: số việc, ngày dự báo kết thúc so với hạn, đường găng, các giả định chính.

Quy tắc:
- Thời lượng không có căn cứ trong kho tri thức thì ghi rõ trong assumptions là giả định.
- Không ghi tên người; chỉ ghi vai trò (Mua hàng, Kỹ thuật, Logistics, Kế toán, QA, IT...).
- Tiếng Việt, ngắn gọn. Mọi con số trong summary phải lấy từ kết quả check_schedule hoặc dữ liệu dự án."""


class PlannerAgent(Agent):
    name = "planner"
    system_prompt = SYSTEM


def schedule_draft(tasks: list[dict], cal: WorkCalendar, start: date) -> dict:
    """Tính ngày cho WBS nháp bằng forward pass theo ngày làm việc. Trả về ngày từng việc, đường găng, lỗi."""
    keys = [t["key"] for t in tasks]
    errors = []
    if len(set(keys)) != len(keys):
        errors.append("key bị trùng")
    by = {t["key"]: t for t in tasks}
    for t in tasks:
        for p in t["depends_on"]:
            if p not in by:
                errors.append(f"{t['key']} phụ thuộc key không tồn tại: {p}")
        if not 1 <= t["duration_wd"] <= 10:
            errors.append(f"{t['key']} dài {t['duration_wd']} ngày, phải từ 1 đến 10 ngày làm việc")
    if errors:
        return {"lỗi": errors}

    first = cal.next_workday(start)
    es, ef, order, pending = {}, {}, [], list(keys)
    while pending:
        ready = [k for k in pending if all(p in ef for p in by[k]["depends_on"])]
        if not ready:
            return {"lỗi": ["phụ thuộc bị vòng lặp: " + ", ".join(pending)]}
        for k in ready:
            es[k] = max([0] + [ef[p] + 1 for p in by[k]["depends_on"]])
            ef[k] = es[k] + by[k]["duration_wd"] - 1
            order.append(k)
            pending.remove(k)

    dates = {k: (cal.add(first, es[k]), cal.add(first, ef[k])) for k in keys}
    data = [TaskData(name=k, subject=by[k]["subject"], status="Open", progress=0,
                     exp_start=dates[k][0], exp_end=dates[k][1], depends_on=by[k]["depends_on"])
            for k in keys]
    _, _, tf, errs = critical_path(data, cal, first)
    end = max(d[1] for d in dates.values())
    return {
        "order": order,
        "dates": {k: (dates[k][0].isoformat(), dates[k][1].isoformat()) for k in keys},
        "critical": [k for k in order if tf.get(k, 1) <= 0],
        "end": end.isoformat(),
        "lỗi": errs,
    }


def build_planner_agent(ctx: Ctx, llm, cfg: dict, audit, project: str) -> PlannerAgent:
    erp = ctx.erp
    p = erp.get_doc("Project", project)
    cal = calendar_for(erp, p.get("company"))
    start = parse_date(p.get("expected_start_date")) or ctx.today
    deadline = parse_date(p.get("custom_baseline_end")) or parse_date(p.get("expected_end_date"))
    result: dict = {}

    def get_project_info(_):
        existing = erp.get_list("Task", filters=[["project", "=", project]], fields=["name", "subject", "status"])
        return {
            "project": project, "tên": p.get("project_name"), "loại": p.get("custom_eup_project_type"),
            "công_ty": p.get("company"), "bắt_đầu": fmt_date(start), "hạn": fmt_date(deadline),
            "ghi_chú_phạm_vi": (p.get("notes") or "")[:3000],
            "task_đã_có": existing,
        }

    def check_schedule(i):
        out = schedule_draft(i["tasks"], cal, start)
        if out.get("lỗi") and "dates" not in out:
            return out
        end = date.fromisoformat(out["end"])
        return {
            "dự_báo_kết_thúc": fmt_date(end),
            "hạn": fmt_date(deadline),
            "kịp_hạn": deadline is None or end <= deadline,
            "trễ_ngày_làm_việc": max(cal.offset(deadline, end), 0) if deadline else 0,
            "đường_găng": out["critical"],
            "lịch": {k: f"{fmt_date(date.fromisoformat(a))} → {fmt_date(date.fromisoformat(b))}"
                     for k, (a, b) in out["dates"].items()},
            "lỗi": out["lỗi"],
        }

    def submit_plan(i):
        out = schedule_draft(i["tasks"], cal, start)
        if "dates" not in out or out["lỗi"]:
            raise ToolRejected("kế hoạch còn lỗi: " + "; ".join(out.get("lỗi", [])))
        agent.check_numbers(i["summary"], i["assumptions"])
        plan = {"start": start.isoformat(), "tasks": i["tasks"], "schedule": out}
        doc = erp.insert("Nx Plan Draft", {
            "project": project, "status": "Nháp",
            "summary": i["summary"], "assumptions": i["assumptions"],
            "task_count": len(i["tasks"]), "forecast_end": out["end"],
            "plan_json": json.dumps(plan, ensure_ascii=False, indent=1),
        })
        result.update(draft=doc["name"], summary=i["summary"])
        if p.get("custom_pmo_owner"):
            erp.send_email([p["custom_pmo_owner"]], f"[Cần duyệt] Kế hoạch nháp {p.get('project_name') or project}",
                           f"<p>{i['summary']}</p><p><a href='{erp.link('Nx Plan Draft', doc['name'])}'>"
                           f"Mở bản kế hoạch nháp</a></p>")
        return f"Đã lưu kế hoạch nháp {doc['name']} ({len(i['tasks'])} việc), chờ PM duyệt."

    s = {"type": "string"}
    task_schema = {"type": "array", "items": {
        "type": "object",
        "properties": {"key": s, "subject": s, "duration_wd": {"type": "integer"},
                       "depends_on": {"type": "array", "items": s}, "owner_role": s,
                       "is_milestone": {"type": "boolean"}, "evidence": s, "done_criteria": s},
        "required": ["key", "subject", "duration_wd", "depends_on", "owner_role", "is_milestone",
                     "evidence", "done_criteria"],
        "additionalProperties": False}}
    tools = pick(read_tools(ctx), "kb_list", "kb_read")
    tools += [
        Tool("get_project_info", "Thông tin dự án cần lập kế hoạch và các Task đã có.", {}, get_project_info),
        Tool("check_schedule", "Engine tính lịch theo ngày làm việc, đường găng, kiểm tra kịp hạn. Không ghi gì.",
             {"tasks": task_schema}, check_schedule),
        Tool("submit_plan", "Lưu kế hoạch nháp để PM duyệt. Gọi một lần khi lịch đã ổn.",
             {"summary": s, "assumptions": s, "tasks": task_schema}, submit_plan, final=True, writes=True),
    ]
    agent = PlannerAgent(llm, tools, max_turns=cfg.get("max_turns", 16),
                         max_tokens_per_run=cfg.get("max_tokens_per_run", 400_000),
                         effort=cfg.get("effort", "high"), audit=audit)
    agent.result = result
    return agent


def make_plan(ctx: Ctx, llm, cfg: dict, audit, project: str):
    agent = build_planner_agent(ctx, llm, cfg, audit, project)
    res = agent.run(f"Lập kế hoạch nháp cho dự án {project}. Hôm nay: {ctx.today:%d/%m/%Y}.")
    return res, agent.result


def apply_plan(erp: ErpClient, draft_name: str) -> list[str]:
    """Tạo Task từ kế hoạch nháp PM đã duyệt. Lệnh này do người chạy, không phải agent."""
    draft = erp.get_doc("Nx Plan Draft", draft_name)
    if draft.get("status") != "Đã duyệt":
        raise ErpError(f"Kế hoạch {draft_name} đang ở trạng thái '{draft.get('status')}', cần 'Đã duyệt'")
    plan = json.loads(draft["plan_json"])
    by = {t["key"]: t for t in plan["tasks"]}
    sched = plan["schedule"]
    names: dict[str, str] = {}
    for key in sched["order"]:
        t = by[key]
        start, end = sched["dates"][key]
        desc = (f"<p>Tiêu chí xong: {t['done_criteria']}</p><p>Vai trò phụ trách: {t['owner_role']}</p>"
                + (f"<p>Bằng chứng gợi ý: {t['evidence']}</p>" if t["evidence"] else ""))
        doc = erp.insert("Task", {
            "subject": t["subject"], "project": draft["project"], "status": "Open",
            "exp_start_date": start, "exp_end_date": end,
            "custom_baseline_start": start, "custom_baseline_end": end,
            "is_milestone": int(t["is_milestone"]), "description": desc,
            "depends_on": [{"task": names[d]} for d in t["depends_on"]],
        })
        names[key] = doc["name"]
    erp.update("Nx Plan Draft", draft_name, {"status": "Đã áp dụng"})
    erp.update("Project", draft["project"], {"custom_forecast_end": sched["end"]})
    log.info("Đã tạo %d Task từ %s", len(names), draft_name)
    return list(names.values())
