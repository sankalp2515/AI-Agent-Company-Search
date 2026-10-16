import json, collections, hashlib, threading
from pathlib import Path
from orglens.core import read_inputs, validate, envelope, crawl_site, corroborated, soup_text, jsonld_org_ids, claim, finish, synthesize

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"out"/"audit-reproduction"
OUT.mkdir(parents=True,exist_ok=True)
def load(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def pointer(obj,path):
    for key in path.split('/')[1:]:
        key=key.replace('~1','/').replace('~0','~')
        obj=obj[int(key)] if isinstance(obj,list) else obj[key]
    return obj
def inspect(folder):
    rows=load(folder/'envelopes.jsonl');counts=collections.Counter();checks=[];sites=[]
    for r in rows:
        evidence={e['id']:e for e in r['evidence']}
        for c in r['claims']:
            counts[c['field']]+=1
            e=evidence[c['evidence_ids'][0]]
            if c['field']=='official_website':sites.append({'org':r['organisation_number'],'name':r['legal_identity'].get('legal_name'),'url':c['value'],'method':e['identity_method'],'locator':e['locator']})
            if not (c['field'].startswith('financials.') or c['field']=='legal_name'):continue
            raw=(folder/'snapshots'/(e['content_sha256']+'.bin')).read_bytes();body=json.loads(raw)
            original=pointer(body,e['locator']['json_pointer'])
            if c['field'].startswith('financials.'):
                record=body[int(e['locator']['json_pointer'].split('/')[1])]
                ok=(original==c['value']['amount'] and record.get('valuta')==c['value']['currency'] and record.get('regnskapstype')==c['value']['account_type'] and record.get('regnskapsperiode')==c['reporting_period'] and str(record['virksomhet']['organisasjonsnummer'])==r['organisation_number'])
            else:ok=(original==c['value'] and str(body.get('organisasjonsnummer'))==r['organisation_number'])
            checks.append({'org':r['organisation_number'],'claim_id':c['id'],'field':c['field'],'correct':ok})
    return {'validation':validate(rows,read_inputs(folder/'input.jsonl'),folder/'snapshots'),'companies':len(rows),'facts':sum(counts.values()),'field_counts':dict(counts),'deterministically_checked_claims':len(checks),'correct_checked_claims':sum(c['correct'] for c in checks),'incorrect_checked_claims':sum(not c['correct'] for c in checks),'financial_checks':sum(c['field'].startswith('financials.') for c in checks),'checks':checks,'websites':sites,'external_activity_companies':sum(any(c['field']=='activity' and c['value'].get('kind')!='official_registry_event' for c in r['claims']) for r in rows),'errors':sum(len(r['errors']) for r in rows)}

class Fake:
    def __init__(self,html):self.html=html;self.lock=threading.Lock();self.host_delays={}
    def get(self,url,source_class='company_owned',headers=None):
        text='' if url.endswith('robots.txt') else self.html
        return {'id':hashlib.sha256(url.encode()).hexdigest()[:24],'source_url':url,'status':404 if url.endswith('robots.txt') else 200,'source_class':source_class,'retrieved_at':'2026-10-17T00:00:00Z','content_sha256':hashlib.sha256(text.encode()).hexdigest(),'text':text,'content_type':'text/html'}
def adversarial():
    org='123456789';body={'navn':'ACME INVEST AS','hjemmeside':'https://acme.no/','organisasjonsform':{'kode':'AS'}}
    row=envelope(org,'adversarial')
    accepted=crawl_site(row,body,Fake('<h1>ACME Group</h1><meta name="description" content="We operate the entire international ACME group of companies.">'),origin='registry')
    row2=envelope(org,'adversarial')
    html='<h1>Other Parent AS</h1><footer>Org.nr 987654321</footer><script type="application/ld+json">{"@type":"Organization","name":"Acme Invest AS","taxID":"123456789"}</script><meta name="description" content="This is the unrelated parent company and all its operations.">'
    accepted2=crawl_site(row2,body,Fake(html),origin='guess',url='https://acmeinvest.no/')
    soup,text=soup_text('<h1>Acme Invest AS</h1><p>Order 2233; item 4455</p>')
    phone=corroborated({**body,'telefon':'22334455'},[(Fake('').get('https://acmeinvest.no/'),soup,text)])
    s=Fake('').get('https://acmeinvest.no/')
    old=envelope(org,'old');old['availability']={'legal_identity':'available','activity':'available','official_website':'available'}
    claim(old,'activity',{'headline':'Registry event','kind':'official_registry_event'},s,{'text_quote':'registry'})
    claim(old,'activity',{'headline':'Website news','kind':'company_owned_article'},s,{'text_quote':'news'})
    finish(old)
    new=envelope(org,'new');new['availability']={'legal_identity':'available','activity':'available','official_website':'failed'}
    claim(new,'activity',{'headline':'Registry event','kind':'official_registry_event'},s,{'text_quote':'registry'})
    finish(new,old)
    news=envelope(org,'sort')
    for headline,date in [('Older Wednesday','Wed, 01 Jan 2025 00:00:00 +0000'),('Newer Thursday','Thu, 01 Jan 2026 00:00:00 +0000')]:
        claim(news,'activity',{'headline':headline,'published_at':date,'kind':'company_owned_feed_item'},s,{'text_quote':headline})
    return {'registry_partial_name_accepts_group_site':{'accepted':accepted,'published_fields':[c['field'] for c in row['claims']],'method':row.get('website_research')},'conflicting_footer_overridden_by_jsonld':{'accepted':accepted2,'published_fields':[c['field'] for c in row2['claims']],'method':row2.get('website_research')},'non_phone_digit_fragments_pass_registered_phone':bool(phone),'long_identifier_suffix_accepted':jsonld_org_ids({'identifier':'99123456789'}),'failed_website_falsely_changes_shared_activity':{'changes':len(new['changes']),'stale_claims_retained':len(new['refresh']['last_known_claims'])},'latest_activity_date_order':synthesize(news)['text']}

result={'saved_smoke':inspect(ROOT/'submission/release/smoke'),'saved_refresh':inspect(ROOT/'submission/release/refresh'),'adversarial':adversarial()}
(OUT/'claim-audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:{a:b for a,b in v.items() if a not in ('checks','websites','field_counts')} for k,v in result.items()},indent=2))

