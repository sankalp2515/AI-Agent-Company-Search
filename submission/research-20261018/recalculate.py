import json,gzip,collections,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=Path(__file__).resolve().parent
summary={}
for name in ('smoke','refresh','scale'):
    folder=root/'submission/release'/name
    p=folder/'envelopes.jsonl'
    lines=p.read_text(encoding='utf8').splitlines() if p.exists() else gzip.open(str(p)+'.gz','rt',encoding='utf8').read().splitlines()
    rows=[json.loads(x) for x in lines if x.strip()]
    report=json.loads((folder/'run-report.json').read_text(encoding='utf8'))
    published=collections.Counter(c['field'] for r in rows for c in r['claims'])
    jobs=sum(c['field']=='jobs' for r in rows for c in r['claims'])
    kinds=collections.Counter(c['value'].get('kind','unknown') for r in rows for c in r['claims'] if c['field']=='activity')
    news=sum(any(c['field']=='activity' and c['value'].get('kind')!='official_registry_event' for c in r['claims']) for r in rows)
    nav=(report.get('jobs_source') or {}).get('detail_requests',0)
    summary[name]={'companies':len(rows),'claims':sum(published.values()),'coverage':report['coverage'],'company_published_activity_companies':news,'activity_kinds':dict(kinds),'requests':report['requests'],'runtime_seconds':report['runtime_seconds'],'jobs_claims':jobs,'nav_detail_requests':nav,'nav_detail_share':nav/report['requests'],'nav_detail_requests_per_published_job':nav/jobs if jobs else None,'changes':sum(len(r['changes']) for r in rows),'agent_active':bool(report.get('agent')),'discovery_active':bool(report.get('discovery'))}
summary['materials']=[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in out.iterdir() if p.suffix in ('.md','.gz')]
(out/'measured-analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
