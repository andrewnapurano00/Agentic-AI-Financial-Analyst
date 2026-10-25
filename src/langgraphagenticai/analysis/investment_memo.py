"""Presentation-only projections of saved research. No collection or inference."""
from dataclasses import dataclass
import json
import math
import re
from urllib.parse import quote, urlsplit, urlunsplit

from langgraphagenticai.utils.safety import redact_sensitive_text


def clean(value, credentials=()):
    """Retain complete selected records, finite numbers and safe public destinations."""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if isinstance(value, dict):
        return {clean(str(k), credentials): clean(v, credentials) for k, v in value.items()
                if not re.search(r"api.?key|password|secret|token|prompt|authorization", str(k), re.I)}
    if isinstance(value, (list, tuple)):
        return [clean(v, credentials) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (int, float, bool)):
        return value
    text = str(value)
    for secret in credentials:
        if secret:
            for form in (secret, quote(secret, safe=""), json.dumps(secret)[1:-1]):
                text = text.replace(form, "[REDACTED]")
    def public_url(match):
        try:
            parts = urlsplit(match.group())
            if parts.scheme.lower() not in {"https", "http"} or not parts.hostname or parts.username:
                return "[unsafe URL removed]"
            return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        except ValueError:
            return "[unsafe URL removed]"
    text = re.sub(r"(?:https?://|javascript:|data:|file://)[^\s<>\"']+", public_url, text, flags=re.I)
    return redact_sensitive_text(text)


def excerpt(text, limit=450):
    text = re.sub(r"(?m)^\s*#{1,6}\s+", "", str(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …"


@dataclass(frozen=True)
class InvestmentMemo:
    title: str
    lineage: str
    thesis: str
    sections: tuple[tuple[str, str], ...]
    appendices: tuple[tuple[str, str], ...]


def research_memo(result, credentials=()):
    saved = clean(result, credentials)
    report = str(saved.get("report") or saved.get("draft") or "No saved narrative available.")
    blocks = re.split(r"(?m)^(?=#{1,6}\s)", report)
    def section(pattern):
        return excerpt("\n".join(b for b in blocks if re.search(pattern, b.split("\n", 1)[0], re.I)), 280) or "Not separately stated in the saved narrative."
    evidence = saved.get("evidence") or []
    highlights = f"{len(evidence)} retained source records. No eligible numerical highlight; consult the full source appendix. Current freshness is not reassessed."
    # Reuse the existing bounded numerical audits at a saved collection reference.
    # This is deliberately separate from AX-06's current-time freshness display.
    from .claim_verification import saved_facts
    from .earnings_metrics import instant
    references_at = []
    for record in evidence:
        try:
            references_at.append(instant(record.get("retrieved_at")))
        except (ValueError, TypeError, AttributeError):
            continue
    if references_at:
        facts, _ = saved_facts(saved, max(references_at).isoformat())
        eligible = [f for f in facts if f.status == "available" and f.value is not None]
        rows = [f"{f.ticker} {f.metric} {f.value:g} {f.currency} ({f.basis}, {f.period_end}; {','.join(f.citations)}; {f.sources[0].get('provider', 'unknown')})" for f in eligible[:2] if f.sources]
        if rows:
            highlights = "; ".join(rows) + ". Checked at saved collection reference; current freshness unassessed. Retrieval dates in source appendix."
    references = json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    decisions = {k: saved[k] for k in ("crewai_decision", "quick_decision") if saved.get(k)}
    details = {k: v for k, v in saved.items() if k not in {"report", "draft", "evidence", "crewai_decision", "quick_decision"}}
    return InvestmentMemo(
        excerpt(saved.get("request", {}).get("question") or saved.get("question") or saved.get("query") or "Executive investment memo", 110),
        "Saved research · " + str(saved.get("status", "status unavailable")),
        excerpt(report, 550),
        (("Evidence highlights", excerpt(highlights, 380)),
         ("Valuation implications", section(r"valuation|pricing|target")),
         ("Upside / downside drivers", section(r"driver|catalyst|bull|bear|competing")),
         ("Material risks", section(r"risk|invalidation|downside")),
         ("Quality / gaps", "Saved AI interpretation; this memo does not verify narrative claims. " + str(saved.get("status", "unknown")) + ". Missing or stale evidence remains unresolved."),
         ("Assumptions", section(r"assumption|limitation|missing|uncertainty"))),
        (("Full retained narrative · saved AI interpretation", report),
         ("Retained draft / original before continuation", str(saved.get("draft") or "No separate saved draft.")),
         ("Saved committee and quick decisions · AI opinion", json.dumps(decisions, ensure_ascii=False, indent=2, sort_keys=True)),
         ("Complete saved details", json.dumps(details, ensure_ascii=False, indent=2, sort_keys=True)),
         ("Complete source references and evidence", references)))


def portfolio_memo(result, credentials=()):
    """A concise decision memo, never a dump of the research universe/history."""
    from langgraphagenticai.analysis.executive_text import executive_text
    from langgraphagenticai.analysis.portfolio_summary import holding_narrative
    def field(obj, key, default=None):
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)
    def text(value, limit=700):
        return excerpt(executive_text(clean(value, credentials)), limit).replace(" | "," / ")
    positions=field(result,"holdings",[])
    snapshot=field(result,"snapshot",{})
    risk=field(result,"risk",{})
    if hasattr(risk,"model_dump"):
        risk=risk.model_dump(mode="json")
    mandate=field(result,"mandate",{})
    rows=[]; details=[]
    for holding in positions[:40]:
        ticker=text(field(holding,"ticker",""),30)
        name=text(field(holding,"name",""),120)
        weight=field(holding,"weight",0)
        ai=field(holding,"ai_analysis",{}) or {}
        narrative=holding_narrative(holding)
        reason=text(narrative["reason"],180)
        thesis=text(narrative["thesis"],850)
        risks=text("; ".join(ai.get("risks") or field(holding,"cons",[])),350)
        rows.append(f"{ticker} | {name} | {weight:.2%} | {reason}")
        details.append((f"{ticker} - {name} ({weight:.2%})", thesis+"\nPortfolio role: "+text(ai.get("portfolio_role") or field(holding,"sizing",""),300)+"\nKey risk: "+risks))
    cash=field(result,"cash",0)
    rows.append(f"CASH | Cash | {cash:.2%} | Liquidity / allocation residual")
    def percent(value):
        return f"{value:.1%}" if isinstance(value,(int,float)) and math.isfinite(value) else "unavailable"
    historical=(f"Annualized volatility {percent(risk.get('annualized_volatility'))}; max drawdown {percent(risk.get('max_drawdown'))}. "
                f"{risk.get('start')} to {risk.get('end')}; {risk.get('observations')} observations. "
                f"Benchmark {field(mandate,'benchmark','unknown')}.") if risk.get("status")=="available" else "Historical risk unavailable."
    return InvestmentMemo("Portfolio investment memo", "Saved portfolio - "+text(field(snapshot,"mode","unknown"),60)+" - retrieved "+text(field(snapshot,"retrieved_at","unknown"),60),
        text("; ".join(f"{field(h,'ticker','')} {field(h,'weight',0):.2%}" for h in positions)+f"; Cash {cash:.2%}",550),
        (("Allocation - ticker | name | weight | reason", "\n".join(rows)),
         ("Eligible historical risk",text(historical,500)),
         ("Material risks",text("; ".join(field(result,"warnings",[])),600) or "Review the holding-specific risks below."),
         ("Assumptions","Hypothetical allocation; historical risk does not predict future losses. ETF look-through exposure may be unavailable. "+text(risk.get("convention",""),450))),
        tuple(details))
