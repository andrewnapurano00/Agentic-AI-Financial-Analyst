"""Active Top Movers social view: text only, explicit collect/generate."""
from hashlib import sha256
import json
import streamlit as st
from langgraphagenticai.providers.social_sentiment import load_social_sentiment
from langgraphagenticai.analysis.social_brief import summarize_social
from langgraphagenticai.analysis.executive_text import executive_text
from langgraphagenticai.utils.safety import sanitize_error


def render_social_brief(symbol, fmp_key, openai_key, model):
    st.subheader(f"{symbol} - Social activity summary")
    identity=sha256(json.dumps([symbol,fmp_key,openai_key,model]).encode()).hexdigest()
    results=dict(st.session_state.get("movers_social_briefs",{}))
    if st.button(f"Generate / refresh {symbol} social summary", key="movers_social_brief_generate", disabled=not fmp_key.strip() or not openai_key.strip()):
        try:
            packet=load_social_sentiment(symbol,fmp_key,5,refresh=True)
            result=summarize_social(packet,openai_key,model)
            results[identity]={"result":result,"retrieved_at":packet.get("retrieved_at")}
            while len(results)>8:results.pop(next(iter(results)))
            st.session_state.movers_social_briefs=results
        except Exception as exc:
            st.warning("Social summary unavailable. Saved summaries are unchanged. "+sanitize_error(exc))
    saved=results.get(identity)
    if saved:
        st.markdown("**"+saved["result"]["tone"]+"**")
        st.write(executive_text(saved["result"]["summary"]))
        st.caption(executive_text(saved["result"]["uncertainty"]))
        st.caption("Observations retrieved "+str(saved["retrieved_at"]))
    else:
        st.info("Generate a short assessment of available social activity. Missing observations will not be replaced with invented sentiment.")
