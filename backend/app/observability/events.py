"""Sanitization helpers for the durable research event ledger."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .logging import REDACTED


_SECRET_KEYS = {"api_key", "authorization", "cookie", "password", "secret", "token"}
_CONTENT_KEYS = {
    "content",
    "document",
    "documents",
    "final_report",
    "input",
    "output",
    "prompt",
    "query",
    "report",
    "response",
    "text",
}


def _digest(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _content_summary(value: Any) -> dict[str, Any]:
    if isinstance(value, (list, tuple, set, Mapping)):
        return {"redacted": True, "count": len(value), "sha256": _digest(value)}
    rendered = str(value)
    return {"redacted": True, "length": len(rendered), "sha256": _digest(rendered)}


def sanitize_event_payload(value: Any, *, max_text_length: int = 512) -> Any:
    """Keep diagnostic metadata while excluding secrets and content-heavy fields."""

    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            normalized_key = key.strip().lower()
            if normalized_key in _SECRET_KEYS or normalized_key.endswith(("_secret", "_password", "_api_key")):
                sanitized[key] = REDACTED
            elif normalized_key in _CONTENT_KEYS:
                sanitized[key] = _content_summary(item)
            else:
                sanitized[key] = sanitize_event_payload(item, max_text_length=max_text_length)
        return sanitized
    if isinstance(value, (list, tuple, set)):
        return [sanitize_event_payload(item, max_text_length=max_text_length) for item in value[:100]]
    if isinstance(value, str) and len(value) > max_text_length:
        return f"{value[:max_text_length]}...[TRUNCATED]"
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)

