"""LLM giả: trả lần lượt các lượt đã viết sẵn, để test vòng lặp agent mà không gọi Claude thật."""

from __future__ import annotations

from types import SimpleNamespace as NS


def text(t):
    return NS(type="text", text=t)


def call(_tool, **inp):
    call.n += 1
    return NS(type="tool_use", id=f"toolu_{call.n}", name=_tool, input=inp)


call.n = 0


class FakeLLM:
    def __init__(self, turns):
        self.turns = list(turns)
        self.requests = []

    def __call__(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})  # chụp lại, list gốc còn thay đổi
        if not self.turns:
            raise AssertionError("LLM giả hết lượt viết sẵn")
        blocks = self.turns.pop(0)
        stop = "tool_use" if any(b.type == "tool_use" for b in blocks) else "end_turn"
        return NS(content=blocks, stop_reason=stop, _request_id="req_fake",
                  usage=NS(input_tokens=1000, output_tokens=200))

    def tool_results(self, i):
        """Các tool_result Claude nhận được ở request thứ i."""
        last = self.requests[i]["messages"][-1]
        return last["content"] if isinstance(last["content"], list) else []
