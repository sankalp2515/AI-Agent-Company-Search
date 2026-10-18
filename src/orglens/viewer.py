"""Portable evidence viewer: no CDN, no server, no unsafe interpolated HTML."""
import json
from pathlib import Path


def render(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
    path.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


TEMPLATE = r'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OrgLens Company Profiles</title>
<style>
:root{--bg:#f2f7f6;--card:#fff;--ink:#142f35;--muted:#587178;--accent:#087f69;--link:#086c78;--line:#d5e4e4;--chip:#e4f3ee;--warn:#fff1d6;--head:#113d42;--headink:#c3dfdb;--code:#f3f7f7}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0e1a1c;--card:#152528;--ink:#e2eeec;--muted:#93aaa8;--accent:#3cc6a6;--link:#6fd0dc;--line:#26403f;--chip:#1d3a33;--warn:#3a3020;--head:#0a2427;--headink:#9cc6c0;--code:#10201f}}
:root[data-theme="dark"]{--bg:#0e1a1c;--card:#152528;--ink:#e2eeec;--muted:#93aaa8;--accent:#3cc6a6;--link:#6fd0dc;--line:#26403f;--chip:#1d3a33;--warn:#3a3020;--head:#0a2427;--headink:#9cc6c0;--code:#10201f}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,sans-serif}
header{background:var(--head);color:#fff;padding:22px max(16px,calc((100vw - 1280px)/2))}header p{color:var(--headink);margin:4px 0}h1{font-size:28px;margin:0}
main{max-width:1320px;margin:20px auto;padding:0 16px}.toolbar{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
input,select,button{font:inherit;padding:10px 12px;border:1px solid var(--line);border-radius:9px;background:var(--card);color:var(--ink)}input{flex:1;min-width:180px}button{cursor:pointer}button:hover{border-color:var(--accent)}
.layout{display:grid;grid-template-columns:320px minmax(0,1fr);gap:18px}.list{max-height:80vh;overflow:auto}.item{display:block;width:100%;text-align:left;margin-bottom:8px}.item small{display:block;color:var(--muted)}.item.active{border:2px solid var(--accent)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:14px;overflow-wrap:anywhere}.eyebrow{color:var(--accent);letter-spacing:.1em;font-size:12px;font-weight:700}
h2{margin:6px 0;font-size:24px}h3{margin:0 0 10px;font-size:18px}a{color:var(--link)}pre{white-space:pre-wrap;background:var(--code);padding:10px;border-radius:8px;font-size:12.5px;max-height:320px;overflow:auto}
.chip{display:inline-block;border-radius:20px;padding:2px 10px;background:var(--chip);margin:3px;font-size:13px}.chip.unknown{background:var(--warn)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:10px 0}.kpi{border:1px solid var(--line);border-radius:10px;padding:10px}.kpi b{display:block;font-size:20px}.kpi span{color:var(--muted);font-size:13px}
.muted{color:var(--muted)}details{border-top:1px solid var(--line);padding:8px 0}summary{cursor:pointer}.cite{font-size:12px;margin-left:4px;vertical-align:super}
.rows div{border-top:1px solid var(--line);padding:8px 0}.comparison{display:grid;grid-template-columns:1fr 1fr;gap:14px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-top:1px solid var(--line);padding:6px;text-align:left}
.compare-overview{table-layout:fixed}.compare-overview th:first-child{width:28%}.compare-overview td,.compare-overview th{vertical-align:top;overflow-wrap:anywhere}.compare-overview caption{text-align:left;color:var(--muted);padding-bottom:12px}
@media(max-width:780px){.layout,.comparison{grid-template-columns:1fr}.list{max-height:240px}.card{padding:16px}h1{font-size:23px}}
</style>
<header><h1>OrgLens <span style="font-weight:300">/ Norwegian company profiles</span></h1><p>Every fact links to its source. Unknowns stay visible and are never zero.</p></header>
<main><div class="toolbar"><input id="search" aria-label="Search companies" placeholder="Search name, org number, city or industry"><select id="filter" aria-label="Filter"><option value="all">All companies</option><option value="official_website">Verified website</option><option value="jobs">Hiring (job ads)</option><option value="owned_profiles">Social profiles</option><option value="changes">Changed since last run</option></select><button id="compare">Compare (0/2)</button><button id="download">Download JSONL</button></div>
<p id="stats" class="muted"></p><div class="layout"><nav class="list" id="list" aria-label="Company results"></nav><section id="detail" aria-live="polite"></section></div></main>
<script id="data" type="application/json">__DATA__</script>
<script>
const rows=JSON.parse(document.getElementById('data').textContent),selected=new Set();let current=rows[0],comparing=false;
const el=(t,x,c)=>{const n=document.createElement(t);if(x!==undefined)n.textContent=x;if(c)n.className=c;return n};
const name=r=>r.legal_identity.legal_name||r.organisation_number;const pretty=v=>typeof v==='string'?v:JSON.stringify(v,null,2);
const claims=(r,f)=>r.claims.filter(c=>c.field===f);
function link(url,label){const a=el('a',label||url);try{const p=new URL(url);if(['http:','https:'].includes(p.protocol)){a.href=p.href;a.target='_blank';a.rel='noopener noreferrer'}}catch{}return a}
function evidence(r,ids){const box=el('span');ids.slice(0,4).forEach((id,i)=>{const e=r.evidence.find(x=>x.id===id);if(!e)return;const a=link(e.source_url,'['+(i+1)+']');a.className='cite';a.title=(e.identity_method||'')+' · retrieved '+e.retrieved_at;box.append(a)});return box}
function money(v){if(!v||typeof v.amount!=='number')return '—';return (v.currency||'')+' '+v.amount.toLocaleString('en')}
function section(title){const c=el('div',undefined,'card');c.append(el('h3',title));return c}
function profile(r){const w=el('div');const top=el('div',undefined,'card');top.append(el('div',r.organisation_number,'eyebrow'),el('h2',name(r)));
const site=claims(r,'official_website')[0];if(site)top.append(link(site.value));top.append(el('p','Researched '+r.run.completed_at+' · '+r.claims.length+' supported facts · '+r.changes.length+' changes','muted'));
const pick=el('button',selected.has(r.organisation_number)?'Remove from comparison':'Add to comparison');pick.onclick=()=>{const id=r.organisation_number;selected.has(id)?selected.delete(id):selected.size<2&&selected.add(id);document.getElementById('compare').textContent='Compare ('+selected.size+'/2)';show()};top.append(pick);w.append(top);
const sum=section('Summary');for(const s of (r.summary.statements||[])){const p=el('p',s.text);p.append(evidence(r,s.evidence_ids||[]));sum.append(p)}w.append(sum);
const fin={};for(const c of r.claims)if(c.field.startsWith('financials.'))fin[c.field.slice(11)]=c;
if(Object.keys(fin).length){const f=section('Latest filed accounts');const k=el('div',undefined,'kpis');for(const [key,label] of [['revenue','Revenue'],['operating_result','Operating result'],['annual_result','Net result'],['assets','Total assets'],['equity','Equity']])if(fin[key]){const d=el('div',undefined,'kpi');d.append(el('b',money(fin[key].value)),el('span',label));d.append(evidence(r,fin[key].evidence_ids));k.append(d)}f.append(k);const any=Object.values(fin)[0];if(any.reporting_period)f.append(el('p','Period '+(any.reporting_period.fraDato||'')+' – '+(any.reporting_period.tilDato||'')+' · '+(any.value.account_type||'')+' accounts · source: Regnskapsregisteret','muted'));w.append(f)}
const lists=[['leadership','Leadership (official register)',v=>v.name+' — '+v.role],['jobs','Active job ads',v=>v.title+(v.location?' · '+v.location:'')+(v.date_posted?' · posted '+String(v.date_posted).slice(0,10):'')],['owned_profiles','Company-linked profiles',v=>v.platform+': '+v.url],['activity','Dated activity',v=>String(v.published_at).slice(0,10)+' — '+v.headline+(v.kind==='official_registry_event'?' (registry)':'')],['locations','Registered workplaces',v=>(v.name||'')+' · '+((v.address||{}).poststed||'')],['contact','Contact',v=>v.type+': '+v.value]];
for(const [f,title,fmt] of lists){const cs=claims(r,f);if(!cs.length)continue;const s=section(title+' ('+cs.length+')');const box=el('div',undefined,'rows');cs.slice(0,25).forEach(c=>{const d=el('div');const url=c.value&&c.value.url;d.append(url?link(url,fmt(c.value)):document.createTextNode(fmt(c.value)));d.append(evidence(r,c.evidence_ids));box.append(d)});s.append(box);w.append(s)}
const st=section('Research status');for(const [k,v] of Object.entries(r.availability))st.append(el('span',k.replaceAll('_',' ')+': '+v,'chip'+(v==='available'?'':' unknown')));w.append(st);
const all=el('details',undefined,'card');all.append(el('summary','All facts with evidence locators ('+r.claims.length+')'));for(const c of r.claims){const d=el('details');d.append(el('summary',c.field.replaceAll('_',' ')),el('pre',pretty(c.value)));for(const id of c.evidence_ids){const e=r.evidence.find(x=>x.id===id);if(!e)continue;d.append(link(e.source_url,'Open source'),el('p','Retrieved '+e.retrieved_at+' · '+e.identity_method+(e.reporting_period?' · period '+pretty(e.reporting_period):''),'muted'),el('pre','SHA-256 '+e.content_sha256+'\nLocator '+pretty(e.locator)))}all.append(d)}w.append(all);
if(r.changes.length){const c=section('What changed since the previous run');for(const ch of r.changes)c.append(el('p',ch.type+': '+ch.field.replaceAll('_',' ')));c.append(el('pre',pretty(r.changes)));w.append(c)}
if(r.refresh&&(r.refresh.last_known_claims||[]).length){const c=section('Last known facts (refresh could not re-verify)');const prev=r.refresh.previous_evidence||[];const box=el('div',undefined,'rows');for(const k of r.refresh.last_known_claims){const d=el('div');d.append(el('span','Not re-verified','chip unknown'),document.createTextNode(' '+String(k.field||'').replaceAll('_',' ')+': '+(typeof k.value==='string'?k.value:JSON.stringify(k.value))));for(const id of (k.evidence_ids||[])){const e=prev.find(x=>x.id===id);if(!e)continue;const a=link(e.source_url,'previous source');a.className='cite';a.title='Retrieved '+e.retrieved_at+(e.identity_method?' · '+e.identity_method:'');d.append(document.createTextNode(' '),a)}box.append(d)}c.append(box);w.append(c)}
if(r.errors.length){const d=el('details',undefined,'card');d.append(el('summary','Research limitations ('+r.errors.length+')'),el('pre',pretty(r.errors)));w.append(d)}return w}
function comparisonOverview(pair){const box=section('Compare selected companies');const table=el('table',undefined,'compare-overview');table.append(el('caption','Filed accounts retain their reporting periods. Unknown values remain explicit.'));const head=el('tr');head.append(el('th','Information'));pair.forEach(r=>head.append(el('th',name(r))));table.append(head);
for(const [field,label] of [['official_website','Website'],['employees','Employees'],['financials.revenue','Revenue'],['financials.annual_result','Net result'],['jobs','Job ads']]){const tr=el('tr');tr.append(el('th',label));for(const r of pair){const td=el('td');const cs=claims(r,field).slice().sort((a,b)=>String(b.reporting_period?.tilDato||'').localeCompare(String(a.reporting_period?.tilDato||'')));const c=cs[0];if(c){td.append(field==='official_website'?link(c.value,'Verified website'):document.createTextNode(field.startsWith('financials.')?money(c.value):field==='jobs'?cs.length+' observed':pretty(c.value)));if(c.reporting_period)td.append(el('div',Object.entries(c.reporting_period).map(([k,v])=>k+': '+v).join(' · '),'muted'));td.append(evidence(r,c.evidence_ids||[]))}else{const family=field.startsWith('financials.')?'financials':field==='employees'?'legal_identity':field;td.append(el('span',field==='employees'?'Not established':String(r.availability[family]||'not_available').replaceAll('_',' '),'muted'))}tr.append(td)}table.append(tr)}box.append(table);return box}
function show(){const d=document.getElementById('detail');d.replaceChildren();if(comparing&&selected.size===2){const pair=rows.filter(x=>selected.has(x.organisation_number));d.append(comparisonOverview(pair));const g=el('div',undefined,'comparison');pair.forEach(r=>g.append(profile(r)));d.append(g)}else if(current)d.append(profile(current));else d.append(el('p','Select a company to see its profile.','muted'))}
function hay(r){const i=r.legal_identity;return [name(r),r.organisation_number,i.municipality||'',(i.industry||{}).beskrivelse||''].join(' ').toLowerCase()}
function list(){const q=document.getElementById('search').value.toLowerCase(),f=document.getElementById('filter').value;const m=rows.filter(r=>hay(r).includes(q)&&(f==='all'||(f==='changes'?r.changes.length>0:r.availability[f]==='available')));const n=document.getElementById('list');n.replaceChildren();
if(!m.includes(current)){current=m[0]||null;comparing=false}
if(!m.length)n.append(el('p','No companies match this search or filter.','muted'));
for(const r of m){const b=el('button',name(r),'item'+(r===current?' active':''));b.append(el('small',r.organisation_number+' · '+(r.legal_identity.municipality||'')+' · '+r.claims.length+' facts'));b.onclick=()=>{current=r;comparing=false;list();show()};n.append(b)}
const cov=f=>rows.filter(r=>r.availability[f]==='available').length;document.getElementById('stats').textContent=m.length+' of '+rows.length+' companies · websites '+cov('official_website')+' · hiring '+cov('jobs')+' · social '+cov('owned_profiles')+' · accounts '+cov('financials')}
document.getElementById('search').oninput=()=>{list();show()};document.getElementById('filter').onchange=()=>{list();show()};document.getElementById('compare').onclick=()=>{comparing=!comparing;show()};
document.getElementById('download').onclick=()=>{const u=URL.createObjectURL(new Blob([rows.map(r=>JSON.stringify(r)).join('\n')],{type:'application/x-ndjson'}));const a=el('a');a.href=u;a.download='orglens-envelopes.jsonl';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};
const h=location.hash.slice(1);if(h){const f=rows.find(r=>r.organisation_number===h);if(f)current=f}list();show();
</script></html>'''
