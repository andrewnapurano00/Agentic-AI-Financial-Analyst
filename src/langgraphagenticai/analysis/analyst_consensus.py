"""Three-category analyst rating arithmetic, retaining zero versus missing."""
from math import isfinite

FIELDS = ("strongBuy", "buy", "hold", "sell", "strongSell")
CATEGORIES = ("Buy", "Hold", "Sell")


def consensus_distribution(payload, symbol):
    if not isinstance(payload, list):
        raise ValueError("Analyst consensus response is unavailable or malformed.")
    matches = [r for r in payload if isinstance(r, dict) and r.get("symbol") == symbol]
    normalized = []
    for row in matches:
        counts = {}
        for field in FIELDS:
            value = row.get(field)
            if value is None or isinstance(value, bool):
                raise ValueError("Analyst rating counts are incomplete.")
            try:
                numeric = float(value)
            except (TypeError, ValueError, OverflowError):
                raise ValueError("Analyst rating counts are invalid.") from None
            if not isfinite(numeric) or numeric < 0 or not numeric.is_integer():
                raise ValueError("Analyst rating counts must be finite, nonnegative whole numbers.")
            counts[field] = int(numeric)
        if counts not in normalized:
            normalized.append(counts)
    if len(normalized) != 1:
        raise ValueError("No unique analyst consensus record matches the selected stock.")
    raw = normalized[0]
    counts = {"Buy":raw["strongBuy"]+raw["buy"], "Hold":raw["hold"], "Sell":raw["sell"]+raw["strongSell"]}
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("No analyst ratings are available for this stock.")
    rows = [{"category":key,"count":counts[key],"percent":100*counts[key]/total} for key in CATEGORIES]
    maximum = max(counts.values())
    leaders = [key for key in CATEGORIES if counts[key] == maximum]
    return {"symbol":symbol,"total":total,"categories":rows,"leading_category":leaders[0] if len(leaders)==1 else None,
            "raw_counts":raw,"as_of":None}
