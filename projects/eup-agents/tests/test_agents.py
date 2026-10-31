import json
from datetime import date, timedelta

import pytest

from eup_agents import guard, llm
from eup_agents.agents import common, erp_watch, intake, nudge, report
from eup_agents.config import settings
from eup_agents.workdays import Calendar

from .fake_erp import FakeERP

TODAY = date(2026, 11, 4)  # thứ Tư
D = lambda n: str(TODAY + timedelta(days=n))  # noqa: E731


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "dry_run", False)
    monkeypatch.setattr(settings, "llm_enabled", False)
    monkeypatch.setattr(settings, "notify_backend", "erp_bell")
    monkeypatch.setattr(settings, "report_dir", tmp_path / "reports")
    org = tmp_path / "org.json"
    org.write_text(json.dumps({"department_heads": {"Kế toán": "tp@eup.vn"}}), encoding="utf-8")
    monkeypatch.setattr(settings, "org_file", org)
    monkeypatch.setattr(guard, "ACTION_LOG", tmp_path / "actions.jsonl")
    monkeypatch.setattr(common, "today", lambda: TODAY)
    for mod in (nudge, report, erp_watch, intake):
        monkeypatch.setattr(mod, "today", lambda: TODAY)


def task(name, due, **kw):
    return {"name": name, "subject": f"Việc {name}", "status": "Open", "priority": "Medium",
            "exp_end_date": due, "_assign": json.dumps(["nv@eup.vn"]), "owner": "sep@eup.vn",
            "department": "Kế toán", "company": None, "eup_escalation_level": 0, **kw}


# ---------- ngày làm việc ----------
def test_workdays_skip_sunday_and_holiday():
    cal = Calendar({date(2026, 11, 6)})  # thứ Sáu nghỉ lễ (giả định)
    assert cal.workdays_between(TODAY, date(2026, 11, 9)) == 3  # T5, T7, T2
    assert cal.workdays_between(date(2026, 11, 9), TODAY) == -3


# ---------- A2 nhắc việc ----------
def test_nudge_levels():
    cal = Calendar()
    assert nudge.level_for(task("a", D(2)), cal, TODAY) == 0
    assert nudge.level_for(task("a", D(5)), cal, TODAY) is None
    assert nudge.level_for(task("a", D(0)), cal, TODAY) == 1
    assert nudge.level_for(task("a", D(-1)), cal, TODAY) == 2
    assert nudge.level_for(task("a", D(-1), priority="Urgent"), cal, TODAY) == 3
    assert nudge.level_for(task("a", D(-3)), cal, TODAY) == 3
    assert nudge.level_for(task("a", None), cal, TODAY) is None


def test_nudge_groups_one_message_per_person_and_escalates():
    db = {"Task": [task("T1", D(1)), task("T2", D(-1)), task("T3", D(0)),
                   task("T4", D(-1), eup_confirm_state="Chờ xác nhận")]}
    erp = FakeERP(settings, db)
    out = nudge.run(erp)
    bells = db["Notification Log"]
    assert {b["for_user"] for b in bells} == {"nv@eup.vn", "tp@eup.vn"}
    assert len([b for b in bells if b["for_user"] == "nv@eup.vn"]) == 1  # gộp 3 việc vào 1 tin
    assert "T4" not in json.dumps(bells)  # việc chưa xác nhận không bị nhắc
    assert out["escalated"] == 1 and db["Task"][1]["eup_escalation_level"] == 2
    assert db["Comment"][0]["reference_name"] == "T2"


def test_nudge_afternoon_skips_level0():
    db = {"Task": [task("T1", D(1))]}
    assert nudge.run(FakeERP(settings, db), "afternoon")["items"] == 0


# ---------- Lớp Kiểm soát ----------
def test_guard_blocks_unsafe_writes():
    with pytest.raises(guard.GuardError):
        guard.check("x", "Purchase Invoice", "update", {})
    with pytest.raises(guard.GuardError):
        guard.check("x", "Task", "update", {"status": "Completed"})
    with pytest.raises(guard.GuardError):
        guard.check("x", "Task", "create", {"subject": "a", "eup_agent_created": 1})


def test_dry_run_sends_nothing(monkeypatch):
    monkeypatch.setattr(settings, "dry_run", True)
    db = {"Task": [task("T2", D(-1))]}
    erp = FakeERP(settings, db)
    nudge.run(erp)
    assert [c for c in erp.calls if c[0] != "GET"] == []
    assert db["Task"][0]["eup_escalation_level"] == 0


# ---------- A3 giám sát ERP ----------
def test_erp_watch_creates_tasks_once():
    db = {"Task": [],
          "Purchase Order": [{"name": "PO-1", "docstatus": 0, "owner": "mh@eup.vn", "company": "EUP",
                              "creation": D(-5)},
                             {"name": "PO-2", "docstatus": 0, "owner": "mh@eup.vn", "company": "EUP",
                              "creation": D(-1)}],
          "Purchase Receipt": [{"name": "PR-1", "docstatus": 1, "per_billed": 0, "posting_date": D(-10),
                                "owner": "kho@eup.vn", "company": "EUP", "supplier": "NCC A"}]}
    erp = FakeERP(settings, db)
    assert erp_watch.run(erp) == {"created": 2, "skipped_existing": 0}
    t = db["Task"][0]
    assert t["eup_confirm_state"] == "Chờ xác nhận" and t["eup_source_ref"] == "Purchase Order::PO-1"
    assert json.loads(t["_assign"]) == ["mh@eup.vn"]
    for t in db["Task"]:
        t["status"] = "Open"
    assert erp_watch.run(erp) == {"created": 0, "skipped_existing": 2}


# ---------- A5 báo cáo ----------
def test_report_counts(tmp_path):
    db = {"Task": [task("T1", D(-2)), task("T2", None),
                   task("T3", D(-1), status="Completed", completed_on=D(-2), creation=D(-3)),
                   task("T4", D(-3), status="Completed", completed_on=D(-1), creation=D(-10))]}
    for t in db["Task"]:
        t.setdefault("creation", D(-20))
    out = report.run(FakeERP(settings, db))
    md = open(out["files"][0], encoding="utf-8").read()
    assert "| Việc trễ hạn đang mở | 1 |" in md
    assert "| Việc hoàn thành trong tuần | 2 (đúng hạn 50%) |" in md
    assert "| Việc thiếu hạn / thiếu người phụ trách | 1 / 0 |" in md


# ---------- A1 tiếp nhận ----------
def test_intake_creates_unconfirmed_drafts(monkeypatch):
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(llm, "ask", lambda *a, **k: {"tasks": [
        {"subject": "Đối chiếu công nợ nội bộ T10", "owner": "nv@eup.vn", "due_date": D(2),
         "priority": "High", "company": "", "definition_of_done": "Biên bản ký 2 bên", "confidence": 0.9},
        {"subject": "Lập danh sách phiếu nhập chưa có hóa đơn", "owner": "nguoila@ngoai.com",
         "due_date": "", "priority": "Medium", "company": "", "definition_of_done": "Danh sách",
         "confidence": 0.6}]})
    db = {"Task": [], "User": [{"name": "nv@eup.vn"}, {"name": "sep@eup.vn"}]}
    out = intake.run(FakeERP(settings, db), "email...", "sep@eup.vn")
    assert len(out["created"]) == 2
    a, b = db["Task"]
    assert a["eup_confirm_state"] == b["eup_confirm_state"] == "Chờ xác nhận"
    assert json.loads(a["_assign"]) == ["nv@eup.vn"] and "_assign" not in b
    assert "Hạn do agent đề xuất" in b["description"] and "Độ tin cậy thấp" in b["description"]
