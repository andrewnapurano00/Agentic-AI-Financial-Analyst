from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .manager import MODEL_PRICING, RESEARCH_RULES, _estimated_cost, _token_usage, message_text
from .models import Evidence, ResearchRequest, dumps, json_safe, utc_now
from .prompt_context import compact, evidence_context


CostMode = Literal["Economy", "Balanced", "Maximum quality"]


@dataclass(frozen=True)
class V2Mode:
    planning_model: str
    report_model: str
    review_model: str
    specialist_model: str
    lead_model: str
    standard_report_tokens: int
    extended_report_tokens: int
    interpretive_review: bool


MODES: dict[str, V2Mode] = {
    "Economy": V2Mode("gpt-5-nano", "gpt-5-mini", "gpt-5-nano", "gpt-5-nano", "gpt-5-mini", 1800, 3000, False),
    "Balanced": V2Mode("gpt-5-nano", "gpt-5-mini", "gpt-5-nano", "gpt-5-nano", "gpt-5-mini", 2200, 3500, True),
    "Maximum quality": V2Mode("gpt-5-mini", "gpt-5", "gpt-5-mini", "gpt-5-mini", "gpt-5", 2200, 3500, True),
}


def build_stage_llm(provider: str, model: str, *, openai_api_key: str = "", groq_api_key: str = "",
                    ollama_base_url: str = "http://localhost:11434/v1"):
    """Create a LangChain chat model without coupling the research manager to a provider."""
    provider = provider.lower()
    common = {"model": model, "timeout": 90, "max_retries": 1}
    if provider == "openai":
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for the selected OpenAI stage.")
        return ChatOpenAI(api_key=openai_api_key, stream_usage=True, **common)
    if provider == "groq":
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY is required for the selected Groq stage.")
        try:
            from langchain_groq import ChatGroq
        except ImportError as exc:
            raise RuntimeError("Install langchain-groq to use Groq in Deep Research V2.") from exc
        return ChatGroq(api_key=groq_api_key, **common)
    if provider == "ollama":
        return ChatOpenAI(api_key="ollama", base_url=ollama_base_url.rstrip("/") + "/", **common)
    raise ValueError(f"Unsupported model provider: {provider}")


def stage_configuration(mode: str, *, light_provider: str, light_model: str | None = None) -> dict[str, Any]:
    selected = MODES[mode]
    light = light_model.strip() if light_model and light_model.strip() else selected.planning_model
    maximum = mode == "Maximum quality"
    utility_provider = "OpenAI" if maximum else light_provider
    utility_model = selected.planning_model if maximum else light
    return {
        "mode": mode,
        "routes": {
            "plan": {"provider": utility_provider, "model": utility_model},
            "draft": {"provider": "OpenAI", "model": selected.report_model},
            "review": {"provider": "OpenAI" if maximum else light_provider,
                       "model": selected.review_model if maximum else light},
            "follow_up": {"provider": "OpenAI", "model": selected.report_model},
            "crew_specialists": {"provider": "OpenAI" if maximum else light_provider,
                                 "model": selected.specialist_model if maximum else light},
            "crew_lead": {"provider": "OpenAI", "model": selected.lead_model},
        },
        "limits": {
            "plan": (75, 650),
            "draft": (150, selected.extended_report_tokens),
            "review": (90, 1200),
            "follow_up": (90, 1000),
        },
        "depth_draft_tokens": {"Standard": selected.standard_report_tokens, "Extended": selected.extended_report_tokens},
        "contexts": {
            "draft_standard": 22000, "draft_extended": 34000,
            "review_standard": 12000, "review_extended": 14000,
            "follow_up": 12000, "committee": 10000,
        },
        "interpretive_review": selected.interpretive_review,
    }


def validate_report(request: ResearchRequest, evidence: list[Evidence], report: str) -> list[str]:
    """Cheap mechanical checks; nuanced judgment remains a model task when enabled."""
    issues: list[str] = []
    headings = ("Executive Investment Thesis", "Risks", "invalidation")
    lower = report.lower()
    for heading in headings:
        if heading.lower() not in lower:
            issues.append(f"Required report topic is missing: {heading}.")
    for symbol in request.symbols:
        if not re.search(rf"\b{re.escape(symbol)}\b", report, flags=re.IGNORECASE):
            issues.append(f"Selected ticker is not discussed: {symbol}.")
    known = {item.id for item in evidence}
    cited = {value for value in re.findall(r"\bE\d{3}\b", report)}
    unknown = cited - known
    if unknown:
        issues.append("Unknown evidence IDs: " + ", ".join(sorted(unknown)))
    if not cited:
        issues.append("No evidence IDs are cited.")
    if not re.search(r"\b(?:USD|EUR|GBP|JPY|currency)\b", report, flags=re.IGNORECASE):
        issues.append("No currency label or limitation is present.")
    if not re.search(r"\b(?:20\d{2}|as[- ]of|dated|period)\b", report, flags=re.IGNORECASE):
        issues.append("No date or as-of context is present.")
    return issues


def prompt_diagnostics(evidence: list[Evidence], limits: dict[str, int], *, focus: str) -> list[dict]:
    rows = []
    for name, limit in limits.items():
        if not isinstance(limit, int):
            continue
        packet = evidence_context(evidence, limit, focus=focus)
        characters = len(dumps(packet))
        rows.append({"context": name, "limit_characters": limit, "actual_characters": characters,
                     "estimated_tokens": (characters + 3) // 4})
    return rows


def research_cache_key(request: ResearchRequest, config: dict, evidence: list[dict] | None = None) -> str:
    dates = []
    for item in evidence or []:
        dates.append((item.get("symbol"), item.get("category"), item.get("retrieved_at")))
    value = {"request": asdict(request), "config": config, "provider_dates": dates}
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()[:20]


class QuickDecision(BaseModel):
    verdict: Literal["BUY", "WATCH", "NO_BUY"]
    preferred_ticker: str | None = None
    confidence: int = Field(ge=0, le=100)
    summary: str
    catalysts: list[str]
    risks: list[str]
    invalidation_signals: list[str]
    limitations: list[str]


def compact_decision_brief(result: dict, max_chars: int = 10000) -> dict:
    evidence = [Evidence(**item) for item in result.get("evidence", [])]
    brief = {
        "request": result.get("request", {}), "created_at": result.get("created_at"),
        "comparison": compact(result.get("comparison", []), list_limit=8, string_limit=500),
        "warnings": compact(result.get("warnings", []), list_limit=8, string_limit=300),
        "gaps": compact(result.get("gaps", []), list_limit=8, string_limit=300),
        "evidence": evidence_context(evidence, max_chars, focus="valuation growth risk catalysts recommendation"),
    }
    text = dumps(brief)
    if len(text) > max_chars:
        brief["evidence"] = brief["evidence"][:max(1, len(brief["evidence"]) // 2)]
        brief["comparison"] = compact(brief["comparison"], list_limit=4, string_limit=240)
        while len(dumps(brief)) > max_chars and len(brief["evidence"]) > 1:
            brief["evidence"] = brief["evidence"][:-1]
        brief["truncated"] = True
    return json_safe(brief)


def run_quick_decision(result: dict, llm, *, model: str, max_chars: int = 10000) -> tuple[dict, dict]:
    brief = compact_decision_brief(result, max_chars)
    symbols = result.get("request", {}).get("symbols", [])
    structured = llm.with_structured_output(QuickDecision, include_raw=True)
    instruction = (
        RESEARCH_RULES + "\nMake one concise investment decision from the compact brief. Select only from "
        + ", ".join(symbols) + ". Use NO_BUY and null preferred_ticker when none qualifies."
    )
    started = __import__("time").monotonic()
    response = structured.invoke(instruction + "\n" + dumps(brief), max_completion_tokens=900)
    parsed = response.get("parsed") if isinstance(response, dict) else response
    raw = response.get("raw") if isinstance(response, dict) else None
    if parsed is None:
        raise RuntimeError("The quick-decision model did not return a valid structured result.")
    value = parsed.model_dump(mode="json") if hasattr(parsed, "model_dump") else dict(parsed)
    preferred = value.get("preferred_ticker")
    if preferred and str(preferred).upper() not in set(symbols):
        raise ValueError("The quick decision selected a ticker outside the research universe.")
    usage = getattr(raw, "usage_metadata", None)
    input_chars = len(instruction) + len(dumps(brief))
    counts = _token_usage(usage, input_characters=input_chars, output_text=dumps(value))
    diagnostic = {"stage": "quick_decision", "model": model, **counts,
                  "seconds": round(__import__("time").monotonic() - started, 2), "status": "ok"}
    cost = _estimated_cost(model, counts)
    if cost is not None:
        diagnostic["estimated_cost_usd"] = cost
    value.update({"created_at": utc_now(), "model": model,
                  "disclaimer": "AI-generated research opinion, not personalized investment advice."})
    return value, diagnostic


def committee_diagnostics(decision: dict) -> list[dict]:
    """Expose Crew usage by stage; allocation is explicitly estimated when Crew reports only a total."""
    usage = decision.get("usage_metrics") or {}
    if not isinstance(usage, dict):
        usage = {}
    total_input = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    total_output = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    rows = []
    for stage, model, fraction in (
        ("crew_specialists", decision.get("specialist_model", "unknown"), 2 / 3),
        ("crew_lead", decision.get("model", "unknown"), 1 / 3),
    ):
        counts = {"input_tokens": round(total_input * fraction), "cached_input_tokens": 0,
                  "output_tokens": round(total_output * fraction), "reasoning_tokens": 0,
                  "token_counts_estimated": True}
        row = {"stage": stage, "model": model, **counts, "status": "ok", "seconds": 0.0,
               "usage_note": "CrewAI reported aggregate usage; stage allocation is estimated."}
        cost = _estimated_cost(str(model), counts)
        if cost is not None:
            row["estimated_cost_usd"] = cost
        rows.append(row)
    return rows


def projected_cost(model: str, *, input_characters: int, output_tokens: int) -> float:
    prices = next((value for key, value in MODEL_PRICING.items()
                   if model.lower() == key or model.lower().startswith(key + "-")), None)
    if not prices:
        return 0.0
    return round((((input_characters + 3) // 4) * prices[0] + output_tokens * prices[2]) / 1_000_000, 6)
