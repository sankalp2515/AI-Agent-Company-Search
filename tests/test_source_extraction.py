from orglens.core import envelope, extract_site_facts, soup_text
from test_integrity_fixes import snapshot
from orglens.discovery import candidate_roots


def test_search_preserves_company_subpage_when_requested():
    result=candidate_roots({'results':[{'url':'https://brand.no/shops/holmestrand/?utm_source=x#top'}]},preserve_paths=True)
    assert result==['https://brand.no/shops/holmestrand/']


def test_plain_company_description_has_literal_source_quote():
    html='<h1>Example AS</h1><main><p>We manufacture specialist equipment for fishing vessels along the Norwegian coast.</p></main><footer>Org.nr 123456789</footer>'
    soup,text=soup_text(html)
    row=envelope('123456789','test')
    extract_site_facts(row,{'navn':'Example AS'},[(snapshot(html),soup,text)],'labelled_organisation_number')
    found=[c for c in row['claims'] if c['field']=='description']
    assert found[0]['value']=='We manufacture specialist equipment for fishing vessels along the Norwegian coast.'
    evidence=next(e for e in row['evidence'] if e['id'] in found[0]['evidence_ids'])
    assert evidence['locator']['text_quote']==found[0]['value']


def test_main_description_does_not_take_cookie_banner():
    html='<p>We use cookies to improve your experience and analyze traffic on this website.</p><main><p>Example AS repairs boats and supplies marine equipment throughout northern Norway.</p></main>'
    soup,text=soup_text(html)
    row=envelope('123456789','test')
    extract_site_facts(row,{'navn':'Example AS'},[(snapshot(html),soup,text)],'labelled_organisation_number')
    assert next(c['value'] for c in row['claims'] if c['field']=='description').startswith('Example AS repairs')


def test_description_selector_never_receives_third_party_news_cards():
    import time
    html='<main><div class="blog-item"><h2><a href="/news/patent-agreement">Patent agreement</a></h2><p>Foreign patent authorities have signed an agreement to cooperate on patent applications.</p></div><section><p>We manufacture marine equipment and repair industrial pumps for Norwegian customers.</p></section></main>'
    soup,text=soup_text(html)
    class Selector:
        def select_description(self,name,options,transport):
            assert not any('patent authorities' in x for x in options)
            return options[0]
    row=envelope('123456789','test')
    transport=type('T',(),{'deadline':time.monotonic()+60})()
    extract_site_facts(row,{'navn':'Example AS'},[(snapshot(html),soup,text)],'labelled_organisation_number',Selector(),transport)
    assert next(c['value'] for c in row['claims'] if c['field']=='description').startswith('We manufacture')


def test_generic_article_markup_on_careers_or_sales_terms_is_not_news():
    import json
    home=snapshot('<main>Example AS</main>','https://example.no/')
    home_soup,home_text=soup_text(home['text'])
    for path,title in (('career','Career - Example AS'),('salgsbetingelser','Salgsbetingelser - Example AS')):
        html='<script type="application/ld+json">'+json.dumps({'@type':'Article','headline':title,'datePublished':'2025-04-03','url':'https://example.no/'+path+'/'})+'</script>'
        parsed,text=soup_text(html)
        row=envelope('123456789','test')
        extract_site_facts(row,{'navn':'Example AS'},[(home,home_soup,home_text),(snapshot(html,'https://example.no/'+path+'/'),parsed,text)],'verified_site')
        assert not [c for c in row['claims'] if c['field']=='activity']


def test_actual_news_about_careers_remains_available():
    import json
    home=snapshot('<main>Example AS</main>','https://example.no/')
    home_soup,home_text=soup_text(home['text'])
    url='https://example.no/news/new-career-programme/'
    html='<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','headline':'New career programme opens','datePublished':'2026-10-12','url':url})+'</script>'
    parsed,text=soup_text(html)
    row=envelope('123456789','test')
    extract_site_facts(row,{'navn':'Example AS'},[(home,home_soup,home_text),(snapshot(html,url),parsed,text)],'verified_site')
    assert next(c['value']['url'] for c in row['claims'] if c['field']=='activity')==url
