from orglens.core import envelope, extract_feed, social_profile
from test_integrity_fixes import snapshot


def test_rss_keeps_article_url_and_decodes_title():
    row=envelope('123456789','test')
    xml='<?xml version="1.0"?><rss version="2.0"><channel><item><title>New factory &amp; jobs</title><link>https://example.no/news/factory</link><pubDate>Mon, 12 Oct 2026 13:46:22 +0000</pubDate></item></channel></rss>'
    extract_feed(row,snapshot(xml,'https://example.no/feed'))
    assert row['claims'][0]['value']['url']=='https://example.no/news/factory'
    assert row['claims'][0]['value']['headline']=='New factory & jobs'


def test_atom_keeps_alternate_article_url():
    row=envelope('123456789','test')
    xml='<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>A new office</title><updated>2026-10-12T12:00:00Z</updated><link rel="self" href="https://example.no/api/1"/><link rel="alternate" href="https://example.no/news/office"/></entry></feed>'
    extract_feed(row,snapshot(xml,'https://example.no/feed'))
    assert row['claims'][0]['value']['url']=='https://example.no/news/office'


def test_facebook_posts_and_photos_are_not_company_profiles():
    assert social_profile('https://facebook.com/599407360228640_1643082740855585') is None
    assert social_profile('https://facebook.com/photo.php?fbid=123') is None
    assert social_profile('https://facebook.com/story.php?story_fbid=123&id=456') is None
    assert social_profile('https://facebook.com/examplecompany')['url']=='https://facebook.com/examplecompany'


def test_facebook_query_profile_preserves_identity_and_drops_tracking():
    assert social_profile('https://www.facebook.com/profile.php?id=123456789&utm_source=site')['url'] == 'https://www.facebook.com/profile.php?id=123456789'


def test_facebook_query_profile_without_unique_numeric_identity_is_rejected():
    for url in ('https://facebook.com/profile.php', 'https://facebook.com/profile.php?id=abc',
                'https://facebook.com/profile.php?id=123&id=456'):
        assert social_profile(url) is None


def test_unlabelled_numeric_facebook_media_links_are_not_profiles():
    from orglens.core import extract_site_facts,soup_text
    html='<main><a href="https://facebook.com/1552125346617992"><img src="photo.jpg"></a></main><footer><a aria-label="Facebook" href="https://facebook.com/599407360228640">Follow us</a></footer>'
    parsed,text=soup_text(html)
    row=envelope('123456789','test')
    extract_site_facts(row,{'navn':'Example AS'},[(snapshot(html),parsed,text)],'verified_site')
    assert [c['value']['url'] for c in row['claims'] if c['field']=='owned_profiles']==['https://facebook.com/599407360228640']


def test_social_evidence_preserves_actual_anchor_and_jsonld_locator():
    from orglens.core import extract_site_facts,soup_text
    href='https://m.facebook.com/profile.php?id=123456789&utm_source=site'
    html='<footer><a href="'+href+'">Facebook</a></footer><script type="application/ld+json">{"@type":"Organization","sameAs":"https://linkedin.com/company/example?trk=site"}</script>'
    parsed,text=soup_text(html)
    row=envelope('123456789','test')
    extract_site_facts(row,{'navn':'Example AS'},[(snapshot(html),parsed,text)],'verified_site')
    profiles={c['value']['platform']:c for c in row['claims'] if c['field']=='owned_profiles'}
    evidence={e['id']:e for e in row['evidence']}
    assert profiles['facebook']['value']['url']=='https://facebook.com/profile.php?id=123456789'
    assert evidence[profiles['facebook']['evidence_ids'][0]]['locator']=={'link_href':href}
    assert evidence[profiles['linkedin']['evidence_ids'][0]]['locator']=={'jsonld':{'sameAs':'https://linkedin.com/company/example?trk=site'}}
