"""Test logic phối hợp bằng FakeLLM — không gọi API thật, không cần API key."""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_team.agent import AutoOperator, Runtime
from ai_team.config import BotConfig, load_team
from ai_team.grader import Grade
from ai_team.room import load_room, post
from ai_team.store import Workspace

PROJECT = Path(__file__).resolve().parent.parent
_ids = itertools.count()


def text(t: str):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=t)], stop_reason="end_turn")


def tool(tool_name: str, **inp):
    block = SimpleNamespace(type="tool_use", id=f"toolu_{next(_ids)}", name=tool_name, input=inp)
    return SimpleNamespace(content=[block], stop_reason="tool_use")


class FakeLLM:
    def __init__(self, scripts: dict[str, list], grades: list[Grade] | None = None):
        self.scripts = {k: list(v) for k, v in scripts.items()}
        self.grades = list(grades or [])
        self.calls: list[dict] = []

    def create(self, *, bot, system, messages, tools, effort, max_tokens=16000):
        self.calls.append({"bot": bot, "system": system, "messages": list(messages), "tools": [t["name"] for t in tools]})
        return self.scripts[bot].pop(0)

    def parse(self, *, purpose, system, prompt, schema, effort="medium", max_tokens=16000):
        return self.grades.pop(0)


@pytest.fixture
def make_rt(tmp_path):
    def _make(scripts, grades=None, approve=False):
        team = load_team(PROJECT / "team" / "team.json")
        ws = Workspace(tmp_path / "ws", seed_skills=PROJECT / "team" / "skills")
        op = AutoOperator(approve_all=approve)
        return Runtime(team, ws, FakeLLM(scripts, grades), op), op

    return _make


def last_tool_result(llm: FakeLLM, bot: str) -> str:
    msgs = [c for c in llm.calls if c["bot"] == bot][-1]["messages"]
    return msgs[-1]["content"][0]["content"]


def test_simple_answer_is_logged(make_rt):
    rt, _ = make_rt({"copywriter": [text("Xin chào")]})
    r = rt.run("copywriter", "Viết lời chào")
    assert r.text == "Xin chào" and r.passed is None
    assert rt.ws.recent_logs("copywriter")[-1]["result"] == "Xin chào"


def test_manager_chains_tasks_through_delegation(make_rt):
    rt, _ = make_rt(
        {
            "chief_of_staff": [
                tool("delegate", bot="researcher", task="Tra giá DJI Mic", rubric="", skill=""),
                tool("delegate", bot="writer", task="Viết tin đăng", rubric="", skill=""),
                text("Đã xong: giá 3tr, tin đăng sẵn sàng"),
            ],
            "researcher": [text("Giá mới 5tr, cũ rẻ nhất 3tr")],
            "writer": [text("Tin đăng theo văn phong")],
        }
    )
    r = rt.run("chief_of_staff", "Bán micro DJI")
    assert r.text.startswith("Đã xong")
    assert r.tools_used == ["delegate", "delegate"]
    assert json.loads(last_tool_result(rt.llm, "chief_of_staff"))["result"] == "Tin đăng theo văn phong"
    assert rt.ws.recent_logs("researcher")[-1]["parent"] == "chief_of_staff"


def test_delegate_only_lead_has_no_work_tools_and_limited_delegates(make_rt):
    rt, _ = make_rt(
        {
            "content_lead": [
                tool("write_file", path="x.md", content="tự làm"),
                tool("delegate", bot="researcher", task="tra cứu", rubric="", skill=""),
                text("ok"),
            ]
        }
    )
    rt.run("content_lead", "Làm chiến dịch")
    call_tools = rt.llm.calls[0]["tools"]
    assert "write_file" not in call_tools and "delegate" in call_tools
    results = [c["messages"][-1]["content"][0] for c in rt.llm.calls[1:]]
    assert results[0]["is_error"] and "không được cấp" in results[0]["content"]
    assert results[1]["is_error"] and "copywriter" in results[1]["content"]
    assert not (rt.ws.root / "outputs" / "x.md").exists()
    assert "KHÔNG tự làm" in rt.llm.calls[0]["system"]


def test_delegate_only_config_rejects_work_tools():
    with pytest.raises(ValueError):
        BotConfig(name="lead", title="t", role="r", tools=["publish"], delegates=["a"], delegate_only=True)


@pytest.mark.parametrize("approve", [False, True])
def test_publish_requires_human_approval(make_rt, approve):
    rt, op = make_rt(
        {"chief_of_staff": [tool("publish", channel="facebook", title="Ban mic", content="..."), text("xong")]},
        approve=approve,
    )
    rt.run("chief_of_staff", "Đăng bài")
    assert op.requests == [("chief_of_staff", "publish")]
    published = list((rt.ws.root / "outputs").glob("published/**/*.md"))
    assert bool(published) == approve
    if not approve:
        assert "KHÔNG duyệt" in last_tool_result(rt.llm, "chief_of_staff")


def test_self_check_retries_until_rubric_passes(make_rt):
    fail = Grade(passed=False, score=4, criteria=[], feedback="Hook quá dài")
    ok = Grade(passed=True, score=9, criteria=[], feedback="")
    rt, _ = make_rt({"copywriter": [text("bản 1"), text("bản 2")]}, grades=[fail, ok])
    r = rt.run("copywriter", "Viết bài bán hàng", skill="sales-post")
    assert (r.text, r.passed, r.score, r.attempts) == ("bản 2", True, 9, 2)
    feedback = rt.llm.calls[1]["messages"][-1]["content"]
    assert "Hook quá dài" in feedback
    assert "Tiêu chí đạt" in rt.llm.calls[0]["messages"][0]["content"]


def test_loading_skill_mid_run_activates_its_rubric(make_rt):
    rt, _ = make_rt(
        {"scriptwriter": [tool("load_skill", name="video-script"), text("kịch bản")]},
        grades=[Grade(passed=True, score=8, criteria=[], feedback="")],
    )
    r = rt.run("scriptwriter", "Kịch bản quảng cáo")
    assert r.passed is True and r.attempts == 1


def test_self_check_gives_up_after_max_attempts(make_rt):
    fail = Grade(passed=False, score=3, criteria=[], feedback="sai")
    rt, _ = make_rt({"copywriter": [text("a"), text("b"), text("c")]}, grades=[fail] * 3)
    r = rt.run("copywriter", "x", rubric="phải đúng")
    assert r.passed is False and r.attempts == 3 and r.text == "c"


def test_memory_persists_into_next_system_prompt(make_rt):
    rt, _ = make_rt({"writer": [tool("remember", note="Xưng 'mình', câu ngắn"), text("ok"), text("ok2")]})
    rt.run("writer", "Học văn phong")
    rt.run("writer", "Viết lại")
    assert "Xưng 'mình', câu ngắn" in rt.llm.calls[-1]["system"]
    assert "Học văn phong" in rt.llm.calls[-1]["system"]  # nhật ký việc gần đây


def test_write_file_cannot_escape_outputs(make_rt):
    rt, _ = make_rt({"chief_of_staff": [tool("write_file", path="../../evil.md", content="x"), text("x")]})
    rt.run("chief_of_staff", "x")
    assert "outputs/" in last_tool_result(rt.llm, "chief_of_staff")
    assert not (rt.ws.root.parent / "evil.md").exists()


def test_room_mention_routes_only_to_mentioned_bot(make_rt):
    rt, _ = make_rt({"designer": [text("Nên có nút ghi âm to")]})
    room = load_room(rt, "meow", ["pm", "designer", "engineer"])
    replies = post(rt, room, "@designer giao diện app dịch tiếng mèo?")
    assert replies == [("designer", "Nên có nút ghi âm to")]
    assert [c["bot"] for c in rt.llm.calls] == ["designer"]


def test_room_broadcast_lets_bots_pass_and_debate(make_rt):
    rt, _ = make_rt(
        {
            "pm": [text("Thị trường ngách. @engineer làm được không?"), text("Đối tượng: chủ mèo 25-40 tuổi")],
            "designer": [text("PASS")],
            "engineer": [text("Khả thi. @pm cần làm rõ đối tượng"), text("Cần dữ liệu gắn nhãn")],
        }
    )
    room = load_room(rt, "meow", ["pm", "designer", "engineer"])
    replies = post(rt, room, "Ý tưởng: app dịch tiếng mèo sang tiếng Anh")
    # designer PASS bị ẩn; pm @nhắc engineer, engineer @nhắc lại pm -> tranh luận tiếp
    assert [b for b, _ in replies] == ["pm", "engineer", "pm"]
    engineer_prompt = [c for c in rt.llm.calls if c["bot"] == "engineer"][0]["messages"][0]["content"]
    assert "nhắc tên trực tiếp" in engineer_prompt and "@engineer làm được không?" in engineer_prompt
    saved = load_room(rt, "meow")
    assert len(saved.transcript) == 4 and saved.members == ["pm", "designer", "engineer"]


def test_room_debate_is_bounded(make_rt):
    ping = [text("@designer ý bạn?")] * 10
    pong = [text("@pm ý bạn?")] * 10
    rt, _ = make_rt({"pm": ping, "designer": pong})
    room = load_room(rt, "loop", ["pm", "designer"])
    assert len(post(rt, room, "@pm bắt đầu")) == 4  # 2 x số thành viên


def test_seed_skills_listed_and_workspace_overrides(make_rt):
    rt, _ = make_rt({})
    names = [s.name for s in rt.ws.list_skills()]
    assert {"marketplace-listing", "sales-post", "video-script"} <= set(names)
    rt.ws.save_skill("sales-post", "## Mô tả\nBản riêng\n")
    assert rt.ws.get_skill("sales-post").description == "Bản riêng"
