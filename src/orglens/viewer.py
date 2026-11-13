"""Portable evidence viewer: one file, no CDN, no server, no unsafe interpolated HTML.

The research is embedded gzip-compressed (about an eighth of the raw size) and unpacked by the browser.
Every figure carries a mark that opens its source: where it came from, when, the exact place in the
source, why it is the right company, and a fingerprint of the saved bytes.
"""
import base64
import gzip
import json
from pathlib import Path

DROP_ROW = ("source_snapshots", "research_sources", "website_research")
DROP_EVIDENCE = ("snapshot_id", "extraction_method")


def compact(row):
    """What the page needs. The complete envelopes stay in envelopes.jsonl beside it."""
    out = {key: value for key, value in row.items() if key not in DROP_ROW}
    out["evidence"] = [{key: value for key, value in item.items() if key not in DROP_EVIDENCE} for item in row.get("evidence", [])]
    if isinstance(row.get("refresh"), dict):
        out["refresh"] = {key: value for key, value in row["refresh"].items() if key != "previous_snapshots"}
    return out


def render(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    packed = json.dumps([compact(row) if isinstance(row, dict) else row for row in rows], ensure_ascii=False, separators=(",", ":"))
    encoded = base64.b64encode(gzip.compress(packed.encode("utf-8"), 9)).decode("ascii")
    path.write_text(PAGE.replace("__PACKED__", encoded), encoding="utf-8")


def _ascii_script(page):
    """Write the script's non-ASCII characters as \\u escapes, valid in JS strings and regexes."""
    head, _, rest = page.rpartition("<script>")
    code, _, tail = rest.partition("</script>")
    code = "".join(ch if ord(ch) < 128 else f"\\u{ord(ch):04x}" for ch in code)
    return head + "<script>" + code + "</script>" + tail


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Signalpost · OrgLens company research</title>
<meta name="description" content="Norwegian company research where every figure links back to its source.">
<style>
:root{--paper:#FBFCFA;--water:#DCECF1;--shoal:#C3DFE8;--land:#F4E8C3;--card:#FFFFFF;--ink:#0E2A36;--muted:#48626D;--line:#B4CAD2;--mark:#B0146A;--good:#0B6B57;--warn:#8A5A00;--bad:#B3261E;--hatch:#9DB9C2;
--sans:"Schibsted Grotesk","Inter","Segoe UI",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,"Cascadia Mono",Consolas,monospace;--note:"Newsreader",Georgia,"Times New Roman",serif}
:root[data-theme="night"]{--paper:#071821;--water:#0C2632;--shoal:#123746;--land:#2B2918;--card:#0B202A;--ink:#E6F0F2;--muted:#9CB6BF;--line:#25495A;--mark:#FF86BE;--good:#5FD0B5;--warn:#E6B85C;--bad:#F2938B;--hatch:#3C6070}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 var(--sans);-webkit-font-smoothing:antialiased}
a{color:inherit}button,input,select{font:inherit;color:inherit}:focus-visible{outline:2px solid var(--mark);outline-offset:2px}
.skip{position:absolute;left:-999px}.skip:focus{left:12px;top:12px;background:var(--card);padding:8px;z-index:50}
.wrap{max-width:1240px;margin:0 auto;padding:0 20px}.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}.note{font-family:var(--note);font-style:italic;color:var(--muted)}
.eyebrow{font:500 11.5px/1.2 var(--mono);letter-spacing:.11em;text-transform:uppercase;color:var(--muted)}
header.top{border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--paper);z-index:20}
.bar{display:flex;align-items:center;gap:12px;height:58px}.logo{display:flex;gap:9px;align-items:center;font-weight:800;font-size:18px;letter-spacing:-.02em}
.bar .sp{flex:1}.btn{border:1px solid var(--line);background:var(--card);border-radius:3px;min-height:40px;padding:0 13px;cursor:pointer;font-size:14px}
.btn.ink{background:var(--ink);color:var(--paper);border-color:var(--ink);font-weight:700}.btn:hover{border-color:var(--ink)}
.hero{display:grid;grid-template-columns:1.15fr 1fr;gap:36px;align-items:end;padding:40px 0 18px}
h1{font-size:clamp(38px,6.4vw,84px);line-height:.95;letter-spacing:-.045em;font-weight:800;margin:10px 0 0}h1 em{font-family:var(--note);font-weight:400;letter-spacing:-.02em;color:var(--mark)}
.lede{color:var(--muted);font-size:17px;margin:0 0 14px;max-width:52ch}
.search{display:flex;gap:8px;flex-wrap:wrap}.search input{flex:1;min-width:200px;height:54px;border:1.5px solid var(--ink);background:var(--card);border-radius:3px;padding:0 14px;font-size:17px}
.search select{height:54px;border:1px solid var(--line);background:var(--card);border-radius:3px;padding:0 10px}
.chart{position:relative;border:1px solid var(--ink);background:var(--water);height:min(52vh,470px);min-height:330px;margin-top:8px;overflow:hidden}
.chart svg{position:absolute;inset:0;width:100%;height:100%}.chart .frame{position:absolute;inset:7px;border:1px solid var(--ink);pointer-events:none}
.snd{font:500 11px var(--mono);fill:var(--ink);opacity:.82;cursor:pointer;text-anchor:middle}.snd.ring{opacity:.5}.snd.dim{opacity:.1}.snd:hover,.snd:focus{opacity:1;fill:var(--mark);font-size:15px}
.axis{font:500 10px var(--mono);letter-spacing:.1em;fill:var(--muted)}.contour{fill:none;stroke:var(--shoal);stroke-width:1.2}
.legend{position:absolute;left:78px;bottom:84px;background:var(--card);border:1px solid var(--ink);padding:9px 11px;max-width:240px;font-size:12.5px;line-height:1.35}
.tip{position:absolute;pointer-events:none;background:var(--card);border:1px solid var(--ink);border-left:3px solid var(--mark);padding:9px 11px;font-size:13px;display:none;z-index:5;min-width:210px}
.stats{display:flex;gap:30px;flex-wrap:wrap;padding:14px 0 6px;color:var(--muted);font-size:13px}.stats b{display:block;font:500 22px var(--mono);color:var(--ink)}
.layout{display:grid;grid-template-columns:330px minmax(0,1fr);gap:26px;padding:26px 0 40px;align-items:start}
.rule{border-top:1px solid var(--ink);padding-top:10px;display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.list{max-height:78vh;overflow:auto;border-top:1px solid var(--ink)}
.item{display:grid;grid-template-columns:34px 1fr;gap:10px;align-items:center;width:100%;text-align:left;background:none;border:0;border-bottom:1px solid var(--line);padding:10px 4px;cursor:pointer}
.item:hover{background:var(--card)}.item.active{background:var(--land)}.item b{display:block;font-weight:700;font-size:15px;letter-spacing:-.01em}.item small{display:block;color:var(--muted);font:12px var(--mono)}
.ring path{fill:none;stroke:var(--line);stroke-width:4}.ring path.m{stroke:var(--mark)}.ring path.f{stroke:var(--ink)}
.panelbox{border:1px solid var(--ink);background:var(--card);padding:24px;margin-bottom:18px;overflow-wrap:anywhere}
.pname{font-size:clamp(30px,4.6vw,54px);font-weight:800;letter-spacing:-.04em;line-height:1;margin:8px 0 6px}
.meta{font:500 13px var(--mono);color:var(--muted)}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.glance{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));border-top:1px solid var(--ink);margin-top:18px}
.glance>div{padding:12px 12px 12px 0;border-bottom:1px solid var(--line)}.glance label{display:block;font-size:12px;color:var(--muted)}.glance .v{font:500 18px var(--mono);letter-spacing:-.02em}
.up{color:var(--good)}.down{color:var(--bad)}.delta{font:500 12px var(--mono)}
h3{font-size:22px;letter-spacing:-.03em;margin:0 0 10px}
.fix{display:inline-grid;place-items:center;width:28px;height:28px;margin:-6px 0 -6px 1px;vertical-align:middle;border:0;background:none;cursor:pointer;position:relative;padding:0}
.fix::before{content:"";width:13px;height:13px;border:1.6px solid var(--mark);border-radius:50%;transition:transform .16s}.fix::after{content:"";position:absolute;width:3.5px;height:3.5px;border-radius:50%;background:var(--mark)}
.fix:hover::before{transform:scale(1.35)}
table{border-collapse:collapse;width:100%}th,td{padding:9px 7px;border-bottom:1px solid var(--line);text-align:right;font:14px var(--mono);vertical-align:top}
th:first-child,td:first-child{text-align:left;font-family:var(--sans);font-weight:500}thead th{font:500 11.5px var(--mono);color:var(--muted);border-bottom:1px solid var(--ink)}
.tablebox{overflow-x:auto}.neg{color:var(--bad)}
.rows>div{border-bottom:1px solid var(--line);padding:9px 0}.rows small{color:var(--muted);font:12px var(--mono)}
.unsv{background:repeating-linear-gradient(135deg,transparent 0 6px,var(--hatch) 6px 7px);border:1px dashed var(--muted);padding:10px}
.unsv ul{margin:0;padding:0;list-style:none}.unsv li{background:var(--card);display:inline-block;margin:3px;padding:3px 8px;font-size:14px}.unsv b{font:500 11px var(--mono);letter-spacing:.1em;margin-right:6px}
.chip{display:inline-block;font:500 11px var(--mono);letter-spacing:.06em;text-transform:uppercase;padding:3px 7px;border:1px solid var(--line);margin:2px;background:var(--card)}
.chip.ok{border-color:var(--good);color:var(--good)}.chip.unknown{border-style:dashed}
details{border-top:1px solid var(--line);padding:8px 0}summary{cursor:pointer}pre{white-space:pre-wrap;font:12px var(--mono);background:var(--paper);padding:8px;max-height:280px;overflow:auto}
.cmp .bar2{height:9px;background:var(--ink);margin-top:4px}.cmp .bar2.loss{background:repeating-linear-gradient(135deg,var(--bad) 0 3px,transparent 3px 6px);border:1px solid var(--bad)}
.cmp td.a{text-align:right}.cmp td.a .bar2{margin-left:auto}.cmp td.b{text-align:left}.cmp th.l{text-align:center;font:500 11px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.cmp caption{text-align:left;color:var(--muted);padding-bottom:10px;font-size:14px}.cmp td{width:42%}
#panel{position:fixed;top:0;right:0;bottom:0;width:min(440px,100vw);background:var(--card);border-left:3px solid var(--mark);padding:24px;overflow:auto;z-index:40;transform:translateX(100%);transition:transform .22s;box-shadow:none}
#panel.open{transform:none}#panel .big{font:500 28px var(--mono);letter-spacing:-.03em;margin:4px 0 6px;overflow-wrap:anywhere}
#panel dt{font:500 11px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-top:13px}#panel dd{margin:3px 0 0;overflow-wrap:anywhere}
footer{border-top:1px solid var(--ink);padding:20px 0 50px;color:var(--muted);font-size:13px}
@media(max-width:860px){.hero{grid-template-columns:1fr;gap:14px;padding-top:24px}.layout{grid-template-columns:1fr}.list{max-height:300px}.legend{display:none}
#panel{top:auto;left:0;right:0;width:auto;max-height:78vh;border-left:0;border-top:3px solid var(--mark);transform:translateY(100%)}.panelbox{padding:16px}.cmp td{font-size:12.5px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style></head>
<body><a class="skip" href="#detail">Skip to the company</a>
<header class="top"><div class="wrap bar"><div class="logo"><svg width="24" height="24" viewBox="0 0 26 26" aria-hidden="true"><circle cx="13" cy="13" r="8.5" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="13" cy="13" r="2.4" fill="#B0146A"/><path d="M13 0v5M13 21v5M0 13h5M21 13h5" stroke="currentColor" stroke-width="1.8"/></svg>Signalpost</div>
<span class="sp"></span><button class="btn" id="compare">Compare (0/2)</button><button class="btn" id="export">Export list (CSV)</button><button class="btn" id="download">Download JSONL</button><button class="btn" id="theme" aria-label="Switch between day and night chart">NIGHT</button></div></header>
<main class="wrap">
<section class="hero"><div><div class="eyebrow">Norwegian companies · charted from public sources</div><h1>Every fact has a <em>way back.</em></h1></div>
<div><p class="lede">Find a company, compare two, and press the magenta mark beside any figure to see exactly where it came from. What nobody could confirm stays marked as unsurveyed.</p>
<div class="search"><input id="search" aria-label="Search companies" placeholder="Name, organisation number, town or industry"><select id="filter" aria-label="Filter"><option value="all">All companies</option><option value="official_website">Verified website</option><option value="jobs">Hiring now</option><option value="activity">Dated news or activity</option><option value="owned_profiles">Social profiles</option><option value="changes">Changed since last run</option></select></div></div></section>
<div class="chart" id="chart" aria-label="Chart of companies by founding year and revenue. Each number is a company's employee count."></div>
<p id="stats" class="stats" aria-live="polite"></p>
<div class="layout"><div><div class="rule"><span class="eyebrow">Find</span><span class="note">website first, then depth</span></div><nav class="list" id="list" aria-label="Company results"></nav></div>
<section id="detail" aria-live="polite" tabindex="-1"></section></div>
<footer>Research by OrgLens. Every figure links to its source with retrieval time, reporting period and why it belongs to this company. Contains data under the Norwegian Licence for Open Government Data (NLOD) made available by Brønnøysundregistrene, and data from Mattilsynet and NAV.</footer></main>
<aside id="panel" role="dialog" aria-label="Source of a fact" aria-modal="false"></aside>
<script id="packed" type="application/octet-stream">__PACKED__</script>
<script>
const $id=id=>document.getElementById(id);
const el=(t,x,c)=>{const n=document.createElement(t);if(x!==undefined)n.textContent=x;if(c)n.className=c;return n};
let rows=[],current=null,comparing=false,lastMark=null;const selected=new Set();
const FAM=[['official_website','Website'],['owned_profiles','Profiles'],['activity','News'],['description','Description'],['jobs','Job ads'],['financials','Accounts'],['leadership','Leadership'],['locations','Workplaces'],['contact','Contact']];
const REASON={not_available:'We looked and found nothing.',blocked:'The source refused the request.',ambiguous:'Not sure it is the right company, so nothing is published.',failed:'The check failed on this run.',not_applicable:'Does not apply to this company.'};
const FORMS={Aksjeselskap:'Limited company',Allmennaksjeselskap:'Public limited company',Borettslag:'Housing cooperative',Eierseksjonssameie:'Condominium association',Stiftelse:'Foundation',Samvirkeforetak:'Cooperative','Forening/lag/innretning':'Association',Enkeltpersonforetak:'Sole proprietorship','Norskregistrert utenlandsk foretak':'Norwegian branch of a foreign company'};
const form=f=>f?(FORMS[f]?FORMS[f]+' ('+f+')':f):'';
const name=r=>(r.legal_identity&&r.legal_identity.legal_name)||r.organisation_number;
const nice=s=>String(s).toLowerCase().replace(/(^|[\s\-/(&.])([a-zæøåäöü])/g,(m,a,b)=>a+b.toUpperCase()).replace(/\b(As|Asa|Sa|Ans|Da|Nuf|Ba|Sti|Ks|Iks)\b/g,w=>w.toUpperCase());
const fmtOrg=o=>String(o).replace(/(\d{3})(\d{3})(\d{3})/,'$1 $2 $3');
const claims=(r,f)=>(r.claims||[]).filter(c=>c.field===f);
const evOf=(r,id)=>{if(!r._ev){r._ev={};for(const e of r.evidence||[])r._ev[e.id]=e}return r._ev[id]};
function money(v){if(!v||typeof v.amount!=='number')return '—';return (v.currency||'NOK')+' '+v.amount.toLocaleString('en')}
function short(n){const a=Math.abs(n);return (n<0?'−':'')+(a>=1e9?(a/1e9).toFixed(1)+' bn':a>=1e6?(a/1e6).toFixed(1)+' m':a>=1e3?Math.round(a/1e3)+' k':String(a))}
function link(url,label){const a=el('a',label||url);try{const p=new URL(url);if(['http:','https:'].includes(p.protocol)){a.href=p.href;a.target='_blank';a.rel='noopener noreferrer'}}catch(e){}return a}
const pretty=v=>typeof v==='string'?v:JSON.stringify(v,null,2);
function where(loc){loc=loc||{};if(loc.json_pointer)return 'Field '+loc.json_pointer+' in the register record';if(loc.text_quote)return 'Page text: “'+String(loc.text_quote).slice(0,200)+'”';if(loc.link_href)return 'Link on the page: '+loc.link_href;if(loc.declared_by)return 'Website field in '+loc.declared_by;if(loc.csv_key)return 'Row '+loc.csv_key+'='+loc.csv_value+' in the published file';return pretty(loc).slice(0,240)}
const METHOD={official_organisation_endpoint:'Looked up by organisation number in the official register',labelled_organisation_number:"The company's site shows this exact organisation number",legal_name_and_registered_address:'The site shows the full legal name and the registered address',legal_name_and_registered_phone:'The site shows the full legal name and the registered phone number',registry_declared_homepage:'The official register lists this site for the company',jsonld_organisation_identifier:"The site's structured data declares this organisation number",full_name_domain_and_registered_operating_head:"The domain spells the full name and the site names the registered managing director",verified_company_site:"Found on the company's verified website",official_record_exact_orgnr:'Official record filed under this exact organisation number',official_record_registered_subunit:"Official record for one of the company's registered workplaces"};
function mark(r,c,label){const b=el('button',undefined,'fix');b.setAttribute('aria-label','Check the source of '+label);b.onclick=()=>openPanel(r,c,label,b);return b}
function openPanel(r,c,label,origin){const p=$id('panel');if(!p)return;lastMark=origin;p.replaceChildren();const e=evOf(r,(c.evidence_ids||[])[0])||{};
const close=el('button','Close','btn');close.onclick=closePanel;p.append(close,el('div','⊙ Position confirmed','eyebrow'),el('div',label+' · '+nice(name(r)),'note'));
const v=c.value;p.append(el('div',typeof v==='object'&&v&&typeof v.amount==='number'?money(v):typeof v==='string'?v:(v&&(v.headline||v.title||v.name||v.url))||pretty(v),'big'));
const dl=el('dl');const row=(k,x)=>{if(x){dl.append(el('dt',k),el('dd',x))}};
row('Where it came from',e.source_url?new URL(e.source_url).hostname.replace(/^www\./,''):'');row('Retrieved',(e.retrieved_at||'').replace('T',' ').slice(0,16)+' UTC');
const per=c.reporting_period||e.reporting_period;if(per&&per.tilDato)row('Reporting period',(per.fraDato||'')+' to '+per.tilDato);else if(per&&per.published_at)row('Published',per.published_at);
row('Exact place in the source',where(e.locator));row('Why this is the right company',METHOD[e.identity_method]||c.identity_method||e.identity_method);row('Fingerprint of the saved source',(e.content_sha256||'').slice(0,16));
p.append(dl);if(e.source_url){const a=link(e.source_url,'Open the original source ↗');a.className='btn ink';a.setAttribute('style','display:inline-flex;align-items:center;margin-top:18px;text-decoration:none');p.append(a)}
p.className='open';close.focus&&close.focus()}
function closePanel(){const p=$id('panel');if(p){p.className='';if(lastMark&&lastMark.focus)lastMark.focus()}}
document.onkeydown=e=>{if(e.key==='Escape')closePanel();if(e.key==='/'&&document.activeElement!==$id('search')){e.preventDefault&&e.preventDefault();$id('search').focus&&$id('search').focus()}};
function ring(r){const k=['official_website','owned_profiles','activity','description','jobs','financials','leadership','locations'];let s='<svg class="ring" width="30" height="30" viewBox="0 0 36 36" aria-hidden="true">';
k.forEach((f,i)=>{const a0=(i*45-85)*Math.PI/180,a1=((i+1)*45-95)*Math.PI/180,R=13,on=(r.availability||{})[f]==='available';s+='<path class="'+(on?(i<5?'m':'f'):'')+'" d="M'+(18+R*Math.cos(a0)).toFixed(1)+' '+(18+R*Math.sin(a0)).toFixed(1)+' A13 13 0 0 1 '+(18+R*Math.cos(a1)).toFixed(1)+' '+(18+R*Math.sin(a1)).toFixed(1)+'"/>'});return s+'</svg>'}
function section(title,note){const c=el('div',undefined,'panelbox');const h=el('div',undefined,'rule');h.append(el('h3',title));if(note)h.append(el('span',note,'note'));c.append(h);return c}
function years(r){const by={};for(const c of r.claims||[])if(c.field.startsWith('financials.')&&c.reporting_period&&c.reporting_period.tilDato){const y=c.reporting_period.tilDato.slice(0,4);(by[c.field.slice(11)]=by[c.field.slice(11)]||{})[y]=c}return by}
function spark(series){const ys=Object.keys(series).sort();if(ys.length<2)return null;const v=ys.map(y=>series[y].value.amount),mn=Math.min(...v),mx=Math.max(...v),sp=mx-mn||1;
const pts=v.map((x,i)=>[4+i*(66/(v.length-1)),18-(x-mn)/sp*14]);const s=el('span');s.innerHTML='<svg width="74" height="22" viewBox="0 0 74 22" aria-hidden="true"><path d="M'+pts.map(p=>p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' L')+'" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="'+pts.at(-1)[0].toFixed(1)+'" cy="'+pts.at(-1)[1].toFixed(1)+'" r="2.6" fill="#B0146A"/></svg>';return s}
function profile(r){const w=el('div');const i=r.legal_identity||{};const top=el('div',undefined,'panelbox');
top.append(el('div','Company research · '+String((r.run||{}).completed_at||'').slice(0,10),'eyebrow'),el('div',nice(name(r)),'pname'));
top.append(el('div',[fmtOrg(r.organisation_number),form((i.legal_form||{}).beskrivelse),i.municipality&&nice(i.municipality),i.founded_on&&'founded '+String(i.founded_on).slice(0,4)].filter(Boolean).join(' · '),'meta'));
const fy=years(r),glance=el('div',undefined,'glance');const latest=f=>{const s=fy[f];if(!s)return null;const ys=Object.keys(s).sort();return [s[ys.at(-1)],ys.length>1?s[ys.at(-2)]:null,ys.at(-1)]};
for(const [f,label] of [['revenue','Revenue'],['annual_result','Net result']]){const l=latest(f);if(!l)continue;const d=el('div');d.append(el('label',label+' '+l[2]));const v=el('span',short(l[0].value.amount),'v');if(l[0].value.amount<0)v.className='v neg';d.append(v,mark(r,l[0],label+' '+l[2]));
if(l[1]&&l[1].value.amount){const ch=(l[0].value.amount-l[1].value.amount)/Math.abs(l[1].value.amount)*100;d.append(el('div',(ch>=0?'+':'−')+Math.abs(ch).toFixed(1)+'% on '+(+l[2]-1),'delta '+(ch>=0?'up':'down')))}glance.append(d)}
const emp=claims(r,'employees')[0];if(emp){const d=el('div');d.append(el('label','Employees'),el('span',String(emp.value),'v'),mark(r,emp,'Employees'));glance.append(d)}
const site=claims(r,'official_website')[0];const sd=el('div');sd.append(el('label','Website'));if(site){sd.append(link(site.value,site.value.replace(/^https?:\/\/(www\.)?/,'').replace(/\/$/,'')+' ↗'),mark(r,site,'Website'))}else sd.append(el('span','unsurveyed','note'));glance.append(sd);
const jobs=claims(r,'jobs');const jd=el('div');jd.append(el('label','Job ads'),el('span',jobs.length?String(jobs.length):'none found','v'));glance.append(jd);top.append(glance);
const acts=el('div',undefined,'actions');const pick=el('button',selected.has(r.organisation_number)?'Remove from comparison':'Add to comparison','btn ink');
pick.onclick=()=>{const id=r.organisation_number;selected.has(id)?selected.delete(id):selected.size<2&&selected.add(id);$id('compare').textContent='Compare ('+selected.size+'/2)';if(selected.size===2)comparing=true;show()};acts.append(pick);
acts.append(link('https://data.brreg.no/enhetsregisteret/oppslag/enheter/'+r.organisation_number,'Official register ↗'));top.append(acts);w.append(top);
const sum=section('In brief','every sentence traces to a source');for(const s of (r.summary||{}).statements||[]){const p=el('p',s.text);const c={value:s.text,evidence_ids:s.evidence_ids||[]};if((s.evidence_ids||[]).length)p.append(mark(r,c,'this statement'));sum.append(p)}
const unk=((r.summary||{}).unknowns||[]);if(unk.length)sum.append(el('p','Still unknown: '+unk.map(u=>String(u.field||u).replaceAll('_',' ')).join(', ')+'.','note'));w.append(sum);
if(Object.keys(fy).length){const f=section('Filed accounts','NOK · newest first');const allY=[...new Set(Object.values(fy).flatMap(s=>Object.keys(s)))].sort().reverse().slice(0,4);const box=el('div',undefined,'tablebox');const t=el('table');const hd=el('tr');hd.append(el('th','Account item'),el('th','Trend'));allY.forEach(y=>hd.append(el('th',y)));const th=el('thead');th.append(hd);t.append(th);const tb=el('tbody');
for(const [k,label] of [['revenue','Revenue'],['operating_result','Operating result'],['annual_result','Net result'],['assets','Total assets'],['equity','Equity']]){if(!fy[k])continue;const tr=el('tr');tr.append(el('td',label));const sc=el('td');const sp=spark(fy[k]);if(sp)sc.append(sp);tr.append(sc);
allY.forEach(y=>{const td=el('td');const c=fy[k][y];if(c){const s=el('span',c.value.amount.toLocaleString('en'));if(c.value.amount<0)s.className='neg';td.append(s,mark(r,c,label+' '+y))}else td.append(el('span','not filed','note'));tr.append(td)});tb.append(tr)}t.append(tb);box.append(t);f.append(box);w.append(f)}
const lists=[['activity','News and official activity',v=>[v.headline||'',String(v.published_at||'').slice(0,10)],v=>v.url],['jobs','Hiring',v=>[v.title,[v.location,v.date_posted&&'posted '+String(v.date_posted).slice(0,10)].filter(Boolean).join(' · ')],v=>v.url],['owned_profiles','On the web',v=>[v.platform,v.url],v=>v.url],['description',"In the company's own words",v=>[typeof v==='string'?v:(v.text||pretty(v)),''],v=>null],['leadership','People',v=>[v.name,v.role],v=>null],['locations','Registered workplaces',v=>[v.name||'',((v.address||{}).poststed)||''],v=>null],['contact','Contact',v=>[v.value,v.type],v=>null]];
const missing=[];for(const [f,title,fmt,url] of lists){const cs=claims(r,f);if(!cs.length){const st=(r.availability||{})[f];if(st&&st!=='available')missing.push([title,st]);continue}
const s=section(title,cs.length+(cs.length===1?' item':' items'));const box=el('div',undefined,'rows');cs.slice(0,25).forEach(c=>{const d=el('div');const [a,b]=fmt(c.value||{});const u=url(c.value||{});d.append(u?link(u,a):el('span',a),mark(r,c,title));if(b)d.append(el('small',' '+b));box.append(d)});s.append(box);w.append(s)}
if(missing.length){const u=el('div',undefined,'panelbox');u.append(el('h3','Unsurveyed'));const box=el('div',undefined,'unsv');const ul=el('ul');missing.forEach(([t,st])=>{const li=el('li');li.append(el('b',t.toUpperCase()),document.createTextNode(REASON[st]||st));ul.append(li)});box.append(ul);u.append(box);w.append(u)}
const st=section('What we checked','last checked '+String((r.run||{}).completed_at||'').slice(0,10));for(const [k,label] of FAM){const v=(r.availability||{})[k];if(v)st.append(el('span',label+': '+v.replaceAll('_',' '),'chip'+(v==='available'?' ok':' unknown')))}w.append(st);
if(r.refresh&&(r.refresh.last_known_claims||[]).length){const c=el('div',undefined,'panelbox');c.append(el('h3','Last known facts (refresh could not re-verify)'));const prev=r.refresh.previous_evidence||[];const box=el('div',undefined,'rows');
for(const k of r.refresh.last_known_claims){const d=el('div');d.append(el('span','Not re-verified','chip unknown'),document.createTextNode(' '+String(k.field||'').replaceAll('_',' ')+': '+(typeof k.value==='string'?k.value:JSON.stringify(k.value))));for(const id of (k.evidence_ids||[])){const e=prev.find(x=>x.id===id);if(!e)continue;const a=link(e.source_url,'previous source');a.title='Retrieved '+e.retrieved_at;d.append(document.createTextNode(' '),a)}box.append(d)}c.append(box);w.append(c)}
if((r.changes||[]).length){const c=section('What changed since the previous run');for(const ch of r.changes)c.append(el('p',ch.type+': '+ch.field.replaceAll('_',' ')));w.append(c)}
const all=el('details',undefined,'panelbox');all.append(el('summary','Every fact with its evidence ('+(r.claims||[]).length+')'));for(const c of (r.claims||[]).slice(0,400)){const d=el('details');d.append(el('summary',c.field.replaceAll('_',' ')),el('pre',pretty(c.value)));for(const id of c.evidence_ids||[]){const e=evOf(r,id);if(!e)continue;d.append(link(e.source_url,'Open source'),el('pre','Retrieved '+e.retrieved_at+'\nIdentity '+(e.identity_method||'')+'\nSHA-256 '+e.content_sha256+'\nLocator '+pretty(e.locator)))}all.append(d)}w.append(all);
if((r.errors||[]).length){const d=el('details',undefined,'panelbox');d.append(el('summary','Research limitations ('+r.errors.length+')'),el('pre',pretty(r.errors)));w.append(d)}return w}
function comparisonOverview(pair){const box=section('Compare','both bars in a row share one scale');const t=el('table',undefined,'cmp');t.append(el('caption','Filed accounts keep their reporting periods. Unknown values stay explicit.'));
const head=el('tr');const ha=el('th',nice(name(pair[0])));ha.setAttribute('style','text-align:right;font:800 19px var(--sans);letter-spacing:-.02em');const hb=el('th',nice(name(pair[1])));hb.setAttribute('style','text-align:left;font:800 19px var(--sans);letter-spacing:-.02em');head.append(ha,el('th','',' l'),hb);t.append(head);
const latest=(r,f)=>claims(r,f).slice().sort((a,b)=>String(b.reporting_period&&b.reporting_period.tilDato||'').localeCompare(String(a.reporting_period&&a.reporting_period.tilDato||'')))[0];
for(const [field,label] of [['financials.revenue','Revenue'],['financials.operating_result','Operating result'],['financials.annual_result','Net result'],['financials.assets','Total assets'],['financials.equity','Equity'],['employees','Employees'],['official_website','Website'],['owned_profiles','Linked profiles'],['activity','News and activity'],['jobs','Job ads']]){
const cs=pair.map(r=>latest(r,field));const cur=cs.map(c=>c&&c.value&&typeof c.value==='object'?c.value.currency:null);const same=!cur[0]||!cur[1]||cur[0]===cur[1];
const nums=cs.map(c=>!same?null:c&&c.value&&typeof c.value==='object'&&typeof c.value.amount==='number'?c.value.amount:c&&typeof c.value==='number'?c.value:null);const scale=Math.max(1,...nums.filter(n=>n!==null).map(Math.abs));
const tr=el('tr');pair.forEach((r,ix)=>{const td=el('td',undefined,ix?'b':'a');const c=cs[ix];if(c){if(['owned_profiles','activity','jobs'].includes(field))td.append(document.createTextNode(claims(r,field).length+' found'));else if(field==='official_website')td.append(link(c.value,c.value.replace(/^https?:\/\/(www\.)?/,'').replace(/\/$/,'')));else td.append(el('span',field.startsWith('financials.')?money(c.value):pretty(c.value),nums[ix]<0?'neg':undefined));
td.append(mark(r,c,label));if(c.reporting_period&&c.reporting_period.tilDato)td.append(el('div',(c.reporting_period.fraDato||'')+' to '+c.reporting_period.tilDato,'note'));
if(nums[ix]!==null){const b=el('div',undefined,'bar2'+(nums[ix]<0?' loss':''));b.setAttribute('style','width:'+Math.max(2,Math.abs(nums[ix])/scale*100).toFixed(1)+'%');td.append(b)}}
else{const fam=field.startsWith('financials.')?'financials':field==='employees'?'legal_identity':field;const stt=String((r.availability||{})[fam]||'not_available');td.append(el('span','unsurveyed · '+stt.replaceAll('_',' '),'note'))}
if(ix===0){tr.append(td);const lb=el('th',label,'l');if(!same)lb.append(el('div','other currency','note'));tr.append(lb)}else tr.append(td)});t.append(tr)}const tb=el('div',undefined,'tablebox');tb.append(t);box.append(tb);return box}
function show(){const d=$id('detail');d.replaceChildren();if(comparing&&selected.size===2){const pair=rows.filter(x=>selected.has(x.organisation_number));d.append(comparisonOverview(pair));if(location)location.hash='compare='+pair.map(x=>x.organisation_number).join(',')}
else if(current){d.append(profile(current));if(location)location.hash=current.organisation_number}else d.append(el('p','Select a company to see its profile.','note'))}
function hay(r){if(!r._hay){const i=r.legal_identity||{};r._hay=[name(r),r.organisation_number,i.municipality||'',(i.industry||{}).beskrivelse||''].join(' ').toLowerCase();r._hay2=r._hay.replace(/ø/g,'o').replace(/æ/g,'ae').replace(/å/g,'a')}return r._hay}
function matches(){const q=($id('search').value||'').toLowerCase().trim(),f=$id('filter').value||'all';const q2=q.replace(/ø/g,'o').replace(/æ/g,'ae').replace(/å/g,'a');
return rows.filter(r=>(hay(r).includes(q)||r._hay2.includes(q2))&&(f==='all'||(f==='changes'?(r.changes||[]).length>0:(r.availability||{})[f]==='available')))}
function list(){const m=matches();const n=$id('list');n.replaceChildren();if(!m.includes(current)){current=m[0]||null;comparing=false}
if(!m.length)n.append(el('p','No companies match this search or filter.','note'));
for(const r of m){const b=el('button',undefined,'item'+(r===current?' active':''));const rg=el('span');rg.innerHTML=ring(r);const tx=el('span');tx.append(el('b',nice(name(r))),el('small',fmtOrg(r.organisation_number)+' · '+nice((r.legal_identity||{}).municipality||'')+' · '+(r.claims||[]).length+' facts'));b.append(rg,tx);b.onclick=()=>{current=r;comparing=false;list();show();$id('detail').focus&&$id('detail').focus()};n.append(b)}
const cov=f=>rows.filter(r=>(r.availability||{})[f]==='available').length;const facts=rows.reduce((s,r)=>s+(r.claims||[]).length,0);
$id('stats').textContent=m.length+' of '+rows.length+' companies shown · '+facts.toLocaleString('en')+' facts, each with a source · '+cov('official_website')+' verified websites · '+cov('jobs')+' hiring · '+cov('financials')+' with filed accounts';dim(m)}
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function chart(){const box=$id('chart');if(!box||!box.getBoundingClientRect)return;const W=box.clientWidth,H=box.clientHeight,padL=70,padR=22,padT=24,band=58,padB=32,y0=H-padB-band;
const x=(yr,j)=>yr<1970?padL+(j%23)*0.9:padL+22+(Math.min(2026,yr)-1970)/56*(W-padL-padR-22);const y=v=>y0-(Math.log10(Math.max(1e4,Math.min(5e10,v)))-4)/(10.7-4)*(y0-padT);
let h='<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none"><defs><pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="var(--hatch)" stroke-width="1.4"/></pattern></defs>';
for(let i=0;i<6;i++){const yy=padT+36+i*(y0-padT)/6;let d='M0 '+yy;for(let px=0;px<=W;px+=W/8)d+=' S'+(px-W/16)+' '+(yy+Math.sin(i*1.7+px/190)*22)+' '+px+' '+(yy+Math.cos(i+px/260)*15);h+='<path class="contour" d="'+d+'"/>'}
h+='<rect x="0" y="'+(y0+8)+'" width="'+W+'" height="'+band+'" fill="url(#hatch)"/><text class="axis" x="'+(padL+8)+'" y="'+(y0+24)+'">UNSURVEYED · NO REVENUE FILED</text>';
[1970,1980,1990,2000,2010,2020].forEach(v=>h+='<text class="axis" x="'+x(v,0)+'" y="'+(H-12)+'" text-anchor="middle">'+(v===1970?'≤1970':v)+'</text>');
[[1e5,'100 K'],[1e6,'1 M'],[1e7,'10 M'],[1e8,'100 M'],[1e9,'1 BN']].forEach(([v,l])=>h+='<text class="axis" x="18" y="'+(y(v)+3)+'">'+l+'</text>');
const taken=new Set(),cells=(px,py,w)=>{const o=[];for(let gx=Math.floor((px-w/2)/6);gx<=Math.floor((px+w/2)/6);gx++)for(let gy=Math.floor((py-9)/6);gy<=Math.floor(py/6);gy++)o.push(gx+','+gy);return o};
const small=W<640;const pts=rows.map((r,i)=>[r,i]).filter((_,i)=>!small||i%2===0).sort((a,b)=>((b[0].legal_identity||{}).employees||0)-((a[0].legal_identity||{}).employees||0));
for(const [r,i] of pts){const id=r.legal_identity||{};const rev=(years(r).revenue||{});const ys=Object.keys(rev).sort();const amount=ys.length?rev[ys.at(-1)].value.amount:null;const yr=+String(id.founded_on||'').slice(0,4)||2000;let hs=0;for(const ch of r.organisation_number)hs=(hs*31+ch.charCodeAt(0))%997;
const px=x(yr,hs)+(hs%11-5),py=amount>0?y(amount):y0+20+(hs%(band-26));const label=id.employees?String(id.employees):'',w=label.length*6.8+2,cs=label?cells(px,py,w):[];const fits=label&&cs.every(k=>!taken.has(k));if(fits)cs.forEach(k=>taken.add(k));
h+='<text class="snd'+(fits?'':' ring')+'" data-i="'+i+'" x="'+px.toFixed(1)+'" y="'+py.toFixed(1)+'">'+(fits?esc(label):'∘')+'</text>'}
box.innerHTML=h+'</svg><div class="frame"></div><div class="legend"><b class="eyebrow">How to read this chart</b><br>Each number is one company: its employee count, placed by founding year and revenue. Press one to open it.</div><div class="tip" id="tip"></div>';
const svg=box.querySelector('svg'),tip=$id('tip');svg.onclick=e=>{const t=e.target.closest('.snd');if(!t)return;current=rows[+t.dataset.i];comparing=false;list();show();$id('detail').scrollIntoView({behavior:'smooth'})};
svg.onmousemove=e=>{const t=e.target.closest('.snd');if(!t){tip.style.display='none';return}const r=rows[+t.dataset.i],id=r.legal_identity||{};const rev=(years(r).revenue||{});const ys=Object.keys(rev).sort();
tip.innerHTML='<b>'+esc(nice(name(r)))+'</b><br><span class="mono">'+esc(nice(id.municipality||''))+' · founded '+esc(String(id.founded_on||'').slice(0,4))+'</span><br>'+(ys.length?'Revenue NOK '+esc(short(rev[ys.at(-1)].value.amount)):'<i>No revenue filed</i>')+' · '+esc(id.employees||'no')+' employees<br><i>'+(r.claims||[]).length+' facts, each with a source</i>';
tip.style.display='block';const b=box.getBoundingClientRect();let lx=e.clientX-b.left+14,ly=e.clientY-b.top+14;if(lx+240>W)lx-=260;if(ly+110>H)ly-=120;tip.style.left=lx+'px';tip.style.top=ly+'px'};svg.onmouseleave=()=>tip.style.display='none';dim(matches())}
function dim(m){const box=$id('chart');if(!box||!box.querySelectorAll)return;const keep=new Set(m.map(r=>rows.indexOf(r)));const all=m.length===rows.length;box.querySelectorAll('.snd').forEach(t=>t.classList.toggle('dim',!all&&!keep.has(+t.dataset.i)))}
function start(data){rows=data;rows.sort((a,b)=>((b.availability||{}).official_website==='available')-((a.availability||{}).official_website==='available')||(b.claims||[]).length-(a.claims||[]).length);current=rows[0]||null;
const h=(location&&location.hash||'').slice(1);if(h.startsWith('compare=')){h.slice(8).split(',').forEach(o=>rows.some(r=>r.organisation_number===o)&&selected.add(o));if(selected.size===2){comparing=true;$id('compare').textContent='Compare (2/2)'}}else if(h){const f=rows.find(r=>r.organisation_number===h);if(f)current=f}
list();show();chart();if(typeof addEventListener==='function')addEventListener('resize',()=>chart())}
$id('search').oninput=()=>{list();show()};$id('filter').onchange=()=>{list();show()};$id('compare').onclick=()=>{comparing=!comparing&&selected.size===2;show()};
if($id('export'))$id('export').onclick=()=>{const q=v=>'"'+String(v==null?'':v).replace(/"/g,'""')+'"';const head=['organisation_number','name','municipality','industry','website','latest_revenue_nok','employees','facts'];
const lines=[head.join(',')].concat(matches().map(r=>{const i=r.legal_identity||{};const rev=years(r).revenue||{};const ys=Object.keys(rev).sort();const site=claims(r,'official_website')[0];return [r.organisation_number,name(r),i.municipality||'',(i.industry||{}).beskrivelse||'',site?site.value:'',ys.length?rev[ys.at(-1)].value.amount:'',i.employees||'',(r.claims||[]).length].map(q).join(',')}));
const u=URL.createObjectURL(new Blob(['﻿'+lines.join('
')],{type:'text/csv'}));const a=el('a');a.href=u;a.download='signalpost-companies.csv';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};
$id('download').onclick=()=>{const a=el('a');a.href='envelopes.jsonl';a.download='envelopes.jsonl';a.click()};
const R=document.documentElement;if(R){try{if(localStorage.getItem('sp-theme')==='night')R.dataset.theme='night'}catch(e){}}
if($id('theme'))$id('theme').onclick=()=>{if(!R)return;const n=R.dataset.theme==='night';R.dataset.theme=n?'':'night';$id('theme').textContent=n?'NIGHT':'DAY';try{localStorage.setItem('sp-theme',n?'day':'night')}catch(e){}};
const packed=$id('packed');
if(packed&&typeof DecompressionStream!=='undefined'){const bin=Uint8Array.from(atob(packed.textContent.trim()),c=>c.charCodeAt(0));new Response(new Blob([bin]).stream().pipeThrough(new DecompressionStream('gzip'))).text().then(t=>start(JSON.parse(t)))}
else if(packed){$id('detail').append(el('p','This browser cannot unpack the research. Open envelopes.jsonl beside this page, or use a current browser.','note'))}
else start(JSON.parse($id('data').textContent));
</script></body></html>'''


PAGE = _ascii_script(TEMPLATE)
