from datetime import date

import yaml

from eup_pm.config import ROOT
from eup_pm.engine import (TaskData, WorkCalendar, compute_rag, critical_path, effective_progress,
                           evaluate_project, fmt_num, planned_fraction)

RULES = yaml.safe_load((ROOT / "config" / "rules.yaml").read_text(encoding="utf-8"))
MON = date(2026, 11, 2)  # Thứ Hai


def t(name, start, end, deps=(), **kw):
    return TaskData(name=name, subject=name, status=kw.pop("status", "Open"), progress=kw.pop("progress", 0),
                    exp_start=start, exp_end=end, depends_on=list(deps), **kw)


def test_calendar_skips_sunday_and_holidays():
    cal = WorkCalendar({date(2026, 11, 4)})  # Thứ Tư nghỉ lễ
    assert cal.workdays_between(MON, date(2026, 11, 8)) == 5   # T2,T3,T5,T6,T7
    assert cal.add(MON, 2) == date(2026, 11, 5)
    assert cal.offset(MON, date(2026, 11, 9)) == 5
    assert cal.offset(date(2026, 11, 9), MON) == -5


def test_planned_fraction_linear():
    cal = WorkCalendar()
    task = t("A", MON, date(2026, 11, 6))  # 5 ngày làm việc
    assert planned_fraction(task, cal, date(2026, 11, 1)) == 0
    assert planned_fraction(task, cal, date(2026, 11, 4)) == 3 / 5
    assert planned_fraction(task, cal, date(2026, 11, 6)) == 1


def test_evidence_caps_progress():
    a = t("A", MON, MON, progress=100, has_evidence=True, evidence_met=False)
    assert effective_progress(a) == 0.9
    a.evidence_met = True
    assert effective_progress(a) == 1.0


def test_critical_path_and_float():
    cal = WorkCalendar()
    # A(3 ngày) -> B(2 ngày) -> D ; A -> C(1 ngày) -> D(1 ngày)
    a = t("A", MON, date(2026, 11, 4))
    b = t("B", date(2026, 11, 5), date(2026, 11, 6), ["A"])
    c = t("C", date(2026, 11, 5), date(2026, 11, 5), ["A"])
    d = t("D", date(2026, 11, 7), date(2026, 11, 7), ["B", "C"])
    es, ef, tf, errors = critical_path([a, b, c, d], cal, MON)
    assert not errors
    assert tf["A"] == 0 and tf["B"] == 0 and tf["D"] == 0
    assert tf["C"] == 1
    assert ef["D"] == date(2026, 11, 7)


def test_late_task_pushes_successor_and_fires_r01():
    cal = WorkCalendar()
    a = t("A", MON, date(2026, 11, 4), forecast_end=date(2026, 11, 7), progress=50)
    b = t("B", date(2026, 11, 5), date(2026, 11, 6), ["A"])
    res = evaluate_project([a, b], cal, MON, RULES, deadline=date(2026, 11, 6))
    assert res.forecast_end == date(2026, 11, 10)
    assert res.slip_wd == 3
    codes = {(x.rule_code, x.task) for x in res.alerts}
    assert ("R01", "A") in codes and ("R01", "B") in codes
    assert res.rag == "Đỏ"


def test_cycle_reported_as_data_error_not_alert():
    cal = WorkCalendar()
    a = t("A", MON, MON, ["B"])
    b = t("B", MON, MON, ["A"])
    res = evaluate_project([a, b], cal, MON, RULES)
    assert res.data_errors and not res.alerts


def test_spi_and_rag():
    cal = WorkCalendar()
    a = t("A", date(2026, 10, 26), date(2026, 10, 31), status="Completed", progress=100)
    b = t("B", MON, date(2026, 11, 7), progress=0)
    res = evaluate_project([a, b], cal, date(2026, 11, 4), RULES)
    # KH: A 6/6 + B 3/6 trên tổng trọng số 12 = 0,75 ; TT: 6/12 = 0,5
    assert round(res.planned_pct, 3) == 0.75
    assert round(res.actual_pct, 3) == 0.5
    assert round(res.spi, 3) == 0.667
    assert compute_rag([], res.spi, RULES) == "Đỏ"


def test_vietnamese_number_format():
    assert fmt_num(1240.5, 1) == "1.240,5"
    assert fmt_num(0.85, 2) == "0,85"
