"""Test đội agent với ERP giả và LLM giả: vòng lặp, policy, kiểm tra con số, phối hợp giữa các agent."""

import json
from datetime import date

import pytest

from eup_pm.agents import Team
from eup_pm.agents.base import Agent, Tool
from eup_pm.agents.planner import apply_plan
from eup_pm.config import load_settings

from .fake_erp import FakeErp, sample_docs
from .fake_llm import FakeLLM, call, text

TODAY = date(2026, 11, 4)


@pytest.fixture
def erp():
    return FakeErp(sample_docs(TODAY))


def team(erp, turns):
    llm = FakeLLM(turns)
    return Team(erp, load_settings(), llm, TODAY), llm


def writes(erp, kind, doctype):
    return [w for w in erp.writes if w[0] == kind and w[1] == doctype]


# ------------------------------------------------------------- ③ Thu thập

def test_tracker_updates_only_owned_tasks(erp):
    erp.docs["Task"]["T4"]["_assign"] = '["daotao@eup.vn"]'
    t, llm = team(erp, [
        [call("list_my_tasks")],
        [call("submit_updates", reply_text="x", updates=[
            {"task": "T4", "progress": 50, "forecast_end": "", "blocker": "", "quote": "đào tạo 50%"}])],
        [call("submit_updates", reply_text="Đã ghi nhận: Hàng về kho 60%, dự kiến 13/11.", updates=[
            {"task": "T2", "progress": 60, "forecast_end": "2026-11-13", "blocker": "", "quote": "hàng về 60%"}])],
    ])
    out = t.handle({"type": "reply", "from": "kythuat@eup.vn", "text": "hang ve 60%, chac 13/11 xong"})
    assert out["ok"] and out["kind"] == "updated" and out["tasks"] == ["T2"]
    # lần nộp đầu bị từ chối vì T4 không phải việc của người gửi
    rejected = llm.tool_results(2)[0]
    assert rejected.get("is_error") and "không phụ trách" in rejected["content"]
    upd = [w for w in writes(erp, "update", "Task") if w[2] == "T2"]
    assert upd and upd[0][3]["progress"] == 60 and upd[0][3]["custom_forecast_end"] == "2026-11-13"
    assert not [w for w in writes(erp, "update", "Task") if w[2] == "T4"]
    assert erp.emails[-1][0] == ["kythuat@eup.vn"]


def test_tracker_asks_when_message_is_vague(erp):
    t, _ = team(erp, [
        [call("list_my_tasks")],
        [call("ask_clarification", question="Anh/chị đang nói việc 'Hàng về kho' hay 'Lắp đặt khung máy'?")],
    ])
    out = t.handle({"type": "reply", "from": "kythuat@eup.vn", "text": "sắp xong rồi"})
    assert out["kind"] == "clarify"
    assert not writes(erp, "update", "Task")


def test_tracker_caps_evidence_task_at_90(erp):
    erp.docs["Task"]["T1"]["status"] = "Working"
    t, _ = team(erp, [
        [call("list_my_tasks")],
        [call("submit_updates", reply_text="ok", updates=[
            {"task": "T1", "progress": 100, "forecast_end": "", "blocker": "", "quote": "xong rồi"}])],
    ])
    t.handle({"type": "reply", "from": "kythuat@eup.vn", "text": "đặt máy xong rồi"})
    upd = [w for w in writes(erp, "update", "Task") if w[2] == "T1"][0][3]
    assert upd["progress"] == 90 and "status" not in upd


# ------------------------------------------------------------- ⑤ Rủi ro

def test_risk_rejects_unverified_numbers_then_saves(erp):
    t, llm = team(erp, [
        [call("get_task", task="T2"), call("get_document", doctype="Customs declaration", name="TK-1035")],
        [call("submit_analysis", alert="ALERT-2611-0001", root_cause="Tờ khai TK-1035 đang Chờ kiểm hóa.",
              impact="Lắp đặt trễ.", decision_owner_role="Giám đốc nhà máy", decide_by="06/11/2026",
              data_gaps="", options=[{"option": "Thuê thêm đội lắp, chi phí 350 triệu", "tradeoff": "tốn tiền"}])],
        [call("submit_analysis", alert="ALERT-2611-0001", root_cause="Tờ khai TK-1035 đang Chờ kiểm hóa.",
              impact="Lắp đặt khung máy và mốc Chạy thử không tải bị đẩy lùi.",
              decision_owner_role="Giám đốc nhà máy", decide_by="06/11/2026",
              data_gaps="Chi phí thuê đội lắp",
              options=[{"option": "Thuê thêm đội lắp để rút ngắn lắp đặt [CẦN DỮ LIỆU: chi phí]",
                        "tradeoff": "Tăng chi phí"},
                       {"option": "Dời mốc chạy thử", "tradeoff": "Trễ bàn giao"}])],
    ])
    out = t.handle({"type": "alert", "alert": "ALERT-2611-0001"})
    assert out["ok"]
    first = llm.tool_results(2)[0]
    assert first.get("is_error") and "350" in first["content"]
    saved = writes(erp, "update", "Nx Project Alert")
    assert len(saved) == 1 and saved[0][3]["analysed_by_agent"] == 1
    assert "TK-1035" in saved[0][3]["root_cause"]


def test_risk_cannot_read_unlisted_doctype(erp):
    t, llm = team(erp, [
        [call("get_document", doctype="Salary Slip", name="SAL-1")],
        [call("submit_analysis", alert="ALERT-2611-0001", root_cause="Chưa đủ dữ liệu", impact="—",
              decision_owner_role="PM", decide_by="", data_gaps="Thiếu chứng từ",
              options=[{"option": "Kiểm tra lại tờ khai", "tradeoff": "mất thời gian"}])],
    ])
    t.handle({"type": "alert", "alert": "ALERT-2611-0001"})
    r = llm.tool_results(1)[0]
    assert r.get("is_error") and "Không được đọc" in r["content"]


# ------------------------------------------------------------- ② Lập kế hoạch

PLAN = [
    {"key": "A1", "subject": "Chốt thông số", "duration_wd": 5, "depends_on": [], "owner_role": "Kỹ thuật",
     "is_milestone": False, "evidence": "", "done_criteria": "Biên bản chốt"},
    {"key": "A2", "subject": "Đặt hàng thiết bị", "duration_wd": 3, "depends_on": ["A1"], "owner_role": "Mua hàng",
     "is_milestone": False, "evidence": "Purchase Order · workflow_state = Approved", "done_criteria": "PO duyệt"},
    {"key": "A3", "subject": "Nghiệm thu", "duration_wd": 1, "depends_on": ["A2"], "owner_role": "QA",
     "is_milestone": True, "evidence": "", "done_criteria": "Biên bản nghiệm thu"},
]


def test_planner_drafts_then_human_applies(erp):
    erp.docs["Project"]["PROJ-0001"]["expected_start_date"] = TODAY.isoformat()
    t, llm = team(erp, [
        [call("get_project_info"), call("kb_list")],
        [call("kb_read", name="wbs-mau-DT-dau-tu-nha-may")],
        [call("check_schedule", tasks=PLAN)],
        [call("submit_plan", summary="3 việc, dự báo xong 13/11/2026.", assumptions="Thời lượng theo WBS mẫu.",
              tasks=PLAN)],
    ])
    out = t.handle({"type": "new_project", "project": "PROJ-0001"})
    assert out["ok"]
    sched = json.loads(llm.tool_results(3)[0]["content"])
    assert sched["dự_báo_kết_thúc"] == "13/11/2026" and sched["đường_găng"] == ["A1", "A2", "A3"]
    draft = writes(erp, "insert", "Nx Plan Draft")[0][2]
    assert draft["status"] == "Nháp" and draft["task_count"] == 3
    assert not writes(erp, "insert", "Task"), "agent không được tự tạo Task"

    # PM duyệt, người chạy apply-plan
    erp.docs["Nx Plan Draft"]["KH-1"] = {"name": "KH-1", **draft, "status": "Đã duyệt"}
    with pytest.raises(Exception):
        apply_plan(erp, "KH-1")          # client thường không được tạo Task
    erp.allow_task_create = True
    names = apply_plan(erp, "KH-1")
    created = writes(erp, "insert", "Task")
    assert len(names) == 3
    assert created[1][2]["depends_on"] == [{"task": names[0]}]
    assert created[2][2]["exp_start_date"] == "2026-11-13" and created[2][2]["is_milestone"] == 1


def test_apply_plan_requires_approval(erp):
    erp.allow_task_create = True
    erp.docs["Nx Plan Draft"]["KH-2"] = {"name": "KH-2", "project": "PROJ-0001", "status": "Nháp",
                                         "plan_json": "{}"}
    with pytest.raises(Exception, match="Đã duyệt"):
        apply_plan(erp, "KH-2")


# ------------------------------------------------------------- ① Điều phối

def test_orchestrator_delegates_to_risk_agent(erp):
    t, llm = team(erp, [
        # Điều phối
        [call("get_project_overview", project="PROJ-0001"), call("list_alerts", project="PROJ-0001")],
        [call("delegate_risk_analysis", alert="ALERT-2611-0001")],
        # Agent Rủi ro (được Điều phối gọi)
        [call("get_document", doctype="Customs declaration", name="TK-1035")],
        [call("submit_analysis", alert="ALERT-2611-0001", root_cause="Tờ khai TK-1035 đang Chờ kiểm hóa.",
              impact="Mốc chạy thử bị đẩy lùi.", decision_owner_role="Giám đốc nhà máy", decide_by="",
              data_gaps="", options=[{"option": "Làm việc với hải quan để ưu tiên kiểm hóa",
                                      "tradeoff": "Phụ thuộc bên ngoài"}])],
        # Điều phối trả lời
        [text("Dự án đang Đỏ vì tờ khai TK-1035 đang Chờ kiểm hóa. Cần Giám đốc nhà máy quyết phương án.")],
    ])
    out = t.handle({"type": "ask", "text": "Dự án dây chuyền ép số 3 sao rồi, vì sao trễ?"})
    assert "TK-1035" in out["answer"] and "chưa kiểm chứng" not in out["answer"]
    assert writes(erp, "update", "Nx Project Alert")
    # Điều phối không có tool ghi trực tiếp
    orch_tools = {tl["name"] for tl in llm.requests[0]["tools"]}
    assert not any(n.startswith(("submit", "erp_")) for n in orch_tools)


def test_orchestrator_flags_unverified_numbers(erp):
    t, _ = team(erp, [
        [call("get_project_overview", project="PROJ-0001")],
        [text("Dự án cần thêm 750 triệu.")],
    ])
    out = t.handle({"type": "ask", "text": "tình hình?"})
    assert "chưa kiểm chứng" in out["answer"] and "750" in out["answer"]


# ------------------------------------------------------------- khung agent

def test_agent_stops_at_turn_limit():
    loop = Tool("noop", "không làm gì", {}, lambda i: "ok")
    done = Tool("finish", "xong", {}, lambda i: "ok", final=True)
    llm = FakeLLM([[call("noop")]] * 3)
    res = Agent(llm, [loop, done], max_turns=3).run("thử")
    assert not res.ok and "Hết 3 lượt" in res.error


def test_tool_specs_are_strict(erp):
    t, llm = team(erp, [[call("list_my_tasks")], [call("ask_clarification", question="?")]])
    t.handle({"type": "reply", "from": "kythuat@eup.vn", "text": "?"})
    for spec in llm.requests[0]["tools"]:
        assert spec["strict"] and spec["input_schema"]["additionalProperties"] is False


def test_all_tool_results_returned_in_one_message(erp):
    t, llm = team(erp, [
        [call("get_task", task="T2"), call("get_predecessors", task="T5")],
        [call("submit_analysis", alert="ALERT-2611-0001", root_cause="Chưa đủ dữ liệu", impact="—",
              decision_owner_role="PM", decide_by="", data_gaps="", options=[{"option": "Theo dõi", "tradeoff": "—"}])],
    ])
    t.handle({"type": "alert", "alert": "ALERT-2611-0001"})
    assert len(llm.tool_results(1)) == 2


def test_audit_log_written(erp, tmp_path):
    s = load_settings()
    s.log_dir = tmp_path
    llm = FakeLLM([[call("list_my_tasks")], [call("ask_clarification", question="?")]])
    Team(erp, s, llm, TODAY).handle({"type": "reply", "from": "kythuat@eup.vn", "text": "?"})
    lines = [json.loads(x) for f in tmp_path.glob("audit-*.jsonl") for x in f.read_text().splitlines()]
    assert {x["event"] for x in lines} == {"start", "tool", "end"}
