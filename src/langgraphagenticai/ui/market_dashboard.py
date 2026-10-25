"""Market Brief: evidence first, explicit saved AI, heatmap and daily chart."""
import pandas as pd
import streamlit as st
from html import escape
from langgraphagenticai.deep_research.models import safe_url
from langgraphagenticai.providers.market_dashboard import load_dashboard
from langgraphagenticai.providers.market_brief_news import load_market_news
from langgraphagenticai.providers.fmp_daily_prices import load_fmp_daily_prices
from langgraphagenticai.providers.symbol_history import load_symbol_history, clear_history_cache
from langgraphagenticai.analysis.market_brief_ai import evidence_identity, interpret_market, SUMMARY_VERSION
from langgraphagenticai.ui.sector_heatmap import mosaic_chart
from langgraphagenticai.ui.technical_chart import render_technical_chart
from langgraphagenticai.ui.opening_presentation import heading, opening_styles, terminal_chart, number
from langgraphagenticai.utils.safety import sanitize_error
from langgraphagenticai.providers.ticker_ribbon import load_ribbon, load_members
from langgraphagenticai.ui.ticker_ribbon import render_ticker_ribbon
from langgraphagenticai.ui.market_news_summary import render_news_summary
from langgraphagenticai.analysis.executive_text import executive_text


def render_market_ai(packet, news, api_key, model):
    st.subheader("Executive market brief")
    identity = evidence_identity(packet, news)
    summary_identity = evidence_identity(packet, {})
    ready = any(row.get("Level") is not None for row in packet.get("rows", []))
    if st.button("Generate / refresh market summary", key="market_summary_generate", type="primary", disabled=not api_key.strip() or not ready):
        try:
            with st.spinner("Distilling macro and sector trends into an executive briefing…"):
                text = interpret_market(packet, news, api_key, model)
            st.session_state.market_ai_summary = {"text": text, "identity": summary_identity, "model": model, "version": SUMMARY_VERSION}
        except Exception as exc:
            st.warning("Market summary unavailable; saved summary preserved. "+sanitize_error(exc))
    saved = st.session_state.get("market_ai_summary")
    if saved and saved.get("version") != SUMMARY_VERSION:
        st.info("Generate the updated executive brief for a high-level view of what is working and what is not.")
        with st.expander("Previously saved market summary"):
            st.markdown(executive_text(saved["text"]))
    elif saved:
        if saved["identity"] != summary_identity or saved["model"] != model:
            st.warning("Saved summary uses different evidence or model settings. Generate again to update it.")
        with st.container(border=True):
            st.markdown(executive_text(saved["text"]))
    else:
        st.info("A fuller executive view of the past 5 trading days, month and 3 months: macro crosscurrents, sector leaders and laggards, technical confirmation and what to watch.")
    if not api_key.strip():
        st.caption("Configure OpenAI to generate a summary or ask follow-up questions.")
    with st.expander("Ask AI about this dashboard", expanded=bool(saved)):
        history = st.session_state.get("market_ai_chat", [])
        for message in history:
            with st.chat_message(message["role"]):
                st.markdown(executive_text(message["content"]) if message["role"]=="assistant" else message["content"])
        chat_matches = st.session_state.get("market_chat_identity") == identity and st.session_state.get("market_chat_model") == model
        if history and not chat_matches:
            st.caption("Earlier answers used different evidence or model settings; new questions use the current dashboard.")
        with st.form("market_followup_form", clear_on_submit=True):
            question = st.text_input("Market question", max_chars=2000, placeholder="Where is momentum diverging from the daily move?")
            send = st.form_submit_button("Ask market AI", disabled=not api_key.strip() or not ready)
        if send and question.strip():
            try:
                current_history = history if chat_matches else []
                answer = interpret_market(packet, news, api_key, model, question, current_history)
                st.session_state.market_ai_chat = (current_history + [{"role": "user", "content": question}, {"role": "assistant", "content": answer}])[-12:]
                st.session_state.market_chat_identity = identity
                st.session_state.market_chat_model = model
                st.rerun()
            except Exception as exc:
                st.warning("Market AI unavailable; previous conversation preserved. "+sanitize_error(exc))


def render_daily_market_chart(api_key, openai_key, model, *, refresh=False):
    st.subheader("Daily price chart")
    with st.form("market_chart_symbol_form"):
        symbol = st.text_input("Chart ticker", value=st.session_state.get("market_chart_symbol", "^GSPC"), help="S&P 500: ^GSPC. Enter a company, index or ETF ticker.")
        apply = st.form_submit_button("Update chart")
    valid_apply = False
    if apply:
        import re
        candidate = symbol.strip().upper()
        if re.fullmatch(r"\^?[A-Z0-9][A-Z0-9.\-]{0,14}", candidate):
            st.session_state.market_chart_symbol = candidate
            valid_apply = True
        else:
            st.error("Enter a valid company, index or ETF ticker.")
    symbol = st.session_state.get("market_chart_symbol", "^GSPC")
    from langgraphagenticai.ui.technical_questions import render_technical_questions
    render_technical_questions(symbol, api_key, openai_key, model)
    previous_request = st.session_state.get("market_daily_request", (symbol, "1Y"))
    period = st.segmented_control("Daily chart range", ["1M", "3M", "1Y", "3Y", "5Y", "10Y"], default=previous_request[1], key="market_daily_range") or previous_request[1]
    chart_refresh = st.button("Refresh chart history", key="market_daily_refresh")
    if chart_refresh:
        clear_history_cache()
    request = (symbol, period)
    if refresh or chart_refresh or valid_apply or request != previous_request:
        st.session_state.market_daily_request = request
        try:
            chart = dict(load_symbol_history(symbol, api_key, period))
            chart["daily_only"] = True
            if chart.get("points") or not st.session_state.get("market_daily_saved_chart"):
                st.session_state.market_daily_saved_chart = {"request": request, "chart": chart}
            else:
                st.warning("No new chart observations returned; saved chart preserved.")
        except Exception as exc:
            st.warning("Daily chart refresh failed; saved chart preserved. " + sanitize_error(exc))
    saved = st.session_state.get("market_daily_saved_chart")
    if not saved:
        st.info("No saved chart. Refresh chart history to load observations.")
        return
    if saved["request"] != request:
        st.warning("Showing a saved chart for different inputs. Refresh chart history to retry the selected ticker and range.")
    chart = saved["chart"]
    try:
        render_technical_chart(chart, key="market_daily_technical", openai_api_key=openai_key, model_name=model, chart_style=terminal_chart)
    except Exception as exc:
        st.warning("Daily chart unavailable; dashboard evidence preserved. "+sanitize_error(exc))


def render_market_news(news, openai_api_key="", model_name="gpt-5"):
    st.subheader("Market headlines")
    st.caption("The stories shaping the market · Serper, Marketaux & FMP")
    for warning in news.get("warnings", []):
        st.caption(warning)
    articles = [article for article in news.get("articles", []) if safe_url(article.get("url"))]
    if not articles:
        st.info("No market headlines available. Configure the news providers or refresh to retry.")
        return

    def story(article, *, lead=False):
        with st.container(border=True):
            publisher = str(article.get("publisher") or "Market coverage")
            providers = " + ".join(article.get("providers", []))
            st.caption(("LEAD STORY · " if lead else "") + publisher + (" · " + providers if providers else ""))
            st.markdown(f'<h3 style="text-transform:none;font-size:{"1.35rem" if lead else "1.05rem"};line-height:1.35;margin:0 0 .5rem;overflow-wrap:anywhere">{escape(str(article.get("title") or "Untitled"))}</h3>', unsafe_allow_html=True)
            snippet = " ".join(str(article.get("snippet") or "").split())
            limit = 320 if lead else 190
            if snippet:
                st.text(snippet[:limit].rsplit(" ", 1)[0] + "…" if len(snippet) > limit else snippet)
            st.caption(str(article.get("published") or "Publication date unavailable"))
            st.link_button("Read full story ↗", safe_url(article["url"]))

    story(articles[0], lead=True)
    columns = st.columns(2, gap="medium")
    for index, article in enumerate(articles[1:5]):
        with columns[index % 2]:
            story(article)
    if len(articles) > 5:
        with st.expander(f"More headlines ({len(articles)-5})"):
            for article in articles[5:]:
                story(article)


def render_market_dashboard(fmp_api_key="", openai_api_key="", model_name="gpt-5", marketaux_api_key="", serper_api_key=""):
    opening_styles()
    heading("Market Brief", "Market direction, sector rotation and the drivers behind the moves.")
    refresh = st.button("Refresh market evidence", key="intro_refresh")
    if refresh:
        clear_history_cache()
        for loader in (load_ribbon, load_members, load_dashboard, load_fmp_daily_prices, load_market_news):
            loader_clear = getattr(loader, "clear", None)
            if loader_clear:
                loader_clear()
        previous = st.session_state.get("market_evidence_snapshot", {})
        snapshot = dict(previous)
        with st.spinner("Loading macro, sector, technical and market-news evidence…"):
            for name, loader, args in (("packet", load_dashboard, (fmp_api_key,)),
                                       ("news", load_market_news, (serper_api_key, marketaux_api_key, fmp_api_key)),
                                       ("ribbon", load_ribbon, (fmp_api_key,))):
                try:
                    snapshot[name] = loader(*args)
                except Exception as exc:
                    st.warning(f"{name.title()} refresh failed; previously saved evidence preserved. " + sanitize_error(exc))
        st.session_state.market_evidence_snapshot = snapshot
    snapshot = st.session_state.get("market_evidence_snapshot")
    if not snapshot:
        st.info("Select Refresh market evidence to load the dashboard, ticker ribbon, chart and news. You can open any other workspace first; no market data is requested until you refresh.")
        return
    st.caption("Saved market snapshot · data changes only when you refresh. Returning to Market Brief and changing indicator settings reuse saved evidence; it may be stale. Chart ticker/range changes and Refresh chart history request chart data separately.")
    packet = snapshot.get("packet") or {"rows": [], "sectors": {}, "warnings": []}
    news = snapshot.get("news") or {"articles": [], "warnings": []}
    if snapshot.get("ribbon"):
        render_ticker_ribbon(snapshot["ribbon"])
    render_market_ai(packet, news, openai_api_key, model_name)
    render_news_summary(news, openai_api_key, model_name)
    for warning in packet.get("warnings", []):
        st.warning(warning)
    stale = [row["Ticker"] for row in packet["rows"] if row["evidence"].get("stale")]
    if stale:
        st.warning("Stale or unavailable price evidence: "+", ".join(stale))
    st.subheader("Sector heatmap")
    st.caption("Color and large value: 1-day price change. Small value: 5-trading-day return. Equal-size sector ETF tiles.")
    st.altair_chart(mosaic_chart(packet, None), use_container_width=True, theme=None, key="market_sector_mosaic")
    st.subheader("Macro context & sector ETFs")
    st.caption("Returns: latest dated price versus historical adjusted close; 5/30/60 count trading observations; 1M/3M use calendar-month anniversaries with the last adjusted-close observation on/before the anniversary (within seven days). RSI (14) uses daily adjusted closes; SMA distance = (latest price / daily adjusted-close SMA − 1) × 100. Yield-index changes are percentages, not basis points; levels retain instrument-specific units.")
    frame = pd.DataFrame([{key: value for key, value in row.items() if key != "evidence"} for row in packet["rows"]])
    percent = [c for c in frame if c.endswith("%")]
    formats = {c: lambda v: number(v, "%", True) for c in percent}
    formats.update({"Level": "{:,.2f}", "RSI (14)": "{:.1f}"})
    if frame.empty:
        st.info("Market metrics unavailable. Refresh market evidence to retry; other saved sections remain available.")
    else:
        styled = frame.style.format(formats, na_rep="Unavailable").map(
            lambda v: "color: #37B68C" if pd.notna(v) and v > 0 else "color: #E2747E" if pd.notna(v) and v < 0 else "", subset=percent)
        st.dataframe(styled, hide_index=True, use_container_width=True, height=560)
    with st.expander("Calculation inputs & data diagnostics"):
        st.json(packet)
    render_daily_market_chart(fmp_api_key, openai_api_key, model_name, refresh=refresh)
    render_market_news(news, openai_api_key, model_name)
