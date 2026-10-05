import os, json, requests
from pathlib import Path
from datetime import datetime, timezone
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[1]
key=os.environ.get('FMP_API_KEY') or dotenv_values(ROOT.parent/'.env').get('FMP_API_KEY')
if not key:
    raise SystemExit('Set FMP_API_KEY in your execution environment; do not paste it into chat.')
(ROOT/'raw/smoke').mkdir(parents=True,exist_ok=True)
url='https://financialmodelingprep.com/stable/profile'
try:
    r=requests.get(url,params={'symbol':'AAPL'},headers={'apikey':key},timeout=(10,25),verify=str(ROOT/'documentation/windows_ca_bundle.pem'))
    body=r.content
    if key.encode() in body:
        print('credential_reflection_quarantined'); raise SystemExit(1)
    (ROOT/'raw/smoke/profile-AAPL.body').write_bytes(body)
    meta={'endpoint':url,'parameters':{'symbol':'AAPL'},'http_status':r.status_code,'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'bytes':len(body)}
    (ROOT/'raw/smoke/profile-AAPL.metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    data=r.json()
    print('smoke',r.status_code,'records',len(data) if isinstance(data,list) else 0,'sector',data[0].get('sector') if isinstance(data,list) and data else None,'body_type',type(data).__name__)
except requests.RequestException as e:
    print('smoke transport failure',type(e).__name__)
