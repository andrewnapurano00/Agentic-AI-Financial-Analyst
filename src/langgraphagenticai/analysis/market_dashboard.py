"""Daily market dashboard arithmetic; missing adjusted inputs stay missing."""
import pandas as pd
from langgraphagenticai.analysis.sector_heatmap import sector_returns
from langgraphagenticai.providers.discovery_numbers import finite_number
from langgraphagenticai.technical_analysis.indicators import wilder_rsi


def dashboard_metrics(records, now, quote=None, quote_timezone="America/New_York"):
    result = sector_returns(records, now, quote, timezone_name=quote_timezone)
    result["quote_date_policy"] = quote_timezone
    end = pd.Timestamp(result["price_date"]).date() if result.get("price_date") else None
    dated = {}
    for row in records:
        stamp = pd.to_datetime(row.get("date"), errors="coerce")
        if pd.notna(stamp) and end and stamp.date() <= end:
            date = stamp.date()
            dated[date] = row if date not in dated else {"adj_close": None}
    prior = sorted(date for date in dated if date < end) if end else []
    for label, offset, gap in (("30D", 30, 55), ("60D", 60, 100)):
        result[label] = None
        if len(prior) >= offset and result.get("price"):
            start = prior[-offset]
            value = finite_number(dated[start].get("adj_close"))
            if value is not None and value > 0 and (end-start).days <= gap:
                result[label] = (result["price"] / value - 1) * 100
                result["inputs"][label] = {"price": result["price"], "adjClose": value, "date": start.isoformat()}
    # A live quote is not inserted as an extra daily indicator observation.
    values = pd.Series([finite_number(dated[date].get("adj_close")) for date in sorted(dated)], dtype=float)
    result["RSI (14)"] = None
    invalid = values.isna() | (values <= 0)
    if invalid.any():
        values = values.iloc[invalid[invalid].index[-1]+1:]
    if len(values) >= 15:
        result["RSI (14)"] = finite_number(wilder_rsi(values.reset_index(drop=True), 14).iloc[-1])
    for window in (7, 14, 21, 50, 200):
        result[f"vs SMA {window} %"] = float((result["price"] / values.iloc[-window:].mean() - 1) * 100) if len(values) >= window and result.get("price") else None
    result["indicator_date"] = max(dated).isoformat() if len(values) else None
    return result
