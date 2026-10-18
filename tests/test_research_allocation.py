import json
import time

import orglens.core as core


def test_external_first_does_not_spend_entire_budget_before_sites(tmp_path, monkeypatch):
    visited=[]
    def get(self,url,source_class='official_registry',headers=None):
        try:self.reserve(url)
        except core.BudgetExceeded:return {'source_url':url,'status':0,'budget_exhausted':True,'error':'budget'}
        visited.append(url)
        org=url.split('/')[-1]
        if org.isdigit():
            return {'id':org,'source_url':url,'status':200,'source_class':source_class,'text':json.dumps({'organisasjonsnummer':org,'navn':'Example '+org+' AS','hjemmeside':'https://company'+org+'.no/'}),'retrieved_at':'2026-10-18T00:00:00Z','content_sha256':'0'*64}
        return {'source_url':url,'status':404,'error':'missing'}
    monkeypatch.setattr(core.Transport,'get',get)
    monkeypatch.setattr(core.Transport,'reserve',lambda self,url: reserve(self))
    def reserve(transport):
        if transport.requests>=transport.limit:raise core.BudgetExceeded()
        transport.requests+=1
    def website(row,body,transport,*a,**k):
        transport.get(body['hjemmeside'],'company_owned')
        row.setdefault('website_research',{})['tried']=True
    monkeypatch.setattr(core,'research_website',website)
    monkeypatch.setattr(core,'validate',lambda *a,**k:{'passed':True,'errors':[]})
    monkeypatch.setattr(core,'official',lambda row,t,module:t.get('https://records.no/'+module))
    orgs=[str(100000000+i) for i in range(10)]
    rows,report=core.run_batch(orgs,tmp_path,run_id='test',requests=20,seconds=60,workers=1,strategy='balanced')
    assert len(rows)==10
    assert sum('website_research' in r for r in rows)==10
    assert any('company100000000' in url for url in visited)
    assert report['requests']<=20


def test_unknown_strategy_is_rejected_before_fetching(tmp_path):
    import pytest
    with pytest.raises(ValueError,match='strategy'):
        core.run_batch(['123456789'],tmp_path,run_id='test',strategy='magic')
