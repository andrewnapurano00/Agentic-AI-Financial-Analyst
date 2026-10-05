from pathlib import Path
import os, re, json, importlib.util, ssl
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
print('modules', {m: bool(importlib.util.find_spec(m)) for m in ['openpyxl','requests','bs4','dotenv']})
print('env_key_present', bool(os.environ.get('FMP_API_KEY')))
for p in [REPO / '.env', REPO / '.streamlit/secrets.toml']:
    names = sorted(set(re.findall(r'(?im)^\s*([\w]*FMP[\w]*|FINANCIAL[\w]*KEY)\s*=', p.read_text(encoding='utf-8-sig')))) if p.exists() else []
    print(p.name, 'exists', p.exists(), 'key_names', names)
(ROOT/'documentation').mkdir(exist_ok=True)
bundle = ROOT/'documentation/windows_ca_bundle.pem'
bundle.write_text(''.join(ssl.DER_cert_to_PEM_cert(c) for c in ssl.create_default_context().get_ca_certs(binary_form=True)), encoding='ascii')
r = requests.get('https://site.financialmodelingprep.com/developer/docs', timeout=30, verify=str(bundle))
(ROOT/'documentation/official_docs.html').write_bytes(r.content)
print('official_docs', r.status_code, len(r.content))
s = BeautifulSoup(r.text, 'html.parser')
print('scripts', [(x.get('id'),len(x.text)) for x in s.find_all('script') if len(x.text)>2000])
data = s.find('script', id='__NEXT_DATA__')
if data:
    (ROOT/'documentation/official_docs_data.json').write_text(data.text, encoding='utf-8')
    print('nextkeys', list(json.loads(data.text).get('props',{}).get('pageProps',{})))
links = sorted(set(x.get('href','') for x in s.find_all('a') if '/developer/docs' in x.get('href','')))
(ROOT/'documentation/docs_links.json').write_text(json.dumps(links, indent=2),encoding='utf-8')
print('doc_links',len(links))
