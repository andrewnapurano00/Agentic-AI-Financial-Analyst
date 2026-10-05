from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from langgraphagenticai.deep_research.models import json_safe, utc_now


class TickerDecision(BaseModel):
    ticker: str
    recommendation: Literal["BUY", "HOLD", "SELL"]
    confidence: int = Field(ge=0, le=100)
    rationale: str
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    invalidation_signals: list[str] = Field(default_factory=list)


class CommitteeDecision(BaseModel):
    mode: Literal["single_ticker", "multi_ticker_comparison"]
    summary: str
    decisions: list[TickerDecision]
    preferred_ticker: str | None = None
    dissent: str
    evidence_limitations: list[str] = Field(default_factory=list)


def clean_committee_text(value: str) -> str:
    """Remove internal research notation from executive-facing committee prose."""
    text = re.sub(r"\[(?:\s*E\d{3}\s*[,;]?\s*)+\]", "", str(value or ""), flags=re.IGNORECASE)
    text = re.sub(r"\b(?:research|evidence) packet\b", "analysis", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:source|evidence) IDs?\b", "supporting information", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+([,.;:])", r"\1", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def _clean_payload_text(value):
    if isinstance(value, dict):
        return {key: _clean_payload_text(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_payload_text(item) for item in value]
    return clean_committee_text(value) if isinstance(value, str) else value


def _research_packet(result: dict, *, max_chars: int = 30000) -> str:
    """Build a bounded, credential-free packet from completed research."""
    from .model_packets import bounded_decision_packet
    return json.dumps(bounded_decision_packet(result,max_chars),ensure_ascii=False,default=str)


def run_investment_committee(result: dict, *, openai_api_key: str, model_name: str,
                             specialist_model: str | None = None,
                             specialist_provider: str = "OpenAI", groq_api_key: str = "",
                             packet_max_chars: int = 30000, ollama_base_url: str | None = None) -> dict:
    """Run a CrewAI committee over saved research without recollecting data."""
    try:
        from crewai import Agent, Crew, LLM, Process, Task
    except ImportError as exc:
        raise RuntimeError(
            "CrewAI is not installed in the Streamlit environment. Install the root project dependencies and restart the app."
        ) from exc

    symbols = list(result.get("request", {}).get("symbols", []))
    if not symbols:
        raise ValueError("The saved research does not contain any ticker symbols.")
    if not openai_api_key:
        raise ValueError("An OpenAI API key is required to run the CrewAI committee.")

    model = model_name if "/" in model_name else f"openai/{model_name}"
    lead_llm = LLM(model=model, api_key=openai_api_key, timeout=90, max_retries=1)
    specialist_name = specialist_model or model_name
    if specialist_provider.lower() == "groq":
        if not groq_api_key:
            raise ValueError("A Groq API key is required for Groq committee specialists.")
        specialist_llm = LLM(model=f"groq/{specialist_name}", api_key=groq_api_key, timeout=90, max_retries=1)
    elif specialist_provider.lower() == "ollama":
        base_options = {"base_url": ollama_base_url.rstrip("/").removesuffix("/v1")} if ollama_base_url else {}
        specialist_llm = LLM(model=f"ollama/{specialist_name}", timeout=90, max_retries=1, **base_options)
    else:
        normalized = specialist_name if "/" in specialist_name else f"openai/{specialist_name}"
        specialist_llm = LLM(model=normalized, api_key=openai_api_key, timeout=90, max_retries=1)
    packet = _research_packet(result, max_chars=packet_max_chars)
    common = (
        "Use only the supplied research packet. Do not browse, call tools, or invent current facts. "
        "Treat missing or stale evidence as uncertainty. Distinguish facts from judgment. Internal evidence IDs may be used "
        "in specialist working notes, but never include them in the final executive decision."
    )

    fundamental_agent = Agent(
        role="Fundamental and Valuation Analyst",
        goal="Assess business quality, financial durability, valuation, and upside for every supplied ticker.",
        backstory="You are a skeptical institutional equity analyst who refuses to fill evidence gaps with assumptions.",
        llm=specialist_llm, verbose=False, allow_delegation=False, max_iter=4, max_execution_time=90,
    )
    risk_agent = Agent(
        role="Risk and Bear-Case Analyst",
        goal="Challenge the investment case, identify downside, and define thesis invalidation signals for every ticker.",
        backstory="You are an independent risk officer rewarded for finding unsupported confidence and asymmetric downside.",
        llm=specialist_llm, verbose=False, allow_delegation=False, max_iter=4, max_execution_time=90,
    )
    lead_agent = Agent(
        role="Lead Portfolio Decision Maker",
        goal="Reconcile the analysts and issue clear BUY, HOLD, or SELL recommendations appropriate to the stated horizon.",
        backstory="You chair an investment committee, preserve meaningful dissent, and calibrate confidence to evidence quality.",
        llm=lead_llm, verbose=False, allow_delegation=False, max_iter=4, max_execution_time=90,
    )

    fundamentals = Task(
        description=f"{common}\nAnalyze fundamentals and valuation for {', '.join(symbols)}.\nRESEARCH PACKET:\n{packet}",
        expected_output="A ticker-by-ticker bull/base assessment with cited evidence, valuation considerations, and unresolved gaps.",
        agent=fundamental_agent,
    )
    risks = Task(
        description=f"{common}\nIndependently develop the bear case and risk controls for {', '.join(symbols)}.\nRESEARCH PACKET:\n{packet}",
        expected_output="A ticker-by-ticker risk assessment with downside drivers, contrary evidence, and observable invalidation signals.",
        agent=risk_agent,
    )
    decision = Task(
        description=(
            f"{common}\nSynthesize the specialist assessments for {', '.join(symbols)}. Return one decision for every ticker. "
            "For multiple tickers, compare them directly and name preferred_ticker only when at least one is rated BUY; "
            "otherwise use null. Apply the same rule for one ticker. Preserve the strongest disagreement in dissent. "
            "A HOLD is appropriate when evidence or risk/reward is inconclusive. Write for an investment-committee executive: "
            "use polished plain English, concise paragraphs and short bullets. Do not mention the research packet, evidence IDs, "
            "source IDs, internal prompts, or agent workflow. Avoid raw metric dumps; explain only the figures material to the decision."
        ),
        expected_output="A structured verdict with recommendations, confidence, reasons, catalysts, risks, and invalidation signals.",
        agent=lead_agent, context=[fundamentals, risks], output_pydantic=CommitteeDecision,
    )
    output = Crew(
        agents=[fundamental_agent, risk_agent, lead_agent], tasks=[fundamentals, risks, decision],
        process=Process.sequential, verbose=False, memory=False,
    ).kickoff()
    parsed = output.pydantic
    if parsed is None:
        raise RuntimeError("CrewAI completed without a structured committee decision.")
    payload = parsed.model_dump(mode="json")
    payload.update({
        "created_at": utc_now(), "model": model_name, "specialist_model": specialist_name,
        "specialist_provider": specialist_provider, "source_research_id": result.get("id"),
        "usage_metrics": json_safe(getattr(output, "token_usage", None) or getattr(output, "usage_metrics", None)),
        "disclaimer": "AI-generated research opinion, not personalized investment advice.",
    })
    return json_safe(_clean_payload_text(payload))
