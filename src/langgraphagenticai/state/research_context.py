"""Metadata-only company navigation; never a financial evidence packet."""
from dataclasses import dataclass
from typing import Literal
import re

Workspace = Literal["Introduction", "Top Movers", "Research", "Equity Report", "Stock Screener", "Portfolio Lab", "Deep Research", "Deep Research V2"]
WORKSPACES = ("Introduction", "Top Movers", "Research", "Equity Report", "Stock Screener", "Portfolio Lab", "Deep Research", "Deep Research V2")


def normalize_company_symbol(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Company symbol must be text.")
    symbol = value.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{0,9}(?:[.-][A-Z0-9]{1,3})?", symbol):
        raise ValueError("Enter a valid company ticker, such as AAPL or BRK-B.")
    return symbol


@dataclass(frozen=True)
class SavedEvidenceReference:
    reference_id: str
    source: str | None = None
    as_of: str | None = None

    def __post_init__(self):
        # Opaque local identifiers and labels only: no URLs, credentials or payloads.
        from langgraphagenticai.utils.safety import redact_sensitive_text
        for value in (self.reference_id, self.source):
            if value is not None and (not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_. -]{1,100}", value) or redact_sensitive_text(value) != value):
                raise ValueError("Use a local saved-reference identifier and source label.")
        if self.as_of is not None:
            from datetime import datetime
            if not isinstance(self.as_of, str):
                raise ValueError("As-of metadata must be a dated string.")
            datetime.fromisoformat(self.as_of.replace("Z", "+00:00"))


@dataclass(frozen=True)
class ResearchContext:
    symbols: tuple[str, ...]
    destination: Workspace
    intent: Literal["analyze", "compare", "deep_research"]
    origin: Workspace
    saved_reference: SavedEvidenceReference | None = None

    def __post_init__(self):
        if self.origin not in WORKSPACES or self.destination not in WORKSPACES:
            raise ValueError("Unknown workspace.")
        if self.destination not in ("Introduction", "Research", "Equity Report", "Deep Research", "Deep Research V2"):
            raise ValueError("Unsupported company destination.")
        if self.intent not in ("analyze", "compare", "deep_research"):
            raise ValueError("Unknown handoff intent.")
        if not isinstance(self.symbols, (tuple, list)) or not self.symbols:
            raise ValueError("Select at least one company.")
        normalized = tuple(dict.fromkeys(normalize_company_symbol(x) for x in self.symbols))
        maximum = 1 if self.destination == "Introduction" else 4
        if len(normalized) > maximum:
            raise ValueError(f"This destination accepts at most {maximum} companies.")
        if self.intent == "compare" and len(normalized) < 2:
            raise ValueError("Comparison requires at least two companies.")
        if self.saved_reference is not None and not isinstance(self.saved_reference, SavedEvidenceReference):
            raise ValueError("Saved evidence must be metadata only.")
        object.__setattr__(self, "symbols", normalized)
