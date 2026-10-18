"""Sector ETF returns from one dated, adjusted daily series per security."""
from zoneinfo import ZoneInfo

import pandas as pd

from langgraphagenticai.providers.discovery_numbers import finite_number

SECTORS = {
    "Technology": "XLK", "Financial Services": "XLF", "Healthcare": "XLV",
    "Consumer Cyclical": "XLY", "Communication Services": "XLC", "Industrials": "XLI",
    "Consumer Defensive": "XLP", "Energy": "XLE", "Utilities": "XLU",
    "Materials": "XLB", "Real Estate": "XLRE",
}
ALIASES = {"Financials": "Financial Services", "Financial": "Financial Services",
           "Communication": "Communication Services", "Cons. Cyclical": "Consumer Cyclical",
           "Cons. Staples": "Consumer Defensive", "Basic Materials": "Materials"}


def canonical_sector(value):
    return ALIASES.get(value, value) if isinstance(value, str) else "Unmapped"


def sector_returns(records, now, quote=None, timezone_name="America/New_York"):
    """Latest FMP price / prior trading observation's explicit adjClose.

    U.S. ETF quote instants map to New York dates. Current-day history remains
    usable; only a dated quote at the same/later date supersedes historical close.
    Missing adjusted closes never become raw closes or older baselines.
    """
    instant = pd.Timestamp(now)
    if instant.tz is None:
        instant = instant.tz_localize("UTC")
    today = instant.tz_convert(ZoneInfo(timezone_name)).date()
    result = {"day": None, "week": None, "ytd": None, "change": None, "as_of": None,
              "price": None, "price_date": None, "price_source": "Unavailable",
              "previous_adj_close": None, "starts": {}, "inputs": {}, "stale": True}
    dated = {}
    for row in records:
        stamp = pd.to_datetime(row.get("date"), errors="coerce")
        if pd.notna(stamp) and stamp.date() <= today:
            if stamp.date() in dated:
                dated[stamp.date()] = {"close": None, "adj_close": None}
            else:
                dated[stamp.date()] = row
    if not dated:
        return result
    dates = sorted(dated)
    end = dates[-1]
    price = finite_number(dated[end].get("close"))
    source, as_of = "FMP historical close (quote unavailable or older)", end.isoformat()
    if isinstance(quote, dict):
        stamp = pd.to_datetime(quote.get("as_of"), errors="coerce")
        value = finite_number(quote.get("price"))
        if pd.notna(stamp) and stamp.tz is not None and stamp <= instant and value is not None and value > 0:
            quote_date = stamp.tz_convert(ZoneInfo(timezone_name)).date()
            if quote_date >= end:
                end, price, source, as_of = quote_date, value, "FMP quote price", stamp.isoformat()
    result.update(price=price if price is not None and price > 0 else None, price_date=end.isoformat(),
                  price_source=source, as_of=as_of, stale=(today-end).days > 4)
    prior = [date for date in dates if date < end]
    if result["price"] is None:
        return result
    for period, offset, gap in (("day", 1, 4), ("week", 5, 10)):
        if len(prior) >= offset:
            start = prior[-offset]
            value = finite_number(dated[start].get("adj_close"))
            if value is not None and value > 0 and (end-start).days <= gap:
                result[period] = (price / value - 1) * 100
                result["starts"][period] = start.isoformat()
                result["inputs"][period] = {"price": price, "adjClose": value, "date": start.isoformat()}
                if period == "day":
                    result.update(previous_adj_close=value, change=price-value)
    year_start = end.replace(month=1, day=1)
    year_baselines = [date for date in dates if date < year_start]
    if year_baselines and end.year == today.year:
        start = year_baselines[-1]
        value = finite_number(dated[start].get("adj_close"))
        if value is not None and value > 0 and (year_start-start).days <= 7:
            result["ytd"] = (price / value - 1) * 100
            result["starts"]["ytd"] = start.isoformat()
            result["inputs"]["ytd"] = {"price": price, "adjClose": value, "date": start.isoformat()}
    return result


def industry_groups(universe, sector):
    """Membership only: undated screened returns cannot establish industry returns.

    Exact symbols are deduplicated. Share classes are retained; no market-cap
    aggregation is performed because issuer identity/currency/date are unverified.
    """
    if universe is None or universe.empty or not {"symbol", "sector", "industry"}.issubset(universe.columns):
        return {}
    frame = universe.copy()
    frame = frame[frame["sector"].map(canonical_sector) == sector]
    frame = frame.drop_duplicates("symbol")
    frame["industry"] = frame["industry"].fillna("Industry unavailable").astype(str)
    frame["_cap"] = frame.get("marketCap", pd.Series(index=frame.index, dtype=float)).map(finite_number)
    frame = frame.sort_values(["_cap", "symbol"], ascending=[False, True], na_position="last")
    return {name: group.drop(columns="_cap").to_dict("records") for name, group in frame.groupby("industry", sort=True)}
