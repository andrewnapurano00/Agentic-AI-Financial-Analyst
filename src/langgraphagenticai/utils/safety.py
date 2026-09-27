from __future__ import annotations

import re
from typing import Any


_QUERY_SECRET = re.compile(
    r"(?i)([?&](?:api[_-]?key|apikey|api_token|token|access_token|key)=)[^&\s\"'<>]+"
)
_HEADER_SECRET = re.compile(
    r"(?i)((?:authorization|x-api-key)\s*[:=]\s*(?:bearer\s+)?)[^,;\s\"']+"
)
_OPENAI_SECRET = re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b")


def redact_sensitive_text(value: Any, *, max_length: int | None = None) -> str:
    """Remove common credential forms from text before logs, UI, or exports."""
    text = str(value or "")
    text = _QUERY_SECRET.sub(r"\1[REDACTED]", text)
    text = _HEADER_SECRET.sub(r"\1[REDACTED]", text)
    text = _OPENAI_SECRET.sub("[REDACTED]", text)
    if max_length is not None and len(text) > max_length:
        return text[:max_length] + "..."
    return text


def sanitize_error(error: BaseException | str, *, fallback: str = "The request failed.") -> str:
    """Return bounded, credential-safe error text suitable for users and telemetry."""
    cleaned = redact_sensitive_text(error, max_length=600).strip()
    return cleaned or fallback


def redact_value(value: Any) -> Any:
    """Recursively redact values passed to structured logging."""
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if any(marker in str(key).lower() for marker in ("api_key", "apikey", "token", "password", "secret"))
            else redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    return value
