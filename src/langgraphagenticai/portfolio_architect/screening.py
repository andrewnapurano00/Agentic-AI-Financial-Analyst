"""Auditable sector-relative screening; provider TTM ratios are not audited statements."""
from collections import defaultdict
from datetime import datetime, timezone
from .schemas import Fact
from langgraphagenticai.deep_research.sector import map_sector_to_framework, SECTOR_METRIC_REGISTRY
from langgraphagenticai.providers.discovery_numbers import finite_number

# Same concepts/applicability registry as Equity Report; never reuse its legacy scores.
METRICS = {
    "margin_ttm": ("netProfitMarginTTM", "Latest Net Margin", "fraction", True),
    "operating_margin_ttm": ("operatingProfitMarginTTM", "Latest Operating Margin", "fraction", True),
    "roe_ttm": ("returnOnEquityTTM", "ROE", "fraction", True),
    "roa_ttm": ("returnOnAssetsTTM", "ROA", "fraction", True),
    "roic_ttm": ("returnOnInvestedCapitalTTM", "ROIC", "fraction", True),
    "fcf_yield_ttm": ("freeCashFlowYieldTTM", "FCF Yield", "fraction", True),
    "pe_ttm": ("priceToEarningsRatioTTM", "P/E TTM", "multiple", False),
    "pb_ttm": ("priceToBookRatioTTM", "P/B TTM", "multiple", False),
    "debt_assets_ttm": ("debtToAssetsRatioTTM", "Debt / Assets", "fraction", False),
    "debt_equity_ttm": ("debtToEquityRatioTTM", "Debt to Equity", "multiple", False),
    "gross_margin_ttm": ("grossProfitMarginTTM", "Latest Gross Margin", "fraction", True),
    "ebitda_margin_ttm": ("ebitdaMarginTTM", "Latest EBITDA Margin", "fraction", True),
    "ps_ttm": ("priceToSalesRatioTTM", "P/S TTM", "multiple", False),
    "pfcf_ttm": ("priceToFreeCashFlowRatioTTM", "P/FCF TTM", "multiple", False),
    "debt_capital_ttm": ("debtToCapitalRatioTTM", "Debt / Capital", "fraction", False),
    "debt_service_ttm": ("debtServiceCoverageRatioTTM", "Debt Service Coverage", "multiple", True),
    "dividend_yield_ttm": ("dividendYieldTTM", "Dividend Yield", "fraction", True),
}
KEY_FIELDS = {"roe_ttm", "roa_ttm", "roic_ttm", "fcf_yield_ttm"}
POSITIVE_MULTIPLES = {"pe_ttm", "pb_ttm", "ps_ttm", "pfcf_ttm", "debt_service_ttm"}
NONNEGATIVE = {"debt_equity_ttm", "debt_assets_ttm", "debt_capital_ttm", "dividend_yield_ttm"}


def metric_facts(symbol, ratios, metrics, retrieved_at, source_suffix=""):
    result = []
    for field, (key, _, unit, _) in METRICS.items():
        row = metrics if field in KEY_FIELDS else ratios
        value = finite_number(row.get(key))
        if value is None:
            continue
        route = "key-metrics-ttm" if field in KEY_FIELDS else "ratios-ttm"
        result.append(Fact(id=f"{symbol}:{field}", field=field, value=value, unit=unit,
            basis="provider TTM; fiscal end unavailable; not independently audited",
            as_of=None, retrieved_at=retrieved_at, source="FMP stable/"+route+source_suffix))
    return result


def applicable(sector):
    framework = map_sector_to_framework(sector)
    avoided = SECTOR_METRIC_REGISTRY[framework]["avoid_or_downweight"]
    fields = [f for f, (_, label, _, _) in METRICS.items() if label not in avoided]
    if framework == "Banks / Financials":
        fields = [f for f in fields if f not in {"fcf_yield_ttm", "roic_ttm", "debt_equity_ttm", "debt_assets_ttm", "debt_capital_ttm", "debt_service_ttm", "operating_margin_ttm", "ps_ttm"}]
    return framework, fields


def metric_weights(sector):
    """Shared Equity Report priorities, applied only to collected comparable metrics."""
    framework, fields = applicable(sector)
    registry = SECTOR_METRIC_REGISTRY[framework]
    return {f: 2. if METRICS[f][1] in registry["must_have"] else
            1. if METRICS[f][1] in registry["preferred"] else .5 for f in fields}


def sector_lens(security):
    if security.asset == "etf":
        return {"framework":"ETF category", "available":[], "missing_required":["Fund holdings look-through, fees and duration"],
                "policy":"Company profitability and valuation ratios are inapplicable to funds."}
    framework, fields = applicable(security.sector)
    labels = {METRICS[f.field][1] for f in security.facts if f.field in fields}
    if any(f.field == "revenue_cagr_3y" for f in security.facts):
        labels.add("Revenue CAGR 3Y")
    priorities = SECTOR_METRIC_REGISTRY[framework]
    return {"framework":framework, "available":sorted(labels),
            "missing_required":[v for v in priorities["must_have"] if v not in labels],
            "specialist_gaps":priorities["missing_but_useful"],
            "policy":"Equity Report applicability/priorities; provider TTM ratios and separate annual growth only. Not full Equity Report coverage or audited-statement parity."}


def rank_rows(rows):
    """Fixed sector-priority denominator penalizes missing evidence; midrank, n>=3."""
    groups = defaultdict(list)
    for row in rows:
        groups[map_sector_to_framework(row["sector"])].append(row)
    for group in groups.values():
        for row in group:
            framework, fields = applicable(row["sector"])
            weights = metric_weights(row["sector"])
            values = row["values"]
            usable = {f: values[f] for f in fields if f in values and
                      (f not in POSITIVE_MULTIPLES or values[f] > 0) and
                      (f not in NONNEGATIVE or values[f] >= 0)}
            coverage = sum(weights[f] for f in usable)/sum(weights.values())
            reasons = []
            if framework == "General / Cross-Sector":
                reasons.append("Unclassified sector; sector-relative quality cannot be established")
            if framework == "Real Estate / REITs":
                reasons.append("Specialist FFO/AFFO/NOI unavailable; generic ratios cannot establish REIT quality")
            if values.get("margin_ttm", 0) <= 0 or values.get("roa_ttm", 0) <= 0:
                reasons.append("Positive TTM net margin and ROA required")
            if coverage < .6:
                reasons.append("Applicable metric coverage below 60%")
            score, components = 0., {}
            for field, value in usable.items():
                peers = [p["values"].get(field) for p in group]
                peers = [v for v in peers if v is not None and
                         (field not in POSITIVE_MULTIPLES or v > 0) and
                         (field not in NONNEGATIVE or v >= 0)]
                if len(peers) < 3:
                    continue
                lower = sum(v < value for v in peers)
                tied = sum(v == value for v in peers)
                percentile = (lower + (tied-1)/2)/(len(peers)-1)
                if not METRICS[field][3]:
                    percentile = 1-percentile
                components[field] = {"value": value, "peer_count": len(peers), "percentile": percentile,
                                     "priority_weight":weights[field], "score_contribution":percentile*weights[field]/sum(weights.values())*100}
                score += components[field]["score_contribution"]
            if len(components) < 3:
                reasons.append("Fewer than three metrics with at least three sector peers")
            row.update(framework=framework, coverage=coverage, score=score, components=components, metric_weights=weights,
                       exclusion="; ".join(reasons))
    return sorted(rows, key=lambda r: (-r["score"], r["symbol"]))


def shortlist(ranked, mandate, limit=30):
    eligible = [r for r in ranked if not r["exclusion"] and r["symbol"] not in mandate.forbidden
                and map_sector_to_framework(r["sector"]) not in {map_sector_to_framework(s) for s in mandate.excluded_sectors}]
    if mandate.investment_style == "growth" and "AI" in mandate.themes:
        from .mandate_fit import AI_SECTOR_PROXIES
        # Reserve research capacity for possible theme candidates before full issuer evidence exists.
        # Sector membership is only a collection proxy; final ranking uses issuer metadata and annual growth.
        proxies = [r for r in eligible if r["framework"] in AI_SECTOR_PROXIES]
        chosen = [r["symbol"] for r in proxies[:min(20,limit)]]
        chosen += [r["symbol"] for r in eligible if r["symbol"] not in chosen][:limit-len(chosen)]
        return tuple(chosen)
    # First preserve two leaders per framework, then fill by global sector-relative score.
    selected, counts = [], defaultdict(int)
    for row in eligible:
        if counts[row["framework"]] < 2 and len(selected) < limit:
            selected.append(row["symbol"])
            counts[row["framework"]] += 1
    for row in eligible:
        if row["symbol"] not in selected and len(selected) < limit:
            selected.append(row["symbol"])
    return tuple(selected)


def macro_assessment(packet, now=None):
    now = now or datetime.now(timezone.utc)
    observations, risks, upside = [], [], []
    for row in packet.get("rows", []):
        if row.get("Group") != "Macro":
            continue
        evidence = row.get("evidence", {})
        stamp = evidence.get("as_of")
        try:
            instant = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if instant.tzinfo is None:
                instant = instant.replace(tzinfo=timezone.utc)  # daily observation, timing unknown
            valid = 0 <= (now-instant).total_seconds() <= 7*86400 and evidence.get("stale") is False
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            continue
        name = row.get("Instrument")
        level = finite_number(row.get("Level"))
        trend = finite_number(row.get("vs SMA 200 %"))
        move = finite_number(row.get("30D %"))
        try:
            indicator_day = datetime.fromisoformat(evidence["indicator_date"][:10]).date()
            if not 0 <= (now.date()-indicator_day).days <= 7:
                trend, move = None, None
        except (ValueError, TypeError, KeyError):
            trend, move = None, None
        observations.append({"instrument": name, "level": level, "vs_sma200_pct": trend,
                             "30_session_price_change_pct": move, "as_of": stamp, "evidence": evidence})
        if name == "VIX" and level is not None:
            (risks if level >= 25 else upside).append(f"VIX {level:.1f}: "+("elevated implied volatility; equity stress risk" if level >= 25 else "below the 25 stress threshold; shocks remain possible"))
        if name == "S&P 500" and trend is not None:
            (risks if trend < 0 else upside).append(f"S&P 500 {trend:+.1f}% versus 200-bar SMA: trend "+("headwind" if trend < 0 else "tailwind"))
        if name in {"US 10Y yield index", "US Dollar", "Oil"} and move is not None:
            risks.append(f"{name} {move:+.1f}% over 30 observed sessions: monitor financing, currency or input-cost sensitivity; relative price/index change, not a yield percentage-point move")
    return {"provider": packet.get("provider", "FMP"), "retrieved_at": packet.get("retrieved_at"),
            "status": "partial" if len(observations) < 5 else "available", "observations": observations,
            "risks": risks, "upside": upside, "warnings": packet.get("warnings", []),
            "policy": "Descriptive thresholds, not a return forecast. Market proxies do not measure GDP, inflation or policy surprises. Cash and hard caps remain user assumptions."}


def position_tradeoffs(security, macro):
    framework, _ = applicable(security.sector)
    sensitivity = {
        "Banks / Financials": "Credit losses, deposit costs and yield-curve changes can offset a low earnings/book multiple; capital adequacy is unmeasured.",
        "Technology / Software / Semis": "Higher discount rates and capex expectations can overwhelm strong margins; competition and execution remain unmeasured.",
        "Energy": "Oil/gas price reversals can erase apparent cash-flow value; current TTM profitability may be cyclical.",
        "Utilities": "Refinancing costs and regulatory decisions can offset defensive demand; rate-base and allowed returns are unmeasured.",
    }.get(framework, "Demand weakness, input-cost inflation and financing conditions can reverse current profitability; company-specific execution remains unmeasured.")
    if security.asset == "etf":
        sensitivity = "Diversifies issuer exposure but adds fund fees, duration/category risk and unmeasured overlap; company fundamentals are inapplicable."
    specific = []
    facts = {f.field:f for f in security.facts}
    for field, threshold, label in (("pe_ttm", 30, "Earnings multiple exceeds 30x; slower growth could cause multiple compression"),
                                   ("debt_assets_ttm", .5, "Debt/assets exceeds 50%; financing and refinancing deserve scrutiny")):
        if field in facts and facts[field].value > threshold:
            specific.append(f"{label} [{facts[field].id}]. Threshold is a research heuristic, not fair value/default probability.")
    if "fcf_yield_ttm" in facts and facts["fcf_yield_ttm"].value <= 0:
        specific.append(f"Nonpositive provider FCF yield weakens cash-generation support [{facts['fcf_yield_ttm'].id}].")
    catalyst = "Conditional catalyst to investigate: sustained earnings/cash-flow improvement in the next issuer filing; no dated company event is verified."
    if security.asset == "etf":
        catalyst = "Conditional fund driver to investigate: changes in underlying index earnings, yields or commodity prices; fund-specific event impact unverified."
    return [sensitivity] + specific + macro.get("risks", [])[:2], [
        catalyst,
        *["Conditional market tailwind: "+v for v in macro.get("upside", [])[:2]]]
