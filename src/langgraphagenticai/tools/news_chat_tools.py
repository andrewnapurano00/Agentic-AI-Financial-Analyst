from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

import pandas as pd
from langchain_core.tools import StructuredTool
from openai import OpenAI

from langgraphagenticai.tools.news_pipeline_tools import (
    compute_news_window,
    ensure_list,
    run_news_pipeline,
)


OPENAI_MODEL = "gpt-5-mini"
MAX_ARTICLES_PER_TICKER = 8
MAX_CHARS_PER_ARTICLE = 1500
MAX_TOTAL_CHARS = 14000


def normalize_ticker(ticker: str) -> str:
    return (ticker or "").strip().upper()


def clean_text(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def safe_str_contains(series: pd.Series, pattern: str) -> pd.Series:
    return series.fillna("").astype(str).str.contains(pattern, case=False, regex=True, na=False)


def build_article_blurb(row: pd.Series, text_col: str = "content_for_analysis") -> str:
    title = clean_text(row.get("title_clean", row.get("title", "")))
    source = clean_text(row.get("source", ""))
    published_at = clean_text(row.get("published_at", ""))
    text = clean_text(row.get(text_col, ""))

    if len(text) > MAX_CHARS_PER_ARTICLE:
        text = text[:MAX_CHARS_PER_ARTICLE].rsplit(" ", 1)[0] + "..."

    parts = []
    if title:
        parts.append(f"Title: {title}")
    if source:
        parts.append(f"Source: {source}")
    if published_at:
        parts.append(f"Published: {published_at}")
    if text:
        parts.append(f"Content: {text}")
    return "\n".join(parts).strip()


def score_article_relevance(row: pd.Series, ticker: str) -> float:
    ticker = normalize_ticker(ticker)
    title = clean_text(row.get("title_clean", row.get("title", "")))
    desc = clean_text(row.get("description_clean", row.get("description", "")))
    snippet = clean_text(row.get("snippet_clean", row.get("snippet", "")))
    article = clean_text(row.get("article_text_clean", row.get("article_text", "")))
    entity_symbols = clean_text(row.get("entity_symbols", ""))

    score = 0.0
    if ticker in entity_symbols.upper():
        score += 10
    if ticker in title.upper():
        score += 6
    if ticker in snippet.upper():
        score += 4
    if ticker in desc.upper():
        score += 3
    if ticker in article.upper():
        score += 2

    ems = row.get("entity_match_score_avg", None)
    try:
        if ems is not None and not pd.isna(ems):
            score += float(ems) / 50.0
    except Exception:
        pass

    article_len = row.get("article_text_clean_len", row.get("article_text_len", 0))
    try:
        if article_len is not None and not pd.isna(article_len):
            score += min(float(article_len), 3000) / 3000.0
    except Exception:
        pass

    return score


def filter_articles_for_ticker(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    ticker = normalize_ticker(ticker)
    mask = pd.Series(False, index=df.index)

    if "search_tickers" in df.columns:
        mask = mask | safe_str_contains(df["search_tickers"], rf"\b{re.escape(ticker)}\b")
    if "entity_symbols" in df.columns:
        mask = mask | safe_str_contains(df["entity_symbols"], rf"\b{re.escape(ticker)}\b")

    text_cols = [
        c
        for c in [
            "title",
            "title_clean",
            "description",
            "description_clean",
            "snippet",
            "snippet_clean",
            "article_text",
            "article_text_clean",
            "content_for_analysis",
        ]
        if c in df.columns
    ]
    for c in text_cols:
        mask = mask | safe_str_contains(df[c], rf"\b{re.escape(ticker)}\b")

    return df.loc[mask].copy()


def build_combined_prompt(ticker: str, articles_df: pd.DataFrame, text_col: str = "content_for_analysis") -> str:
    article_blurbs = []
    running_chars = 0

    for _, row in articles_df.iterrows():
        blurb = build_article_blurb(row, text_col=text_col)
        if not blurb:
            continue
        if running_chars + len(blurb) > MAX_TOTAL_CHARS:
            break
        article_blurbs.append(blurb)
        running_chars += len(blurb)

    joined_articles = "\n\n--- ARTICLE ---\n\n".join(article_blurbs)

    return f"""
You are summarizing recent news for stock ticker {ticker}.

Task:
- Produce ONE combined summary for {ticker}, not separate article summaries.
- Keep it concise: 2 to 4 sentences.
- Focus on repeated themes, key catalysts, risks, and changes in tone.
- Ignore macro commentary unless it directly affects {ticker}.
- Do not use bullet points.
- Do not mention article titles or sources.

Articles:
{joined_articles}
""".strip()


def build_news_context_for_qa(
    df: pd.DataFrame,
    ticker: str,
    max_articles: int = MAX_ARTICLES_PER_TICKER,
    max_chars_per_article: int = 1500,
    max_total_chars: int = 14000,
) -> str:
    if df.empty:
        return ""

    work = filter_articles_for_ticker(df, ticker)
    if work.empty:
        return ""

    work = work.copy()
    if "published_at" in work.columns:
        work["published_at"] = pd.to_datetime(work["published_at"], errors="coerce")
        work = work.sort_values("published_at", ascending=False)

    selected_chunks = []
    running_chars = 0

    for _, row in work.head(max_articles).iterrows():
        title = clean_text(row.get("title_clean", row.get("title", "")))
        source = clean_text(row.get("source", ""))
        published = clean_text(row.get("published_at", ""))
        content = clean_text(
            row.get("article_text_clean")
            or row.get("content_for_analysis")
            or row.get("article_text")
            or row.get("snippet_clean")
            or row.get("snippet")
            or row.get("description_clean")
            or row.get("description")
        )
        if len(content) > max_chars_per_article:
            content = content[:max_chars_per_article].rsplit(" ", 1)[0] + "..."

        chunk = f"Title: {title}\nSource: {source}\nPublished: {published}\nContent: {content}".strip()
        if running_chars + len(chunk) > max_total_chars:
            break

        selected_chunks.append(chunk)
        running_chars += len(chunk)

    return "\n\n--- ARTICLE ---\n\n".join(selected_chunks)


def build_marketaux_news_chat_tools(openai_api_key: Optional[str] = None, marketaux_api_key: Optional[str] = None):
    def _make_tool(func):
        return StructuredTool.from_function(
            func=func,
            name=func.__name__,
            description=(func.__doc__ or "").strip(),
        )

    openai_api_key = (openai_api_key or os.getenv("OPENAI_API_KEY") or "").strip()
    marketaux_api_key = (marketaux_api_key or os.getenv("MARKETAUX_API_KEY") or "").strip()
    dataset_cache: Dict[str, pd.DataFrame] = {}

    def _safe_json_dumps(payload: Dict[str, Any]) -> str:
        return json.dumps(payload, indent=2, ensure_ascii=False, default=str)

    def _error_payload(tool_name: str, message: str, **extra) -> str:
        payload: Dict[str, Any] = {"ok": False, "tool": tool_name, "error": message}
        payload.update(extra)
        return _safe_json_dumps(payload)

    def _cache_key(symbols: List[str], days_back: int, limit: int, max_pages: int, dedupe: bool, search: str) -> str:
        return json.dumps(
            {
                "symbols": sorted(symbols),
                "days_back": int(days_back),
                "limit": int(limit),
                "max_pages": int(max_pages),
                "dedupe": bool(dedupe),
                "search": search or "",
            },
            sort_keys=True,
        )

    def _load_df(symbols: List[str], days_back: int, limit: int, max_pages: int, dedupe: bool, search: str) -> pd.DataFrame:
        key = _cache_key(symbols, days_back, limit, max_pages, dedupe, search)
        if key in dataset_cache:
            return dataset_cache[key].copy()

        published_after, published_before = compute_news_window(days_back)
        df = run_news_pipeline(
            search_tickers=symbols,
            marketaux_api_key=marketaux_api_key,
            published_after=published_after,
            published_before=published_before,
            limit=limit,
            max_pages=max_pages,
            dedupe=dedupe,
            search=search or None,
            debug=False,
        )
        dataset_cache[key] = df.copy()
        return df

    def _client() -> OpenAI:
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is missing. Add it in the sidebar or environment before using news summary / QA tools.")
        return OpenAI(api_key=openai_api_key)

    def summarize_marketaux_news(
        symbols: str,
        days_back: int = 7,
        limit: int = 20,
        max_pages: int = 2,
        dedupe: bool = True,
        search: str = "",
        model: str = OPENAI_MODEL,
    ) -> str:
        """
        Generate a concise combined news summary for one or more tickers using cleaned Marketaux article context.
        symbols can be a comma-separated string like 'MSFT,NVDA'.
        """
        tickers = ensure_list(symbols)

        if not marketaux_api_key:
            return _error_payload("summarize_marketaux_news", "MARKETAUX_API_KEY is missing. Add it in the sidebar or environment.", symbols=tickers)
        if not tickers:
            return _error_payload("summarize_marketaux_news", "At least one ticker symbol is required.")

        try:
            df = _load_df(
                tickers,
                max(1, min(int(days_back), 30)),
                max(5, min(int(limit), 50)),
                max(1, min(int(max_pages), 5)),
                bool(dedupe),
                (search or "").strip(),
            )
            if df.empty:
                return _error_payload("summarize_marketaux_news", "No processed news articles were found.", symbols=tickers)

            client = _client()
            results = []

            for ticker in tickers:
                df_t = filter_articles_for_ticker(df, ticker)
                if df_t.empty:
                    results.append(
                        {
                            "target_ticker": ticker,
                            "article_count_used": 0,
                            "combined_summary_gpt": "",
                            "status": "no_articles_found",
                            "error": f"No articles found for {ticker}",
                        }
                    )
                    continue

                df_t = df_t.copy()
                df_t["relevance_score"] = df_t.apply(lambda r: score_article_relevance(r, ticker), axis=1)

                if "published_at" in df_t.columns:
                    df_t["published_at_sort"] = pd.to_datetime(df_t["published_at"], errors="coerce")
                    df_t = df_t.sort_values(by=["relevance_score", "published_at_sort"], ascending=[False, False])
                else:
                    df_t = df_t.sort_values(by="relevance_score", ascending=False)

                df_top = df_t.head(MAX_ARTICLES_PER_TICKER).copy()
                prompt = build_combined_prompt(ticker, df_top, text_col="content_for_analysis")

                try:
                    resp = client.responses.create(model=model, input=prompt)
                    summary_text = getattr(resp, "output_text", "") or ""
                    summary_text = clean_text(summary_text)

                    results.append(
                        {
                            "target_ticker": ticker,
                            "article_count_used": int(len(df_top)),
                            "combined_summary_gpt": summary_text,
                            "status": "ok",
                            "error": "",
                        }
                    )
                except Exception as exc:
                    results.append(
                        {
                            "target_ticker": ticker,
                            "article_count_used": int(len(df_top)),
                            "combined_summary_gpt": "",
                            "status": "error",
                            "error": str(exc),
                        }
                    )

            return _safe_json_dumps(
                {
                    "ok": True,
                    "tool": "summarize_marketaux_news",
                    "symbols": tickers,
                    "results": results,
                }
            )

        except Exception as exc:
            return _error_payload("summarize_marketaux_news", str(exc), symbols=tickers)

    def answer_question_about_marketaux_news(
        symbols: str,
        question: str,
        days_back: int = 7,
        limit: int = 20,
        max_pages: int = 2,
        dedupe: bool = True,
        search: str = "",
        model: str = OPENAI_MODEL,
    ) -> str:
        """
        Answer a specific question about recent company news for one or more tickers.
        Use this for questions about sentiment, risks, catalysts, comparisons, and headline interpretation.
        """
        tickers = ensure_list(symbols)
        question = clean_text(question)

        if not marketaux_api_key:
            return _error_payload("answer_question_about_marketaux_news", "MARKETAUX_API_KEY is missing. Add it in the sidebar or environment.", symbols=tickers)
        if not tickers:
            return _error_payload("answer_question_about_marketaux_news", "At least one ticker symbol is required.")
        if not question:
            return _error_payload("answer_question_about_marketaux_news", "A question is required.", symbols=tickers)

        try:
            df = _load_df(
                tickers,
                max(1, min(int(days_back), 30)),
                max(5, min(int(limit), 50)),
                max(1, min(int(max_pages), 5)),
                bool(dedupe),
                (search or "").strip(),
            )
            if df.empty:
                return _error_payload("answer_question_about_marketaux_news", "No processed news articles were found.", symbols=tickers)

            client = _client()
            contexts = []

            for ticker in tickers:
                context = build_news_context_for_qa(df, ticker)
                if context:
                    contexts.append(f"Ticker: {ticker}\n{context}")

            if not contexts:
                return _error_payload("answer_question_about_marketaux_news", "No usable article context was found for the requested ticker(s).", symbols=tickers)

            joined_context = "\n\n====================\n\n".join(contexts)
            prompt = f"""
You are answering a question about recent company news.

Question:
{question}

Context:
{joined_context}

Instructions:
- Answer directly and clearly.
- Focus only on what is supported by the provided articles.
- If comparing companies, keep the comparison balanced.
- Keep the answer concise but informative.
- If evidence is mixed, say so.
- Do not mention article titles unless necessary.
""".strip()

            resp = client.responses.create(model=model, input=prompt)
            answer_text = clean_text(getattr(resp, "output_text", "") or "")

            return _safe_json_dumps(
                {
                    "ok": True,
                    "tool": "answer_question_about_marketaux_news",
                    "symbols": tickers,
                    "question": question,
                    "answer": answer_text,
                }
            )

        except Exception as exc:
            return _error_payload("answer_question_about_marketaux_news", str(exc), symbols=tickers, question=question)

    return [
            _make_tool(summarize_marketaux_news),
            _make_tool(answer_question_about_marketaux_news),
        ]