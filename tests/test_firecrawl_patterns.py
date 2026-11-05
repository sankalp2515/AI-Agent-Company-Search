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


def test_historical_name_domain_is_a_candidate_but_current_entity_is_proved(monkeypatch):
    import orglens.names as names
    monkeypatch.setattr(names,'guess_domains',lambda legal_name,form=None:['https://oldbrand.no/'] if legal_name=='Oldbrand AS' else [])
    monkeypatch.setattr(names,'resolves',lambda url:True)
    t=Sites({'https://parent.no/':'<h1>Parent Group AS</h1><p>Org.nr 987654321</p>',
             'https://oldbrand.no/':'<h1>Newbrand AS</h1><p>Org.nr 123456789</p>'})
    row=core.envelope('123456789','t')
    assert core.research_website(row,{'navn':'Newbrand AS','hjemmeside':'https://parent.no/',
                                     'historiskeNavn':[{'navn':'Oldbrand AS'}]},t,3,max_guess_fetches=1)
    assert row['website_research']['verification']['origin']=='historical_name_guess'
    assert row['website_research']['verification']['method']=='labelled_organisation_number'


def test_historical_name_does_not_authorize_a_different_entity(monkeypatch):
    import orglens.names as names
    monkeypatch.setattr(names,'guess_domains',lambda legal_name,form=None:['https://oldbrand.no/'])
    monkeypatch.setattr(names,'resolves',lambda url:True)
    t=Sites({'https://oldbrand.no/':'<h1>Oldbrand AS</h1><p>Org.nr 987654321</p>'})
    row=core.envelope('123456789','t')
    assert not core.research_website(row,{'navn':'Newbrand AS','historiskeNavn':[{'navn':'Oldbrand AS'}]},t,3,max_guess_fetches=1)
    assert not [c for c in row['claims'] if c['field']=='official_website']


def test_instructional_blog_post_is_not_company_news_despite_publisher_suffix():
    import json
    home='<h1>Example AS</h1>'
    for title in ['How to Build Confidence as a Leader - Example', '5 Leadership Traits Every Woman Should Cultivate - Example']:
        html='<h1>'+title+'</h1><script type="application/ld+json">'+json.dumps({'@type':'BlogPosting','headline':title,'datePublished':'2025-03-11','description':'Advice from Example AS about leadership.'})+'</script>'
        snap={**site('https://example.no/leadership-advice',html),'news_context':{'index_url':'https://example.no/blog','link_label':title}}
        row=core.envelope('123456789','t')
        core.extract_site_facts(row,{'navn':'EXAMPLE AS'},[(site('https://example.no/',home),*core.soup_text(home)),(snap,*core.soup_text(html))],'labelled_organisation_number')
        assert not [c for c in row['claims'] if c['field']=='activity']


def test_instructional_headline_is_rejected_consistently_for_feeds():
    xml='<rss><channel><item><title>How to Build Confidence as a Leader</title><pubDate>Tue, 11 Mar 2025 10:00:00 +0000</pubDate><link>https://example.no/news/leadership-advice</link></item></channel></rss>'
    row=core.envelope('123456789','t')
    core.extract_feed(row,site('https://example.no/feed',xml),{'navn':'Example AS'},'https://example.no/')
    assert not [c for c in row['claims'] if c['field']=='activity']
