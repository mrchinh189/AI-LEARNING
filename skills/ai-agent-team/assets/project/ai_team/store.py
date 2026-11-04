"""Lưu trữ trên đĩa: trí nhớ từng bot, skill, nhật ký, phòng chat, file đầu ra.

Mọi thứ là file Markdown/JSONL đọc được bằng mắt, để người vận hành có thể
xem và sửa tay — đúng tinh thần "bot là nhân sự, hồ sơ phải minh bạch".
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


@dataclass
class Skill:
    name: str
    text: str

    @property
    def description(self) -> str:
        return _section(self.text, "Mô tả").splitlines()[0] if _section(self.text, "Mô tả") else ""

    @property
    def rubric(self) -> str:
        return _section(self.text, "Tiêu chí đạt")


def _section(text: str, heading: str) -> str:
    """Lấy nội dung dưới `## <heading>` cho tới heading cấp 2 tiếp theo."""
    match = re.search(rf"^##\s+{re.escape(heading)}[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return match.group(1).strip() if match else ""


class Workspace:
    def __init__(self, root: Path, seed_skills: Path | None = None):
        self.root = Path(root)
        self.seed_skills = Path(seed_skills) if seed_skills else None
        for sub in ("memory", "skills", "logs", "rooms", "outputs", "reports"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    # ---- Trí nhớ dài hạn của từng bot -------------------------------------
    def memory(self, bot: str) -> str:
        path = self.root / "memory" / f"{bot}.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def remember(self, bot: str, note: str) -> None:
        path = self.root / "memory" / f"{bot}.md"
        with path.open("a", encoding="utf-8") as f:
            f.write(f"- ({time.strftime('%Y-%m-%d')}) {note.strip()}\n")

    # ---- Skill (quy trình chuẩn đã đóng gói) -------------------------------
    def _skill_dirs(self) -> list[Path]:
        dirs = [self.root / "skills"]  # skill trong workspace ghi đè skill mẫu
        if self.seed_skills:
            dirs.append(self.seed_skills)
        return dirs

    def list_skills(self) -> list[Skill]:
        seen: dict[str, Skill] = {}
        for d in self._skill_dirs():
            for path in sorted(d.glob("*.md")):
                seen.setdefault(path.stem, Skill(path.stem, path.read_text(encoding="utf-8")))
        return sorted(seen.values(), key=lambda s: s.name)

    def get_skill(self, name: str) -> Skill | None:
        if not SKILL_NAME_RE.match(name):
            return None
        for d in self._skill_dirs():
            path = d / f"{name}.md"
            if path.exists():
                return Skill(name, path.read_text(encoding="utf-8"))
        return None

    def save_skill(self, name: str, text: str) -> Path:
        if not SKILL_NAME_RE.match(name):
            raise ValueError("Tên skill chỉ gồm chữ thường, số và dấu gạch ngang")
        path = self.root / "skills" / f"{name}.md"
        path.write_text(text, encoding="utf-8")
        return path

    # ---- File đầu ra (sandbox trong outputs/) ------------------------------
    def output_path(self, rel: str) -> Path:
        base = (self.root / "outputs").resolve()
        path = (base / rel).resolve()
        if base != path and base not in path.parents:
            raise ValueError("Đường dẫn phải nằm trong thư mục outputs/")
        return path

    def write_output(self, rel: str, content: str) -> Path:
        path = self.output_path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def read_output(self, rel: str) -> str:
        return self.output_path(rel).read_text(encoding="utf-8")

    # ---- Nhật ký công việc (dữ liệu cho Dr. X) -----------------------------
    def log(self, bot: str, entry: dict[str, Any]) -> None:
        entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "bot": bot, **entry}
        with (self.root / "logs" / f"{bot}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def recent_logs(self, bot: str, limit: int = 5) -> list[dict[str, Any]]:
        path = self.root / "logs" / f"{bot}.jsonl"
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines[-limit:] if line.strip()]

    # ---- Phòng chat nhóm ---------------------------------------------------
    def room_path(self, room: str) -> Path:
        if not SKILL_NAME_RE.match(room):
            raise ValueError("Tên phòng chỉ gồm chữ thường, số và dấu gạch ngang")
        return self.root / "rooms" / f"{room}.json"
