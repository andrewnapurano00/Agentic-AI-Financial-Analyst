"""Disclosed first-pass methods supplement specialist valuation inputs."""
from datetime import datetime


LIMITATIONS = {
    "Real Estate / REITs": "Earnings P/E is a provisional REIT/real-estate proxy. Depreciation and property gains can distort EPS; FFO/AFFO, occupancy and asset NAV are unavailable. FFO/AFFO and NAV valuation require additional inputs.",
    "Materials": "Earnings are not validated as normalized or mid-cycle. Commodity prices, volumes and input costs can materially change earnings; no commodity-price deck or mine/reserve NAV is supplied.",
    "General / Cross-Sector": "Sector classification is unavailable. Company earnings, history and available forecasts provide the basis; sector benchmarks and specialist metrics are unavailable.",
    "Utilities": "P/E is a first-pass earnings framework. Rate-base growth, allowed regulatory returns and a dividend-discount valuation are not independently modeled.",
    "Industrials": "Latest annual EPS is a first-pass input, not normalized cycle earnings; cycle position can change earnings and exit multiples.",
    "Banks / Financials": "Common-book-value P/B is a first-pass financials framework, not a full bank, insurer or asset-manager specialist model.",
}


def source_current(sources, kind, now):
    try:
        stamp = datetime.fromisoformat(str(sources.get(kind, {}).get("retrieved_at", "")).replace("Z", "+00:00"))
        return stamp.tzinfo is not None and 0 <= (now - stamp).total_seconds() <= 86400
    except (ValueError, TypeError):
        return False


def usable_book(balance, contract, sources, currencies, now):
    """Optional book method must satisfy its own date/currency/source contract."""
    try:
        dated = datetime.strptime(balance.get("date", ""), "%Y-%m-%d").date()
        value = contract.get("value")
        return bool(value is not None and value > 0 and 0 <= (now.date() - dated).days <= 550
                    and balance.get("reportedCurrency") in currencies and len(currencies) == 1
                    and source_current(sources, "balance", now)
                    and (contract.get("reported_index") is None or source_current(sources, "balance_reported", now)))
    except (ValueError, TypeError):
        return False


def earnings_basis(row, *, allow_proxy=False):
    from .model import number
    eps = number(row.get("epsDiluted"))
    shares, profit = number(row.get("weightedAverageShsOutDil")), number(row.get("netIncome"))
    proxy = row.get("epsDiluted") is None and allow_proxy and profit is not None and profit > 0 and shares is not None and shares > 0
    return (number(profit / shares) if proxy else eps), proxy


def method_disclosure(framework, method, *, financial_fallback=False, earnings_proxy=False):
    label = method
    note = LIMITATIONS.get(framework, "")
    if method == "P/E" and framework in {"Real Estate / REITs", "Materials", "General / Cross-Sector"}:
        label = "Provisional earnings P/E"
    if framework == "Energy":
        label = "Conditional Energy P/E"
        note = "Conditional Energy P/E scenarios use reported annual or eligible annual consensus EPS, not validated normalized or mid-cycle earnings. Commodity prices, production, refining margins and capital spending can materially change earnings; no commodity-price deck, reserves/NAV model or mid-cycle valuation is supplied."
    if financial_fallback:
        label = "Financials earnings P/E fallback"
        note = "Usable annual common book value is unavailable. Conditional P/E uses annual earnings or eligible annual consensus EPS; no P/B, tangible-book or regulatory-capital valuation is implied."
    if earnings_proxy:
        note = note.replace("use reported annual or eligible annual consensus EPS", "use the disclosed historical earnings-per-share proxy")
        label += " (earnings proxy)"
        note += " Reported diluted EPS is unavailable: historical earnings per diluted share is calculated as annual net income / annual diluted weighted-average shares. This proxy does not establish income attributable to common shareholders or reported diluted EPS. Consensus EPS remains context only for this proxy; it is not substituted into the numeric anchor."
    return label, note.strip()
