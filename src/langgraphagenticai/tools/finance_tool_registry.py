from langgraphagenticai.tools.company_overview_tools import build_company_overview_tools
from langgraphagenticai.tools.earnings_transcript_tools import build_earnings_transcript_tools
from langgraphagenticai.tools.financial_statement_tools import build_financial_statement_tools
from langgraphagenticai.tools.news_chat_tools import build_marketaux_news_chat_tools
from langgraphagenticai.tools.news_pipeline_tools import build_marketaux_news_fetch_tools
from langgraphagenticai.tools.price_data_tools import build_price_data_tools

# Expanded FMP MCP coverage
from langgraphagenticai.tools.analyst_tools import build_analyst_tools
from langgraphagenticai.tools.valuation_tools import build_valuation_tools
from langgraphagenticai.tools.calendar_tools import build_calendar_tools
from langgraphagenticai.tools.directory_tools import build_directory_tools
from langgraphagenticai.tools.esg_tools import build_esg_tools
from langgraphagenticai.tools.research_bundle_tools import build_research_bundle_tools


def get_finance_tools(fmp_api_key: str, openai_api_key: str = "", marketaux_api_key: str = ""):
    """
    Central finance tool registry for the LangGraph chat agent.

    The FMP tools are MCP-backed and grouped by topic so the agent can handle
    both simple prompts (quote/profile) and deeper research prompts
    (analyst estimates, valuation, calendars, ESG, and full stock-analysis bundles).
    """
    tools = []

    if fmp_api_key:
        # Existing core tools
        tools.extend(build_company_overview_tools(fmp_api_key))
        tools.extend(build_price_data_tools(fmp_api_key))
        tools.extend(build_financial_statement_tools(fmp_api_key))
        tools.extend(build_earnings_transcript_tools(fmp_api_key))

        # Expanded MCP tools
        tools.extend(build_analyst_tools(fmp_api_key))
        tools.extend(build_valuation_tools(fmp_api_key))
        tools.extend(build_calendar_tools(fmp_api_key))
        tools.extend(build_directory_tools(fmp_api_key))
        tools.extend(build_esg_tools(fmp_api_key))
        tools.extend(build_research_bundle_tools(fmp_api_key))

    if marketaux_api_key:
        tools.extend(build_marketaux_news_fetch_tools(marketaux_api_key=marketaux_api_key))

    if marketaux_api_key and openai_api_key:
        tools.extend(
            build_marketaux_news_chat_tools(
                openai_api_key=openai_api_key,
                marketaux_api_key=marketaux_api_key,
            )
        )

    # Defensive de-duplication by tool name. This prevents duplicate LangChain
    # tool names if files are imported through multiple registry paths.
    unique_tools = []
    seen_names = set()
    for tool in tools:
        name = getattr(tool, "name", None)
        if name and name not in seen_names:
            unique_tools.append(tool)
            seen_names.add(name)

    return unique_tools
