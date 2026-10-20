"""Reuse allowlisted raw inputs, never scores, narrative summaries or financial guesses."""
from copy import deepcopy
from langgraphagenticai.providers.company_evidence import saved_company_evidence,credential_scope
from langgraphagenticai.providers.valuation import reusable_component,normalize_rows


def company_inputs(state,names,api_key):
    scope=credential_scope(api_key);result={}
    for symbol in names:
        current=saved_company_evidence(state,symbol,api_key) or dict(symbol=symbol,credential_scope=scope,sources={})
        valuation=state.get("valuation_evidence",{}).get(scope+":"+symbol,{})
        for kind in ("quote","profile","ratios"):
            if reusable_component(current,kind,symbol):continue
            if reusable_component(valuation,kind,symbol):
                current[kind]=deepcopy(valuation[kind]);current["sources"][kind]=deepcopy(valuation["sources"][kind])
        if any(reusable_component(current,kind,symbol) for kind in ("quote","profile","ratios")):result[symbol]=current
    return result
