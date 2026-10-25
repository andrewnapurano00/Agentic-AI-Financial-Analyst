"""Simple sector-aware reader view; all content comes from the saved result."""
import pandas as pd
import streamlit as st
from langgraphagenticai.portfolio_architect.executive import holding_review, recommendation_rows


def render_advisor_executive(result):
    st.subheader("Portfolio recommendation")
    if result.snapshot.mode == "SYNTHETIC DEMO":
        st.warning("SYNTHETIC DEMO - Invented observations; this is a software demonstration.")
    roles = {u.get("role") for u in result.usage if u.get("role")}
    if "explanation_only" in roles or not result.model:
        st.caption("Sector metrics + your objective select holdings. Local rules set allocations. AI explains the saved evidence; it does not change holdings or weights.")
    else:
        st.caption("Saved earlier workflow: AI may have influenced selection or sizing. New Builds use metrics-led selection with AI explanation only.")
    status = result.ai_review_status.get("state")
    if status == "failed":
        st.warning("AI explanation unavailable. The local portfolio is preserved. " + result.ai_review_status.get("reason", ""))
    st.write(f"{len(result.holdings)} holdings with {result.cash:.0%} cash, for your {result.mandate.horizon}-year {result.mandate.investment_style} objective. "
             "Stock quality is compared within the relevant sector framework; ETFs are evaluated by allocation role.")
    st.caption("Saved evidence retrieved: " + result.snapshot.retrieved_at + ". Scores are relative research measures, not expected returns or fair values. Sector priorities match Equity Report; collected evidence is a narrower provider-TTM/annual subset.")
    st.markdown("### Recommendation snapshot")
    st.dataframe(pd.DataFrame(recommendation_rows(result)), hide_index=True, width="stretch",
        column_config={"Allocation %":st.column_config.NumberColumn(format="%.1f"),
                       "Sector score / 100":st.column_config.NumberColumn(format="%.1f")})
    st.caption(f"Cash: {result.cash:.1%} (${result.cash_dollars:,.2f}). Sector score measures saved applicable peer factors; evidence coverage is the weighted usable-input share, not an audit pass.")
    st.markdown("### Why each holding is included")
    ids = [h.ticker for h in result.holdings]
    if st.session_state.get("architect_executive_ticker") not in ids:
        st.session_state["architect_executive_ticker"] = ids[0]
    ticker = st.selectbox("Review a holding",ids,key="architect_executive_ticker")
    holding = next(h for h in result.holdings if h.ticker == ticker)
    review = holding_review(result, holding)
    st.markdown("**" + holding.ticker + " | " + holding.name + "**")
    st.caption(review["framework"] + f" | {holding.weight:.1%} allocation | ${holding.dollars:,.2f}")
    st.markdown("**Why included**")
    st.write(review["why"])
    st.markdown("**Main risk**")
    st.write(review["risk"])
    st.markdown("**What would change the thesis**")
    st.write(review["change"])
    if review["metrics"]:
        with st.expander("Sector metrics behind this recommendation", expanded=True):
            st.dataframe(pd.DataFrame(review["metrics"])[["Metric", "Saved value", "Sector priority", "Relative standing"]], hide_index=True, width="stretch")
            st.caption("Higher sector percentile means a more favorable saved factor comparison, not a return forecast. Source dates and fiscal bases remain separate.")
            if review["missing"]:
                st.caption("Uncollected sector priorities: " + ", ".join(review["missing"]))
            with st.expander("Metric sources, periods and evidence IDs"):
                st.dataframe(pd.DataFrame(review["metrics"]),hide_index=True,width="stretch")
    else:
        st.caption("ETF allocation framework: " + "; ".join(review["missing"]))
    st.caption("AI text is interpretation; references and sector classification are checked, prose semantics are not verified." if holding.ai_analysis else "Local explanation from saved evidence; no AI thesis used for this holding.")
    with st.expander("How allocations were determined"):
        st.write("Selection respects your asset, sector, ticker and mandate settings. Local sizing then applies cash, position and category limits; the selected historical sizing method can affect weights.")
        st.write(holding.sizing)
        st.caption("No future return, loss limit or ETF look-through exposure is established by these checks.")
