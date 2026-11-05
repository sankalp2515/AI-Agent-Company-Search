"""Behavioral experiments for the official keyless source contract."""
import json
from datetime import datetime,timedelta,timezone
from email.utils import parsedate_to_datetime

import orglens.core as core
from orglens.navjobs import NavJobs
from test_integrity_fixes import snapshot
from test_v4_review import Sites,profiles,site


def test_missing_publisher_labels_cannot_authorize_a_shared_brand_parent():
    transport=Sites({'https://fjordbakst.no/':'<div>Fjordbakst Group</div><a href="/kontakt">Kontakt</a>',
                     'https://fjordbakst.no/kontakt':'<p>Fjordbakst Vest AS Org.nr 123456789</p>'})
    row=core.envelope('123456789','t')
    assert not core.crawl_site(row,{'navn':'FJORDBAKST VEST AS'},transport,3,origin='search',url='https://fjordbakst.no/')


def test_media_card_has_the_same_subject_rule_as_feed_news():
    html='<h1>Radio Grenland AS</h1><article><a href="/news/cup">Football club wins new trophy</a><p>03.11.2026</p></article>'
    row=core.envelope('123456789','t');parsed,visible=core.soup_text(html)
    core.extract_site_facts(row,{'navn':'RADIO GRENLAND AS','naeringskode1':{'kode':'60.100'}},
                            [(site('https://example.no/',html),parsed,visible)],'labelled_organisation_number')
    assert not [c for c in row['claims'] if c['field']=='activity']


def test_norwegian_agency_credit_is_not_company_ownership():
    html='<h1>Example AS</h1><footer><p>Nettside levert av <a href="https://facebook.com/profile.php?id=999888777">Studio X</a></p></footer>'
    assert profiles(html)==[]


def test_exact_three_letter_company_profile_is_preserved():
    html='<h1>TGS ASA</h1><a href="https://linkedin.com/company/tgs">LinkedIn</a>'
    row=core.envelope('123456789','t');parsed,visible=core.soup_text(html)
    core.extract_site_facts(row,{'navn':'TGS ASA'},[(site('https://tgs.no/',html),parsed,visible)],'labelled_organisation_number')
    assert [c['value']['url'] for c in row['claims'] if c['field']=='owned_profiles']==['https://linkedin.com/company/tgs']


def test_redirected_feed_cannot_change_the_verified_article_publisher():
    class RedirectedFeed(Sites):
        def get(self,url,source_class='company_owned',headers=None):
            if url=='https://example.no/feed/':
                xml='<rss><channel><item><title>Other company opens new office</title><pubDate>Tue, 03 Nov 2026 10:00:00 +0000</pubDate><link>https://other.no/news/office</link></item></channel></rss>'
                return {**site('https://other.no/feed/',xml),'requested_url':url}
            return super().get(url,source_class,headers)
    t=RedirectedFeed({'https://example.no/':'<h1>Example AS</h1><p>Org.nr 123456789</p><link type="application/rss+xml" href="/feed/">'})
    row=core.envelope('123456789','t')
    assert core.crawl_site(row,{'navn':'EXAMPLE AS'},t,3,origin='search',url='https://example.no/')
    assert not [c for c in row['claims'] if c['field']=='activity']


def test_static_page_inside_news_namespace_is_not_a_news_item():
    xml='<rss><channel><item><title>Privacy Policy Details</title><pubDate>Tue, 03 Nov 2026 10:00:00 +0000</pubDate><link>https://example.no/news/privacy-policy</link></item></channel></rss>'
    row=core.envelope('123456789','t')
    core.extract_feed(row,snapshot(xml,'https://example.no/feed/'))
    assert not [c for c in row['claims'] if c['field']=='activity']


class ActiveJobs:
    def __init__(self,old=False):self.now=datetime.now(timezone.utc);self.old=old
    def get(self,url,source_class='official_public_api',headers=None):
        if url.endswith('/api/v1/feed'):
            when=self.now-timedelta(days=60)
            begin=parsedate_to_datetime(headers['If-Modified-Since'])
            body={'items':([{'date_modified':when.isoformat(),'url':'/api/v1/feedentry/old',
                              '_feed_entry':{'uuid':'old','status':'ACTIVE','businessName':'Example AS'}}] if begin<=when else []),'next_url':None}
        else:
            expired=url.endswith('a-old')
            body={'status':'ACTIVE','ad_content':{'title':'A genuine vacancy','employer':{'orgnr':'123456789'},
                  'published':(self.now-timedelta(days=60 if expired else 1)).isoformat(),
                  'expires':(self.now+timedelta(days=-1 if expired else 30)).isoformat(),'link':'https://example.no/jobs/1'}}
        return {**snapshot(json.dumps(body),url),'status':200}


def test_default_bootstrap_finds_still_active_two_month_old_ad(monkeypatch):
    monkeypatch.setenv('NAV_FEED_TOKEN','test-token')
    nav=NavJobs(segments=1);t=ActiveJobs();nav.load(t,page_cap=10)
    row=core.envelope('123456789','t')
    nav.research(row,{'navn':'Example AS'},t,core.claim)
    assert row['availability']['jobs']=='available'


def test_newest_candidate_precedes_expired_candidate_when_detail_budget_is_small():
    nav=NavJobs(max_candidate_details=1);nav.state='loaded';nav.token='test-token'
    now=datetime.now(timezone.utc)
    nav.index={'example':{k:{'url':'/api/v1/feedentry/'+k,'date_modified':(now-timedelta(days=days)).isoformat(),
                            '_feed_entry':{'uuid':k,'status':'ACTIVE','businessName':'Example AS'}}
                          for k,days in [('a-old',60),('z-new',1)]}}
    row=core.envelope('123456789','t')
    nav.research(row,{'navn':'Example AS'},ActiveJobs(),core.claim)
    assert row['availability']['jobs']=='available'


def test_website_verifier_can_use_leadership_retrieved_in_this_run(tmp_path,monkeypatch):
    seen=[]
    def get(self,url,source_class='official_registry',headers=None):
        if url.endswith('/roller'):
            body={'rollegrupper':[{'roller':[{'person':{'navn':{'fornavn':'Kari','etternavn':'Nordmann'}},'type':{'beskrivelse':'Daglig leder'}}]}]}
        else:body={'organisasjonsnummer':'123456789','navn':'Example AS'}
        raw=json.dumps(body).encode();sha=core.digest(raw);(self.root/(sha+'.bin')).write_bytes(raw);self.requests+=1
        return {'id':core.digest(url),'source_url':url,'source_class':source_class,'status':200,'text':raw.decode(),
                'retrieved_at':core.now(),'content_sha256':sha,'snapshot_path':'snapshots/'+sha+'.bin'}
    def research(row,*args,**kwargs):
        seen.append(any(c['field']=='leadership' for c in row['claims']));return False
    monkeypatch.setattr(core.Transport,'get',get);monkeypatch.setattr(core,'research_website',research)
    rows,report=core.run_batch(['123456789'],tmp_path,run_id='t',modules=('website','leadership'),strategy='balanced')
    assert report['validation']['passed']
    assert seen==[True]


def test_stopped_ad_with_future_expiry_is_not_published():
    class Stopped(ActiveJobs):
        def get(self,url,source_class='official_public_api',headers=None):
            response=super().get(url,source_class,headers)
            body=json.loads(response['text']);body['status']='INACTIVE'
            return snapshot(json.dumps(body),url)
    nav=NavJobs();nav.state='loaded';nav.token='test-token'
    nav.index={'example':{'one':{'url':'/api/v1/feedentry/z-new','_feed_entry':{'uuid':'one','businessName':'Example AS'}}}}
    row=core.envelope('123456789','t')
    nav.research(row,{'navn':'Example AS'},Stopped(),core.claim)
    assert not [c for c in row['claims'] if c['field']=='jobs']


def test_job_depth_waits_for_all_companies_and_stays_within_shared_budget(tmp_path):
    orgs=[str(100000000+i) for i in range(5)]
    registry=tmp_path/'registry.jsonl'
    core.write_rows(registry,[{'organisasjonsnummer':o,'navn':'Example '+o+' AS'} for o in orgs])
    class Jobs:
        max_ads=10
        max_candidate_details=4
        max_detail_requests=None
        details=0
        def __init__(self):self.calls=[];self.seen={}
        def load(self,t,cap):self.transport=t
        def research(self,row,body,t,claim):
            org=row['organisation_number'];limit=min(6,self.max_candidate_details)
            self.calls.append((org,self.max_candidate_details))
            previous=self.seen.get(org,0)
            for i in range(previous,limit):
                if self.details>=self.max_detail_requests:break
                t.reserve('https://pam-stilling-feed.nav.no/api/v1/feedentry/'+org+'-'+str(i));self.details+=1
                raw=json.dumps({'org':org,'job':i}).encode();sha=core.digest(raw);(t.root/(sha+'.bin')).write_bytes(raw)
                source={'id':sha[:24],'source_url':'https://pam-stilling-feed.nav.no/api/v1/feedentry/'+org+'-'+str(i),
                        'status':200,'source_class':'official_public_api','retrieved_at':core.now(),
                        'content_sha256':sha,'snapshot_path':'snapshots/'+sha+'.bin'}
                claim(row,'jobs',{'title':'Vacancy '+str(i),'url':'https://example.no/jobs/'+str(i)},source,{'json_pointer':'/job'})
                self.seen[org]=i+1
            row['availability']['jobs']='available'
            row.setdefault('research_sources',{})['nav_jobs']={'candidate_count':6,'detail_requests':self.seen.get(org,0),'accepted_ads':self.seen.get(org,0)}
            return []
        def report(self):return {'state':'loaded','detail_requests':self.details}
    jobs=Jobs()
    rows,report=core.run_batch(orgs,tmp_path/'output',run_id='t',requests=100,seconds=300,
                              workers=1,registry=registry,modules=('jobs',),strategy='balanced',jobs_source=jobs)
    assert report['validation']['passed']
    assert len(jobs.calls)==10
    assert all(depth==4 for _,depth in jobs.calls[:5])
    assert {org for org,_ in jobs.calls[:5]}==set(orgs)
    assert all(depth==12 for _,depth in jobs.calls[5:])
    assert all(len([c for c in row['claims'] if c['field']=='jobs'])==6 for row in rows)
    assert report['requests']==30 and report['requests']<=100
