"""Gọi Claude API. Lỗi hoặc tắt LLM thì trả None để agent dùng bản soạn sẵn theo luật."""

import json
import logging

import anthropic

from .config import settings

log = logging.getLogger("eup_agents.llm")

# Model hỗ trợ server-side fallback dạng "default" khi bị từ chối (refusal).
_FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # đọc ANTHROPIC_API_KEY từ môi trường
    return _client


def ask(system: str, user: str, schema: dict | None = None, max_tokens: int = 16000) -> str | dict | None:
    """Một lần gọi model. Có schema thì trả dict JSON đúng schema."""
    if not settings.llm_enabled:
        return None
    output_config: dict = {"effort": settings.llm_effort}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    kwargs = dict(
        model=settings.llm_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config=output_config,
    )
    if settings.llm_model in _FALLBACK_MODELS:
        kwargs.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    try:
        resp = _get_client().beta.messages.create(**kwargs)
    except TypeError as e:
        if "authentication" not in str(e):
            raise
        log.error("Chưa cấu hình ANTHROPIC_API_KEY — chạy tiếp không có LLM")
        return None
    except anthropic.AuthenticationError:
        log.error("ANTHROPIC_API_KEY sai hoặc chưa đặt — chạy tiếp không có LLM")
        return None
    except anthropic.RateLimitError:
        log.warning("Claude API giới hạn tốc độ — chạy tiếp không có LLM")
        return None
    except anthropic.APIStatusError as e:
        log.error("Claude API lỗi %s: %s", e.status_code, e.message)
        return None
    except anthropic.APIConnectionError:
        log.error("Không kết nối được Claude API — chạy tiếp không có LLM")
        return None

    if resp.stop_reason == "refusal":
        log.warning("Model từ chối yêu cầu (request id %s)", resp._request_id)
        return None
    text = "".join(b.text for b in resp.content if b.type == "text")
    if schema:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            log.error("Model trả JSON không hợp lệ (request id %s)", resp._request_id)
            return None
    return text
