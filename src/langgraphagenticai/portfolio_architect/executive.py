"""Readable projections of saved advisor evidence; no recollection or rescoring."""
from .screening import METRICS, metric_weights, applicable, sector_lens
from .etf_assessment import assess_etf
from langgraphagenticai.analysis.executive_text import executive_text


def formatted(fact):
    if fact.unit == "fraction":
        return f"{fact.value:.1%}"
    if fact.unit == "multiple":
        return f"{fact.value:.1f}x"
    return f"{fact.value:.2f} {fact.unit}"


def holding_review(result, holding):
    security = next(s for s in result.snapshot.securities if s.ticker == holding.ticker)
    lens = sector_lens(security)
    ai = holding.ai_analysis
    if security.asset == "etf":
        fund = assess_etf(security)
        return dict(framework="ETF allocation", score=None, coverage=None, support=fund["role"],
            concern=fund["risk"], why=executive_text(ai.get("thesis") or fund["conditional_driver"]),
            risk=executive_text((ai.get("risks") or [fund["risk"]])[0]),
            change=executive_text(ai.get("thesis_breaker") or holding.thesis_breakers[0]),
            metrics=[], missing=[fund["valuation_status"]], security=security)
    framework, fields = applicable(security.sector)
    weights = metric_weights(security.sector)
    facts = {f.field:f for f in security.facts if f.field in fields or f.field == "revenue_cagr_3y"}
    peer = next((r for r in result.snapshot.screening.get("ranked", []) if r["symbol"] == holding.ticker), {})
    components = {k:v for k,v in peer.get("components", {}).items() if k in facts and v.get("peer_count",0) >= 3}
    ordered = sorted(components, key=lambda k:(-components[k]["percentile"], -weights.get(k,0), k))
    priorities = sorted(facts, key=lambda k:(-weights.get(k, 1), k))
    def label(field):
        return METRICS[field][1] if field in METRICS else "Revenue CAGR 3Y"
    support = label(ordered[0]) + ": " + formatted(facts[ordered[0]]) + f" (sector percentile {components[ordered[0]]['percentile']:.0%})" if ordered else (
        label(priorities[0]) + ": " + formatted(facts[priorities[0]]) if priorities else "Sector evidence unavailable")
    concern = label(ordered[-1]) + " is the weakest saved relative factor" if ordered else "Sector peer ranking unavailable"
    missing = lens["missing_required"]
    risk = next((v for v in holding.cons if "exceeds" in v or "Nonpositive" in v), None)
    if not risk:
        risk = "Missing sector evidence: " + ", ".join(missing[:3]) if missing else concern
    metrics = []
    for field in priorities:
        fact = facts[field]
        comp = components.get(field)
        metrics.append({"Metric":label(field), "Saved value":formatted(fact),
            "Sector priority":"Growth requirement" if field == "revenue_cagr_3y" and result.mandate.investment_style == "growth" else "Required" if weights.get(field) == 2 else "Preferred" if weights.get(field) == 1 else "Additional",
            "Relative standing":f"{comp['percentile']:.0%} / {comp['peer_count']} peers" if comp else "Not ranked",
            "Basis":fact.basis, "As of":fact.as_of or "Unavailable", "Retrieved":fact.retrieved_at,
            "Source":fact.source, "Evidence ID":fact.id})
    score_fact = next((f for f in security.facts if f.field == "screen_score"), None)
    score = score_fact.value if score_fact else peer.get("score")
    return dict(framework=framework, score=score, coverage=peer.get("coverage"), support=support, concern=concern,
        why=executive_text(ai.get("thesis") or f"Selected using {framework} priorities, your objective and portfolio constraints. {support}."),
        risk=executive_text((ai.get("risks") or [risk])[0]),
        change=executive_text(ai.get("thesis_breaker") or holding.thesis_breakers[0]),
        metrics=metrics, missing=missing, security=security)


def recommendation_rows(result):
    rows=[]
    for holding in result.holdings:
        review=holding_review(result, holding)
        rows.append({"Ticker":holding.ticker, "Allocation %":holding.weight*100,
            "Sector / role":review["framework"], "Sector score / 100":review["score"],
            "Evidence coverage":f"{review['coverage']:.0%}" if review["coverage"] is not None else "Not saved" if holding.asset=="stock" else "Fund framework",
            "Main support":review["support"], "Main concern":review["concern"]})
    return rows
