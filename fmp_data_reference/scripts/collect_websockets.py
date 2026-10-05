"""Bounded official legacy WebSocket probes; outbound login payloads are never saved."""
import json, ssl, time, csv
from collections import defaultdict
from datetime import datetime,timezone
from reference import ROOT, SECTORS, key, safe_path, dump, writecsv, rel, extract_dates

SOURCES={
'FMP-235':('wss://websockets.financialmodelingprep.com','https://site.financialmodelingprep.com/developer/docs/websocket-api',list(SECTORS)),
'FMP-236':('wss://crypto.financialmodelingprep.com','https://site.financialmodelingprep.com/developer/docs/crypto-websocket',['BTCUSD']),
'FMP-237':('wss://forex.financialmodelingprep.com','https://site.financialmodelingprep.com/developer/docs/forex-websocket',['EURUSD'])}

def main():
    try:import websocket
    except ImportError:raise SystemExit('Installed websocket-client unavailable; no dependencies installed. REST coverage remains preserved.')
    secret=key();run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    coverage=list(csv.DictReader((ROOT/'coverage_matrix.csv').open(encoding='utf-8')))
    inventory=list(csv.DictReader((ROOT/'endpoint_inventory.csv').open(encoding='utf-8')))
    for api,(endpoint,doc,tickers) in SOURCES.items():
        start=time.monotonic();retrieved=datetime.now(timezone.utc).isoformat();samples=defaultdict(list);frames=[];status='empty_in_bounded_window';detail='No matching market messages in the 12-second window; not proof of provider noncoverage.';conn=None
        params={'subscription_tickers':[t.lower() for t in tickers],'max_seconds':12,'max_frames':128,'max_frame_bytes':65536,'records_per_ticker':5}
        try:
            conn=websocket.create_connection(endpoint,timeout=5,sslopt={'ca_certs':str(ROOT/'documentation/windows_ca_bundle.pem'),'cert_reqs':ssl.CERT_REQUIRED})
            conn.send(json.dumps({'event':'login','data':{'apiKey':secret}}))
            conn.send(json.dumps({'event':'subscribe','data':{'ticker':params['subscription_tickers']}}))
            while time.monotonic()-start<12 and len(frames)<128:
                conn.settimeout(min(2,max(.1,12-(time.monotonic()-start))))
                try:frame=conn.recv()
                except websocket.WebSocketTimeoutException:continue
                if not frame:break
                body=frame.encode('utf-8') if isinstance(frame,str) else frame
                if secret.encode() in body:status='credential_reflection_quarantined';detail='Credential-bearing response not persisted.';break
                if len(body)>65536:status='bounded_frame';detail='Oversized incoming frame not persisted; connection closed.';break
                p=ROOT/'raw'/api/run/('frame-'+str(len(frames)+1).zfill(4)+'.body');safe_path(p).write_bytes(body);frames.append(rel(p))
                text=body.decode('utf-8',errors='replace')
                if any(s in text.lower() for s in ['invalid api','unauthorized','not authorized','premium','subscription','denied','not allowed','do not have access']):
                    status='restricted';detail='Provider authentication/entitlement response; see original key-free server frame.';break
                try:payload=json.loads(text)
                except ValueError:continue
                records=payload if isinstance(payload,list) else [payload]
                for record in records:
                    if isinstance(record,dict):
                        ticker=str(record.get('s','')).upper()
                        if ticker in tickers and len(samples[ticker])<5:samples[ticker].append(record)
                if all(len(samples[t])>=5 for t in tickers):break
        except Exception as error:
            status='transport_failed';detail=type(error).__name__
        finally:
            if conn:
                try:conn.close(timeout=1)
                except Exception:pass
        metadata={'api_id':api,'endpoint':endpoint,'official_source':doc,'retrieved_at_utc':retrieved,'parameters':params,'status':status,'detail':detail,'received_frame_files':frames,'outbound_login_saved':False,'no_retries':True,'duration_seconds':round(time.monotonic()-start,2)}
        dump(ROOT/'raw'/api/run/'websocket_probe.metadata.json',metadata)
        # Replace the REST collector's unsupported marker with the actual bounded probe result.
        coverage=[r for r in coverage if not (r['api_id']==api and r['status']=='unsupported_transport')]
        for ticker in tickers:
            samplefile=''
            if samples[ticker]:
                p=ROOT/'samples'/api/run/(ticker+'-websocket.json');dump(p,samples[ticker]);samplefile=rel(p)
            coverage.append({'api_id':api,'category':'Websocket','endpoint_name':next(x['endpoint_name'] for x in inventory if x['api_id']==api),'ticker_or_input':ticker,'variant':'websocket-probe','status':'success' if samples[ticker] else status,'http_status':'','endpoint':endpoint,'parameters_json':json.dumps(params,sort_keys=True),'retrieved_at_utc':retrieved,'record_count':len(samples[ticker]),'data_dates_json':json.dumps(extract_dates(samples[ticker])),'sample_limit':5,'raw_file':frames[0] if frames else '', 'sample_file':samplefile,'binary_sample_file':'','format':'websocket_json_frames','cache_reused':False,'detail':detail if not samples[ticker] else 'Actual matched messages; original frame fields unchanged.','applicability_notes':'Stock stream subscribed to all 11 selected tickers in one connection.' if api=='FMP-235' else 'Non-stock stream uses documented lowercase btcusd/eurusd subscription.','parameter_controls_basis':'Official legacy login/subscribe protocol. Outbound credential payload omitted. Lowercase subscriptions required by official guidance.'})
        item=next(x for x in inventory if x['api_id']==api)
        item.update(verified_endpoint=endpoint,official_example=endpoint,official_documentation=doc,mapping_status='official_legacy_websocket_documented',mapping_notes='Bounded documented login/subscription probe; exact access tested, not assumed.',stock_applicable=api=='FMP-235',collection_scope='stock_stream' if api=='FMP-235' else 'non_stock_stream')
        writecsv(ROOT/'coverage_matrix.csv',coverage);writecsv(ROOT/'endpoint_inventory.csv',inventory)
        print(api,status,'market_records',sum(len(v) for v in samples.values()),'server_frames',len(frames),flush=True)
    writecsv(ROOT/'raw'/('coverage-websocket-'+run+'.csv'),coverage)

if __name__=='__main__':main()
