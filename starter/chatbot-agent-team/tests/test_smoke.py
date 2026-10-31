"""Kiểm thử đầu-cuối ở chế độ FAKE_LLM (không gọi API thật, không tốn tiền).

Chạy: pytest -q
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config, db, ingest, worker

KB = Path(__file__).resolve().parents[1] / "kb"
SESSION = "test-session-0001"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "FAKE_LLM", True)
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "N8N_WEBHOOK_URL", "")
    db.init_db()
    for title, content in ingest.chunk((KB / "faq-mau.md").read_text(encoding="utf-8")):
        db.add_kb_chunk("faq-mau.md", title, content)
    from app.main import app
    with TestClient(app) as c:
        yield c


def chat(client, text, session=SESSION):
    r = client.post("/api/chat", json={"session_id": session, "text": text})
    assert r.status_code == 200
    return r.json()


def events(client, task_id, session=SESSION):
    r = client.get(f"/api/tasks/{task_id}/events", params={"session_id": session})
    assert r.status_code == 200
    return r.json()["events"]


def test_search_kb_ignores_diacritics(client):
    assert db.search_kb("phi giao hang")[0]["title"] == "Phí giao hàng"


def test_fast_path_answers_with_sources(client):
    out = chat(client, "Phí giao hàng nội thành bao nhiêu?")
    assert out["route"] == "fast"
    assert "Nguồn:" in out["reply"] and "Phí giao hàng" in out["reply"]


def test_deep_path_runs_agent_team(client):
    out = chat(client, "/sau So sánh chính sách bảo hành máy in của các hãng")
    assert out["route"] == "deep"
    assert worker.run_once()
    kinds = [e["kind"] for e in events(client, out["task_id"])]
    assert kinds[0] == "progress" and kinds[-1] == "result"
    assert client.get(f"/api/tasks/{out['task_id']}", params={"session_id": SESSION}).json()["status"] == "done"


def test_action_requires_approval(client):
    out = chat(client, "Tạo ticket: máy in đơn hàng 123 bị kẹt giấy")
    worker.run_once()
    approval = next(e for e in events(client, out["task_id"]) if e["kind"] == "approval")
    approval_id = approval["data"]["approval_id"]

    # Người khác không duyệt được
    r = client.post(f"/api/approvals/{approval_id}", json={"session_id": "someone-else-01", "decision": "approve"})
    assert r.status_code == 404

    r = client.post(f"/api/approvals/{approval_id}", json={"session_id": SESSION, "decision": "approve"})
    assert r.json()["ok"] is True
    worker.run_once()
    result = [e for e in events(client, out["task_id"]) if e["kind"] == "action_result"]
    assert result and "Chế độ thử" in result[0]["message"]

    r = client.post(f"/api/approvals/{approval_id}", json={"session_id": SESSION, "decision": "approve"})
    assert r.json()["ok"] is False


def test_handoff_to_human_and_back(client):
    assert chat(client, "Cho tôi gặp nhân viên")["route"] == "human"
    assert chat(client, "Alo?")["route"] == "human"
    assert chat(client, "/bot")["route"] == "help"
    assert chat(client, "Giờ làm việc?")["route"] == "fast"


def test_tasks_are_private(client):
    out = chat(client, "/sau nghiên cứu thị trường máy chiếu")
    r = client.get(f"/api/tasks/{out['task_id']}/events", params={"session_id": "someone-else-01"})
    assert r.status_code == 404


class FakeTelegram:
    def __init__(self):
        self.sent, self.calls = [], []

    def call(self, method, **params):
        self.calls.append((method, params))
        return {}

    def send(self, chat_id, text, reply_markup=None):
        self.sent.append((str(chat_id), text, reply_markup))


def test_telegram_message_and_approval_button(client):
    from app import telegram_bot

    tg = FakeTelegram()
    telegram_bot.handle_update(tg, {"update_id": 1, "message": {"chat": {"id": 42}, "text": "Tạo ticket: máy chiếu mờ"}})
    assert "Đã nhận yêu cầu" in tg.sent[-1][1]
    worker.run_once()

    approval = next(e for e in db.undelivered_events("telegram") if e["kind"] == "approval")
    assert approval["external_id"] == "42"
    data = f"a:{approval['data']['approval_id']}:y"
    callback = {"id": "cb1", "data": data, "message": {"chat": {"id": 42}, "message_id": 7}}
    telegram_bot.handle_update(tg, {"update_id": 2, "callback_query": callback})
    assert tg.sent[-1][1].startswith("Đã duyệt")
    worker.run_once()
    assert any(e["kind"] == "action_result" for e in db.undelivered_events("telegram"))
