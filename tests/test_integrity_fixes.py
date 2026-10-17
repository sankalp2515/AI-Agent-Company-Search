import json
import threading

from orglens.core import (claim, crawl_site, envelope, finish, jsonld_org_ids,
                          corroborated, soup_text, synthesize)


def snapshot(html, url='https://acmeinvest.no/'):
    import hashlib
    return {'id': hashlib.sha256((url + html).encode()).hexdigest()[:24],
            'source_url': url, 'status': 200, 'source_class': 'company_owned',
            'retrieved_at': '2026-10-17T00:00:00Z', 'text': html,
            'content_sha256': hashlib.sha256(html.encode()).hexdigest(), 'content_type': 'text/html'}


class Site:
    def __init__(self, html):
        self.html = html
        self.lock = threading.Lock()
        self.host_delays = {}

    def get(self, url, source_class='company_owned', headers=None):
        return {**snapshot('' if url.endswith('robots.txt') else self.html, url),
                'status': 404 if url.endswith('robots.txt') else 200}


def test_registry_partial_name_never_assigns_group_description():
    row = envelope('123456789', 'test')
    body = {'navn': 'ACME INVEST AS', 'hjemmeside': 'https://acme.no/', 'organisasjonsform': {'kode': 'AS'}}
    assert not crawl_site(row, body, Site('<h1>ACME Group</h1><meta name="description" content="Operations of the entire international group">'))
    assert not row['claims']


def test_conflicting_footer_vetoes_matching_jsonld():
    html = '<footer>Org.nr 987654321</footer><script type="application/ld+json">{"@type":"Organization","name":"Acme Invest AS","taxID":"123456789"}</script>'
    row = envelope('123456789', 'test')
    assert not crawl_site(row, {'navn': 'ACME INVEST AS'}, Site(html), origin='name_guess', url='https://acmeinvest.no/')
    assert not row['claims']


def test_identifier_suffix_and_foreign_identifier_are_not_norwegian_identity():
    assert jsonld_org_ids({'identifier': '99123456789', 'duns': '123456789', 'leiCode': 'XX123456789'}) == []
    assert jsonld_org_ids({'vatID': 'NO 123 456 789 MVA'}) == ['123456789']


def test_unrelated_digit_fragments_cannot_corroborate_phone():
    html = '<h1>Acme Invest AS</h1><p>Order 2233; item 4455</p>'
    soup, text = soup_text(html)
    assert corroborated({'navn': 'ACME INVEST AS', 'telefon': '22334455'}, [(snapshot(html), soup, text)]) is None


def test_shared_director_and_domain_name_are_not_legal_identity():
    row = envelope('123456789', 'test')
    claim(row, 'leadership', {'name': 'Kari Nordmann', 'role': 'Daglig leder'}, snapshot('{}'), {'json_pointer': '/x'})
    html = '<p>Contact Kari Nordmann</p>'
    soup, text = soup_text(html)
    assert corroborated({'navn': 'ACME INVEST AS'}, [(snapshot(html), soup, text)], row, True) is None


def test_failed_site_does_not_remove_activity_when_registry_succeeds():
    registry = {**snapshot('{}', 'https://data.brreg.no/entity/123456789'), 'source_class': 'official_registry'}
    website = snapshot('news', 'https://acmeinvest.no/news/')
    old = envelope('123456789', 'old')
    old['availability'] = {'activity': 'available', 'official_website': 'available'}
    claim(old, 'activity', {'headline': 'Registry event', 'kind': 'official_registry_event'}, registry, {'text_quote': 'registry'})
    claim(old, 'activity', {'headline': 'Company event', 'kind': 'company_owned_article'}, website, {'text_quote': 'news'})
    finish(old)
    new = envelope('123456789', 'new')
    new['availability'] = {'activity': 'available', 'official_website': 'failed'}
    claim(new, 'activity', {'headline': 'Registry event', 'kind': 'official_registry_event'}, registry, {'text_quote': 'registry'})
    finish(new, old)
    assert new['changes'] == []
    assert len(new['refresh']['last_known_claims']) == 1
    assert new['refresh']['last_known_claims'][0]['value']['headline'] == 'Company event'
    retry = envelope('123456789', 'retry')
    retry['availability'] = {'activity': 'available', 'official_website': 'failed'}
    claim(retry, 'activity', {'headline': 'Registry event', 'kind': 'official_registry_event'}, registry, {'text_quote': 'registry'})
    finish(retry, new)
    assert retry['changes'] == []
    assert len(retry['refresh']['last_known_claims']) == 1


def test_successfully_observed_removal_is_reported():
    site = snapshot('old', 'https://acmeinvest.no/news/')
    old = envelope('123456789', 'old')
    old['availability']['activity'] = 'available'
    claim(old, 'activity', {'headline': 'Old event'}, site, {'text_quote': 'old'})
    finish(old)
    new = envelope('123456789', 'new')
    new['availability'].update(activity='not_available', official_website='available')
    from orglens.core import attach
    attach(new, snapshot('no news', site['source_url']))
    finish(new, old)
    assert len(new['changes']) == 1 and new['changes'][0]['type'] == 'removed'
    assert new['refresh']['last_known_claims'] == []


def test_latest_activity_compares_parsed_dates():
    row = envelope('123456789', 'date')
    for headline, date in [('Old', 'Wed, 01 Jan 2025 00:00:00 +0000'), ('New', 'Thu, 01 Jan 2026 00:00:00 +0000')]:
        claim(row, 'activity', {'headline': headline, 'published_at': date, 'kind': 'company_owned_feed_item'}, snapshot(headline), {'text_quote': headline})
    assert '“New”' in synthesize(row)['text']
    assert '2026-01-01' in synthesize(row)['text']


def test_operating_head_on_full_name_domain_is_accepted_but_board_member_is_not():
    html = '<h1>Myre og Partnere</h1><p>Daglig leder Jan Nevestad</p>'
    soup, text = soup_text(html)
    pages = [(snapshot(html), soup, text)]
    row = envelope('123456789', 'test')
    claim(row, 'leadership', {'name': 'Jan Nevestad', 'role': 'Styremedlem'}, snapshot('{}'), {'json_pointer': '/x'})
    assert corroborated({'navn': 'MYRE & PARTNERE AS'}, pages, row, True) is None
    claim(row, 'leadership', {'name': 'Jan Nevestad', 'role': 'Daglig leder'}, snapshot('{}'), {'json_pointer': '/y'})
    assert corroborated({'navn': 'MYRE & PARTNERE AS'}, pages, row, True)[2] == 'full_name_domain_and_registered_operating_head'
    assert corroborated({'navn': 'MYRE & PARTNERE AS'}, pages, row, False) is None


def test_static_about_page_article_schema_is_not_dated_news():
    from orglens.core import extract_site_facts
    row = envelope('123456789', 'test')
    row['availability'] = {}
    about = '<script type="application/ld+json">{"@type":"Article","headline":"Om oss","datePublished":"2020-01-01"}</script>'
    news = '<script type="application/ld+json">{"@type":"BlogPosting","headline":"Vi åpner ny butikk","datePublished":"2026-09-01"}</script>'
    pages = []
    for html, url in (('<p>home</p>', 'https://acme.no/'), (about, 'https://acme.no/om-oss'), (news, 'https://acme.no/nyheter/ny-butikk')):
        soup, text = soup_text(html)
        pages.append((snapshot(html, url), soup, text))
    extract_site_facts(row, {'navn': 'ACME AS'}, pages, 'labelled_organisation_number')
    headlines = [c['value']['headline'] for c in row['claims'] if c['field'] == 'activity']
    assert headlines == ['Vi åpner ny butikk']


def test_trickling_response_is_abandoned_within_the_wall_clock_cap(tmp_path, monkeypatch):
    import orglens.core as core
    monkeypatch.setattr(core, "MAX_READ_SECONDS", 0.2)
    monkeypatch.setattr(core, "public_url", lambda url: None)

    class Slow:
        code = 200
        headers = type("H", (), {"get_content_charset": lambda self: "utf-8", "get_content_type": lambda self: "text/html"})()

        def read(self, n):
            __import__("time").sleep(0.05)
            return b"x"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class Opener:
        def open(self, req, timeout=None):
            return Slow()

    monkeypatch.setattr(core.urllib.request, "build_opener", lambda *a: Opener())
    started = __import__("time").monotonic()
    result = core.Transport(tmp_path).get("https://slow.example/")
    assert result["status"] == 0 and "too slow" in result["error"]
    assert __import__("time").monotonic() - started < 3


def test_registry_declared_parent_group_domain_is_rejected(monkeypatch):
    import threading
    import orglens.core as core
    pages = {"https://www.ypsomed.com/robots.txt": (404, ""),
             "https://www.ypsomed.com/en/": (200, "<h1>Ypsomed</h1><p>mylife Diabetes Care products</p>")}

    class T:
        lock = threading.Lock()
        host_delays = {}

        def get(self, url, source_class="x", headers=None):
            code, html = pages.get(url, (404, ""))
            return {**snapshot(html, url), "status": code, "content_type": "text/html"}

    row = envelope("123456789", "t")
    body = {"navn": "MYLIFE DIABETES CARE AS", "organisasjonsform": {"kode": "AS"}, "hjemmeside": "https://www.ypsomed.com/en/"}
    assert not core.crawl_site(row, body, T(), 3, origin="registry")
