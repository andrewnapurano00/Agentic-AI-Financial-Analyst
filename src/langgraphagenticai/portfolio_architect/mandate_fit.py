"""Explicit objective fit from saved evidence, not future-return predictions."""
import re


AI_BUSINESS_TERMS = re.compile(r"\bartificial intelligence\b|\bmachine learning\b|\bAI\b|\bsemiconductors?\b|\bdata[ -]cent(?:er|re)s?\b|\baccelerated computing\b", re.I)
AI_SECTOR_PROXIES = {"Technology / Software / Semis", "Communication Services", "Industrials"}


def theme_fit(security, mandate):
    if "AI" in mandate.themes and AI_BUSINESS_TERMS.search(security.business_summary):
        return 1., "Saved issuer description mentions AI, semiconductors or data-center activity; AI revenue exposure is unquantified."
    if set(security.themes)&set(mandate.themes):
        return .5, "Curated theme metadata matches; current theme revenue exposure is unverified."
    return 0., "No supported requested-theme match in saved business description or curated metadata."


def growth_fit(security, mandate):
    """Return eligibility, priority and explanation; never manufacture missing growth."""
    if mandate.investment_style != "growth":
        return True, None, "Balanced style; growth is not an eligibility requirement."
    if security.asset == "etf":
        eligible = "growth" in security.themes or "AI" in security.themes or "broad equity" in security.sector.lower()
        return eligible, 0.5 if eligible else 0., "Curated equity/growth fund classification; underlying growth and holdings are unmeasured."
    fact = next((f for f in security.facts if f.field == "revenue_cagr_3y"), None)
    if fact is None or fact.value <= 0:
        return False, None, "Growth mandate requires positive comparable three-year annual revenue CAGR; unavailable/nonpositive growth is not inferred."
    return True, min(fact.value/.30, 1.), f"Positive saved annual revenue CAGR [{fact.id}]; historical growth, not a forecast."


def mandate_priority(security, mandate, quality):
    eligible, growth, explanation = growth_fit(security, mandate)
    relevance, theme_reason = theme_fit(security, mandate)
    if mandate.investment_style == "growth":
        # Fixed transparent priority weights: a high value/quality score alone cannot dominate an AI mandate.
        score = (45*relevance+35*(growth or 0)+20*quality) if mandate.themes else (65*(growth or 0)+35*quality)
    else:
        score = 100*quality+5*relevance
    return eligible, score, {"style":mandate.investment_style, "growth_priority":growth, "theme_relevance":relevance,
                             "growth_basis":explanation, "theme_basis":theme_reason,
                             "policy":"Objective-fit ranking is a disclosed research heuristic, not expected return or quantified theme exposure."}
