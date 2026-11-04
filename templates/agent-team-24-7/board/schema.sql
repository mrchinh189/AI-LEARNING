-- Goal & Task Board: nguồn sự thật của toàn hệ thống
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE goals (
    id            BIGSERIAL PRIMARY KEY,
    owner_user_id BIGINT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT,
    status        TEXT NOT NULL DEFAULT 'planning',  -- planning|awaiting_approval|active|paused|done|cancelled
    priority      TEXT NOT NULL DEFAULT 'normal',     -- low|normal|high
    budget_usd    NUMERIC(10,2) NOT NULL DEFAULT 5,
    spent_usd     NUMERIC(10,4) NOT NULL DEFAULT 0,
    deadline      TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tasks (
    id                  BIGSERIAL PRIMARY KEY,
    goal_id             BIGINT NOT NULL REFERENCES goals(id),
    title               TEXT NOT NULL,
    instructions        TEXT NOT NULL,
    acceptance_criteria TEXT NOT NULL,
    role                TEXT NOT NULL,               -- khớp agents/registry.yaml
    status              TEXT NOT NULL DEFAULT 'todo',-- todo|queued|doing|review|done|blocked|cancelled
    depends_on          BIGINT[] NOT NULL DEFAULT '{}',
    attempts            INT NOT NULL DEFAULT 0,
    result              TEXT,
    review_feedback     TEXT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON tasks (goal_id, status);

CREATE TABLE runs (                                  -- mỗi lần agent chạy một task
    id          BIGSERIAL PRIMARY KEY,
    task_id     BIGINT NOT NULL REFERENCES tasks(id),
    agent_role  TEXT NOT NULL,
    model       TEXT,
    cost_usd    NUMERIC(10,4) NOT NULL DEFAULT 0,
    trace_id    TEXT,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

CREATE TABLE approvals (                             -- hành động rủi ro chờ người duyệt
    id              BIGSERIAL PRIMARY KEY,
    task_id         BIGINT REFERENCES tasks(id),
    action          TEXT NOT NULL,
    payload         JSONB NOT NULL,
    idempotency_key TEXT UNIQUE NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending', -- pending|approved|rejected
    decided_at      TIMESTAMPTZ
);

CREATE TABLE memories (
    id        BIGSERIAL PRIMARY KEY,
    goal_id   BIGINT REFERENCES goals(id),
    kind      TEXT NOT NULL,                         -- fact|lesson|skill
    content   TEXT NOT NULL,
    embedding vector(1536)
);
