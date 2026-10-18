import concurrent.futures
import threading
import time
from orglens.discovery import MultiSearchDiscovery


class Transport:
    requests=0
    limit=100
    deadline=time.monotonic()+120
    def reserve(self,url):self.requests+=1


class Provider:
    endpoint='https://example.test/search'
    disabled=False
    label='test'
    def __init__(self):self.count=0;self.lock=threading.Lock()
    def search(self,q,timeout):
        with self.lock:self.count+=1
        time.sleep(.01)
        return ['https://example.no/']


def test_concurrent_search_reserves_cost_before_call():
    provider=Provider()
    search=MultiSearchDiscovery([provider],unit_cost=1,max_cost=1)
    t=Transport()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(lambda _:search.discover({'navn':'Example AS'},t),range(8)))
    assert provider.count==1
    assert sum(bool(x) for x in results)==1
    assert search.calls==1 and float(search.spent)==1


def test_query_cap_is_shared_by_all_companies():
    provider=Provider()
    search=MultiSearchDiscovery([provider],max_queries=2)
    for _ in range(5):search.discover({'navn':'Example AS'},Transport())
    assert search.calls==2
    assert provider.count==2
