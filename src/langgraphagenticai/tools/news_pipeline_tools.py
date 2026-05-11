from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import requests
import trafilatura
from langchain_core.tools import StructuredTool
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_MAX_ARTICLES_RETURNED = 8
MIN_EXTRACTED_ARTICLE_LEN = 250
MIN_CONTENT_FOR_ANALYSIS_LEN = 120
SLEEP_BETWEEN_ARTICLES = 0.15


def normalize_ticker(ticker: str) -> str:
    return (ticker or "").strip().upper()


def ensure_list(symbols: Union[str, List[str]]) -> List[str]:
    if isinstance(symbols, list):
        return [normalize_ticker(x) for x in symbols if str(x).strip()]
    if not symbols:
        return []
    return [normalize_ticker(x) for x in str(symbols).split(",") if str(x).strip()]


def clean_text_for_gpt(text: Any) -> str:
    if text is None:
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_title(text: str) -> str:
    txt = clean_text_for_gpt(text).lower()
    txt = re.sub(r"[^a-z0-9 ]+", "", txt)
    return txt.strip()


def get_marketaux_news(
    search_tickers: Union[str, List[str]],
    marketaux_api_key: str,
    published_after: Optional[str] = None,
    published_before: Optional[str] = None,
    language: str = "en",
    limit: int = 20,
    max_pages: int = 2,
    must_have_entities: bool = True,
    filter_entities: bool = True,
    group_similar: bool = True,
    search: Optional[str] = None,
) -> pd.DataFrame:
    tickers = ensure_list(search_tickers)
    if not marketaux_api_key or not tickers:
        return pd.DataFrame()

    s = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=0.7,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)

    all_rows: List[Dict[str, Any]] = []

    for ticker in tickers:
        page = 1
        while page <= max_pages:
            params = {
                "api_token": marketaux_api_key,
                "symbols": ticker,
                "language": language,
                "limit": max(1, min(int(limit), 50)),
                "page": page,
                "must_have_entities": "true" if must_have_entities else "false",
                "filter_entities": "true" if filter_entities else "false",
                "group_similar": "true" if group_similar else "false",
            }
            if published_after:
                params["published_after"] = published_after
            if published_before:
                params["published_before"] = published_before
            if search:
                params["search"] = search

            try:
                resp = s.get("https://api.marketaux.com/v1/news/all", params=params, timeout=30)
                if resp.status_code != 200:
                    break
                payload = resp.json()
            except Exception:
                break

            data = payload.get("data", [])
            if not data:
                break

            for item in data:
                if not isinstance(item, dict):
                    continue

                entities = item.get("entities") or []
                entity_symbols = []
                entity_names = []
                entity_types = []
                sentiments = []
                match_scores = []

                for ent in entities:
                    if not isinstance(ent, dict):
                        continue
                    if ent.get("symbol"):
                        entity_symbols.append(str(ent.get("symbol")))
                    if ent.get("name"):
                        entity_names.append(str(ent.get("name")))
                    if ent.get("type"):
                        entity_types.append(str(ent.get("type")))
                    if ent.get("sentiment_score") is not None:
                        sentiments.append(ent.get("sentiment_score"))
                    if ent.get("match_score") is not None:
                        match_scores.append(ent.get("match_score"))

                all_rows.append(
                    {
                        "search_tickers": ticker,
                        "uuid": item.get("uuid"),
                        "title": item.get("title"),
                        "description": item.get("description"),
                        "snippet": item.get("snippet"),
                        "url": item.get("url"),
                        "image_url": item.get("image_url"),
                        "source": item.get("source"),
                        "language": item.get("language"),
                        "published_at": item.get("published_at"),
                        "keywords": ",".join(item.get("keywords") or []),
                        "marketaux_sentiment": item.get("sentiment"),
                        "entity_symbols": ",".join(entity_symbols),
                        "entity_names": ",".join(entity_names),
                        "entity_types": ",".join(entity_types),
                        "entity_sentiment_avg": sum(sentiments) / len(sentiments) if sentiments else None,
                        "entity_match_score_avg": sum(match_scores) / len(match_scores) if match_scores else None,
                    }
                )

            page += 1

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    if "published_at" in df.columns:
        df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
        df = df.sort_values("published_at", ascending=False)
    return df.reset_index(drop=True)


def extract_with_trafilatura(url: str) -> str:
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ""
        return trafilatura.extract(downloaded, include_comments=False, include_tables=False) or ""
    except Exception:
        return ""


def extract_with_newspaper(url: str) -> str:
    """Optional newspaper fallback extractor.

    Keep newspaper/newspaper3k as a lazy optional import so a broken
    local newspaper install cannot crash the entire Streamlit app at startup.
    Trafilatura remains the primary extractor; this returns an empty string
    when newspaper is unavailable or broken.
    """
    try:
        from newspaper import Article  # type: ignore
    except Exception:
        return ""

    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text or ""
    except Exception:
        return ""


def extract_article_text(url: str, min_len: int = MIN_EXTRACTED_ARTICLE_LEN) -> str:
    if not url:
        return ""
    text = extract_with_trafilatura(url)
    if text and len(text.strip()) >= min_len:
        return text.strip()
    text = extract_with_newspaper(url)
    if text and len(text.strip()) >= min_len:
        return text.strip()
    return ""


def add_article_text(
    df: pd.DataFrame,
    url_col: str = "url",
    sleep_seconds: float = SLEEP_BETWEEN_ARTICLES,
    min_len: int = MIN_EXTRACTED_ARTICLE_LEN,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()
    article_texts = []
    extraction_status = []

    for url in out[url_col].fillna(""):
        text = extract_article_text(url, min_len=min_len)
        article_texts.append(text)
        extraction_status.append("success" if len(text) >= min_len else "failed")
        if sleep_seconds and sleep_seconds > 0:
            time.sleep(sleep_seconds)

    out["article_text"] = article_texts
    out["article_text_len"] = out["article_text"].fillna("").str.len()
    out["article_extraction_status"] = extraction_status
    return out


def build_content_for_analysis(row: pd.Series) -> str:
    article_text_clean = row.get("article_text_clean", "") or ""
    title_clean = row.get("title_clean", "") or ""
    description_clean = row.get("description_clean", "") or ""
    snippet_clean = row.get("snippet_clean", "") or ""

    if len(article_text_clean.strip()) >= MIN_CONTENT_FOR_ANALYSIS_LEN:
        return article_text_clean.strip()

    fallback = "\n\n".join(
        [x for x in [title_clean, description_clean, snippet_clean] if str(x).strip()]
    ).strip()
    return fallback


def build_gpt_input_text(row: pd.Series) -> str:
    parts = [
        f"Search Tickers: {row.get('search_tickers', '') or ''}",
        f"Title: {row.get('title_clean', '') or ''}",
        f"Description: {row.get('description_clean', '') or ''}",
        f"Snippet: {row.get('snippet_clean', '') or ''}",
        f"Source: {row.get('source', '') or ''}",
        f"Published At: {row.get('published_at', '') or ''}",
        f"URL: {row.get('url', '') or ''}",
        f"Entity Symbols: {row.get('entity_symbols', '') or ''}",
        "",
        "Article Content:",
        row.get("content_for_analysis", "") or "",
    ]
    return "\n".join([p for p in parts if str(p).strip()]).strip()


def prepare_news_for_gpt(
    df: pd.DataFrame,
    dedupe: bool = True,
    min_content_len: int = MIN_CONTENT_FOR_ANALYSIS_LEN,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()
    out["title_clean"] = out["title"].fillna("").apply(clean_text_for_gpt)
    out["description_clean"] = out["description"].fillna("").apply(clean_text_for_gpt)
    out["snippet_clean"] = out["snippet"].fillna("").apply(clean_text_for_gpt)
    out["article_text_clean"] = out["article_text"].fillna("").apply(clean_text_for_gpt)
    out["article_text_clean_len"] = out["article_text_clean"].str.len()
    out["content_for_analysis"] = out.apply(build_content_for_analysis, axis=1)
    out["content_for_analysis_len"] = out["content_for_analysis"].fillna("").str.len()
    out = out[out["content_for_analysis_len"] >= min_content_len].copy()

    if out.empty:
        return out

    out["title_norm"] = out["title_clean"].apply(normalize_title)

    if dedupe:
        sort_cols = []
        if "content_for_analysis_len" in out.columns:
            sort_cols.append("content_for_analysis_len")
        if "published_at" in out.columns:
            sort_cols.append("published_at")
        out = (
            out.sort_values(sort_cols, ascending=[False] * len(sort_cols))
            .drop_duplicates(subset=["title_norm", "source"], keep="first")
            .copy()
        )

    if "published_at" in out.columns:
        out = out.sort_values("published_at", ascending=False)

    out["gpt_input_text"] = out.apply(build_gpt_input_text, axis=1)
    out["gpt_input_len"] = out["gpt_input_text"].str.len()
    return out.reset_index(drop=True)


def run_news_pipeline(
    search_tickers: Union[str, List[str]],
    marketaux_api_key: str,
    published_after: Optional[str] = None,
    published_before: Optional[str] = None,
    language: str = "en",
    limit: int = 20,
    max_pages: int = 2,
    must_have_entities: bool = True,
    filter_entities: bool = True,
    group_similar: bool = True,
    search: Optional[str] = None,
    sleep_seconds: float = SLEEP_BETWEEN_ARTICLES,
    min_extracted_article_len: int = MIN_EXTRACTED_ARTICLE_LEN,
    min_content_len: int = MIN_CONTENT_FOR_ANALYSIS_LEN,
    dedupe: bool = True,
    debug: bool = False,
) -> pd.DataFrame:
    df_news = get_marketaux_news(
        search_tickers=search_tickers,
        marketaux_api_key=marketaux_api_key,
        published_after=published_after,
        published_before=published_before,
        language=language,
        limit=limit,
        max_pages=max_pages,
        must_have_entities=must_have_entities,
        filter_entities=filter_entities,
        group_similar=group_similar,
        search=search,
    )

    if debug:
        print("After API pull:", df_news.shape)
    if df_news.empty:
        return df_news

    df_news = add_article_text(
        df_news,
        url_col="url",
        sleep_seconds=sleep_seconds,
        min_len=min_extracted_article_len,
    )

    final_df = prepare_news_for_gpt(
        df=df_news,
        dedupe=dedupe,
        min_content_len=min_content_len,
    )

    if debug:
        print("After GPT prep:", final_df.shape)

    return final_df


def compute_news_window(days_back: int) -> tuple[str, str]:
    now = datetime.utcnow()
    published_before = now.strftime("%Y-%m-%dT%H:%M:%S")
    published_after = (now - timedelta(days=max(1, int(days_back)))).strftime("%Y-%m-%dT%H:%M:%S")
    return published_after, published_before


def compact_article_records(df: pd.DataFrame, max_articles: int) -> List[Dict[str, Any]]:
    if df.empty:
        return []

    keep_cols = [
        c
        for c in [
            "published_at",
            "source",
            "title_clean",
            "title",
            "entity_symbols",
            "article_extraction_status",
            "content_for_analysis_len",
            "marketaux_sentiment",
            "url",
            "content_for_analysis",
        ]
        if c in df.columns
    ]

    work = df[keep_cols].copy().head(max_articles)
    if "published_at" in work.columns:
        work["published_at"] = work["published_at"].astype(str)
    return work.to_dict(orient="records")


def build_marketaux_news_fetch_tools(marketaux_api_key: Optional[str] = None):
    def _make_tool(func):
        return StructuredTool.from_function(
            func=func,
            name=func.__name__,
            description=(func.__doc__ or "").strip(),
        )

    cache: Dict[str, pd.DataFrame] = {}
    marketaux_api_key = (marketaux_api_key or os.getenv("MARKETAUX_API_KEY") or "").strip()

    def _safe_json_dumps(payload: Dict[str, Any]) -> str:
        return json.dumps(payload, indent=2, ensure_ascii=False, default=str)

    def _error_payload(tool_name: str, message: str, **extra) -> str:
        payload: Dict[str, Any] = {"ok": False, "tool": tool_name, "error": message}
        payload.update(extra)
        return _safe_json_dumps(payload)

    def _cache_key(tickers: List[str], days_back: int, limit: int, max_pages: int, dedupe: bool, search: str) -> str:
        return json.dumps(
            {
                "tickers": sorted(tickers),
                "days_back": int(days_back),
                "limit": int(limit),
                "max_pages": int(max_pages),
                "dedupe": bool(dedupe),
                "search": search or "",
            },
            sort_keys=True,
        )

    def fetch_marketaux_company_news(
        symbols: str,
        days_back: int = 7,
        limit: int = 20,
        max_pages: int = 2,
        dedupe: bool = True,
        max_articles_returned: int = DEFAULT_MAX_ARTICLES_RETURNED,
        search: str = "",
    ) -> str:
        """
        Fetch processed recent company news for one or more tickers using Marketaux,
        including article extraction, cleaning, deduping, and compact article records.
        symbols can be a comma-separated string like 'MSFT,NVDA'.
        """
        tickers = ensure_list(symbols)

        if not marketaux_api_key:
            return _error_payload(
                "fetch_marketaux_company_news",
                "MARKETAUX_API_KEY is missing. Add it in the sidebar or environment before using enhanced news tools.",
                symbols=tickers,
            )
        if not tickers:
            return _error_payload("fetch_marketaux_company_news", "At least one ticker symbol is required.")

        key = _cache_key(tickers, int(days_back), int(limit), int(max_pages), bool(dedupe), (search or "").strip())

        try:
            if key in cache:
                df = cache[key].copy()
            else:
                published_after, published_before = compute_news_window(days_back)
                df = run_news_pipeline(
                    search_tickers=tickers,
                    marketaux_api_key=marketaux_api_key,
                    published_after=published_after,
                    published_before=published_before,
                    limit=max(5, min(int(limit), 50)),
                    max_pages=max(1, min(int(max_pages), 5)),
                    dedupe=bool(dedupe),
                    search=(search or "").strip() or None,
                    debug=False,
                )
                cache[key] = df.copy()
        except Exception as exc:
            return _error_payload("fetch_marketaux_company_news", str(exc), symbols=tickers)

        return _safe_json_dumps(
            {
                "ok": True,
                "tool": "fetch_marketaux_company_news",
                "symbols": tickers,
                "article_count": int(len(df)),
                "articles": compact_article_records(df, max_articles=max(1, min(int(max_articles_returned), 20))),
                "notes_for_agent": [
                    "This news set has already been cleaned and deduped.",
                    "Use the content_for_analysis field for qualitative synthesis.",
                    "If the user asks for provenance, mention title, source, date, and URL.",
                ],
            }
        )

    return [_make_tool(fetch_marketaux_company_news)]