"""Chạy toàn bộ luồng daily / checkin / report trên ERP giả."""

from datetime import date

import pytest

from eup_pm.config import load_settings
from eup_pm.erp import ErpError
from eup_pm.jobs import run_checkin, run_daily, run_report
from eup_pm.llm import unknown_numbers

from .fake_erp import FakeErp, sample_docs

TODAY = date(2026, 11, 4)


@pytest.fixture
def erp():
    return FakeErp(sample_docs(TODAY))


def test_daily_completes_task_by_evidence_and_alerts(erp):
    summary = run_daily(erp, load_settings(), today=TODAY)
    (_, res, created), = summary
    completed = [w for w in erp.writes if w[0] == "update" and w[1] == "Task" and w[2] == "T1"
                 and w[3].get("status") == "Completed"]
    assert completed, "T1 phải tự hoàn thành vì PO đã Approved"
    codes = {(a.rule_code, a.task) for a in res.alerts}
    assert ("R01", "T2") in codes      # Hàng về kho dự báo trễ, nằm trên đường găng
    assert ("R09", "T2") in codes      # có vướng mắc
    assert ("R02", "T5") in codes      # mốc chạy thử trễ hơn 3 ngày làm việc
    assert res.rag == "Đỏ"
    # ALERT-2611-0001 (R01, T2) đã có từ hôm qua nên không tạo lại
    inserted = {(w[2]["rule_code"], w[2]["task"]) for w in erp.writes if w[0] == "insert" and w[1] == "Nx Project Alert"}
    assert ("R01", "T2") not in inserted and ("R02", "T5") in inserted
    assert any("Cảnh báo ĐỎ" in subj for _, subj in erp.emails)


def test_agent_cannot_write_business_documents(erp):
    with pytest.raises(ErpError):
        erp.update("Purchase Order", "PO-2611-0042", {"workflow_state": "Cancelled"})
    with pytest.raises(ErpError):
        erp.update("Task", "T1", {"subject": "đổi tên"})


def test_checkin_groups_by_owner(erp):
    per_owner = run_checkin(erp, load_settings(), today=TODAY)
    assert set(per_owner) == {"kythuat@eup.vn"}
    assert len(erp.emails) == 1


def test_report_without_llm(erp):
    out = run_report(erp, load_settings(), today=TODAY, use_llm=False)
    (_, _, body), = out
    assert "RAG: Đỏ" in body and "Chạy thử không tải" in body


def test_number_guard():
    facts = {"spi": "0,85", "hạn": "12/11/2026", "trễ": 5}
    assert unknown_numbers("SPI 0,85, trễ 5 ngày, hạn 12/11/2026, có 2 phương án.", facts) == []
    assert unknown_numbers("Chi phí phát sinh 350 triệu.", facts) == ["350"]
