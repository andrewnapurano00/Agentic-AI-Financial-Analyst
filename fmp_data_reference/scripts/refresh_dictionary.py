"""Build searchable observed dictionaries from actual samples, never provider contracts."""
import csv, json, re
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timezone
from reference import ROOT, DOC, SECTORS, dump, safe_path, writecsv

DEFINITIONS={
'symbol':('Trading/security symbol supplied by FMP.','identifier'),
'cik':('SEC Central Index Key identifying a registered filer; preserve string/leading zeros.','identifier'),
'cusip':('CUSIP security identifier; preserve the returned string and leading zeros.','identifier'),
'isin':('International Securities Identification Number; preserve the returned string.','identifier'),
'currency':('Currency label returned by this endpoint; do not assume every monetary field shares it.','currency_code'),
'reportedCurrency':('Currency label associated with this financial report.','currency_code'),
'companyName':('Company name returned by FMP.','text'),
'sector':('FMP sector classification label at retrieval time.','text'),
'industry':('FMP industry classification label at retrieval time.','text'),
'date':('Endpoint-specific observation or financial period date; not interchangeable with retrieval/filing date.','date'),
'fillingDate':('Provider filing-date field (spelling preserved); separate from period date.','date'),
'filingDate':('Filing-date field; separate from financial period date.','date'),
'acceptedDate':('Reported filing acceptance date/time; timezone is not inferred if absent.','datetime'),
'publishedDate':('Publication date/time of the record; timezone is unknown unless explicit.','datetime'),
'timestamp':('Provider timestamp; epoch unit/timezone must be verified rather than assumed.','unknown'),
'period':('Provider fiscal-period label; inspect FY/Q1/Q2/Q3/Q4 before comparing.','fiscal_period'),
'fiscalYear':('Provider fiscal-year label, not necessarily calendar year.','year'),
'calendarYear':('Provider calendar-year label; does not establish fiscal-year alignment.','year'),
'revenue':('Revenue reported for the period identified in this record.','monetary'),
'netIncome':('Net income reported for the record’s period.','monetary'),
'grossProfit':('Gross profit reported for the record’s period.','monetary'),
'operatingIncome':('Operating income reported for the record’s period.','monetary'),
'operatingExpenses':('Operating expenses reported for the record’s period.','monetary'),
'incomeBeforeTax':('Income before tax reported for the record’s period.','monetary'),
'incomeTaxExpense':('Income-tax expense reported for the record’s period.','monetary'),
'researchAndDevelopmentExpenses':('Research and development expenses for the record’s period.','monetary'),
'sellingGeneralAndAdministrativeExpenses':('Selling, general and administrative expenses for the period.','monetary'),
'costOfRevenue':('Reported cost of revenue for the period.','monetary'),
'totalAssets':('Total assets at the reported balance-sheet date.','monetary'),
'totalLiabilities':('Total liabilities at the reported balance-sheet date.','monetary'),
'totalStockholdersEquity':('Reported stockholders’ equity at the balance-sheet date.','monetary'),
'totalEquity':('Reported total equity at the balance-sheet date.','monetary'),
'cashAndCashEquivalents':('Cash and cash equivalents at the balance-sheet date.','monetary'),
'totalDebt':('Provider-reported total debt; debt components must be checked before comparison.','monetary'),
'netDebt':('Provider-reported net debt; exact calculation should be checked separately.','monetary'),
'operatingCashFlow':('Reported operating cash flow for the fiscal period.','monetary'),
'netCashProvidedByOperatingActivities':('Net cash provided by operating activities for the period.','monetary'),
'capitalExpenditure':('Reported capital expenditure; preserve its sign convention.','monetary'),
'freeCashFlow':('Provider-reported free cash flow; exact formula is not established by these samples.','monetary'),
'dividendsPaid':('Reported dividends paid; preserve sign convention and period.','monetary'),
'eps':('Reported earnings per share for the record’s period; basic/diluted basis depends on endpoint.','currency_per_share'),
'epsDiluted':('Reported diluted earnings per share.','currency_per_share'),
'weightedAverageShsOut':('Reported weighted-average shares outstanding for the period.','shares'),
'weightedAverageShsOutDil':('Reported diluted weighted-average shares outstanding.','shares'),
'sharesOutstanding':('Reported shares outstanding as of the record’s observation.','shares'),
'floatShares':('Provider-reported float shares; float methodology is not established here.','shares'),
'price':('Provider price observation; currency/as-of time must be read from record or matching profile.','currency_per_share'),
'open':('Opening price for the specified trading interval.','currency_per_share'),
'high':('Highest reported price in the trading interval.','currency_per_share'),
'low':('Lowest reported price in the trading interval.','currency_per_share'),
'close':('Closing price for the trading interval; adjustment basis must be checked for this endpoint.','currency_per_share'),
'adjClose':('Provider adjusted-close field; adjustment methodology is not established by its name alone.','currency_per_share'),
'vwap':('Volume-weighted average price as supplied by FMP.','currency_per_share'),
'volume':('Provider trading-volume field; shares versus contracts depends on instrument/endpoint.','unknown'),
'marketCap':('Provider market capitalization at its observation time.','monetary'),
'marketCapitalization':('Provider market capitalization at the record’s date.','monetary'),
'enterpriseValue':('Provider enterprise value; exact components/calculation require separate verification.','monetary'),
'url':('Provider source or article URL; validate before use in an application.','url'),
'link':('Provider source link; query credentials are not retained in this reference.','url'),
'finalLink':('Provider final filing/source link.','url'),
'image':('Provider company image/logo URL.','url'),
'title':('Provider title for the article, note, or other record.','text'),
'text':('Provider text content; not AI interpretation.','text'),
'content':('Provider content field; preserve original nesting and text.','text'),
'exchange':('Provider exchange label/code.','identifier'),
'exchangeShortName':('Provider short exchange label/code.','identifier'),
'name':('Endpoint-specific name label; entity type depends on endpoint.','text'),
'year':('Endpoint-specific year label; check fiscal/calendar meaning.','year'),
'quarter':('Reported quarter label; distinguish fiscal and calendar context.','fiscal_period'),
}

def typename(v):
    return 'null' if v is None else 'boolean' if isinstance(v,bool) else 'integer' if isinstance(v,int) else 'number' if isinstance(v,float) else 'string' if isinstance(v,str) else 'array' if isinstance(v,list) else 'object' if isinstance(v,dict) else 'unknown'
def describe(field,path):
    if field in DEFINITIONS:
        definition,unit=DEFINITIONS[field];return definition,unit,'inferred'
    if field.startswith('growth') or field.endswith('Growth'):
        return 'Provider growth measure named '+field+'; base period, formula and ratio/percent scale need verification.','unknown','inferred'
    if field.endswith('Ratio') or field.endswith('Margin') or field.endswith('Yield'):
        return 'Provider ratio/margin/yield named '+field+'; exact inputs and percentage scaling are not established.','unknown','inferred'
    return 'Exact provider definition for '+field+' is not established; consult the official endpoint and formula documentation.','unknown','unknown'

def main():
    inventory=list(csv.DictReader((ROOT/'endpoint_inventory.csv').open(encoding='utf-8')))
    byid={r['api_id']:r for r in inventory}
    coverage=list(csv.DictReader((ROOT/'coverage_matrix.csv').open(encoding='utf-8')))
    seen=set();stats=defaultdict(lambda:defaultdict(lambda:{'types':set(),'examples':[],'present':0,'nulls':0,'samples':set(),'tickers':set(),'sector':defaultdict(Counter),'parent':''}))
    object_counts=defaultdict(Counter);sector_objects=defaultdict(lambda:defaultdict(Counter));currencies=defaultdict(set)
    def walk(api,v,path,ticker,sample,parent=''):
        e=stats[api][path];e['types'].add(typename(v));e['present']+=1;e['nulls']+=v is None;e['samples'].add(sample);e['tickers'].add(ticker);e['sector'][ticker][typename(v)]+=1;e['parent']=parent
        if not isinstance(v,(dict,list)):
            display=json.dumps(v,ensure_ascii=False)
            if len(display)<=180 and display not in [json.dumps(x,ensure_ascii=False) for x in e['examples']] and len(e['examples'])<4:e['examples'].append(v)
        if isinstance(v,dict):
            object_counts[api][path]+=1;sector_objects[api][ticker][path]+=1
            for k,x in v.items():
                if k in ['currency','reportedCurrency'] and isinstance(x,str):currencies[api].add(x)
                walk(api,x,path+'.'+k,ticker,sample,path)
        elif isinstance(v,list):
            for x in v:walk(api,x,path+'[]',ticker,sample,path)
    for row in coverage:
        sample=row.get('sample_file','')
        if not sample or sample in seen:continue
        seen.add(sample)
        p=ROOT/sample
        if p.exists():walk(row['api_id'],json.loads(p.read_text(encoding='utf-8')),'$',row['ticker_or_input'],sample)
    # Include every historical collected JSON sample as well as current coverage projections.
    # Counts describe observations in saved sample files, not independent securities/requests.
    for p in sorted((ROOT/'samples').rglob('*.json')):
        sample=str(p.relative_to(ROOT)).replace('\\','/')
        if sample in seen:continue
        api=p.relative_to(ROOT/'samples').parts[0]
        if api not in byid:continue
        candidate=p.stem.split('-')[0]
        ticker=candidate if candidate in SECTORS and api!='FMP-103' else 'alternative'
        seen.add(sample);walk(api,json.loads(p.read_text(encoding='utf-8')),'$',ticker,sample)
    entries=[]
    for api in sorted(stats):
        for path,e in sorted(stats[api].items()):
            field=path.rsplit('.',1)[-1];definition,units,basis=describe(field,path)
            parent=e['parent'];missing=max(0,object_counts[api][parent]-e['present']) if parent and not path.endswith('[]') else 0
            differences={}
            for ticker in set(e['sector']) | set(sector_objects[api]):
                counts=e['sector'].get(ticker,Counter())
                if ticker=='alternative':continue
                differences[ticker]={'types':sorted(counts),'null_observations':counts['null'],'present_observations':sum(counts.values()),'missing_in_observed_parent_objects':max(0,sector_objects[api][ticker][parent]-sum(counts.values())) if parent and not path.endswith('[]') else 0}
            join='Inferred candidate join: symbol + relevant date/period/currency; verify unique cardinality before joins.' if field=='symbol' else 'Inferred identifier join candidate; preserve string/leading zeros and verify entity/security identity.' if field.lower() in ['cik','cusip','isin'] else ''
            note='Observed samples only; presence/non-nullability is not a universal contract. All historical JSON samples included; counts may include repeated cached projections, not independent records. Arrays locally bounded; raw bodies are separate. Examples over 180 characters omitted. Consult endpoint/variant before mixing legacy/current shapes.'
            if 'ttm' in byid[api]['verified_endpoint']:note+=' TTM basis; do not compare directly with annual/quarterly measures.'
            if 'statement' in byid[api]['verified_endpoint']:note+=' Read each record period/fiscalYear/date and reportedCurrency; filing dates are distinct.'
            if 'historical-price' in byid[api]['verified_endpoint']:note+=' Price adjustment basis is not inferred; this route is not assumed to be dividend-adjusted total return.'
            entries.append({'api_id':api,'category':byid[api]['category'],'endpoint_name':byid[api]['endpoint_name'],'original_endpoint':byid[api]['original_endpoint'],'verified_endpoint':byid[api]['verified_endpoint'],'field_name':field,'field_path':path,'definition':definition,'definition_status':basis,'observed_json_types':json.dumps(sorted(e['types'])),'example_values_json':json.dumps(e['examples'],ensure_ascii=False),'observed_currency_labels':json.dumps(sorted(currencies[api])),'currency_basis':'Returned currency/reportedCurrency labels aggregated across sampled records; not assigned universally to all fields.','units':units,'units_status':'inferred' if units!='unknown' else 'unknown','scaling':'Original provider values; no thousands/millions rescaling or numeric coercion. Exact scale unverified unless stated.','date_period_meaning':definition if units in ['date','datetime','year','fiscal_period'] else 'Interpret with record date/period and request variant; retrieval time is metadata.','observed_count':e['present'],'null_count':e['nulls'],'missing_in_observed_parent_objects':missing,'sector_differences_json':json.dumps(differences,sort_keys=True),'join_relationships':join,'interpretation_notes':note,'official_documentation':byid[api]['official_documentation'] or 'No current mapping verified; original workbook reference retained.','sample_files_json':json.dumps(sorted(e['samples'])),'schema_basis':'observed_actual_samples'})
    # Workbook-only paths remain discoverable without pretending they were collected or documented.
    tabs=json.loads((ROOT/'documentation/workbook_tabs.json').read_text(encoding='utf-8'))
    for r in tabs.get('Response Fields',[]):
        api=r['API ID'];path=r.get('Field Path','')
        if not any(e['api_id']==api and (e['field_path']==path or e['field_path'].endswith('.'+str(path))) for e in entries):
            item=byid[api];entries.append({'api_id':api,'category':item['category'],'endpoint_name':item['endpoint_name'],'original_endpoint':item['original_endpoint'],'verified_endpoint':item['verified_endpoint'],'field_name':str(path).rsplit('.',1)[-1],'field_path':path,'definition':'Workbook-supplied field path; live definition not established.','definition_status':'unknown','observed_json_types':'[]','example_values_json':'[]','observed_currency_labels':'[]','currency_basis':'unknown','units':'unknown','units_status':'unknown','scaling':'unknown','date_period_meaning':'unknown','observed_count':0,'null_count':0,'missing_in_observed_parent_objects':'unknown','sector_differences_json':'{}','join_relationships':'','interpretation_notes':'Workbook-only inferred field; not seen in collected live samples. Workbook supplied examples remain separately preserved.','official_documentation':item['official_documentation'],'sample_files_json':'[]','schema_basis':'workbook_only_not_live_observed'})
    writecsv(ROOT/'data_dictionary.csv',entries)
    md=['# FMP observed data dictionary','','Search the CSV for precise paths, currencies, null/missing counts, sector differences and all sample links. Definitions labeled inferred are cautious interpretations, not official field contracts. Unknown fields remain unknown.','']
    for item in inventory:
        api=item['api_id'];rows=[e for e in entries if e['api_id']==api]
        md.extend(['<a id="'+api.lower()+'"></a>','', '## '+api+' — '+item['category']+' / '+item['endpoint_name'],'', 'Original: `'+item['original_endpoint']+'`','', 'Verified route: `'+(item['verified_endpoint'] or 'unverified')+'`','', '[Official catalogue]('+DOC+')','', '| Path | Observed types | Definition | Basis |','| --- | --- | --- | --- |'])
        for e in rows:md.append('| `'+str(e['field_path']).replace('|','\\|')+'` | '+str(e['observed_json_types'])+' | '+e['definition'].replace('|','\\|')+' | '+e['definition_status']+' |')
        if not rows:md.append('| — | No observed fields | No successful parseable response collected. See coverage matrix. | unknown |')
        md.append('')
        fields={path:{'observed_types':sorted(v['types']),'null_observations':v['nulls'],'present_observations':v['present'],'observed_missing_in_parent':max(0,object_counts[api][v['parent']]-v['present']) if v['parent'] and not path.endswith('[]') else 0} for path,v in stats[api].items()}
        dump(ROOT/'schemas'/(api+'.json'),{'api_id':api,'basis':'observed_response_shapes_not_json_schema_contract','generated_at_utc':datetime.now(timezone.utc).isoformat(),'sample_files':sorted({s for v in stats[api].values() for s in v['samples']}),'required_fields_asserted':False,'fields':fields,'limitation':'Observed path/type union, including nulls and missing observations. No assertion of universal requiredness, completeness or non-nullability. Workbook inferred schemas are separate.'})
        schema_path=ROOT/'schemas'/(api+'.json')
        schema=json.loads(schema_path.read_text(encoding='utf-8'))
        schema['observed_non_json_formats']=sorted({r['format'] for r in coverage if r['api_id']==api and r.get('binary_sample_file')})
        schema['binary_sample_files']=sorted({r['binary_sample_file'] for r in coverage if r['api_id']==api and r.get('binary_sample_file')})
        dump(schema_path,schema)
    safe_path(ROOT/'data_dictionary.md').write_text('\n'.join(md),encoding='utf-8')
    totals={'api_references':len(inventory),'coverage_cases':len(coverage),'case_statuses':dict(Counter(r['status'] for r in coverage)),'apis_with_actual_samples':len({r['api_id'] for r in coverage if r.get('sample_file') and int(r.get('record_count') or 0)>0}),'sample_files':len(seen),'dictionary_entries':len(entries),'observed_dictionary_entries':sum(e['schema_basis']=='observed_actual_samples' for e in entries),'workbook_only_entries':sum(e['schema_basis']!='observed_actual_samples' for e in entries)}
    dump(ROOT/'collection_totals.json',totals)
    print(json.dumps(totals),flush=True)

if __name__=='__main__':main()
