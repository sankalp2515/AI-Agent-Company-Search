import copy
import io
import json
from datetime import date
from email.message import Message

import pytest

from orglens.awards import API, extract, research
from orglens.core import Transport, claim, digest, envelope, finish, json_request_bytes, run_batch
from orglens.replay import ReplayTransport

ORG = '915313760'


def award(org=ORG, identifier='1000252454'):
    return {'stoettetiltaksnummer': identifier, 'status': 'stoettetiltaksstatus.registrert',
            'tildelingsdato': '2026-05-26', 'mottattDato': '2026-08-27',
            'tildeltBeloep': {'beloep': '70000.00', 'valuta': 'NOK'},
            'stoetteinstrument': 'stoetteinstrumenttype.tilskudd',
            'rolle': [{'type': 'rolletype.stoettemottaker', 'rolleinnehavertype': 'virksomhet',
                       'rolleinnehaverVirksomhet': {'organisasjonsnummer': org}}]}


def parse(*items):
    return extract({'stoettetildeling': list(items)}, ORG, as_of=date(2026, 11, 6))


def snapshot(body, org=ORG, status=200, stamp='2026-11-06T00:00:00Z'):
    raw = json.dumps(body).encode()
    request = [{'field': 'STOETTEMOTTAKER_ORGNR', 'value': org, 'matchType': 'EXACT_MATCH'}]
    request_hash = digest(json_request_bytes(request))
    return {'id': digest({'raw': digest(raw), 'request': request_hash, 'stamp': stamp})[:24], 'source_url': API,
            'source_class': 'official_public_api', 'status': status, 'retrieved_at': stamp,
            'content_sha256': digest(raw), 'request_method': 'POST', 'request_body_sha256': request_hash,
            'request_body': json_request_bytes(request).decode(), 'text': raw.decode()}


def result(items, previous=None, org=ORG, **kwargs):
    row = envelope(org, 'test')
    row['legal_identity'] = {'legal_name': 'Example AS'}
    snap = snapshot({'stoettetildeling': items}, org=org, **kwargs)
    class Fake:
        def post(self, url, payload):
            assert url == API and payload[0]['value'] == org
            return snap
    research(row, Fake(), claim)
    return finish(row, previous)


def test_recipient_not_donor_or_name_decides_identity():
    wrong = award('999999999')
    wrong['rolle'].append({'type': 'rolletype.stoettegiver', 'rolleinnehavertype': 'virksomhet',
                          'rolleinnehaverVirksomhet': {'organisasjonsnummer': ORG}})
    assert parse(wrong)[1] == {'recipient_mismatch': 1}
    assert result([wrong])['availability']['public_awards'] == 'ambiguous'


def test_award_and_registration_dates_are_distinct_and_refresh_stable():
    old = result([award()])
    changed_registration = award()
    changed_registration['mottattDato'] = '2026-09-01'
    fresh = result([changed_registration], old, stamp='2026-11-06T02:00:00Z')
    assert fresh['changes'] == []
    value = fresh['claims'][0]['value']
    assert value['award_date'] == '2026-05-26'
    assert fresh['evidence'][0]['locator']['registration_date'] == '2026-09-01'
    assert fresh['summary']['statements'][0]['evidence_ids']
    assert 'not evidence of cash receipt or revenue' in fresh['summary']['text']
    assert not fresh['external_footprint']['news']
    assert len(fresh['external_footprint']['public_awards']) == 1


def test_duplicate_ids_deduplicate_and_conflicts_never_reappear():
    assert len(parse(award(), award())[0]) == 1
    conflict = award()
    conflict['tildeltBeloep']['beloep'] = '80000'
    facts, rejected = parse(award(), conflict, award())
    assert not facts and rejected == {'duplicate_id_conflict': 1}


def test_missing_and_interval_amounts_never_become_zero():
    item = award()
    item.pop('tildeltBeloep')
    item['beloepsintervall'] = {'fraBeloep': 100000, 'tilBeloep': 500000}
    value = parse(item)[0][0]['value']
    assert value['amount'] is None and value['amount_interval'] == item['beloepsintervall']
    item['tildeltBeloep'] = {'beloep': '0', 'valuta': 'NOK'}
    assert parse(item)[0][0]['value']['amount']['amount'] == '0'


@pytest.mark.parametrize('key,value', [('status','stoettetiltaksstatus.feilregistrert'),
                                    ('status','stoettetiltaksstatus.utgaatt'),
                                    ('tildelingsdato','2026-11-07'), ('tildelingsdato','2020-01-01')])
def test_noncurrent_or_unregistered_awards_are_excluded(key, value):
    item = award()
    item[key] = value
    assert not parse(item)[0]


def test_failed_or_partial_refresh_retains_prior_awards():
    old = result([award()])
    for row in [result([], old, status=503), result([], old, status=403),
                result([award('999999999')], old)]:
        assert not row['changes']
        assert row['refresh']['last_known_claims'][0]['stale']
    complete = result([], old)
    assert complete['changes'][0]['type'] == 'removed'
    assert not complete['refresh']['last_known_claims']


def test_same_url_with_wrong_request_body_cannot_prove_removal():
    old = result([award()])
    current = result([], org='999999999')
    current['organisation_number'] = ORG
    current['changes'] = []
    finish(current, old)
    assert not current['changes']
    assert current['refresh']['last_known_claims']


def test_amended_amount_is_a_change_with_both_evidence_sides():
    old = result([award()])
    item = award()
    item['tildeltBeloep']['beloep'] = '65000.00'
    changed = result([item], old)
    assert changed['changes'][0]['type'] == 'changed'
    assert changed['refresh']['previous_evidence']
    assert len(changed['claims']) == 1


def test_at_cap_response_is_marked_partial():
    row = result([award(identifier=str(1000000000+i)) for i in range(1000)])
    assert row['research_sources']['public_awards']['state'] == 'partial'


def test_malformed_result_is_not_an_empty_success():
    row = result([None])
    assert row['availability']['public_awards'] == 'failed'


def test_post_budget_and_body_aware_replay_never_contact_network(tmp_path, monkeypatch):
    transport = Transport(tmp_path / 'limited', requests=0)
    monkeypatch.setattr('orglens.core.public_url', lambda url: pytest.fail('DNS after request cap'))
    assert transport.post(API, [])['budget_exhausted']
    source = tmp_path / 'old'
    (source / 'snapshots').mkdir(parents=True)
    rows = [result([award(org)], org=org) for org in [ORG, '999999999']]
    for row in rows:
        snap = row['source_snapshots'][0]
        raw = json.dumps({'stoettetildeling': [award(row['organisation_number'])]}).encode()
        assert digest(raw) == snap['content_sha256']
        (source / 'snapshots' / (digest(raw) + '.bin')).write_bytes(raw)
    (source / 'envelopes.jsonl').write_text('\n'.join(json.dumps(r) for r in rows), encoding='utf-8')
    replay = ReplayTransport(tmp_path / 'new', source, 100, 100)
    for org in [ORG, '999999999']:
        payload = [{'field': 'STOETTEMOTTAKER_ORGNR', 'value': org, 'matchType': 'EXACT_MATCH'}]
        snap = replay.post(API, payload)
        assert json.loads(snap['text'])['stoettetildeling'][0]['rolle'][0]['rolleinnehaverVirksomhet']['organisasjonsnummer'] == org
    assert replay.post(API, [])['status'] == 0
    assert replay.get(API)['status'] == 0


def test_real_post_reserves_request_and_records_body_identity(tmp_path, monkeypatch):
    headers = Message()
    headers['Content-Type'] = 'application/json; charset=utf-8'
    class Response(io.BytesIO):
        code = 200
        def __init__(self):
            super().__init__(b'{"stoettetildeling":[]}')
            self.headers = headers
    seen = []
    class Opener:
        def open(self, request, **kwargs):
            seen.append(request)
            return Response()
    monkeypatch.setattr('orglens.core.public_url', lambda url: None)
    monkeypatch.setattr('orglens.core.urllib.request.build_opener', lambda *args: Opener())
    transport = Transport(tmp_path, requests=1)
    snap = transport.post(API, [{'value': ORG}])
    assert transport.requests == 1 and seen[0].get_method() == 'POST'
    assert snap['request_body_sha256'] == digest(seen[0].data)
    assert transport.post(API, [{'value': '999999999'}])['budget_exhausted']


def test_batch_integration_uses_global_budget(tmp_path, monkeypatch):
    def fake_get(self, url, source_class='official_registry'):
        body = {'organisasjonsnummer': ORG, 'navn': 'Example AS'}
        snap = snapshot(body)
        snap['source_url'] = url
        (self.root / (snap['content_sha256'] + '.bin')).write_bytes(snap['text'].encode())
        return snap
    def fake_post(self, url, payload, source_class='official_public_api'):
        self.reserve(url)
        snap = snapshot({'stoettetildeling': [award()]})
        (self.root / (snap['content_sha256'] + '.bin')).write_bytes(snap['text'].encode())
        return snap
    monkeypatch.setattr(Transport, 'get', fake_get)
    monkeypatch.setattr(Transport, 'post', fake_post)
    rows, report = run_batch([ORG], tmp_path, run_id='integration', requests=1, modules=('awards',))
    assert report['requests'] == 1
    assert report['coverage']['public_awards'] == 1
    assert rows[0]['availability']['public_awards'] == 'available'
