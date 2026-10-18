from orglens.core import envelope,extract_site_facts,soup_text
from test_integrity_fixes import snapshot


def extract(html,url='https://example.no/'):
    parsed,text=soup_text(html)
    row=envelope('123456789','test')
    extract_site_facts(row,{'navn':'Example AS'},[(snapshot(html,url),parsed,text)],'verified_site')
    return row


def test_norwegian_date_card_keeps_headline_link_and_literal_date():
    html='<main><div><a href="/nyheter/2026/new-factory"><span>Example AS opens a new factory</span></a><p>We opened a factory in Oslo.</p><div><p>07.10.2026</p></div></div></main>'
    row=extract(html)
    fact=next(c for c in row['claims'] if c['field']=='activity')
    assert fact['value']['published_at']=='2026-10-07'
    assert fact['value']['url']=='https://example.no/nyheter/2026/new-factory'
    ev=next(e for e in row['evidence'] if e['id'] in fact['evidence_ids'])
    assert ev['locator']['date_quote']=='07.10.2026'
    assert ev['locator']['link_href']=='/nyheter/2026/new-factory'


def test_date_cannot_leak_between_separate_news_cards():
    row=extract('<main><div><a href="/news/undated">Undated company announcement</a></div><div><p>07.10.2026</p></div></main>')
    assert not [c for c in row['claims'] if c['field']=='activity']


def test_footer_dates_and_invalid_dates_are_not_company_news():
    row=extract('<footer><a href="/news/archive">All company announcements</a>07.10.2026</footer><main><article><a href="/news/wrong">Wrong calendar announcement</a>32.13.2026</article></main>')
    assert not [c for c in row['claims'] if c['field']=='activity']


def test_iso_date_cards_are_deduplicated_between_views():
    row=extract('<main><article><a href="/news/factory">Example AS opens a new factory</a><p>2026-10-07</p></article><article><a href="/news/factory">Example AS opens a new factory</a><p>2026-10-07</p></article></main>')
    assert len([c for c in row['claims'] if c['field']=='activity'])==1


def test_norwegian_month_names_are_parsed_without_system_locale():
    row=extract('<main><article><a href="/aktuelt/new-factory">Example AS opens a new factory</a><p>Publisert 7. oktober 2026</p></article></main>')
    fact=next(c for c in row['claims'] if c['field']=='activity')
    assert fact['value']['published_at']=='2026-10-07'
    assert next(e for e in row['evidence'] if e['id'] in fact['evidence_ids'])['locator']['date_quote']=='7. oktober 2026'


def test_one_news_item_from_card_and_article_keeps_both_evidence_sources():
    import json
    home_html='<main><article><a href="/news/factory">Example AS opens a new factory</a><p>2026-10-07</p></article></main>'
    article_html='<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','headline':'Example AS opens a new factory','datePublished':'2026-10-07T12:00:00Z','url':'https://example.no/news/factory'})+'</script>'
    pages=[]
    for html,url in [(home_html,'https://example.no/'),(article_html,'https://example.no/news/factory')]:
        parsed,text=soup_text(html);pages.append((snapshot(html,url),parsed,text))
    row=envelope('123456789','test')
    extract_site_facts(row,{'navn':'Example AS'},pages,'verified_site')
    facts=[c for c in row['claims'] if c['field']=='activity']
    assert len(facts)==1
    assert len(facts[0]['evidence_ids'])==2
