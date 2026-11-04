#!/usr/bin/env python3
"""Kiểm tra cấu hình đội và các skill của một dự án ai-team — không cần API key.

Cách dùng:
    python validate_team.py <thư-mục-dự-án>

Trả mã thoát 0 nếu không có LỖI (cảnh báo không làm thất bại).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WORK_TOOLS = {"write_file", "read_file", "publish", "purchase", "save_skill", "web_search"}
RISKY_TOOLS = {"publish", "purchase", "save_skill"}
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
BOT_NAME_RE = re.compile(r"^[a-z0-9_]+$")  # phải khớp regex @tên trong room.py
SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SKILL_SECTIONS = ("Mô tả", "Các bước", "Tiêu chí đạt")


def check_team(path: Path, errors: list[str], warnings: list[str]) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{path}: không đọc được JSON ({exc})")
        return {}

    for key in ("manager", "charter", "bots"):
        if key not in data:
            errors.append(f"team.json thiếu trường `{key}`")
    bots = {b.get("name"): b for b in data.get("bots", [])}
    if len(bots) != len(data.get("bots", [])):
        errors.append("Có tên bot bị trùng")

    for name, bot in bots.items():
        where = f"bot `{name}`"
        if not name or not BOT_NAME_RE.match(name):
            errors.append(f"{where}: tên chỉ gồm chữ thường, số, gạch dưới (để @nhắc tên được)")
        for field in ("title", "role"):
            if not bot.get(field):
                errors.append(f"{where}: thiếu `{field}`")
        effort = bot.get("effort", "medium")
        if effort not in EFFORTS:
            errors.append(f"{where}: effort `{effort}` không hợp lệ ({', '.join(sorted(EFFORTS))})")
        tools = set(bot.get("tools", []))
        unknown = tools - WORK_TOOLS
        if unknown:
            errors.append(f"{where}: tool không tồn tại {sorted(unknown)}; có: {sorted(WORK_TOOLS)}")
        for d in bot.get("delegates", []):
            if d not in bots:
                errors.append(f"{where}: giao việc cho bot không tồn tại `{d}`")
            if d == name:
                errors.append(f"{where}: không được tự giao việc cho chính mình")
        if bot.get("delegate_only"):
            if tools & WORK_TOOLS:
                errors.append(f"{where}: là delegate_only nhưng có tool làm việc {sorted(tools & WORK_TOOLS)}")
            if not bot.get("delegates"):
                errors.append(f"{where}: là delegate_only nhưng không có ai để giao việc")
        if tools & RISKY_TOOLS and name != data.get("manager"):
            warnings.append(f"{where}: có tool rủi ro {sorted(tools & RISKY_TOOLS)} — thường chỉ nên để ở bot quản lý")
        if len(tools) > 4 and name != data.get("manager"):
            warnings.append(f"{where}: có {len(tools)} tool — vai trò có thể quá rộng, cân nhắc tách bot")
        if len(bot.get("role", "")) > 600:
            warnings.append(f"{where}: mô tả vai trò rất dài — vai trò hẹp giúp bot làm tốt hơn")

    manager = data.get("manager")
    if manager and manager not in bots:
        errors.append(f"manager `{manager}` không có trong danh sách bot")
    elif manager:
        reachable, stack = {manager}, [manager]
        while stack:
            for d in bots[stack.pop()].get("delegates", []):
                if d in bots and d not in reachable:
                    reachable.add(d)
                    stack.append(d)
        orphans = sorted(set(bots) - reachable)
        if orphans:
            warnings.append(f"Bot không nằm trong chuỗi giao việc từ `{manager}` (chỉ gọi được bằng --bot hoặc phòng chat): {orphans}")
    return bots


def check_skills(skill_dir: Path, errors: list[str], warnings: list[str]) -> int:
    if not skill_dir.exists():
        warnings.append(f"Không có thư mục skill {skill_dir}")
        return 0
    count = 0
    for path in sorted(skill_dir.glob("*.md")):
        count += 1
        where = f"skill `{path.name}`"
        if not SKILL_NAME_RE.match(path.stem):
            errors.append(f"{where}: tên file chỉ gồm chữ thường, số, gạch ngang")
        text = path.read_text(encoding="utf-8")
        for section in SKILL_SECTIONS:
            if not re.search(rf"^##\s+{re.escape(section)}", text, re.M):
                warnings.append(
                    f"{where}: thiếu mục `## {section}`"
                    + (" — không có mục này thì bot không tự chấm được" if section == "Tiêu chí đạt" else "")
                )
        rubric = re.search(r"^##\s+Tiêu chí đạt[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S)
        if rubric:
            items = [l for l in rubric.group(1).splitlines() if l.strip().startswith(("-", "*")) or re.match(r"\s*\d+\.", l)]
            if not items:
                warnings.append(f"{where}: tiêu chí đạt nên là danh sách gạch đầu dòng, mỗi dòng một tiêu chí kiểm được")
            unquoted = lambda l: re.sub(r'"[^"]*"|“[^”]*”', "", l)  # bỏ phần ví dụ trong ngoặc kép
            vague = [l.strip() for l in items
                     if re.search(r"\b(hay|tốt|hấp dẫn|chất lượng|phù hợp)\b", unquoted(l), re.I) and not re.search(r"\d", l)]
            for v in vague[:3]:
                warnings.append(f"{where}: tiêu chí có thể mơ hồ, khó chấm: {v!r} — thêm con số hoặc điều kiện cụ thể")
    return count


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1])
    errors: list[str] = []
    warnings: list[str] = []
    bots = check_team(root / "team" / "team.json", errors, warnings)
    n_skills = check_skills(root / "team" / "skills", errors, warnings)
    print(f"Đội: {len(bots)} bot · Skill: {n_skills}")
    for w in warnings:
        print(f"  ⚠ {w}")
    for e in errors:
        print(f"  ✗ {e}")
    print("KẾT QUẢ:", "HỢP LỆ" if not errors else f"{len(errors)} LỖI")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
