"""Explicit, bounded multi-provider company news; no model calls or scraping."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
import requests
import streamlit as st
from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.providers.market_brief_news import merge_news
from langgraphagenticai.tools.serper_tools import SerperClient
from langgraphagenticai.providers.news_content import preview
from langgraphagenticai.state.research_context import normalize_company_symbol
from langgraphagenticai.utils.safety import redact_sensitive_text

ENDPOINT="https://financialmodelingprep.com/api/v3/stock_news"


@st.cache_data(ttl=600,max_entries=64,show_spinner=False)
def _collect(symbol,company,fmp_key,marketaux_key,serper_key):
    now=datetime.now(timezone.utc);cutoff=now-timedelta(days=7)
    def collect(provider):
        rows=[];warnings=[]
        key={"FMP":fmp_key,"Marketaux":marketaux_key,"Serper":serper_key}[provider]
        if not key.strip():return [],[provider+" is not configured; other news sources retained."]
        try:
            if provider=="FMP":
                payload=get_fmp_json(ENDPOINT,api_key=key,params={"tickers":symbol,"limit":12},timeout=(5,20))
                if not isinstance(payload,list):raise ValueError("Invalid company news envelope")
                for item in payload[:12]:
                    if not isinstance(item,dict) or symbol not in {value.strip().upper() for value in str(item.get("symbol") or "").split(",")}:continue
                    rows.append(dict(title=item.get("title"),url=item.get("url"),snippet=item.get("text"),published=item.get("publishedDate"),publisher=item.get("site")))
            elif provider=="Marketaux":
                response=requests.get("https://api.marketaux.com/v1/news/all",params={"api_token":key,"symbols":symbol,
                    "filter_entities":"true","language":"en","limit":3,"group_similar":"true","published_after":cutoff.strftime("%Y-%m-%dT%H:%M:%S")},timeout=(5,20))
                response.raise_for_status();payload=response.json()
                if not isinstance(payload,dict) or not isinstance(payload.get("data"),list):raise ValueError("Invalid company news envelope")
                for item in payload["data"][:3]:
                    if not isinstance(item,dict):continue
                    entities=[str(e.get("symbol") or "").strip().upper() for e in item.get("entities",[]) if isinstance(e,dict)]
                    if entities and symbol not in entities:continue
                    rows.append(dict(title=item.get("title"),url=item.get("url"),snippet=preview(item),published=item.get("published_at"),publisher=item.get("source")))
            else:
                client=SerperClient(key)
                query=f'"{company}" stock news' if company != symbol else f'{symbol} stock news'
                payload=client.search(query,days=7,limit=8)
                rows=list(payload.get("results",[]))[:8]
                # News and ordinary Google search index different material. A bounded
                # web fallback recovers company coverage absent from the news index.
                if len(rows)<3:
                    fallback=client.search(query,news=False,days=7,limit=5,filter_dates=True)
                    rows.extend(fallback.get("results",[])[:5])
                if not rows:raise ValueError("Company search unavailable")
            normalized=[]
            checked_at=datetime.now(timezone.utc)
            for row in rows:
                published=str(row.get("published") or "")
                try:
                    stamp=datetime.fromisoformat(published.replace("Z","+00:00"))
                    # Unknown provider timezones are checked by UTC calendar date only.
                    if stamp.tzinfo is None:
                        warnings.append(provider+": publication timezone unknown; filtering uses UTC calendar dates only.")
                        if not cutoff.date()<=stamp.date()<=checked_at.date():continue
                    elif not cutoff<=stamp<=checked_at:continue
                except (TypeError,ValueError):
                    warnings.append(provider+": some publication dates are missing/relative; requested lookback is not verified for those stories.")
                normalized.append({"title":redact_sensitive_text(row.get("title") or "Untitled",max_length=500),"url":row.get("url"),
                    "snippet":redact_sensitive_text(row.get("snippet"),max_length=2000),"published":redact_sensitive_text(published,max_length=100),
                    "publisher":redact_sensitive_text(row.get("publisher"),max_length=200),"providers":[provider]})
            if not normalized:warnings.append(provider+": no usable matching news returned in the requested window.")
            return normalized,list(dict.fromkeys(warnings))
        except Exception:
            return [],[provider+" company news unavailable; successful sources retained. Check provider access or refresh to retry."]
    with ThreadPoolExecutor(max_workers=3) as pool:
        parts=list(pool.map(collect,("FMP","Marketaux","Serper")))
    return dict(symbol=symbol,company=company,lookback_days=7,retrieved_at=datetime.now(timezone.utc).isoformat(),
                articles=merge_news([row for rows,_ in parts for row in rows]),warnings=[w for _,warnings in parts for w in warnings])


def load_ticker_news(symbol,company,fmp_key="",marketaux_key="",serper_key="",*,refresh=False):
    symbol=normalize_company_symbol(symbol)
    company=redact_sensitive_text(company or symbol,max_length=160)
    if not any(k.strip() for k in (fmp_key,marketaux_key,serper_key)):raise ValueError("Configure at least one news provider.")
    if refresh:_collect.clear(symbol,company,fmp_key,marketaux_key,serper_key)
    return _collect(symbol,company,fmp_key,marketaux_key,serper_key)
