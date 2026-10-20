"""Bounded paper-lab text, including bare credential assignments in narratives."""
import re
from langgraphagenticai.utils.safety import redact_sensitive_text


def safe_text(value, *, max_length=None):
    text = redact_sensitive_text(value)
    text = re.sub(r"(?i)(\b(?:api[_-]?key|token|password|secret)\s*[:=]\s*)[^\s,;\"'<>\\]+",
                  r"\1[REDACTED]", text)
    return text if max_length is None else text[:max_length]
