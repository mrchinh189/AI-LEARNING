"""Engine tính toán tất định: lịch làm việc, đường găng (CPM), % kế hoạch/thực tế, SPI, quy tắc cảnh báo, RAG.

Module này không gọi ERP và không gọi LLM, nên kiểm thử được hoàn toàn bằng dữ liệu giả (xem tests/).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta


# ---------------------------------------------------------------- lịch làm việc

class WorkCalendar:
    """Ngày làm việc = mọi ngày trừ Chủ nhật và các ngày trong Holiday List."""

    def __init__(self, holidays: set[date] | None = None, weekly_off: tuple[int, ...] = (6,)):
        self.holidays = holidays or set()
        self.weekly_off = weekly_off  # 0 = Thứ Hai ... 6 = Chủ nhật

    def is_workday(self, d: date) -> bool:
        return d.weekday() not in self.weekly_off and d not in self.holidays

    def next_workday(self, d: date) -> date:
        while not self.is_workday(d):
            d += timedelta(days=1)
        return d

    def offset(self, start: date, d: date) -> int:
        """Số ngày làm việc từ `start` tới `d`. offset(start, start) = 0; âm nếu d ở trước start."""
        if d == start:
            return 0
        step = 1 if d > start else -1
        n, cur = 0, start
        while cur != d:
            cur += timedelta(days=step)
            if self.is_workday(cur):
                n += step
        return n

    def add(self, start: date, n: int) -> date:
        """Ngày làm việc thứ n tính từ `start` (n = 0 là chính `start` nếu đó là ngày làm việc)."""
        cur = self.next_workday(start)
        step = 1 if n >= 0 else -1
        for _ in range(abs(n)):
            cur += timedelta(days=step)
            while not self.is_workday(cur):
                cur += timedelta(days=step)
        return cur

    def workdays_between(self, a: date, b: date) -> int:
        """Số ngày làm việc trong khoảng [a, b], tính cả hai đầu."""
        if b < a:
            return 0
        return sum(1 for i in range((b - a).days + 1) if self.is_workday(a + timedelta(days=i)))


# ---------------------------------------------------------------- dữ liệu

@dataclass
class TaskData:
    name: str
    subject: str
    status: str                      # Open, Working, Pending Review, Overdue, Template, Completed, Cancelled
    progress: float                  # 0–100
    exp_start: date | None
    exp_end: date | None
    baseline_start: date | None = None
    baseline_end: date | None = None
    forecast_end: date | None = None
    weight: float | None = None
    is_milestone: bool = False
    is_group: bool = False
    depends_on: list[str] = field(default_factory=list)
    last_update: date | None = None
    blocker: str = ""
    owners: list[str] = field(default_factory=list)
    has_evidence: bool = False
    evidence_met: bool = False
    evidence_rejected: bool = False

    @property
    def done(self) -> bool:
        return self.status in ("Completed", "Cancelled")

    @property
    def plan_start(self) -> date | None:
        return self.baseline_start or self.exp_start

    @property
    def plan_end(self) -> date | None:
        return self.baseline_end or self.exp_end


@dataclass
class TaskResult:
    name: str
    early_start: date | None
    early_finish: date | None
    total_float: int | None
    critical: bool
    planned_pct: float
    actual_pct: float
    weight: float


@dataclass
class Alert:
    rule_code: str
    severity: str
    task: str | None
    facts: str


@dataclass
class ProjectResult:
    as_of: date
    planned_pct: float
    actual_pct: float
    spi: float | None
    forecast_end: date | None
    deadline: date | None
    slip_wd: int | None
    rag: str
    tasks: dict[str, TaskResult]
    alerts: list[Alert]
    data_errors: list[str]


# ---------------------------------------------------------------- tiến độ

def effective_progress(t: TaskData, cap_until_met: float = 90) -> float:
    """Tiến độ dùng để tính toán (0–1). Task có bằng chứng: chưa đạt thì tối đa `cap`, đạt thì 100%."""
    if t.status == "Completed":
        if t.has_evidence and not t.evidence_met:
            return min(t.progress, cap_until_met) / 100
        return 1.0
    if t.has_evidence:
        if t.evidence_met:
            return 1.0
        return min(t.progress, cap_until_met) / 100
    return max(0.0, min(t.progress, 100)) / 100


def planned_fraction(t: TaskData, cal: WorkCalendar, as_of: date) -> float:
    """% kế hoạch của task tại ngày `as_of`, tăng tuyến tính theo ngày làm việc từ plan_start tới plan_end."""
    start, end = t.plan_start, t.plan_end
    if not start or not end:
        return 0.0
    if as_of < start:
        return 0.0
    if as_of >= end:
        return 1.0
    total = cal.workdays_between(start, end)
    if total <= 0:
        return 1.0
    return cal.workdays_between(start, as_of) / total


def task_weight(t: TaskData, cal: WorkCalendar) -> float:
    if t.weight:
        return float(t.weight)
    if t.plan_start and t.plan_end:
        return float(max(cal.workdays_between(t.plan_start, t.plan_end), 1))
    return 1.0


# ---------------------------------------------------------------- CPM

def critical_path(tasks: list[TaskData], cal: WorkCalendar, as_of: date):
    """Trả về (early_start, early_finish, total_float, lỗi dữ liệu) cho các task chưa xong.

    Thời lượng còn lại của task = từ max(hôm nay, ngày bắt đầu) tới ngày dự báo xong (hoặc ngày kết thúc
    kế hoạch). Mốc thời gian quy đổi ra số ngày làm việc kể từ `as_of`.
    """
    by_name = {t.name: t for t in tasks if not t.is_group}
    open_tasks = {n: t for n, t in by_name.items() if not t.done}
    errors: list[str] = []
    today = cal.next_workday(as_of)

    dur: dict[str, int] = {}
    earliest: dict[str, int] = {}
    for n, t in open_tasks.items():
        finish = t.forecast_end or t.exp_end
        if not finish:
            errors.append(f"Task {n} ({t.subject}) chưa có ngày kết thúc kế hoạch")
            continue
        s = max(0, cal.offset(today, t.exp_start)) if t.exp_start else 0
        f = max(cal.offset(today, finish), s)
        dur[n] = f - s + 1
        earliest[n] = s

    preds = {n: [p for p in by_name[n].depends_on if p in dur] for n in dur}
    for n in dur:
        for p in by_name[n].depends_on:
            if p not in by_name:
                errors.append(f"Task {n} phụ thuộc task {p} không thuộc dự án")

    order = _topo_sort(list(dur), preds)
    if order is None:
        errors.append("Phụ thuộc giữa các task bị vòng lặp, không tính được đường găng")
        return {}, {}, {}, errors

    es: dict[str, int] = {}
    ef: dict[str, int] = {}
    for n in order:
        es[n] = max([earliest[n]] + [ef[p] + 1 for p in preds[n]])
        ef[n] = es[n] + dur[n] - 1

    if not ef:
        return {}, {}, {}, errors

    project_end = max(ef.values())
    succs: dict[str, list[str]] = {n: [] for n in dur}
    for n in dur:
        for p in preds[n]:
            succs[p].append(n)
    ls: dict[str, int] = {}
    for n in reversed(order):
        lf = min([ls[s] - 1 for s in succs[n]], default=project_end)
        ls[n] = lf - dur[n] + 1

    early_start = {n: cal.add(today, es[n]) for n in dur}
    early_finish = {n: cal.add(today, ef[n]) for n in dur}
    total_float = {n: ls[n] - es[n] for n in dur}
    return early_start, early_finish, total_float, errors


def _topo_sort(nodes: list[str], preds: dict[str, list[str]]) -> list[str] | None:
    indeg = {n: len(preds[n]) for n in nodes}
    succs: dict[str, list[str]] = {n: [] for n in nodes}
    for n in nodes:
        for p in preds[n]:
            succs[p].append(n)
    queue = sorted(n for n in nodes if indeg[n] == 0)
    out: list[str] = []
    while queue:
        n = queue.pop(0)
        out.append(n)
        for s in succs[n]:
            indeg[s] -= 1
            if indeg[s] == 0:
                queue.append(s)
    return out if len(out) == len(nodes) else None


# ---------------------------------------------------------------- tổng hợp dự án

def evaluate_project(tasks: list[TaskData], cal: WorkCalendar, as_of: date, rules: dict,
                     deadline: date | None = None) -> ProjectResult:
    cap = rules.get("evidence", {}).get("progress_cap_until_met", 90)
    leaves = [t for t in tasks if not t.is_group and t.status != "Cancelled"]

    es, ef, tf, errors = critical_path(leaves, cal, as_of)

    results: dict[str, TaskResult] = {}
    sum_w = sum_plan = sum_act = 0.0
    for t in leaves:
        w = task_weight(t, cal)
        p = planned_fraction(t, cal, as_of)
        a = effective_progress(t, cap)
        sum_w += w
        sum_plan += w * p
        sum_act += w * a
        results[t.name] = TaskResult(
            name=t.name,
            early_start=es.get(t.name),
            early_finish=ef.get(t.name),
            total_float=tf.get(t.name),
            critical=tf.get(t.name) is not None and tf[t.name] <= 0,
            planned_pct=p,
            actual_pct=a,
            weight=w,
        )

    planned = sum_plan / sum_w if sum_w else 0.0
    actual = sum_act / sum_w if sum_w else 0.0
    spi = actual / planned if planned > 0 else None
    forecast_end = max(ef.values()) if ef else None
    slip = None
    if forecast_end and deadline:
        slip = cal.offset(deadline, forecast_end)

    alerts = [] if errors else _apply_rules(leaves, results, cal, as_of, rules, spi)
    rag = compute_rag(alerts, spi, rules)
    return ProjectResult(as_of, planned, actual, spi, forecast_end, deadline, slip, rag,
                         results, alerts, errors)


def _apply_rules(tasks: list[TaskData], res: dict[str, TaskResult], cal: WorkCalendar,
                 as_of: date, rules: dict, spi: float | None) -> list[Alert]:
    cfg = rules.get("rules", {})
    out: list[Alert] = []

    def on(code: str) -> dict | None:
        r = cfg.get(code)
        return r if r and r.get("enabled") else None

    for t in tasks:
        r = res[t.name]
        if t.done and not (t.has_evidence and not t.evidence_met):
            continue
        if (c := on("R01_critical_task_late")) and r.critical and r.early_finish and t.exp_end \
                and r.early_finish > t.exp_end:
            late = cal.offset(t.exp_end, r.early_finish)
            out.append(Alert("R01", c["severity"], t.name,
                             f"Việc trên đường găng '{t.subject}' dự báo xong {_d(r.early_finish)}, "
                             f"trễ {late} ngày làm việc so với hạn {_d(t.exp_end)}."))
        if (c := on("R02_milestone_slip")) and t.is_milestone and r.early_finish and t.plan_end:
            slip = cal.offset(t.plan_end, r.early_finish)
            if slip > c.get("threshold_wd", 3):
                out.append(Alert("R02", c["severity"], t.name,
                                 f"Mốc '{t.subject}' dự báo {_d(r.early_finish)}, trễ {slip} ngày làm việc "
                                 f"so với baseline {_d(t.plan_end)}."))
        if (c := on("R03_float_low")) and not r.critical and r.total_float is not None \
                and r.total_float < c.get("threshold_wd", 2):
            out.append(Alert("R03", c["severity"], t.name,
                             f"Việc '{t.subject}' chỉ còn {r.total_float} ngày làm việc dự phòng."))
        if (c := on("R04_evidence_mismatch")) and t.has_evidence and not t.evidence_met \
                and not t.evidence_rejected and (t.status == "Completed" or t.progress >= 90):
            out.append(Alert("R04", c["severity"], t.name,
                             f"Việc '{t.subject}' báo {t.progress:.0f}% hoặc đã xong nhưng chứng từ "
                             f"bằng chứng chưa đạt điều kiện."))
        if (c := on("R05_evidence_rejected")) and t.evidence_rejected:
            out.append(Alert("R05", c["severity"], t.name,
                             f"Chứng từ bằng chứng của việc '{t.subject}' đã bị hủy hoặc từ chối."))
        if (c := on("R06_stale_task")) and not t.done and t.last_update \
                and t.plan_start and t.plan_start <= as_of:
            idle = cal.offset(t.last_update, as_of)
            if idle > c.get("threshold_wd", 5):
                out.append(Alert("R06", c["severity"], t.name,
                                 f"Việc '{t.subject}' không được cập nhật {idle} ngày làm việc "
                                 f"(lần cuối {_d(t.last_update)})."))
        if (c := on("R09_blocker")) and not t.done and t.blocker.strip():
            out.append(Alert("R09", c["severity"], t.name,
                             f"Việc '{t.subject}' đang vướng: {t.blocker.strip()}"))

    if (c := on("R07_spi_low")) and spi is not None:
        red = rules.get("rag", {}).get("spi_red_below", 0.80)
        green = rules.get("rag", {}).get("spi_green_min", 0.95)
        if spi < green:
            out.append(Alert("R07", "Đỏ" if spi < red else c["severity"], None,
                             f"SPI dự án {fmt_num(spi, 2)}, thấp hơn ngưỡng {fmt_num(green, 2)}."))
    return out


def compute_rag(alerts: list[Alert], spi: float | None, rules: dict) -> str:
    rag_cfg = rules.get("rag", {})
    red, green = rag_cfg.get("spi_red_below", 0.80), rag_cfg.get("spi_green_min", 0.95)
    if any(a.severity == "Đỏ" for a in alerts) or (spi is not None and spi < red):
        return "Đỏ"
    if alerts or (spi is not None and spi < green):
        return "Vàng"
    return "Xanh"


# ---------------------------------------------------------------- định dạng kiểu Việt Nam

def _d(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


def fmt_date(d: date | None) -> str:
    return _d(d)


def fmt_num(x: float | None, digits: int = 0) -> str:
    """1240.5 -> '1.240,5' (dấu chấm hàng nghìn, dấu phẩy thập phân)."""
    if x is None:
        return "—"
    s = f"{x:,.{digits}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_pct(x: float | None) -> str:
    return "—" if x is None else f"{fmt_num(x * 100, 0)}%"
