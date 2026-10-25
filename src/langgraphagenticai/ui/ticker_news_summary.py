"""Explicit company-news collection and AI action, with independent saved results."""
from datetime import datetime,timezone,timedelta
from hashlib import sha256
import json
import re
import streamlit as st
from langgraphagenticai.providers.ticker_news import load_ticker_news
from langgraphagenticai.analysis.ticker_news_ai import ticker_evidence,summarize_ticker_news
from langgraphagenticai.deep_research.executive import executive_prose
from langgraphagenticai.providers.article_text import safe_news_url
from langgraphagenticai.state.research_context import normalize_company_symbol
from langgraphagenticai.utils.safety import sanitize_error,redact_sensitive_text


from langgraphagenticai.analysis.executive_text import executive_text as news_text


def render_ticker_news_summary(symbol,company,*,fmp_api_key="",serper_api_key="",marketaux_api_key="",openai_api_key="",model_name="gpt-5"):
    symbol=normalize_company_symbol(symbol)
    st.subheader(f"{symbol} - AI news summary & sentiment")
    st.caption("Requested news window: last 7 days. Follows Consensus stock above; independent of the movers' performance-period filter.")
    credential=sha256(json.dumps([fmp_api_key,serper_api_key,marketaux_api_key]).encode()).hexdigest()
    identity=(credential,symbol)
    evidence_results=dict(st.session_state.get("movers_news_evidence",{}))
    summaries=dict(st.session_state.get("movers_news_summaries",{}))
    summary_identity=(*identity,sha256(openai_api_key.strip().encode()).hexdigest())
    has_provider=any(k.strip() for k in (fmp_api_key,serper_api_key,marketaux_api_key))
    if st.button(f"Load / refresh {symbol} news",key="movers_news_load",disabled=not has_provider):
        try:
            with st.spinner(f"Loading available {symbol} news..."):
                news=load_ticker_news(symbol,company,fmp_api_key,marketaux_api_key,serper_api_key,refresh=True)
            if news.get("symbol")!=symbol:raise ValueError("News response identity did not match the selected stock.")
            if news.get("articles") or identity not in evidence_results:
                evidence_results.pop(identity,None);evidence_results[identity]=news
            else:
                previous=dict(evidence_results[identity]);previous["refresh_warnings"]=["News refresh returned no usable stories; saved news retained.",*news.get("warnings",[])]
                evidence_results[identity]=previous
            while len(evidence_results)>8:evidence_results.pop(next(iter(evidence_results)))
            st.session_state["movers_news_evidence"]=evidence_results
        except Exception as exc:
            st.warning("Company news unavailable; saved evidence preserved. "+sanitize_error(exc))
    news=evidence_results.get(identity)
    try:
        packet=ticker_evidence(news) if news else None
    except ValueError:
        packet=None
        st.warning("Company news could not be prepared within the evidence limits. Refresh news to retry; saved summary preserved.")
    if news and packet:
        st.caption(f"{len(packet['articles'])} stories | news retrieved {news.get('retrieved_at') or 'unknown'} | headline/snippet coverage")
        try:
            stamp=datetime.fromisoformat(str(news.get("retrieved_at")))
            if datetime.now(timezone.utc)-stamp>timedelta(hours=24):
                st.warning("Saved news is over 24 hours old. Refresh news and regenerate to update the briefing.")
        except (TypeError,ValueError):
            st.caption("News retrieval age is unavailable.")
        for warning in news.get("warnings",[])+news.get("refresh_warnings",[]):st.warning(warning)
    if st.button(f"Generate / refresh {symbol} AI news summary",key="movers_news_generate",disabled=not openai_api_key.strip() or not packet or not packet["articles"]):
        try:
            with st.spinner(f"Summarizing {symbol} news and assessing coverage tone..."):
                saved=summarize_ticker_news(news,openai_api_key,model_name)
            summaries.pop(summary_identity,None);summaries[summary_identity]=saved
            while len(summaries)>8:summaries.pop(next(iter(summaries)))
            st.session_state["movers_news_summaries"]=summaries
        except Exception as exc:
            retained="; previous summary preserved" if summary_identity in summaries else ""
            st.warning("AI summary unavailable"+retained+". "+sanitize_error(exc))
    saved=summaries.get(summary_identity)
    if saved:
        if not packet or saved["evidence"]["fingerprint"]!=packet["fingerprint"] or saved["model"]!=model_name:
            st.warning("Saved summary uses earlier news or model settings. Generate again to update it.")
        result=saved["result"]
        tone=result["sentiment"]
        getattr(st,{"Positive":"success","Negative":"error","Mixed":"warning","Insufficient evidence":"info"}[tone])("News sentiment: "+tone)
        st.text(news_text(result["overview"]))
        st.text(news_text(result["sentiment_reason"]))
        for story in result["stories"]:
            st.text("- "+news_text(story["development"]))
            st.caption(news_text(story["implication"]))
        st.caption(news_text(result["limitations"]))
        st.caption(f"AI interpretation | generated {saved.get('generated_at') or 'unknown'} | news retrieved {saved['evidence'].get('retrieved_at') or 'unknown'} | qualitative news tone, separate from social sentiment and analyst ratings.")
    else:
        st.info("Load news, then generate a concise company summary and qualitative sentiment assessment. Changing stocks or filters does not call AI.")
    if not openai_api_key.strip():st.caption("Configure OpenAI in Settings to generate a summary. News collection remains available.")
