"""Explain the actual valuation packet using familiar company-report metric labels."""
from langgraphagenticai.analysis.company_terminal import KEY_STATISTICS, GROWTH_STATISTICS
from langgraphagenticai.valuation.model import number
from langgraphagenticai.valuation.citations import source_roles

LABELS={key:label for label,key in KEY_STATISTICS+GROWTH_STATISTICS}
LABELS.update(annual_per_share_growth="Annual EPS / BVPS growth",annual_gross_margin="Gross margin (annual)",annual_operating_margin="Operating margin (annual)",annual_net_margin="Net margin (annual)",annual_fcf_margin="FCF margin (annual)")
LABELS.update(annual_common_bvps="Common BVPS (annual, calculated)", provider_bvps="Provider BVPS (context only)")
VALUATION={"pe_ttm","pe_forward","peg","price_to_sales","price_to_book","enterprise_value","ev_ebitda","market_cap","dividend_yield"}


def display_value(value,unit="",currency=""):
    value=number(value)
    if value is None:return "Unavailable"
    if unit=="fraction":return f"{value*100:,.1f}%"
    if unit=="percentage_points":return f"{value:+,.1f}%"
    if unit=="currency":
        suffix,scale=("T",1e12) if abs(value)>=1e12 else ("B",1e9) if abs(value)>=1e9 else ("M",1e6) if abs(value)>=1e6 else ("",1)
        return f"{value/scale:,.2f}{suffix} {currency}".strip()
    return f"{value:,.2f}"+("x" if unit=="ratio" else "")


def coverage_rows(packet):
    roles=source_roles(packet)
    result=[]
    def add(category,label,value,basis,asof=None,unit="",currency="",source=""):
        result.append({"Category":category,"Metric":label,"Value":display_value(value,unit,currency),"Basis":basis,"Period / observation date":asof or "Not supplied","Source ID":source,"Used by AI":source in roles})
    quote_currency=packet.get("quote_currency",packet.get("currency",""))
    add("Valuation","Current price",packet.get("price"),"Point-in-time quote",packet.get("quote_as_of"),"currency",quote_currency,"quote:0")
    kind="balance" if packet["method"]=="P/B" else "income"
    basis_id=next((r["id"] for r in packet["evidence"] if r.get("kind")==kind and r.get("fields",{}).get("date")==packet.get("annual_as_of")),"")
    add("Fundamentals","Annual common BVPS" if packet["method"]=="P/B" else "Annual diluted EPS",packet.get("annual_basis_per_share"),"Annual FY; not TTM",packet.get("annual_as_of"),"currency",packet.get("currency",""),basis_id)
    for record in packet["evidence"]:
        fields=record.get("fields",{})
        if record.get("kind")=="calculated_metric":
            key=record["id"].removeprefix("metric:")
            add("Valuation" if key in VALUATION else "Fundamentals",LABELS.get(key,key.replace("_"," ").title()),fields.get("value"),fields.get("basis","Unavailable"),fields.get("as_of"),fields.get("unit",""),fields.get("currency",""),record["id"])
        if record.get("kind")=="technicals":
            for key,label,unit in (("return_1m_pct","1M price return","percentage_points"),("return_3m_pct","3M price return","percentage_points"),("return_1y_pct","1Y price return","percentage_points"),("rsi_14","RSI 14","score"),("sma_50","SMA 50","currency"),("sma_200","SMA 200","currency"),("annualized_volatility_pct","Annualized volatility","percentage_points")):
                if number(fields.get(key)) is not None:
                    add("Technicals",label,fields[key],f"Daily history; {fields.get('price_basis','basis unavailable')}",fields.get("as_of"),unit,quote_currency,record["id"])
    for row in packet.get("supported_forward_estimates",[]):
        source=next((r["id"] for r in packet["evidence"] if r.get("kind")=="estimates" and r.get("fields",{}).get("date")==row["date"]),"")
        add("Analyst expectations",f"Consensus EPS ({int(row['analysts'])} analysts)",row["eps"],row["basis"]+"; "+row.get("currency_basis",""),row["date"],"currency",row.get("currency",""),source)
    for row in packet.get("analyst_targets",[]):
        add("Analyst expectations",f"Target average: last {row['window'].lower()}",row["target"],"Publication window; forecast horizon not supplied",None,"currency",quote_currency,"targets:0")
    return result
