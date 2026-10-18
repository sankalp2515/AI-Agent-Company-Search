from orglens.core import crawl_site,envelope
from test_integrity_fixes import Site,snapshot


class Hub(Site):
    def __init__(self,child_org='123456789'):
        super().__init__('');self.child_org=child_org;self.seen=[]
    def get(self,url,source_class='company_owned',headers=None):
        self.seen.append(url)
        if url.endswith('robots.txt'):return {**snapshot('',url),'status':404}
        html=('<title>Welcome to Kaefer Norway</title><p>Kaefer Energy delivers specialist services.</p><a href="https://kaeferenergy.test/">kaeferenergy.test</a>'
              if 'kaefer.test' in url else '<title>Kaefer Energy AS</title><h1>Kaefer Energy AS</h1><footer>Org.nr '+self.child_org+'</footer>')
        return snapshot(html,url)


def test_registered_group_hub_leads_to_independently_verified_company_site():
    row=envelope('123456789','test');transport=Hub()
    assert crawl_site(row,{'navn':'KAEFER ENERGY AS'},transport,origin='registry',url='https://kaefer.test/',page_limit=5)
    assert next(c['value'] for c in row['claims'] if c['field']=='official_website')=='https://kaeferenergy.test/'


def test_failed_specific_company_link_does_not_publish_the_group_hub():
    row=envelope('123456789','test')
    assert not crawl_site(row,{'navn':'KAEFER ENERGY AS'},Hub('987654321'),origin='registry',url='https://kaefer.test/',page_limit=5)
    assert not [c for c in row['claims'] if c['field']=='official_website']
