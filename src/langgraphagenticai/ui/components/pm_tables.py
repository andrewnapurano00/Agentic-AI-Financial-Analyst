from __future__ import annotations

import pandas as pd
import streamlit as st


def _pct(x):
    try:
        if pd.isna(x):
            return "NA"
        return f"{float(x) * 100:.1f}%"
    except Exception:
        return "NA"


def _num(x):
    try:
        if pd.isna(x):
            return "NA"
        return f"{float(x):,.2f}"
    except Exception:
        return "NA"


def _int(x):
    try:
        if pd.isna(x):
            return "NA"
        return f"{int(float(x))}"
    except Exception:
        return "NA"


def _money(x):
    try:
        if pd.isna(x):
            return "NA"
        return f"${float(x):,.0f}"
    except Exception:
        return "NA"


def _yes_no(x):
    if pd.isna(x):
        return "NA"
    return "Yes" if bool(x) else "No"


def format_recommendation_table(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    for col in ["current_weight", "target_weight", "delta_weight", "peer_percentile", "full_text_ratio", "peer_reliability", "data_quality_score"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").map(_pct)
    for col in ["avg_news_sentiment", "news_signal_score"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").map(_num)
    for col in [
        "screening_score", "fundamental_score", "valuation_score", "technical_score", "catalyst_score", "earnings_score", "risk_fit_score",
        "absolute_score", "peer_score", "composite_score", "confidence", "conviction_score"
    ]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").map(_num)
    for col in ["peer_rank", "peer_news_rank", "article_count", "peer_metric_count", "peer_count", "trade_priority"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").map(_int)
    for col in ["market_value", "last_price", "current_value", "target_value", "trade_value"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").map(_money if col != "last_price" else _num)
    if 'passes_screen' in out.columns:
        out['passes_screen'] = out['passes_screen'].map(_yes_no)
    return out


def render_decision_audit_table(df: pd.DataFrame) -> None:
    st.markdown("### Decision Audit")
    if df is None or df.empty:
        st.info("No decision audit output available yet.")
        return

    preferred = [
        c for c in [
            "ticker",
            "sector",
            "final_action",
            "decision_reason",
            "decision_confidence",
            "data_quality_label",
            "data_quality_score",
            "composite_score",
            "absolute_score",
            "peer_score",
            "peer_rank",
            "peer_group_name",
            "peer_count",
            "peer_reliability",
            "fundamental_score",
            "valuation_score",
            "technical_score",
            "catalyst_score",
            "earnings_score",
            "risk_fit_score",
            "current_weight",
            "suggested_sizing",
            "consensus_state",
            "triggered_guardrails",
            "missing_evidence",
            "pm_decision_summary",
        ] if c in df.columns
    ]
    st.dataframe(format_recommendation_table(df[preferred]), use_container_width=True, hide_index=True)


def render_action_table(title: str, df: pd.DataFrame) -> None:
    st.markdown(f"### {title}")
    if df is None or df.empty:
        st.caption("No names in this bucket.")
        return
    preferred = [
        c for c in [
            "ticker", "sector", "current_weight", "absolute_score", "peer_score", "peer_rank", "peer_confidence", "peer_reliability",
            "data_quality_label", "data_quality_score", "decision_reason",
            "consensus_state", "suggested_sizing", "decision_confidence", "composite_score", "confidence",
            "final_action", "key_supports", "key_conflicts", "next_steps"
        ] if c in df.columns
    ]
    st.dataframe(format_recommendation_table(df[preferred]), use_container_width=True, hide_index=True)


def render_recommendation_matrix(df: pd.DataFrame) -> None:
    st.markdown("### Recommendation Matrix")
    if df is None or df.empty:
        st.info("No recommendations to display yet.")
        return

    preferred_first = [
        "ticker",
        "sector",
        "final_action",
        "decision_reason",
        "decision_confidence",
        "data_quality_label",
        "composite_score",
        "peer_rank",
        "peer_score",
        "current_weight",
        "suggested_sizing",
        "pm_decision_summary",
    ]
    ordered = [c for c in preferred_first if c in df.columns] + [c for c in df.columns if c not in preferred_first]
    st.dataframe(format_recommendation_table(df[ordered]), use_container_width=True, hide_index=True)
