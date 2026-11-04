"""Dòng lệnh: python -m ai_team <lệnh> ..."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agent import AutoOperator, CLIOperator, Runtime
from .config import load_team
from .llm import LLM
from .store import Workspace

PROJECT_DIR = Path(__file__).resolve().parent.parent


def build_runtime(args: argparse.Namespace, llm: LLM | None = None) -> Runtime:
    team = load_team(Path(args.team))
    ws = Workspace(Path(args.workspace), seed_skills=Path(args.team).parent / "skills")
    operator = AutoOperator(approve_all=True) if args.auto_approve else CLIOperator()
    return Runtime(team, ws, llm or LLM(), operator, verbose=not args.quiet)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ai_team", description="Đội AI agent: bot quản lý, bot chuyên môn, phòng chat, Dr. X")
    p.add_argument("--team", default=str(PROJECT_DIR / "team" / "team.json"), help="file cấu hình đội")
    p.add_argument("--workspace", default="workspace", help="thư mục lưu trí nhớ, skill, nhật ký, đầu ra")
    p.add_argument("--auto-approve", action="store_true", help="tự duyệt mọi hành động rủi ro (chỉ dùng khi demo)")
    p.add_argument("-q", "--quiet", action="store_true", help="không in tiến trình giao việc")
    sub = p.add_subparsers(dest="cmd", required=True)

    ask = sub.add_parser("ask", help="giao việc cho một bot (mặc định: bot quản lý)")
    ask.add_argument("task")
    ask.add_argument("--bot", help="tên bot nhận việc")
    ask.add_argument("--skill", default="", help="áp dụng skill (quy trình chuẩn) theo tên")
    ask.add_argument("--rubric", default="", help="tiêu chí đạt để bot tự chấm trước khi nộp")

    chat = sub.add_parser("chat", help="phòng chat nhóm nhiều bot")
    chat.add_argument("room")
    chat.add_argument("message", nargs="?", help="bỏ trống để vào chế độ tương tác")
    chat.add_argument("--members", default="", help="danh sách bot, phân cách bằng dấu phẩy")

    sub.add_parser("doctor", help="Dr. X khám các bot và đề xuất cải tiến")
    sub.add_parser("skills", help="liệt kê skill")
    mem = sub.add_parser("memory", help="xem trí nhớ của một bot")
    mem.add_argument("bot")

    args = p.parse_args(argv)
    rt = build_runtime(args)

    if args.cmd == "ask":
        r = rt.run(args.bot or rt.team.manager, args.task, rubric=args.rubric, skill=args.skill)
        print("\n" + r.text)
        if r.passed is not None:
            print(f"\n— Tự chấm: {'ĐẠT' if r.passed else 'CHƯA ĐẠT'} ({r.score}/10) sau {r.attempts} lần")
    elif args.cmd == "chat":
        from .room import load_room, post

        members = [m.strip() for m in args.members.split(",") if m.strip()]
        room = load_room(rt, args.room, members)
        messages = [args.message] if args.message else _interactive(room.name)
        for msg in messages:
            for bot, reply in post(rt, room, msg):
                print(f"\n[{bot}]: {reply}")
    elif args.cmd == "doctor":
        from .doctor import examine

        report, path = examine(rt)
        print(path.read_text(encoding="utf-8"))
    elif args.cmd == "skills":
        for s in rt.ws.list_skills():
            print(f"{s.name:28} {s.description}")
    elif args.cmd == "memory":
        rt.team.get(args.bot)
        print(rt.ws.memory(args.bot) or "(trống)")
    return 0


def _interactive(room: str):
    print(f"Phòng `{room}` — gõ tin nhắn, dùng @tên để gọi riêng một bot, Ctrl-D để thoát.")
    while True:
        try:
            line = input("\nbạn> ").strip()
        except EOFError:
            return
        if line:
            yield line


if __name__ == "__main__":
    sys.exit(main())
