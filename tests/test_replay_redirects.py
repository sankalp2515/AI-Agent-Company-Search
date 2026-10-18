import json

from orglens.core import digest
from orglens.replay import ReplayTransport


def test_replay_recognizes_observed_redirect_destination_without_refreshing(tmp_path):
    source=tmp_path/'source'
    (source/'snapshots').mkdir(parents=True)
    raw=b'<main>Example AS</main>'
    sha=digest(raw)
    snap={'source_url':'https://www.example.no/', 'requested_url':'https://example.no/',
          'status':200,'retrieved_at':'2026-10-17T10:00:00Z','content_sha256':sha}
    (source/'snapshots'/(sha+'.bin')).write_bytes(raw)
    (source/'envelopes.jsonl').write_text(json.dumps({'source_snapshots':[snap]})+'\n',encoding='utf8')
    transport=ReplayTransport(tmp_path/'target',source,10,30)
    observed=transport.get('https://www.example.no/')
    assert observed['status']==200
    assert observed['text']=='<main>Example AS</main>'
    assert observed['retrieved_at']=='2026-10-17T10:00:00Z'
    assert observed['replayed'] is True
    assert transport.get('https://unknown.example.no/')['status']==0
