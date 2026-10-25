"""Retain distinct provider previews without presenting them as full articles."""
from langgraphagenticai.providers.article_text import normalize_article_body


def preview(item):
    parts = []
    for key in ("description", "snippet", "text"):
        text = str(item.get(key) or "").strip()
        if text and text not in parts:
            parts.append(text)
    for entity in item.get("entities", []) or []:
        if isinstance(entity, dict):
            for highlight in entity.get("highlights", []) or []:
                if isinstance(highlight, dict):
                    text = normalize_article_body(highlight.get("highlight"))["article_text"]
                    if text and text not in parts:
                        parts.append(text)
    return "\n".join(parts)[:3500]
