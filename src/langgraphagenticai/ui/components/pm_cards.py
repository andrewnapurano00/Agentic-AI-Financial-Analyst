from __future__ import annotations

import pandas as pd
import streamlit as st


def render_metric_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div style='padding:0.8rem 1rem;border:1px solid rgba(128,128,128,0.25);border-radius:0.9rem;'>
            <div style='font-size:0.85rem;opacity:0.75;'>{label}</div>
            <div style='font-size:1.2rem;font-weight:600;'>{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_score_card(title: str, score: float, verdict: str, bullets: list[str], risks: list[str], thesis: str = "", conviction: str = "") -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        caption_bits = [f"Score: {score:.2f}", f"Verdict: {verdict}"]
        if thesis:
            caption_bits.append(f"Thesis: {thesis}")
        if conviction:
            caption_bits.append(f"Conviction: {conviction}")
        st.caption(" | ".join(caption_bits))
        if bullets:
            st.markdown("Support")
            for b in bullets[:3]:
                st.write(f"- {b}")
        if risks:
            st.markdown("Pushback")
            for r in risks[:3]:
                st.write(f"- {r}")


def pct(x):
    try:
        return "NA" if pd.isna(x) else f"{float(x) * 100:.1f}%"
    except Exception:
        return "NA"
