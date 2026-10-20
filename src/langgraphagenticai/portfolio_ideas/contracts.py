"""Small recommendation contracts; allocations remain local and reproducible."""
import hashlib
import json
import re
from langgraphagenticai.state.research_context import normalize_company_symbol
from langgraphagenticai.utils.safety import redact_sensitive_text

PERSONAS = {
    "Warren": ("Value & quality", "Favor profitability, sensible valuation and durable businesses; do not invent a moat from ratios alone."),
    "George": ("Contrarian opportunities", "Look for valuation/technical/news disagreements. Do not invent macro conditions or claim price moves are caused by headlines."),
    "Ray": ("Diversification & resilience", "Favor sector and business-model diversification with attention to balance-sheet risks. No covariance or calculated risk-parity claim."),
    "Cathie": ("Innovation & growth", "Favor innovative business models and growth potential supported by available evidence. No crypto-only restriction; do not invent growth forecasts."),
}
DEFAULT_UNIVERSE = "AAPL, MSFT, NVDA, AMZN, GOOGL, META, JPM, V, JNJ, UNH, XOM, CAT"
DEFAULT_PROMPT = "Suggest a balanced portfolio of 3–4 companies for a 3–5 year research horizon. Compare business quality, valuation, technical positioning and recent news. Explain the main risk and what would change each view."


def clean(value, credentials=(), limit=600):
    text=str(value or "")
    for key in credentials:
        if key:text=text.replace(key,"[REDACTED]")
    text=redact_sensitive_text(text)
    text=re.sub(r"(?i)\b((?:api[_-]?key|token|password|secret)\s*[:=]\s*)[^\s\"'\\,;<>]+",r"\1[REDACTED]",text)
    return text[:limit]


def universe(text):
    names=list(dict.fromkeys(normalize_company_symbol(s) for s in re.split(r"[,\s]+",text.strip()) if s))
    if not 4<=len(names)<=12:
        raise ValueError("Choose 4–12 unique company tickers.")
    return names


def fingerprint(prompt,names,evidence,model):
    return hashlib.sha256(json.dumps(dict(version=2,prompt=prompt,universe=names,evidence=evidence,model=model),sort_keys=True,allow_nan=False).encode()).hexdigest()


def export(result,credentials=()):
    text=clean(json.dumps(result,allow_nan=False,indent=2),credentials,limit=None)
    if len(text.encode())>2000000:raise ValueError("The saved result exceeds the export budget.")
    return text.encode()
