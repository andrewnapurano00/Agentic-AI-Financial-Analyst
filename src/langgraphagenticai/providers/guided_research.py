"""Narrow read-only contracts for Guided research (D01-D04)."""
from datetime import datetime, timezone, timedelta
import math
import re
from urllib.parse import urlsplit
import requests
from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.state.research_context import normalize_company_symbol
from langgraphagenticai.utils.safety import redact_sensitive_text

TOOLS = ('quote_profile', 'annual_income', 'news_snapshot')

def clean(value, secrets=()):
    # Replace complete configured credentials before truncation can split them.
    text = str(value or '')
    for secret in secrets:
        if secret:
            text = text.replace(secret, '[REDACTED]')
    return redact_sensitive_text(text, max_length=800)

def safe_link(value):
    if not isinstance(value, str) or len(value) > 1500:
        return ''
    if any(c.isspace() or ord(c)<32 for c in value):
        return ''
    try:
        p = urlsplit(value)
    except ValueError:
        return ''
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password or p.query or p.fragment:
        return ''
    return value

def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None

def collect(tool, symbol, *, fmp_key='', news_key='', now=None):
    symbol = normalize_company_symbol(symbol)
    if tool not in TOOLS:
        raise ValueError('Unapproved tool.')
    injected_now = now
    now = now or datetime.now(timezone.utc)
    records, warnings = [], []
    secrets = (fmp_key, news_key)
    def record(route, fields, basis, as_of=None, currency=None, unit=None, notes=None):
        missing = [k for k,v in fields.items() if v is None]
        records.append(dict(id=f'{tool}-{len(records)+1}', symbol=symbol, provider='Marketaux' if tool == 'news_snapshot' else 'FMP', route=route, status='missing' if len(missing)==len(fields) else 'partial' if missing else 'available', retrieved_at=(injected_now or datetime.now(timezone.utc)).isoformat(), as_of=as_of, basis=basis, currency=currency, unit=unit, fields=fields, missing=missing, limitations=notes or []))
    def fmp(route, params):
        rows = get_fmp_json('https://financialmodelingprep.com'+route, api_key=fmp_key, params={'symbol':symbol, **params})
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            raise ValueError('No usable provider row.')
        row=rows[0]
        if normalize_company_symbol(row.get('symbol')) != symbol:
            raise ValueError('Provider security mismatch.')
        return row
    def attempt(fn):
        try:
            fn()
        except Exception:
            warnings.append('Provider response unavailable or failed validation; successful evidence retained.')
    if tool == 'quote_profile':
        currency=[None]
        def profile():
            row=fmp('/stable/profile', {})
            currency[0]=row.get('currency') if isinstance(row.get('currency'), str) and re.fullmatch(r'[A-Z]{3}',row['currency']) else None
            fields={k:clean(row[k], secrets) if isinstance(row.get(k),str) else None for k in ('companyName','sector','industry','description')}
            record('/stable/profile', fields, 'undated business profile', notes=['Profile has no verified business as-of date.'])
        def quote():
            row=fmp('/stable/quote', {})
            ts=number(row.get('timestamp'))
            if ts is None:
                raise ValueError('Missing quote date.')
            dated=datetime.fromtimestamp(ts, timezone.utc)
            if dated>now:
                raise ValueError('Future quote.')
            record('/stable/quote', {k:number(row.get(k)) for k in ('price','marketCap')}, 'point-in-time quote', dated.isoformat(), currency[0], {'price':'currency/share','marketCap':'currency amount'}, ['Currency is profile-reported; actual quote currency is unverified. Price adjustment basis unknown.', 'Quote timestamp is interpreted as Unix seconds; dictionary units are unknown and this interpretation is inferred.'])
        attempt(profile); attempt(quote)
    elif tool == 'annual_income':
        def annual():
            row=fmp('/stable/income-statement', {'period':'annual','limit':1})
            date=datetime.strptime(row.get('date',''), '%Y-%m-%d').date()
            curr=row.get('reportedCurrency')
            if row.get('period') != 'FY' or not isinstance(curr,str) or not re.fullmatch(r'[A-Z]{3}',curr) or date>now.date():
                raise ValueError('Invalid annual basis.')
            record('/stable/income-statement', {k:number(row.get(k)) for k in ('revenue','operatingIncome','netIncome')}, 'annual FY', date.isoformat(), curr, 'currency amount', ['Annual fiscal amounts; not TTM, growth, EPS or ratios.', 'Original provider monetary values are preserved without rescaling; exact monetary scaling has not been independently verified.'])
        attempt(annual)
    else:
        def news():
            if not news_key:
                raise ValueError('Missing news key.')
            response=requests.get('https://api.marketaux.com/v1/news/all', params={'api_token':news_key,'symbols':symbol,'filter_entities':'true','limit':5,'page':1,'published_after':(now-timedelta(days=7)).isoformat()}, timeout=(5,20))
            response.raise_for_status()
            payload=response.json()
            rows=payload.get('data') if isinstance(payload,dict) else None
            if not isinstance(rows,list):
                raise ValueError('Invalid news response.')
            seen=set(); rejected=0
            for row in rows[:5]:
                try:
                    if not isinstance(row,dict) or not isinstance(row.get('entities'),list) or not any(isinstance(e,dict) and e.get('symbol')==symbol for e in row['entities']):
                        raise ValueError('Identity missing.')
                    published=datetime.fromisoformat(str(row.get('published_at','')).replace('Z','+00:00'))
                    if published.tzinfo is None or not now-timedelta(days=7)<=published<=now:
                        raise ValueError('Publication outside window or unknown.')
                    url=safe_link(row.get('url'))
                    title=clean(row.get('title',''),secrets)
                    if not url or not title:
                        raise ValueError('Source link or title missing.')
                    identity=(url,title.casefold())
                    if identity in seen:
                        rejected+=1
                        continue
                    seen.add(identity)
                    fields={k:clean(row.get(k,''),secrets) or None for k in ('title','source','description')}
                    fields['url']=clean(url,secrets)
                    record('/v1/news/all',fields,'news publication',published.isoformat(), notes=['Single page, maximum five records; requested seven-day coverage is incomplete.'])
                except (ValueError,TypeError,OverflowError):
                    rejected+=1
            if rejected or len(rows)>5:
                warnings.append(f'{rejected + max(0,len(rows)-5)} news records omitted: invalid identity/date/link, duplicate or page limit.')
        attempt(news)
    usable=any(e['status']!='missing' for e in records)
    status='failed' if warnings and not records else 'missing' if records and not usable else 'partial' if records and (warnings or any(e['status']!='available' for e in records)) else 'available' if records else 'empty'
    return dict(tool=tool, symbol=symbol, status=status, evidence=records, warnings=warnings)
