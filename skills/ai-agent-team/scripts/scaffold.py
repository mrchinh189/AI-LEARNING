#!/usr/bin/env python3
"""Tạo một dự án đội AI agent mới từ mẫu đi kèm skill.

Cách dùng:
    python scaffold.py <thư-mục-đích> [--preset sales-content|product|minimal]

- Sao chép mã nguồn ai_team/, test, README, requirements và skill mẫu.
- Chọn cấu hình đội theo preset (mặc định: sales-content).
- Không ghi đè thư mục đã có nội dung.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "project"
PRESETS = {
    "sales-content": TEMPLATE / "team" / "team.json",
    "product": SKILL_DIR / "assets" / "presets" / "product.json",
    "minimal": SKILL_DIR / "assets" / "presets" / "minimal.json",
}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("target")
    p.add_argument("--preset", choices=sorted(PRESETS), default="sales-content")
    args = p.parse_args()

    target = Path(args.target).resolve()
    if target.exists() and any(target.iterdir()):
        print(f"Thư mục {target} đã có nội dung — chọn thư mục khác hoặc xoá trước.", file=sys.stderr)
        return 1

    shutil.copytree(TEMPLATE, target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "workspace"))
    shutil.copyfile(PRESETS[args.preset], target / "team" / "team.json")

    print(f"Đã tạo dự án tại {target} (preset: {args.preset})")
    print("Bước tiếp theo:")
    print(f"  cd {target}")
    print("  python -m venv .venv && source .venv/bin/activate")
    print("  pip install -r requirements.txt pytest")
    print("  python -m pytest -q")
    print(f"  python {SKILL_DIR / 'scripts' / 'validate_team.py'} .")
    print("  export ANTHROPIC_API_KEY=...   # hoặc: ant auth login")
    print("  python -m ai_team skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
