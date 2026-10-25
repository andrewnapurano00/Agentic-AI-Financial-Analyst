"""AX-04 earnings adapter: pure raw-statement validation and saved-value reconciliation."""
from dataclasses import replace
from datetime import datetime, timezone, date
import math
import re
from urllib.parse import urlsplit, urlunsplit

from .metric_contracts import DEFINITIONS, MetricInput, MetricObservation
from langgraphagenticai.deep_research.quarterly_ttm import window, flow_duration, number, METHODOLOGY
from langgraphagenticai.utils.safety import redact_sensitive_text

ASSUMPTIONS = (
    "Standardized flows assume standalone quarters when duration metadata is absent; explicit YTD/unknown duration is rejected.",
    "Provider monetary scaling is not independently certified and is not changed.",
    "Fiscal period end is not filing availability; unknown filing/acceptance timezone remains unknown.",
    "Total company net income is not reported diluted EPS, FFO/AFFO or normalized future earnings.",
    "Corporate-event comparability is not inferred; stock splits do not rescale total company earnings.",
)


def instant(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Explicit timezone-aware reference/retrieval time is required")
    return parsed.astimezone(timezone.utc)


def safe_route(value):
    try:
        parts = urlsplit(str(value or ""))
        if parts.scheme not in {"https", "http"} or not parts.hostname or parts.username or parts.password:
            return ""
        parts.port
        if re.search(r"[\s\\\x00-\x1f]", parts.netloc):
            return ""
        return redact_sensitive_text(urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")))
    except ValueError:
        return ""


def observe_net_income(rows, ticker, *, basis, source_id, provider, route, retrieved_at, reference_time):
    """Build a new observation; never mutate rows or infer an annual/TTM substitute."""
    definition = DEFINITIONS["net_income." + ("ttm" if basis == "TTM" else basis)]
    ticker = redact_sensitive_text(ticker).strip().upper()
    obs = MetricObservation(definition.id, ticker, None, None, definition.basis, "missing",
        "derived" if basis == "TTM" else "provider", "unverifiable", None, redact_sensitive_text(reference_time), assumptions=ASSUMPTIONS)
    try:
        try:
            reference = instant(reference_time)
        except (ValueError, TypeError, OverflowError):
            return obs.flagged("unverifiable", "Reference instant is unknown or lacks a timezone")
        obs = replace(obs, evaluated_at=reference.isoformat())
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,14}", ticker):
            return replace(obs, ticker="[invalid]").flagged("unsupported", "Unsupported company security identity")
        if not isinstance(rows, list) or not rows:
            return obs.flagged("missing", "No raw reported earnings records")
        if any(not isinstance(r, dict) for r in rows):
            return obs.flagged("unverifiable", "Statement records must be objects")
        if any(r.get("symbol") != ticker for r in rows):
            return obs.flagged("inconsistent", "Statement security identity is missing or mismatched")
        if any(not re.fullmatch(r"[A-Z]{3}", str(r.get("reportedCurrency") or "")) for r in rows):
            return obs.flagged("unverifiable", "Explicit supported reporting currency is required; quote/profile currency is not a substitute")
        if any(r.get("scale", 1) != 1 or r.get("unitScale", 1) != 1 for r in rows):
            return obs.flagged("unverifiable", "Unsupported monetary scaling; no automatic rescaling")
        if basis in {"quarterly", "TTM"}:
            selected = window(rows, ticker, count=4 if basis == "TTM" else 1)
        else:
            by_year = {}
            for row in rows:
                if str(row.get("period")).upper() not in {"FY", "ANNUAL"}:
                    raise ValueError("Annual observations require reported fiscal-year records")
                valid, reason = flow_duration(row)
                if not valid:
                    raise ValueError(reason)
                year = int(row["fiscalYear"])
                end = date.fromisoformat(row["date"])
                if not 1900 <= year <= 2200 or abs(end.year - year) > 1 or end > reference.date():
                    raise ValueError("Invalid annual fiscal identity/date")
                if year in by_year and row != by_year[year]:
                    raise ValueError("Ambiguous annual revision; no automatic restatement selection")
                by_year[year] = row
            selected = [by_year[max(by_year)]]
        if any(date.fromisoformat(r["date"]) > reference.date() for r in selected):
            raise ValueError("Fiscal period end is later than the supplied reference")
        currency = selected[0]["reportedCurrency"]
        if any(r["reportedCurrency"] != currency for r in selected):
            raise ValueError("Mixed reporting currencies")
        for row in selected:
            for key in ("unit", "units"):
                if str(row.get(key) or "").strip().lower() not in {"", "currency", "currency units", "reported currency units", currency.lower()}:
                    return obs.flagged("unverifiable", "Explicit monetary units/scaling are unsupported; values were not rescaled")
        security_ids = {str(r["cik"]).lstrip("0") for r in selected if r.get("cik")}
        if len(security_ids) > 1:
            raise ValueError("Reported security identifiers differ within the earnings window")
        values = [number(r.get("netIncome")) for r in selected]
        end = selected[0]["date"]
        inputs = tuple(MetricInput(redact_sensitive_text(source_id), redact_sensitive_text(provider), safe_route(route),
            "netIncome", v, r["reportedCurrency"], int(r["fiscalYear"]), str(r["period"]), r["date"],
            redact_sensitive_text(retrieved_at), redact_sensitive_text(r["filingDate"]) if r.get("filingDate") else None,
            redact_sensitive_text(r["acceptedDate"]) if r.get("acceptedDate") else None,
            security_id=redact_sensitive_text(r["cik"]) if r.get("cik") else None) for r, v in zip(selected, values))
        value = sum(values) if all(v is not None for v in values) else None
        if value is not None and not math.isfinite(value):
            raise ValueError("Earnings aggregation is nonfinite")
        obs = replace(obs, value=value, currency=currency, as_of=end, inputs=inputs,
                      verification="reconciled" if basis == "TTM" else "structural")
        if value is None:
            return obs.flagged("missing", "A reported net-income component is missing/nonfinite; it is not zero")
        if not provider or not source_id or not safe_route(route):
            return obs.flagged("unverifiable", "Source identity/provider/route is unavailable")
        try:
            retrieval = instant(retrieved_at)
        except (ValueError, TypeError, OverflowError):
            return obs.flagged("unverifiable", "Source retrieval instant is unknown or has no timezone")
        if retrieval > reference:
            return obs.flagged("inconsistent", "Source retrieval is later than the supplied reference")
        for row in selected:
            if date.fromisoformat(row["date"]) > retrieval.date():
                raise ValueError("Financial period ends after the source retrieval date")
            for key in ("filingDate", "acceptedDate"):
                if row.get(key):
                    available_day = date.fromisoformat(str(row[key])[:10])
                    if available_day < date.fromisoformat(row["date"]) or available_day > retrieval.date():
                        raise ValueError("Filing/acceptance date is inconsistent with fiscal end or retrieval availability")
        if (reference - retrieval).total_seconds() > definition.retrieval_max_days * 86400 or (
                reference.date() - date.fromisoformat(end)).days > definition.observation_max_days:
            return obs.flagged("stale", "Earnings retrieval or fiscal observation exceeds the disclosed freshness policy")
        return replace(obs, status="available", reasons=())
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        return obs.flagged("inconsistent", redact_sensitive_text(exc, max_length=400))


def research_net_income(saved, ticker, *, basis="TTM", reference_time):
    """Adapt original saved evidence. A new audit never overwrites its saved number."""
    definition = DEFINITIONS["net_income." + ("ttm" if basis == "TTM" else basis)]
    ticker = redact_sensitive_text(ticker).strip().upper()
    empty = MetricObservation(definition.id, ticker, None, None, definition.basis, "unverifiable",
        "derived" if basis == "TTM" else "provider", "unverifiable", None, redact_sensitive_text(reference_time), assumptions=ASSUMPTIONS)
    try:
        if not isinstance(saved, dict) or ticker not in saved.get("request", {}).get("symbols", []):
            return empty.flagged("unsupported", "Company is not part of the saved research request")
        records = saved.get("evidence", [])
        if not isinstance(records, list) or any(not isinstance(e, dict) for e in records):
            return empty.flagged("unverifiable", "Malformed evidence register")
        ids = [e.get("id") for e in records]
        if any(not key for key in ids) or len(set(ids)) != len(ids):
            return empty.flagged("inconsistent", "Missing or duplicate evidence identifiers")
        category = "income_annual" if basis == "annual" else "income_quarterly"
        raw = [e for e in records if e.get("symbol") == ticker and e.get("category") == category]
        if len(raw) != 1 or raw[0].get("status") != "ok":
            # Legacy/saved-only derived values remain readable, but cannot be called revalidated TTM.
            rows = [r for r in saved.get("comparison", []) if isinstance(r, dict) and r.get("Ticker") == ticker]
            declared = number(rows[0].get("Net income (TTM)")) if basis == "TTM" and len(rows) == 1 else None
            return replace(empty, value=declared).flagged("unverifiable", "Unique successful raw income statements are unavailable; original saved values are retained")
        source = raw[0]
        observed = observe_net_income(source.get("data"), ticker, basis=basis,
            source_id=source["id"], provider=source.get("provider"), route=source.get("url"),
            retrieved_at=source.get("retrieved_at"), reference_time=reference_time)
        if basis != "TTM":
            return observed
        rows = [r for r in saved.get("comparison", []) if isinstance(r, dict) and r.get("Ticker") == ticker]
        if len(rows) != 1:
            return observed.flagged("unverifiable", "Unique saved earnings comparison is unavailable")
        row = rows[0]; contract = row.get("Metric contracts", {}).get("Net income (TTM)", {})
        declared = number(row.get("Net income (TTM)"))
        original = replace(observed, value=declared)
        if observed.status in {"inconsistent", "unverifiable", "missing", "unsupported"}:
            return replace(original, status=observed.status, verification="unverifiable")
        if saved.get("financial_methodology") != METHODOLOGY or contract.get("methodology") != METHODOLOGY:
            return original.flagged("unverifiable", "Legacy or unavailable financial methodology")
        if (declared is None or number(contract.get("value")) != declared or contract.get("status") != "ok"
                or contract.get("unit") != "currency" or contract.get("currency") != observed.currency
                or contract.get("applicability") != "applicable"):
            return original.flagged("inconsistent", "Saved earnings amount/unit/currency/status does not match its contract")
        if not contract.get("formula"):
            return original.flagged("unverifiable", "Saved earnings formula is unavailable")
        if row.get("TTM through") not in {None, observed.as_of} or row.get("TTM currency") not in {None, observed.currency}:
            return original.flagged("inconsistent", "Displayed TTM date/currency differs from raw earnings")
        if not math.isclose(declared, observed.value, rel_tol=1e-12, abs_tol=1e-6):
            return original.flagged("inconsistent", "Saved earnings do not reconcile to the four raw quarters; original amount retained")
        inputs = contract.get("inputs", [])
        if len(inputs) != 1 or not isinstance(inputs[0], dict):
            return original.flagged("unverifiable", "One derived earnings source input is required")
        inp = inputs[0]
        derived = [e for e in records if e.get("id") == inp.get("source_id")]
        if len(derived) != 1 or derived[0].get("category") != "income_ttm" or derived[0].get("symbol") != ticker or derived[0].get("status") != "ok":
            return original.flagged("inconsistent", "Derived earnings source identity cannot be resolved")
        ds = derived[0]; data = ds.get("data", [])
        if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
            return original.flagged("inconsistent", "Derived earnings source is ambiguous")
        record = data[0]
        quarters = record.get("quarters")
        expected = tuple((i.period_end, i.fiscal_year, i.period) for i in observed.inputs)
        actual = tuple((q.get("date"), int(q.get("fiscalYear")), q.get("period")) for q in quarters)
        if (actual != expected or contract.get("basis") != quarters or record.get("period") != "TTM"
                or record.get("methodology") != METHODOLOGY or record.get("reportedCurrency") != observed.currency
                or record.get("date") != observed.as_of or record.get("symbol") != ticker
                or number(record.get("netIncome")) != declared or inp.get("value") != declared
                or inp.get("category") != "income_ttm" or inp.get("field") != "netIncome"
                or inp.get("currency") != observed.currency or inp.get("date") != observed.as_of
                or inp.get("provider") != ds.get("provider") or inp.get("retrieved_at") != ds.get("retrieved_at")):
            return original.flagged("inconsistent", "Derived earnings amount/source/fiscal basis is inconsistent with raw statements")
        metadata = record.get("source_records", {})
        if metadata and (metadata.get("category") != category or metadata.get("retrieved_at") != source.get("retrieved_at")
                         or safe_route(metadata.get("url")) != safe_route(source.get("url"))):
            return original.flagged("inconsistent", "Derived source lineage differs from its raw statement source")
        return original
    except (AttributeError, ValueError, TypeError, KeyError, OverflowError) as exc:
        return empty.flagged("unverifiable", "Malformed saved earnings audit: " + redact_sensitive_text(exc, max_length=250))
