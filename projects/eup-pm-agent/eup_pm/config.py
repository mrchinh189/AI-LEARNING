"""Đọc cấu hình từ .env và rules.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    erp_url: str
    erp_api_key: str
    erp_api_secret: str
    dry_run: bool
    model: str
    effort: str
    fallbacks: str
    rules: dict
    log_dir: Path


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    rules_file = ROOT / os.getenv("RULES_FILE", "config/rules.yaml")
    with open(rules_file, encoding="utf-8") as f:
        rules = yaml.safe_load(f)
    log_dir = ROOT / os.getenv("LOG_DIR", "logs")
    log_dir.mkdir(exist_ok=True)
    return Settings(
        erp_url=os.getenv("ERP_URL", "").rstrip("/"),
        erp_api_key=os.getenv("ERP_API_KEY", ""),
        erp_api_secret=os.getenv("ERP_API_SECRET", ""),
        dry_run=os.getenv("DRY_RUN", "1") != "0",
        model=os.getenv("EUP_AGENT_MODEL", ""),
        effort=os.getenv("EUP_AGENT_EFFORT", "medium"),
        fallbacks=os.getenv("EUP_AGENT_FALLBACKS", "default"),
        rules=rules,
        log_dir=log_dir,
    )
