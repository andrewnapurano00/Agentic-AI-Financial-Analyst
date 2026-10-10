"""D01-D06/D09: conservative immutable adapter for saved earnings sensitivities."""
from dataclasses import dataclass
from datetime import datetime, date, timezone
import math
import re
from langgraphagenticai.deep_research.quarterly_ttm import METHODOLOGY, number
from langgraphagenticai.deep_research.sector import map_sector_to_framework, SECTOR_METRIC_REGISTRY, GENERAL_FRAMEWORK
from langgraphagenticai.deep_research.research_metrics import ALIASES

LIMITATIONS = (
    "Standardized flows assume standalone quarters where duration is absent; raw reported monetary scaling is unverified and is not changed.",
    "Saved quote Unix timestamps are interpreted as seconds in UTC, an existing disclosed assumption.",
    "Quote freshness policy: at most seven UTC calendar days at the supplied reference; future instants are rejected.",
    "Hypothetical total equity values are user sensitivities, not forecasts, returns, recommendations or per-share targets.",
)

@dataclass(frozen=True)
class SavedInputs:
    ticker: str
    eligible: bool
    reasons: tuple[str, ...]
    net_income: float | None = None
    market_cap: float | None = None
    currency: str = ""
    ttm_through: str = ""
    quote_as_of: str = ""
    reference_time: str = ""
    framework: str = ""
    provenance: tuple = ()
    quarters: tuple = ()
    limitations: tuple = LIMITATIONS

def _instant(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timezone is required")
    return parsed.astimezone(timezone.utc)

def saved_inputs(result, ticker, reference_time):
    """Malformed/legacy saved packets stay readable but cannot grant eligibility."""
    try:
        return _saved_inputs(result, ticker, reference_time)
    except (AttributeError, TypeError, KeyError, ValueError, IndexError, OverflowError):
        return SavedInputs(str(ticker).strip().upper(), False, ("Malformed or incomplete saved audit packet.",))

def _saved_inputs(result, ticker, reference_time):
    """Read actual saved contracts and their sources, never reaggregate earnings."""
    ticker = str(ticker).strip().upper()
    reasons = []
    try:
        reference = _instant(reference_time)
    except (TypeError, ValueError, OverflowError):
        return SavedInputs(ticker, False, ("Invalid explicit UTC freshness reference.",))
    reference_text = reference.isoformat()
    def unavailable(message):
        return SavedInputs(ticker, False, tuple(reasons + [message]), reference_time=reference_text)
    if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.\-^=]{0,14}", ticker):
        return unavailable("Invalid security identity.")
    if ticker not in [str(s).strip().upper() for s in result.get("request", {}).get("symbols", [])]:
        return unavailable("Security is not part of the saved research request.")
    rows = [r for r in result.get("comparison", []) if str(r.get("Ticker", "")).strip().upper() == ticker]
    if len(rows) != 1:
        return unavailable("One unique saved company comparison is required.")
    row = rows[0]
    framework = map_sector_to_framework(row.get("Sector"), row.get("Industry"))
    avoided = {ALIASES.get(k, k) for k in SECTOR_METRIC_REGISTRY[framework]["avoid_or_downweight"]}
    if framework == GENERAL_FRAMEWORK or "P/E (TTM)" in avoided:
        return unavailable("Earnings-multiple model unavailable for this unknown or inapplicable sector.")
    evidence = result.get("evidence", [])
    if not all(isinstance(e, dict) for e in evidence):
        return unavailable("Saved evidence must contain records.")
    ids = [e.get("id") for e in evidence]
    if len(ids) != len(set(ids)) or any(not i for i in ids):
        return unavailable("Duplicate or missing saved evidence IDs.")
    sources = {e["id"]: e for e in evidence}
    contracts = row.get("Metric contracts") or {}
    validated = []
    for key, category, field in (("Net income (TTM)", "income_ttm", "netIncome"), ("Market cap", "quote", "marketCap")):
        c = contracts.get(key) or {}
        value = number(row.get(key))
        if (value is None or value <= 0 or number(c.get("value")) != value or c.get("status") != "ok"
                or c.get("unit") != "currency" or c.get("methodology") != METHODOLOGY
                or c.get("applicability") != "applicable" or not c.get("formula") or not c.get("currency")):
            return unavailable(key + ": positive finite audited currency contract is required.")
        inputs = c.get("inputs") or []
        if len(inputs) != 1 or not isinstance(inputs[0], dict):
            return unavailable(key + ": one resolvable source input is required.")
        inp = inputs[0]; source = sources.get(inp.get("source_id"), {})
        data = source.get("data")
        records = data if isinstance(data, list) else [data]
        if len(records) != 1 or not isinstance(records[0], dict):
            return unavailable(key + ": unique saved source record is required.")
        raw = records[0]
        currency = raw.get("reportedCurrency") or raw.get("currency")
        if (source.get("status") != "ok" or source.get("category") != category or inp.get("category") != category
                or inp.get("field") != field or str(source.get("symbol", "")).upper() != ticker
                or str(raw.get("symbol", "")).upper() != ticker or number(raw.get(field)) != value
                or number(inp.get("value")) != value or not currency or currency != c.get("currency")
                or currency != inp.get("currency") or inp.get("currency_basis") != "Source-reported currency"
                or not source.get("provider") or inp.get("provider") != source.get("provider")
                or not source.get("retrieved_at") or inp.get("retrieved_at") != source.get("retrieved_at")):
            return unavailable(key + ": source identity/value/currency/provenance is missing or inconsistent; inferred currency is unverified.")
        validated.append((value, c, inp, source, raw, currency))
    ni, nc, nip, nis, income, currency = validated[0]
    cap, cc, cip, caps, quote, quote_currency = validated[1]
    if currency != quote_currency:
        return unavailable("Statement and quote currencies differ.")
    quarters = income.get("quarters")
    if not isinstance(quarters, list) or len(quarters) != 4 or nc.get("basis") != quarters or row.get("TTM fiscal quarters") != quarters:
        return unavailable("Four matching audited fiscal quarters are required.")
    try:
        keys = [int(q["fiscalYear"]) * 4 + int(q["period"][1]) for q in quarters if q["period"] in {"Q1", "Q2", "Q3", "Q4"}]
        days = [date.fromisoformat(q["date"]) for q in quarters]
        if len(keys) != 4 or any(a-b != 1 for a,b in zip(keys, keys[1:])) or any(not 60 <= (a-b).days <= 120 for a,b in zip(days,days[1:])):
            raise ValueError("Nonconsecutive quarters")
        if any(d > reference.date() or abs(d.year-int(q["fiscalYear"])) > 1 for d,q in zip(days,quarters)):
            raise ValueError("Invalid fiscal dates")
    except (KeyError, TypeError, ValueError, IndexError):
        return unavailable("Invalid, duplicate or nonconsecutive fiscal quarter identities/dates.")
    if (income.get("period") != "TTM" or income.get("methodology") != METHODOLOGY or not income.get("units")
            or not income.get("duration_assumption") or not income.get("formula")
            or income.get("date") != quarters[0]["date"] or nip.get("date") != income.get("date")
            or row.get("TTM through") != income.get("date") or row.get("TTM currency") != currency):
        return unavailable("Saved TTM basis/methodology/date is inconsistent or incomplete.")
    try:
        epoch = number(quote.get("timestamp"))
        if epoch is None:
            raise ValueError("Missing quote timestamp")
        as_of = datetime.fromtimestamp(epoch, timezone.utc)
        contract_time = _instant(cip.get("date"))
        row_time = _instant(row.get("Quote as of"))
        # Existing saved contracts retain second precision.
        if as_of > reference:
            raise ValueError("Future quote instant")
        as_of = as_of.replace(microsecond=0)
        if as_of != contract_time or as_of != row_time or as_of > reference or (reference.date()-as_of.date()).days > 7:
            raise ValueError("Stale/future/mismatched quote")
    except (ValueError, TypeError, OverflowError, OSError):
        return unavailable("Quote as-of is unknown, malformed, inconsistent, future or older than seven UTC calendar days.")
    provenance = tuple((key, inp["source_id"], source["provider"], source["retrieved_at"], inp["date"], c["formula"])
        for key, (_,c,inp,source,raw,cur) in zip(("Calculated audited TTM net income", "Provider market capitalization"), validated))
    return SavedInputs(ticker, True, (), ni, cap, currency, income["date"], as_of.isoformat(), reference_text,
                       framework, provenance, tuple((q["date"], str(q["fiscalYear"]), q["period"]) for q in quarters))

def calculate(inputs, earnings_change_percent, pe):
    change, multiple = number(earnings_change_percent), number(pe)
    if not inputs.eligible:
        raise ValueError("Saved inputs are unavailable.")
    if change is None or multiple is None or not -100 <= change <= 200 or not 0 < multiple <= 100:
        raise ValueError("Earnings change must be -100% to +200%; P/E must be above zero and at most 100.")
    value = inputs.net_income * (1 + change / 100) * multiple
    difference = value / inputs.market_cap - 1
    if not math.isfinite(value) or not math.isfinite(difference) or not math.isfinite(difference*100):
        raise ValueError("Hypothetical arithmetic overflowed.")
    return dict(earnings_change_percent=change, pe=multiple, hypothetical_total_equity_value=value,
                difference_vs_saved_cap_percent=difference*100)
