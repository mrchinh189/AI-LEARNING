"""Đọc cấu hình từ biến môi trường (file .env)."""
import os

from dotenv import load_dotenv

load_dotenv()


def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


# Lưu trữ
DB_PATH = os.getenv("DB_PATH", "data/app.db")

# Model theo vai trò (model tiering): nhỏ cho router, tầm trung cho agent, mạnh nhất cho orchestrator
MODEL_ROUTER = os.getenv("MODEL_ROUTER", "claude-haiku-5-5")
MODEL_AGENT = os.getenv("MODEL_AGENT", "claude-sonnet-5-5")
MODEL_ORCHESTRATOR = os.getenv("MODEL_ORCHESTRATOR", "claude-opus-5-5")

# FAKE_LLM=1: không gọi API thật, trả kết quả giả để chạy thử / chạy test không tốn tiền
FAKE_LLM = _flag("FAKE_LLM")

# Research agent dùng công cụ web search/web fetch phía server của Anthropic
ENABLE_WEB_SEARCH = _flag("ENABLE_WEB_SEARCH", "1")

# Kênh và tích hợp (để trống nếu chưa dùng)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")

# Vận hành
BOT_NAME = os.getenv("BOT_NAME", "Trợ lý ABC")
WORKER_POLL_SECONDS = float(os.getenv("WORKER_POLL_SECONDS", "2"))
MAX_REVIEW_ROUNDS = int(os.getenv("MAX_REVIEW_ROUNDS", "2"))
