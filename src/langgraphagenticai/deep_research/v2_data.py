"""Compatibility names for the shared fresh-research financial boundary."""
from langgraphagenticai.providers.fmp_http import get_fmp_json
from .quarterly_data import QuarterlyFinancialDataSource as _SharedSource
from .research_metrics import audited_comparison_rows as quarterly_comparison_rows

class QuarterlyFinancialDataSource(_SharedSource):
    def fetch_json(self, *args, **kwargs):
        return get_fmp_json(*args, **kwargs)
