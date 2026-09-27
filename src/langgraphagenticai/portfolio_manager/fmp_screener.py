from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.utils.safety import sanitize_error


SERVER_KEYS = {
    'country', 'exchange', 'sector', 'industry', 'isActivelyTrading',
    'marketCapMoreThan', 'marketCapLowerThan',
    'priceMoreThan', 'priceLowerThan',
    'volumeMoreThan', 'volumeLowerThan',
    'betaMoreThan', 'betaLowerThan',
    'dividendMoreThan', 'dividendLowerThan',
    'limit', 'page', 'isEtf', 'isFund'
}


def _sanitize_params(filters: dict[str, Any]) -> dict[str, Any]:
    p = {k: v for k, v in (filters or {}).items() if k in SERVER_KEYS and v not in (None, '', [])}
    for bkey in ['isActivelyTrading', 'isEtf', 'isFund']:
        if bkey in p and isinstance(p[bkey], bool):
            p[bkey] = 'true' if p[bkey] else 'false'
    p['limit'] = max(1, min(int(p.get('limit', 100)), 500))
    return p


@st.cache_data(ttl=3600, show_spinner=False)
def fmp_company_screener(filters: dict[str, Any], api_key: str, timeout: int = 25, max_pages: int = 10) -> tuple[pd.DataFrame, dict[str, Any]]:
    api_key = str(api_key or '').strip()
    if not api_key:
        return pd.DataFrame(), {'errors': ['Missing FMP API key'], 'warnings': [], 'pages': 0}

    url = 'https://financialmodelingprep.com/stable/company-screener'
    params_base = _sanitize_params(filters)
    all_rows: list[pd.DataFrame] = []
    meta = {'errors': [], 'warnings': [], 'pages': 0}

    for page in range(max_pages):
        try:
            data = get_fmp_json(
                url, api_key=api_key, params={**params_base, 'page': page},
                timeout=(5, timeout),
            ) or []
            if not data:
                break
            df = pd.DataFrame(data)
            if 'symbol' in df.columns:
                df = df.rename(columns={'symbol': 'ticker'})
            if 'ticker' not in df.columns:
                break
            df['ticker'] = df['ticker'].astype(str).str.upper().str.strip()
            all_rows.append(df)
            meta['pages'] = page + 1
            if len(df) < int(params_base['limit']):
                break
        except Exception as exc:
            meta['warnings'].append(f"Page {page}: {sanitize_error(exc)}")
            break

    out = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    if out.empty:
        return out, meta

    for col in ['marketCap', 'price', 'volume', 'beta']:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors='coerce')
    out = out.drop_duplicates(subset=['ticker']).reset_index(drop=True)
    if 'isEtf' in out.columns:
        out = out[out['isEtf'].astype(str).str.lower().isin(['false', '0', 'nan'])]
    if 'isFund' in out.columns:
        out = out[out['isFund'].astype(str).str.lower().isin(['false', '0', 'nan'])]
    if 'marketCap' in out.columns:
        out = out.sort_values('marketCap', ascending=False, na_position='last').reset_index(drop=True)
    return out, meta
