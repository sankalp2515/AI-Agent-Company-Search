from concurrent.futures import ThreadPoolExecutor
from orglens.core import Transport


def test_same_run_company_observation_is_single_flight(tmp_path, monkeypatch):
    import time
    calls=[]
    def fetch(self,url,source_class,headers):
        calls.append(url)
        time.sleep(.02)
        return {'source_url':url,'status':200,'retrieved_at':'2026-10-18T00:00:00Z'}
    monkeypatch.setattr(Transport,'_get',fetch,raising=False)
    t=Transport(tmp_path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        observations=list(pool.map(lambda _:t.get('https://example.test/','company_owned'),range(8)))
    assert len(calls)==1
    assert t.site_cache_hits==7
    assert {s['retrieved_at'] for s in observations}=={'2026-10-18T00:00:00Z'}
    # A refresh uses a new transport and performs a new fetch.
    Transport(tmp_path).get('https://example.test/','company_owned')
    assert len(calls)==2


def test_temporary_stage_budget_failure_is_not_cached(tmp_path,monkeypatch):
    calls=[]
    def fetch(self,url,source_class,headers):
        calls.append(url)
        return {'source_url':url,'status':0,'budget_exhausted':True} if len(calls)==1 else {'source_url':url,'status':200}
    monkeypatch.setattr(Transport,'_get',fetch,raising=False)
    t=Transport(tmp_path)
    assert t.get('https://example.test/','company_owned')['status']==0
    assert t.get('https://example.test/','company_owned')['status']==200
    assert len(calls)==2
