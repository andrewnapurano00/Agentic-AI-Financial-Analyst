from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests
from langchain_core.tools import StructuredTool

from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient


def build_news_tools(fmp_api_key: str):
    def _make_tool(func):
        return StructuredTool.from_function(
            func=func,
            name=func.__name__,
            description=(func.__doc__ or "").strip(),
        )

    """
    Builds finance news tools using:
    - FMP MCP as the primary source
    - Finnhub REST API as the secondary / fallback source

    Environment variable expected:
    - FINNHUB_API_KEY
    """
    client = FMPMCPClient(fmp_api_key)
    finnhub_api_key = os.getenv("FINNHUB_API_KEY", "").strip()

    # ---------------------------
    # Internal helpers
    # ---------------------------

    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _safe_json_dumps(payload: Dict[str, Any]) -> str:
        return json.dumps(payload, indent=2, ensure_ascii=False, default=str)

    def _extract_payload_data(payload: Any) -> List[Dict[str, Any]]:
        """
        Supports both:
        - old/raw payloads from MCP
        - normalized dict payloads with {"ok":..., "data":[...]}
        """
        if payload is None:
            return []

        if isinstance(payload, dict):
            if "data" in payload and isinstance(payload["data"], list):
                return payload["data"]
            if "data" in payload and isinstance(payload["data"], dict):
                return [payload["data"]]
            if "data" in payload and payload["data"] is None:
                return []
            return [payload]

        if isinstance(payload, list):
            return payload

        return []

    def _normalize_text(text: Optional[str]) -> str:
        return " ".join((text or "").strip().lower().split())

    def _parse_date_to_iso(value: Any) -> str:
        if value is None:
            return ""

        # unix timestamp
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
            except Exception:
                return ""

        text = str(value).strip()
        if not text:
            return ""

        # try common formats
        candidates = [
            text,
            text.replace("Z", "+00:00"),
            text.replace(" UTC", ""),
        ]

        for candidate in candidates:
            try:
                dt = datetime.fromisoformat(candidate)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).isoformat()
            except Exception:
                pass

        # try basic date only
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(text[:19], fmt).replace(tzinfo=timezone.utc)
                return dt.isoformat()
            except Exception:
                pass

        return text

    def _safe_get(url: str, params: Dict[str, Any], timeout: int = 20) -> Any:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def _normalize_fmp_articles(symbol: str, payload: Any) -> List[Dict[str, Any]]:
        rows = _extract_payload_data(payload)
        articles: List[Dict[str, Any]] = []

        for item in rows:
            if not isinstance(item, dict):
                continue

            title = item.get("title") or item.get("headline") or ""
            source = item.get("site") or item.get("source") or item.get("publisher") or "FMP"
            published_at = (
                item.get("publishedDate")
                or item.get("date")
                or item.get("published_at")
                or item.get("datetime")
            )
            url = item.get("url") or item.get("link") or ""
            summary = item.get("text") or item.get("content") or item.get("summary") or ""

            articles.append(
                {
                    "provider": "fmp",
                    "symbol": symbol.upper(),
                    "title": str(title).strip(),
                    "source": str(source).strip(),
                    "published_at": _parse_date_to_iso(published_at),
                    "url": str(url).strip(),
                    "summary": str(summary).strip(),
                    "category": "company-news",
                }
            )

        return articles

    def _fetch_finnhub_company_news(symbol: str, lookback_days: int = 7) -> List[Dict[str, Any]]:
        if not finnhub_api_key:
            return []

        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=max(1, int(lookback_days)))

        url = "https://finnhub.io/api/v1/company-news"
        params = {
            "symbol": symbol.upper(),
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "token": finnhub_api_key,
        }

        try:
            payload = _safe_get(url, params=params, timeout=20)
        except Exception:
            return []

        articles: List[Dict[str, Any]] = []
        if not isinstance(payload, list):
            return articles

        for item in payload:
            if not isinstance(item, dict):
                continue

            published_at = _parse_date_to_iso(item.get("datetime"))
            title = item.get("headline") or ""
            source = item.get("source") or "Finnhub"
            url = item.get("url") or ""
            summary = item.get("summary") or ""

            articles.append(
                {
                    "provider": "finnhub",
                    "symbol": symbol.upper(),
                    "title": str(title).strip(),
                    "source": str(source).strip(),
                    "published_at": published_at,
                    "url": str(url).strip(),
                    "summary": str(summary).strip(),
                    "category": item.get("category") or "company-news",
                }
            )

        return articles

    def _fetch_finnhub_market_news(category: str = "general", limit: int = 10) -> List[Dict[str, Any]]:
        if not finnhub_api_key:
            return []

        url = "https://finnhub.io/api/v1/news"
        params = {
            "category": category,
            "token": finnhub_api_key,
        }

        try:
            payload = _safe_get(url, params=params, timeout=20)
        except Exception:
            return []

        articles: List[Dict[str, Any]] = []
        if not isinstance(payload, list):
            return articles

        for item in payload[: max(1, int(limit))]:
            if not isinstance(item, dict):
                continue

            articles.append(
                {
                    "provider": "finnhub",
                    "symbol": None,
                    "title": str(item.get("headline") or "").strip(),
                    "source": str(item.get("source") or "Finnhub").strip(),
                    "published_at": _parse_date_to_iso(item.get("datetime")),
                    "url": str(item.get("url") or "").strip(),
                    "summary": str(item.get("summary") or "").strip(),
                    "category": item.get("category") or category,
                }
            )

        return articles

    def _dedupe_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        deduped: List[Dict[str, Any]] = []

        for article in articles:
            title_key = _normalize_text(article.get("title"))
            url_key = _normalize_text(article.get("url"))
            date_key = str(article.get("published_at", ""))[:10]

            key = url_key if url_key else f"{title_key}|{date_key}"
            if not key.strip("|"):
                continue

            if key in seen:
                continue

            seen.add(key)
            deduped.append(article)

        return deduped

    def _days_old(iso_str: str) -> Optional[float]:
        if not iso_str:
            return None
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return max(0.0, (now - dt.astimezone(timezone.utc)).total_seconds() / 86400.0)
        except Exception:
            return None

    def _score_article(article: Dict[str, Any], symbol: str) -> float:
        """
        Lightweight relevance score for ranking.
        """
        score = 0.0
        title = (article.get("title") or "").upper()
        summary = (article.get("summary") or "").upper()
        source = (article.get("source") or "").lower()
        provider = (article.get("provider") or "").lower()

        if symbol.upper() in title:
            score += 0.45
        if symbol.upper() in summary:
            score += 0.20

        high_quality_sources = {
            "reuters", "bloomberg", "cnbc", "marketwatch", "wsj", "yahoo", "associated press", "ap"
        }
        if any(src in source for src in high_quality_sources):
            score += 0.20

        if provider == "fmp":
            score += 0.05
        if provider == "finnhub":
            score += 0.05

        age_days = _days_old(article.get("published_at", ""))
        if age_days is not None:
            if age_days <= 1:
                score += 0.20
            elif age_days <= 3:
                score += 0.12
            elif age_days <= 7:
                score += 0.06

        keywords = [
            "earnings", "guidance", "revenue", "profit", "margin",
            "acquisition", "merger", "buyback", "dividend", "lawsuit",
            "regulation", "ai", "chip", "cloud", "forecast"
        ]
        joined = f"{title} {summary}".lower()
        if any(word in joined for word in keywords):
            score += 0.10

        return round(score, 4)

    def _make_news_summary(symbol: str, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not articles:
            return {
                "symbol": symbol.upper(),
                "article_count": 0,
                "top_themes": [],
                "source_mix": {},
                "note": "No recent articles found from FMP or Finnhub.",
            }

        source_mix: Dict[str, int] = {}
        theme_counter = {
            "earnings": 0,
            "guidance": 0,
            "product_ai": 0,
            "analyst": 0,
            "macro_regulatory": 0,
            "m_and_a": 0,
        }

        for article in articles:
            source = article.get("source") or "Unknown"
            source_mix[source] = source_mix.get(source, 0) + 1

            text = f"{article.get('title', '')} {article.get('summary', '')}".lower()

            if "earnings" in text or "quarter" in text or "q1" in text or "q2" in text or "q3" in text or "q4" in text:
                theme_counter["earnings"] += 1
            if "guidance" in text or "forecast" in text or "outlook" in text:
                theme_counter["guidance"] += 1
            if "product" in text or "ai" in text or "chip" in text or "cloud" in text:
                theme_counter["product_ai"] += 1
            if "analyst" in text or "rating" in text or "price target" in text or "upgrade" in text or "downgrade" in text:
                theme_counter["analyst"] += 1
            if "fed" in text or "regulation" in text or "regulatory" in text or "lawsuit" in text:
                theme_counter["macro_regulatory"] += 1
            if "acquisition" in text or "merger" in text or "buyout" in text:
                theme_counter["m_and_a"] += 1

        top_themes = [k for k, v in sorted(theme_counter.items(), key=lambda x: x[1], reverse=True) if v > 0][:3]

        return {
            "symbol": symbol.upper(),
            "article_count": len(articles),
            "top_themes": top_themes,
            "source_mix": source_mix,
        }

    # ---------------------------
    # Tools exposed to LangChain
    # ---------------------------

    def get_recent_company_news(symbol: str, lookback_days: int = 7, max_articles: int = 10) -> str:
        """
        Get recent company news for a ticker using both FMP and Finnhub,
        then deduplicate, rank, and return a structured JSON payload.
        """
        symbol = symbol.upper().strip()
        max_articles = max(1, min(int(max_articles), 25))
        lookback_days = max(1, min(int(lookback_days), 30))

        fmp_payload = client.stock_news(symbol, limit=max_articles)
        fmp_articles = _normalize_fmp_articles(symbol, fmp_payload)
        finnhub_articles = _fetch_finnhub_company_news(symbol, lookback_days=lookback_days)

        articles = _dedupe_articles(fmp_articles + finnhub_articles)

        for article in articles:
            article["relevance_score"] = _score_article(article, symbol)

        articles = sorted(
            articles,
            key=lambda x: (x.get("relevance_score", 0), x.get("published_at", "")),
            reverse=True,
        )[:max_articles]

        payload = {
            "ok": True,
            "tool": "get_recent_company_news",
            "symbol": symbol,
            "as_of": _utc_now_iso(),
            "lookback_days": lookback_days,
            "providers_used": {
                "fmp": len(fmp_articles),
                "finnhub": len(finnhub_articles),
            },
            "article_count": len(articles),
            "summary": _make_news_summary(symbol, articles),
            "articles": articles,
        }
        return _safe_json_dumps(payload)

    def get_market_news(category: str = "general", max_articles: int = 10) -> str:
        """
        Get broad market news from Finnhub categories such as:
        general, forex, crypto, merger.
        """
        max_articles = max(1, min(int(max_articles), 25))
        category = (category or "general").strip().lower()

        articles = _fetch_finnhub_market_news(category=category, limit=max_articles)

        payload = {
            "ok": True,
            "tool": "get_market_news",
            "category": category,
            "as_of": _utc_now_iso(),
            "provider": "finnhub",
            "article_count": len(articles),
            "articles": articles[:max_articles],
        }
        return _safe_json_dumps(payload)

    return [
        _make_tool(get_recent_company_news),
        _make_tool(get_market_news),
    ]