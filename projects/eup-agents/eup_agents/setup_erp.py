"""Tạo các custom field cho Task. Chạy bằng API key của tài khoản quản trị, trên site TEST trước.

    python -m eup_agents setup-erp            # chỉ kiểm tra, không ghi gì
    python -m eup_agents setup-erp --apply    # tạo field còn thiếu
"""

import json

from .config import ROOT
from .erp import ERPClient, ERPError

FIELDS_FILE = ROOT / "setup" / "custom_fields.json"
STANDARD_TASK_FIELDS = ["company", "department", "exp_end_date", "completed_on", "priority"]


def run(erp: ERPClient, apply: bool) -> dict:
    have = {f["fieldname"] for f in erp.get_doc("DocType", "Task").get("fields", [])}
    have |= {f["fieldname"] for f in erp.get_list("Custom Field", [["dt", "=", "Task"]], ["fieldname"])}

    missing_std = [f for f in STANDARD_TASK_FIELDS if f not in have]
    wanted = json.loads(FIELDS_FILE.read_text(encoding="utf-8"))
    missing = [f for f in wanted if f["fieldname"] not in have]
    print(f"Trường chuẩn thiếu trên Task: {missing_std or 'không'}")
    print(f"Custom field cần tạo: {[f['fieldname'] for f in missing] or 'đã đủ'}")
    created = []
    if apply:
        for f in missing:
            body = {"doctype": "Custom Field", "dt": "Task", **f}
            try:
                erp._req("POST", "/api/resource/Custom Field", json=body)
                created.append(f["fieldname"])
                print(f"  + đã tạo {f['fieldname']}")
            except ERPError as e:
                print(f"  ! lỗi khi tạo {f['fieldname']}: {e}")
    elif missing:
        print("Chưa ghi gì. Thêm --apply để tạo.")
    return {"missing_standard": missing_std, "missing_custom": [f["fieldname"] for f in missing], "created": created}
