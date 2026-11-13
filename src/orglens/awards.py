"""Dated official state-aid evidence joined by an exact corporate recipient ID."""
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

API = 'https://stottetiltak-registerinfo-api.app.brreg.no/api/v1/soek/stoettetildeling?language=ENG'


def exact_json(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: exact_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [exact_json(v) for v in value]
    return value


def extract(payload, org, *, as_of=None):
    as_of = as_of or datetime.now(timezone.utc).date()
    try:
        start = as_of.replace(year=as_of.year - 3)
    except ValueError:
        start = as_of.replace(year=as_of.year - 3, day=28)
    facts, rejected, conflicted = {}, Counter(), set()
    for i, item in enumerate(payload['stoettetildeling']):
        recipients = [r.get('rolleinnehaverVirksomhet', {}).get('organisasjonsnummer')
                      for r in item.get('rolle', []) if r.get('type') == 'rolletype.stoettemottaker'
                      and r.get('rolleinnehavertype') == 'virksomhet']
        if org not in recipients:
            rejected['recipient_mismatch'] += 1
            continue
        if item.get('status') != 'stoettetiltaksstatus.registrert':
            rejected['not_registered'] += 1
            continue
        try:
            when = date.fromisoformat(item['tildelingsdato'])
        except (ValueError, KeyError, TypeError):
            rejected['missing_award_date'] += 1
            continue
        if not start <= when <= as_of:
            rejected['outside_window'] += 1
            continue
        identifier = item.get('stoettetiltaksnummer', '')
        if not isinstance(identifier, str) or not re.fullmatch(r'[0-9]+', identifier):
            rejected['invalid_id'] += 1
            continue
        amount = item.get('tildeltBeloep') or {}
        try:
            number = Decimal(str(amount['beloep']))
            if not number.is_finite() or number < 0 or not re.fullmatch('[A-Z]{3}', amount['valuta']):
                raise ValueError('invalid amount')
        except (ValueError, InvalidOperation, TypeError, KeyError):
            amount = None
        else:
            amount = {'amount': str(number), 'currency': amount['valuta']}
        donors = [r.get('rolleinnehaverVirksomhet') for r in item.get('rolle', [])
                  if r.get('type') == 'rolletype.stoettegiver' and r.get('rolleinnehavertype') == 'virksomhet']
        value = {'organisation_number': org, 'award_id': identifier,
                 'kind': 'official_state_aid_award', 'award_date': when.isoformat(),
                 'amount': amount, 'amount_interval': exact_json(item.get('beloepsintervall')),
                 'instrument': item.get('stoetteinstrument'), 'donors': donors,
                 'url': 'https://stotte.brreg.no/nb/oppslag/stoettetildeling/' + identifier}
        if identifier in conflicted:
            continue
        if identifier in facts and facts[identifier]['value'] != value:
            rejected['duplicate_id_conflict'] += 1
            facts.pop(identifier, None)
            conflicted.add(identifier)
            continue
        facts.setdefault(identifier, {'value': value, 'json_pointer': '/stoettetildeling/' + str(i),
                                      'registered_date': item.get('mottattDato'), 'source_changed_at': item.get('endret')})
    return list(facts.values()), dict(rejected)


def research(row, transport, claim):
    """One bounded request. At-cap or malformed results stay explicitly partial."""
    from .core import attach, availability

    org = row['organisation_number']
    payload = [{'field': 'STOETTEMOTTAKER_ORGNR', 'value': org, 'matchType': 'EXACT_MATCH'}]
    snap = transport.post(API, payload)
    state = availability(snap)
    info = row.setdefault('research_sources', {}).setdefault('public_awards', {})
    info.update(state=state, request_body_sha256=snap.get('request_body_sha256'),
                source_url=API, window_years=3, complete=False)
    row['availability']['public_awards'] = state
    if state != 'available':
        if state == 'not_available':
            row['availability']['public_awards'] = info['state'] = 'failed'
        attach(row, snap)
        return
    try:
        data = json.loads(snap['text'], parse_float=Decimal)
        if not isinstance(data, dict) or not isinstance(data.get('stoettetildeling'), list):
            raise ValueError('State-aid response is missing its result array')
        items = data['stoettetildeling']
        if any(not isinstance(item, dict) or not isinstance(item.get('rolle', []), list)
               or any(not isinstance(r, dict) for r in item.get('rolle', [])) for item in items):
            raise ValueError('Malformed state-aid row')
        # Replay uses the original observation's date for the recency window.
        as_of = date.fromisoformat(snap['retrieved_at'][:10])
        facts, rejected = extract(data, org, as_of=as_of)
        partial = len(items) >= 1000 or bool(set(rejected) - {'outside_window', 'not_registered'})
        info.update(state='partial' if partial else 'complete', complete=not partial,
                    source_rows=len(items), accepted=len(facts), rejections=rejected)
        for fact in facts:
            value = fact['value']
            claim(row, 'public_awards', value, snap,
                  {'json_pointer': fact['json_pointer'], 'recipient_organisation_number': org,
                   'award_id': value['award_id'], 'request_body_sha256': snap.get('request_body_sha256'),
                   'public_url': value['url'],
                   'registration_date': fact['registered_date'], 'source_changed_at': fact['source_changed_at']},
                  period={'date': value['award_date']}, identity_method='exact_official_award_recipient')
        attach(row, snap)
        row['availability']['public_awards'] = 'available' if facts else 'ambiguous' if partial else 'not_available'
        if partial:
            row['errors'].append({'module': 'awards', 'message': 'Award lookup partial; missing records remain unknown.'})
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        attach(row, snap)
        info.update(state='failed', complete=False)
        row['availability']['public_awards'] = 'failed'
        row['errors'].append({'module': 'awards', 'message': str(exc)})
