"""Always-available, disclosed screening rules; no model or provider dependency."""
from datetime import datetime,timezone
from langgraphagenticai.providers.discovery_numbers import finite_number
from .contracts import PERSONAS,clean,fingerprint

RULES_VERSION=1


def _percentile(value,values,lower=False):
    values=[v for v in values if v is not None]
    if value is None:return None
    if len(values)<2:return .5
    less=sum(v<value for v in values);equal=sum(v==value for v in values)
    rank=(less+(equal-1)/2)/(len(values)-1)
    return 1-rank if lower else rank


def rank_companies(evidence):
    rows=evidence["rows"];result={}
    for symbol,row in rows.items():
        facts=row.get("fundamentals",{});tech=row.get("technicals",{})
        sector=row.get("sector","Unknown")
        peers=[r for r in rows.values() if r.get("sector","Unknown")==sector]
        metric="pb_ttm" if "financial" in sector.lower() else "pe_ttm"
        raw=finite_number(facts.get(metric));multiple=raw if raw is not None and raw>0 else None
        value=_percentile(multiple,[v if (v:=finite_number(p.get("fundamentals",{}).get(metric))) is not None and v>0 else None for p in peers],True)
        margin=finite_number(facts.get("net_margin_ttm"))
        quality=_percentile(margin,[finite_number(p.get("fundamentals",{}).get("net_margin_ttm")) for p in peers])
        debt=finite_number(facts.get("debt_equity_ttm"))
        resilience=None if "financial" in sector.lower() or debt is None or debt<0 else 1/(1+debt)
        distance=finite_number(tech.get("distance_sma200_pct"));short=finite_number(tech.get("distance_sma50_pct"))
        trend=None if distance is None else min(1,max(0,.5+distance/100))
        pullback=None if short is None else min(1,max(0,.5-short/100))
        proxy=1. if any(s in sector.lower() for s in ("technology","communication","health")) else .0 if sector!="Unknown" else None
        features=dict(value=value,quality=quality,resilience=resilience,trend=trend,pullback=pullback,innovation_sector_proxy=proxy)
        # A sector label alone never qualifies a company as an investment candidate.
        if all(features[k] is None for k in ("value","quality","resilience","trend","pullback")):continue
        weights={"Warren":dict(quality=.5,value=.4,trend=.1),"George":dict(value=.45,pullback=.35,quality=.2),
                 "Ray":dict(quality=.6,resilience=.3,value=.1),"Cathie":dict(trend=.45,quality=.35,innovation_sector_proxy=.2)}
        scores={p:sum(features[k]*w for k,w in terms.items() if features[k] is not None)/sum(w for k,w in terms.items() if features[k] is not None)
                if any(features[k] is not None for k in terms) else None for p,terms in weights.items()}
        result[symbol]=dict(features=features,scores=scores,sector=sector)
    return result


def pick_card(symbol,evidence):
    row=evidence["rows"][symbol];f=row.get("fundamentals",{});t=row.get("technicals",{})
    observations=[]
    if (v:=finite_number(f.get("pe_ttm"))) is not None:observations.append(f"Provider TTM P/E {v:.1f}x")
    if (v:=finite_number(f.get("net_margin_ttm"))) is not None:observations.append(f"TTM net margin {100*v:.1f}%")
    if (v:=finite_number(t.get("distance_sma200_pct"))) is not None:observations.append(f"Price {v:+.1f}% from the provider 200-bar average")
    return dict(symbol=symbol,thesis="; ".join(observations) or "Selected by the disclosed available-data screen.",
                risk="Concentration and valuation risk; missing inputs and sector differences can change the ranking.",
                monitor="Reassess after new earnings, material business news or a change in technical positioning.",
                evidence_refs=list(row.get("evidence_refs",{}))[:4])


def apply_selection(view,symbols,evidence,basis):
    view["picks"]=[dict(pick_card(s,evidence),weight_pct=100/len(symbols)) for s in symbols]
    view["selection_basis"]=basis


def build_ranked(prompt,names,evidence,model=""):
    scores=rank_companies(evidence);views={}
    for persona,(style,_) in PERSONAS.items():
        ordered=sorted((s for s,v in scores.items() if v["scores"][persona] is not None),key=lambda s:(-scores[s]["scores"][persona],s))
        if persona=="Ray":
            chosen=[];sectors=set()
            for symbol in ordered:
                sector=scores[symbol]["sector"]
                if sector!="Unknown" and sector not in sectors:chosen.append(symbol);sectors.add(sector)
                if len(chosen)==4:break
            ordered=chosen+[s for s in ordered if s not in chosen]
        selected=ordered[:4] if len(ordered)>=3 else []
        view=dict(persona=persona,summary=style+": data-ranked shortlist. Your free-text request has not been applied as a hard constraint.")
        apply_selection(view,selected,evidence,"Data-ranked screen")
        views[persona]=view
    return dict(schema_version=2,prompt=clean(prompt,limit=1500),universe=names,evidence=evidence,perspectives=views,warnings=[],
                generated_at=datetime.now(timezone.utc).isoformat(),model=model,model_calls=0,prompt_tokens=None,completion_tokens=None,
                fingerprint=fingerprint(prompt,names,evidence,model),ranking=scores,rules_version=RULES_VERSION,
                ai_status="not_requested",basis="Disclosed heuristic shortlist; AI refinement optional; no trades or return forecast")
