from __future__ import annotations

import json
import re
from typing import Any

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


def _client(openai_api_key: str):
    if not openai_api_key or OpenAI is None:
        return None
    return OpenAI(api_key=openai_api_key)


def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\u200b", "")
    text = text.replace("\xa0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _call_llm(payload: dict[str, Any], openai_api_key: str, model_name: str) -> str:
    client = _client(openai_api_key)
    if client is None:
        return "AI features are disabled. Add OPENAI_API_KEY to use AI commentary and Q&A."

    try:
        response = client.responses.create(
            model=model_name,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a portfolio strategist. "
                        "Respond in clean plain text only. "
                        "Do not use markdown tables, bold text, unusual symbols, unicode bullets, or decorative formatting. "
                        "Use short section headers and standard hyphen bullets only. "
                        "Keep numbers on one line and avoid fragmented spacing. "
                        "Be practical, data-driven, and concise. "
                        "News sentiment is intentionally excluded from the Portfolio Manager context. "
                        "Only use the supplied structured context."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, indent=2, default=str),
                },
            ],
        )
        return _clean_text(getattr(response, "output_text", None) or "No response returned.")
    except Exception as exc:
        return f"AI request failed: {exc}"


def build_portfolio_manager_note(
    regime_info: dict[str, Any],
    diagnostics: dict[str, Any],
    cross_asset_leaders: list[dict[str, Any]],
    sector_ranks: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    portfolio_news: list[dict[str, Any]],
    openai_api_key: str,
    model_name: str,
) -> str:
    payload = {
        "task": (
            "Write an investment committee style allocation memo in clean plain text. "
            "Use this exact structure:\n"
            "1. Executive Summary\n"
            "2. Macro Regime\n"
            "3. Cross-Asset Leaders\n"
            "4. Sector Winners and Losers\n"
            "5. Agent Agreement and Conflicts\n"
            "6. Portfolio Risks\n"
            "7. Top Recommended Trades\n"
            "8. Implementation Risks\n"
            "9. Bottom Line\n"
            "Use simple sentences and hyphen bullets only. "
            "Explain where the specialist agents agree or conflict."
        ),
        "regime_info": regime_info,
        "diagnostics": diagnostics,
        "cross_asset_leaders": cross_asset_leaders[:12],
        "sector_ranks": sector_ranks[:11],
        "top_recommendations": recommendations[:12],
        "portfolio_news": [],
    }
    return _call_llm(payload, openai_api_key, model_name)


def answer_portfolio_question(
    question: str,
    regime_info: dict[str, Any],
    diagnostics: dict[str, Any],
    cross_asset_leaders: list[dict[str, Any]],
    sector_ranks: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    portfolio_news: list[dict[str, Any]],
    openai_api_key: str,
    model_name: str,
) -> str:
    payload = {
        "task": (
            "Answer the user's portfolio question using only the supplied context. "
            "Respond in clean plain text. "
            "Use short paragraphs and simple hyphen bullets when helpful. "
            "Discuss technicals, macro regime, sector leadership, valuation, forward outlook, and risk where relevant. "
            "Do not reference news because it is intentionally excluded from this workflow."
        ),
        "question": question,
        "regime_info": regime_info,
        "diagnostics": diagnostics,
        "cross_asset_leaders": cross_asset_leaders[:12],
        "sector_ranks": sector_ranks[:11],
        "recommendations": recommendations[:20],
        "portfolio_news": [],
    }
    return _call_llm(payload, openai_api_key, model_name)


def build_ticker_news_brief(
    ticker: str,
    news_row: dict[str, Any],
    openai_api_key: str,
    model_name: str,
) -> str:
    payload = {
        "task": (
            "News summaries are disabled for the AI Portfolio Manager. "
            "Return a short note saying this workflow excludes news and relies on the agent scorecard. "
            "Use plain text only."
        ),
        "ticker": ticker,
        "news_context": news_row,
    }
    return _call_llm(payload, openai_api_key, model_name)

def build_ticker_decision_explainer(
    ticker: str,
    sector: str,
    current_weight: float,
    final_action: str,
    openai_api_key: str,
    model_name: str,
    industry: str | None = None,
    action_bias: str | None = None,
    why: list[str] | None = None,
    risks: list[str] | None = None,
    next_steps: list[str] | None = None,
    composite_score: float | None = None,
    sub_scores: dict[str, Any] | None = None,
    strengths: list[str] | None = None,
) -> str:
    strengths = strengths or why or []
    why = why or strengths or []
    risks = risks or []
    next_steps = next_steps or []
    sub_scores = sub_scores or {}

    payload = {
        "task": (
            "Write a concise portfolio-manager memo for a single stock. "
            "Use this structure: Decision, Why It Works, Risks, Portfolio Context, Next Step. "
            "Reflect cross-agent agreement or disagreement when relevant. "
            "Use plain text only and keep it under 180 words."
        ),
        "ticker": ticker,
        "sector": sector,
        "industry": industry,
        "current_weight": current_weight,
        "final_action": final_action,
        "action_bias": action_bias,
        "composite_score": composite_score,
        "sub_scores": sub_scores,
        "strengths": strengths,
        "why": why,
        "risks": risks,
        "next_steps": next_steps,
    }
    return _call_llm(payload, openai_api_key, model_name)


def build_multi_agent_portfolio_note(
    portfolio_summary: dict[str, Any],
    recommendation_table: list[dict[str, Any]],
    add_candidates: list[dict[str, Any]],
    trim_candidates: list[dict[str, Any]],
    sell_candidates: list[dict[str, Any]],
    openai_api_key: str,
    model_name: str,
) -> str:
    payload = {
        "task": (
            "Write an investment committee note for the multi-agent portfolio manager. "
            "Use this structure: Executive Summary, Best Adds, Holds, Trims or Sells, Biggest Risks, Bottom Line. "
            "Mention where fundamentals, valuation, forward outlook, technicals, risk, portfolio fit, and capital policy agree or conflict."
        ),
        "portfolio_summary": portfolio_summary,
        "recommendation_table": recommendation_table[:20],
        "add_candidates": add_candidates[:10],
        "trim_candidates": trim_candidates[:10],
        "sell_candidates": sell_candidates[:10],
    }
    return _call_llm(payload, openai_api_key, model_name)


def answer_multi_agent_portfolio_question(
    question: str,
    portfolio_summary: dict[str, Any],
    recommendation_table: list[dict[str, Any]],
    ticker_bundles: dict[str, Any],
    openai_api_key: str,
    model_name: str,
) -> str:
    payload = {
        "task": (
            "Answer the user's question using the multi-agent portfolio manager output only. "
            "Use plain text, short paragraphs, and direct recommendations."
        ),
        "question": question,
        "portfolio_summary": portfolio_summary,
        "recommendation_table": recommendation_table[:25],
        "ticker_bundles": ticker_bundles,
    }
    return _call_llm(payload, openai_api_key, model_name)
