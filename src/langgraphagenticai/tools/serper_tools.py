"""Serper news/search with bounded requests and source metadata."""
from __future__ import annotations

import requests

from langgraphagenticai.deep_research.models import safe_url, utc_now


class SerperClient:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip()

    def search(self, query: str, *, news: bool = True, days: int = 30, limit: int = 5) -> dict:
        if not self.api_key:
            return {"ok": False, "error": "SERPER_API_KEY is not configured.", "results": []}
        endpoint = "news" if news else "search"
        payload = {"q": query[:500], "num": min(max(limit, 1), 10), "gl": "us", "hl": "en"}
        if news:
            payload["tbs"] = f"qdr:d{min(max(days, 1), 90)}"
        try:
            response = requests.post(
                f"https://google.serper.dev/{endpoint}", json=payload,
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                timeout=(5, 25),
            )
            if response.status_code != 200:
                return {"ok": False, "error": f"Serper returned HTTP {response.status_code}. Check the key, credits, or rate limit.", "results": []}
            raw = response.json()
            if not isinstance(raw, dict) or raw.get("error"):
                return {"ok": False, "error": "Serper returned an invalid result.", "results": []}
            collection = "news" if news else "organic"
            if collection not in raw:
                return {"ok": False, "error": f"Serper response is missing the expected {collection} result collection.", "results": []}
            items = raw[collection]
            if not isinstance(items, list):
                return {"ok": False, "error": "Serper returned an invalid result collection.", "results": []}
            rows, seen = [], set()
            for item in items:
                if not isinstance(item, dict):
                    continue
                url = safe_url(item.get("link"))
                if not url or url in seen:
                    continue
                seen.add(url)
                rows.append({
                    "title": str(item.get("title") or "Untitled")[:500], "url": url,
                    "snippet": str(item.get("snippet") or "")[:2000],
                    "published": str(item.get("date") or "Date not supplied"),
                    "publisher": str(item.get("source") or ""),
                })
                if len(rows) >= limit:
                    break
            return {"ok": bool(rows), "results": rows, "query": query, "retrieved_at": utc_now(),
                    "error": "" if rows else "Serper returned results, but none had usable safe source links." if items else "No matching search results returned."}
        except requests.exceptions.SSLError:
            return {"ok": False, "error": "Serper HTTPS certificate verification failed. Configure a trusted CA bundle for this Python environment.", "results": []}
        except (requests.RequestException, ValueError):
            return {"ok": False, "error": "Serper request failed or timed out. Try again later.", "results": []}
