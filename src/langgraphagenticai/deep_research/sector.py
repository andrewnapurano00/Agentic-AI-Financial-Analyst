"""Shared sector classification and metric priorities for equity research."""
from __future__ import annotations

from typing import Any


GENERAL_FRAMEWORK = "General / Cross-Sector"


SECTOR_METRIC_REGISTRY: dict[str, dict[str, list[str]]] = {
    GENERAL_FRAMEWORK: {
        "must_have": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY",
                      "Forward EPS Next FY", "Latest Operating Margin", "ROE", "ROA", "FCF CAGR 3Y",
                      "Debt to Equity", "Forward P/E", "Forward P/S", "Price Target Upside",
                      "YTD Return", "1Y Return", "% From SMA 200", "RSI 14"],
        "preferred": ["Net Income CAGR 3Y", "Latest Gross Margin", "Latest EBITDA Margin", "FCF Yield",
                      "Cash Conversion", "P/E TTM", "P/S TTM", "P/FCF TTM", "EV / EBITDA",
                      "Rating Score", "% From SMA 50"],
        "avoid_or_downweight": [], "missing_but_useful": [],
    },
    "Technology / Software / Semis": {
        "must_have": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY",
                      "Forward EPS Next FY", "Latest Gross Margin", "Latest Operating Margin", "FCF CAGR 3Y",
                      "R&D as % Revenue", "Capex to Revenue", "Forward P/S", "Forward P/E", "P/S TTM",
                      "Price Target Upside", "% From SMA 50", "% From SMA 200", "RSI 14"],
        "preferred": ["ROIC", "Income Quality", "Stock-Based Comp % Revenue", "FCF Yield", "P/FCF TTM",
                      "EV / Sales", "EV / FCF", "Rating Score", "1Y Return"],
        "avoid_or_downweight": ["P/B TTM", "Dividend Yield", "Loan-to-Deposit Ratio", "Provision / Loans", "CET1 Ratio"],
        "missing_but_useful": ["ARR", "Net Revenue Retention", "Cloud Backlog", "Customer Churn", "Segment Revenue Growth"],
    },
    "Communication Services": {
        "must_have": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
                      "Latest EBITDA Margin", "Latest Operating Margin", "FCF CAGR 3Y", "Capex to Revenue",
                      "Forward P/E", "Forward P/S", "P/S TTM", "EV / EBITDA", "Price Target Upside",
                      "% From SMA 50", "% From SMA 200", "RSI 14"],
        "preferred": ["FCF Yield", "Cash Conversion", "Net Debt / EBITDA", "ROA", "ROE", "EV / Sales", "EV / FCF", "1Y Return"],
        "avoid_or_downweight": ["P/B TTM", "Current Ratio"],
        "missing_but_useful": ["ARPU", "Subscriber Growth", "Churn", "Ad Revenue Growth", "Content Spend"],
    },
    "Consumer Discretionary": {
        "must_have": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
                      "Latest Gross Margin", "Latest Operating Margin", "FCF CAGR 3Y", "Forward P/E", "Forward P/S",
                      "P/E TTM", "Price Target Upside", "% From SMA 50", "% From SMA 200", "RSI 14"],
        "preferred": ["P/S TTM", "FCF Yield", "Cash Conversion", "ROA", "ROE", "Inventory Days",
                      "Cash Conversion Cycle Days", "Debt to Equity", "1Y Return"],
        "avoid_or_downweight": ["P/B TTM", "R&D as % Revenue"],
        "missing_but_useful": ["Same Store Sales Growth", "Traffic Growth", "Average Ticket", "Store Count"],
    },
    "Consumer Staples": {
        "must_have": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
                      "Latest Gross Margin", "Latest Operating Margin", "FCF CAGR 3Y", "Forward P/E", "P/E TTM",
                      "Dividend Yield", "Dividend Payout Ratio", "Price Target Upside", "% From SMA 50", "% From SMA 200", "RSI 14"],
        "preferred": ["FCF Yield", "Cash Conversion", "ROA", "ROE", "Debt to Equity", "Inventory Days",
                      "Cash Conversion Cycle Days", "1Y Return"],
        "avoid_or_downweight": ["P/B TTM", "R&D as % Revenue", "Forward P/S"],
        "missing_but_useful": ["Organic Sales Growth", "Volume Growth", "Pricing Growth", "Retail Scanner Data"],
    },
    "Consumer": {
        "must_have": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
                      "Latest Gross Margin", "Latest Operating Margin", "FCF CAGR 3Y", "Forward P/E", "Forward P/S",
                      "P/E TTM", "Price Target Upside", "% From SMA 50", "% From SMA 200", "RSI 14"],
        "preferred": ["P/S TTM", "FCF Yield", "Cash Conversion", "Dividend Yield", "Dividend Payout Ratio",
                      "Inventory Days", "Cash Conversion Cycle Days", "ROA", "ROE", "1Y Return"],
        "avoid_or_downweight": ["R&D as % Revenue", "P/B TTM"],
        "missing_but_useful": ["Same Store Sales Growth", "Traffic Growth", "Average Ticket", "Store Count"],
    },
    "Healthcare": {
        "must_have": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
                      "Latest Gross Margin", "Latest Operating Margin", "Latest Net Margin", "FCF CAGR 3Y",
                      "R&D as % Revenue", "Forward P/E", "Forward P/S", "Price Target Upside",
                      "% From SMA 50", "% From SMA 200", "RSI 14"],
        "preferred": ["P/S TTM", "FCF Yield", "Cash Conversion", "Debt to Equity", "ROA", "ROE", "ROIC", "1Y Return"],
        "avoid_or_downweight": ["P/B TTM", "Dividend Yield"],
        "missing_but_useful": ["Pipeline Stage Data", "Patent Cliff Exposure", "Drug-Level Revenue", "Medical Loss Ratio"],
    },
    "Banks / Financials": {
        "must_have": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward EPS Next FY", "P/B TTM", "ROE", "ROA",
                      "Book Value / Share", "Book Value Growth 3Y", "P/E TTM", "Forward P/E", "Earnings Yield",
                      "Dividend Yield", "Price Target Upside", "% From SMA 50", "% From SMA 200", "RSI 14"],
        "preferred": ["Latest Net Margin", "Debt / Assets", "Debt / Capital", "Liabilities to Assets",
                      "Net Interest Margin Proxy", "Efficiency Ratio", "Bank Fee Revenue Mix", "Rating Score", "1Y Return"],
        "avoid_or_downweight": ["Latest Gross Margin", "Latest EBITDA Margin", "FCF Margin", "FCF CAGR 3Y", "P/FCF TTM",
                                "Current Ratio", "R&D as % Revenue", "Stock-Based Comp % Revenue", "CET1 Ratio",
                                "Provision / Loans", "Forward P/S"],
        "missing_but_useful": ["CET1 Ratio", "Risk-Weighted Assets", "Net Charge-Offs", "True Net Interest Margin"],
    },
    "Industrials": {
        "must_have": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
                      "Latest EBITDA Margin", "Latest Operating Margin", "FCF CAGR 3Y", "Capex to Revenue",
                      "Net Debt / EBITDA", "EV / EBITDA", "Forward P/E", "Price Target Upside",
                      "% From SMA 50", "% From SMA 200", "RSI 14"],
        "preferred": ["ROIC", "ROA", "ROE", "Debt / Capital", "FCF Yield", "EV / FCF", "Cash Conversion", "1Y Return"],
        "avoid_or_downweight": ["P/S TTM", "R&D as % Revenue", "P/B TTM"],
        "missing_but_useful": ["Backlog", "Book-to-Bill", "Order Growth", "Organic Growth", "Segment Margin"],
    },
    "Energy": {
        "must_have": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
                      "Latest EBITDA Margin", "Latest Operating Margin", "FCF Yield", "EV / EBITDA", "Net Debt / EBITDA",
                      "Forward P/E", "Dividend Yield", "Dividend Payout Ratio", "Price Target Upside",
                      "% From SMA 50", "% From SMA 200", "RSI 14"],
        "preferred": ["FCF CAGR 3Y", "Capex to Revenue", "Debt / Capital", "Debt / Assets", "EV / FCF", "1Y Return"],
        "avoid_or_downweight": ["R&D as % Revenue", "P/B TTM", "Current Ratio", "Forward P/S"],
        "missing_but_useful": ["Production Growth", "Reserve Replacement Ratio", "Proved Reserves", "Realized Oil/Gas Pricing"],
    },
    "Materials": {
        "must_have": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
                      "Latest Gross Margin", "Latest EBITDA Margin", "Latest Operating Margin", "FCF CAGR 3Y",
                      "EV / EBITDA", "Forward P/E", "Price Target Upside", "% From SMA 50", "% From SMA 200", "RSI 14"],
        "preferred": ["FCF Yield", "Capex to Revenue", "Net Debt / EBITDA", "Debt / Capital", "ROIC", "ROA", "ROE",
                      "EV / FCF", "1Y Return"],
        "avoid_or_downweight": ["R&D as % Revenue", "P/B TTM", "Forward P/S"],
        "missing_but_useful": ["Volume Growth", "Commodity Exposure", "Input Cost Inflation", "Capacity Utilization"],
    },
    "Utilities": {
        "must_have": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward EPS Next FY", "Dividend Yield",
                      "Dividend Payout Ratio", "Debt / Capital", "Debt / Assets", "Debt Service Coverage", "Forward P/E",
                      "P/B TTM", "Latest Net Margin", "Price Target Upside", "% From SMA 50", "% From SMA 200", "RSI 14"],
        "preferred": ["Earnings Yield", "ROE", "ROA", "Net Debt / EBITDA", "1Y Return"],
        "avoid_or_downweight": ["R&D as % Revenue", "P/S TTM", "Forward P/S", "High Growth Metrics"],
        "missing_but_useful": ["Rate Base Growth", "Allowed ROE", "Regulated Earnings Mix", "Capex Plan"],
    },
    "Real Estate / REITs": {
        "must_have": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
                      "Dividend Yield", "Dividend Payout Ratio", "Debt / Assets", "Debt / Capital", "Net Debt / EBITDA",
                      "P/B TTM", "Forward P/E", "Price Target Upside", "% From SMA 50", "% From SMA 200", "RSI 14"],
        "preferred": ["Book Value / Share", "Tangible Book Value / Share", "Latest Net Margin", "Debt Service Coverage", "1Y Return"],
        "avoid_or_downweight": ["P/E TTM", "P/FCF TTM", "Latest Gross Margin", "R&D as % Revenue", "Current Ratio", "Forward P/S"],
        "missing_but_useful": ["FFO", "AFFO", "AFFO Payout Ratio", "Occupancy Rate", "Same Store NOI Growth"],
    },
}


SECTOR_DESCRIPTIONS = {
    GENERAL_FRAMEWORK: "Balanced framework across growth, profitability, cash generation, leverage, valuation, estimates and trend.",
    "Technology / Software / Semis": "Growth, gross-margin durability, R&D investment, free cash flow and sales-based forward valuation.",
    "Communication Services": "Subscriber or audience economics, EBITDA, capital intensity, cash conversion and enterprise valuation.",
    "Consumer Discretionary": "Demand growth, gross and operating margins, inventory discipline, cash conversion and earnings valuation.",
    "Consumer Staples": "Organic growth, margin resilience, cash conversion, dividends, leverage and earnings valuation.",
    "Consumer": "Consumer demand, margins, inventory discipline, cash generation and forward valuation.",
    "Healthcare": "Pipeline or product durability, R&D intensity, margins, cash generation and forward growth valuation.",
    "Banks / Financials": "Book-value compounding, returns on equity/assets, capital and credit quality, earnings valuation and dividends.",
    "Industrials": "Orders and backlog, operating leverage, capital intensity, free cash flow, leverage and enterprise valuation.",
    "Energy": "Production and commodity sensitivity, capital discipline, free cash flow, leverage, dividends and cycle-aware valuation.",
    "Materials": "Volume and pricing cycle, margins, capital intensity, free cash flow, leverage and enterprise valuation.",
    "Utilities": "Rate-base growth, regulated returns, dividend durability, financing needs, leverage and earnings valuation.",
    "Real Estate / REITs": "FFO/AFFO economics, occupancy and NOI, dividend coverage, leverage, asset value and refinancing risk.",
}


def map_sector_to_framework(sector_value: Any, industry_value: Any = "") -> str:
    """Map provider sector/industry labels to the same peer groups used by Equity Research."""
    sector = str(sector_value or "").strip().lower()
    industry = str(industry_value or "").strip().lower()
    text = f"{sector} {industry}".strip()
    if not text:
        return GENERAL_FRAMEWORK
    # Real estate is checked before financials because mortgage REIT profiles often contain both labels.
    if any(term in text for term in ("real estate", "reit", "mortgage")):
        return "Real Estate / REITs"
    if any(term in text for term in ("bank", "financial", "capital markets", "asset management", "insurance")):
        return "Banks / Financials"
    if any(term in text for term in ("technology", "software", "semiconductor", "information technology", "hardware")):
        return "Technology / Software / Semis"
    if any(term in text for term in ("communication", "telecom", "media", "entertainment")):
        return "Communication Services"
    if any(term in text for term in ("consumer cyclical", "consumer discretionary")):
        return "Consumer Discretionary"
    if any(term in text for term in ("consumer defensive", "consumer staples")):
        return "Consumer Staples"
    if any(term in text for term in ("health", "biotech", "pharma", "medical")):
        return "Healthcare"
    if "industrial" in text:
        return "Industrials"
    if any(term in text for term in ("energy", "oil", "gas")):
        return "Energy"
    if any(term in text for term in ("material", "chemical", "metals", "mining")):
        return "Materials"
    if any(term in text for term in ("utilities", "utility")):
        return "Utilities"
    if "consumer" in text:
        return "Consumer"
    return GENERAL_FRAMEWORK


def sector_frameworks(evidence: list[Any], symbols: list[str], comparison: list[dict] | None = None) -> list[dict]:
    """Describe sector priorities and coverage for every researched company."""
    rows = {str(row.get("Ticker")): row for row in (comparison or [])}
    output = []
    for symbol in symbols:
        profile_item = next((item for item in evidence if item.symbol == symbol and item.category == "profile"
                             and item.status == "ok"), None)
        profile = (profile_item.data[0] if profile_item and isinstance(profile_item.data, list) and profile_item.data
                   else profile_item.data if profile_item and isinstance(profile_item.data, dict) else {})
        sector, industry = profile.get("sector"), profile.get("industry")
        framework = map_sector_to_framework(sector, industry)
        registry = SECTOR_METRIC_REGISTRY[framework]
        row = rows.get(symbol, {})
        priorities = registry["must_have"] + registry["preferred"]
        available = [metric for metric in priorities if row.get(metric) is not None]
        unavailable = [metric for metric in registry["must_have"] if row.get(metric) is None]
        output.append({
            "symbol": symbol, "sector": sector or "Unknown", "industry": industry or "Unknown",
            "framework": framework, "description": SECTOR_DESCRIPTIONS[framework],
            "must_have": registry["must_have"], "preferred": registry["preferred"],
            "avoid_or_downweight": registry["avoid_or_downweight"],
            "available_priority_metrics": available,
            "unavailable_priority_metrics": unavailable,
            "missing_but_useful": registry["missing_but_useful"],
        })
    return output


def sector_prompt_context(frameworks: list[dict]) -> dict:
    """Deduplicate sector rules before sending them to the model."""
    definitions = {}
    companies = []
    for item in frameworks:
        name = item["framework"]
        definitions.setdefault(name, {
            "description": item["description"], "must_have": item["must_have"],
            "preferred": item["preferred"], "avoid_or_downweight": item["avoid_or_downweight"],
            "missing_but_useful": item["missing_but_useful"],
        })
        companies.append({key: item[key] for key in (
            "symbol", "sector", "industry", "framework",
            "available_priority_metrics", "unavailable_priority_metrics",
        )})
    return {
        "companies": companies,
        "frameworks": definitions,
        "cross_sector_note": "For mixed sectors, compare common measures only when economically comparable; evaluate each company first on its own sector drivers.",
    }
