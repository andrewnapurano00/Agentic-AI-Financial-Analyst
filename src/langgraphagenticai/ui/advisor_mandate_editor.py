"""Local mandate presentation and draft comparison; no providers or models."""
import re
import pandas as pd
import streamlit as st
from langgraphagenticai.portfolio_architect.schemas import InvestorMandate
from langgraphagenticai.portfolio_architect.mandate import default_mandate
from langgraphagenticai.portfolio_architect.universe import SECTORS, THEMES, UNIVERSE


SIZING_METHODS = {
    "ai_risk_budget": "Covariance risk budgets",
    "risk_parity": "Equal covariance risk budgets",
    "min_variance": "Constrained minimum variance",
    "risk": "Legacy volatility / correlation heuristic",
    "equal": "Equal weight",
    "conviction_risk": "Legacy conviction + risk heuristic",
}


def preview_rows(mandate, values, ai=False, prompt=None):
    """Only the existing local parser establishes prompt-extracted field provenance."""
    objective = mandate.objective if prompt is None else prompt
    local, _ = default_mandate(objective)
    text = objective.lower()
    risks = set(re.findall(r"\b(conservative|moderate|aggressive)\b", text))
    years = set(re.findall(r"\b(1|3|5|10)[ -]year", text))
    explicit = {"risk": len(risks) == 1, "horizon": len(years) == 1,
                "investment_style": local.investment_style == "growth" or bool(re.search(r"\bbalanced\b", text))}
    labels = {"investment_style": "Investment style", "horizon": "Horizon (years)",
              "risk": "Risk preference (indicative)", "amount": "Hypothetical amount (USD)"}
    rows = []
    for field, label in labels.items():
        value = values[field]
        if value != getattr(mandate, field):
            origin = "User edit"
        elif explicit.get(field) and value == getattr(local, field):
            origin = "Prompt keyword / numeric horizon"
        else:
            origin = "AI suggestion - Needs confirmation" if ai else "Default - Needs confirmation"
        rows.append({"Setting": label, "Current choice": str(value), "Basis": origin})
    return rows


def draft_changes(mandate, saved_mandate):
    """Compare only this editor's existing widget namespace with the saved result."""
    prefix = f"architect_edit_{st.session_state.get('architect_editor_version', 0)}_"
    fields = {"style": "investment_style", "horizon": "horizon", "risk": "risk", "amount": "amount",
              "holdings": "holdings", "assets": "assets", "method": "method", "cash": "cash",
              "cap": "position_cap", "sector": "sector_cap", "excluded": "excluded_sectors",
              "forbidden": "forbidden", "themes": "themes", "benchmark": "benchmark"}
    for widget, field in fields.items():
        current = st.session_state.get(prefix + widget, getattr(mandate, field))
        if widget in {"cash", "cap", "sector"} and prefix + widget in st.session_state:
            current /= 100
        if widget == "forbidden" and isinstance(current, str):
            current = [s.strip().upper() for s in current.split(",") if s.strip()]
        if current != getattr(saved_mandate, field):
            return True
    enabled = st.session_state.get(prefix + "vol_enabled", mandate.historical_volatility_cap is not None)
    ceiling = st.session_state.get(prefix + "vol_cap", (mandate.historical_volatility_cap or .20)*100)/100 if enabled else None
    return ceiling != saved_mandate.historical_volatility_cap or mandate.objective != saved_mandate.objective


def render_mandate_editor(mandate, ai=False):
    prefix = f"architect_edit_{st.session_state.get('architect_editor_version', 0)}_"
    st.markdown("### 2. Review your mandate")
    st.caption("Review defaults and suggestions, then confirm the displayed choices with Build portfolio. Unparsed prompt requirements need manual confirmation in the controls.")
    text = mandate.objective.lower()
    if len(set(re.findall(r"\b(conservative|moderate|aggressive)\b", text))) > 1:
        st.warning("Conflicting risk words in the objective: choose one indicative preference below. No future loss or volatility ceiling is enforced.")
    st.caption("Risk preference is indicative, not an enforced volatility/loss limit or a suitability assessment. Amounts in the prompt are not extracted by the local parser; confirm the USD amount below.")
    origin = InvestorMandate.model_validate(st.session_state.get("architect_interpreted_mandate", mandate.model_dump()))
    with st.form(prefix + "form"):
        style = st.selectbox("Investment style", ["balanced", "growth"], index=["balanced", "growth"].index(mandate.investment_style), format_func=str.capitalize, key=prefix + "style")
        cols = st.columns(3)
        horizon = cols[0].selectbox("Horizon (years)", [1, 3, 5, 10], index=[1, 3, 5, 10].index(mandate.horizon), key=prefix + "horizon")
        risk = cols[1].selectbox("Risk preference", ["conservative", "moderate", "aggressive"], index=["conservative", "moderate", "aggressive"].index(mandate.risk), key=prefix + "risk")
        amount = cols[2].number_input("Hypothetical amount (USD)", min_value=100., max_value=100000000., value=mandate.amount, key=prefix + "amount")
        st.dataframe(pd.DataFrame(preview_rows(origin, dict(investment_style=style, horizon=horizon, risk=risk, amount=amount), ai,
            st.session_state.get("architect_interpret_prompt"))), hide_index=True, width="stretch")
        st.caption("Form edits apply together on Build. Growth requires positive comparable annual stock revenue growth; theme matches are preferences, not measured revenue exposure.")
        with st.expander("Advanced settings", expanded=False):
            cols = st.columns(3)
            n = cols[0].number_input("Holdings", min_value=5, max_value=15, value=mandate.holdings, key=prefix + "holdings")
            assets = cols[1].selectbox("Allowed assets", ["both", "stocks", "etfs"], index=["both", "stocks", "etfs"].index(mandate.assets), key=prefix + "assets")
            method = cols[2].selectbox("Sizing method", list(SIZING_METHODS), index=list(SIZING_METHODS).index(mandate.method), format_func=lambda v: SIZING_METHODS[v], key=prefix + "method")
            cols = st.columns(3)
            cash = cols[0].number_input("Cash target (%)", min_value=0., max_value=80., value=mandate.cash * 100, key=prefix + "cash")
            cap = cols[1].number_input("Max position (%)", min_value=1., max_value=100., value=mandate.position_cap * 100, key=prefix + "cap")
            sector = cols[2].number_input("Max sector/category (%)", min_value=1., max_value=100., value=mandate.sector_cap * 100, key=prefix + "sector")
            vol_enabled = st.checkbox("Enforce historical-volatility ceiling", value=mandate.historical_volatility_cap is not None, key=prefix + "vol_enabled")
            vol_cap = st.number_input("Historical annualized volatility ceiling (%)", min_value=1., max_value=100., value=(mandate.historical_volatility_cap or .20)*100, key=prefix + "vol_cap")
            st.caption("Optional build gate on aligned historical price returns. A failed or unavailable check blocks the build; edit cash, sizing or the ceiling explicitly. No future volatility/loss guarantee. Cash and caps are never relaxed automatically.")
            excluded = st.multiselect("Excluded stock sectors (all ETFs excluded when set: no look-through)", SECTORS, default=mandate.excluded_sectors, key=prefix + "excluded")
            forbidden = st.text_input("Forbidden tickers (comma separated)", value=", ".join(mandate.forbidden), key=prefix + "forbidden")
            themes = st.multiselect("Preferred curated themes", THEMES, default=mandate.themes, key=prefix + "themes")
            benchmark = st.selectbox("Historical benchmark", sorted(UNIVERSE), index=sorted(UNIVERSE).index(mandate.benchmark), key=prefix + "benchmark")
        submitted = st.form_submit_button("Build portfolio", type="primary")
    if not submitted:
        return None
    try:
        return InvestorMandate(objective=mandate.objective, investment_style=style, horizon=horizon, risk=risk, amount=amount,
            holdings=int(n), assets=assets, cash=cash/100, position_cap=cap/100, sector_cap=sector/100,
            excluded_sectors=excluded, forbidden=[s.strip() for s in forbidden.split(",") if s.strip()],
            themes=themes, benchmark=benchmark, method=method, historical_volatility_cap=vol_cap/100 if vol_enabled else None)
    except ValueError:
        st.error("The mandate is invalid or infeasible. Check holdings multiplied by position/sector cap against the non-cash allocation; increase cash/caps or revise holdings. Check ticker formats. Previous results remain available.")
        return None
