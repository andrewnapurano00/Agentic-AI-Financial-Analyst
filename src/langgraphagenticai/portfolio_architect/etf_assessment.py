"""Fund allocation hypotheses from curated categories and saved observations only."""
from datetime import date
from math import isfinite, sqrt
from statistics import stdev


def assess_etf(security):
    category = security.sector
    if category == "ETF Treasuries":
        role, driver, risk = "Treasury allocation", "Changes in Treasury yields and carry", "Rate increases can reduce bond prices; duration and yield unavailable"
    elif category == "ETF bonds":
        role, driver, risk = "Diversified bond allocation", "Interest rates, credit spreads and carry", "Credit and duration risk; constituent quality, yield and duration unavailable"
    elif category == "ETF gold":
        role, driver, risk = "Gold diversifier", "Gold prices, real yields and currency conditions", "No earnings anchor; gold can fall alongside equities"
    elif category == "ETF broad equity":
        role, driver, risk = "Core equity allocation", "Underlying company earnings and market valuations", "Equity drawdowns and overlap with other equity holdings"
    elif category == "ETF dividend":
        role, driver, risk = "Dividend equity allocation", "Underlying dividends and company earnings", "Dividend cuts, sector concentration and equity drawdowns"
    elif category == "ETF small cap":
        role, driver, risk = "Small-cap equity satellite", "Smaller-company earnings and financing conditions", "Cyclical and financing sensitivity; category does not establish diversification"
    else:
        role, driver, risk = "Growth or sector equity satellite", "Underlying sector earnings and valuation changes", "Sector/style concentration and overlap with broad equity funds"
    prices, days = [], []
    for day, value in sorted(security.history.items()):
        try:
            date.fromisoformat(day)
            price = float(value)
        except (ValueError, TypeError):
            continue
        if isfinite(price) and price > 0:
            prices.append(price)
            days.append(day)
    observed = {}
    if len(prices) >= 61:
        returns = [b/a-1 for a,b in zip(prices, prices[1:])]
        peak, drawdown = prices[0], 0.
        for price in prices:
            peak = max(peak, price)
            drawdown = min(drawdown, price/peak-1)
        observed = {"annualized_volatility":stdev(returns)*sqrt(252),
                    "maximum_drawdown":drawdown, "observations":len(prices),
                    "start":days[0], "end":days[-1], "retrieved_at":security.history_retrieved_at,
                    "source":security.provider, "basis":security.history_basis,
                    "convention":"Daily observed price returns; sample standard deviation x sqrt(252); no dividend cash flows; gaps not filled. Historical, not forecast."}
    return {"framework":"ETF allocation", "role":role, "conditional_driver":driver,
            "risk":risk, "observed_history":observed,
            "missing_required":["Dated fund fees", "Constituent holdings and overlap", "Tracking difference", "Dated NAV and compatible market price"],
            "specialist_gaps":["Duration, credit quality and yield for bond funds", "Underlying valuation for equity funds"],
            "valuation_status":"Unavailable; company P/E, ROE and margins are inapplicable. Price history is not fair value.",
            "policy":"Curated category is a research hypothesis, not verified constituent exposure. No measured diversification or future-loss promise."}
