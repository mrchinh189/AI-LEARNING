"""Tính ngày làm việc theo Holiday List của công ty trên ERP."""

from datetime import date, timedelta


class Calendar:
    def __init__(self, holidays: set[date] | None = None, saturday_off: bool = False):
        self.holidays = holidays or set()
        self.saturday_off = saturday_off

    @classmethod
    def from_erp(cls, erp, company: str | None) -> "Calendar":
        """Đọc Holiday List mặc định của công ty. Không đọc được thì chỉ nghỉ Chủ nhật."""
        if not company:
            return cls()
        try:
            hl = erp.get_doc("Company", company).get("default_holiday_list")
            if not hl:
                return cls()
            rows = erp.get_doc("Holiday List", hl).get("holidays", [])
            return cls({date.fromisoformat(r["holiday_date"]) for r in rows})
        except Exception:
            return cls()

    def is_workday(self, d: date) -> bool:
        if d in self.holidays or d.weekday() == 6:
            return False
        return not (self.saturday_off and d.weekday() == 5)

    def workdays_between(self, start: date, end: date) -> int:
        """Số ngày làm việc từ start tới end (end > start: dương; end < start: âm; cùng ngày: 0)."""
        if start == end:
            return 0
        step = 1 if end > start else -1
        n, d = 0, start
        while d != end:
            d += timedelta(days=step)
            if self.is_workday(d):
                n += step
        return n
