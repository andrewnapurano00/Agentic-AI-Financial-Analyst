"""One evidence snapshot per explicit build; local result survives failed AI review."""
from hashlib import sha256
import json
from .schemas import PortfolioRecommendation, HoldingRecommendation, CommitteeReview, CandidateScore
from .research import candidates
from .optimizer import select, allocate, dollar_allocations
from .risk import diagnostics
from .universe import OVERLAP_GROUPS
from .committee import review


def build(snapshot, mandate, api_key="", model="", use_ai=False):
    securities, ranked, excluded = candidates(snapshot, mandate)
    local_selection = select(securities, ranked, mandate)
    initial = {s.ticker:(1-mandate.cash)/mandate.holdings for s in local_selection}
    warnings = list(snapshot.warnings)
    conviction, usage, source = {}, [], "Deterministic specialist responsibilities; no AI opinions used"
    ai_rejected, ai_concerns = {}, []
    chosen = local_selection
    if use_ai:
        try:
            output, consumed = review(securities, ranked, mandate, api_key, model)
            usage.append(consumed)
            ai_rank = [CandidateScore(ticker=p.ticker, score=len(output.picks)-i, citations=p.evidence_ids,
                                     pros=[], cons=[]) for i,p in enumerate(output.picks)]
            names = {p.ticker for p in output.picks}
            proposed = select([s for s in securities if s.ticker in names], ai_rank, mandate)
            # Run mechanical sizing before accepting specialist selection.
            conviction = {p.ticker:p.conviction for p in output.picks}
            allocate(proposed, mandate, conviction)
            chosen = proposed
            source = "One structured AI call covering four responsibilities, followed by deterministic risk review and finalization"
            ai_rejected = {p.ticker:"AI opinion: "+p.reason.replace("_", " ") for p in output.rejected}
            ai_concerns = ["AI review hypothesis: "+v.replace("_", " ") for v in output.concerns]
        except Exception:
            # No raw errors/prompts/credentials retained. Successful evidence/local basket survives.
            warnings.append("AI review failed validation, was refused or interrupted; deterministic local portfolio preserved. No automatic retry.")
            if not usage:
                usage.append({"status":"failed", "stage":"specialist_review", "attempts":1, "model":model,
                              "input_tokens":None, "output_tokens":None, "estimated_cost_usd":None})
            conviction = {}
    weights, cash, sectors, used, binding, note = allocate(chosen, mandate, conviction)
    dollar = dollar_allocations(weights, cash, mandate.amount)
    risk = diagnostics(chosen, weights, snapshot.benchmark)
    warnings += [note, "Risk tolerance affects descriptive preferences; no suitability assessment or forecast loss/volatility target is enforced."]
    overlap = ["Possible category duplication (unmeasured constituent overlap): "+", ".join(sorted(set(weights)&g))
               for g in OVERLAP_GROUPS if len(set(weights)&g) > 1]
    warnings += overlap
    if any(s.asset == "etf" for s in chosen) and any(s.asset == "stock" for s in chosen):
        warnings.append("ETF/single-stock constituent overlap is unmeasured; underlying sector limits cannot be certified.")
    score_map = {s.ticker:s for s in ranked}
    holdings = []
    for s in chosen:
        sc = score_map[s.ticker]
        holdings.append(HoldingRecommendation(ticker=s.ticker, name=s.name, sector=s.sector, asset=s.asset,
            weight=weights[s.ticker], dollars=dollar[s.ticker], conviction=conviction.get(s.ticker, "not AI rated"),
            pros=sc.pros, cons=sc.cons, citations=sc.citations,
            sizing=f"{used}: relative sizing signal, constrained by {mandate.position_cap:.0%} position and {mandate.sector_cap:.0%} sector/category caps; cash reserved first. "
                   "Conviction, when used, has a bounded subjective influence and is not expected alpha.",
            thesis_breakers=["Reassess after a deterioration in dated profitability evidence or an unresolved data gap.",
                            "Reassess if concentration, volatility or mandate requirements change. No numerical price target is established."]))
    changes = []
    for s in sorted(set(initial)|set(weights)):
        if abs(initial.get(s,0)-weights.get(s,0)) > 1e-7:
            changes.append(f"{s}: {initial.get(s,0):.2%} initial equal-weight proposal → {weights.get(s,0):.2%} final, after selection, historical sizing and constraints.")
    rejections = {s:"Excluded by mandate/eligibility: "+reason for s,reason in excluded.items()}
    rejections.update(ai_rejected)
    for sc in ranked:
        if sc.ticker not in weights and len([k for k in rejections if k not in excluded]) < 5:
            rejections.setdefault(sc.ticker, "Not selected: lower descriptive priority after sector-cap capacity and mandate preferences; not evidence of inferiority.")
    # Ensure no accepted holding is described as rejected.
    rejections = {k:v for k,v in rejections.items() if k not in weights}
    vulnerabilities = ["Historical correlations can rise in stress; this window cannot establish future diversification.",
                       "Valuation, growth, catalysts and current news are incomplete; no return forecast is supported.",
                       "Current curated universe introduces selection and survivorship limitations; this is not a point-in-time backtest."]
    if risk.status == "unavailable":
        vulnerabilities.append("Historical portfolio risk metrics are unavailable; equal-weight fallback does not establish low risk.")
    vulnerabilities += overlap + ai_concerns
    committee = CommitteeReview(source=source, initial_weights=initial, changes=changes or ["No weight change from the initial equal-weight proposal."],
        vulnerabilities=vulnerabilities, disagreements=["Theme/conviction preferences can conflict with diversification; mechanical caps take precedence.",
        "No independent adversarial-agent consensus or forward-performance validation is claimed."], rejected=rejections,
        roles={"Research analyst":"Ranks positive dated margin availability and curated theme matches; no sector-relative fair value claim.",
               "Portfolio strategist":"Selects mandate-compatible securities while preserving feasible sector capacity.",
               "Risk reviewer":"Checks historical alignment, covariance, category duplication and hard allocation caps.",
               "Investment committee":"Records proposal-to-final changes, unresolved tradeoffs and rejected alternatives; never executes trades."})
    identity = sha256(json.dumps({"snapshot":snapshot.id,"mandate":mandate.model_dump(),"weights":weights,"conviction":conviction},sort_keys=True).encode()).hexdigest()[:24]
    return PortfolioRecommendation(id=identity, snapshot=snapshot, mandate=mandate, holdings=holdings, cash=cash, cash_dollars=dollar["CASH"],
        sectors=sectors, risk=risk, committee=committee, warnings=warnings, binding_constraints=binding, method_used=used,
        model=model if use_ai else None, usage=usage)
