# agent-team-24-7 — Scaffold dự án

Bộ khung dự án theo kiến trúc trong [`docs/research/doi-ai-agent-tu-dong-24-7.md`](../../docs/research/doi-ai-agent-tu-dong-24-7.md): một đội AI agent chạy 24/7, nhận **mục tiêu** qua chatbot Telegram, tự lập kế hoạch, chia task, giao cho agent worker, review và báo cáo.

> Đây là **khung** (skeleton): các module đã có interface, luồng chạy và schema DB. Phần gọi LLM và tool được đánh dấu `TODO` để bạn gắn framework mình chọn (LangGraph, CrewAI, Claude Agent SDK, OpenAI Agents SDK...).

## Cấu trúc

```
agent-team-24-7/
├── gateway/            # Lớp chatbot: Telegram bot, parse lệnh /goal /status /approve...
│   ├── telegram_bot.py
│   └── commands.py
├── orchestrator/       # Bộ não: planner phân rã goal -> task, heartbeat tái lập kế hoạch
│   ├── planner.py
│   └── heartbeat.py
├── board/              # Nguồn sự thật: goals, tasks, runs, approvals (Postgres)
│   ├── schema.sql
│   ├── models.py
│   └── repo.py
├── runtime/            # Hàng đợi + worker loop (Redis), retry, idempotency
│   ├── queue.py
│   └── worker.py
├── agents/             # Đội agent: registry vai trò, base class, prompt từng vai
│   ├── registry.yaml
│   ├── base.py
│   ├── reviewer.py
│   └── prompts/*.md
├── policy/             # Chốt chặn: tool allowlist, hành động cần duyệt, ngân sách
│   ├── policy.yaml
│   └── guard.py
├── memory/             # Bộ nhớ dài hạn (pgvector) + skills tích lũy
│   └── store.py
├── tools/              # Cấu hình MCP server cho agent
│   └── mcp_servers.json
├── supervisor/         # Watchdog: task treo, vượt ngân sách, báo cáo sáng
│   └── watchdog.py
├── observability/      # Tracing (Langfuse / OpenTelemetry)
│   └── tracing.py
├── infra/              # Docker Compose: app, worker, postgres, redis, langfuse
│   ├── docker-compose.yml
│   └── Dockerfile
├── tests/              # Test luồng chính không cần LLM
│   └── test_flow.py
├── skill/              # Bản nháp SKILL.md để đóng gói thành skill tái sử dụng
│   └── SKILL.md
├── config.py
├── main.py             # Entrypoint: chạy gateway | worker | heartbeat | watchdog
├── pyproject.toml
└── .env.example
```

## Ánh xạ kiến trúc -> thư mục

| Lớp trong thiết kế | Thư mục |
|---|---|
| Kênh chat + Chat Gateway | `gateway/` |
| Orchestrator / Planner | `orchestrator/` |
| Goal & Task Board | `board/` |
| Task queue / runtime bền | `runtime/` |
| Đội agent worker + Reviewer | `agents/` |
| Policy & Budget guard | `policy/` |
| Memory | `memory/` |
| Tools (MCP) | `tools/` |
| Supervisor / Watchdog | `supervisor/` |
| Observability | `observability/` |

## Chạy thử

```bash
cp .env.example .env   # điền TELEGRAM_BOT_TOKEN, LLM API key, ALLOWED_USER_IDS
docker compose -f infra/docker-compose.yml up -d --build
```

Chạy test luồng (không cần LLM, không cần DB):

```bash
pip install -e ".[dev]" && pytest -q
```

## Các bước gắn LLM thật

1. `agents/base.py` → `Agent.run()`: gọi LLM/framework với `system_prompt` + toolset từ `registry.yaml`.
2. `orchestrator/planner.py` → `Planner.plan()`: gọi LLM trả JSON danh sách task theo schema `TaskDraft`.
3. `agents/reviewer.py` → chấm kết quả theo `acceptance_criteria`.
4. `board/repo.py` → thay `InMemoryBoard` bằng `PostgresBoard` (schema trong `board/schema.sql`).
