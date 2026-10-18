"""Saved, explicit-action news summary; ordinary reruns never call a model."""
import streamlit as st
from langgraphagenticai.analysis.market_news_ai import news_evidence, summarize_news, NEWS_VERSION
from langgraphagenticai.utils.safety import sanitize_error, redact_sensitive_text
from langgraphagenticai.providers.article_text import safe_news_url


def render_news_summary(news, api_key="", model="gpt-5"):
    st.subheader("Market news & sentiment")
    evidence = news_evidence(news)
    body_count = sum(bool(a.get("article_text")) for a in evidence["articles"])
    st.caption(f"Available coverage: {len(evidence['articles'])} stories · {body_count} with provider article text · {len(evidence['articles'])-body_count} headline/snippet only. Article completeness is unverified; long bodies may be abbreviated.")
    if st.button("Generate / refresh news briefing", key="market_news_summarize", disabled=not api_key.strip() or not evidence["articles"]):
        try:
            with st.spinner("Synthesizing available headlines across news sources..."):
                st.session_state.market_news_summary = summarize_news(news, api_key, model)
        except Exception as exc:
            st.warning("News summary unavailable; previous summary preserved. " + sanitize_error(exc))
    saved = st.session_state.get("market_news_summary")
    if saved:
        if saved["evidence"]["fingerprint"] != evidence["fingerprint"] or saved["model"] != model:
            st.warning("Saved news summary uses earlier evidence or model settings. Generate again to update it.")
        st.caption(f"AI interpretation · saved news retrieved {saved['evidence'].get('retrieved_at') or 'Unknown'}. Source references are checked; prose meaning is not independently verified.")
        sources = {a["id"]: a for a in saved["evidence"]["articles"]}
        result = saved["result"]
        def source_links(ids):
            for evidence_id in dict.fromkeys(ids):
                article = sources.get(evidence_id, {})
                url = safe_news_url(article.get("url"))
                if url:
                    basis = article.get("content_basis") or "Headline/snippet only"
                    st.link_button(f"[{evidence_id}] {article['title']}", url)
                    st.caption(basis + (" · Abbreviated" if article.get("content_truncated") else ""))
        if saved["evidence"].get("version") != NEWS_VERSION or not result.get("sentiment"):
            st.info("Previously saved headline summary. Generate the updated briefing for top stories, broader-market implications and cited news tone.")
        else:
            st.markdown("**News tone · " + result["sentiment"].upper() + "**")
            st.caption("Qualitative AI assessment of this coverage, not a measured investor-sentiment index or return forecast.")
            st.text(redact_sensitive_text(result["overview"]))
            st.text(redact_sensitive_text(result["sentiment_reason"]))
            with st.expander("Sources behind the news tone"):
                source_links(result["sentiment_evidence_ids"])
        for claim in saved["result"]["claims"]:
            st.text("• " + redact_sensitive_text(claim["interpretation"]))
            if claim.get("market_implication"):
                st.text("Market relevance: " + redact_sensitive_text(claim["market_implication"]))
            with st.expander("Story sources: " + ", ".join(claim["evidence_ids"])):
                source_links(claim["evidence_ids"])
        st.caption(redact_sensitive_text(saved["result"]["limitations"]))
    else:
        st.info("Generate a top-stories briefing: what happened, why it may matter for the broader market, and the tone of the available coverage. Uses saved article text where available and clearly labels preview-only sources. One explicit model request; reruns reuse the result.")
