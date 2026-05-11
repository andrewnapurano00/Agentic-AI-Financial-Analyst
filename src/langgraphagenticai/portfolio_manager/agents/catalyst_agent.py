from __future__ import annotations

import pandas as pd

from langgraphagenticai.portfolio_manager.schemas import CatalystResult
from langgraphagenticai.portfolio_manager.scoring import clip_score, pct_to_score, weighted_average


def _is_valid_number(x) -> bool:
    return x is not None and not pd.isna(x)


def run_catalyst_agent(ticker: str, data: dict) -> CatalystResult:
    avg_sent = data.get("avg_news_sentiment")
    signal = data.get("news_signal_score")
    article_count = data.get("article_count")
    full_text_ratio = data.get("full_text_ratio")
    news_quality_score = data.get("news_quality_score", 0.0)
    usable_news_count = data.get("usable_news_count")
    overlay_used = bool(data.get("news_overlay_used", False))
    news_status = str(data.get("news_data_status") or "")
    peer_news_score = data.get("peer_news_score")
    peer_news_rank = data.get("peer_news_rank")
    pos = data.get("catalyst_positive_count", 0)
    neg = data.get("catalyst_negative_count", 0)
    noisy = data.get("low_signal_noisy_count", 0)
    summary_text = str(data.get("news_summary") or "").strip()

    usable_news_count = 0 if usable_news_count is None or pd.isna(usable_news_count) else int(usable_news_count)
    article_count = 0 if article_count is None or pd.isna(article_count) else int(article_count)
    low_count_penalty = 0.0 if usable_news_count >= 3 else (0.6 if usable_news_count == 2 else 1.0 if usable_news_count == 1 else 1.4)
    has_usable_news = bool(article_count > 0 and overlay_used and (_is_valid_number(avg_sent) or _is_valid_number(signal)))

    if has_usable_news:
        base_score = weighted_average([
            (pct_to_score(avg_sent, -1.0, 1.0), 0.28),
            (pct_to_score(signal, -1.0, 1.0), 0.30),
            (pct_to_score(usable_news_count, 0, 6), 0.14),
            (pct_to_score(full_text_ratio, 0.0, 1.0), 0.10),
            (pct_to_score(news_quality_score, 0, 10), 0.18),
        ])
        if _is_valid_number(peer_news_score):
            base_score = weighted_average([(base_score, 0.82), (clip_score(peer_news_score), 0.18)])
        score = clip_score(base_score - low_count_penalty)
    else:
        score = 5.0

    if not has_usable_news:
        sentiment = "neutral"
        catalyst_view = "no_usable_news"
        signal_meaning = "News signal is unavailable, so catalysts are treated as neutral rather than predictive."
    elif neg > pos and neg >= noisy:
        sentiment = "negative"
        catalyst_view = "headwind"
        signal_meaning = "Recent coverage leans negative enough to act as a tactical headwind."
    elif pos > neg and pos >= noisy:
        sentiment = "positive"
        catalyst_view = "supportive"
        signal_meaning = "Recent coverage contains supportive catalysts rather than just positive tone."
    else:
        sentiment = "neutral"
        catalyst_view = "mixed"
        signal_meaning = "Recent coverage is mixed or too noisy to materially change the base case."

    summary = []
    risks = []
    if has_usable_news and summary_text:
        summary.append(summary_text)
    elif not has_usable_news:
        summary.append("No usable recent news was ingested, so the overlay is excluded from materially affecting the score.")

    if has_usable_news and pos > 0:
        summary.append(f"Recent coverage includes {int(pos)} catalyst-positive items.")
    if has_usable_news and neg > 0:
        risks.append(f"Recent coverage includes {int(neg)} catalyst-negative items.")
    if has_usable_news and usable_news_count < 2:
        risks.append("The news sample is small, so the catalyst signal carries lower confidence.")
    if has_usable_news and noisy > max(pos, neg):
        risks.append("Much of the recent flow is low-signal and should not override the core thesis.")
    if not has_usable_news and news_status:
        risks.append(f"News data status: {news_status.replace('_', ' ')}.")

    return CatalystResult(
        thesis=("supportive" if score >= 6.2 else "cautious" if score <= 4.3 else "neutral"),
        conviction=("high" if has_usable_news and usable_news_count >= 3 else "medium" if has_usable_news else "low"),
        evidence_for=summary[:3],
        evidence_against=risks[:3],
        action_preference=("Buy" if score >= 6.8 else "Hold" if score >= 4.8 else "Watchlist"),
        challenge_points=["Separate genuine catalysts from low-signal article flow before increasing position size."],
        data_gaps=[] if has_usable_news else ["Usable recent news coverage is limited."],
        ticker=ticker,
        score=score,
        verdict=sentiment,
        sentiment=sentiment,
        catalyst_view=catalyst_view,
        summary=summary[:3],
        risks=risks[:3],
        metrics={
            "catalyst_signal_meaning": signal_meaning,
            "news_overlay_used": overlay_used,
            "news_data_status": news_status,
            "avg_news_sentiment": avg_sent if has_usable_news else None,
            "news_signal_score": signal if has_usable_news else None,
            "article_count": article_count,
            "full_text_ratio": full_text_ratio if has_usable_news else None,
            "news_quality_score": news_quality_score if has_usable_news else 0.0,
            "usable_news_count": usable_news_count,
            "peer_news_score": peer_news_score if has_usable_news else None,
            "peer_news_rank": peer_news_rank if has_usable_news else None,
            "catalyst_positive_count": pos,
            "catalyst_negative_count": neg,
            "low_signal_noisy_count": noisy,
        },
    )
