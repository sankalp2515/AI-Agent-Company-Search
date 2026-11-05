"""Behavioral cases motivated by Firecrawl inspection; no connector needed at runtime."""
from orglens import core
from test_v4_review import Sites,site


def test_news_index_is_followed_within_the_existing_page_budget():
    home='<h1>Example AS</h1><p>Org.nr 123456789</p><a href="/articles">News</a>'
    index='<h1>News</h1><a href="/ceo_transition">Example appoints its new chief executive Press Release</a>'
    article='<main><h1>Example AS appoints its new chief executive</h1><h3>02 November 2026, Oslo (Norway)</h3><p>The appointment is effective 1 November 2026.</p></main>'
    t=Sites({'https://example.no/':home,'https://example.no/articles':index,'https://example.no/ceo_transition':article})
    row=core.envelope('123456789','t')
    assert core.crawl_site(row,{'navn':'EXAMPLE AS'},t,3,origin='search',url='https://example.no/')
    facts=[c['value'] for c in row['claims'] if c['field']=='activity']
    assert [(v['url'],v['published_at']) for v in facts]==[('https://example.no/ceo_transition','2026-11-02')]
    html_pages=[s for s in row['source_snapshots'] if not s['source_url'].endswith('/robots.txt')]
    assert len(html_pages)<=3


def test_dated_contact_link_on_news_index_is_not_news():
    home='<h1>Example AS</h1><p>Org.nr 123456789</p><a href="/news">News</a>'
    index='<main><h1>News</h1><a href="/contact">Contact Example AS for more information</a></main>'
    contact='<main><h1>Contact Example AS for more information</h1><h3>02 November 2026</h3></main>'
    t=Sites({'https://example.no/':home,'https://example.no/news':index,'https://example.no/contact':contact})
    row=core.envelope('123456789','t')
    core.crawl_site(row,{'navn':'EXAMPLE AS'},t,4,origin='search',url='https://example.no/')
    assert not [c for c in row['claims'] if c['field']=='activity']


def test_article_effective_date_is_not_a_publication_date():
    row=core.envelope('123456789','t')
    html='<main><h1>Example AS appoints its new chief executive</h1><p>The appointment is effective 1 November 2026.</p></main>'
    snap={**site('https://example.no/ceo_transition',html),'news_context':{'index_url':'https://example.no/articles','link_label':'Example appoints new CEO'}}
    core.extract_site_facts(row,{'navn':'EXAMPLE AS'},[(site('https://example.no/','<h1>Example AS</h1>'),*core.soup_text('<h1>Example AS</h1>')),
                            (snap,*core.soup_text(html))],'labelled_organisation_number')
    assert not [c for c in row['claims'] if c['field']=='activity']


def test_news_link_cannot_switch_publishers_or_publish_other_company():
    home='<h1>Example AS</h1><p>Org.nr 123456789</p><a href="/news">News</a>'
    index='<h1>News</h1><a href="https://other.no/announcement">Example opens a new office Press release</a><a href="/competitor-event">Other company opens a new office Press release</a>'
    other='<main><h1>Other Company AS opens a new office</h1><h3>02 November 2026</h3><p>Other Company is expanding.</p></main>'
    t=Sites({'https://example.no/':home,'https://example.no/news':index,'https://example.no/competitor-event':other})
    row=core.envelope('123456789','t')
    core.crawl_site(row,{'navn':'EXAMPLE AS'},t,4,origin='search',url='https://example.no/')
    assert not [c for c in row['claims'] if c['field']=='activity']
    assert not [s for s in row['source_snapshots'] if 'other.no' in s['source_url']]


def test_missing_metadata_description_uses_literal_company_paragraph():
    html='<h1>Example AS</h1><p>Example AS er et rådgivningsfirma som leverer tjenester innen planlegging og prosess.</p><footer><p>Example AS tilbyr nettsider laget av en annen bedrift.</p></footer>'
    row=core.envelope('123456789','t')
    core.extract_site_facts(row,{'navn':'EXAMPLE AS'},[(site('https://example.no/',html),*core.soup_text(html))],'labelled_organisation_number')
    facts=[c for c in row['claims'] if c['field']=='description']
    assert len(facts)==1 and facts[0]['value']=='Example AS er et rådgivningsfirma som leverer tjenester innen planlegging og prosess.'


def test_navigation_or_footer_cannot_supply_fallback_description():
    html='<nav><p>Example AS er et rådgivningsfirma som leverer tjenester innen planlegging og prosess.</p></nav><footer><p>Example AS leverer tjenester innen planlegging og prosess.</p></footer>'
    row=core.envelope('123456789','t')
    core.extract_site_facts(row,{'navn':'EXAMPLE AS'},[(site('https://example.no/',html),*core.soup_text(html))],'labelled_organisation_number')
    assert not [c for c in row['claims'] if c['field']=='description']
