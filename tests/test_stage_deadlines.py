import json
import threading
from decimal import Decimal

import orglens.core as core


def test_expired_search_stage_does_not_consume_time_reserved_for_records(tmp_path,monkeypatch):
    class Clock:
        now=100.0
        def monotonic(self):return self.now
    clock=Clock()
    monkeypatch.setattr(core.time,'monotonic',clock.monotonic)
    def get(self,url,source_class='official_registry',headers=None):
        if clock.now>=self.deadline:
            return {'source_url':url,'status':0,'budget_exhausted':True,'error':'time budget'}
        if '/regnskap/' in url:body=[]
        elif url.endswith('/roller'):body={'rollegrupper':[]}
        elif '/underenheter?' in url:body={'_embedded':{'underenheter':[]}}
        else:body={'organisasjonsnummer':'123456789','navn':'Example AS'}
        raw=json.dumps(body).encode();sha=core.digest(raw)
        (self.root/(sha+'.bin')).write_bytes(raw)
        self.requests+=1
        return {'id':core.digest(url),'source_url':url,'source_class':source_class,'status':200,'text':raw.decode(),
                'retrieved_at':'2026-10-19T00:00:00Z','content_sha256':sha,'snapshot_path':'snapshots/'+sha+'.bin'}
    monkeypatch.setattr(core.Transport,'get',get)
    monkeypatch.setattr(core,'research_website',lambda *a,**k:False)
    class Search:
        local=threading.local();unit_cost=Decimal(0);max_cost=Decimal(0);spent=Decimal(0);calls=0;provider_name='test'
        def discover(self,body,transport):
            clock.now=transport.deadline+.01
            return []
    rows,report=core.run_batch(['123456789'],tmp_path,run_id='test',seconds=900,requests=100,
                              strategy='balanced',workers=1,modules=('website','financials','leadership','locations'),discovery=Search())
    assert report['validation']['passed']
    assert all(rows[0]['availability'][field] in {'available','not_available'} for field in ['financials','leadership','locations']), (rows[0]['availability'],rows[0]['errors'],report['stages'])
    assert all(any(s['status']==200 and fragment in s['source_url'] for s in rows[0]['source_snapshots'])
               for fragment in ['/regnskap/','/roller','/underenheter?'])
    assert report['runtime_seconds']<900
