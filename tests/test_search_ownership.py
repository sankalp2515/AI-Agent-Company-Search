from orglens.core import crawl_site, envelope
from test_integrity_fixes import Site, snapshot


class Directory(Site):
    def get(self, url, source_class='company_owned', headers=None):
        if url.endswith('robots.txt'):
            return {**snapshot('', url), 'status': 404}
        html = ('<h1>Find any business</h1><footer>Org.nr 987654321</footer>'
                if url == 'https://directory.test/' else
                '<h1>Example AS</h1><p>Org.nr 123456789</p><a href="https://facebook.com/directory">Facebook</a>')
        return snapshot(html, url)


def test_search_business_listing_cannot_become_owned_website():
    row = envelope('123456789', 'test')
    assert not crawl_site(row, {'navn': 'Example AS'}, Directory(''), origin='search',
                          url='https://directory.test/company/example')
    assert not row['claims']


def test_search_deep_link_can_verify_real_company_at_root():
    row = envelope('123456789', 'test')
    assert crawl_site(row, {'navn': 'Example AS'}, Site('<h1>Example AS</h1><footer>Org.nr 123456789</footer>'),
                      origin='search', url='https://example.test/news/new-product')
    assert next(c['value'] for c in row['claims'] if c['field'] == 'official_website') == 'https://example.test/'
