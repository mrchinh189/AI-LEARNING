"""Dòng lệnh: python -m eup_pm <lệnh> [tuỳ chọn]

Các lệnh:
  ping        Kiểm tra kết nối ERP và tài khoản đang dùng
  setup-erp   Tạo doctype, custom field, role (chạy 1 lần, cần tài khoản System Manager)
  compute     Tính tiến độ, đường găng, cảnh báo và in ra màn hình (không ghi gì)
  daily       Đối chiếu chứng từ + tính toán + ghi RAG/SPI + tạo cảnh báo
  checkin     Gửi email nhắc người phụ trách cập nhật tiến độ
  report      Soạn báo cáo tuần (bản nháp) cho từng dự án
  publish     Gửi các báo cáo PM đã chuyển sang 'Đã phát hành'

Đội AI agent (cần ANTHROPIC_API_KEY và EUP_AGENT_MODEL):
  ask "câu hỏi"                     ① Điều phối trả lời, tự giao việc cho agent khác khi cần
  plan --project P                  ② Lập kế hoạch: soạn WBS nháp (Nx Plan Draft) chờ PM duyệt
  apply-plan --draft KH-2611-0001   Tạo Task từ kế hoạch PM đã duyệt (lệnh của người, không phải agent)
  reply --from email --text "..."   ③ Thu thập: đọc tin trả lời của người phụ trách, cập nhật Task
  risk --alert A | --project P      ⑤ Rủi ro: phân tích nguyên nhân gốc và phương án cho cảnh báo
  event --json '{"type": ...}'      Đưa một sự kiện vào bộ định tuyến (giống webhook)
  serve                             Mở webhook nhận sự kiện tại 127.0.0.1:8787/event
"""

from __future__ import annotations

import argparse
import json
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
    ap.add_argument("command", choices=["ping", "setup-erp", "compute", "daily", "checkin", "report", "publish",
                                        "ask", "plan", "apply-plan", "reply", "risk", "event", "serve"])
    ap.add_argument("text", nargs="?", help="Lệnh ask: câu hỏi")
    ap.add_argument("--alert", help="Lệnh risk: mã Nx Project Alert")
    ap.add_argument("--draft", help="Lệnh apply-plan: mã Nx Plan Draft")
    ap.add_argument("--from", dest="sender", help="Lệnh reply/ask: email người gửi")
    ap.add_argument("--text", dest="body", help="Lệnh reply: nội dung tin nhắn")
    ap.add_argument("--json", dest="event", help="Lệnh event: sự kiện dạng JSON")
    ap.add_argument("--no-agents", action="store_true", help="Lệnh daily: không gọi Agent Rủi ro")
    ap.add_argument("--port", type=int, default=8787)
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
                        dry_run=s.dry_run, allow_schema=args.command == "setup-erp",
                        allow_task_create=args.command == "apply-plan")
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
            team = None if args.no_agents or not s.model else _team(erp, s, today)
            run_daily(erp, s, args.project, today, team=team)
        elif args.command == "checkin":
            run_checkin(erp, s, args.project, today)
        elif args.command == "report":
            for _, name, body in run_report(erp, s, args.project, today, use_llm=not args.no_llm):
                if s.dry_run:
                    print(f"\n===== {name} =====\n{body}\n")
        elif args.command == "publish":
            run_publish(erp, s)
        elif args.command == "apply-plan":
            from .agents.planner import apply_plan
            names = apply_plan(erp, _required(args.draft, "--draft"))
            log.info("Đã tạo %d Task", len(names))
        elif args.command == "serve":
            from .agents.server import serve
            serve(lambda: _team(erp, s, date.today()), port=args.port)
        else:
            _run_agent_command(args, _team(erp, s, today))
    except ErpError as e:
        log.error("Lỗi ERP: %s", e)
        return 2
    except (RuntimeError, ValueError) as e:
        log.error("%s", e)
        return 2
    return 0


def _team(erp, s, today):
    from .agents import Team
    from .agents.base import llm_for_agent
    agents = ("orchestrator", "planner", "tracker", "risk")
    return Team(erp, s, llm_for_agent(s, "orchestrator"), today,
                {a: llm_for_agent(s, a) for a in agents})


def _required(value, flag):
    if not value:
        raise ValueError(f"Thiếu {flag}")
    return value


def _run_agent_command(args, team):
    cmd = args.command
    if cmd == "ask":
        event = {"type": "ask", "text": _required(args.text, "câu hỏi"), "from": args.sender or ""}
    elif cmd == "plan":
        event = {"type": "new_project", "project": _required(args.project, "--project")}
    elif cmd == "reply":
        event = {"type": "reply", "from": _required(args.sender, "--from"), "text": _required(args.body, "--text")}
    elif cmd == "risk":
        if args.project and not args.alert:
            n = team.analyse_new_red_alerts(args.project)
            print(f"Agent Rủi ro đã phân tích {n} cảnh báo Đỏ của {args.project}")
            return
        event = {"type": "alert", "alert": _required(args.alert, "--alert hoặc --project")}
    else:  # event
        event = json.loads(_required(args.event, "--json"))
    result = team.handle(event)
    if "answer" in result:
        print("\n" + result["answer"] + "\n")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


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
