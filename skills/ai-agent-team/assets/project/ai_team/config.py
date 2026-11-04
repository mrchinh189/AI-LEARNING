"""Định nghĩa đội bot, đọc từ team.json."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

WORK_TOOLS = {"write_file", "read_file", "publish", "purchase", "save_skill", "web_search"}


@dataclass
class BotConfig:
    name: str
    title: str
    role: str
    effort: str = "medium"
    tools: list[str] = field(default_factory=list)
    delegates: list[str] = field(default_factory=list)
    delegate_only: bool = False  # Nguyên tắc 5: trưởng nhóm chỉ phân việc

    def __post_init__(self) -> None:
        if self.delegate_only:
            bad = WORK_TOOLS.intersection(self.tools)
            if bad:
                raise ValueError(f"{self.name} là delegate_only nhưng có tool làm việc: {sorted(bad)}")
            if not self.delegates:
                raise ValueError(f"{self.name} là delegate_only nhưng không có ai để giao việc")


@dataclass
class Team:
    charter: str
    bots: dict[str, BotConfig]
    manager: str

    def get(self, name: str) -> BotConfig:
        if name not in self.bots:
            raise KeyError(f"Không có bot tên '{name}'. Có: {', '.join(self.bots)}")
        return self.bots[name]


def load_team(path: Path) -> Team:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    bots = {b["name"]: BotConfig(**b) for b in data["bots"]}
    for bot in bots.values():
        for d in bot.delegates:
            if d not in bots:
                raise ValueError(f"{bot.name} giao việc cho bot không tồn tại: {d}")
    if data["manager"] not in bots:
        raise ValueError("manager phải là một bot trong danh sách")
    return Team(charter=data["charter"], bots=bots, manager=data["manager"])
