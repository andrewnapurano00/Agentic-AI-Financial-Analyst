"""One quote batch, one news batch and bounded reusable company fundamentals."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
import streamlit as st
from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.providers.discovery_numbers import finite_number
from langgraphagenticai.providers.valuation import reusable_component,normalize_rows
from langgraphagenticai.providers.company_evidence import credential_scope
from langgraphagenticai.providers.article_text import safe_news_url
from langgraphagenticai.portfolio_ideas.contracts import universe,clean

BASE="https://financialmodelingprep.com/stable/"


@st.cache_data(ttl=300,max_entries=16,show_spinner=False)
def load_ideas_evidence(names,api_key,shared=None):
    names=universe(",".join(names))
    if not api_key.strip():raise ValueError("Configure FMP for company evidence.")
    warnings=[]
    saved_quotes={}
    for symbol in names:
        source=(shared or {}).get(symbol)
        if source and source.get("credential_scope")==credential_scope(api_key) and reusable_component(source,"quote",symbol):
            try:
                valid=normalize_rows("quote",source["quote"],symbol,api_key,1)
                if len(valid)==1:saved_quotes[symbol]=(valid[0],dict(source["sources"]["quote"],reused=True))
            except (ValueError,TypeError):pass
    def fetch(route,params):
        try:
            raw=get_fmp_json(BASE+route,api_key=api_key,params=params,timeout=(3,12))
            return raw if isinstance(raw,list) else []
        except Exception as exc:
            status=getattr(exc,"status_code",None)
            detail=f" (HTTP {status})" if isinstance(status,int) and 400<=status<=599 else ""
            warnings.append(route+": unavailable"+detail+"; other evidence retained.")
            return []
    def company(symbol):
        source=(shared or {}).get(symbol)
        if not source or source.get("credential_scope")!=credential_scope(api_key):source=None
        result={"symbol":symbol,"sources":{}}
        for kind,route in (("profile","profile"),("ratios","ratios-ttm")):
            reused=reusable_component(source,kind,symbol)
            raw=source[kind] if reused else fetch(route,{"symbol":symbol})
            try:
                rows=normalize_rows(kind,raw,symbol,api_key,1)
            except (ValueError,TypeError):rows=[]
            result[kind]=rows[0] if len(rows)==1 else {}
            result["sources"][kind]=dict(source["sources"][kind],reused=True) if reused else dict(provider="FMP",retrieved_at=datetime.now(timezone.utc).isoformat(),status="available" if rows else "unavailable")
        return symbol,result
    with ThreadPoolExecutor(max_workers=3) as pool:
        needed=[s for s in names if s not in saved_quotes]
        quotes_future=pool.submit(fetch,"batch-quote",{"symbols":",".join(needed)}) if needed else None
        news_future=pool.submit(fetch,"news/stock",{"symbols":",".join(names),"limit":80,"from":(datetime.now(timezone.utc)-timedelta(days=7)).date().isoformat()})
        companies=dict(pool.map(company,names))
        quotes,articles=(quotes_future.result() if quotes_future else []),news_future.result()
        quotes.extend(row for row,_ in saved_quotes.values())
    present={row.get("symbol") for row in quotes if isinstance(row,dict)}
    missing=[symbol for symbol in names if symbol not in present]
    fallback_symbols=set()
    if missing:
        # Some FMP subscriptions allow /quote but not /batch-quote. Bound fallback
        # to one logical dispatch per missing company; do not splice quote fields.
        def individual(symbol):
            raw=fetch("quote",{"symbol":symbol})
            return symbol,[row for row in raw if isinstance(row,dict) and row.get("symbol")==symbol]
        with ThreadPoolExecutor(max_workers=3) as pool:
            for symbol,records in pool.map(individual,missing):
                quotes.extend(records)
                if records:fallback_symbols.add(symbol)
        if fallback_symbols:
            warnings.append("Batch coverage incomplete or unavailable; regular FMP company quotes used for "+", ".join(sorted(fallback_symbols))+".")
    now=datetime.now(timezone.utc)
    by_symbol={s:[] for s in names}
    for row in quotes:
        if isinstance(row,dict) and row.get("symbol") in by_symbol:by_symbol[row["symbol"]].append(row)
    rows={}
    for symbol in names:
        data=companies[symbol];profile,ratios=data["profile"],data["ratios"]
        if ratios.get("date"):
            try:
                period=datetime.fromisoformat(str(ratios["date"]).replace("Z","+00:00")).date()
                if period>now.date():ratios={}
            except (ValueError,TypeError):ratios={}
        quote=by_symbol[symbol][0] if len(by_symbol[symbol])==1 else {}
        price,stamp=finite_number(quote.get("price")),finite_number(quote.get("timestamp"))
        try:
            as_of=datetime.fromtimestamp(stamp,timezone.utc)
            dated=0<=(now-as_of).total_seconds()<=7*86400
        except (TypeError,ValueError,OverflowError,OSError):dated=False
        currencies={c for c in (quote.get("currency"),profile.get("currency")) if c}
        reasons=[]
        if not by_symbol[symbol]:reasons.append("quote unavailable")
        elif len(by_symbol[symbol])!=1:reasons.append("ambiguous duplicate quotes")
        else:
            if price is None or price<=0:reasons.append("positive quote price unavailable")
            if not dated:reasons.append("quote timestamp missing, future or older than seven days")
            if not currencies:reasons.append("quote/listing currency unavailable")
            elif currencies!={"USD"}:reasons.append("quote/listing currency conflicts or is not USD")
        if reasons:
            warnings.append(symbol+": "+"; ".join(reasons)+"; excluded from recommendations.")
            continue
        data["sources"]["quote"]=saved_quotes[symbol][1] if symbol in saved_quotes else dict(provider="FMP",route="/stable/quote" if symbol in fallback_symbols else "/stable/batch-quote",retrieved_at=now.isoformat(),as_of=as_of.isoformat(),status="available")
        facts={key:finite_number(ratios.get(field)) for key,field in {
            "pe_ttm":"priceToEarningsRatioTTM","pb_ttm":"priceToBookRatioTTM","ps_ttm":"priceToSalesRatioTTM",
            "net_margin_ttm":"netProfitMarginTTM","operating_margin_ttm":"operatingProfitMarginTTM",
            "debt_equity_ttm":"debtToEquityRatioTTM","dividend_yield_ttm":"dividendYieldTTM"}.items()}
        if facts["pe_ttm"] is None:facts["pe_ttm"]=finite_number(ratios.get("peRatioTTM"))
        technical={}
        for label,field in (("sma50","priceAvg50"),("sma200","priceAvg200")):
            value=finite_number(quote.get(field))
            technical[label]=value if value is not None and value>0 else None
            technical["distance_"+label+"_pct"]=100*(price/value-1) if value is not None and value>0 else None
        news=[];seen=set()
        for article in articles:
            if not isinstance(article,dict) or symbol not in {s.strip().upper() for s in str(article.get("symbol","")).split(",")}:continue
            url=safe_news_url(article.get("url"));title=clean(article.get("title"),(api_key,),200)
            try:
                published=datetime.fromisoformat(str(article.get("publishedDate","")).replace("Z","+00:00"))
                # FMP naive news times: calendar dates only; same-day timing unverified.
                in_range=0<=(now-published).total_seconds()<=7*86400 if published.tzinfo else 0<=(now.date()-published.date()).days<=7
            except (ValueError,TypeError):in_range=False
            identity=url or title.lower()
            if not title or not url or len(url)>2000 or not in_range or identity in seen:continue
            seen.add(identity)
            news.append(dict(id=f"{symbol}:news:{len(news)}",title=title,url=url,published=published.isoformat(),
                             time_basis="reported timezone" if published.tzinfo else "provider wall-clock; timezone unknown",provider="FMP"))
            if len(news)==2:break
        refs={symbol+":technicals":dict(basis="Provider priceAvg50/200; adjustment/observed-bar policy unverified",as_of=as_of.isoformat())} if any(v is not None for v in technical.values()) else {}
        if any(v is not None for v in facts.values()):refs[symbol+":fundamentals"]=dict(basis="Provider TTM ratios; units: multiples or fractions; period end may be unavailable",period_end=ratios.get("date"),**data["sources"]["ratios"])
        for article in news:refs[article["id"]]=dict(basis="Headline only; not verified causation",published=article["published"])
        rows[symbol]=dict(symbol=symbol,company=clean(profile.get("companyName") or symbol,(api_key,),100),sector=clean(profile.get("sector") or "Unknown",(api_key,),80),
                          price=price,currency="USD",as_of=as_of.isoformat(),currency_basis="quote reported" if quote.get("currency") else "current profile listing; quote units assumed compatible",
                          fundamentals=facts,technicals=technical,news=news,evidence_refs=refs,sources=data["sources"],
                          gaps=[label for label,missing in (("Fundamentals",not any(v is not None for v in facts.values())),("Technicals",not refs.get(symbol+":technicals")),("News",not news)) if missing])
    return dict(provider="FMP",retrieved_at=now.isoformat(),credential_scope=credential_scope(api_key),rows=rows,warnings=sorted(set(warnings)),news_basis="At most two headlines/company from one shared 80-article, seven-day batch; uneven/incomplete coverage.")
