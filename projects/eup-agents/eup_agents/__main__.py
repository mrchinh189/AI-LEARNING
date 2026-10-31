"""Giao diện dòng lệnh.

    python -m eup_agents check                    # kiểm tra kết nối ERP và Claude API
    python -m eup_agents setup-erp [--apply]      # tạo custom field cho Task
    python -m eup_agents nudge [--slot afternoon] # A2 nhắc việc
    python -m eup_agents report [--send]          # A5 báo cáo tuần
    python -m eup_agents erp-watch                # A3 giám sát chứng từ
    python -m eup_agents intake --file email.txt --sender sep@eup.vn   # A1 tiếp nhận việc
"""

import argparse
import json
import logging
import sys

from . import llm, setup_erp
from .agents import erp_watch, intake, nudge, report
from .config import settings
from .erp import ERPClient, ERPError


def check(erp: ERPClient) -> int:
    ok = True
    print(f"ERP_URL   : {settings.erp_url}")
    print(f"DRY_RUN   : {settings.dry_run}")
    print(f"LLM       : {'bật — ' + settings.llm_model if settings.llm_enabled else 'tắt'}")
    try:
        print(f"[OK] Đăng nhập ERP bằng user: {erp.ping()}")
        n = len(erp.get_list("Task", [], ["name"], limit=5))
        print(f"[OK] Đọc được Task ({n} bản ghi mẫu)")
    except ERPError as e:
        ok = False
        print(f"[LỖI] ERP: {e}")
    if settings.llm_enabled:
        out = llm.ask("Trả lời đúng một từ.", "Nói 'sẵn sàng'.", max_tokens=1000)
        print(f"[OK] Claude API trả lời: {out.strip()}" if out else "[LỖI] Không gọi được Claude API — xem log ở trên")
        ok = ok and bool(out)
    return 0 if ok else 1


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="eup_agents")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    s = sub.add_parser("setup-erp"); s.add_argument("--apply", action="store_true")
    s = sub.add_parser("nudge"); s.add_argument("--slot", choices=["morning", "afternoon"], default="morning")
    s = sub.add_parser("report"); s.add_argument("--send", action="store_true")
    sub.add_parser("erp-watch")
    s = sub.add_parser("intake")
    s.add_argument("--file", required=True); s.add_argument("--sender", required=True)
    s.add_argument("--source", default="Email"); s.add_argument("--ref", default="")
    a = p.parse_args(argv)

    erp = ERPClient()
    if a.cmd == "check":
        return check(erp)
    try:
        out = _dispatch(erp, a)
    except ERPError as e:
        print(f"[LỖI] {e}")
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


def _dispatch(erp: ERPClient, a) -> dict:
    if a.cmd == "setup-erp":
        out = setup_erp.run(erp, a.apply)
    elif a.cmd == "nudge":
        out = nudge.run(erp, a.slot)
    elif a.cmd == "report":
        out = report.run(erp, a.send)
    elif a.cmd == "erp-watch":
        out = erp_watch.run(erp)
    else:
        text = open(a.file, encoding="utf-8").read()
        out = intake.run(erp, text, a.sender, a.source, a.ref or a.file)
    return out


if __name__ == "__main__":
    sys.exit(main())
