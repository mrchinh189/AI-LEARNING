"""Agent Đối chiếu chứng từ: so trạng thái chứng từ ERP với điều kiện trong bảng Chứng từ bằng chứng của Task.

Toàn bộ là truy vấn tất định, không dùng LLM. Chứng từ nghiệp vụ chỉ được đọc.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from .erp import ErpClient, ErpError

log = logging.getLogger("eup_pm.evidence")

ROW_FIELDS = ("name", "reference_doctype", "reference_name", "condition_field", "required_value",
              "is_met", "is_rejected", "last_checked")


def check_row(erp: ErpClient, row: dict, rejected_values: list[str]) -> tuple[bool, bool, str]:
    """Trả về (đạt, bị từ chối, mô tả trạng thái hiện tại)."""
    dt, name = row.get("reference_doctype"), row.get("reference_name")
    if not dt or not name:
        return False, False, "chưa khai chứng từ"
    try:
        doc = erp.get_doc(dt, name)
    except ErpError as e:
        if "HTTP 404" in str(e):
            return False, False, f"không tìm thấy {dt} {name}"
        raise
    field = row.get("condition_field") or "workflow_state"
    current = doc.get(field)
    met = str(current) == str(row.get("required_value"))
    rejected = (
        doc.get("docstatus") == 2
        or doc.get("workflow_state") in rejected_values
        or doc.get("status") in rejected_values
    )
    return met, rejected, f"{dt} {name}: {field} = {current}"


def verify_task(erp: ErpClient, task_doc: dict, rejected_values: list[str],
                today: date) -> tuple[bool, bool] | None:
    """Đối chiếu một Task. Trả về (đạt hết, có chứng từ bị từ chối), hoặc None nếu Task không có bằng chứng."""
    rows = task_doc.get("custom_evidence") or []
    if not rows:
        return None

    changed = False
    new_rows, notes = [], []
    for row in rows:
        met, rejected, note = check_row(erp, row, rejected_values)
        notes.append(note)
        if bool(row.get("is_met")) != met or bool(row.get("is_rejected")) != rejected:
            changed = True
        new_rows.append({**{k: row.get(k) for k in ROW_FIELDS},
                         "is_met": int(met), "is_rejected": int(rejected),
                         "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    all_met = all(r["is_met"] for r in new_rows)
    any_rejected = any(r["is_rejected"] for r in new_rows)
    name = task_doc["name"]

    if changed:
        erp.update("Task", name, {"custom_evidence": new_rows})
        log.info("Task %s: cập nhật trạng thái bằng chứng (%s)", name, "; ".join(notes))

    if all_met and task_doc.get("status") != "Completed":
        try:
            erp.update("Task", name, {
                "status": "Completed",
                "progress": 100,
                "completed_on": today.isoformat(),
                "custom_progress_source": "Bằng chứng",
            })
            erp.add_comment("Task", name, "Tự hoàn thành vì chứng từ bằng chứng đã đạt: " + "; ".join(notes))
        except ErpError as e:
            # Thường gặp: ERPNext không cho Completed khi task phụ thuộc chưa xong.
            log.warning("Không tự hoàn thành được Task %s: %s", name, e)
            erp.add_comment("Task", name,
                            f"Chứng từ bằng chứng đã đạt nhưng ERP chưa cho chuyển Completed: {e}")
    if any_rejected and changed:
        erp.add_comment("Task", name, "Chứng từ bằng chứng bị hủy hoặc từ chối: " + "; ".join(notes))

    return all_met, any_rejected
