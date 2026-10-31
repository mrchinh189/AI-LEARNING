"""Lớp mỏng bọc Anthropic SDK: một chỗ duy nhất gọi model, xử lý từ chối, pause_turn và chế độ giả lập."""
import json
import logging
from dataclasses import dataclass, field

import anthropic

from . import config

log = logging.getLogger(__name__)

# Với Opus 5.5 / Sonnet 5.5: nếu model từ chối vì lý do an toàn, API tự chạy lại bằng model dự phòng phù hợp
FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}

_client: anthropic.Anthropic | None = None


class LLMRefusal(RuntimeError):
    """Model từ chối trả lời (stop_reason = refusal)."""


@dataclass
class Answer:
    text: str
    sources: list[tuple[str, str]] = field(default_factory=list)  # (tiêu đề, url)


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        # Đọc ANTHROPIC_API_KEY từ môi trường; tự retry lỗi mạng / 429 / 5xx
        _client = anthropic.Anthropic(max_retries=3)
    return _client


def _create(model: str, **kwargs):
    client = _get_client()
    if model in FALLBACK_MODELS:
        return client.beta.messages.create(model=model, betas=[FALLBACK_BETA], fallbacks="default", **kwargs)
    return client.messages.create(model=model, **kwargs)


def _check(resp) -> None:
    if resp.stop_reason == "refusal":
        category = getattr(getattr(resp, "stop_details", None), "category", None)
        raise LLMRefusal(f"Model từ chối yêu cầu (category={category})")
    if resp.stop_reason == "max_tokens":
        log.warning("Câu trả lời bị cắt do chạm max_tokens (model=%s)", resp.model)


def _text_of(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text")


def _sources_of(resp) -> list[tuple[str, str]]:
    found = []
    for block in resp.content:
        for cit in getattr(block, "citations", None) or []:
            url = getattr(cit, "url", None)
            if url:
                found.append((getattr(cit, "title", None) or url, url))
    return found


def ask_json(model: str, system: str, prompt: str, schema: dict, *,
             effort: str = "low", max_tokens: int = 4000, fake=None) -> dict:
    """Gọi model và ép kết quả theo JSON schema (structured outputs)."""
    if config.FAKE_LLM:
        return fake() if callable(fake) else fake
    resp = _create(
        model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
    )
    _check(resp)
    return json.loads(_text_of(resp))


def ask_text(model: str, system: str, prompt: str, *, effort: str = "low", max_tokens: int = 16000,
             tools: list | None = None, fake=None, max_continuations: int = 5) -> Answer:
    """Gọi model lấy văn bản; hỗ trợ server tool (web search) với vòng lặp pause_turn."""
    if config.FAKE_LLM:
        return Answer(fake() if callable(fake) else (fake or "[FAKE_LLM] câu trả lời giả lập."))
    messages = [{"role": "user", "content": prompt}]
    kwargs = {"max_tokens": max_tokens, "system": system, "output_config": {"effort": effort}}
    if tools:
        kwargs["tools"] = tools
    texts, sources = [], []
    for _ in range(max_continuations + 1):
        resp = _create(model, messages=messages, **kwargs)
        _check(resp)
        texts.append(_text_of(resp))
        sources.extend(_sources_of(resp))
        if resp.stop_reason != "pause_turn":
            break
        # Công cụ phía server chạm giới hạn vòng lặp: gửi lại để API tiếp tục từ chỗ dừng
        messages.append({"role": "assistant", "content": resp.content})
    return Answer("".join(texts).strip(), list(dict.fromkeys(sources)))
