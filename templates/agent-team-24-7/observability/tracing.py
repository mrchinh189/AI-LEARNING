"""Tracing: bọc mỗi lần agent chạy thành một span (Langfuse hoặc OpenTelemetry)."""
from __future__ import annotations

from contextlib import contextmanager


@contextmanager
def span(name: str, **attrs):
    """TODO: thay bằng langfuse.start_as_current_span / opentelemetry tracer."""
    yield {"name": name, **attrs}
