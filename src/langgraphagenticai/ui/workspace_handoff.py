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
        updates.update(intro_company_symbol=context.symbols[0], intro_company_query=text, intro_company_search=text)
    elif context.destination == "Research":
        updates["research_request_draft"] = f"{'Compare' if context.intent == 'compare' else 'Analyze'} {text}: business, financials, valuation and risks."
    elif context.destination == "Equity Report":
        updates.update(equity_report_ticker_text=text, equity_report_ticker_input=text)
    else:
        updates["dr_tickers" if context.destination == "Deep Research" else "drv2_tickers"] = text
    state.update(updates)
    del state["pending_company_context"]
    return context


def render_company_handoffs(symbol: str, origin: str, *, key: str) -> None:
    import streamlit as st
    from langgraphagenticai.utils.safety import sanitize_error
    destinations = ("Research", "Equity Report", "Deep Research", "Deep Research V2")
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
