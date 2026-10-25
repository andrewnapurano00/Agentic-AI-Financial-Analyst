"""Concise saved holding narrative, shared by screen and PDF."""
from langgraphagenticai.analysis.executive_text import executive_text


def holding_narrative(holding):
    def field(key, default=None):
        return holding.get(key,default) if isinstance(holding,dict) else getattr(holding,key,default)
    ai=field("ai_analysis",{}) or {}
    # Operational eligibility is not an investment thesis. Preserve meaningful
    # financial pros without making up a narrative when no AI review was saved.
    pros=[p for p in field("pros",[]) if not any(t in p.lower() for t in ("quote available","explicit research universe","source id","evidence id"))]
    fallback="; ".join(pros) or "Selected by the saved sector-relative ranking and allocation constraints."
    return {"reason":executive_text(ai.get("conviction_summary") or ai.get("portfolio_role") or fallback),
            "thesis":executive_text(ai.get("thesis") or fallback),
            "role":executive_text(ai.get("portfolio_role") or field("sizing",""))}
