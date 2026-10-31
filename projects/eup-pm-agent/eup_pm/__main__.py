"""Dòng lệnh: python -m eup_pm <lệnh> [tuỳ chọn]

Các lệnh:
  ping        Kiểm tra kết nối ERP và tài khoản đang dùng
  setup-erp   Tạo doctype, custom field, role (chạy 1 lần, cần tài khoản System Manager)
  compute     Tính tiến độ, đường găng, cảnh báo và in ra màn hình (không ghi gì)
  daily       Đối chiếu chứng từ + tính toán + ghi RAG/SPI + tạo cảnh báo
  checkin     Gửi email nhắc người phụ trách cập nhật tiến độ
  report      Soạn báo cáo tuần (bản nháp) cho từng dự án
  publish     Gửi các báo cáo PM đã chuyển sang 'Đã phát hành'
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from .config import load_settings
from .engine import fmt_date, fmt_num, fmt_pct
from .erp import ErpClient, ErpError
from .jobs import analyse_project, run_checkin, run_daily, run_publish, run_report
from .loader import active_projects


def _setup_logging(log_dir, verbose: bool):
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    handlers = [logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_dir / f"{date.today():%Y-%m-%d}.log", encoding="utf-8")]
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format=fmt, handlers=handlers)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="eup_pm", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["ping", "setup-erp", "compute", "daily", "checkin", "report", "publish"])
    ap.add_argument("--project", help="Chỉ chạy cho một Project (mã Project, VD PROJ-0001)")
    ap.add_argument("--date", help="Giả lập ngày chạy, dạng YYYY-MM-DD (để thử)")
    ap.add_argument("--no-llm", action="store_true", help="Lệnh report: không gọi Claude")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    s = load_settings()
    _setup_logging(s.log_dir, args.verbose)
    log = logging.getLogger("eup_pm")
    today = date.fromisoformat(args.date) if args.date else date.today()

    try:
        erp = ErpClient(s.erp_url, s.erp_api_key, s.erp_api_secret,
                        dry_run=s.dry_run, allow_schema=args.command == "setup-erp")
        if s.dry_run and args.command not in ("ping", "compute"):
            log.info("Đang ở chế độ CHẠY THỬ (DRY_RUN=1): không ghi gì lên ERP, không gửi email.")

        if args.command == "ping":
            log.info("Kết nối %s thành công, tài khoản: %s", s.erp_url, erp.whoami())
            projects = active_projects(erp)
            log.info("Số Project đang Open và bật AI agent: %d", len(projects))
            for p in projects:
                log.info("  - %s  %s", p["name"], p.get("project_name"))
        elif args.command == "setup-erp":
            from .setup_erp import run_setup
            run_setup(erp)
        elif args.command == "compute":
            for p in active_projects(erp, args.project):
                res, docs = analyse_project(erp, s, p, today, verify=False)
                _print_result(p, res, {d["name"]: d.get("subject") for d in docs})
        elif args.command == "daily":
            run_daily(erp, s, args.project, today)
        elif args.command == "checkin":
            run_checkin(erp, s, args.project, today)
        elif args.command == "report":
            for _, name, body in run_report(erp, s, args.project, today, use_llm=not args.no_llm):
                if s.dry_run:
                    print(f"\n===== {name} =====\n{body}\n")
        elif args.command == "publish":
            run_publish(erp, s)
    except ErpError as e:
        log.error("Lỗi ERP: %s", e)
        return 2
    return 0


def _print_result(p, res, subjects):
    print(f"\n=== {p['name']} — {p.get('project_name')} ===")
    print(f"RAG {res.rag} | KH {fmt_pct(res.planned_pct)} | TT {fmt_pct(res.actual_pct)} | "
          f"SPI {fmt_num(res.spi, 2)} | baseline {fmt_date(res.deadline)} | dự báo {fmt_date(res.forecast_end)}")
    for e in res.data_errors:
        print(f"  LỖI DỮ LIỆU: {e}")
    print(f"  {'Task':<14} {'Găng':<5} {'Float':>5} {'KH':>5} {'TT':>5}  Dự báo xong  Việc")
    for name, t in sorted(res.tasks.items(), key=lambda x: (x[1].early_start or date.max)):
        print(f"  {name:<14} {'x' if t.critical else '':<5} "
              f"{'' if t.total_float is None else t.total_float:>5} {fmt_pct(t.planned_pct):>5} "
              f"{fmt_pct(t.actual_pct):>5}  {fmt_date(t.early_finish):<11}  {subjects.get(name, '')}")
    for a in res.alerts:
        print(f"  [{a.severity}] {a.rule_code} {a.task or ''}: {a.facts}")


if __name__ == "__main__":
    sys.exit(main())
