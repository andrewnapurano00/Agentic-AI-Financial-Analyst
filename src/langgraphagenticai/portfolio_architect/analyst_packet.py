"""Sector-aware bounded model evidence, separate from provider collection."""
import json
import numpy as np
from .screening import sector_lens, metric_weights
from .risk import aligned_returns
from .mandate_fit import mandate_priority

PACKET_BYTE_LIMIT = 42000


def encode_packet(packet):
    """Use the same UTF-8 wire encoding for budgeting and model submission."""
    return json.dumps(packet, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def review_pool(securities, ranked, local_selection):
    names = {s.ticker for s in local_selection}
    for candidate in ranked:
        if len(names) >= 20:
            break
        names.add(candidate.ticker)
    return [s for s in securities if s.ticker in names]


def research_packet(securities, scores, mandate, macro=None, sector_screen=None, required_tickers=None):
    ranks = {s.ticker:s.score for s in scores}
    peers = {r["symbol"]:r for r in (sector_screen or {}).get("ranked", [])}
    rows = []
    for s in securities:
        weights = metric_weights(s.sector) if s.asset == "stock" else {}
        facts = [f for f in s.facts if f.field in weights or f.field in {"price", "screen_score", "revenue_cagr_3y"}]
        facts.sort(key=lambda f: (-weights.get(f.field, 1.5 if f.field == "revenue_cagr_3y" else 0), f.field))
        # Keep substantive ratios first; price and composites cannot alone justify a stock thesis.
        chosen = facts[:8]
        growth = next((f for f in facts if f.field == "revenue_cagr_3y"),None)
        if mandate.investment_style == "growth" and growth is not None and growth not in chosen:
            chosen[-1] = growth
        lens = sector_lens(s)
        components = peers.get(s.ticker, {}).get("components", {})
        packed_facts = []
        for fact in chosen:
            item = fact.model_dump(mode="json")
            if fact.field in components:
                item["sector_peer_rank"] = {k:components[fact.field].get(k) for k in ("percentile", "peer_count", "priority_weight")}
            packed_facts.append(item)
        rows.append({"ticker":s.ticker, "asset":s.asset, "category":s.sector, "themes":s.themes,
                     "sector_lens":{"framework":lens["framework"], "missing_required":lens["missing_required"][:5], "missing_required_count":len(lens["missing_required"]), "specialist_gaps":lens.get("specialist_gaps",[])[:3]},
                     **({"fund_assessment":{k:v for k,v in lens.items() if k in {"role", "conditional_driver", "risk", "observed_history", "valuation_status", "policy"}}} if s.asset == "etf" else {}),
                     "facts":packed_facts,
                     "provider":s.provider, "retrieved_at":s.retrieved_at,
                     "local_priority":ranks.get(s.ticker), "mandate_fit":{k:v for k,v in mandate_priority(s,mandate,0)[2].items() if k != "policy"},
                     "business_context":s.business_summary[:350], "flags":s.flags[:2],
                     "news":[{k:n.get(k) for k in ("id", "title", "published_date", "retrieved_at", "source")} for n in s.news[:1]],
                     "omitted_facts":len(s.facts)-len(chosen), "omitted_news":max(0,len(s.news)-1)})
    packet = {"mandate":mandate.model_dump(), "macro":macro or {}, "candidates":rows,
              "policy":"Provider TTM fiscal end unavailable unless dated. Annual revenue CAGR is separate from TTM/forecasts. Missing metrics remain unknown. Headlines do not establish catalysts. Local priority is descriptive, not expected return."}
    returns, note = aligned_returns(securities)
    if returns is None:
        packet["historical_risk"] = {"status":"unavailable", "reason":note}
    else:
        corr = returns.corr().fillna(0)
        packet["historical_risk"] = {"status":"available", "observations":len(returns), "end":str(returns.index[-1]),
            "basis":"Aligned daily price returns; sample volatility annualized at 252 sessions; no forward risk/return prediction.",
            "annualized_volatility":{n:float(v) for n,v in (returns.std(ddof=1)*np.sqrt(252)).items()},
            "high_correlations":[{"a":a,"b":b,"correlation":float(corr.loc[a,b])} for i,a in enumerate(corr.columns) for b in corr.columns[i+1:] if corr.loc[a,b] > .85][:10]}
    # Intern repeated metadata without truncating dates, source identities or formulas.
    # Each retained value/unit/ID resolves to its exact original metadata record.
    provenance, identifiers = {}, {}
    for row in rows:
        for fact in row["facts"]:
            metadata = {k:fact.pop(k) for k in ("source","basis","as_of","retrieved_at")}
            identity = encode_packet(metadata)
            if identity not in identifiers:
                ref = f"P{len(identifiers)+1}"
                identifiers[identity] = ref
                provenance[ref] = metadata
            fact["provenance_id"] = identifiers[identity]
    packet["provenance"] = provenance
    packet["provenance_policy"] = "Each fact inherits exact source, basis, as_of and retrieved_at from provenance[provenance_id]. Unit/value/ID remain on the fact."
    packet["omitted_candidates"] = []

    if required_tickers is None:
        from .optimizer import select
        required_tickers = {s.ticker for s in select(securities,scores,mandate)}
    required_tickers = set(required_tickers)
    if not required_tickers <= {r["ticker"] for r in rows}:
        raise ValueError("Required portfolio holdings are missing from the review packet.")

    def prune_provenance():
        used = {f["provenance_id"] for row in rows for f in row["facts"]}
        packet["provenance"] = {k:v for k,v in provenance.items() if k in used}

    # Retain complete provenance for every sent fact; explicitly count omissions.
    def size():
        prune_provenance()
        return len(encode_packet(packet).encode("utf-8"))
    if size() > PACKET_BYTE_LIMIT:
        # Macro narratives are optional context, never allowed to crowd out company facts.
        packet["macro"] = {"status":(macro or {}).get("status","unavailable"),
                           "omitted_for_budget":True, "note":"Full saved macro context remains in the report."}
        for row in rows:
            row["omitted_news"] += len(row["news"])
            row["news"] = []
            row["flags"] = ["See saved evidence for complete provider warnings."]
            row["business_context"] = "See saved issuer description; mandate_fit retains its classification basis."
    while size() > PACKET_BYTE_LIMIT:
        removable = [r for r in rows if len(r["facts"]) > (3 if r["asset"] == "stock" else 1)]
        if not removable:
            optional = [r for r in rows if r["ticker"] not in required_tickers]
            if optional:
                row = min(optional,key=lambda r:(ranks.get(r["ticker"],0),r["ticker"]))
                rows.remove(row)
                packet["omitted_candidates"].append(row["ticker"])
                risk = packet["historical_risk"]
                if risk.get("status") == "available":
                    risk["annualized_volatility"].pop(row["ticker"],None)
                    risk["high_correlations"] = [p for p in risk["high_correlations"] if row["ticker"] not in (p["a"],p["b"])]
                continue
            raise ValueError("Sector research packet cannot fit the 42KB evidence budget.")
        row = max(removable, key=lambda r:len(r["facts"]))
        protected = {"revenue_cagr_3y"} if mandate.investment_style == "growth" else set()
        removable_indices = [i for i,f in enumerate(row["facts"]) if f["field"] not in protected]
        row["facts"].pop(removable_indices[-1])
        row["omitted_facts"] += 1
    return packet
