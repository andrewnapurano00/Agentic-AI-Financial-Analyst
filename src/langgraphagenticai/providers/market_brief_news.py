"""Bounded thematic market-news collection; no article scraping or model calls."""
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import requests
import streamlit as st
import truststore
from langgraphagenticai.tools.serper_tools import SerperClient
from langgraphagenticai.providers.news_content import preview
from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.providers.article_text import normalize_article_body, safe_news_url

NEWS_LIMIT = 50
SERPER_QUERIES = (
    "US stock market outlook sector rotation earnings",
    "US Federal Reserve interest rates inflation jobs economic growth markets",
    "global markets Treasury yields dollar oil geopolitical risk US stocks",
)

# Keep certificate verification enabled while honoring the OS trusted roots.
truststore.inject_into_ssl()


def merge_news(rows):
    merged, titles = {}, {}
    for row in rows:
        url = safe_news_url(row.get("url"))
        if not url:
            continue
        parts = urlsplit(url)
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid", "msclkid"}]
        key = urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), urlencode(sorted(query)), ""))
        title = " ".join(str(row.get("title", "")).lower().split())
        key = titles.get(title, key) if title else key
        if key in merged:
            previous = merged[key]
            previous["providers"] = sorted(set(previous["providers"] + row["providers"]))
            if len(row.get("snippet") or "") > len(previous.get("snippet") or ""):
                previous["snippet"] = row["snippet"]
            for field in ("published", "publisher"):
                if not previous.get(field) and row.get(field):
                    previous[field] = row[field]
            if len(row.get("article_text") or "") > len(previous.get("article_text") or ""):
                for field in ("article_text", "content_basis", "content_truncated", "content_source", "content_retrieved_at"):
                    previous[field] = row.get(field)
        else:
            merged[key] = {k: v for k, v in {**row, "url": url}.items() if k != "sentiment"}
            if title:
                titles[title] = key
    return list(merged.values())[:NEWS_LIMIT]


@st.cache_data(ttl=600, show_spinner=False)
def load_market_news(serper_api_key="", marketaux_api_key="", fmp_api_key=""):
    now = datetime.now(timezone.utc)
    rows, warnings = [], []
    if serper_api_key.strip():
        for query in SERPER_QUERIES:
            try:
                result = SerperClient(serper_api_key).search(query, days=2, limit=10)
            except Exception:
                result = {"ok": False, "error": "Market headlines unavailable; other provider results preserved."}
            if not result.get("ok"):
                # Provider diagnostics are kept outside executive prose.
                warnings.append("Serper: " + str(result.get("error") or "Market search unavailable."))
            for item in result.get("results", []):
                if not isinstance(item, dict):
                    continue
                rows.append({"title": str(item.get("title") or "Untitled")[:500], "url": item.get("url"), "snippet": item.get("snippet", ""),
                             "published": item.get("published"), "publisher": item.get("publisher"), "providers": ["Serper"]})
    else:
        warnings.append("Configure Serper for search-based market headlines.")
    if marketaux_api_key.strip():
        try:
            response = requests.get("https://api.marketaux.com/v1/news/all", params={"api_token": marketaux_api_key,
                "language": "en", "countries": "us", "limit": 3, "group_similar": "true",
                "published_after": (now-timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")}, timeout=(5,25))
            if response.status_code != 200:
                warnings.append(f"Marketaux returned HTTP {response.status_code}. Check the API plan, quota and request parameters.")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise ValueError("Invalid market news envelope")
            for item in payload["data"]:
                if not isinstance(item, dict):
                    continue
                rows.append({"title": str(item.get("title") or "Untitled")[:500], "url": item.get("url"),
                    "snippet": preview(item),
                    "published": item.get("published_at"), "publisher": item.get("source"), "providers": ["Marketaux"]})
        except requests.exceptions.SSLError:
            warnings.append("Marketaux HTTPS certificate verification failed. Restart the app with OS trust-store support installed, or configure a trusted CA bundle.")
        except (requests.RequestException, ValueError, TypeError):
            warnings.append("Marketaux market news unavailable; other provider results preserved.")
    else:
        warnings.append("Configure Marketaux for market headlines.")
    if fmp_api_key.strip():
        try:
            items = get_fmp_json("https://financialmodelingprep.com/stable/news/general-latest",
                                 api_key=fmp_api_key, params={"page": 0, "limit": 10}, timeout=(5, 20))
            if not isinstance(items, list):
                raise ValueError("Invalid FMP news response")
            for item in items[:10]:
                if isinstance(item, dict):
                    rows.append({"title": str(item.get("title") or "Untitled")[:500], "url": item.get("url"),
                                 "snippet": str(item.get("text") or item.get("content") or "")[:2000],
                                 "published": item.get("publishedDate"), "publisher": item.get("site") or item.get("publisher"),
                                 "providers": ["FMP"]})
        except Exception:
            warnings.append("FMP general news unavailable; other provider results preserved. Check news entitlement or refresh to retry.")
        try:
            articles = get_fmp_json("https://financialmodelingprep.com/stable/fmp-articles",
                                    api_key=fmp_api_key, params={"page": 0, "limit": 5}, timeout=(5, 20))
            if not isinstance(articles, list):
                raise ValueError("Invalid FMP article response")
            for item in articles[:5]:
                if isinstance(item, dict):
                    body = normalize_article_body(item.get("content"))
                    rows.append({"title": str(item.get("title") or "Untitled")[:500],
                                 "url": item.get("link") or item.get("url"),
                                 "snippet": body["article_text"][:500], **body,
                                 "content_source": "FMP Articles API", "content_retrieved_at": now.isoformat(),
                                 "published": item.get("date"), "publisher": item.get("site") or "Financial Modeling Prep",
                                 "providers": ["FMP"]})
        except Exception:
            warnings.append("FMP article bodies unavailable; headline/snippet coverage retained. Full publisher articles are not inferred from previews.")
    else:
        warnings.append("Configure FMP for general market headlines.")
    articles = merge_news(rows)
    configured = {"Serper":bool(serper_api_key.strip()), "Marketaux":bool(marketaux_api_key.strip()), "FMP":bool(fmp_api_key.strip())}
    coverage = {provider:{"configured":enabled,
                         "returned_rows":sum(provider in row.get("providers", []) for row in rows),
                         "retained_stories":sum(provider in row.get("providers", []) for row in articles)}
                for provider,enabled in configured.items()}
    return {"articles": articles, "warnings": list(dict.fromkeys(warnings)), "retrieved_at": now.isoformat(),
            "coverage":coverage, "collection_policy":{"lookback_days_requested":2, "serper_searches":len(SERPER_QUERIES) if serper_api_key.strip() else 0,
                "story_cap":NEWS_LIMIT, "rows_before_merge":len(rows), "retained_stories":len(articles),
                "note":"Bounded samples, not all market news. Requested search lookback is not verified publication timing; FMP latest routes may include older stories."}}
