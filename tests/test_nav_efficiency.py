import concurrent.futures
import threading
import time

from orglens.core import claim, envelope
from orglens.navjobs import BASE, NavJobs
from test_nav_coverage import Transport, ad, entry, loaded


def test_shared_candidate_detail_fetched_once_per_run(monkeypatch):
    nav = loaded([entry('shared', 'Example')], monkeypatch)
    transport = Transport({BASE + '/api/v1/feedentry/shared': (200, ad('123456789'))})
    first, other = envelope('123456789', 'a'), envelope('987654321', 'b')
    nav.research(first, {'navn': 'Example AS'}, transport, claim)
    nav.research(other, {'navn': 'Example AS'}, transport, claim)
    assert transport.urls.count(BASE + '/api/v1/feedentry/shared') == 1
    assert nav.details == 1
    assert any(c['field'] == 'jobs' for c in first['claims'])
    assert not any(c['field'] == 'jobs' for c in other['claims'])


def test_same_candidate_concurrently_fetched_once(monkeypatch):
    nav = loaded([entry('shared', 'Example')], monkeypatch)
    class Slow(Transport):
        def get(self, *args, **kwargs):
            time.sleep(.01)
            return super().get(*args, **kwargs)
    transport = Slow({BASE + '/api/v1/feedentry/shared': (200, ad('123456789'))})
    rows = [envelope('123456789', str(i)) for i in range(8)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda r: nav.research(r, {'navn': 'Example AS'}, transport, claim), rows))
    assert transport.urls.count(BASE + '/api/v1/feedentry/shared') == 1
    assert all(any(c['field'] == 'jobs' for c in row['claims']) for row in rows)


def test_candidate_detail_cap_preserves_unknown_for_unchecked_ads(monkeypatch):
    nav = loaded([entry(str(i), 'Example') for i in range(12)], monkeypatch)
    row = envelope('123456789', 'a')
    transport = Transport({BASE + '/api/v1/feedentry/' + str(i): (200, ad('987654321')) for i in range(12)})
    nav.research(row, {'navn': 'Example AS'}, transport, claim)
    assert nav.details <= 4
    assert row['research_sources']['nav_jobs']['state'] == 'partial'
    assert row['availability']['jobs'] == 'failed'
