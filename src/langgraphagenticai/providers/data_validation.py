"""Explicit read-only endpoint probes; bounded, sanitized session output only."""
from datetime import date, datetime, timedelta, timezone
import json
import math
import re
from time import perf_counter
from urllib.parse import urlsplit
import requests
from .data_validation_catalog import endpoint
from .fmp_http import get_fmp_json, ProviderRequestError
from langgraphagenticai.utils.safety import redact_sensitive_text

MAX_BYTES = 1_000_000
MAX_ROWS = 1000


def normalize_symbol(value):
    symbol = str(value or "").strip().upper()
    if not re.fullmatch(r"\^?[A-Z0-9][A-Z0-9.=-]{0,19}", symbol):
        raise ValueError("Enter one ticker, such as AAPL, BRK-B, SPY or ^GSPC.")
    return symbol


def defaults_for(item, today=None):
    today = today or datetime.now(timezone.utc).date()
    values = {k:v for k,v in item["defaults"].items() if v is not None}
    for name in ("from", "from_date"):
        if name in item["allowed"]:
            values[name] = (today-timedelta(days=30)).isoformat()
    for name in ("to", "to_date"):
        if name in item["allowed"]:
            values[name] = today.isoformat()
    return values


def prepare(identifier, ticker, parameters=None, query=""):
    item = endpoint(identifier)
    if not isinstance(parameters, dict):
        raise ValueError("Parameters must be a JSON object.")
    if set(parameters)-set(item["allowed"]):
        raise ValueError("Only this endpoint's listed parameters are allowed; credentials and ticker overrides are not accepted.")
    params = {**defaults_for(item), **parameters}
    for name,value in params.items():
        if isinstance(value,(dict,list)) or value is None:
            raise ValueError("Use scalar parameter values; remove optional null fields.")
        if name in {"limit","days","page","year","quarter","period_length"} or name=="period" and item["id"]=="fmp.v3.rsi":
            if isinstance(value,bool) or not isinstance(value,int):
                raise ValueError(name+" must be an integer.")
            low,high = (0,100) if name=="page" else (1,4) if name=="quarter" else (1990,date.today().year+1) if name=="year" else (1,90 if item["provider"]=="Serper" else 3650) if name=="days" else (1,252) if name in {"period_length","period"} else (1,10 if item["provider"]=="Serper" else 100)
            if not low <= value <= high:
                raise ValueError(name+" is outside its supported checker range.")
        elif name=="nonadjusted":
            if not isinstance(value,bool): raise ValueError("nonadjusted must be true or false.")
        else:
            if not isinstance(value,str) or not value.strip() or len(value)>200 or any(ord(c)<32 for c in value):
                raise ValueError(name+" requires a short nonempty text value.")
            if name=="period" and value not in {"annual","quarter"}:
                raise ValueError("Period must be annual or quarter.")
            if name=="timeframe" and value not in {"daily","1min","5min","15min","30min","1hour","4hour"}:
                raise ValueError("Select a supported timeframe.")
            if name=="interval" and value not in {"1d","5m"}: raise ValueError("Yahoo interval must be 1d or 5m.")
            if name=="type" and value!="rsi": raise ValueError("This app route uses RSI.")
            if name=="cik" and not re.fullmatch(r"[0-9]{1,10}",value): raise ValueError("CIK requires up to ten digits.")
            if name in {"from","to","from_date","to_date","published_after"}:
                try: day=date.fromisoformat(value[:10])
                except ValueError: raise ValueError("Use ISO dates: YYYY-MM-DD.") from None
                if day>datetime.now(timezone.utc).date(): raise ValueError("Future dates are not supported by the checker.")
    for first,last in (("from","to"),("from_date","to_date")):
        if first in params and last in params and (params[first]>params[last] or (date.fromisoformat(params[last])-date.fromisoformat(params[first])).days>3650):
            raise ValueError("Use an ordered date window no longer than ten years.")
    if item["id"]=="yahoo.history" and params.get("interval")=="5m" and params["days"]>30:
        raise ValueError("Use at most 30 days for five-minute Yahoo history.")
    symbol = normalize_symbol(ticker) if item["scope"] in {"ticker","search"} else ""
    if item["symbol_param"] and symbol: params[item["symbol_param"]]=symbol
    if item["scope"]=="search":
        query = query.strip() or symbol+" company financial news"
        if len(query)>500 or any(ord(c)<32 for c in query): raise ValueError("Search text must be at most 500 characters.")
        params["query"]=query
    route = item["route"].replace("{symbol}",symbol)
    return item, symbol, route, params


def sanitize_payload(value, credentials=()):
    """Bound structures and replace credentials before any truncation or output."""
    remaining=[MAX_BYTES//2]; count=[0]; truncated=[False]
    def text(value):
        result=str(value)
        for secret in credentials:
            if secret: result=result.replace(secret,"[REDACTED]")
        result=redact_sensitive_text(result)
        if result.lower().startswith(("javascript:","data:","file:")):return "[Unsafe link omitted]"
        if result.startswith(("http://","https://")):
            try:
                if urlsplit(result).username or urlsplit(result).password:return "[Credential-bearing link omitted]"
            except ValueError:return "[Invalid link omitted]"
        length=min(10000,max(0,remaining[0]))
        if len(result)>length:truncated[0]=True
        result=result[:length]
        remaining[0]-=len(result)
        return result
    def walk(value,depth=0):
        count[0]+=1
        if depth>12 or count[0]>20000 or remaining[0]<=0:
            truncated[0]=True;return "[Response preview limit]"
        if isinstance(value,dict):
            result={}
            for i,(key,item) in enumerate(value.items()):
                if i>=MAX_ROWS or count[0]>20000 or remaining[0]<=0:truncated[0]=True;break
                name=text(key)
                sensitive=any(token in re.sub(r"[^a-z]","",str(key).lower()) for token in ("apikey","token","apitoken","accesstoken","authorization","password","secret","credential","cookie"))
                result[name]="[REDACTED]" if sensitive else walk(item,depth+1)
            return result
        if isinstance(value,(list,tuple)):
            if len(value)>MAX_ROWS:truncated[0]=True
            result=[]
            for item in value[:MAX_ROWS]:
                if count[0]>20000 or remaining[0]<=0:truncated[0]=True;break
                result.append(walk(item,depth+1))
            return result
        if value is None or isinstance(value,(bool,int)):return value
        if isinstance(value,float):return value if math.isfinite(value) else None
        return text(value)
    cleaned=walk(value)
    if len(json.dumps(cleaned,ensure_ascii=False).encode())>MAX_BYTES//2:
        return {"preview":"Response too large for a safe download; narrow the request parameters."},True
    return cleaned,truncated[0]


def response_rows(payload):
    if isinstance(payload,list):return [r for r in payload if isinstance(r,dict)]
    if isinstance(payload,dict):
        for key in ("historical","data","results"):
            if key in payload:
                if isinstance(payload[key],list):return [r for r in payload[key] if isinstance(r,dict)]
                if isinstance(payload[key],dict):return response_rows(payload[key])
                return []
        return [payload] if payload else []
    return []


def _dispatch(item, symbol, route, params, credentials):
    provider=item["provider"]
    if provider=="FMP REST":
        return get_fmp_json("https://financialmodelingprep.com"+route,api_key=credentials["FMP_API_KEY"],params=params,timeout=(5,25))
    if provider=="FMP MCP":
        from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient
        client=FMPMCPClient(credentials["FMP_API_KEY"],retries=0,timeout_seconds=30)
        return getattr(client,item["method"])(**params)
    if provider=="Marketaux":
        response=requests.get(route,params={**params,"api_token":credentials["MARKETAUX_API_KEY"]},timeout=(5,25),allow_redirects=False)
        if response.status_code>=300:
            raise ProviderRequestError("Marketaux","Marketaux request failed.",status_code=response.status_code)
        result=response.json()
        if not isinstance(result,dict) or "error" in result:raise ValueError("Provider error envelope.")
        return result
    if provider=="Serper":
        from langgraphagenticai.tools.serper_tools import SerperClient
        return SerperClient(credentials["SERPER_API_KEY"]).search(params["query"],news=item["id"]=="serper.news",days=params["days"],limit=min(10,params["limit"]),filter_dates=True)
    if provider=="Yahoo Finance":
        import yfinance as yf
        from curl_cffi import requests as curl_requests
        with curl_requests.Session(impersonate="chrome",timeout=15) as session:
            if item["id"]=="yahoo.info":return yf.Ticker(symbol,session=session).get_info()
            now=datetime.now(timezone.utc).date()
            frame=yf.download(symbol,start=(now-timedelta(days=params["days"])).isoformat(),end=(now+timedelta(days=1)).isoformat(),interval=params["interval"],auto_adjust=True,progress=False,threads=False,timeout=15,session=session)
            if frame.empty:return []
            frame=frame.copy()
            frame.columns=[" | ".join(str(v) for v in c) if isinstance(c,tuple) else str(c) for c in frame.columns]
            return json.loads(frame.reset_index().to_json(orient="records",date_format="iso"))
    raise ValueError("Unregistered provider.")


def fetch_endpoint(identifier,ticker,parameters=None,query="",credentials=None):
    item,symbol,route,params=prepare(identifier,ticker,{} if parameters is None else parameters,query)
    credentials=credentials or {}
    key_name={"FMP REST":"FMP_API_KEY","FMP MCP":"FMP_API_KEY","Marketaux":"MARKETAUX_API_KEY","Serper":"SERPER_API_KEY"}.get(item["provider"])
    if key_name and not str(credentials.get(key_name) or "").strip():raise ValueError("Configure "+key_name+" in Settings before fetching this endpoint.")
    started=perf_counter()
    result={"endpoint_id":identifier,"label":item["label"],"provider":item["provider"],"route":route,"ticker":symbol or None,"parameters":params,"status":"error","retrieved_at":datetime.now(timezone.utc).isoformat(),"http_status":None,"data":None,"truncated":False}
    try:
        raw=_dispatch(item,symbol,route,params,credentials)
        data,truncated=sanitize_payload(raw,tuple(credentials.values()))
        result.update(data=data,truncated=truncated)
        if isinstance(raw,dict) and (raw.get("ok") is False or raw.get("error") or raw.get("Error Message")):
            result["message"]="Provider returned a failure envelope; inspect the sanitized response and check access or parameters."
        else:
            rows=response_rows(data)
            result["status"]="available" if rows else "empty"
            result["record_count"]=len(rows)
            identities=sorted({str(r["symbol"]) for r in rows if isinstance(r.get("symbol"),str)} | ({data["symbol"]} if isinstance(data,dict) and isinstance(data.get("symbol"),str) else set()))
            result["returned_symbols"]=identities[:30]
            if item["scope"]=="ticker" and item["provider"].startswith("FMP") and identities and any(s!=symbol for s in identities) and "stock-peers" not in route and not route.endswith("/peers"):
                result["identity_warning"]="Returned symbols differ from the requested ticker. Raw data is retained for validation; do not treat this as verified company evidence."
    except Exception as exc:
        status=getattr(exc,"status_code",None)
        result["http_status"]=status
        result["message"]=(f"HTTP {status}: authentication failed; check the configured provider key." if status==401 else f"HTTP {status}: endpoint access denied; check provider entitlement or permissions." if status in (402,403) else "HTTP 429: rate limited; wait before fetching again." if status==429 else f"HTTP {status}: provider request failed." if status else "Provider request failed, timed out or returned an invalid response. Check settings and try an explicit fetch again.")
    result["elapsed_seconds"]=round(perf_counter()-started,3)
    result["basis"]="Raw provider/adapter response. Retrieval success does not verify financial accuracy, period, currency, adjustment basis or freshness. Yahoo history explicitly uses auto_adjust=True. No fallback provider or model was invoked."
    # The raw body was already sanitized once. Keep its node budget separate
    # from request metadata so a large response cannot evict required UI fields.
    metadata,truncated=sanitize_payload({k:v for k,v in result.items() if k!="data"},tuple(credentials.values()))
    metadata["data"]=result["data"]
    metadata["truncated"]=bool(result["truncated"] or truncated)
    return metadata
