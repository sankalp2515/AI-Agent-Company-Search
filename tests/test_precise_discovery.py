import io
import json
import time

from orglens.discovery import MultiSearchDiscovery,TavilyProvider,candidate_roots


def test_precise_discovery_keeps_legal_phrase_and_removes_directory_noise():
    class Provider:
        endpoint='https://example.test/search'
        disabled=False
        def search(self,query,timeout):
            assert '"AV & PÅ ELEKTRO AS"' in query
            assert '-site:proff.no' in query
            return ['https://avogpaa.no/']
    class Transport:
        requests=0
        limit=5
        deadline=time.monotonic()+30
        def reserve(self,url):self.requests+=1
    search=MultiSearchDiscovery([Provider()],max_queries=1,query_policy='precise')
    t=Transport()
    assert search.discover({'navn':'AV & PÅ ELEKTRO AS','forretningsadresse':{'kommune':'RINGERIKE'}},t)==['https://avogpaa.no/']
    assert search.discover({'navn':'Second AS'},t)==[]
    assert search.calls==1


def test_precise_tavily_search_expands_hints_without_model_answers(monkeypatch):
    import orglens.discovery as d
    def open_request(request,timeout,ctx):
        body=json.loads(request.data)
        assert body['max_results']==10
        assert body['country']=='norway'
        assert body['search_depth']=='basic'
        assert body['include_answer'] is False
        assert 'rocketreach.co' in body['exclude_domains']
        return io.BytesIO(json.dumps({'results':[{'url':'https://rocketreach.co/profile/company'},*[{'url':f'https://company{i}.no/'} for i in range(8)]]}).encode())
    monkeypatch.setattr(d,'_open',open_request)
    found=TavilyProvider('test-key',query_policy='precise').search('"Company AS"',5)
    assert found==[f'https://company{i}.no/' for i in range(6)]


def test_sales_directories_are_not_website_candidates():
    assert candidate_roots(['https://rocketreach.co/company','https://leadiq.com/company','https://tracxn.com/company','https://company.no/'])==['https://company.no/']
