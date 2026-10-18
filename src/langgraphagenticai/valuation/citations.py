"""Resolve valuation support by metric meaning and provenance, not ID spelling."""
from copy import deepcopy
from langgraphagenticai.valuation.model import number
from langgraphagenticai.valuation.errors import ValuationResponseError

GROWTH_METRICS = {
    "annual_per_share_growth", "revenue_cagr_3y", "revenue_cagr_5y", "revenue_growth",
    "annual_gross_margin", "annual_operating_margin", "annual_net_margin", "annual_fcf_margin",
    "gross_margin", "operating_margin", "net_margin", "fcf_margin", "roe", "roa", "roic",
    "net_income_cagr_3y", "fcf_cagr_3y",
    "annual_common_bvps",
}
VALUATION_METRICS = {"annual_common_bvps", "provider_bvps", "pe_ttm", "pe_forward", "price_to_book", "price_to_sales", "peg", "ev_ebitda", "enterprise_value", "market_cap", "dividend_yield"}


class CitationFailure(ValuationResponseError):
    def __init__(self, field, reason, known_ids=(), unknown_count=0):
        super().__init__("citations")
        # All values are constructed by the validator, never arbitrary model prose.
        self.diagnostics = dict(field=field, reason=reason, recognized_sources=sorted(known_ids), unknown_source_count=unknown_count)


def source_roles(packet):
    rows = {r["id"]: r for r in packet["evidence"]}
    roles = {key:set() for key in rows}
    forecasts = packet.get("supported_forward_estimates", [])
    def resolves(key,seen=None):
        seen=set() if seen is None else seen
        if key in seen or key not in rows:return False
        row=rows[key]
        if row.get("kind")!="calculated_metric":return True
        fields=row.get("fields",{})
        sources=fields.get("source_ids",[])
        return bool(sources) and number(fields.get("value")) is not None and all(resolves(ref,seen|{key}) for ref in sources)
    for key,row in rows.items():
        kind, fields = row.get("kind"), row.get("fields", {})
        if kind == "quote" and number(fields.get("price")) is not None:
            roles[key].update(("price", "valuation"))
        if kind == "income" and fields.get("period") == "FY" and any(number(fields.get(k)) is not None for k in ("epsDiluted", "revenue", "netIncome")):
            roles[key].add("growth")
        if kind == "balance" and packet["method"] == "P/B" and any(number(fields.get(k)) is not None for k in ("commonStockEquity", "totalStockholdersEquity")):
            roles[key].add("growth")
        if kind == "estimates":
            eps=next((number(fields.get(k)) for k in ("epsAvg","estimatedEpsAvg","estimatedEps") if number(fields.get(k)) is not None),None)
            count=next((number(fields.get(k)) for k in ("numAnalystsEps","numberAnalystEstimatedEps","numberAnalystsEstimatedEps") if number(fields.get(k)) is not None),None)
            currency=fields.get("reportedCurrency") or fields.get("currency")
            if any(r["date"]==fields.get("date") and r["eps"]==eps and r["analysts"]==count and (not currency or currency==r["currency"]) for r in forecasts):
                roles[key].update(("growth", "valuation"))
        if kind in ("ratios", "metrics") and any(number(v) is not None for k,v in fields.items() if k not in ("symbol", "date")):
            roles[key].add("valuation")
        if kind == "cashflow" and fields.get("period") == "FY" and number(fields.get("freeCashFlow")) is not None:
            roles[key].add("growth")
        if kind == "targets" and any(number(fields.get(k)) is not None for k in ("lastMonthAvgPriceTarget", "lastQuarterAvgPriceTarget")):
            roles[key].add("valuation")
        if kind == "technicals":
            roles[key].add("momentum")
    for key,row in rows.items():
        if row.get("kind") != "calculated_metric":
            continue
        metric = key.removeprefix("metric:")
        fields = row.get("fields", {})
        # Derived metrics must resolve every declared source and carry a finite value.
        sources = fields.get("source_ids", [])
        if not sources or not resolves(key) or number(fields.get("value")) is None:
            continue
        if metric in GROWTH_METRICS:
            roles[key].add("growth")
        if metric in VALUATION_METRICS:
            roles[key].add("valuation")
    return roles


def check_sources(citations, field, packet, *, required_role=None):
    roles = source_roles(packet)
    unknown = set(citations) - set(roles)
    known = set(citations) & set(roles)
    if unknown:
        raise CitationFailure(field,"unknown_source",known,len(unknown))
    if required_role and not any(required_role in roles[key] for key in known):
        raise CitationFailure(field,f"missing_{required_role}_support",known)


def schema_for_packet(schema, packet):
    """Prevent invented IDs at generation time, retaining local validation as well."""
    schema = deepcopy(schema)
    roles = source_roles(packet)
    all_ids = sorted(roles)
    def restrict(field, choices):
        field["items"] = {"type":"string", "enum":choices or all_ids}
    props = schema["properties"]
    if packet["target_eligibility"]:
        props["growth_evidence_ids"]["minItems"]=1
        props["multiple_evidence_ids"]["minItems"]=1
        props["scenarios"]["minItems"]=3
    restrict(props["evidence_ids"],all_ids)
    restrict(props["growth_evidence_ids"],sorted(key for key,value in roles.items() if "growth" in value))
    restrict(props["multiple_evidence_ids"],sorted(key for key,value in roles.items() if "valuation" in value))
    restrict(schema["$defs"]["ScenarioDriver"]["properties"]["evidence_ids"],sorted(key for key,value in roles.items() if value & {"growth","valuation"}))
    return schema
