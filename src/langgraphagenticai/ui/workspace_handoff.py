"""One-shot pre-widget adapters. Preparing a handoff performs no collection."""
from langgraphagenticai.state.research_context import ResearchContext


def queue_handoff(state, context: ResearchContext) -> None:
    if not isinstance(context, ResearchContext):
        raise ValueError("A validated ResearchContext is required.")
    state["pending_company_context"] = context
    state["next_workspace"] = context.destination


def apply_pending_handoff(state) -> ResearchContext | None:
    context = state.get("pending_company_context")
    if context is None:
        return None
    if not isinstance(context, ResearchContext):
        raise ValueError("Invalid pending company context.")
    text = ", ".join(context.symbols)
    updates = {"research_context": context}
    if context.destination == "Introduction":
        updates.update(intro_company_symbol=context.symbols[0], intro_company_query=text, intro_company_search=text,
                       market_chart_symbol=context.symbols[0])
    elif context.destination == "Research":
        discovery_request = state.pop("pending_discovery_request", None)
        matching_draft = discovery_request[1] if isinstance(discovery_request, tuple) and len(discovery_request) == 2 and context.symbols == (discovery_request[0],) else None
        updates["research_request_draft"] = matching_draft or f"{'Compare' if context.intent == 'compare' else 'Analyze'} {text}: business, financials, valuation and risks."
    elif context.destination == "Equity Report":
        updates.update(equity_report_ticker_text=text, equity_report_ticker_input=text)
    elif context.destination == "AI Valuation":
        updates["valuation_ticker"] = context.symbols[0]
    else:
        updates["dr_tickers"] = text
        updates["drv2_tickers"] = text
        updates["deep_research_format"] = "Low cost format" if context.destination == "Deep Research V2" else "Standard format"
    state.update(updates)
    del state["pending_company_context"]
    return context


def render_company_handoffs(symbol: str, origin: str, *, key: str) -> None:
    import streamlit as st
    from langgraphagenticai.utils.safety import sanitize_error
    destinations = tuple(d for d in ("Research", "Equity Report", "AI Valuation", "Deep Research") if d != origin)
    columns = st.columns(len(destinations))
    for column, destination in zip(columns, destinations):
        if column.button(f"Open {destination}", key=f"{key}_{destination}", use_container_width=True):
            try:
                context = ResearchContext((symbol,), destination, "deep_research" if destination.startswith("Deep") else "analyze", origin)
                queue_handoff(st.session_state, context)
            except ValueError as exc:
                st.error(sanitize_error(exc))
            else:
                st.rerun()
