from orglens.core import crawl_site,envelope
from test_integrity_fixes import snapshot


class Pages:
    def __init__(self,privacy_proof=False):
        import threading
        self.lock=threading.Lock();self.host_delays={};self.seen=[];self.privacy_proof=privacy_proof
    def get(self,url,source_class='company_owned',headers=None):
        self.seen.append(url)
        if url.endswith('robots.txt'):return {**snapshot('',url),'status':404}
        html='<title>Example AS</title><a href="/kontakt">Kontakt</a><a href="/om-oss">Om oss</a><a href="/personvern">Personvern</a><a href="/news">News</a>'
        if not self.privacy_proof or url.endswith('/personvern'):html+='<footer>Org.nr 123456789</footer>'
        return snapshot(html,url)


def test_after_identity_news_gets_the_remaining_page_budget():
    pages=Pages()
    assert crawl_site(envelope('123456789','test'),{'navn':'Example AS'},pages,page_limit=4,url='https://example.test/')
    assert 'https://example.test/news' in pages.seen
    assert 'https://example.test/personvern' not in pages.seen
    assert len([u for u in pages.seen if not u.endswith('robots.txt')])<=4


def test_privacy_page_can_complete_identity_when_contact_pages_do_not():
    pages=Pages(privacy_proof=True)
    row=envelope('123456789','test')
    assert crawl_site(row,{'navn':'Example AS'},pages,page_limit=4,url='https://brand.test/')
    assert next(c['value'] for c in row['claims'] if c['field']=='official_website')=='https://brand.test/'
    assert 'https://brand.test/personvern' in pages.seen
    assert len([u for u in pages.seen if not u.endswith('robots.txt')])<=4
