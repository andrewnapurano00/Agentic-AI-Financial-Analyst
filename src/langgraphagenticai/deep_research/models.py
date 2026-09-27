from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_symbols(text: str) -> list[str]:
    symbols = list(dict.fromkeys(s.upper() for s in re.split(r"[,;\s]+", text.strip()) if s))
    if not symbols or len(symbols) > 4:
        raise ValueError("Enter between one and four ticker symbols.")
    if any(not re.fullmatch(r"[A-Z0-9^][A-Z0-9.\-^=]{0,14}", s) for s in symbols):
        raise ValueError("Use ticker symbols such as AAPL, MSFT, or BRK-B.")
    return symbols


def safe_url(value: Any) -> str:
    try:
        parts = urlsplit(str(value or ""))
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username:
            return ""
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
    except ValueError:
        return ""


def json_safe(value: Any) -> Any:
    """Remove credentials, binary artifacts and non-finite numbers from evidence."""
    if isinstance(value, dict):
        return {
            str(k): json_safe(v) for k, v in value.items()
            if not any(part in str(k).lower() for part in ("api_key", "apikey", "secret", "token", "password", "_bytes"))
            and not isinstance(v, bytes)
        }
    if isinstance(value, (tuple, list)):
        return [json_safe(v) for v in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        return re.sub(r"(?i)([?&](?:apikey|api_key|token|key)=)[^&\s\"'<>]+", r"\1[REDACTED]", value)
    if value is None or isinstance(value, (int, bool)):
        return value
    if hasattr(value, "item"):
        return json_safe(value.item())
    return str(value)


def dumps(value: Any) -> str:
    return json.dumps(json_safe(value), ensure_ascii=False, allow_nan=False, default=str)


@dataclass
class ResearchRequest:
    symbols: list[str]
    question: str = "Develop an investment thesis and compare the relative opportunities."
    horizon: str = "1–3 years"
    depth: str = "Standard"
    period: str = "annual"
    news_days: int = 30
    include_news: bool = True

    def __post_init__(self):
        self.symbols = parse_symbols(",".join(self.symbols))
        if self.depth not in {"Standard", "Extended"} or self.period not in {"annual", "quarter"}:
            raise ValueError("Unsupported research depth or statement period.")
        if self.news_days not in {7, 30, 90}:
            raise ValueError("News window must be 7, 30, or 90 days.")
        self.question = self.question.strip()[:4000] or "Develop an investment thesis."


@dataclass
class Evidence:
    id: str
    symbol: str
    category: str
    title: str
    provider: str
    data: Any
    retrieved_at: str = field(default_factory=utc_now)
    url: str = ""
    status: str = "ok"
    note: str = ""

    def to_dict(self) -> dict:
        return json_safe(asdict(self))
