"""Explicit, editable interpretation. Defaults never establish personal suitability."""
import re
from .schemas import InvestorMandate
from .universe import THEMES
from langgraphagenticai.utils.safety import redact_sensitive_text


def infer_style(prompt):
    text = str(prompt)
    return "growth" if re.search(r"\bgrowth\b",text,re.I) and not re.search(r"\b(?:not|avoid|no)\s+(?:a\s+)?growth\b",text,re.I) else "balanced"


def default_mandate(prompt):
    prompt = redact_sensitive_text(str(prompt)).strip()
    risk = next((v for v in ("conservative", "moderate", "aggressive") if v in prompt.lower()), "moderate")
    years = re.search(r"\b(1|3|5|10)[ -]year", prompt.lower())
    horizon = int(years[1]) if years else 5
    mandate = InvestorMandate(objective=prompt, risk=risk, horizon=horizon,
                               investment_style=infer_style(prompt),
                               themes=[t for t in THEMES if re.search(r"\b"+re.escape(t)+r"\b", prompt, re.I)])
    return mandate, ["Local interpretation: explicit growth/balanced style, risk, numeric year horizon and curated theme keywords are extracted. "
                     "Other prompt constraints are not enforced until you enter them in the mandate editor. "
                     "Defaults: moderate risk, five years, ten holdings, ten percent cash, hypothetical USD account."]


def interpret(prompt, api_key="", model="", use_ai=False):
    local, notes = default_mandate(prompt)
    if not use_ai:
        return local, notes, None
    from .committee import structured_call
    value, usage = structured_call(InvestorMandate, {"objective": local.objective, "defaults": local.model_dump()},
                                  api_key, model, "Interpret explicit investor constraints; do not infer personal suitability. "
                                  "Use defaults for absent fields. Preserve explicit growth style as investment_style=growth. Contradictions must fail server validation. Themes are preferences, not guarantees.", 1800)
    if local.investment_style == "growth":
        value = value.model_copy(update={"investment_style":"growth", "themes":sorted(set(value.themes)|set(local.themes))})
    return value, ["AI interpretation; review every constraint before Build. No personal suitability assessment."], usage
