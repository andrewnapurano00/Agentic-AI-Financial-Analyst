"""Offline checks; synthetic fixtures are tests, never collected market samples."""
import unittest, tempfile, json
from pathlib import Path
from unittest.mock import patch
from argparse import Namespace
import reference as ref

class Response:
    status_code=200
    ok=True
    headers={'Content-Type':'application/json'}
    def __init__(self,payload):self.payload=payload
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def iter_content(self,size):yield self.payload

class CollectionTests(unittest.TestCase):
    def test_sampling_preserves_zero_null_identifiers_nesting(self):
        value=[{'cik':'0000320193','price':0,'optional':None,'nested':[{'a':1},{'a':2}]}]*8
        result=ref.bounded_sample(value,5)
        self.assertEqual(len(result),5)
        self.assertEqual(result[0]['cik'],'0000320193')
        self.assertEqual(result[0]['price'],0)
        self.assertIsNone(result[0]['optional'])
        self.assertEqual(result[0]['nested'],value[0]['nested'])
        self.assertEqual(len(value),8)
    def test_outside_write_rejected(self):
        with self.assertRaises(ValueError):ref.safe_path(ref.ROOT.parent/'not-permitted.tmp')
    def test_http_200_errors_and_reflected_credentials(self):
        with tempfile.TemporaryDirectory(dir=ref.ROOT,prefix='offline-test-') as td, patch.object(ref,'ROOT',Path(td)), patch.object(ref,'key',return_value='synthetic-test-key'), patch.object(ref.time,'sleep'):
            args=Namespace(max_bytes=2048,refresh=False,retries=0,interval=.75,timeout=10)
            c=ref.Collector(args)
            with patch.object(c.session,'get',return_value=Response(b'{"Error Message":"Premium Query Parameter"}')):
                meta,body=c.request(ref.BASE+'profile',{'symbol':'AAPL'},'test-error')
                self.assertEqual(meta['status'],'restricted')
                self.assertEqual(meta['http_status'],200)
            with patch.object(c.session,'get',return_value=Response(b'{"error":"synthetic-test-key"}')):
                meta,body=c.request(ref.BASE+'profile',{'symbol':'JNJ'},'test-reflected')
                self.assertEqual(meta['status'],'credential_reflection_quarantined')
                self.assertEqual(body,b'')
                self.assertEqual(meta['raw_file'],'')
                for p in Path(td).rglob('*'):
                    if p.is_file():self.assertNotIn(b'synthetic-test-key',p.read_bytes())
    def test_transient_retry_is_bounded_and_cached(self):
        with tempfile.TemporaryDirectory(dir=ref.ROOT,prefix='offline-test-') as td, patch.object(ref,'ROOT',Path(td)),patch.object(ref,'key',return_value='synthetic-test-key'),patch.object(ref.time,'sleep'):
            args=Namespace(max_bytes=2048,refresh=False,retries=1,interval=.75,timeout=10)
            c=ref.Collector(args);failed=Response(b'{}');failed.status_code=503;failed.ok=False
            with patch.object(c.session,'get',side_effect=[failed,Response(b'[{"symbol":"AAPL","value":0}]')]) as get:
                meta,body=c.request(ref.BASE+'profile',{'symbol':'AAPL'},'test-retry')
                self.assertEqual(get.call_count,2)
                self.assertEqual(meta['status'],'success')
                cached,again=c.request(ref.BASE+'profile',{'symbol':'AAPL'},'test-retry')
                self.assertTrue(cached['cache_reused']);self.assertEqual(again,body)
                self.assertEqual(get.call_count,2)

if __name__=='__main__':unittest.main()
