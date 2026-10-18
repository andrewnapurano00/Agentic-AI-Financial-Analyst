"""Explicit target evidence + shared quote cache; failures remain independent."""
from datetime import datetime,timezone
import streamlit as st
from langgraphagenticai.analysis.price_targets import normalize_targets
from langgraphagenticai.providers.fmp_http import get_fmp_json,ProviderRequestError
from langgraphagenticai.providers.discovery import load_selected_quote
from langgraphagenticai.state.research_context import normalize_company_symbol

ENDPOINT="https://financialmodelingprep.com/api/v4/price-target-summary"


@st.cache_data(ttl=3600,max_entries=64,show_spinner=False)
def _summary(symbol,api_key):
    packet=dict(symbol=symbol,provider="Financial Modeling Prep",retrieved_at=datetime.now(timezone.utc).isoformat(),as_of=None,targets=[],warnings=[])
    try:
        payload=get_fmp_json(ENDPOINT,api_key=api_key,params={"symbol":symbol},timeout=(5,20))
        packet["targets"]=[{**row,"retrieved_at":packet["retrieved_at"]} for row in normalize_targets(payload,symbol)]
    except ProviderRequestError as exc:
        packet["warnings"].append(f"Price targets unavailable (HTTP {exc.status_code}); refresh to retry." if exc.status_code else "Price-target request failed; refresh to retry.")
    except ValueError as exc:
        packet["warnings"].append(str(exc))
    return packet


def load_price_targets(symbol,api_key,*,refresh=False):
    symbol=normalize_company_symbol(symbol)
    if not api_key.strip():raise ValueError("Configure FMP to load price targets.")
    if refresh:
        _summary.clear(symbol,api_key)
        load_selected_quote.clear(symbol,api_key)
    summary=_summary(symbol,api_key)
    quote=load_selected_quote(symbol,api_key)
    return dict(symbol=symbol,summary=summary,quote=quote)
