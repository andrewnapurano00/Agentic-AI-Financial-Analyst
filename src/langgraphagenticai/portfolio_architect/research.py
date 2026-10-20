"""Deterministic demo, eligibility audit and modest descriptive ranking."""
from datetime import date, datetime, timedelta, timezone
from math import exp, sin
from .schemas import EvidenceSnapshot, SecurityEvidence, Fact, CandidateScore, utc_stamp
from .universe import UNIVERSE, ETFS, UNIVERSE_VERSION
from langgraphagenticai.providers.portfolio_architect import snapshot_id, HISTORY_BASIS


def demo_snapshot(names, benchmark):
    # Fixed synthetic clock makes repeated inputs and diagnostics reproducible.
    stamp = "2026-10-19T12:00:00+00:00"
    dates = [(date(2025, 6, 1)+timedelta(days=i)).isoformat() for i in range(502)
             if (date(2025, 6, 1)+timedelta(days=i)).weekday() < 5]
    values = {}
    for s in sorted(set(names) | {benchmark}):
        i = sorted(UNIVERSE).index(s)
        history, price = {}, 60.+i*3
        for j, day in enumerate(dates):
            price *= exp(.00015+.008*sin(j*.21+i*.7)+.004*sin(j*.57+i))
            history[day] = price
        fs = [("price", price, "USD/share", "synthetic point-in-time"), ("margin_ttm", .05+i*.004, "fraction", "synthetic TTM"),
              ("pe_ttm", 12.+i, "multiple", "synthetic TTM"), ("debt_equity_ttm", .2+i*.02, "multiple", "synthetic TTM")]
        facts = [Fact(id=s+":"+f, field=f, value=v, unit=u, basis=b, as_of=stamp, retrieved_at=stamp, source="SYNTHETIC DEMO") for f,v,u,b in fs]
        values[s] = SecurityEvidence(ticker=s, name=s+" synthetic example", asset="etf" if s in ETFS else "stock",
                                    sector=UNIVERSE[s][0], themes=UNIVERSE[s][1], price=price, currency="USD", currency_basis="Synthetic USD",
                                    quote_as_of=stamp, retrieved_at=stamp, provider="SYNTHETIC DEMO", facts=facts, history=history,
                                    history_retrieved_at=stamp, history_basis="Synthetic prices; no real market observations.",
                                    flags=["All values and history are invented for software demonstration."])
    packet = dict(mode="SYNTHETIC DEMO", retrieved_at=stamp, securities=[values[s].model_dump() for s in names],
                  benchmark=values[benchmark].model_dump(), warnings=["SYNTHETIC DEMO: not live research or historical market performance."],
                  excluded={}, universe_version=UNIVERSE_VERSION)
    return EvidenceSnapshot(id=snapshot_id(packet), **packet)


def candidates(snapshot, mandate, now=None):
    now = now or datetime.now(timezone.utc)
    excluded = dict(snapshot.excluded)
    selected, scores = [], []
    for s in snapshot.securities:
        reason = None
        if s.ticker in mandate.forbidden:
            reason = "Forbidden ticker"
        elif mandate.assets != "both" and (s.asset == "etf") != (mandate.assets == "etfs"):
            reason = "Asset class excluded"
        elif s.sector.lower() in {v.lower() for v in mandate.excluded_sectors}:
            reason = "Sector excluded"
        elif s.asset == "etf" and mandate.excluded_sectors:
            reason = "ETF excluded: sector exclusions cannot be certified without look-through"
        elif snapshot.mode == "FMP live":
            if s.provider != "FMP" or not 0 <= (now-utc_stamp(s.quote_as_of)).total_seconds() <= 7*86400:
                reason = "Invalid/stale/future quote observation"
            elif not 0 <= (now-utc_stamp(s.retrieved_at)).total_seconds() <= 900:
                reason = "Saved quote retrieval older than fifteen minutes; explicit refresh required"
        if reason:
            excluded[s.ticker] = reason
            continue
        fs = {f.field: f for f in s.facts}
        pros = ["Dated USD quote available.", "Eligible within the explicit curated research universe."]
        cons = ["Past observations do not establish future returns.", "No current news or forward earnings evidence collected."]
        score = 1.0 + .3*len(set(s.themes)&set(mandate.themes))
        # Stock-only, broad descriptive heuristics; not sector-normalized valuation.
        if s.asset == "stock" and fs.get("margin_ttm") and fs["margin_ttm"].value > 0:
            score += .2
            pros.append("Provider TTM net margin is positive; fiscal end may be unavailable.")
        if s.asset == "stock" and fs.get("pe_ttm") and fs["pe_ttm"].value <= 0:
            cons.append("Provider earnings multiple is nonpositive; valuation inference is unsupported.")
        if s.asset == "etf":
            cons.append("Fund constituents and sector look-through unmeasured; category is not underlying exposure.")
        if mandate.risk == "conservative" and "defensive" in s.themes:
            score += .4
        if len(s.history) < 61:
            cons.append("Insufficient history for risk sizing.")
        selected.append(s)
        scores.append(CandidateScore(ticker=s.ticker, score=score, citations=[f.id for f in s.facts], pros=pros[:4], cons=cons[:4]))
    return selected, sorted(scores, key=lambda v: (-v.score, v.ticker)), excluded
