"""Historical question form; only submission retrieves data and calls AI."""
from datetime import date, timedelta
import streamlit as st
from langgraphagenticai.technical_analysis.questions import answer_question
from langgraphagenticai.analysis.executive_text import executive_text
from langgraphagenticai.utils.safety import sanitize_error


def render_technical_questions(symbol, fmp_key, openai_key, model):
    with st.expander("Ask historical technical questions"):
        st.caption("Ask about any technical topic or historical period. Available daily history is bounded; answers explain gaps. Intraday and volume analysis may be unavailable.")
        with st.form("historical_technical_question"):
            ticker = st.text_input("Historical question ticker", value=symbol, max_chars=16)
            start = st.date_input("From", value=date.today()-timedelta(days=365), min_value=date(1900,1,1))
            end = st.date_input("Through", value=date.today(), min_value=date(1900,1,1))
            question = st.text_area("Technical question", max_chars=2000, placeholder="How did momentum change during this period, and where did the trend weaken?")
            submit = st.form_submit_button("Ask technical AI", disabled=not openai_key.strip())
        if submit:
            try:
                with st.spinner("Reviewing historical prices and indicators..."):
                    answer = answer_question(ticker, start, end, question, fmp_key, openai_key, model)
                st.session_state.historical_technical_answers = (st.session_state.get("historical_technical_answers", [])+[answer])[-8:]
            except Exception as exc:
                st.warning("Historical technical answer unavailable. "+sanitize_error(exc))
        for answer in st.session_state.get("historical_technical_answers", []):
            st.markdown("**"+answer["symbol"]+"**")
            st.text(answer["question"])
            st.write(executive_text(answer["answer"]))
            st.caption(f"Observed period: {answer['start']} to {answer['end']}")
