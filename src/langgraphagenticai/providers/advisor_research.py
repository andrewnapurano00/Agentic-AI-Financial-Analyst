"""Bounded issuer follow-up: annual revenue history and dated news references."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from urllib.parse import urlsplit, urlunsplit
import streamlit as st
from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.providers.advisor_batches import RequestBatch
from langgraphagenticai.providers.discovery_numbers import finite_number
from langgraphagenticai.providers.portfolio_architect import BASE, clean, failure_note
from langgraphagenticai.portfolio_architect.schemas import Fact
from langgraphagenticai.state.research_context import normalize_company_symbol


def annual_growth(symbol, raw, stamp, now=None):
    now = now or datetime.now(timezone.utc).date()
    if not isinstance(raw, list) or len(raw) != 4:
        return []
    try:
        rows = sorted(raw, key=lambda r: r["date"])
        days = [date.fromisoformat(r["date"]) for r in rows]
        years = [int(r["fiscalYear"]) for r in rows]
        currency = rows[0]["reportedCurrency"]
        values = [finite_number(r.get("revenue")) for r in rows]
        if not currency or any(r.get("symbol") != symbol or r.get("period") != "FY" or
                               r.get("reportedCurrency") != currency for r in rows):
            return []
        if any(y != years[0]+i for i,y in enumerate(years)) or any(not 330 <= (b-a).days <= 400 for a,b in zip(days,days[1:])):
            return []
        if not 0 <= (now-days[-1]).days <= 550 or any(v is None or v <= 0 for v in values):
            return []
    except (ValueError, TypeError, KeyError):
        return []
    facts = [Fact(id=f"{symbol}:revenue_fy{y}", field=f"revenue_fy{y}", value=v, unit=currency,
                  basis=f"reported annual FY{y}; not TTM", as_of=d.isoformat(), retrieved_at=stamp,
                  source="FMP stable/income-statement") for y,v,d in zip(years,values,days)]
    facts.append(Fact(id=symbol+":revenue_cagr_3y",field="revenue_cagr_3y",value=(values[-1]/values[0])**(1/3)-1,
                      unit="fraction",basis=f"Local (FY{years[-1]} revenue / FY{years[0]} revenue)^(1/3)-1; same reported currency; annual, not TTM/forecast",
                      as_of=days[-1].isoformat(), retrieved_at=stamp, source="Local calculation from four saved FMP annual revenues"))
    return [f.model_dump() for f in facts]


def news_rows(symbol, raw, stamp, api_key="", now=None):
    now = now or datetime.now(timezone.utc).date()
    result, seen = [], set()
    for row in raw if isinstance(raw, list) else []:
        if not isinstance(row, dict) or row.get("symbol") != symbol:
            continue
        try:
            day = date.fromisoformat(str(row.get("publishedDate", ""))[:10])
            link = urlsplit(str(row.get("url", "")))
            if not 0 <= (now-day).days <= 30 or link.scheme != "https" or not link.hostname or link.username or link.password:
                continue
            url = urlunsplit(("https", link.netloc, link.path, "", ""))
            if api_key and api_key in url:
                continue
            title = clean(row.get("title"), api_key, 250)
            if not title or url in seen:
                continue
            seen.add(url)
            result.append({"id":f"{symbol}:news:{len(result)+1}","title":title,"url":url,
                           "published_date":day.isoformat(),"publication_timing":"Provider calendar date; timezone unverified",
                           "retrieved_at":stamp,"source":"FMP stable/news/stock", "publisher":clean(row.get("publisher"),api_key)})
        except (ValueError, TypeError):
            continue
        if len(result) == 3:
            break
    return result


@st.cache_data(ttl=3600, max_entries=8, show_spinner=False)
def load_issuer_research(names, api_key, _budget=None):
    budget = _budget or RequestBatch()
    if len(names) > 30 or any(normalize_company_symbol(s) != s for s in names):
        raise ValueError("At most thirty normalized issuer symbols per research collection.")
    def fetch(symbol):
        stamp = datetime.now(timezone.utc).isoformat()
        result = {"facts":[],"news":[],"warnings":[]}
        for route, params in (("income-statement",{"symbol":symbol,"period":"annual","limit":4}),
                              ("news/stock",{"symbols":symbol,"limit":5})):
            if budget.stopped.is_set():
                result["warnings"].append(budget.warning)
                break
            try:
                raw = budget.request(get_fmp_json, BASE+route,api_key=api_key,params=params)
                if route == "income-statement":
                    result["facts"] = annual_growth(symbol,raw,stamp)
                else:
                    result["news"] = news_rows(symbol,raw,stamp,api_key)
            except Exception as exc:
                result["warnings"].append(route+": "+failure_note(exc))
        return symbol,result
    with ThreadPoolExecutor(max_workers=3) as pool:
        return dict(pool.map(fetch,names))
