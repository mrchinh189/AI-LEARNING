"""Đọc cấu hình từ biến môi trường (.env) và file config/org.json."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    erp_url: str = os.getenv("ERP_URL", "https://erp.eup.vn").rstrip("/")
    erp_api_key: str = os.getenv("ERP_API_KEY", "")
    erp_api_secret: str = os.getenv("ERP_API_SECRET", "")
    # DRY_RUN=true: chỉ đọc ERP, mọi lệnh ghi và tin nhắn chỉ in ra màn hình.
    dry_run: bool = _bool("DRY_RUN", True)
    llm_enabled: bool = _bool("LLM_ENABLED", True)
    llm_model: str = os.getenv("LLM_MODEL", "claude-opus-5-5")
    llm_effort: str = os.getenv("LLM_EFFORT", "medium")
    notify_backend: str = os.getenv("NOTIFY_BACKEND", "console")  # console | webhook | erp_bell
    notify_webhook_url: str = os.getenv("NOTIFY_WEBHOOK_URL", "")
    service_token: str = os.getenv("SERVICE_TOKEN", "")
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo(os.getenv("TZ_NAME", "Asia/Ho_Chi_Minh")))
    org_file: Path = ROOT / os.getenv("ORG_FILE", "config/org.json")
    report_dir: Path = ROOT / os.getenv("REPORT_DIR", "reports")

    def org(self) -> dict:
        """Danh bạ tổ chức: trưởng phòng, công ty pilot, ngưỡng luật."""
        if not self.org_file.exists():
            return {}
        return json.loads(self.org_file.read_text(encoding="utf-8"))


settings = Settings()
