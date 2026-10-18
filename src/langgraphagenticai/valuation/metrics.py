"""Valuation uses the app's canonical company metrics and technical calculations."""
from datetime import date
from langgraphagenticai.analysis.company_terminal import build_metrics, metric
from langgraphagenticai.deep_research.data import technical_snapshot
from langgraphagenticai.deep_research.sector import SECTOR_METRIC_REGISTRY
from langgraphagenticai.valuation.model import number


def company_metrics(raw, facts):
    first = lambda kind: (raw.get(kind) or [{}])[0]
    normalized_estimates = [{"date": r["date"], "epsAvg": r["eps"], "numAnalystsEps": r["analysts"], "reportedCurrency": r["currency"]} for r in facts["estimates"]]
    snapshot = dict(quote={"price": facts["price"], "currency": facts["quote_currency"], "timestamp": facts["quote_as_of"], "market_cap": first("quote").get("marketCap")}, profile=first("profile"), terminal_evidence={"ratios": first("ratios"), "metrics": first("metrics"), "income":raw.get("quarter_income",[]), "cashflow":raw.get("quarter_cashflow",[])})
    result = build_metrics(snapshot, annual=raw.get("income", []), estimates=normalized_estimates)
    ratio_keys={"pe_ttm","peg","price_to_sales","price_to_book","debt_to_equity","current_ratio","dividend_yield","gross_margin","operating_margin","net_margin"}
    for name, item in result.items():
        item["provider"] = "FMP / app calculation"
        kind="ratios" if name in ratio_keys else "estimates" if name=="pe_forward" else "income" if "cagr" in name else "quote" if name=="market_cap" else "profile" if name=="beta" else "metrics"
        if item.get("inputs") and name in {"gross_margin", "operating_margin", "net_margin", "revenue_growth", "fcf_margin"}:
            kind = "quarter_income"
        item["retrieved_at"] = raw.get("sources", {}).get(kind, {}).get("retrieved_at") or raw.get("retrieved_at")
        dates={r.get("date") for r in item.get("inputs",[]) if isinstance(r,dict) and r.get("date")}
        if name=="pe_forward" and item.get("as_of"):
            dates={item["as_of"]}
        item["source_ids"]=[f"{kind}:{i}" for i,r in enumerate(raw.get(kind,[])) if not dates or r.get("date") in dates]
        if name == "fcf_margin" and kind == "quarter_income":
            item["source_ids"] += [f"quarter_cashflow:{i}" for i,r in enumerate(raw.get("quarter_cashflow",[])) if r.get("date") in dates]
    if facts["method"] == "P/B" and facts["basis"] is not None:
        result["annual_common_bvps"] = {**metric(facts["basis"], basis=facts["formula"], unit="currency", as_of=facts["as_of"], currency=facts["currency"]), "source_ids":facts.get("basis_source_ids",[]), "provider":"Calculated from FMP annual evidence", "retrieved_at":facts["retrieved_at"]}
    provider_bvps = number(first("metrics").get("bookValuePerShareTTM"))
    if provider_bvps is not None:
        result["provider_bvps"] = {**metric(provider_bvps, basis="Provider book value per share; fiscal/common-equity denominator not independently verified; context only", unit="currency", currency=facts["currency"], as_of=first("metrics").get("date")), "source_ids":["metrics:0"], "provider":"FMP", "retrieved_at":raw.get("sources",{}).get("metrics",{}).get("retrieved_at")}
    history = sorted(facts["history"], key=lambda r:r["date"], reverse=True)
    if len(history) >= 2:
        latest, prior = history[:2]
        gap = (date.fromisoformat(latest["date"]) - date.fromisoformat(prior["date"])).days
        if 330 <= gap <= 400 and prior["value"] > 0:
            result["annual_per_share_growth"] = metric(latest["value"] / prior["value"] - 1, basis=f"Calculated annual {facts['method']} basis YoY; not a forecast", unit="fraction", as_of=latest["date"], currency=facts["currency"], inputs=history[:2])
            if facts["method"] == "P/B":
                result["annual_per_share_growth"].update(source_ids=list(dict.fromkeys(ref for row in history[:2] for ref in row.get("source_ids",[]))), provider="Calculated from FMP annual evidence", retrieved_at=facts["retrieved_at"])
    annual = sorted([r for r in raw.get("income", []) if r.get("period") == "FY" and r.get("date") == facts["as_of"] and r.get("reportedCurrency")==facts["currency"]], key=lambda r:r["date"], reverse=True)
    if annual:
        row = annual[0]
        revenue = number(row.get("revenue"))
        if revenue and revenue > 0:
            for key, field in (("annual_gross_margin", "grossProfit"), ("annual_operating_margin", "operatingIncome"), ("annual_net_margin", "netIncome")):
                value = number(row.get(field))
                result[key] = metric(value / revenue if value is not None else None, basis="Calculated annual FY", unit="fraction", as_of=row["date"], currency=facts["currency"], fields=(field,"revenue"))
            matching = [r for r in raw.get("cashflow", []) if r.get("symbol") == facts["symbol"] and r.get("period") == "FY" and r.get("date") == row["date"] and r.get("reportedCurrency") == facts["currency"]]
            if len(matching) == 1:
                fcf = number(matching[0].get("freeCashFlow"))
                result["annual_fcf_margin"] = metric(fcf / revenue if fcf is not None else None, basis="Calculated matching annual FY income and cash flow", unit="fraction", as_of=row["date"], currency=facts["currency"], fields=("freeCashFlow","revenue"))
    tech = technical_snapshot(raw.get("history", []))
    tech.pop("series", None)
    # Keep the existing sector priorities visible; no universal EV/EBITDA narrative for banks/REITs.
    priorities = SECTOR_METRIC_REGISTRY[facts["framework"]]
    projected = {}
    excluded = set(priorities["avoid_or_downweight"])
    labels = {"pe_ttm": "P/E TTM", "pe_forward": "Forward P/E", "price_to_sales": "P/S TTM", "price_to_book": "P/B TTM", "ev_ebitda": "EV / EBITDA", "fcf_margin": "FCF Margin", "annual_fcf_margin": "FCF Margin"}
    for key, item in result.items():
        if item.get("value") is not None and labels.get(key) not in excluded:
            if "source_ids" not in item:
                kind="balance" if key=="annual_per_share_growth" and facts["method"]=="P/B" else "income"
                dates={r.get("date") for r in item.get("inputs",[]) if isinstance(r,dict)} or {item.get("as_of")}
                item["source_ids"]=[f"{kind}:{i}" for i,r in enumerate(raw.get(kind,[])) if r.get("date") in dates]
                if key=="annual_fcf_margin":
                    item["source_ids"] += [f"cashflow:{i}" for i,r in enumerate(raw.get("cashflow",[])) if r.get("date")==item.get("as_of") and r.get("reportedCurrency")==facts["currency"]]
                item["provider"]="Calculated from FMP annual evidence"
                item["retrieved_at"]=raw.get("sources",{}).get(kind,{}).get("retrieved_at")
            projected[key] = {k:v for k,v in item.items() if k not in {"inputs", "raw"} and v not in (None, "", (), [])}
    analyst = []
    for row in raw.get("targets", []):
        if row.get("currency") and row["currency"]!=facts["quote_currency"]:
            continue
        for window in ("Month", "Quarter"):
            target, count = number(row.get(f"last{window}AvgPriceTarget")), number(row.get(f"last{window}Count"))
            if target is not None and target > 0 and count is not None and count >= 1 and count.is_integer():
                analyst.append(dict(window=window, target=target, analysts=count, currency_basis="same-listing-currency assumption; target currency not supplied", horizon="publication window; target horizon unspecified", retrieved_at=raw.get("sources", {}).get("targets", {}).get("retrieved_at")))
    return dict(fundamentals=projected, technicals=tech, analyst_targets=analyst, sector_priorities=priorities["must_have"][:18], missing_context=["Peer multiples and macro outlook are not collected; do not fabricate them."])
