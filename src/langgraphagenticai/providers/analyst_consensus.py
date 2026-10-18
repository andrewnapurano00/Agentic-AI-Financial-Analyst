"""One bounded FMP consensus request; credential-safe cached evidence."""
from datetime import datetime, timezone
import streamlit as st
from langgraphagenticai.providers.fmp_http import get_fmp_json, ProviderRequestError
from langgraphagenticai.state.research_context import normalize_company_symbol
from langgraphagenticai.analysis.analyst_consensus import consensus_distribution

ENDPOINT = "https://financialmodelingprep.com/api/v4/upgrades-downgrades-consensus"


@st.cache_data(ttl=3600, max_entries=64, show_spinner=False)
def _collect(symbol, api_key):
    packet = {"symbol":symbol,"provider":"Financial Modeling Prep","retrieved_at":datetime.now(timezone.utc).isoformat(),
              "as_of":None,"status":"unavailable","warnings":[],"data":None}
    try:
        payload=get_fmp_json(ENDPOINT,api_key=api_key,params={"symbol":symbol},timeout=(5,20))
        packet["data"]=consensus_distribution(payload,symbol)
        packet["status"]="available"
    except ProviderRequestError as exc:
        packet["warnings"]=[f"Analyst consensus request failed (HTTP {exc.status_code}). Check FMP access and refresh to retry." if exc.status_code else "Analyst consensus request could not be completed. Refresh to retry."]
    except ValueError as exc:
        packet["warnings"]=[str(exc)]
    return packet


def load_analyst_consensus(symbol, api_key, *, refresh=False):
    symbol=normalize_company_symbol(symbol)
    if not api_key.strip():
        raise ValueError("Configure FMP to load analyst consensus.")
    if refresh:
        _collect.clear(symbol,api_key)
    return _collect(symbol,api_key)
