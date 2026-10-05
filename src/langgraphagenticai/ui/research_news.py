"""Shared saved Serper coverage presentation; never retrieves new evidence."""
from datetime import datetime, timezone

import streamlit as st

from langgraphagenticai.deep_research.models import safe_url


def render_serper_news_coverage(result: dict) -> None:
    request = result.get("request", {})
    if not request.get("include_news"):
        return
    symbols = set(request.get("symbols", []))
    records = [item for item in result.get("evidence", [])
               if item.get("category") == "news" and item.get("provider") == "Serper"
               and item.get("status") == "ok" and item.get("symbol") in symbols
               and isinstance(item.get("data"), list) and item["data"]]
    records = [{**item, "data": [row for row in item["data"]
                if isinstance(row, dict) and isinstance(row.get("title"), str)
                and row["title"].strip() and safe_url(row.get("url") or item.get("url"))]}
               for item in records]
    records = [item for item in records if item["data"]]
    count = sum(len(item["data"]) for item in records)
    covered = len({item["symbol"] for item in records})
    times = []
    for item in records:
        try:
            value = datetime.fromisoformat(item.get("retrieved_at", "").replace("Z", "+00:00"))
            if value.tzinfo is not None:
                times.append(value.astimezone(timezone.utc))
        except (ValueError, TypeError, AttributeError):
            continue
    dates = sorted({value.strftime("%Y-%m-%d %H:%M:%S UTC") for value in times})
    retrieval = " to ".join([dates[0], dates[-1]]) if len(dates) > 1 else dates[0] if dates else "unavailable"
    st.caption(f"Serper news coverage · {count} results · {covered}/{len(symbols)} companies · "
               f"{request.get('news_days', 30)}-day requested lookback · Retrieved: {retrieval}")
    st.caption("News snippets are discovery evidence. Publication dates are supplied by Serper; "
               "the requested lookback does not verify each article's age. Saved reuse does not refresh news.")
    if not count:
        st.warning("Serper news was requested, but no usable news results were saved. "
                   "Check the data-coverage details and SERPER_API_KEY.")
    elif covered < len(symbols):
        st.warning("Serper news coverage is partial. Some requested companies have no usable saved news; "
                   "check Sources and evidence gaps.")
