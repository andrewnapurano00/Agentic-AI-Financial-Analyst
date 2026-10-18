"""Safe presentation of the shared five-index quote ribbon."""
from datetime import datetime, timezone
from html import escape
from langgraphagenticai.providers.market_strip import INDEXES


def market_strip_html(rows, packet, *, now=None):
    now = now or datetime.now(timezone.utc)
    cells = []
    for name, symbol in INDEXES.items():
        row = rows.get(symbol)
        title = "Configure FMP in Settings" if packet.get("status") == "unconfigured" else "Index quote unavailable; retries after the five-minute cache expires"
        values = '<span class="ax-market-state">Unavailable</span>'
        if row:
            percent = row.get("percent")
            change = f"{percent:+.2f}%" if percent is not None else "Change unavailable"
            color = "#37b68c" if percent is not None and percent > 0 else "#e2747e" if percent is not None and percent < 0 else "#bac7d5"
            state = "Saved quote" if row.get("retained") else "Latest reported"
            try:
                stamp = datetime.fromisoformat(row.get("as_of") or "")
                if stamp.tzinfo is None or (now-stamp).total_seconds() > 7*86400:
                    state += "; stale"
            except (ValueError, TypeError):
                state += "; quote date unavailable"
            title = f"{name} ({symbol}); {state}; FMP; index points; quote as of {row.get('as_of') or 'unavailable'}; retrieved {row.get('retrieved_at') or 'unavailable'}; {row.get('change_basis', 'daily price change')}; excludes dividends"
            badge = ' <span class="ax-market-state">Saved</span>' if row.get("retained") else ''
            if "stale" in state or "date unavailable" in state:
                badge += ' <span class="ax-market-state">Stale / undated</span>'
            values = f'<span class="ax-market-values"><span>{row["price"]:,.2f}</span><strong style="color:{color}">{change}</strong></span>{badge}'
        cells.append(f'<div class="ax-market-item" title="{escape(title, quote=True)}"><span class="ax-market-name">{escape(name)}</span>{values}</div>')
    dates = sorted({row["as_of"] for row in rows.values() if row.get("as_of")})
    as_of = dates[0] if len(dates) == 1 else (dates[0] + " to " + dates[-1]) if dates else "Unavailable"
    meta = "FMP | index levels | daily price change | as of " + as_of + " | cached up to 5 min"
    if packet.get("status") == "unconfigured":
        meta = "Configure FMP in Settings for index quotes."
    elif packet.get("status") != "available":
        meta += " | Partial coverage; saved quotes retain their original dates"
    return '<div class="ax-market-strip">' + ''.join(cells) + '</div><div class="ax-market-meta">' + escape(meta) + '</div>'
