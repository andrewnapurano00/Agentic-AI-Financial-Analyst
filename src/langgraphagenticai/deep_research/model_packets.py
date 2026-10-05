"""Small, sector-projected decision inputs bounded as complete serialized packets."""
from .models import dumps, json_safe, Evidence
from .research_metrics import project_sector_row
from .sector import SECTOR_METRIC_REGISTRY, GENERAL_FRAMEWORK


def compact_comparison(rows,max_chars=7000):
    result=[]
    for raw in rows:
        row=project_sector_row(raw)
        registry=SECTOR_METRIC_REGISTRY.get(row.get("Sector framework"),SECTOR_METRIC_REGISTRY[GENERAL_FRAMEWORK])
        core=["Ticker","Sector framework","Quote currency","TTM through","TTM currency","Cash flow TTM through","Cash flow TTM currency",
              "Balance sheet date","Balance currency","Quote as of","Price","Revenue (TTM)","Net income (TTM)","Operating cash flow (TTM)",
              "Forward P/E","Estimate period","Forward revenue","Forward revenue growth (%)","Analyst target","Target upside (%)"]
        keys=list(dict.fromkeys(core+registry["must_have"]+registry["preferred"]))
        item={key:row[key] for key in keys if row.get(key) is not None}
        item["metric_basis"]={key:row["Metric contracts"][key]["unit"] for key in item if key in row.get("Metric contracts",{}) and row["Metric contracts"][key]["unit"] not in {"metadata","text","date"}}
        item["missing_priority_metrics"]=[key for key in registry["must_have"] if row.get(key) is None][:5]
        allowance=max_chars//max(len(rows),1)-20
        while len(dumps(item))>allowance:
            optional=[key for key in reversed(keys) if key in item and key not in core[:15]]
            if not optional:break
            key=optional[0];item.pop(key);item["metric_basis"].pop(key,None)
        result.append(item)
    return json_safe(result)


def bounded_decision_packet(result,max_chars=10000):
    from .prompt_context import evidence_context
    request=dict(result.get("request",{}));request["question"]=str(request.get("question", ""))[:500]
    from .quarterly_ttm import METHODOLOGY
    policy=("TTM standalone flows, latest snapshot leverage, matched beginning/end ROE/ROA; units supplied; forward growth FY+2/FY+1; omitted detail remains in saved audit." if result.get("financial_methodology")==METHODOLOGY else
            "Saved legacy comparison values; fiscal duration and units may be unverified. No recomputation or recollection. Sector exclusions applied.")
    packet={"request":request,"created_at":result.get("created_at"),"financial_methodology":result.get("financial_methodology","legacy_unverified"),
        "comparison":compact_comparison(result.get("comparison",[]),max_chars//2),
        "warnings":[str(w)[:120] for w in result.get("warnings",[])[:4]],
        "gaps":[str(w)[:120] for w in result.get("gaps",[])[:4]],
        "basis_policy":policy}
    evidence=[Evidence(**item) for item in result.get("evidence",[])]
    remaining=max_chars-len(dumps(packet))-20
    packet["evidence"]=evidence_context(evidence,max(remaining,0),focus="valuation growth risk catalysts")
    # Trim optional explanatory material, never drop a company to hide an overrun.
    while len(dumps(packet))>max_chars:
        if packet["warnings"]:packet["warnings"].pop()
        elif packet["gaps"]:packet["gaps"].pop()
        elif packet["request"].get("question"):packet["request"]["question"]=""
        else:raise ValueError("Decision packet budget cannot preserve all company data.")
    return json_safe(packet)
