"""Correlation context shared by logs, metrics, traces, and research events."""

from __future__ import annotations

import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, replace
from typing import Iterator
from uuid import uuid4


_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


@dataclass(frozen=True, slots=True)
class ObservabilityContext:
    """Identifiers that connect one request to its research execution."""

    request_id: str
    session_id: str | None = None
    research_id: str | None = None
    run_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None

    def as_log_fields(self) -> dict[str, str]:
        """Return only populated identifiers, suitable for structured logs."""

        return {key: value for key, value in asdict(self).items() if value is not None}


_CURRENT_CONTEXT: ContextVar[ObservabilityContext | None] = ContextVar(
    "observability_context",
    default=None,
)


def normalize_correlation_id(value: str | None, *, prefix: str = "req") -> str:
    """Accept a safe external identifier or generate an opaque replacement."""

    if value and _CORRELATION_ID_PATTERN.fullmatch(value):
        return value
    return f"{prefix}-{uuid4().hex}"


def new_request_context(
    *,
    request_id: str | None = None,
    session_id: str | None = None,
    research_id: str | None = None,
) -> ObservabilityContext:
    """Create the root context for an incoming HTTP request."""

    return ObservabilityContext(
        request_id=normalize_correlation_id(request_id),
        session_id=session_id,
        research_id=research_id,
    )


def current_context() -> ObservabilityContext | None:
    """Return the context bound to the current async task, if any."""

    return _CURRENT_CONTEXT.get()


@contextmanager
def bind_context(
    context: ObservabilityContext | None = None,
    **updates: str | None,
) -> Iterator[ObservabilityContext]:
    """Temporarily bind a context and restore its parent on exit."""

    parent = current_context()
    if context is None:
        context = parent or new_request_context()
    if updates:
        unknown = set(updates) - set(ObservabilityContext.__dataclass_fields__)
        if unknown:
            raise TypeError(f"Unknown observability context fields: {sorted(unknown)}")
        context = replace(context, **updates)

    token = _CURRENT_CONTEXT.set(context)
    try:
        yield context
    finally:
        _CURRENT_CONTEXT.reset(token)

