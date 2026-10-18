"""Month/quarter targets relative to the same saved latest quote."""
from datetime import datetime,timezone
from hashlib import sha256
import altair as alt
import pandas as pd
import streamlit as st
from langgraphagenticai.analysis.price_targets import compare_targets
from langgraphagenticai.providers.price_targets import load_price_targets
from langgraphagenticai.state.research_context import normalize_company_symbol
from langgraphagenticai.ui.opening_presentation import terminal_chart


def target_chart(comparison):
    rows=[r for r in comparison["rows"] if r["upside_pct"] is not None and r["target"] is not None]
    values=[r["target"] for r in rows]+[comparison["price"]]
    low,high=min(values),max(values)
    padding=max((high-low)*.3,high*.08,1)
    frame=pd.DataFrame(rows)
    x=alt.X("price:Q",title="Price (quote units)",axis=alt.Axis(tickCount=6,format=",.2f" if high<10 else ",.0f"),scale=alt.Scale(domain=[max(0,low-padding),high+padding],zero=False))
    y=alt.Y("window:N",title=None,sort=["Last month","Last quarter"],axis=alt.Axis(labelLimit=120))
    color=alt.Color("direction:N",scale=alt.Scale(domain=["Upside","Downside","At target"],range=["#37B68C","#E2747E","#C8AA73"]),legend=None)
    base=alt.Chart(frame)
    lines=base.mark_rule(strokeWidth=4).encode(x=x,x2="target:Q",y=y,color=color)
    current=base.mark_point(filled=True,color="#E6EBF2",size=110).encode(x=x,y=y,tooltip=[alt.Tooltip("price:Q",title="Latest quote",format=",.2f")])
    targets=base.mark_point(shape="diamond",filled=True,size=180).encode(x=alt.X("target:Q",scale=alt.Scale(domain=[max(0,low-padding),high+padding],zero=False)),y=y,color=color,
        tooltip=["window:N",alt.Tooltip("target:Q",title="Average target",format=",.2f"),alt.Tooltip("upside_pct:Q",title="Upside / downside (%)",format="+.1f"),alt.Tooltip("count:Q",title="Coverage count")])
    rule=alt.Chart(pd.DataFrame([{"price":comparison["price"]}])).mark_rule(color="#E6EBF2",strokeDash=[5,4],opacity=.6).encode(x=x)
    labels=base.transform_calculate(label="format(datum.upside_pct, '+.1f') + '%'").mark_text(dy=-20,fontSize=14,fontWeight="bold").encode(x="target:Q",y=y,text="label:N",color=color)
    return terminal_chart(alt.layer(rule,lines,current,targets,labels).properties(height=220))


def merge_target_evidence(previous,fresh):
    if previous is None:return fresh
    result=dict(fresh);warnings=[]
    old_rows={row["window"]:row for row in previous["summary"].get("targets",[])}
    new_rows=fresh["summary"].get("targets",[])
    merged=[]
    for row in new_rows:
        old=old_rows.get(row["window"],{})
        if row.get("target") is None and row.get("count")!=0 and old.get("target") is not None:
            merged.append(old);warnings.append(row["window"]+" refresh unavailable; showing saved target.")
        else:
            merged.append(row)
    if not new_rows and old_rows:
        merged=list(old_rows.values());warnings.append("Target refresh unavailable; showing saved targets.")
    result["summary"]={**fresh["summary"],"targets":merged}
    if not new_rows and old_rows:
        result["summary"]["retrieved_at"]=previous["summary"].get("retrieved_at")
    if compare_targets(fresh["summary"],fresh["quote"])["price"] is None and compare_targets(previous["summary"],previous["quote"])["price"] is not None:
        result["quote"]=previous["quote"];warnings.append("Quote refresh unavailable; showing saved quote.")
    result["refresh_warnings"]=warnings
    return result


def render_price_targets(symbol,api_key):
    symbol=normalize_company_symbol(symbol)
    st.subheader(f"{symbol} - Analyst price targets")
    st.caption("Compare the latest quote with targets published during the last month and quarter. Uses the Consensus stock selected above.")
    identity=(sha256(api_key.strip().encode()).hexdigest(),symbol)
    results=dict(st.session_state.get("movers_target_results",{}))
    if st.button(f"Load / refresh {symbol} price targets",key="movers_targets_load",disabled=not api_key.strip()):
        with st.spinner(f"Loading {symbol} targets and latest quote..."):
            fresh=load_price_targets(symbol,api_key,refresh=True)
        if fresh.get("symbol")!=symbol or fresh["summary"].get("symbol")!=symbol or fresh["quote"].get("symbol")!=symbol:
            st.warning("Target/quote identity mismatch; saved evidence preserved.")
        else:
            packet=merge_target_evidence(results.get(identity),fresh)
            results.pop(identity,None);results[identity]=packet
            while len(results)>8:results.pop(next(iter(results)))
            st.session_state["movers_target_results"]=results
    packet=results.get(identity)
    if not packet:
        st.info("Load price targets to compare analyst expectations with the latest available quote.")
        return
    summary,quote=packet["summary"],packet["quote"]
    comparison=compare_targets(summary,quote)
    for warning in summary.get("warnings",[])+packet.get("refresh_warnings",[])+comparison["warnings"]:
        if warning.startswith("Target/quote currency"):
            st.caption(warning)
        else:
            st.warning(warning)
    if quote.get("error"):st.warning("Latest quote unavailable. Available targets are preserved; upside requires a valid quote.")
    unit=comparison["currency"] or "quote units"
    price=comparison["price"]
    st.metric("Latest FMP price",f"{price:,.2f} {unit}" if price is not None else "Unavailable")
    st.caption(f"Quote as of {quote.get('as_of') or 'unavailable'} | retrieved {quote.get('retrieved_at') or 'unavailable'}")
    if any(r["upside_pct"] is not None for r in comparison["rows"]):
        st.altair_chart(target_chart(comparison),width="stretch",theme=None,key="movers_price_targets")
        st.caption("White circles / dashed line: latest price. Diamonds: average analyst targets. Signed labels show upside (+) or downside (-).")
    else:
        st.info("No comparable target/quote pair is available. Available evidence remains below.")
    for column,row in zip(st.columns(2),comparison["rows"]):
        target=row.get("target");pct=row.get("upside_pct")
        target_unit=row.get("currency") or unit
        column.metric(row["window"]+" avg target",f"{target:,.2f} {target_unit}" if target is not None else "Unavailable",
                      delta=f"{pct:+.1f}% vs latest price" if pct is not None else None)
        column.caption(f"{row['count']} ratings" if row.get("count") is not None else "Coverage count unavailable")
        if row.get("retrieved_at"):column.caption("Target retrieved "+row["retrieved_at"])
        if row.get("note"):column.caption(row["note"])
    try:
        oldest=min(datetime.fromisoformat(r.get("retrieved_at") or summary["retrieved_at"]) for r in comparison["rows"] if r.get("target") is not None)
        if (datetime.now(timezone.utc)-oldest).total_seconds()>86400:
            st.warning("Some saved targets were retrieved over 24 hours ago. Refresh for the latest available averages.")
    except (ValueError,TypeError,KeyError):
        pass  # Retrieval strings remain visible; no freshness is inferred.
    st.caption(f"FMP target summary retrieved {summary.get('retrieved_at') or 'unavailable'}. Target publication as-of date unavailable. Windows can overlap; targets are not guaranteed returns or time-to-target forecasts.")
    with st.expander("Price-target evidence & calculation"):
        st.dataframe(pd.DataFrame(comparison["rows"]),hide_index=True,width="stretch")
        st.caption("Upside/downside = (average target / latest quote - 1) x 100. Targets and quotes are independently retrieved; unverified currency/adjustment compatibility is disclosed above. Refresh is explicit; targets cache for one hour and quotes for five minutes.")
