"""Presentation-only summaries of saved metadata. Never collect or infer evidence."""
from datetime import datetime, timezone
from numbers import Real
from urllib.parse import urlsplit, parse_qsl

from langgraphagenticai.utils.safety import redact_sensitive_text


def source_link(value):
    """Allow public HTTP sources without credential-bearing URLs."""
    try:
        text = str(value or "")
        parts = urlsplit(text)
        if parts.scheme not in {"https", "http"} or not parts.hostname or parts.username or parts.password or any(char.isspace() for char in text):
            return ""
        if redact_sensitive_text(text) != text or any(
            any(word in key.lower() for word in ("key", "token", "secret", "password", "signature", "credential"))
            for key, _ in parse_qsl(parts.query) + parse_qsl(parts.fragment)
        ):
            return ""
        return text
    except ValueError:
        return ""


def saved_time(value):
    if not value:
        return "Unavailable"
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat(sep=" ")
    except (ValueError, TypeError):
        return "Unavailable"


def snapshot_status(snapshot):
    quote = snapshot.get("quote", {})
    basis = snapshot.get("fundamental_basis", {})
    has_data = quote.get("price") is not None or any(isinstance(value, Real) and not isinstance(value, bool) for value in snapshot.get("fundamentals", {}).values())
    status = "Missing" if not has_data else "Partial" if snapshot.get("source_errors") or basis.get("status") != "complete" or quote.get("price") is None else "Retrieval successful"
    return [
        ("Company datasets", status),
        ("Source", "FMP company snapshot; news source labelled separately"),
        ("Quote as of", saved_time(quote.get("timestamp"))),
        ("Snapshot retrieved", saved_time(snapshot.get("fetched_at"))),
        ("Financial basis", f"{basis.get('period') or 'Unavailable'} through {basis.get('through') or 'Unavailable'}; currency {basis.get('currency') or 'Unknown'}"),
    ]


def evidence_status(result):
    records = result.get("evidence", [])
    usable = [item for item in records if item.get("status") == "ok" and item.get("data")]
    state = "Missing" if not usable else "Partial" if len(usable) != len(records) or result.get("gaps") else "Retrieval successful"
    dates, unknown_zone, missing = [], [], 0
    for item in usable:
        try:
            stamp = datetime.fromisoformat(str(item.get("retrieved_at") or "").replace("Z", "+00:00"))
        except ValueError:
            missing += 1
            continue
        if stamp.tzinfo is None:
            unknown_zone.append(stamp.isoformat(sep=" "))
        else:
            dates.append(stamp.astimezone(timezone.utc))
    date_range = " to ".join((min(dates).isoformat(sep=" "), max(dates).isoformat(sep=" "))) if dates else "Unavailable"
    if unknown_zone:
        date_range += "; timezone unknown: " + ", ".join(sorted(set(unknown_zone)))
    return [
        ("Saved evidence", f"{state}: {len(usable)} usable / {len(records)} records"),
        ("Sources", ", ".join(sorted({str(item.get("provider") or "Unknown") for item in usable})) or "Unavailable"),
        ("Evidence retrieved", date_range),
        ("Missing retrieval dates", str(missing)),
        ("Failed / missing records", str(sum(item.get("status") != "ok" or not item.get("data") for item in records))),
        ("Explicit stale records", str(sum(item.get("stale") is True or item.get("status") == "stale" for item in records))),
        ("Evidence gaps", str(len(result.get("gaps", [])))),
    ]


def market_status(data, requested_indexes=None):
    """Summarize actual saved quote presence, without implying freshness."""
    indexes = data.get("indexes") or {}
    requested = tuple(requested_indexes) if requested_indexes is not None else tuple(indexes)
    usable = sum(isinstance(indexes.get(label), dict) and indexes[label].get("price") is not None for label in requested)
    status = "Missing" if not usable else "Partial" if usable < len(requested) or data.get("warnings") else "Retrieval successful"
    return {"status": status, "usable_quotes": usable, "requested_quotes": len(requested)}
