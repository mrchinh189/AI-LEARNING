"""Lớp gọi LLM: Claude (Anthropic) hoặc Gemini (Google).

Mỗi provider nhận lịch sử hội thoại dạng [{"role": "user"|"assistant", "text": str}]
và trả về câu trả lời dạng chuỗi.
"""

from __future__ import annotations

import os


class ClaudeProvider:
    name = "claude"

    def __init__(self) -> None:
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.AsyncAnthropic()  # đọc ANTHROPIC_API_KEY
        self.model = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
        self.effort = os.getenv("CLAUDE_EFFORT", "low")

    async def reply(self, system: str, history: list[dict]) -> str:
        messages = [{"role": m["role"], "content": m["text"]} for m in history]
        response = await self.client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=messages,
            output_config={"effort": self.effort},
            # Nếu Claude từ chối vì bộ lọc an toàn, API tự chạy lại trên model dự phòng.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            return "Xin lỗi, mình không thể trả lời yêu cầu này."
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        return text or "(Không có nội dung trả lời)"


class GeminiProvider:
    name = "gemini"

    def __init__(self) -> None:
        from google import genai
        from google.genai import types

        self.types = types
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    async def reply(self, system: str, history: list[dict]) -> str:
        t = self.types
        contents = [
            t.Content(
                role="model" if m["role"] == "assistant" else "user",
                parts=[t.Part(text=m["text"])],
            )
            for m in history
        ]
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=t.GenerateContentConfig(system_instruction=system),
        )
        return (response.text or "").strip() or "(Không có nội dung trả lời)"


def build_providers() -> dict:
    """Khởi tạo các provider có API key."""
    providers = {}
    if os.getenv("ANTHROPIC_API_KEY"):
        providers["claude"] = ClaudeProvider()
    if os.getenv("GEMINI_API_KEY"):
        providers["gemini"] = GeminiProvider()
    if not providers:
        raise SystemExit("Cần đặt ít nhất một trong ANTHROPIC_API_KEY hoặc GEMINI_API_KEY trong .env")
    return providers
