"""Research-only portfolio construction workspace."""
def render_robo_advisor(fmp_api_key="", openai_api_key="", model_name="gpt-5"):
    from langgraphagenticai.ui.portfolio_architect_tab import render_portfolio_architect
    render_portfolio_architect(fmp_api_key=fmp_api_key, openai_api_key=openai_api_key, model_name=model_name)
