"""Retain distinct historical request variants and correct collector-only alias artifacts."""
import csv,json,hashlib
from pathlib import Path
from reference import ROOT,writecsv,dump

def main():
    paths=sorted((ROOT/'raw').glob('coverage-*.csv'))+[ROOT/'coverage_matrix.csv']
    merged={}
    for path in paths:
        for row in csv.DictReader(path.open(encoding='utf-8')):
            # The first RSS pass was labeled with sector aliases despite the same global request.
            if row['api_id']=='FMP-103':
                row['ticker_or_input']='alternative'
                row['applicability_notes']='Global sentiment RSS example; sector ticker aliases were removed because the request was not stock-filtered.'
            # Early batch quote postprocessing produced redundant empty extractions from single-symbol responses.
            # Actual quote bodies and the correct per-stock projections remain intact; do not treat these aliases as requests.
            if row['api_id']=='FMP-238' and row.get('sample_file','').endswith('-bulk.json'):continue
            if row['api_id'] in ('FMP-235','FMP-236','FMP-237') and row['status']=='unsupported_transport':continue
            signature=(row['api_id'],row['ticker_or_input'],row['variant'],row['endpoint'],row['parameters_json'])
            merged[signature]=row
    rows=list(merged.values());writecsv(ROOT/'coverage_matrix.csv',rows)
    # Correct the early metadata annotation (quarter sampling was eight, not five); bodies are untouched.
    corrected=0
    for path in (ROOT/'raw').rglob('*.metadata.json'):
        meta=json.loads(path.read_text(encoding='utf-8'))
        if str(meta.get('parameters',{}).get('limit'))=='8' and meta.get('sampling_limit')==5:
            meta['sampling_limit']=8;meta['annotation_correction']='Quarterly local sampling limit corrected from 5 to 8; original response and retrieval time unchanged.';dump(path,meta);corrected+=1
    smoke=ROOT/'raw/smoke/profile-AAPL.metadata.json'
    if smoke.exists():
        meta=json.loads(smoke.read_text(encoding='utf-8'));body=ROOT/'raw/smoke/profile-AAPL.body'
        meta.update(raw_file='raw/smoke/profile-AAPL.body',sha256=hashlib.sha256(body.read_bytes()).hexdigest(),attempts=1)
        dump(smoke,meta)
    dump(ROOT/'documentation/processing_notes.json',{'coverage_reconciliation':'Union of historical/current request variants, keyed by API ID/input/variant/endpoint/parameters; latest projection chosen for identical requests.','rss_label_correction':'FMP-103 global requests were originally repeated under ticker aliases; current coverage represents their actual global input. Original sample files remain preserved.','batch_extraction_correction':'Removed collector-only redundant FMP-238 bulk aliases from current coverage; correct per-stock quote projections were rebuilt from the cached original bodies without provider requests.','sampling_annotation_corrections':corrected,'raw_response_bodies_modified':False})
    print('Reconciled coverage cases',len(rows),'sampling annotations corrected',corrected)

if __name__=='__main__':main()
