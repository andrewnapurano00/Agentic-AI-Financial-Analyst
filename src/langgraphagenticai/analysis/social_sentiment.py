"""Finite, identity-aware social snapshots and unweighted daily statistics."""
from datetime import datetime, timedelta, timezone
from statistics import mean, median
from zoneinfo import ZoneInfo
from langgraphagenticai.analysis.trading_calendar import session_dates, last_trading_dates
from langgraphagenticai.providers.discovery_numbers import finite_number

PLATFORMS = {"Stocktwits": "stocktwits", "Twitter": "twitter"}
METRICS = {"Sentiment score": "Sentiment", "Posts": "Posts", "Comments": "Comments", "Likes": "Likes", "Impressions": "Impressions"}
FIELDS = tuple(prefix + suffix for prefix in PLATFORMS.values() for suffix in METRICS.values())
WINDOWS = ("Last 5 trading days", "Latest 5 reported trading dates")


def normalize_snapshots(rows, symbol, now):
    records, conflicts = {}, set()
    rejected = duplicates = conflict_count = invalid_values = 0
    for row in rows:
        if not isinstance(row, dict) or str(row.get("symbol") or "").strip().upper() != symbol:
            rejected += 1
            continue
        try:
            raw = row.get("date")
            if not isinstance(raw, str) or not raw.strip() or len(raw) > 64:
                raise ValueError("Missing observation time")
            stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            aware = stamp.tzinfo is not None
            if aware:
                stamp = stamp.astimezone(timezone.utc)
                if stamp > now:
                    raise ValueError("Future observation")
            elif stamp.date() > now.date():
                raise ValueError("Future calendar date")
        except (TypeError, ValueError, OverflowError):
            rejected += 1
            continue
        record = {"timestamp": stamp.isoformat(), "day": stamp.date().isoformat(),
                  "timezone": "UTC (explicit offset normalized)" if aware else "Unknown (provider wall-clock date)"}
        for field in FIELDS:
            value = finite_number(row.get(field))
            if value is not None and not field.endswith("Sentiment") and value < 0:
                value = None
            if row.get(field) is not None and value is None:
                invalid_values += 1
            record[field] = value
        if not any(record[field] is not None for field in FIELDS):
            rejected += 1
            continue
        key = record["timestamp"]
        if key in conflicts:
            duplicates += 1
        elif key in records:
            duplicates += 1
            if any(records[key][field] != record[field] for field in FIELDS):
                records.pop(key)
                conflicts.add(key)
                conflict_count += 1
        else:
            records[key] = record
    return sorted(records.values(), key=lambda r: r["timestamp"]), {
        "rejected_rows": rejected, "duplicate_rows": duplicates,
        "conflicting_timestamps": conflict_count, "invalid_values": invalid_values,
    }


def trading_day(record):
    stamp = datetime.fromisoformat(record["timestamp"])
    if stamp.tzinfo is not None:
        return stamp.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    return record["day"]


def daily_statistics(records, now, window=WINDOWS[0], *, min_posts=1, hide_zero_sentiment=True):
    if window not in WINDOWS:
        raise ValueError("Unsupported sentiment window")
    if not isinstance(min_posts, int) or isinstance(min_posts, bool) or min_posts < 1:
        raise ValueError("Minimum posts must be at least one")
    ending = now.astimezone(ZoneInfo("America/New_York")).date()
    recent = last_trading_dates(ending)
    dated = [(trading_day(r), r) for r in records]
    if window == WINDOWS[0]:
        days = recent
    else:
        earliest = min([ending, *(datetime.fromisoformat(day).date() for day, _ in dated)])
        sessions = set(session_dates(earliest, ending))
        days = sorted({day for day, _ in dated if day in sessions})[-5:]
    result = []
    for day in days:
        observations = [r for observed_day, r in dated if observed_day == day]
        for platform, prefix in PLATFORMS.items():
            active = [r for r in observations if r.get(prefix+"Posts") is not None and r[prefix+"Posts"] >= min_posts]
            for metric, suffix in METRICS.items():
                values = [r[prefix+suffix] for r in active if r.get(prefix+suffix) is not None
                          and not (suffix == "Sentiment" and hide_zero_sentiment and r[prefix+suffix] == 0)]
                result.append({"Date": day, "Platform": platform, "Metric": metric,
                               "Average": mean(values) if values else None,
                               "Median": median(values) if values else None,
                               "Observations": len(values), "Snapshots": len(observations),
                               "Active snapshots": len(active), "Excluded snapshots": len(observations)-len(values)})
    return result
