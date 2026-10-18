"""Normalize provider-supplied article HTML without fetching publisher pages."""
from html.parser import HTMLParser
from urllib.parse import urlsplit, parse_qsl
from langgraphagenticai.deep_research.models import safe_url
from langgraphagenticai.utils.safety import redact_sensitive_text

MAX_ARTICLE_CHARS = 10000


def safe_news_url(value):
    url = safe_url(value)
    if not url:
        return ""
    forbidden = {"apikey", "api_key", "api-key", "api_token", "token", "access_token", "key", "password", "secret"}
    return "" if any(key.lower() in forbidden for key, _ in parse_qsl(urlsplit(url).query)) else url


class _ArticleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def normalize_article_body(value):
    parser = _ArticleText()
    parser.feed(str(value or "")[:200000])
    text = redact_sensitive_text(" ".join(" ".join(parser.parts).split()))
    return {"article_text": text[:MAX_ARTICLE_CHARS],
            "content_basis": "Provider article body; completeness unverified" if text else "Headline/snippet only",
            "content_truncated": len(text) > MAX_ARTICLE_CHARS or len(str(value or "")) > 200000}
