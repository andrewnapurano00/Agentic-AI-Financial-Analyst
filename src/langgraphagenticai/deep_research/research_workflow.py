"""Fresh V1/V2 audited financial boundary with explicit saved-legacy preservation."""
from .manager import ResearchManager
from .research_metrics import audited_comparison_rows
from .quarterly_ttm import METHODOLOGY

class AuditedResearchManager(ResearchManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.comparison_builder = audited_comparison_rows
        self.financial_methodology = METHODOLOGY

    def run(self, request, app_context=()):
        # Unverified cross-workspace TTM packets cannot substitute for audited statements.
        result = super().run(request, app_context=())
        result["financial_methodology"] = METHODOLOGY
        return result

    def resume(self, saved):
        fresh = saved.get("financial_methodology") == METHODOLOGY or any(
            e.get("category") == "income_ttm" and isinstance(e.get("data"),list)
            and e["data"] and e["data"][0].get("methodology") == METHODOLOGY
            for e in saved.get("evidence",[]))
        previous = self.comparison_builder
        if not fresh:
            self.comparison_builder = lambda evidence, symbols: saved.get("comparison", [])
        try:
            result = super().resume(saved)
            if fresh:
                result["financial_methodology"] = METHODOLOGY
            else:
                result["legacy_financial_basis"] = "Saved legacy methodology; comparison values preserved without recomputation or recollection."
            return result
        finally:
            self.comparison_builder = previous


AUDITED_TOOL_NAMES = {"get_company_profile", "get_price_snapshot", "get_latest_earnings_transcript",
    "get_earnings_transcript", "get_analyst_estimates", "get_price_target_consensus",
    "get_available_earnings_transcript_periods", "get_company_peers", "get_dcf_valuation",
    "get_levered_dcf", "get_ratings_snapshot", "get_stock_grades", "get_company_earnings",
    "get_dividend_history", "get_esg_ratings", "get_esg_bundle"}

def audited_finance_tools(tools):
    return [tool for tool in tools if tool.name in AUDITED_TOOL_NAMES]
