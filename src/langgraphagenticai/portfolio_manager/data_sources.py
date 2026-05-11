from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from langgraphagenticai.portfolio_manager.fmp_fundamentals import fetch_fmp_fundamental_snapshots
from langgraphagenticai.portfolio_manager.research_snapshot import build_research_snapshot

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    import trafilatura
except Exception:
    trafilatura = None

try:
    from newspaper import Article
except Exception:
    Article = None

SECTOR_ETFS = ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]
CROSS_ASSET = ["SPY", "QQQ", "IWM", "GLD", "TLT", "IEF", "SHY", "USO", "BTC-USD", "^VIX"]
ETF_SECTOR_MAP = {
    "XLB": "Materials",
    "XLC": "Communication Services",
    "XLE": "Energy",
    "XLF": "Financial Services",
    "XLI": "Industrials",
    "XLK": "Technology",
    "XLP": "Consumer Defensive",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLV": "Healthcare",
    "XLY": "Consumer Cyclical",
    "SPY": "US Equity Benchmark",
    "QQQ": "Large Cap Growth",
    "IWM": "Small Caps",
    "GLD": "Gold",
    "TLT": "Long Treasuries",
    "IEF": "Intermediate Treasuries",
    "SHY": "Short Treasuries",
    "USO": "Oil",
    "BTC-USD": "Bitcoin",
    "^VIX": "Volatility",
}

MIN_EXTRACTED_ARTICLE_LEN = 250
MIN_CONTENT_FOR_ANALYSIS_LEN = 120
THEME_KEYWORDS = {
    "earnings": ["earnings", "eps", "quarter", "guidance", "beat", "miss"],
    "guidance": ["guidance", "outlook", "forecast", "raised", "lowered"],
    "ai_product": ["ai", "artificial intelligence", "chip", "gpu", "cloud", "software", "product"],
    "m&a_capital": ["acquisition", "merger", "deal", "buyback", "dividend", "capital return"],
    "regulation_legal": ["lawsuit", "antitrust", "regulation", "probe", "investigation", "fine"],
    "macro_demand": ["demand", "consumer", "recession", "slowdown", "inflation", "tariff", "rates"],
}
POSITIVE_CATALYST_KEYWORDS = [
    "beat", "beats", "raised guidance", "guidance raised", "upgrade", "upgraded", "record",
    "strong demand", "acceleration", "margin expansion", "buyback", "contract win", "launch",
    "approval", "partnership", "outperform", "tailwind", "rebound", "surge", "expansion",
]
NEGATIVE_CATALYST_KEYWORDS = [
    "miss", "misses", "guidance cut", "lowered guidance", "downgrade", "downgraded", "lawsuit",
    "investigation", "probe", "fine", "warning", "slowdown", "margin pressure", "layoffs",
    "recall", "default", "bankruptcy", "tariff", "recession", "weak demand", "decline",
]
NOISY_KEYWORDS = [
    "analyst says", "price target", "roundup", "newsletter", "watchlist", "top stocks", "what to know",
    "opinion", "rumor", "rumour", "speculation", "social media", "reddit", "blog", "preview",
]


def _safe_float(x, default=None):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def _normalize_symbol(ticker: str) -> str:
    return str(ticker).upper().strip()


def build_reference_universe(user_tickers: list[str], benchmark: str) -> list[str]:
    universe = {_normalize_symbol(t) for t in user_tickers if str(t).strip()}
    universe.add(_normalize_symbol(benchmark))
    universe.update(SECTOR_ETFS)
    universe.update(CROSS_ASSET)
    return sorted(universe)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_price_history(tickers: list[str], period: str = "2y") -> pd.DataFrame:
    tickers = [_normalize_symbol(t) for t in tickers if str(t).strip()]
    if not tickers:
        return pd.DataFrame()

    data = yf.download(
        tickers=tickers,
        period=period,
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=True,
    )

    if data.empty or "Close" not in data:
        return pd.DataFrame()

    prices = data["Close"]
    if isinstance(prices, pd.Series):
        prices = prices.to_frame()

    prices.columns = [str(c).upper() for c in prices.columns]
    prices = prices.sort_index().ffill().dropna(how="all")
    return prices


def _infer_sector_from_info(ticker: str, info: dict[str, Any]) -> str:
    if ticker in ETF_SECTOR_MAP:
        return ETF_SECTOR_MAP[ticker]

    candidates = [
        info.get("sector"),
        info.get("sectorDisp"),
        info.get("category"),
        info.get("fundFamily"),
        info.get("quoteType"),
    ]
    for value in candidates:
        if value and str(value).strip():
            text = str(value).strip()
            if text.lower() not in {"none", "nan", "n/a"}:
                return text

    quote_type = str(info.get("quoteType") or "").lower()
    if "etf" in quote_type:
        return "ETF"
    if "equity" in quote_type:
        return "Equity"
    if ticker.endswith("-USD"):
        return "Digital Asset"
    return "Unknown"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_company_info(tickers: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for ticker in sorted({_normalize_symbol(t) for t in tickers if str(t).strip()}):
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception:
            info = {}

        sector = _infer_sector_from_info(ticker, info)
        out[ticker] = {
            "symbol": ticker,
            "shortName": info.get("shortName") or info.get("longName") or ticker,
            "sector": sector,
            "industry": info.get("industry") or ("ETF" if ticker in ETF_SECTOR_MAP else "Unknown"),
            "marketCap": _safe_float(info.get("marketCap")),
            "beta": _safe_float(info.get("beta")),
            "quoteType": info.get("quoteType"),
        }
    return out


def _build_retry_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=4,
        backoff_factor=0.7,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    })
    return s


def _safe_get(url: str, params: dict[str, Any], timeout: int = 20) -> Any:
    response = _build_retry_session().get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _normalize_text(text: str | None) -> str:
    return " ".join((text or "").strip().lower().split())


def _clean_text_for_analysis(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def _parse_date_to_iso(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
        except Exception:
            return ""
    text = str(value).strip()
    if not text:
        return ""
    candidates = [text, text.replace("Z", "+00:00"), text.replace(" UTC", "")]
    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
    return text


def _dedupe_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    deduped: list[dict[str, Any]] = []
    for article in articles:
        title_key = _normalize_text(article.get("title"))
        url_key = _normalize_text(article.get("url"))
        date_key = str(article.get("published_at", ""))[:10]
        key = url_key if url_key else f"{title_key}|{date_key}"
        if not key.strip("|") or key in seen:
            continue
        seen.add(key)
        deduped.append(article)
    return deduped


def _simple_sentiment_score(text: str) -> float:
    text_l = (text or "").lower()
    positive = [
        "beat", "beats", "strong", "record", "growth", "upgrade", "raised",
        "improves", "improving", "bullish", "expansion", "outperform", "momentum",
        "surge", "surges", "positive", "benefit", "tailwind",
    ]
    negative = [
        "miss", "misses", "weak", "cut", "cuts", "downgrade", "lowered",
        "decline", "declines", "bearish", "lawsuit", "investigation", "recession",
        "slowdown", "pressure", "volatile", "volatility", "risk", "warning",
        "layoffs", "margin pressure",
    ]
    pos = sum(word in text_l for word in positive)
    neg = sum(word in text_l for word in negative)
    raw = pos - neg
    if raw == 0:
        return 0.0
    return max(-1.0, min(1.0, round(raw / max(3, pos + neg), 4)))


def _sentiment_label(score: float) -> str:
    if score >= 0.20:
        return "Positive"
    if score <= -0.20:
        return "Negative"
    return "Neutral"


def _extract_marketaux_entity_sentiment(item: dict[str, Any], symbol: str) -> float | None:
    entities = item.get("entities") or []
    symbol = _normalize_symbol(symbol)
    matched_scores: list[float] = []
    fallback_scores: list[float] = []

    if isinstance(entities, list):
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            score = _safe_float(entity.get("sentiment_score"))
            if score is None:
                continue
            fallback_scores.append(score)
            entity_symbol = _normalize_symbol(entity.get("symbol") or "")
            if entity_symbol == symbol:
                matched_scores.append(score)

    if matched_scores:
        return float(sum(matched_scores) / len(matched_scores))
    if fallback_scores:
        return float(sum(fallback_scores) / len(fallback_scores))
    return _safe_float(item.get("sentiment"))


def _extract_with_trafilatura(url: str) -> str:
    if not trafilatura or not url:
        return ""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ""
        return trafilatura.extract(downloaded, include_comments=False, include_tables=False) or ""
    except Exception:
        return ""


def _extract_with_newspaper(url: str) -> str:
    if Article is None or not url:
        return ""
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text or ""
    except Exception:
        return ""


def _extract_article_text(url: str, min_len: int = MIN_EXTRACTED_ARTICLE_LEN) -> tuple[str, str]:
    text = _extract_with_trafilatura(url)
    if text and len(text.strip()) >= min_len:
        return text.strip(), "trafilatura"
    text = _extract_with_newspaper(url)
    if text and len(text.strip()) >= min_len:
        return text.strip(), "newspaper"
    return "", "failed"


def _build_content_for_analysis(title: str, summary: str, article_text: str) -> str:
    article_text_clean = _clean_text_for_analysis(article_text)
    if len(article_text_clean) >= MIN_CONTENT_FOR_ANALYSIS_LEN:
        return article_text_clean
    return "\n\n".join([x for x in [_clean_text_for_analysis(title), _clean_text_for_analysis(summary)] if x]).strip()


def _extract_theme_labels(text: str) -> list[str]:
    text_l = (text or "").lower()
    themes = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(k in text_l for k in keywords):
            themes.append(theme)
    return themes


def _keyword_hits(text: str, keywords: list[str]) -> int:
    text_l = (text or "").lower()
    return sum(1 for keyword in keywords if keyword in text_l)


def _classify_news_signal(title: str, summary: str, article_text: str, sentiment: float, themes: list[str]) -> tuple[str, float, str]:
    combined = " ".join([str(title or ""), str(summary or ""), str(article_text or "")]).strip()
    text_len = len((article_text or "").strip())
    pos_hits = _keyword_hits(combined, POSITIVE_CATALYST_KEYWORDS)
    neg_hits = _keyword_hits(combined, NEGATIVE_CATALYST_KEYWORDS)
    noisy_hits = _keyword_hits(combined, NOISY_KEYWORDS)

    if text_len < MIN_CONTENT_FOR_ANALYSIS_LEN and noisy_hits > 0:
        return "low_signal_noisy", -0.15, "thin article text and mostly opinion/watchlist style coverage"
    if noisy_hits >= 2 and pos_hits == 0 and neg_hits == 0:
        return "low_signal_noisy", -0.10, "coverage looks more commentary-driven than catalyst-driven"

    if neg_hits > pos_hits and (sentiment <= -0.10 or neg_hits >= 2 or "regulation_legal" in themes):
        penalty = min(1.0, 0.35 + 0.12 * neg_hits + (0.10 if "regulation_legal" in themes else 0.0))
        return "catalyst_negative", -penalty, "negative catalyst language tied to demand, guidance, or legal risk"

    if pos_hits > neg_hits and (sentiment >= 0.10 or pos_hits >= 2 or "earnings" in themes or "guidance" in themes):
        boost = min(1.0, 0.30 + 0.12 * pos_hits + (0.08 if "earnings" in themes or "guidance" in themes else 0.0))
        return "catalyst_positive", boost, "positive catalyst language tied to earnings, guidance, demand, or execution"

    if abs(float(sentiment or 0.0)) < 0.12:
        return "low_signal_noisy", -0.05, "signal is weak or mixed and not strong enough to influence positioning much"

    if float(sentiment or 0.0) > 0:
        return "catalyst_positive", min(0.45, 0.20 + abs(float(sentiment)) * 0.8), "news flow leans positive but without a major confirmed catalyst"
    return "catalyst_negative", max(-0.45, -0.20 - abs(float(sentiment)) * 0.8), "news flow leans negative but without a single dominant catalyst"


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_recent_news(
    tickers: list[str],
    marketaux_api_key: str,
    lookback_days: int = 7,
    max_articles: int = 8,
) -> pd.DataFrame:
    api_key = str(marketaux_api_key or "").strip()
    if not api_key:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    base_url = "https://api.marketaux.com/v1/news/all"
    published_after = (datetime.now(timezone.utc) - timedelta(days=max(1, int(lookback_days)))).strftime("%Y-%m-%dT%H:%M:%S")

    for symbol in sorted({_normalize_symbol(t) for t in tickers if str(t).strip()}):
        params = {
            "api_token": api_key,
            "symbols": symbol,
            "language": "en",
            "published_after": published_after,
            "limit": max(1, min(int(max_articles), 20)),
            "filter_entities": "true",
            "must_have_entities": "true",
            "group_similar": "true",
        }
        try:
            payload = _safe_get(base_url, params=params, timeout=25)
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", "unknown")
            try:
                detail = exc.response.json()
            except Exception:
                detail = getattr(exc.response, "text", str(exc))
            errors.append(f"{symbol}: HTTP {status} - {detail}")
            continue
        except Exception as exc:
            errors.append(f"{symbol}: {exc}")
            continue

        data = payload.get("data", []) if isinstance(payload, dict) else []
        articles: list[dict[str, Any]] = []
        for item in data:
            title = str(item.get("title") or "").strip()
            summary = str(item.get("description") or item.get("snippet") or "").strip()
            source = str(item.get("source") or item.get("domain") or "MarketAux").strip()
            url = str(item.get("url") or "").strip()
            published_at = _parse_date_to_iso(item.get("published_at"))
            api_sentiment = _extract_marketaux_entity_sentiment(item, symbol)
            if not title and not summary:
                continue

            article_text, extraction_method = _extract_article_text(url)
            content_for_analysis = _build_content_for_analysis(title, summary, article_text)
            derived_sentiment = _simple_sentiment_score(content_for_analysis or f"{title} {summary}")
            theme_labels = _extract_theme_labels(content_for_analysis or f"{title} {summary}")
            signal_bucket, signal_strength, signal_rationale = _classify_news_signal(
                title=title,
                summary=summary,
                article_text=article_text,
                sentiment=derived_sentiment,
                themes=theme_labels,
            )

            articles.append(
                {
                    "symbol": symbol,
                    "title": title,
                    "summary": summary,
                    "source": source,
                    "url": url,
                    "published_at": published_at,
                    "provider": "marketaux",
                    "api_sentiment": api_sentiment,
                    "derived_sentiment": derived_sentiment,
                    "effective_sentiment": api_sentiment if api_sentiment is not None else derived_sentiment,
                    "article_text": article_text,
                    "article_text_len": len(article_text or ""),
                    "article_extraction_status": "success" if len(article_text or "") >= MIN_EXTRACTED_ARTICLE_LEN else "fallback",
                    "article_extraction_method": extraction_method,
                    "content_for_analysis": content_for_analysis,
                    "content_for_analysis_len": len(content_for_analysis or ""),
                    "theme_labels": ", ".join(theme_labels),
                    "signal_bucket": signal_bucket,
                    "signal_strength": signal_strength,
                    "signal_rationale": signal_rationale,
                }
            )

        rows.extend(_dedupe_articles(articles)[:max_articles])

    columns = [
        "symbol", "title", "summary", "source", "url", "published_at", "provider",
        "api_sentiment", "derived_sentiment", "effective_sentiment", "article_text",
        "article_text_len", "article_extraction_status", "article_extraction_method",
        "content_for_analysis", "content_for_analysis_len", "theme_labels",
        "signal_bucket", "signal_strength", "signal_rationale",
    ]
    if not rows:
        debug_df = pd.DataFrame(columns=columns)
        if errors:
            debug_df.attrs["fetch_errors"] = errors
        return debug_df

    df = pd.DataFrame(rows)
    if errors:
        df.attrs["fetch_errors"] = errors
    return df.sort_values(["symbol", "published_at"], ascending=[True, False]).reset_index(drop=True)


def summarize_news_by_ticker(news_df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "ticker", "article_count", "articles_with_full_text", "usable_news_count", "full_text_ratio",
        "avg_news_sentiment", "news_sentiment_label", "top_themes", "news_summary",
        "top_headlines", "article_records", "catalyst_positive_count",
        "catalyst_negative_count", "low_signal_noisy_count", "news_signal_score",
        "positioning_news_view", "positioning_news_rationale", "news_quality_score",
        "news_overlay_used", "news_data_status",
    ]
    if news_df is None or news_df.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for symbol, group in news_df.groupby("symbol", dropna=False):
        grp = group.copy()
        grp["effective_sentiment"] = pd.to_numeric(grp.get("effective_sentiment"), errors="coerce")
        grp["signal_strength"] = pd.to_numeric(grp.get("signal_strength"), errors="coerce")
        grp["article_text_len"] = pd.to_numeric(grp.get("article_text_len"), errors="coerce")
        grp["content_for_analysis_len"] = pd.to_numeric(grp.get("content_for_analysis_len"), errors="coerce")

        article_count = int(len(grp))
        full_text_mask = grp["article_text_len"].fillna(0) >= MIN_EXTRACTED_ARTICLE_LEN
        usable_mask = grp["content_for_analysis_len"].fillna(0) >= MIN_CONTENT_FOR_ANALYSIS_LEN
        extraction_success = int(full_text_mask.sum())
        usable_news_count = int(usable_mask.sum())
        full_text_ratio = round(float(extraction_success) / float(article_count), 4) if article_count else np.nan

        valid_sent = grp.loc[usable_mask, "effective_sentiment"].dropna()
        if valid_sent.empty:
            valid_sent = grp["effective_sentiment"].dropna()
        avg_sent = round(float(valid_sent.mean()), 4) if not valid_sent.empty else np.nan
        top_headlines = " | ".join(grp["title"].head(3).astype(str).tolist())

        theme_counter = Counter()
        signal_counter = Counter()
        bullets = []
        article_records = []

        for _, row in grp.head(6).iterrows():
            headline = str(row.get("title") or "").strip()
            source = str(row.get("source") or "").strip()
            content = str(row.get("content_for_analysis") or "").strip()
            for theme in [x.strip() for x in str(row.get("theme_labels") or "").split(",") if x.strip()]:
                theme_counter[theme] += 1
            signal_bucket = str(row.get("signal_bucket") or "")
            if signal_bucket:
                signal_counter[signal_bucket] += 1
            if headline:
                bullets.append(f"{headline} ({source})")
            article_records.append(
                {
                    "title": headline,
                    "source": source,
                    "published_at": str(row.get("published_at") or ""),
                    "url": str(row.get("url") or ""),
                    "sentiment": _safe_float(row.get("effective_sentiment"), 0.0),
                    "extraction_status": str(row.get("article_extraction_status") or ""),
                    "signal_bucket": signal_bucket,
                    "signal_strength": _safe_float(row.get("signal_strength"), 0.0),
                    "signal_rationale": str(row.get("signal_rationale") or ""),
                    "content_preview": content[:700],
                }
            )

        top_themes = ", ".join([theme for theme, _ in theme_counter.most_common(3)])
        pos_count = int(signal_counter.get("catalyst_positive", 0))
        neg_count = int(signal_counter.get("catalyst_negative", 0))
        noisy_count = int(signal_counter.get("low_signal_noisy", 0))

        if article_count > 0:
            raw_signal_score = pos_count * 1.0 - neg_count * 1.0 - noisy_count * 0.35
            signal_score = round(raw_signal_score / float(article_count), 4)
            news_quality_score = round(min(10.0, 10.0 * (0.65 * (usable_news_count / article_count) + 0.35 * (extraction_success / article_count))), 2)
        else:
            signal_score = np.nan
            news_quality_score = 0.0

        news_overlay_used = bool(article_count > 0 and usable_news_count > 0 and (pd.notna(avg_sent) or pd.notna(signal_score)))
        if article_count == 0:
            status = "no_recent_articles"
        elif usable_news_count == 0:
            status = "articles_found_but_not_usable"
        elif not news_overlay_used:
            status = "insufficient_signal"
        else:
            status = "usable"

        if not news_overlay_used:
            positioning_news_view = "No usable news"
            positioning_news_rationale = "Recent articles were not usable enough to influence the catalyst score, so news is excluded from scoring."
            summary_line = "No usable recent news ingested. News overlay excluded from scoring."
        else:
            if pos_count > neg_count and signal_score >= 0.15:
                positioning_news_view = "Supportive"
                positioning_news_rationale = "Catalyst-positive coverage outweighs negatives, so news modestly supports holding or adding on technical confirmation."
            elif neg_count > pos_count and signal_score <= -0.15:
                positioning_news_view = "Caution"
                positioning_news_rationale = "Catalyst-negative coverage dominates, so news argues for smaller sizing or tighter risk controls unless price action improves."
            else:
                positioning_news_view = "Neutral / Low Signal"
                positioning_news_rationale = "Coverage is mixed or noisy, so news should be treated as background context rather than a driver of positioning."

            summary_line = " ; ".join(bullets[:3])
            if top_themes:
                summary_line = f"Themes: {top_themes}. {summary_line}".strip()
            summary_line = (
                f"{positioning_news_view} news backdrop. "
                f"Catalyst+ {pos_count}, Catalyst- {neg_count}, Low-signal {noisy_count}. "
                f"{summary_line}"
            ).strip()

        rows.append(
            {
                "ticker": symbol,
                "article_count": article_count,
                "articles_with_full_text": extraction_success,
                "usable_news_count": usable_news_count,
                "full_text_ratio": full_text_ratio,
                "avg_news_sentiment": avg_sent,
                "news_sentiment_label": _sentiment_label(avg_sent) if pd.notna(avg_sent) else "no_usable_news",
                "top_themes": top_themes,
                "news_summary": summary_line,
                "top_headlines": top_headlines,
                "article_records": article_records,
                "catalyst_positive_count": pos_count,
                "catalyst_negative_count": neg_count,
                "low_signal_noisy_count": noisy_count,
                "news_signal_score": signal_score if news_overlay_used else np.nan,
                "positioning_news_view": positioning_news_view,
                "positioning_news_rationale": positioning_news_rationale,
                "news_quality_score": news_quality_score if news_overlay_used else 0.0,
                "news_overlay_used": news_overlay_used,
                "news_data_status": status,
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=columns)
    return out.sort_values(["news_overlay_used", "avg_news_sentiment", "article_count"], ascending=[False, False, False]).reset_index(drop=True)



def _safe_div(numerator: Any, denominator: Any) -> float | None:
    try:
        num = float(numerator)
        den = float(denominator)
        if den == 0:
            return None
        return num / den
    except Exception:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_company_stats(tickers: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for ticker in sorted({_normalize_symbol(t) for t in tickers if str(t).strip()}):
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception:
            info = {}
        rows.append(
            {
                "ticker": ticker,
                "average_volume": _safe_float(info.get("averageVolume")),
                "shares_outstanding": _safe_float(info.get("sharesOutstanding")),
                "last_price_yf": _safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
                "trailing_pe": _safe_float(info.get("trailingPE")),
                "peg_ratio": _safe_float(info.get("pegRatio")),
                "target_mean_price": _safe_float(info.get("targetMeanPrice")),
                "enterprise_to_revenue": _safe_float(info.get("enterpriseToRevenue")),
            }
        )
    return pd.DataFrame(rows)



def _ensure_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors='coerce')
    return out



def _coalesce_into(base: pd.DataFrame, target: str, candidates: list[str]) -> None:
    if target not in base.columns:
        base[target] = np.nan
    for candidate in candidates:
        if candidate in base.columns and candidate != target:
            base[target] = base[target].where(base[target].notna(), base[candidate])






INVALID_PEER_LABELS = {'', 'unknown', 'nan', 'none', 'n/a', 'na', 'equity', 'etf', 'fund'}

SECTOR_ALIASES = {
    'technology': 'Technology',
    'communication services': 'Communication Services',
    'communications': 'Communication Services',
    'financial services': 'Financial Services',
    'financial': 'Financial Services',
    'healthcare': 'Healthcare',
    'health care': 'Healthcare',
    'consumer defensive': 'Consumer Defensive',
    'consumer staples': 'Consumer Defensive',
    'consumer cyclical': 'Consumer Cyclical',
    'consumer discretionary': 'Consumer Cyclical',
    'industrial goods': 'Industrials',
    'industrials': 'Industrials',
    'basic materials': 'Materials',
    'materials': 'Materials',
    'real estate': 'Real Estate',
    'utilities': 'Utilities',
    'energy': 'Energy',
}

SECTOR_PEER_METRICS = {
    'Technology': {
        'fund_desc': ['revenue_cagr_3y', 'forward_revenue_growth', 'earnings_growth', 'operating_margin', 'fcf_margin', 'cash_conversion'],
        'fund_asc': ['debt_to_equity'],
        'val_desc': ['analyst_upside_pct', 'fcf_yield', 'earnings_yield'],
        'val_asc': ['forward_pe', 'forward_ps', 'price_to_sales', 'price_to_fcf'],
    },
    'Communication Services': {
        'fund_desc': ['revenue_cagr_3y', 'forward_revenue_growth', 'operating_margin', 'fcf_margin', 'return_on_equity'],
        'fund_asc': ['debt_to_equity'],
        'val_desc': ['analyst_upside_pct', 'fcf_yield', 'earnings_yield'],
        'val_asc': ['forward_pe', 'forward_ps', 'price_to_sales', 'price_to_fcf'],
    },
    'Financial Services': {
        'fund_desc': ['return_on_equity', 'return_on_assets', 'profit_margin', 'earnings_growth', 'rating_score'],
        'fund_asc': ['debt_to_equity'],
        'val_desc': ['analyst_upside_pct', 'earnings_yield'],
        'val_asc': ['forward_pe', 'trailing_pe', 'price_to_book'],
    },
    'Energy': {
        'fund_desc': ['fcf_margin', 'ocf_margin', 'return_on_equity', 'profit_margin', 'fcf_cagr_3y'],
        'fund_asc': ['debt_to_equity', 'liabilities_to_assets'],
        'val_desc': ['analyst_upside_pct', 'fcf_yield', 'earnings_yield'],
        'val_asc': ['forward_pe', 'price_to_sales', 'price_to_fcf'],
    },
    'Real Estate': {
        'fund_desc': ['fcf_margin', 'ocf_margin', 'cash_conversion', 'rating_score'],
        'fund_asc': ['debt_to_equity', 'liabilities_to_assets', 'price_to_book'],
        'val_desc': ['analyst_upside_pct', 'fcf_yield'],
        'val_asc': ['price_to_book', 'price_to_sales', 'price_to_fcf'],
    },
    'Healthcare': {
        'fund_desc': ['revenue_cagr_3y', 'earnings_growth', 'operating_margin', 'profit_margin', 'return_on_assets'],
        'fund_asc': ['debt_to_equity'],
        'val_desc': ['analyst_upside_pct', 'fcf_yield', 'earnings_yield'],
        'val_asc': ['forward_pe', 'forward_ps', 'price_to_sales', 'price_to_fcf'],
    },
    'default': {
        'fund_desc': ['revenue_cagr_3y', 'earnings_growth', 'operating_margin', 'return_on_equity', 'return_on_assets', 'fcf_margin'],
        'fund_asc': ['debt_to_equity', 'liabilities_to_assets'],
        'val_desc': ['analyst_upside_pct', 'fcf_yield', 'earnings_yield'],
        'val_asc': ['forward_pe', 'forward_ps', 'price_to_book', 'price_to_fcf'],
    },
}


def _clean_peer_label(value: Any) -> str:
    text = str(value or '').strip()
    return '' if text.lower() in INVALID_PEER_LABELS else text


def _canonical_sector(value: Any) -> str:
    text = _clean_peer_label(value)
    if not text:
        return 'Unknown'
    return SECTOR_ALIASES.get(text.lower(), text)


def _metric_profile_for_sector(sector: str) -> dict[str, list[str]]:
    canonical = _canonical_sector(sector)
    return SECTOR_PEER_METRICS.get(canonical, SECTOR_PEER_METRICS['default'])


def _existing_cols(out: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in out.columns]


def _peer_rank_desc(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors='coerce')
    if s.notna().sum() == 0:
        return pd.Series([np.nan] * len(series), index=series.index)
    return s.rank(ascending=False, method='min')


def _peer_rank_asc(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors='coerce')
    if s.notna().sum() == 0:
        return pd.Series([np.nan] * len(series), index=series.index)
    return s.rank(ascending=True, method='min')


def _rank_to_score(rank_series: pd.Series, valid_n: int) -> pd.Series:
    if valid_n <= 0:
        return pd.Series([np.nan] * len(rank_series), index=rank_series.index)
    if valid_n == 1:
        return pd.Series([10.0 if pd.notna(v) else np.nan for v in rank_series], index=rank_series.index)
    return 10 * (1 - ((rank_series - 1) / (valid_n - 1)))


def _pillar_peer_score(out: pd.DataFrame, desc_cols: list[str] | None = None, asc_cols: list[str] | None = None, mask: pd.Series | None = None) -> pd.Series:
    desc_cols = desc_cols or []
    asc_cols = asc_cols or []
    parts: list[pd.Series] = []
    if mask is None:
        mask = pd.Series(True, index=out.index)
    for col in _existing_cols(out, desc_cols):
        valid_n = int(pd.to_numeric(out.loc[mask, col], errors='coerce').notna().sum())
        if valid_n > 0:
            ranked = _rank_to_score(_peer_rank_desc(out.loc[mask, col]), valid_n)
            parts.append(ranked.reindex(out.index))
    for col in _existing_cols(out, asc_cols):
        valid_n = int(pd.to_numeric(out.loc[mask, col], errors='coerce').notna().sum())
        if valid_n > 0:
            ranked = _rank_to_score(_peer_rank_asc(out.loc[mask, col]), valid_n)
            parts.append(ranked.reindex(out.index))
    if not parts:
        return pd.Series(np.nan, index=out.index)
    return pd.concat(parts, axis=1).mean(axis=1, skipna=True)


def _peer_mask_for_row(out: pd.DataFrame, idx: Any, min_group_size: int = 3) -> tuple[pd.Series, str, str, int]:
    row = out.loc[idx]
    industry = _clean_peer_label(row.get('industry'))
    sector = _canonical_sector(row.get('sector'))

    industry_mask = pd.Series(False, index=out.index)
    sector_mask = pd.Series(False, index=out.index)

    if industry:
        industry_mask = out['industry_clean'].eq(industry)
    if sector and sector != 'Unknown':
        sector_mask = out['sector_clean'].eq(sector)

    industry_n = int(industry_mask.sum())
    sector_n = int(sector_mask.sum())

    if industry_n >= min_group_size:
        return industry_mask, 'industry', industry, industry_n
    if sector_n >= min_group_size:
        return sector_mask, 'sector_fallback', sector, sector_n
    return pd.Series(True, index=out.index), 'broad_fallback', 'All Analyzed Names', int(len(out))


def _peer_fallback_total(out: pd.DataFrame, mask: pd.Series) -> pd.Series:
    fallback_cols = [c for c in ['revenue_cagr_3y', 'forward_pe', 'ret_3m', 'price_vs_200dma', 'analyst_upside_pct', 'fcf_yield'] if c in out.columns]
    if not fallback_cols:
        return pd.Series(np.nan, index=out.index)
    fallback_parts = []
    for col in fallback_cols:
        subset = out.loc[mask, col]
        asc = col in {'forward_pe'}
        valid_n = int(pd.to_numeric(subset, errors='coerce').notna().sum())
        if valid_n <= 0:
            continue
        ranks = _peer_rank_asc(subset) if asc else _peer_rank_desc(subset)
        fallback_parts.append(_rank_to_score(ranks, valid_n).reindex(out.index))
    if not fallback_parts:
        return pd.Series(np.nan, index=out.index)
    return pd.concat(fallback_parts, axis=1).mean(axis=1, skipna=True)


def _peer_reliability_score(group_type: str, peer_count: int, metric_count: int) -> float:
    group_type = str(group_type or '').lower()
    if 'industry' in group_type:
        group_base = 0.88
    elif 'sector' in group_type:
        group_base = 0.66
    else:
        group_base = 0.36
    if peer_count >= 12:
        count_score = 1.00
    elif peer_count >= 8:
        count_score = 0.84
    elif peer_count >= 5:
        count_score = 0.68
    elif peer_count >= 3:
        count_score = 0.50
    else:
        count_score = 0.25
    metric_score = min(1.0, max(0.0, float(metric_count) / 5.0))
    reliability = 0.55 * group_base + 0.30 * count_score + 0.15 * metric_score
    return float(np.clip(reliability, 0.15, 1.0))


def _peer_confidence_label(reliability: float) -> str:
    if reliability >= 0.78:
        return 'high'
    if reliability >= 0.55:
        return 'medium'
    return 'low'


def _add_peer_relative_fields(base: pd.DataFrame, comparison_mode: bool = False, min_group_size: int = 3) -> pd.DataFrame:
    out = base.copy()
    if out.empty:
        return out

    for col, default in [
        ('sector_clean', ''),
        ('industry_clean', ''),
        ('peer_group_type', ''),
        ('peer_group_name', ''),
        ('peer_count', 0),
        ('peer_fundamental_score', np.nan),
        ('peer_valuation_score', np.nan),
        ('peer_technical_score', np.nan),
        ('peer_news_score', np.nan),
        ('peer_total_score', np.nan),
        ('peer_rank_overall', np.nan),
        ('peer_percentile_overall', np.nan),
        ('peer_news_rank', np.nan),
        ('peer_metric_count', 0),
        ('peer_reliability', np.nan),
        ('peer_confidence', ''),
        ('peer_fallback_used', False),
        ('peer_min_count_pass', False),
        ('peer_metrics_used', ''),
        ('peer_missing_core_metrics', ''),
        ('peer_comparison_note', ''),
    ]:
        out[col] = default

    if 'sector' not in out.columns:
        out['sector'] = 'Unknown'
    if 'industry' not in out.columns:
        out['industry'] = 'Unknown'

    out['sector'] = out['sector'].fillna('Unknown').astype(str).str.strip().replace('', 'Unknown')
    out['industry'] = out['industry'].fillna('Unknown').astype(str).str.strip().replace('', 'Unknown')
    out['sector_clean'] = out['sector'].map(_canonical_sector)
    out['industry_clean'] = out['industry'].map(_clean_peer_label).replace('', 'Unknown')

    if not comparison_mode or len(out) < 2:
        return out

    usable_news_mask = out.get('news_overlay_used', pd.Series(False, index=out.index)).fillna(False).astype(bool)

    for idx in out.index:
        peer_mask, group_type, group_name, peer_count = _peer_mask_for_row(out, idx, min_group_size=min_group_size)
        sector = out.at[idx, 'sector_clean']
        profile = _metric_profile_for_sector(sector)

        fund_desc = _existing_cols(out, profile.get('fund_desc', []))
        fund_asc = _existing_cols(out, profile.get('fund_asc', []))
        val_desc = _existing_cols(out, profile.get('val_desc', []))
        val_asc = _existing_cols(out, profile.get('val_asc', []))
        tech_desc = _existing_cols(out, ['ret_3m', 'ret_1y', 'price_vs_50dma', 'price_vs_200dma', 'rel_3m_vs_benchmark'])
        tech_asc = _existing_cols(out, ['ann_vol_3m', 'max_drawdown_1y'])
        news_desc = _existing_cols(out, ['avg_news_sentiment', 'news_signal_score', 'news_quality_score'])

        out.at[idx, 'peer_group_type'] = group_type
        out.at[idx, 'peer_group_name'] = group_name
        out.at[idx, 'peer_count'] = peer_count
        out.at[idx, 'peer_fallback_used'] = group_type != 'industry'
        out.at[idx, 'peer_min_count_pass'] = peer_count >= min_group_size

        fund_scores = _pillar_peer_score(out, desc_cols=fund_desc, asc_cols=fund_asc, mask=peer_mask)
        val_scores = _pillar_peer_score(out, desc_cols=val_desc, asc_cols=val_asc, mask=peer_mask)
        tech_scores = _pillar_peer_score(out, desc_cols=tech_desc, asc_cols=tech_asc, mask=peer_mask)

        group_news_mask = peer_mask & usable_news_mask
        news_scores = _pillar_peer_score(out, desc_cols=news_desc, mask=group_news_mask)
        if not bool(usable_news_mask.loc[idx]):
            news_scores.loc[idx] = np.nan

        out.at[idx, 'peer_fundamental_score'] = fund_scores.loc[idx]
        out.at[idx, 'peer_valuation_score'] = val_scores.loc[idx]
        out.at[idx, 'peer_technical_score'] = tech_scores.loc[idx]
        out.at[idx, 'peer_news_score'] = news_scores.loc[idx]

        metric_values = [fund_scores.loc[idx], val_scores.loc[idx], tech_scores.loc[idx], news_scores.loc[idx]]
        valid_metric_values = [v for v in metric_values if pd.notna(v)]
        out.at[idx, 'peer_metric_count'] = len(valid_metric_values)
        peer_reliability = _peer_reliability_score(group_type, peer_count, len(valid_metric_values))
        out.at[idx, 'peer_reliability'] = peer_reliability
        out.at[idx, 'peer_confidence'] = _peer_confidence_label(peer_reliability)

        total_score = float(pd.Series(valid_metric_values).mean()) if valid_metric_values else np.nan
        if pd.isna(total_score):
            fallback_total = _peer_fallback_total(out, peer_mask)
            total_score = fallback_total.loc[idx]
        out.at[idx, 'peer_total_score'] = total_score

        group_total_scores = pd.Series(np.nan, index=out.index, dtype='float64')
        group_total_scores.loc[peer_mask] = pd.concat([fund_scores.loc[peer_mask], val_scores.loc[peer_mask], tech_scores.loc[peer_mask], news_scores.loc[peer_mask]], axis=1).mean(axis=1, skipna=True)

        if bool(group_total_scores.loc[peer_mask].isna().any()):
            fallback_total = _peer_fallback_total(out, peer_mask)
            fill_mask = peer_mask & group_total_scores.isna()
            group_total_scores.loc[fill_mask] = fallback_total.loc[fill_mask]

        valid_group_scores = pd.to_numeric(group_total_scores.loc[peer_mask], errors='coerce')
        valid_n = int(valid_group_scores.notna().sum())
        if valid_n > 0 and pd.notna(group_total_scores.loc[idx]):
            group_ranks = _peer_rank_desc(group_total_scores.loc[peer_mask])
            row_rank = group_ranks.loc[idx]
            out.at[idx, 'peer_rank_overall'] = row_rank
            out.at[idx, 'peer_percentile_overall'] = 1 - ((row_rank - 1) / (valid_n - 1)) if valid_n > 1 else 1.0

        valid_news_n = int(pd.to_numeric(news_scores.loc[group_news_mask], errors='coerce').notna().sum())
        if valid_news_n > 0 and bool(group_news_mask.loc[idx]) and pd.notna(news_scores.loc[idx]):
            news_ranks = _peer_rank_desc(news_scores.loc[group_news_mask])
            out.at[idx, 'peer_news_rank'] = news_ranks.loc[idx]

        metric_names = fund_desc + fund_asc + val_desc + val_asc + tech_desc + tech_asc + news_desc
        out.at[idx, 'peer_metrics_used'] = ', '.join(dict.fromkeys(metric_names))
        core = set(profile.get('fund_desc', [])[:3] + profile.get('val_asc', [])[:2])
        missing = [c for c in core if c not in out.columns or pd.isna(out.at[idx, c])]
        out.at[idx, 'peer_missing_core_metrics'] = ', '.join(missing)
        out.at[idx, 'peer_comparison_note'] = f"Compared against {peer_count} {group_type.replace('_', ' ')} peers in {group_name}; confidence {out.at[idx, 'peer_confidence']}."

    return out
def build_multi_agent_dataset(
    tickers: list[str],
    prices: pd.DataFrame,
    company_info: dict[str, dict[str, Any]],
    benchmark_col: str,
    news_summary: pd.DataFrame | None = None,
    position_snapshot: pd.DataFrame | None = None,
    fmp_api_key: str = '',
    comparison_mode: bool = False,
) -> pd.DataFrame:
    from langgraphagenticai.portfolio_manager.analytics import build_asset_feature_table

    asset_features = build_asset_feature_table(
        prices,
        company_info=company_info,
        benchmark_col=benchmark_col,
        news_summary=news_summary,
    )
    research = build_research_snapshot(tickers, fmp_api_key) if fmp_api_key else pd.DataFrame({'ticker': tickers})
    fmp_snapshot = fetch_fmp_fundamental_snapshots(tickers, fmp_api_key) if fmp_api_key else pd.DataFrame({'ticker': tickers})
    stats = fetch_company_stats(tickers)

    base = asset_features.merge(research, on='ticker', how='left', suffixes=('', '_report'))
    base = base.merge(fmp_snapshot, on='ticker', how='left', suffixes=('', '_fmp'))
    base = base.merge(stats, on='ticker', how='left', suffixes=('', '_yf'))

    numeric_candidates = [
        'market_cap', 'beta', 'last_price', 'ret_1m', 'ret_3m', 'ret_6m', 'ret_12m', 'ret_1y',
        'relative_strength_3m', 'rel_3m_vs_benchmark', 'price_vs_50dma', 'price_vs_200dma',
        'rsi_14', 'macd', 'macd_signal', 'macd_hist', 'atr_14', 'ann_vol_3m', 'realized_vol_20d',
        'drawdown_from_52w_high', 'distance_from_52w_low', 'max_drawdown_1y', 'volume_vs_20d_avg',
        'revenue_cagr_3y', 'net_income_cagr_3y', 'fcf_cagr_3y', 'revenue_growth', 'earnings_growth',
        'gross_margin', 'operating_margin', 'profit_margin', 'ebitda_margin', 'ocf_margin', 'fcf_margin',
        'operating_cashflow_margin', 'free_cashflow_margin', 'cash_conversion', 'return_on_equity',
        'return_on_assets', 'current_ratio', 'debt_to_equity', 'liabilities_to_assets', 'forward_revenue_growth',
        'forward_eps_growth', 'forward_pe', 'forward_ps', 'trailing_pe', 'price_to_book', 'price_to_sales',
        'price_to_fcf', 'enterprise_to_ebitda', 'price_target_consensus', 'analyst_upside_pct',
        'rating_score', 'earnings_yield', 'fcf_yield', 'target_mean_price', 'enterprise_to_revenue',
    ]
    base = _ensure_numeric(base, numeric_candidates)

    for target in ['sector', 'industry', 'market_cap', 'beta', 'last_price']:
        _coalesce_into(base, target, [f'{target}_report', f'{target}_fmp', f'{target}_yf'])

    _coalesce_into(base, 'ret_1y', ['ret_1y', 'ret_12m'])
    _coalesce_into(base, 'rel_3m_vs_benchmark', ['rel_3m_vs_benchmark', 'relative_strength_3m'])
    _coalesce_into(base, 'ann_vol_3m', ['ann_vol_3m', 'realized_vol_20d'])
    _coalesce_into(base, 'max_drawdown_1y', ['max_drawdown_1y', 'drawdown_from_52w_high'])
    _coalesce_into(base, 'ocf_margin', ['ocf_margin', 'operating_cashflow_margin', 'OCF Margin'])
    _coalesce_into(base, 'fcf_margin', ['fcf_margin', 'free_cashflow_margin', 'FCF Margin'])
    _coalesce_into(base, 'cash_conversion', ['cash_conversion', 'Cash Conversion'])
    _coalesce_into(base, 'earnings_yield', ['earnings_yield'])
    _coalesce_into(base, 'fcf_yield', ['fcf_yield'])
    _coalesce_into(base, 'price_to_fcf', ['price_to_fcf'])
    _coalesce_into(base, 'revenue_growth', ['revenue_growth', 'forward_revenue_growth'])
    _coalesce_into(base, 'earnings_growth', ['earnings_growth', 'forward_eps_growth'])
    _coalesce_into(base, 'operating_margin', ['operating_margin', 'Latest Operating Margin'])
    _coalesce_into(base, 'analyst_upside_pct', ['analyst_upside_pct', 'Price Target Upside'])

    if 'earnings_yield' in base.columns and 'trailing_pe' in base.columns:
        base['earnings_yield'] = base['earnings_yield'].where(base['earnings_yield'].notna(), 1 / base['trailing_pe'].replace(0, np.nan))
    if 'fcf_yield' in base.columns and 'price_to_fcf' in base.columns:
        base['fcf_yield'] = base['fcf_yield'].where(base['fcf_yield'].notna(), 1 / base['price_to_fcf'].replace(0, np.nan))

    if position_snapshot is not None and not position_snapshot.empty:
        pos_cols = [c for c in ['ticker', 'shares', 'market_value', 'current_weight'] if c in position_snapshot.columns]
        base = base.merge(position_snapshot[pos_cols], on='ticker', how='left')
    else:
        base['shares'] = 0.0
        base['market_value'] = 0.0
        base['current_weight'] = 0.0

    for c in ['article_count', 'articles_with_full_text', 'usable_news_count', 'full_text_ratio', 'avg_news_sentiment', 'news_signal_score', 'news_quality_score']:
        if c not in base.columns:
            base[c] = np.nan
    if 'news_overlay_used' not in base.columns:
        base['news_overlay_used'] = False
    if 'news_data_status' not in base.columns:
        base['news_data_status'] = ''

    completeness_cols = ['ret_3m', 'price_vs_200dma', 'rsi_14', 'market_cap', 'revenue_cagr_3y', 'forward_pe', 'forward_ps']
    for c in completeness_cols:
        if c not in base.columns:
            base[c] = np.nan
    base['data_completeness'] = base[completeness_cols].notna().mean(axis=1)
    base = _add_peer_relative_fields(base, comparison_mode=comparison_mode)

    # Data quality is a transparent confidence input used by the lead PM and rebalance engine.
    # It prevents high-conviction recommendations when fundamentals, estimates, peer data, or
    # full-text news are thin.
    quality_base_cols = [
        c for c in [
            'last_price', 'market_cap', 'ret_3m', 'price_vs_200dma', 'rsi_14',
            'ann_vol_3m', 'max_drawdown_1y', 'revenue_cagr_3y', 'operating_margin',
            'profit_margin', 'return_on_equity', 'debt_to_equity', 'forward_pe',
            'forward_ps', 'analyst_upside_pct', 'fcf_yield'
        ] if c in base.columns
    ]
    if quality_base_cols:
        base['data_quality_score'] = base[quality_base_cols].notna().mean(axis=1).astype(float)
    else:
        base['data_quality_score'] = base.get('data_completeness', 0.0)

    if 'usable_news_count' in base.columns:
        news_bonus = pd.to_numeric(base['usable_news_count'], errors='coerce').fillna(0).clip(lower=0, upper=3) / 3 * 0.04
        base['data_quality_score'] = base['data_quality_score'] + news_bonus
    if 'peer_reliability' in base.columns:
        peer_bonus = pd.to_numeric(base['peer_reliability'], errors='coerce').fillna(0).clip(lower=0, upper=1) * 0.06
        base['data_quality_score'] = base['data_quality_score'] + peer_bonus

    base['data_quality_score'] = pd.to_numeric(base['data_quality_score'], errors='coerce').fillna(0.0).clip(lower=0.0, upper=1.0)
    base['data_quality_label'] = np.select(
        [base['data_quality_score'] >= 0.78, base['data_quality_score'] >= 0.55],
        ['high', 'medium'],
        default='low',
    )
    return base
