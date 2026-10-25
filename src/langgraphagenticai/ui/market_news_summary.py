"""Saved, explicit-action news summary; ordinary reruns never call a model."""
import streamlit as st
from langgraphagenticai.analysis.market_news_ai import news_evidence, summarize_news, NEWS_VERSION
from langgraphagenticai.utils.safety import sanitize_error, redact_sensitive_text
from langgraphagenticai.analysis.executive_text import executive_text


def render_news_summary(news, api_key="", model="gpt-5"):
    st.subheader("Market news & sentiment")
    evidence = news_evidence(news)
    if st.button("Generate / refresh news briefing", key="market_news_summarize", disabled=not api_key.strip() or not evidence["articles"]):
        try:
            with st.spinner("Preparing your executive market briefing..."):
                st.session_state.market_news_summary = summarize_news(news, api_key, model)
        except Exception as exc:
            retained = " Your saved briefing is unchanged." if st.session_state.get("market_news_summary") else ""
            st.warning("News briefing unavailable." + retained + " " + sanitize_error(exc))
    saved = st.session_state.get("market_news_summary")
    if saved:
        if saved["evidence"]["fingerprint"] != evidence["fingerprint"] or saved["model"] != model:
            st.warning("Saved news summary uses earlier evidence or model settings. Generate again to update it.")
        st.caption(f"AI interpretation · saved news retrieved {saved['evidence'].get('retrieved_at') or 'Unknown'}. ")
        result = saved["result"]
        if saved["evidence"].get("version") != NEWS_VERSION or not result.get("sentiment"):
            st.info("Previously saved briefing. Generate the updated executive summary for connected market drivers and crosscurrents.")
        else:
            st.caption("AI news tone: " + result["sentiment"].upper() + " - qualitative interpretation, not a measured sentiment index.")
        with st.container(border=True):
            st.markdown(executive_text(result.get("overview", "")))
    else:
        st.info("Generate an executive synthesis of the main market drivers, crosscurrents and what to watch. Refresh market evidence first to update the coverage; ordinary reruns reuse the saved briefing.")

    with st.expander("Briefing evidence & coverage", expanded=False):
        st.caption("News retrieved: " + str(evidence.get("retrieved_at") or "Unknown"))
        body_count = sum(bool(a.get("article_text")) for a in evidence["articles"])
        st.caption(f"{len(evidence['articles'])} stories retained for analysis; {body_count} with provider article text. Completeness is unverified.")
        if news.get("coverage"):
            st.json(news["coverage"])
        for warning in news.get("warnings", []):
            st.caption(redact_sensitive_text(warning))
        result = saved["result"] if saved else {}
        st.caption(executive_text(result.get("limitations", "")))
        if result.get("sentiment_reason"):
            st.text(executive_text(result["sentiment_reason"]))
        for claim in result.get("claims", []):
            st.text(executive_text(claim["interpretation"]))
            if claim.get("market_implication"):
                st.text(executive_text(claim["market_implication"]))
