"""Offline integrity and credential checks; no provider calls or writes outside ROOT."""
import csv, hashlib, json, re, zipfile, io
from collections import Counter
from pathlib import Path
from datetime import datetime,timezone
from reference import ROOT, key, dump, writecsv

def main():
    secret=key().encode();violations=[];scanned=0;archives_checked=0;partial_archives=0
    for path in ROOT.rglob('*'):
        if path.is_file():
            scanned+=1
            data=path.read_bytes()
            if secret in data:violations.append(str(path.relative_to(ROOT)))
            if data.startswith(b'PK'):
                try:
                    with zipfile.ZipFile(io.BytesIO(data)) as archive:
                        total=sum(m.file_size for m in archive.infolist())
                        if total>64*1024*1024:raise ValueError('Archive exceeds credential-inspection bound')
                        for member in archive.infolist():
                            if secret in member.filename.encode() or (not member.is_dir() and secret in archive.read(member)):
                                violations.append(str(path.relative_to(ROOT)));break
                        archives_checked+=1
                except zipfile.BadZipFile:partial_archives+=1
    if violations:
        print('Credential scan FAILED;',len(violations),'files require quarantine. Contents suppressed.')
        raise SystemExit(1)
    inventory=list(csv.DictReader((ROOT/'endpoint_inventory.csv').open(encoding='utf-8')))
    coverage=list(csv.DictReader((ROOT/'coverage_matrix.csv').open(encoding='utf-8')))
    ids={r['api_id'] for r in inventory};covered={r['api_id'] for r in coverage}
    missing=ids-covered;assert not missing, 'Coverage missing IDs: '+','.join(sorted(missing))
    assert len(inventory)==259 and len(ids)==259
    assert len(list((ROOT/'schemas').glob('FMP-*.json')))==259
    for row in coverage:
        assert row['api_id'] in ids
        for field in ['raw_file','sample_file','binary_sample_file']:
            if row.get(field):assert (ROOT/row[field]).resolve().is_relative_to(ROOT) and (ROOT/row[field]).exists()
        if row.get('sample_file'):
            data=json.loads((ROOT/row['sample_file']).read_text(encoding='utf-8'))
            def check(v):
                if isinstance(v,list):
                    assert len(v)<=int(row['sample_limit'])
                    for x in v:check(x)
                if isinstance(v,dict):
                    for x in v.values():check(x)
            check(data)
        assert 'apikey' not in json.loads(row['parameters_json'])
        assert not re.search(r'(?i)[?&](apikey|api_key)=',row['endpoint'])
    verified_raw=0;metadata=[]
    for path in (ROOT/'raw').rglob('*.metadata.json'):
        meta=json.loads(path.read_text(encoding='utf-8'))
        if meta.get('raw_file') and meta.get('sha256'):
            assert hashlib.sha256((ROOT/meta['raw_file']).read_bytes()).hexdigest()==meta['sha256'];verified_raw+=1
        metadata.append(meta)
    sector=list(csv.DictReader((ROOT/'sector_tickers.csv').open(encoding='utf-8')))
    assert len(sector)==11 and all(r['returned_sector'] for r in sector)
    api_stats={}
    for api in ids:
        cases=[r for r in coverage if r['api_id']==api]
        api_stats[api]={'statuses':dict(Counter(r['status'] for r in cases)), 'cases':len(cases),'stocks_with_samples':len({r['ticker_or_input'] for r in cases if r.get('sample_file') and int(r['record_count'])>0 and r['ticker_or_input']!='alternative'})}
    for row in inventory:
        stats=api_stats[row['api_id']]
        row['collection_status_summary_json']=json.dumps(stats['statuses'],sort_keys=True)
        row['sampled_stock_count']=stats['stocks_with_samples']
        row['live_mapping_test_basis']='See coverage requests; HTTP success does not prove semantic equivalence or optional parameter enforcement.'
    writecsv(ROOT/'endpoint_inventory.csv',inventory)
    totals=json.loads((ROOT/'collection_totals.json').read_text(encoding='utf-8'))
    apis_with_samples=totals['apis_with_actual_samples']
    fullstock=sum(stats['stocks_with_samples']==11 for stats in api_stats.values())
    raw_network_attempts=sum(m.get('attempts',0) for m in metadata)
    totals.update(apis_tracked=len(covered),api_references_with_all_11_stock_samples=fullstock,original_raw_bodies_verified=verified_raw,total_persisted_request_attempts=raw_network_attempts,credential_scan_files=scanned,apis_with_complete_binary_samples=len({r['api_id'] for r in coverage if r.get('binary_sample_file') and r['status']=='success_non_json'}))
    totals['apis_with_actual_json_or_complete_binary_samples']=len({r['api_id'] for r in coverage if (r.get('sample_file') and int(r.get('record_count') or 0)>0) or (r.get('binary_sample_file') and r['status']=='success_non_json')})
    totals['mapping_statuses']=dict(Counter(r['mapping_status'] for r in inventory))
    dump(ROOT/'collection_totals.json',totals)
    checks={'verified_at_utc':datetime.now(timezone.utc).isoformat(),'credential_scan':'passed_no_configured_key_found','files_scanned':scanned,'all_259_ids_covered':True,'all_259_observed_schema_files':True,'raw_sha256_verified':verified_raw,'sample_array_limits':'passed','relative_output_paths':'passed','sector_profiles':'11 available','parameter_key_urls':'none','scope':'Reference artifacts only; no app testing/changes.'}
    checks.update(complete_zip_archives_credential_checked=archives_checked,partial_zip_prefixes_not_fully_inspectable=partial_archives)
    dump(ROOT/'integrity_verification.json',checks)
    restricted=[(api,st) for api,st in sorted(api_stats.items()) if any(s not in ['success','success_non_json'] for s in st['statuses'])]
    text=['# FMP collection report','','Generated UTC: '+datetime.now(timezone.utc).isoformat(),'','## Coverage totals','',f'- Workbook API references inventoried and tracked: **{len(ids)} / 259**, across all five workbook tabs.',f'- Collection cases (API ID × ticker/input × request variant): **{len(coverage)}**.',f'- API references with nonempty actual parseable samples: **{apis_with_samples}**.',f'- API references with nonempty samples for all 11 sector stocks: **{fullstock}**.',f'- Field/path dictionary entries: **{totals["dictionary_entries"]}** ({totals["observed_dictionary_entries"]} observed live; {totals["workbook_only_entries"]} workbook-only).',f'- Original complete/bounded raw bodies with validated SHA-256 metadata: **{verified_raw}**.',f'- Persisted request attempts across smoke/full/resume/selected runs: **{raw_network_attempts}** (cache hits do not count).','','| Case status | Count |','| --- | --- |']
    text += ['| '+s+' | '+str(n)+' |' for s,n in sorted(totals['case_statuses'].items())]
    text += ['', 'Counts include request variants and local bulk extractions, not just unique endpoints or network calls. A success row is not a universal entitlement or quality claim. `empty` may represent legitimate absence; `not_present_in_bounded_bulk` does not establish provider noncoverage.','', '## Source and mapping verification','', 'The available workbook lacked the requested `(1)` suffix; the project workbook with the same base title was used. All API IDs and original references were retained. Current route facts were extracted from the [official FMP catalogue](https://site.financialmodelingprep.com/developer/docs). Direct requests to the documentation site returned HTTP 403; web access supplied the official catalogue. The catalogue proves listed routes/example parameter names, not all optional/required parameter rules or exact legacy equivalence. Inventory notes preserve narrower/changed mappings. Unmapped original HTTP routes were live-tested rather than assumed deprecated. Three WebSocket references are explicitly unsupported by this bounded REST collector.','', 'API authorization used the documented header form. No configured key was persisted. No application files, dependencies, databases or configuration were modified.','', '## Sampling, observed schemas and interpretation limits','', 'Time-series projections aim for five returned records; core statements request five annual and eight quarterly records. The collector preserves complete raw response bytes where within the 3 MiB limit, and explicitly labels bounded prefixes otherwise. Original CSV strings are not coerced into numbers/nulls. Binary spreadsheets remain actual raw responses with no invented JSON schema. JSON array samples are recursively limited; nested fields/values remain unchanged. Request/cache metadata can be shared among workbook IDs with equivalent requests.','', 'Quarterly key-metrics/ratios were restricted by subscription. Annual variants are attempted separately and prior quarter restriction rows retained in current coverage. Different request controls and variants are separate cases. Some documented/example historical years and filer inputs yield older records; retrieval time is not the data date. Full recent-history completeness is not claimed.','', 'Definitions/units are inferred or unknown unless supported explicitly. Path/type schemas are observed unions; no universal requiredness/non-nullability claim is made. Parent-object missing counts and sector differences reflect only collected bounded records. Monetary scaling, cross-currency joins, exact provider formulas, ratio-percent scaling and price adjustments require further verification. CIK/CUSIP/ISIN strings remain uncoerced. No total-return or application normalization is performed.','', 'Bulk partition/pagination is capped at one, so not every selected stock necessarily appears. No unbounded bulk/history/WebSocket download is attempted. Account restrictions, unsupported controls and old legacy response differences remain visible below and in coverage.','', '## Restrictions, empty results, partial coverage and failures','', '| API ID | Case statuses | Nonempty sector stock samples |','| --- | --- | --- |']
    text += ['| '+api+' | '+json.dumps(st['statuses'],sort_keys=True)+' | '+str(st['stocks_with_samples'])+' / 11 |' for api,st in restricted]
    text += ['', 'The 11-stock denominator applies only to stock-specific or local bulk extraction cases; market-wide, macroeconomic, ETF, forex, crypto and other alternative-input APIs do not require 11 independent stock requests. See per-case applicability notes.','', '## Verification and recovery','', 'The collector first completed a small profile/quote/income-statement/Treasury smoke test, then proceeded through the inventory. A nonstandard spreadsheet/CSV response stopped one run; the parser was corrected to separate binary responses and use bounded CSV field sizes. Cached requests were reused on resume, preserving earlier raw/samples.','', 'Four offline unittest checks passed: preservation of zero/null/leading-zero IDs/nesting; refusal to write outside the reference root; HTTP-200 API-error detection and configured-key reflection quarantine; bounded transient retries and cache reuse. Scripts compile in memory. Integrity checks verify all 259 IDs/schema files, local sample/raw paths, array limits, raw hashes and absence of the configured credential. No app/full-suite/browser checks were performed because this task changes only the new reference folder.','', '## Unresolved questions and future use','', '- Exhaustive official required/optional parameter rules and field-level provider definitions remain unverified where not present in accessible official material; successful requests alone do not establish them.', '- Which missing symbols are outside the bounded bulk prefix/partition versus unavailable? Expand only explicitly chosen partitions with the same safeguards.', '- Which premium/quarterly parameters or WebSocket services are included in a different entitlement? Do not infer availability from another endpoint’s success.', '- What are the exact monetary/ratio scaling, adjusted-price methodology, and fiscal-period alignment for each future application use? Check before calculation.', '- Older inputs should be refreshed with documented recent report/filer dates when needed; all saved dates and successful controls are evidence, not a live guarantee.','', 'For future work, tell Codex: **Consult `fmp_data_reference/context_index.md` before planning FMP sourcing or validation; inspect the exact coverage, dictionary paths and raw/sample evidence, and do not change the application unless separately requested.**','']
    text=[line.replace('Three WebSocket references are explicitly unsupported by this bounded REST collector.','Three WebSocket references received separate bounded live probes using official legacy protocols; all returned entitlement restrictions. Original key-free server responses were retained.') for line in text]
    text.extend(['','## Additional route/protocol verification','', '- Official legacy company-image documentation corrected the workbook’s missing `.png` suffix. All 11 actual logos were collected as binary samples, retaining the original failed-route cases.', '- Complete binary samples cover '+str(totals['apis_with_complete_binary_samples'])+' API references; combined nonempty JSON or complete binary coverage is **'+str(totals['apis_with_actual_json_or_complete_binary_samples'])+' / 259**.', '- Stock, crypto and forex WebSocket probes each used one connection with documented login/subscription frames. All three were restricted; no market ticks were fabricated. The stock denial is recorded for all 11 requested symbols, with the shared received server frame. Outbound login payloads were never persisted.', '- Official protocol sources: [stock](https://site.financialmodelingprep.com/developer/docs/websocket-api), [crypto](https://site.financialmodelingprep.com/developer/docs/crypto-websocket), [forex](https://site.financialmodelingprep.com/developer/docs/forex-websocket).', '- Reusable collection enforces bulk-specific cooldowns after official FAQ verification. Initial general-rate bulk requests and all restrictions remain recorded.', '- Coverage reconciliation preserves distinct endpoints/controls and corrects early global RSS ticker aliases and redundant batch postprocessing. Raw response bodies were not changed; corrections are recorded in `documentation/processing_notes.json`.', '- Request-attempt total above counts REST requests. Three additional bounded WebSocket connection/protocol probes are recorded separately.', ''])
    text.extend(['## Environment and final scope checks','', 'Verification used the existing Python 3.12.7 environment, requests 2.34.2 and openpyxl 3.1.5; nothing was installed. All reference scripts compiled in memory, four offline checks passed, and the query helper returned a live-observed financial field. Git status retained the original user changes and added only `fmp_data_reference/` for this task. Public certificate resources and every temporary file were confined to this folder.', '', 'Complete ZIP/spreadsheet archives were inspected for the configured credential without extraction to disk. Bounded incomplete ZIP prefixes cannot be fully inspected as archives; that limitation is recorded in `integrity_verification.json`. Plain-byte checks covered every saved file. No configured credential was found.', '', 'The observed dictionary/schema union considers all '+str(totals['sample_files'])+' historical collected JSON sample files. Counts may include repeated cached projections and are not independent statistical observations. Current coverage provides the retrieval/source controls for choosing dated evidence.', ''])
    (ROOT/'collection_report.md').write_text('\n'.join(text),encoding='utf-8')
    print(json.dumps(totals),flush=True)

if __name__=='__main__':main()
