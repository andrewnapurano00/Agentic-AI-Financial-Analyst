"""Shared saved-state memo controls; no provider/model dependencies."""
def render_investment_memo(result, *, credentials=(), portfolio=False, key="research"):
    import streamlit as st
    from langgraphagenticai.analysis.investment_memo import research_memo, portfolio_memo
    from langgraphagenticai.analysis.memo_pdf import deferred_pdf

    memo = (portfolio_memo if portfolio else research_memo)(result, credentials)
    with st.expander("Executive investment memo", expanded=True):
        st.caption(memo.lineage)
        st.write(memo.thesis.replace("#", "\\#").replace("$", "\\$"))
        for label, text in memo.sections:
            st.markdown("**" + label + "**")
            st.write(text.replace("#", "\\#").replace("$", "\\$"))
        try:
            cache_key = "_investment_memo_pdf_" + key
            cached = st.session_state.get(cache_key)
            if cached is None or cached[0] != memo:
                cached = (memo, deferred_pdf(memo))
                st.session_state[cache_key] = cached
            data = cached[1]
        except ValueError as exc:
            st.warning(str(exc))
            return
        st.caption("The PDF is prepared when you click Download; viewing or navigating does not lay out its full evidence appendices.")
        st.download_button("Executive investment memo PDF", data,
                           file_name="axiom-investment-memo.pdf", mime="application/pdf", key=key + "_memo_pdf", on_click="ignore")
