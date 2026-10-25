from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field, create_model, field_validator, model_validator


class TickerFields(BaseModel):
    @field_validator("best_buy", "runner_up", "preferred_ticker", mode="before", check_fields=False)
    @classmethod
    def normalize_ticker(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


class SpecialistView(TickerFields):
    role: Literal["fundamentals", "valuation", "risk"]
    preferred_ticker: str | None = None
    argument: str
    challenges: list[str] = Field(default_factory=list)


class EquityCommitteeDecision(TickerFields):
    best_buy: str | None = None
    confidence: int = Field(ge=0, le=100)
    verdict: Literal["BUY", "WATCH", "NO_BUY"]
    summary: str
    debate_summary: str
    specialist_views: list[SpecialistView]
    runner_up: str | None = None
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    invalidation_signals: list[str] = Field(default_factory=list)
    evidence_limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_verdict(self):
        if self.verdict == "NO_BUY" and self.best_buy is not None:
            raise ValueError("NO_BUY decisions cannot name a best buy.")
        if self.verdict != "NO_BUY" and self.best_buy is None:
            raise ValueError("BUY and WATCH decisions must name a best buy.")
        return self


def committee_output_schema(symbols: list[str]):
    """Expose exact saved-universe choices to structured generation, including dissent."""
    ticker = Literal[tuple(symbols)]
    specialist = create_model(
        "UniverseSpecialistView", __base__=SpecialistView,
        preferred_ticker=(ticker | None, None),
    )
    return create_model(
        "UniverseEquityCommitteeDecision", __base__=EquityCommitteeDecision,
        best_buy=(ticker | None, None), runner_up=(ticker | None, None),
        specialist_views=(list[specialist], ...),
    )


def _json_value(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    return value if isinstance(value, (str, int, float, bool)) else str(value)


def build_equity_committee_packet(
    scorecard: pd.DataFrame, *, peer_group: str, generated_at: str
) -> dict[str, Any]:
    """Create a bounded, deterministic and credential-free committee input."""
    if scorecard.empty or "Ticker" not in scorecard.columns:
        raise ValueError("The equity scorecard must contain at least one ticker.")
    preferred = [
        "Ticker", "Company Name", "Sector", "Industry", "Final Rank", "Research View",
        "Final Research Score", "Fundamental Score", "Technical Score", "Valuation Score",
        "Growth Score", "Profitability Score", "Balance Sheet Score", "Momentum Score",
        "Best Attribute", "Biggest Weakness", "Valuation Label", "Technical Signal",
        "Price Target Upside", "Price", "Market Cap", "P/E", "Forward P/E", "PEG",
        "EV / EBITDA", "Revenue Growth", "EPS Growth", "Gross Margin", "Operating Margin",
        "Net Margin", "ROE", "ROIC", "Debt / Equity", "Net Debt / EBITDA", "FCF Yield",
        "1Y Return", "RSI", "As Of", "Data Date", "Currency",
    ]
    columns = [column for column in preferred if column in scorecard.columns]
    # Retain the complete decision layer while bounding prompt size.
    if len(columns) < 8:
        columns = list(scorecard.columns[:60])
    frame = scorecard.loc[:, columns].head(12)
    rows = [{str(key): _json_value(value) for key, value in row.items()} for row in frame.to_dict("records")]
    tickers = [str(row.get("Ticker", "")).strip().upper() for row in rows]
    if not all(tickers):
        raise ValueError("Every scorecard row must have a ticker.")
    packet = {
        "peer_group": str(peer_group),
        "generated_at": str(generated_at),
        "tickers": tickers,
        "scorecard": rows,
        "data_policy": "Provider facts and deterministic scores from the saved Equity Report; missing values are null.",
    }
    encoded = json.dumps(packet, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    packet["fingerprint"] = hashlib.sha256(encoded).hexdigest()[:16]
    return packet


def run_equity_committee(
    packet: dict[str, Any], *, openai_api_key: str, model_name: str
) -> dict[str, Any]:
    """Run a bounded CrewAI debate over a saved Equity Report scorecard."""
    if not openai_api_key:
        raise ValueError("An OpenAI API key is required to run the CrewAI debate.")
    symbols = [str(value).strip().upper() for value in packet.get("tickers", [])]
    if not symbols:
        raise ValueError("The committee packet does not contain any tickers.")
    try:
        from crewai import Agent, Crew, LLM, Process, Task
    except ImportError as exc:
        raise RuntimeError("CrewAI is not installed. Install the root project dependencies and restart the app.") from exc

    model = model_name if "/" in model_name else f"openai/{model_name}"
    reasoning_model = model.rsplit("/", 1)[-1].lower().startswith("gpt-5")
    # The installed native CrewAI chat adapter omits GPT-5 reasoning_effort.
    # Its Responses adapter carries the bounded reasoning/output configuration.
    llm = LLM(model=model, api_key=openai_api_key, timeout=60, max_retries=0, max_completion_tokens=4000,
              **({"api":"responses", "store":False, "reasoning_effort":"low"} if reasoning_model else {}))
    evidence = json.dumps(packet, ensure_ascii=False, default=str)
    guardrails = (
        "Use only the supplied Equity Report packet. Do not browse, call tools, or invent facts. "
        "Null means unavailable, zero is a real value, and unlike currencies or periods must not be compared. "
        "Challenge deterministic rankings when the underlying evidence is incomplete. This is research, not personalized advice. Keep each specialist response under 180 words; final decision under 500 words. "
        "Use concise executive English with no source IDs, citations, provider attribution or workflow jargon."
    )

    def agent(role: str, goal: str, backstory: str) -> Any:
        return Agent(
            role=role, goal=goal, backstory=backstory, llm=llm, verbose=False,
            allow_delegation=False, max_iter=2, max_execution_time=180, max_retry_limit=0,
        )

    fundamental = agent(
        "Fundamental Quality Analyst",
        "Rank the supplied companies on durable growth, profitability, cash generation, and balance-sheet quality.",
        "You are a long-horizon analyst who penalizes weak coverage and refuses to confuse growth with quality.",
    )
    valuation = agent(
        "Valuation and Expectations Analyst",
        "Determine which company offers the strongest risk-adjusted upside relative to embedded expectations.",
        "You are a valuation specialist who challenges attractive stories when the price already discounts perfection.",
    )
    risk = agent(
        "Bear-Case and Risk Officer",
        "Cross-examine the bullish cases, expose missing evidence, and identify thesis-breaking signals.",
        "You are an independent risk officer rewarded for dissent and calibrated uncertainty.",
    )
    chair = agent(
        "Investment Committee Chair",
        "Adjudicate the debate and select at most one best buy, or explicitly conclude that none qualifies.",
        "You are a disciplined portfolio manager who preserves dissent and favors evidence over consensus.",
    )

    fundamentals = Task(
        description=f"{guardrails}\nDevelop the fundamental case for every ticker.\nEQUITY REPORT PACKET:\n{evidence}",
        expected_output="A comparative fundamental ranking, strongest evidence, gaps, and the analyst's preferred ticker.",
        agent=fundamental,
    )
    valuation_case = Task(
        description=f"{guardrails}\nIndependently compare valuation, expectations, and upside for every ticker.\nEQUITY REPORT PACKET:\n{evidence}",
        expected_output="A valuation-led ranking, key assumptions, contrary signals, and the analyst's preferred ticker.",
        agent=valuation,
    )
    rebuttal = Task(
        description=(
            f"{guardrails}\nCross-examine both specialist cases. Identify where they agree, where they conflict, "
            f"and why the apparent winner could fail.\nEQUITY REPORT PACKET:\n{evidence}"
        ),
        expected_output="A red-team rebuttal with downside cases, disputed claims, evidence gaps, and invalidation tests.",
        agent=risk, context=[fundamentals, valuation_case],
    )
    final = Task(
        description=(
            f"{guardrails}\nAdjudicate the debate for this exact universe: {', '.join(symbols)}. "
            "Use only exact ticker strings from this universe in best_buy, runner_up and preferred_ticker; never company names, explanations or lists. Return specialist views for fundamentals, valuation, and risk. Select no more than one best_buy. "
            "Use NO_BUY with null best_buy when evidence or risk/reward is inadequate. A WATCH names the strongest "
            "candidate but states why it is not yet a buy. Explain the disagreements and decisive reasoning in plain English."
        ),
        expected_output="A structured best-buy verdict, debate summary, specialist views, risks, catalysts, and invalidation signals.",
        agent=chair, context=[fundamentals, valuation_case, rebuttal], output_pydantic=committee_output_schema(symbols),
    )
    crew = Crew(
        agents=[fundamental, valuation, risk, chair],
        tasks=[fundamentals, valuation_case, rebuttal, final],
        process=Process.sequential, verbose=False, memory=False, cache=False,
    )
    try:
        output = crew.kickoff()
    except Exception as exc:
        # CrewAI timeout messages embed the entire task and saved packet. Never
        # propagate those messages into the UI or external exception chains.
        if isinstance(exc, TimeoutError) or "timed out" in str(exc).lower():
            raise RuntimeError("A committee analyst exceeded its time budget. The saved Equity Report is unchanged. Retry the debate or select a faster model; no automatic retry was made.") from None
        raise RuntimeError("The committee could not return a complete decision. The saved Equity Report is unchanged. Check model access and try the debate again.") from None
    parsed = output.pydantic
    if parsed is None:
        raise RuntimeError("CrewAI completed without a structured best-buy decision.")
    decision = parsed.model_dump(mode="json")
    allowed = set(symbols)
    for field in ("best_buy", "runner_up"):
        value = decision.get(field)
        if value is not None:
            value = str(value).strip().upper()
            if value not in allowed:
                raise ValueError(f"CrewAI returned an out-of-universe {field}.")
            decision[field] = value
    for view in decision.get("specialist_views", []):
        value = view.get("preferred_ticker")
        if value is not None and str(value).strip().upper() not in allowed:
            raise ValueError("CrewAI returned an out-of-universe specialist preference.")
        if value is not None:
            view["preferred_ticker"] = str(value).strip().upper()
    decision.update({
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model_name,
        "input_fingerprint": packet.get("fingerprint"),
        "disclaimer": "AI-generated comparative research opinion, not personalized investment advice.",
    })
    return decision
