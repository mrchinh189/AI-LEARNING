"""Nguyên tắc 2: phòng chat nhóm — nhiều bot cùng bàn một ý tưởng.

- Nhắc `@tên` thì chỉ bot đó trả lời.
- Nhắn chung thì mỗi bot tự quyết có lên tiếng hay không (trả lời `PASS` để im lặng).
- Bot có thể @nhắc đồng đội để phản biện; đồng đội được nhắc sẽ trả lời tiếp,
  trong giới hạn số lượt để cuộc tranh luận không chạy mãi.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .agent import Runtime

MENTION_RE = re.compile(r"@([a-z0-9_]+)")
HISTORY_LIMIT = 30


@dataclass
class Room:
    name: str
    members: list[str]
    transcript: list[dict[str, str]] = field(default_factory=list)


def load_room(runtime: Runtime, name: str, members: list[str] | None = None) -> Room:
    path = runtime.ws.room_path(name)
    room = Room(name, [])
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        room = Room(name, data["members"], data["transcript"])
    if members:
        for m in members:
            runtime.team.get(m)  # kiểm tra tên bot hợp lệ
        room.members = list(dict.fromkeys(room.members + members))
    if not room.members:
        raise ValueError(f"Phòng '{name}' chưa có thành viên — dùng --members")
    return room


def save_room(runtime: Runtime, room: Room) -> None:
    runtime.ws.room_path(room.name).write_text(
        json.dumps({"members": room.members, "transcript": room.transcript}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )


def post(runtime: Runtime, room: Room, text: str, sender: str = "operator") -> list[tuple[str, str]]:
    """Gửi một tin vào phòng, trả về danh sách (bot, câu trả lời) theo thứ tự."""
    room.transcript.append({"speaker": sender, "text": text})
    mentioned = [m for m in MENTION_RE.findall(text) if m in room.members]
    queue: list[tuple[str, bool]] = [(m, True) for m in dict.fromkeys(mentioned)] or [(m, False) for m in room.members]
    budget = 2 * len(room.members)  # tổng số lượt bot được nói cho một tin của người dùng
    replies: list[tuple[str, str]] = []

    while queue and budget > 0:
        bot, direct = queue.pop(0)
        budget -= 1
        result = runtime.run(bot, _prompt(room, bot, direct), parent=f"room:{room.name}")
        reply = result.text.strip()
        if not direct and reply.upper().rstrip(".") == "PASS":
            continue
        room.transcript.append({"speaker": bot, "text": reply})
        replies.append((bot, reply))
        for m in dict.fromkeys(MENTION_RE.findall(reply)):
            if m not in room.members or m == bot:
                continue
            queue = [(q, d) for q, d in queue if q != m]  # đã xếp hàng thì nâng thành "được nhắc trực tiếp"
            queue.append((m, True))

    save_room(runtime, room)
    return replies


def _prompt(room: Room, bot: str, direct: bool) -> str:
    history = "\n".join(f"[{m['speaker']}]: {m['text']}" for m in room.transcript[-HISTORY_LIMIT:])
    others = ", ".join(f"@{m}" for m in room.members if m != bot)
    rule = (
        "Bạn được nhắc tên trực tiếp — hãy trả lời."
        if direct
        else "Đây là tin nhắn chung. Chỉ lên tiếng nếu nó thuộc chuyên môn của bạn hoặc bạn có góc nhìn "
        "MỚI so với những gì đã nói; nếu không, trả lời đúng một từ: PASS"
    )
    return (
        f"Bạn đang ở phòng chat nhóm `{room.name}` cùng {others} và người vận hành.\n\n"
        f"<transcript>\n{history}\n</transcript>\n\n{rule}\n\n"
        "Trả lời ngắn gọn như nhắn tin trong nhóm, từ góc nhìn vai trò của bạn. Được phép phản biện "
        "thành viên khác và @nhắc tên họ khi cần ý kiến của họ. Không lặp lại điều người khác đã nói."
    )
