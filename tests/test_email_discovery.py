import orglens.core as core


def test_registered_business_email_is_a_candidate_not_identity_proof(monkeypatch):
    visited=[]
    def crawl(row,body,transport,page_limit,origin,url):
        visited.append((url,origin));return False
    monkeypatch.setattr(core,'crawl_site',crawl)
    row=core.envelope('123456789','test')
    assert not core.research_website(row,{'navn':'Example AS','epostadresse':'Contact <office@brand-alias.no>'},object(),guesses=False)
    assert visited==[('https://brand-alias.no/','registry_email')]
    assert not row['claims']


def test_personal_email_services_do_not_become_company_website_candidates(monkeypatch):
    visited=[]
    monkeypatch.setattr(core,'crawl_site',lambda *a,**k:visited.append(k['url']))
    for email in ['owner@gmail.com','owner@hotmail.com','owner@online.no','not-an-email']:
        core.research_website(core.envelope('123456789','test'),{'navn':'Example AS','epostadresse':email},object(),guesses=False)
    assert visited==[]


def test_registered_email_candidate_still_rejects_a_different_publisher():
    from test_integrity_fixes import Site
    row=core.envelope('123456789','test')
    assert not core.research_website(row,{'navn':'Example AS','epostadresse':'owner@manager.test'},Site('<title>Manager AS</title><h1>Manager AS</h1><footer>Org.nr 987654321</footer>'),guesses=False)
    assert not [c for c in row['claims'] if c['field']=='official_website']
