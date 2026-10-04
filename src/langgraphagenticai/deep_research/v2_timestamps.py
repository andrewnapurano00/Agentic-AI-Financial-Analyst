"""Saved V2 operation time; deliberately separate from evidence freshness (D01-D03)."""
from datetime import datetime, timezone


def _utc(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def format_saved_time(value):
    """Format only trustworthy timezone-aware timestamps, including legacy history."""
    parsed = _utc(value)
    return parsed.strftime("%Y-%m-%d %H:%M:%S UTC") if parsed else "unavailable"


def saved_result_caption(result, *, now=None):
    parsed = _utc(result.get("result_generated_at"))
    if parsed is None:
        return "Saved result generated: unavailable (legacy or invalid timestamp). Evidence dates may differ."
    current = now or datetime.now(timezone.utc)
    seconds = (current.astimezone(timezone.utc) - parsed).total_seconds()
    if seconds < 0:
        age = "age unavailable (clock mismatch)"
    elif seconds < 60:
        age = "less than 1 minute ago"
    elif seconds < 3600:
        count = int(seconds // 60)
        age = f"{count} minute{'s' if count != 1 else ''} ago"
    elif seconds < 86400:
        count = int(seconds // 3600)
        age = f"{count} hour{'s' if count != 1 else ''} ago"
    else:
        count = int(seconds // 86400)
        age = f"{count} day{'s' if count != 1 else ''} ago"
    return f"Saved result generated: {format_saved_time(result['result_generated_at'])} · {age}. Evidence dates may differ."


def stamp_saved_result(result, history, *, now=None):
    """Stamp an explicitly completed run/recovery, merging its saved checkpoint.

    Call only after run/resume returns, before optional decisions. No provider access,
    legacy backfill, report-completeness inference, or timestamp from stage updates.
    """
    completed = now or datetime.now(timezone.utc)
    if completed.tzinfo is None or completed.utcoffset() is None:
        raise ValueError("Completion time must include a timezone")
    run_id = result["id"]
    merged = next((dict(item) for item in history if item.get("id") == run_id), {})
    merged.update(result)
    merged["result_generated_at"] = completed.astimezone(timezone.utc).isoformat()
    result.update(merged)
    return [merged] + [item for item in history if item.get("id") != run_id][:7]
