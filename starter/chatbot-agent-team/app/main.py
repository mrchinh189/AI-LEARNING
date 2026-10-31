"""Gateway HTTP: API cho web chat và trang chat mẫu.

Chạy: uvicorn app.main:app --reload --port 8000   rồi mở http://localhost:8000
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import config, core, db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    logging.getLogger(__name__).info("API sẵn sàng (FAKE_LLM=%s, DB=%s)", config.FAKE_LLM, config.DB_PATH)
    yield


app = FastAPI(title="Chatbot + AI Agent Team", lifespan=lifespan)


class ChatIn(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    text: str = Field(min_length=1, max_length=4000)


class DecisionIn(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    decision: Literal["approve", "reject"]


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/healthz")
def healthz():
    return {"ok": True, "fake_llm": config.FAKE_LLM}


# Các endpoint dùng `def` (không async): FastAPI chạy chúng trong thread pool nên lời gọi LLM không chặn server
@app.post("/api/chat")
def chat(body: ChatIn):
    return core.handle_message("web", body.session_id, body.text)


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str, session_id: str):
    if not core.task_visible_to(task_id, "web", session_id):
        raise HTTPException(404, "Không tìm thấy tác vụ")
    task = db.get_task(task_id)
    return {k: task[k] for k in ("id", "status", "request", "result", "error")}


@app.get("/api/tasks/{task_id}/events")
def get_events(task_id: str, session_id: str, after: int = 0):
    if not core.task_visible_to(task_id, "web", session_id):
        raise HTTPException(404, "Không tìm thấy tác vụ")
    return {"events": db.events_after(task_id, after), "status": db.get_task(task_id)["status"]}


@app.post("/api/approvals/{approval_id}")
def decide(approval_id: str, body: DecisionIn):
    result = core.decide("web", body.session_id, approval_id, body.decision == "approve")
    if result is None:
        raise HTTPException(404, "Không tìm thấy yêu cầu duyệt")
    return result
