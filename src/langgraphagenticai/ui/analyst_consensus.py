"""Selectable semicircular consensus rating gauge below mover charts."""
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from math import cos, sin, pi
import pandas as pd
import streamlit as st
from langgraphagenticai.providers.analyst_consensus import load_analyst_consensus
from langgraphagenticai.state.research_context import normalize_company_symbol


def consensus_gauge(data):
    """Responsive, accessible SVG; saved percentages and leading category unchanged."""
    rows={row["category"]:row for row in data["categories"]}
    rating=data.get("leading_category") or "Mixed"
    angle={"Sell":pi*.83,"Hold":pi*.5,"Buy":pi*.17,"Mixed":pi*.5}[rating]
    x,y=170+58*cos(angle),122-58*sin(angle)
    columns=[]
    for key,cx,color in (("Sell",85,"#E2747E"),("Hold",170,"#C8AA73"),("Buy",255,"#37B68C")):
        row=rows[key]
        columns.append(f'<text x="{cx}" y="267" fill="#9AA9BC" font-size="14" font-weight="600">{key}</text><text x="{cx}" y="289" fill="{color}" font-size="18" font-weight="700">{row["count"]}</text><text x="{cx}" y="310" fill="{color}" font-size="14">{row["percent"]:.1f}%</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 340 332" role="img" aria-label="Consensus rating: {rating}. Based on {data['total']} analyst ratings." style="display:block;width:100%;max-width:420px;height:auto;margin:0 auto 12px;font-family:Arial,sans-serif">
<rect x="1" y="1" width="338" height="330" rx="5" fill="none" stroke="none"/>
<text x="16" y="30" fill="#E6EBF2" font-size="20" font-weight="600">Consensus Rating</text>
<defs><linearGradient id="consensus-gauge-gradient" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#E64F61"/><stop offset="48%" stop-color="#F4DEA1"/><stop offset="100%" stop-color="#57B993"/></linearGradient></defs>
<path d="M 100 122 A 70 70 0 0 1 240 122" fill="none" stroke="#283649" stroke-width="11"/>
<path d="M 100 122 A 70 70 0 0 1 240 122" fill="none" stroke="url(#consensus-gauge-gradient)" stroke-width="8"/>
<line x1="170" y1="122" x2="{x:.2f}" y2="{y:.2f}" stroke="#E6EBF2" stroke-width="3" stroke-linecap="round"/>
<circle cx="170" cy="122" r="3.5" fill="#E6EBF2"/>
<g text-anchor="middle"><text x="170" y="190" fill="#E6EBF2" font-size="44">{rating}</text><text x="170" y="229" fill="#C6D2DD" font-size="16">Based on {data['total']} Analyst Ratings</text>{''.join(columns)}</g>
</svg>'''


def render_analyst_consensus(symbols, selected, api_key):
    symbols=list(dict.fromkeys(normalize_company_symbol(s) for s in symbols))
    if not symbols:
        return
    st.subheader("Analyst Buy / Hold / Sell consensus")
    previous=st.session_state.get("movers_consensus_stock",selected)
    if previous not in symbols:
        st.session_state["movers_consensus_stock"]=selected if selected in symbols else symbols[0]
    symbol=st.selectbox("Consensus stock",symbols,index=symbols.index(previous) if previous in symbols else 0,key="movers_consensus_stock")
    identity=(sha256(api_key.strip().encode()).hexdigest(),symbol)
    results=dict(st.session_state.get("movers_consensus_results",{}))
    if st.button(f"Load / refresh {symbol} analyst consensus",key="movers_consensus_load",disabled=not api_key.strip()):
        with st.spinner(f"Loading {symbol} analyst ratings..."):
            packet=load_analyst_consensus(symbol,api_key,refresh=True)
        if packet.get("symbol") != symbol:
            st.warning("Consensus response did not match the selected stock; saved evidence preserved.")
        elif packet.get("data") or identity not in results:
            results.pop(identity,None);results[identity]=packet
        else:
            previous=dict(results[identity])
            previous["refresh_warnings"]=["Refresh unavailable; showing previously saved consensus.",*packet.get("warnings",[])]
            results[identity]=previous
        while len(results)>8:
            results.pop(next(iter(results)))
        st.session_state["movers_consensus_results"]=results
    packet=results.get(identity)
    if not packet:
        st.info("Select a ranked stock and load its analyst consensus. Saved stocks remain available without reloading.")
        return
    for warning in packet.get("warnings",[])+packet.get("refresh_warnings",[]):
        st.warning(warning)
    if not packet.get("data"):
        st.info("No usable analyst rating counts are available for this stock.")
        return
    data=packet["data"]
    st.caption(f"{symbol} | FMP | {data['total']} ratings | Retrieved {packet['retrieved_at']} | Rating as-of date unavailable")
    try:
        if datetime.now(timezone.utc)-datetime.fromisoformat(packet["retrieved_at"])>timedelta(hours=24):
            st.warning("Saved consensus was retrieved over 24 hours ago. Refresh for the latest available provider counts.")
    except (ValueError,TypeError):
        st.caption("Retrieval age is unavailable.")
    with st.container(horizontal_alignment="center"):
        st.markdown(consensus_gauge(data),unsafe_allow_html=True)
    st.caption("Strong Buy is included in Buy; Strong Sell is included in Sell. The needle indicates the largest category; ties show Mixed. Percentages describe analyst ratings, not probabilities or price forecasts.")
    with st.expander("Rating counts & coverage"):
        st.dataframe(pd.DataFrame(data["categories"]).rename(columns={"category":"Rating","count":"Count","percent":"Share (%)"}),hide_index=True,width="stretch")
        st.caption("Current provider snapshot; not tied to the movers' performance period. Rating dates and distinct analyst coverage are not supplied by this endpoint. Cache lifetime: one hour; refresh is explicit.")
