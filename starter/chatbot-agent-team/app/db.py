"""Lưu trữ bằng SQLite: hội thoại, tác vụ (hàng đợi), sự kiện tiến độ, duyệt hành động, kho tri thức.

SQLite đủ cho MVP và chạy được nhiều worker trên cùng một máy. Khi cần nhiều máy,
thay module này bằng Postgres (hàng đợi dùng SELECT ... FOR UPDATE SKIP LOCKED).
"""
import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    channel TEXT NOT NULL,
    external_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'bot',          -- bot | human
    created_at REAL NOT NULL,
    UNIQUE (channel, external_id)
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,                          -- user | assistant
    content TEXT NOT NULL,
    route TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    request TEXT NOT NULL,
    context TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'queued',       -- queued | running | done | failed
    result TEXT,
    error TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS task_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    kind TEXT NOT NULL,                          -- progress | approval | action_result | result | error
    message TEXT NOT NULL,
    data TEXT,
    delivered INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    action TEXT NOT NULL,
    params TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',      -- pending | approved | rejected | executing | done | failed
    result TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS kb_chunks USING fts5(
    source, title, content,
    tokenize = 'unicode61 remove_diacritics 2'
);
"""


@contextmanager
def connect():
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    # isolation_level=None: tự commit từng câu lệnh; dùng BEGIN IMMEDIATE khi cần khóa
    conn = sqlite3.connect(config.DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with connect() as c:
        c.executescript(SCHEMA)


def _row(row):
    return dict(row) if row else None


# ---------- Hội thoại ----------

def get_or_create_conversation(channel: str, external_id: str) -> dict:
    with connect() as c:
        c.execute(
            "INSERT OR IGNORE INTO conversations (id, channel, external_id, created_at) VALUES (?, ?, ?, ?)",
            (uuid.uuid4().hex, channel, external_id, time.time()),
        )
        return _row(c.execute(
            "SELECT * FROM conversations WHERE channel = ? AND external_id = ?", (channel, external_id)
        ).fetchone())


def set_conversation_status(conversation_id: str, status: str) -> None:
    with connect() as c:
        c.execute("UPDATE conversations SET status = ? WHERE id = ?", (status, conversation_id))


def add_message(conversation_id: str, role: str, content: str, route: str | None = None) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO messages (conversation_id, role, content, route, created_at) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, role, content, route, time.time()),
        )


def recent_messages(conversation_id: str, limit: int = 6) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def conversation_for_task(task_id: str) -> dict | None:
    with connect() as c:
        return _row(c.execute(
            "SELECT conv.* FROM conversations conv JOIN tasks t ON t.conversation_id = conv.id WHERE t.id = ?",
            (task_id,),
        ).fetchone())


# ---------- Tác vụ (hàng đợi) ----------

def create_task(conversation_id: str, request: str, context: str) -> str:
    task_id = uuid.uuid4().hex[:12]
    now = time.time()
    with connect() as c:
        c.execute(
            "INSERT INTO tasks (id, conversation_id, request, context, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (task_id, conversation_id, request, context, now, now),
        )
    return task_id


def get_task(task_id: str) -> dict | None:
    with connect() as c:
        return _row(c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())


def claim_next_task() -> dict | None:
    """Lấy một tác vụ đang chờ và đánh dấu running. BEGIN IMMEDIATE để hai worker không lấy trùng."""
    with connect() as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT * FROM tasks WHERE status = 'queued' ORDER BY created_at LIMIT 1").fetchone()
        if row:
            c.execute("UPDATE tasks SET status = 'running', updated_at = ? WHERE id = ?", (time.time(), row["id"]))
        c.execute("COMMIT")
    return _row(row)


def finish_task(task_id: str, status: str, result: str | None = None, error: str | None = None) -> None:
    with connect() as c:
        c.execute(
            "UPDATE tasks SET status = ?, result = ?, error = ?, updated_at = ? WHERE id = ?",
            (status, result, error, time.time(), task_id),
        )


def requeue_stale_tasks() -> int:
    """Worker bị tắt giữa chừng thì tác vụ kẹt ở 'running': đưa lại vào hàng đợi khi khởi động."""
    with connect() as c:
        cur = c.execute("UPDATE tasks SET status = 'queued' WHERE status = 'running'")
        c.execute("UPDATE approvals SET status = 'approved' WHERE status = 'executing'")
        return cur.rowcount


# ---------- Sự kiện tiến độ ----------

def add_event(task_id: str, kind: str, message: str, data: dict | None = None) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO task_events (task_id, kind, message, data, created_at) VALUES (?, ?, ?, ?, ?)",
            (task_id, kind, message, json.dumps(data, ensure_ascii=False) if data else None, time.time()),
        )


def events_after(task_id: str, after_id: int = 0) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT id, kind, message, data, created_at FROM task_events WHERE task_id = ? AND id > ? ORDER BY id",
            (task_id, after_id),
        ).fetchall()
    events = []
    for r in rows:
        e = dict(r)
        e["data"] = json.loads(e["data"]) if e["data"] else None
        events.append(e)
    return events


def undelivered_events(channel: str, limit: int = 20) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            """SELECT e.id, e.task_id, e.kind, e.message, e.data, conv.external_id
               FROM task_events e
               JOIN tasks t ON t.id = e.task_id
               JOIN conversations conv ON conv.id = t.conversation_id
               WHERE e.delivered = 0 AND conv.channel = ?
               ORDER BY e.id LIMIT ?""",
            (channel, limit),
        ).fetchall()
    events = []
    for r in rows:
        e = dict(r)
        e["data"] = json.loads(e["data"]) if e["data"] else None
        events.append(e)
    return events


def mark_delivered(event_id: int) -> None:
    with connect() as c:
        c.execute("UPDATE task_events SET delivered = 1 WHERE id = ?", (event_id,))


# ---------- Duyệt hành động ----------

def create_approval(task_id: str, action: str, params: dict, summary: str) -> str:
    approval_id = uuid.uuid4().hex
    now = time.time()
    with connect() as c:
        c.execute(
            "INSERT INTO approvals (id, task_id, action, params, summary, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (approval_id, task_id, action, json.dumps(params, ensure_ascii=False), summary, now, now),
        )
    return approval_id


def get_approval(approval_id: str) -> dict | None:
    with connect() as c:
        return _row(c.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone())


def decide_approval(approval_id: str, approved: bool) -> bool:
    """Chỉ đổi trạng thái khi đang pending; trả False nếu đã được quyết định trước đó."""
    with connect() as c:
        cur = c.execute(
            "UPDATE approvals SET status = ?, updated_at = ? WHERE id = ? AND status = 'pending'",
            ("approved" if approved else "rejected", time.time(), approval_id),
        )
        return cur.rowcount == 1


def claim_approved_action() -> dict | None:
    with connect() as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT * FROM approvals WHERE status = 'approved' ORDER BY updated_at LIMIT 1").fetchone()
        if row:
            c.execute("UPDATE approvals SET status = 'executing', updated_at = ? WHERE id = ?", (time.time(), row["id"]))
        c.execute("COMMIT")
    return _row(row)


def finish_approval(approval_id: str, status: str, result: str) -> None:
    with connect() as c:
        c.execute(
            "UPDATE approvals SET status = ?, result = ?, updated_at = ? WHERE id = ?",
            (status, result, time.time(), approval_id),
        )


# ---------- Kho tri thức (tìm kiếm toàn văn FTS5) ----------

def clear_kb() -> None:
    with connect() as c:
        c.execute("DELETE FROM kb_chunks")


def add_kb_chunk(source: str, title: str, content: str) -> None:
    with connect() as c:
        c.execute("INSERT INTO kb_chunks (source, title, content) VALUES (?, ?, ?)", (source, title, content))


def search_kb(query: str, limit: int = 4) -> list[dict]:
    words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 1]
    if not words:
        return []
    # Ghép các từ bằng OR; bm25 tự ưu tiên đoạn chứa nhiều từ hiếm
    match = " OR ".join(f'"{w}"' for w in dict.fromkeys(words))
    with connect() as c:
        rows = c.execute(
            "SELECT source, title, content, bm25(kb_chunks) AS score FROM kb_chunks "
            "WHERE kb_chunks MATCH ? ORDER BY score LIMIT ?",
            (match, limit),
        ).fetchall()
    return [dict(r) for r in rows]
