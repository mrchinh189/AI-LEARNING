"""Parse lệnh chat thành intent, độc lập với nền tảng chat."""
from __future__ import annotations

from dataclasses import dataclass

COMMANDS = {"goal", "status", "tasks", "approve", "reject", "priority",
            "pause", "resume", "stop", "budget", "agents", "help"}


@dataclass
class Command:
    name: str
    args: str = ""


def parse(text: str) -> Command:
    text = text.strip()
    if not text.startswith("/"):
        return Command("chat", text)                  # hỏi đáp tự do về kết quả
    head, _, rest = text[1:].partition(" ")
    name = head.split("@")[0].lower()                 # /status@MyBot -> status
    return Command(name if name in COMMANDS else "unknown", rest.strip())


HELP = """Lệnh:
/goal <mục tiêu>      tạo mục tiêu mới
/status [id]          tiến độ & chi phí
/tasks [id]           danh sách task
/approve <key>        duyệt hành động
/reject <key> <lý do> từ chối
/priority <id> high   đổi ưu tiên
/budget <id> <usd>    đặt trần chi phí
/pause | /resume | /stop
/agents               xem đội agent"""
