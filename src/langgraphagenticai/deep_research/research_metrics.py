"""Audited fresh-research comparisons: explicit units, inputs, applicability and missingness.

D01-D10: standardized quarterly flows are a declared assumption. This module
never substitutes provider TTM, sums shares/EPS or validates model-written claims.
"""
from datetime import date, datetime, timezone
from .quarterly_ttm import number, divide, same_window, aggregate, INCOME_FIELDS, CASH_FIELDS, METHODOLOGY, flow_duration
from .sector import SECTOR_METRIC_REGISTRY, map_sector_to_framework
from .models import json_safe

BASE_KEYS = ['% From SMA 200', '% From SMA 50', '1Y Return', '1Y price return (%)', '3M price return (%)', 'Analyst target', 'Balance sheet date', 'Book Value / Share', 'Capex to Revenue', 'Capex to revenue (TTM)', 'Capex to revenue (latest period)', 'Capital expenditure (TTM)', 'Capital expenditure (latest period)', 'Cash Conversion', 'Cash Conversion Cycle Days', 'Cash conversion (TTM)', 'Cash conversion (latest period)', 'Company', 'Current Ratio', 'Debt / Assets', 'Debt / Capital', 'Debt Service Coverage', 'Debt to Equity', 'Debt/equity (TTM)', 'Dividend Payout Ratio', 'Dividend Yield', 'EBITDA (TTM)', 'EBITDA (latest period)', 'EBITDA margin (TTM)', 'EBITDA margin (latest period)', 'EV / EBITDA', 'EV / FCF', 'EV / Sales', 'EV/EBITDA (TTM)', 'EV/Sales (TTM)', 'Earnings Yield', 'Estimate period', 'FCF CAGR 3Y', 'FCF Margin', 'FCF Yield', 'FCF margin (TTM)', 'FCF margin (latest period)', 'FCF yield (TTM, fraction)', 'Forward EBITDA', 'Forward EBITDA Next FY', 'Forward EPS', 'Forward EPS Next FY', 'Forward Net Income Next FY', 'Forward P/E', 'Forward P/S', 'Forward Revenue Growth FY+1', 'Forward Revenue Next FY', 'Forward net income', 'Forward revenue', 'Forward revenue growth (%)', 'Forward revenue next period', 'Free cash flow (TTM)', 'Free cash flow (latest period)', 'Gross margin (TTM)', 'Gross margin (latest period)', 'Gross profit (TTM)', 'Gross profit (latest period)', 'Income Quality', 'Industry', 'Inventory Days', 'Latest EBITDA Margin', 'Latest Gross Margin', 'Latest Net Margin', 'Latest Operating Margin', 'Liabilities to Assets', 'Market cap', 'Net Debt / EBITDA', 'Net Income CAGR 3Y', 'Net income (TTM)', 'Net income (latest period)', 'Net margin (TTM)', 'Net margin (TTM, fraction)', 'Net margin (latest period)', 'OCF Margin', 'OCF margin (TTM)', 'OCF margin (latest period)', 'Operating cash flow (TTM)', 'Operating cash flow (latest period)', 'Operating income (TTM)', 'Operating income (latest period)', 'Operating margin (TTM)', 'Operating margin (latest period)', 'P/B (TTM)', 'P/B TTM', 'P/E (TTM)', 'P/E TTM', 'P/FCF TTM', 'P/S (TTM)', 'P/S TTM', 'Price', 'Price Target Upside', 'Price date', 'Quote currency', 'R&D as % Revenue', 'R&D as % revenue (TTM)', 'R&D as % revenue (latest period)', 'ROA', 'ROE', 'ROIC', 'RSI (14)', 'RSI 14', 'Revenue (TTM)', 'Revenue (latest period)', 'Revenue CAGR 3Y', 'SMA 200', 'SMA 50', 'Sector', 'Statement currency', 'Statement date', 'Statement period', 'Stock-Based Comp % Revenue', 'Stock-based comp % revenue (TTM)', 'Stock-based comp % revenue (latest period)', 'TTM currency', 'TTM through', 'Tangible Book Value / Share', 'Target upside (%)', 'Ticker']


def valid_snapshots(rows, symbol):
    valid = {}
    ambiguous = set()
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or row.get("symbol") != symbol or not row.get("reportedCurrency"):
            continue
        try:
            day = date.fromisoformat(row["date"])
            year = int(row.get("fiscalYear"))
            if day > date.today() or not 1900 <= year <= 2200 or abs(day.year-year) > 1 or row.get("period") not in {"Q1","Q2","Q3","Q4"}:
                continue
        except (ValueError, TypeError, KeyError):
            continue
        key = (year, row["period"])
        if key in valid and valid[key] != row:
            ambiguous.add(key)
        valid[key] = row
    return sorted([r for k,r in valid.items() if k not in ambiguous], key=lambda r:r["date"], reverse=True)


def match_balance(rows, income, prior=False):
    quarter = next(iter(income.get("quarters", [])), {})
    year = quarter.get("fiscalYear") or quarter.get("calendarYear")
    if not year:
        return {}
    selected = [r for r in rows if r.get("reportedCurrency") == income.get("reportedCurrency")
                and r.get("period") == quarter.get("period")
                and str(r.get("fiscalYear") or r.get("calendarYear")) == str(int(year)-int(prior))
                and (prior or r.get("date") == income.get("date"))]
    if len(selected) != 1:
        return {}
    if prior:
        try:
            if not 330 <= (date.fromisoformat(income["date"])-date.fromisoformat(selected[0]["date"])).days <= 400:
                return {}
        except (ValueError, KeyError):
            return {}
    return selected[0]


def future_estimates(rows, symbol, today=None):
    today = today or date.today()
    selected = []
    for row in rows:
        if row.get("symbol") != symbol or str(row.get("period") or "FY").upper() not in {"FY", "ANNUAL"}:
            continue
        try:
            end = date.fromisoformat(str(row.get("date")))
        except ValueError:
            continue
        if end > today:
            selected.append(row)
    # Ambiguous same-date consensus records are excluded, never silently selected.
    return sorted([r for r in selected if sum(other["date"] == r["date"] for other in selected)==1], key=lambda r:r["date"])


def annual_cagr(rows, symbol, field):
    valid = {}
    for row in rows:
        if row.get("symbol") != symbol or row.get("period") not in {"FY","ANNUAL"} or not flow_duration(row)[0]:
            continue
        try:
            year = int(row.get("fiscalYear"))
            day=date.fromisoformat(row["date"])
            if day > date.today() or abs(day.year-year)>1: continue
        except (ValueError, TypeError, KeyError):
            continue
        valid.setdefault(year, []).append(row)
    if not valid:
        return None, []
    latest = max(valid)
    if len(valid[latest]) != 1 or len(valid.get(latest-3, [])) != 1:
        return None, []
    a,b = valid[latest][0], valid[latest-3][0]
    if not 1030 <= (date.fromisoformat(a["date"])-date.fromisoformat(b["date"])).days <= 1160:
        return None, [a,b]
    top,bottom = number(a.get(field)), number(b.get(field))
    if not a.get("reportedCurrency") or a.get("reportedCurrency") != b.get("reportedCurrency") or top is None or bottom is None or top<=0 or bottom<=0:
        return None, [a,b]
    return ((top/bottom)**(1/3)-1)*100, [a,b]


def reconciliation(sources, symbol):
    result=[]
    for family,fields in (("income",INCOME_FIELDS),("cash_flow",CASH_FIELDS)):
        annual=sources.get(family+"_annual") or sources.get(family)
        quarterly=sources.get(family+"_quarterly")
        if not annual or not quarterly or not isinstance(annual.data,list):
            continue
        for row in annual.data:
            if row.get("period") not in {"FY","ANNUAL"}: continue
            year=row.get("fiscalYear") or row.get("calendarYear")
            matching=[r for r in quarterly.data if str(r.get("fiscalYear") or r.get("calendarYear"))==str(year)]
            try: total=aggregate(matching,symbol,fields)
            except ValueError: continue
            if total.get("reportedCurrency") != row.get("reportedCurrency"): continue
            for field in fields:
                a,b=number(row.get(field)),number(total.get(field))
                if a is not None and b is not None:
                    result.append(dict(family=family,metric=field,fiscal_year=year,annual=a,quarter_sum=b,
                        difference=b-a,currency=row.get("reportedCurrency"),cause="Unknown; diagnostic only",
                        sources=[annual.id,quarterly.id]))
    return result


ALIASES = {
"P/E TTM":"P/E (TTM)","P/S TTM":"P/S (TTM)","P/B TTM":"P/B (TTM)",
"P/FCF TTM":"P/FCF (TTM)","Debt to Equity":"Debt/equity (latest snapshot)","Debt/equity (TTM)":"Debt/equity (latest snapshot)",
"EV / EBITDA":"EV/EBITDA (TTM)","EV / Sales":"EV/Sales (TTM)","EV / FCF":"EV/FCF (TTM)",
"FCF Yield":"FCF yield (TTM, fraction)","Earnings Yield":"Earnings yield (TTM)",
"Latest Gross Margin":"Gross margin (latest period)","Latest Operating Margin":"Operating margin (latest period)",
"Latest EBITDA Margin":"EBITDA margin (latest period)","Latest Net Margin":"Net margin (latest period)",
"OCF Margin":"OCF margin (TTM)","FCF Margin":"FCF margin (TTM)","Cash Conversion":"Cash conversion (TTM)","Income Quality":"Cash conversion (TTM)",
"R&D as % Revenue":"R&D as % revenue (TTM)","Stock-Based Comp % Revenue":"Stock-based comp % revenue (TTM)",
"Capex to Revenue":"Capex to revenue (TTM)","Net margin (TTM, fraction)":"Net margin (TTM)",
"Forward Revenue Next FY":"Forward revenue", "Forward EPS Next FY":"Forward EPS",
"Forward EBITDA Next FY":"Forward EBITDA","Forward Net Income Next FY":"Forward net income",
"Forward Revenue Growth FY+1":"Forward revenue growth (%)", "Price Target Upside":"Target upside (%)",
"1Y Return":"1Y return (%)","1Y price return (%)":"1Y return (%)","3M price return (%)":"3M return (%)","RSI 14":"RSI (14)"
}


def audited_comparison_rows(evidence, symbols):
    output=[]
    for symbol in symbols:
        sources={e.category:e for e in evidence if e.symbol==symbol and e.status=="ok"}
        def rows(category):
            e=sources.get(category)
            return [r for r in e.data if isinstance(r,dict)] if e and isinstance(e.data,list) else []
        def first(category):
            r=rows(category)
            return r[0] if r else (sources[category].data if category in sources and isinstance(sources[category].data,dict) else {})
        profile,quote,inc,cf,latest_inc,latest_cf=(first(c) for c in ("profile","quote","income_ttm","cash_flow_ttm","income","cash_flow"))
        snapshots=valid_snapshots(rows("balance_quarterly"),symbol)
        latest=first("balance_latest") or (snapshots[0] if snapshots else {})
        end=match_balance(snapshots,inc); begin=match_balance(snapshots,inc,True)
        tech=first("technicals")
        framework=map_sector_to_framework(profile.get("sector"),profile.get("industry"))
        row={key:None for key in BASE_KEYS}; contracts={}
        def input_record(category,field,observation=None):
            source=sources.get(category)
            record=observation if observation is not None else (future_estimates(rows(category),symbol) or [{}])[0] if category=="estimates" else first(category)
            aliases={"revenueAvg":("revenueAvg","estimatedRevenueAvg"),"epsAvg":("epsAvg","estimatedEpsAvg"),
                     "ebitdaAvg":("ebitdaAvg","estimatedEbitdaAvg"),"netIncomeAvg":("netIncomeAvg","estimatedNetIncomeAvg"),
                     "targetConsensus":("targetConsensus","targetMedian")}
            actual_field=next((candidate for candidate in aliases.get(field,(field,)) if number(record.get(candidate)) is not None),field)
            inferred_currency=not (record.get("reportedCurrency") or record.get("currency")) and category in {"quote","estimates","price_targets"}
            return dict(category=category,field=actual_field,requested_field=field,value=record.get(actual_field),
                currency_basis="Matching profile inference; not independently verified" if inferred_currency else "Source-reported currency",
                currency_source_id=sources["profile"].id if inferred_currency and "profile" in sources else None,
                date=quote_time(record.get("timestamp")) if category=="quote" else record.get("date") or record.get("as_of"),
                currency=record.get("reportedCurrency") or record.get("currency") or (profile.get("currency") if inferred_currency else None),source_id=source.id if source else None,
                provider=source.provider if source else None,url=source.url if source else None,retrieved_at=source.retrieved_at if source else None)
        def setv(key,value,unit="ratio",formula="",inputs=(),reason="Missing, invalid, nonpositive or misaligned inputs",currency=None,basis=None):
            value=number(value) if unit not in {"text","date","metadata"} else value
            row[key]=value
            records=[input_record(category,field) for category,field in inputs]
            contracts[key]=dict(value=value,unit=unit,currency=currency,formula=formula or "Provider field; no arithmetic",
                basis=basis,inputs=records,status="ok" if value is not None else "missing",reason="" if value is not None else reason,
                methodology=METHODOLOGY,applicability="applicable")
        for key,value in {"Ticker":symbol,"Company":profile.get("companyName"),"Sector":profile.get("sector"),"Industry":profile.get("industry"),
            "Sector framework":framework,"Quote currency":quote.get("currency") or profile.get("currency"),"Quote currency assumption":"Profile currency inferred when quote currency absent; identity checked",
            "Statement currency":latest_inc.get("reportedCurrency"),"Statement date":latest_inc.get("date"),"Statement period":latest_inc.get("period"),
            "Cash flow statement date":latest_cf.get("date"),"Cash flow statement currency":latest_cf.get("reportedCurrency"),
            "TTM through":inc.get("date"),"TTM currency":inc.get("reportedCurrency"),"Cash flow TTM through":cf.get("date"),
            "Cash flow TTM currency":cf.get("reportedCurrency"),"Balance sheet date":latest.get("date"),"Balance currency":latest.get("reportedCurrency"),
            "TTM methodology":METHODOLOGY,"TTM fiscal quarters":inc.get("quarters"),"Price date":tech.get("as_of"),"Quote as of":quote_time(quote.get("timestamp")),
            "Price basis":tech.get("price_basis"),"Return convention":tech.get("return_note")}.items(): setv(key,value,"metadata")
        qc=row["Quote currency"]
        quote_ok=quote.get("symbol")==symbol
        setv("Price",quote.get("price") if quote_ok else None,"currency","Quote price",[("quote","price")],currency=qc)
        setv("Market cap",quote.get("marketCap") if quote_ok else None,"currency","Quote market cap",[("quote","marketCap")],currency=qc)
        price,cap=row["Price"],row["Market cap"]
        for suffix,income,cash,ic,cc in (("TTM",inc,cf,"income_ttm","cash_flow_ttm"),("latest period",latest_inc,latest_cf,"income","cash_flow")):
            income_duration_ok,income_duration_reason=flow_duration(income) if suffix=="latest period" else (True,"")
            cash_duration_ok,cash_duration_reason=flow_duration(cash) if suffix=="latest period" else (True,"")
            if not income_duration_ok:
                income={**income,**{field:None for field in INCOME_FIELDS}}
            if not cash_duration_ok:
                cash={**cash,**{field:None for field in CASH_FIELDS}}
            aligned=same_window(income,cash) if suffix=="TTM" else bool(income.get("date") and income.get("date")==cash.get("date") and income.get("period")==cash.get("period") and income.get("reportedCurrency")==cash.get("reportedCurrency") and income.get("symbol")==cash.get("symbol")==symbol)
            for field,label,family,category in (("revenue","Revenue",income,ic),("grossProfit","Gross profit",income,ic),("operatingIncome","Operating income",income,ic),
                ("ebitda","EBITDA",income,ic),("netIncome","Net income",income,ic),("netCashProvidedByOperatingActivities","Operating cash flow",cash,cc),
                ("capitalExpenditure","Capital expenditure",cash,cc),("freeCashFlow","Free cash flow",cash,cc)):
                setv(f"{label} ({suffix})",family.get(field),"currency",f"{field}: four standalone fiscal quarter sum" if suffix=="TTM" else f"{field}: selected reported period",[(category,field)],currency=family.get("reportedCurrency"),basis=family.get("quarters") or family.get("date"))
            for field,label in (("grossProfit","Gross margin"),("operatingIncome","Operating margin"),("ebitda","EBITDA margin"),("netIncome","Net margin")):
                setv(f"{label} ({suffix})",divide(income.get(field),income.get("revenue")),"fraction",f"{field} / positive revenue; same fiscal window",[(ic,field),(ic,"revenue")])
            for field,label,bottom in (("netCashProvidedByOperatingActivities","OCF margin","revenue"),("freeCashFlow","FCF margin","revenue"),
                ("netCashProvidedByOperatingActivities","Cash conversion","netIncome"),("stockBasedCompensation","Stock-based comp % revenue","revenue"),("capitalExpenditure","Capex to revenue","revenue")):
                top=number(cash.get(field)); top=abs(top) if field=="capitalExpenditure" and top is not None else top
                value=divide(top,income.get(bottom)) if aligned else None
                points=label in {"Stock-based comp % revenue","Capex to revenue"}
                setv(f"{label} ({suffix})",value*100 if value is not None and points else value,"percentage_points" if points else "fraction",f"{'abs ' if field=='capitalExpenditure' else ''}{field} / positive {bottom}; matching currency/fiscal window",[(cc,field),(ic,bottom)])
            if suffix=="latest period":
                for key,contract in contracts.items():
                    if key.endswith("(latest period)"):
                        cash_metric=key.startswith(("Operating cash flow","Capital expenditure","Free cash flow","Stock-based comp","Capex"))
                        contract["duration"]={"income":{k:latest_inc.get(k) for k in ("period","duration","periodType","reportingBasis","startDate","date")},
                                              "cash_flow":{k:latest_cf.get(k) for k in ("period","duration","periodType","reportingBasis","startDate","date")}}
                        invalid_reason=cash_duration_reason if cash_metric and not cash_duration_ok else income_duration_reason if not income_duration_ok else cash_duration_reason if not cash_duration_ok and key.startswith(("Cash conversion","OCF margin","FCF margin")) else ""
                        if invalid_reason:
                            contract["reason"]=invalid_reason
            research=divide(income.get("researchAndDevelopmentExpenses"),income.get("revenue"))
            setv(f"R&D as % revenue ({suffix})",research*100 if research is not None else None,"percentage_points","R&D / positive same-window revenue * 100",[(ic,"researchAndDevelopmentExpenses"),(ic,"revenue")],reason=income_duration_reason if not income_duration_ok else "Missing or invalid same-period inputs",basis={"date":income.get("date"),"duration":income.get("duration"),"reportingBasis":income.get("reportingBasis")})
        debt,cash,equity,assets,liabilities=(number(latest.get(k)) for k in ("totalDebt","cashAndCashEquivalents","totalStockholdersEquity","totalAssets","totalLiabilities"))
        for key,top,bottom,fields in (("Debt/equity (latest snapshot)",debt,equity,("totalDebt","totalStockholdersEquity")),
            ("Debt / Assets",debt,assets,("totalDebt","totalAssets")),("Liabilities to Assets",liabilities,assets,("totalLiabilities","totalAssets")),
            ("Debt / Capital",debt,debt+equity if debt is not None and equity is not None else None,("totalDebt","totalStockholdersEquity")),
            ("Current Ratio",latest.get("totalCurrentAssets"),latest.get("totalCurrentLiabilities"),("totalCurrentAssets","totalCurrentLiabilities"))):
            setv(key,divide(top,bottom),"ratio",f"Latest valid snapshot {fields[0]} / positive {fields[1]}" if key!="Debt / Capital" else "Latest debt / positive (debt + equity)",[("balance_latest",f) for f in fields])
        for field,key in (("totalStockholdersEquity","ROE"),("totalAssets","ROA")):
            a,b=number(begin.get(field)),number(end.get(field))
            value=divide(inc.get("netIncome"),(a+b)/2) if a is not None and b is not None and a>0 and b>0 else None
            setv(key,value,"fraction",f"TTM net income / average positive beginning and ending {field}",[],basis={"beginning":begin,"ending":end})
            contracts[key]["inputs"]=[input_record("income_ttm","netIncome"),
                {**input_record("balance_quarterly",field,begin),"endpoint":"beginning"},
                {**input_record("balance_quarterly",field,end),"endpoint":"ending"}]
        aligned_cap=quote_ok and cap is not None and cap>0 and qc and qc==inc.get("reportedCurrency")
        for field,key in (("netIncome","P/E (TTM)"),("revenue","P/S (TTM)")):
            setv(key,divide(cap,inc.get(field)) if aligned_cap else None,"multiple",f"Positive quote cap / positive TTM {field}; same security/currency",[("quote","marketCap"),("income_ttm",field)])
        cf_cap=quote_ok and cap is not None and cap>0 and qc and qc==cf.get("reportedCurrency")
        setv("P/FCF (TTM)",divide(cap,cf.get("freeCashFlow")) if cf_cap else None,"multiple","Positive cap / positive TTM FCF; same currency",[("quote","marketCap"),("cash_flow_ttm","freeCashFlow")])
        for key,field,family,category,allowed in (("Earnings yield (TTM)","netIncome",inc,"income_ttm",aligned_cap),("FCF yield (TTM, fraction)","freeCashFlow",cf,"cash_flow_ttm",cf_cap)):
            top=number(family.get(field))
            setv(key,divide(top,cap) if allowed and top is not None else None,"fraction",f"Signed TTM {field} / positive cap; losses/negative cash generation retained",[(category,field),("quote","marketCap")])
        bs_cap=quote_ok and cap is not None and cap>0 and qc and qc==latest.get("reportedCurrency")
        setv("P/B (TTM)",divide(cap,equity) if bs_cap else None,"multiple","Positive current quote cap / positive latest quarterly equity (point-in-time, not a TTM flow)",[("quote","marketCap"),("balance_latest","totalStockholdersEquity")])
        ev=cap+debt-cash if bs_cap and debt is not None and cash is not None else None
        for key,family,field,category in (("EV/EBITDA (TTM)",inc,"ebitda","income_ttm"),("EV/Sales (TTM)",inc,"revenue","income_ttm"),("EV/FCF (TTM)",cf,"freeCashFlow","cash_flow_ttm")):
            allowed=ev is not None and ev>0 and family.get("reportedCurrency")==qc
            setv(key,divide(ev,family.get(field)) if allowed else None,"multiple",f"Simplified EV (quote cap + latest debt - latest cash equivalents) / positive TTM {field}; excludes preferred/minority interests; quote and snapshot dates differ",[("quote","marketCap"),("balance_latest","totalDebt"),("balance_latest","cashAndCashEquivalents"),(category,field)])
        matched_debt,matched_cash=number(end.get("totalDebt")),number(end.get("cashAndCashEquivalents"))
        setv("Net Debt / EBITDA",divide(matched_debt-matched_cash,inc.get("ebitda")) if matched_debt is not None and matched_cash is not None else None,"multiple","Matched TTM-end (total debt - cash equivalents) / positive TTM EBITDA",[("balance_ttm","totalDebt"),("balance_ttm","cashAndCashEquivalents"),("income_ttm","ebitda")])
        for category,field,key in (("income","revenue","Revenue CAGR 3Y"),("income","netIncome","Net Income CAGR 3Y"),("cash_flow","freeCashFlow","FCF CAGR 3Y")):
            annual_category=category+"_annual" if rows(category+"_annual") else category
            value,basis=annual_cagr(rows(annual_category),symbol,field)
            setv(key,value,"percentage_points",f"(Latest positive annual {field} / same-currency annual {field} exactly 3 fiscal years earlier)^(1/3) - 1; * 100",[],basis=basis)
            source=sources.get(annual_category)
            contracts[key]["inputs"]=[dict(category=annual_category,field=field,value=observation.get(field),date=observation.get("date"),
                fiscal_year=observation.get("fiscalYear"),currency=observation.get("reportedCurrency"),
                source_id=source.id if source else None,provider=source.provider if source else None,
                url=source.url if source else None,retrieved_at=source.retrieved_at if source else None,
                endpoint="ending" if i==0 else "beginning") for i,observation in enumerate(basis)]
        for category,family in (("income_ttm",inc),("cash_flow_ttm",cf)):
            for field,value in family.get("growth_pct",{}).items():
                setv(f"{field} TTM growth (%)",value,"percentage_points","Current four-quarter sum / positive prior nonoverlapping four-quarter sum - 1; * 100",[(category,field)],basis=family.get("prior_ttm"))
        estimates=future_estimates(rows("estimates"),symbol)
        estimate=estimates[0] if estimates else {}; next_estimate=estimates[1] if len(estimates)>1 else {}
        def pick(r,*keys): return next((number(r.get(k)) for k in keys if number(r.get(k)) is not None),None)
        revenue=pick(estimate,"revenueAvg","estimatedRevenueAvg");eps=pick(estimate,"epsAvg","estimatedEpsAvg")
        next_revenue=pick(next_estimate,"revenueAvg","estimatedRevenueAvg")
        estimate_currency=estimate.get("reportedCurrency") or estimate.get("currency") or profile.get("currency")
        next_currency=next_estimate.get("reportedCurrency") or next_estimate.get("currency") or profile.get("currency")
        setv("Estimate period",estimate.get("date"),"date")
        setv("Estimate next period",next_estimate.get("date"),"date")
        setv("Estimate currency assumption","Profile currency inferred when estimate currency absent; not independently verified","text")
        for key,value,field in (("Forward revenue",revenue,"revenueAvg"),("Forward revenue next period",next_revenue,"revenueAvg"),("Forward EPS",eps,"epsAvg"),
            ("Forward EBITDA",pick(estimate,"ebitdaAvg","estimatedEbitdaAvg"),"ebitdaAvg"),("Forward net income",pick(estimate,"netIncomeAvg","estimatedNetIncomeAvg"),"netIncomeAvg")):
            selected_estimate=next_estimate if key=="Forward revenue next period" else estimate
            selected_currency=next_currency if key=="Forward revenue next period" else estimate_currency
            setv(key,value,"currency_per_share" if key=="Forward EPS" else "currency",f"Nearest genuinely future annual consensus {field}; no historical fallback",[("estimates",field)],currency=selected_currency,basis=selected_estimate.get("date"))
            if key=="Forward revenue next period":
                contracts[key]["inputs"]=[input_record("estimates",field,next_estimate)]
        consecutive=False
        try: consecutive=330 <= (date.fromisoformat(next_estimate["date"])-date.fromisoformat(estimate["date"])).days <= 400
        except (KeyError,ValueError): pass
        ratio=divide(next_revenue,revenue) if consecutive and estimate_currency and estimate_currency==next_currency else None
        setv("Forward revenue growth (%)",(ratio-1)*100 if ratio is not None else None,"percentage_points","FY+2 revenue / positive FY+1 revenue - 1; *100; consecutive annual dates/currency",[("estimates","revenueAvg")],basis=[estimate,next_estimate])
        contracts["Forward revenue growth (%)"]["inputs"]=[
            {**input_record("estimates","revenueAvg",estimate),"endpoint":"FY+1 denominator"},
            {**input_record("estimates","revenueAvg",next_estimate),"endpoint":"FY+2 numerator"}]
        allow_est=quote_ok and qc and qc==estimate_currency
        setv("Forward P/E",divide(price,eps) if allow_est and price is not None and price>0 else None,"multiple","Positive quote price / positive FY+1 annual EPS; currency inferred from profile if absent",[("quote","price"),("estimates","epsAvg")])
        setv("Forward P/S",divide(cap,revenue) if allow_est and cap is not None and cap>0 else None,"multiple","Positive cap / positive FY+1 annual revenue; currency inferred from profile if absent",[("quote","marketCap"),("estimates","revenueAvg")])
        targets=first("price_targets")
        target_currency=targets.get("currency") or profile.get("currency")
        target=pick(targets,"targetConsensus","targetMedian") if targets.get("symbol")==symbol and target_currency and target_currency==qc else None
        setv("Analyst target",target,"currency","Consensus target; currency inferred from matching profile",[("price_targets","targetConsensus")],currency=qc)
        target_ratio=divide(target,price) if target is not None and target>0 and quote_ok else None
        setv("Target upside (%)",(target_ratio-1)*100 if target_ratio is not None else None,"percentage_points","(Consensus target / positive quote price - 1)*100; matching profile currency inferred",[("price_targets","targetConsensus"),("quote","price")])
        for key,field,unit in (("RSI (14)","rsi_14","index"),("SMA 20","sma_20","currency"),("SMA 50","sma_50","currency"),("SMA 200","sma_200","currency"),
            ("1M return (%)","return_1m_pct","percentage_points"),("3M return (%)","return_3m_pct","percentage_points"),("1Y return (%)","return_1y_pct","percentage_points"),
            ("Volatility (%)","annualized_volatility_pct","percentage_points"),("Max drawdown (%)","max_drawdown_pct","percentage_points"),("YTD Return","return_ytd_pct","percentage_points")):
            setv(key,tech.get(field),unit,"Same historical price basis: "+str(tech.get("price_basis"))+"; price return, not total return; "+("252-session annualization, sample standard deviation" if key=="Volatility (%)" else field),[("technicals",field)],currency=qc if unit=="currency" else None,basis={k:tech.get(k) for k in ("as_of","history_start","price_basis","observations")})
        for length in (50,200):
            ratio=divide(tech.get("last_close"),tech.get(f"sma_{length}"))
            setv(f"% From SMA {length}",(ratio-1)*100 if ratio is not None else None,"percentage_points",f"Historical last close / SMA {length} on same price basis - 1; *100",[("technicals","last_close"),("technicals",f"sma_{length}")])
        for alias,key in ALIASES.items():
            row[alias]=row.get(key);contracts[alias]={**contracts[key],"alias_of":key}
        all_registry={metric for r in SECTOR_METRIC_REGISTRY.values() for group in r.values() for metric in group}
        for key in set(BASE_KEYS)|all_registry:
            if key not in contracts:
                setv(key,None,"unknown","Unsupported: no validated formula/provider contract",reason="Unsupported: validated specialist/per-share/dividend/inventory contract unavailable")
                contracts[key]["status"]="unsupported"
        # Preserve the canonical registry spelling but disclose the actual forward-growth basis.
        contracts["Forward Revenue Growth FY+1"]["label_note"]="Canonical registry alias; calculated change is FY+2 versus FY+1, not historical-to-FY+1 growth"
        row["Metric contracts"]=contracts
        output.append(row)
    return json_safe(output)


def project_sector_row(row):
    """Mask every alias per company while retaining audited values in the audit contract."""
    row=dict(row)
    framework=row.get("Sector framework") or map_sector_to_framework(row.get("Sector"),row.get("Industry"))
    registry=SECTOR_METRIC_REGISTRY.get(framework,SECTOR_METRIC_REGISTRY["General / Cross-Sector"])
    avoid=set(registry["avoid_or_downweight"])
    preferred=set(registry["must_have"]+registry["preferred"])
    contracts={k:dict(v) for k,v in row.get("Metric contracts",{}).items()}
    canonical={v:k for k,v in ALIASES.items()}
    for key in list(row):
        identity=canonical.get(key,key)
        # Multiple aliases must all inherit the same canonical sector prohibition.
        names={key,identity,SECTOR_FAMILY.get(key,key)}|{alias for alias,target in ALIASES.items() if target==ALIASES.get(key,key)}
        prohibited=bool(names & avoid)
        if prohibited:
            row[key]=None
            if key in contracts: contracts[key]["applicability"]="downweighted";contracts[key]["reason"]="Excluded from primary analysis by canonical sector registry"
    # Specialist fields for other sectors never leak through a union of metric columns.
    specialist={m for r in SECTOR_METRIC_REGISTRY.values() for m in r["missing_but_useful"]}
    for key in specialist-set(registry["missing_but_useful"]):
        if key in row: row[key]=None
        if key in contracts: contracts[key]["applicability"]="inapplicable"
    row["Metric contracts"]=contracts
    return row


def format_metric(key,value,row):
    if value is None: return "\u2014"
    contract=row.get("Metric contracts",{}).get(key,{})
    unit=contract.get("unit")
    if not unit:
        # Explicit legacy-unit compatibility, no magnitude inference.
        unit="fraction" if key in FRACTION_KEYS else "percentage_points" if key in POINT_KEYS else "currency" if key in MONEY_KEYS else "multiple" if key in MULTIPLE_KEYS else "ratio" if key in RATIO_KEYS else "text"
        if unit=="currency":
            is_cash=key.startswith(("Operating cash flow", "Capital expenditure", "Free cash flow"))
            currency=row.get("Cash flow TTM currency" if is_cash and "(TTM)" in key else "Cash flow statement currency" if is_cash else "TTM currency" if "(TTM)" in key else "Statement currency" if "(latest period)" in key else "Quote currency")
            contract={"currency":currency}
    value_number=number(value)
    if value_number is None or unit in {"text","date","metadata","unknown"}: return str(value)
    if unit=="fraction": return f"{value_number*100:,.1f}%"
    if unit=="percentage_points": return f"{value_number:,.1f}%"
    if unit=="multiple": return f"{value_number:,.1f}x"
    if unit in {"currency","currency_per_share"}:
        prefix=(contract.get("currency") or row.get("Quote currency") or "Currency unavailable")+" "
        if abs(value_number)>=1e9:return f"{prefix}{value_number/1e9:,.1f}B"
        if abs(value_number)>=1e6:return f"{prefix}{value_number/1e6:,.1f}M"
        return f"{prefix}{value_number:,.2f}"
    return f"{value_number:,.2f}"

SECTOR_FAMILY = {
"Gross margin (TTM)":"Latest Gross Margin","Gross margin (latest period)":"Latest Gross Margin",
"Gross profit (TTM)":"Latest Gross Margin","Gross profit (latest period)":"Latest Gross Margin",
"EBITDA (TTM)":"Latest EBITDA Margin","EBITDA (latest period)":"Latest EBITDA Margin",
"EBITDA margin (TTM)":"Latest EBITDA Margin","EBITDA margin (latest period)":"Latest EBITDA Margin",
"FCF margin (latest period)":"FCF Margin","Free cash flow (TTM)":"FCF Margin","Free cash flow (latest period)":"FCF Margin",
"R&D as % revenue (latest period)":"R&D as % Revenue","Stock-based comp % revenue (latest period)":"Stock-Based Comp % Revenue",
"Capex to revenue (latest period)":"Capex to Revenue"}

FRACTION_KEYS = {"ROE","ROA","ROIC","FCF Yield","Earnings Yield","Dividend Yield","Dividend Payout Ratio","FCF yield (TTM, fraction)","Net margin (TTM, fraction)",
"Latest Gross Margin","Latest Operating Margin","Latest EBITDA Margin","Latest Net Margin","OCF Margin","FCF Margin"} | {f"{label} ({basis})" for label in ("Gross margin","Operating margin","EBITDA margin","Net margin","OCF margin","FCF margin") for basis in ("TTM","latest period")}
POINT_KEYS = {"Forward revenue growth (%)","Forward Revenue Growth FY+1","Target upside (%)","Price Target Upside","Revenue CAGR 3Y","Net Income CAGR 3Y","FCF CAGR 3Y","1Y Return","YTD Return","% From SMA 50","% From SMA 200","R&D as % Revenue","Stock-Based Comp % Revenue","Capex to Revenue"} | {f"{label} ({basis})" for label in ("R&D as % revenue","Stock-based comp % revenue","Capex to revenue") for basis in ("TTM","latest period")}

MONEY_KEYS={"Price","Market cap","Forward revenue","Forward revenue next period","Forward EPS","Forward EBITDA","Forward net income","Analyst target","SMA 20","SMA 50","SMA 200","Forward Revenue Next FY","Forward EPS Next FY"} | {f"{label} ({basis})" for label in ("Revenue","Gross profit","Operating income","EBITDA","Net income","Operating cash flow","Capital expenditure","Free cash flow") for basis in ("TTM","latest period")}
MULTIPLE_KEYS={"P/E TTM","P/S TTM","P/B TTM","P/FCF TTM","P/E (TTM)","P/S (TTM)","P/B (TTM)","P/FCF (TTM)","Forward P/E","Forward P/S","EV / EBITDA","EV / Sales","EV / FCF","EV/EBITDA (TTM)","EV/Sales (TTM)","EV/FCF (TTM)","Net Debt / EBITDA"}
RATIO_KEYS={"Cash Conversion","Income Quality","Debt / Assets","Debt / Capital","Current Ratio","Debt to Equity","Liabilities to Assets","RSI 14","RSI (14)"} | {f"Cash conversion ({basis})" for basis in ("TTM","latest period")}

POINT_KEYS |= {f"{field} TTM growth (%)" for field in INCOME_FIELDS+CASH_FIELDS}


DISPLAY_LABELS = {"1Y price return (%)":"252-session price return (%)", "3M price return (%)":"63-session price return (%)","Forward Revenue Growth FY+1":"Forward Revenue Growth FY+2 / FY+1", "Forward revenue growth (%)":"Forward revenue growth FY+2 / FY+1 (%)", "P/B (TTM)":"P/B (latest quarterly equity)", "P/B TTM":"P/B (latest quarterly equity)", "Debt/equity (TTM)":"Debt/equity (latest quarterly snapshot)"}

def quote_time(value):
    numeric=number(value)
    if numeric is None:return None
    try:
        parsed=datetime.fromtimestamp(numeric,timezone.utc)
        return parsed.isoformat(timespec="seconds") if parsed.date()<=date.today() else None
    except (ValueError,OverflowError,OSError):return None
