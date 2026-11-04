"""Lớp mỏng bọc Anthropic SDK — mọi lời gọi model đi qua đây.

Tách riêng để test có thể thay bằng FakeLLM, không cần API key.
"""

from __future__ import annotations

import os
from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel

MODEL = os.environ.get("AI_TEAM_MODEL", "claude-opus-5-5")

# Khi model từ chối (stop_reason == "refusal"), API tự chạy lại yêu cầu trên
# model dự phòng phù hợp. Bỏ hai dòng này nếu không muốn dùng fallback.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACKS = "default"

T = TypeVar("T", bound=BaseModel)


class RefusalError(RuntimeError):
    pass


class LLM:
    def __init__(self, client: anthropic.Anthropic | None = None, model: str = MODEL):
        self.client = client or anthropic.Anthropic()
        self.model = model

    def create(
        self,
        *,
        bot: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        effort: str = "medium",
        max_tokens: int = 16000,
    ):
        """Một lượt gọi model cho bot `bot` (tham số `bot` chỉ để FakeLLM định tuyến)."""
        kwargs: dict[str, Any] = dict(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            output_config={"effort": effort},
            betas=[FALLBACK_BETA],
            fallbacks=FALLBACKS,
        )
        if tools:
            kwargs["tools"] = tools
        return self.client.beta.messages.create(**kwargs)

    def parse(
        self,
        *,
        purpose: str,
        system: str,
        prompt: str,
        schema: type[T],
        effort: str = "medium",
        max_tokens: int = 16000,
    ) -> T:
        """Gọi model và trả về đối tượng Pydantic đã kiểm tra theo `schema`."""
        response = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
            output_config={"effort": effort},
            betas=[FALLBACK_BETA],
            fallbacks=FALLBACKS,
        )
        if response.stop_reason == "refusal":
            raise RefusalError(f"{purpose}: model từ chối yêu cầu")
        return response.parsed_output
