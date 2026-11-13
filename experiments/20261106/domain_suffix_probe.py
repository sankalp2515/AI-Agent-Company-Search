"""Try name-derived domains that include the legal suffix, then verify the site."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

from orglens.core import Transport, crawl_site, envelope
from orglens.names import name_tokens, resolves


def inputs(runs):
    seen = set()
    for run in runs:
        for line in (run / 'envelopes.jsonl').read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            org = row['organisation_number']
            if org in seen or any(c['field'] == 'official_website' for c in row['claims']):
                continue
            seen.add(org)
            entity = next((s for s in row['source_snapshots'] if s['status'] == 200 and s['source_url'].endswith('/enheter/' + org)), None)
            if not entity or not (run / entity['snapshot_path']).exists():
                continue
            body = json.loads((run / entity['snapshot_path']).read_bytes())
            words = name_tokens(body.get('navn'))
            if (body.get('organisasjonsform') or {}).get('kode') != 'AS' or not 1 <= len(words) <= 3:
                continue
            label = ''.join(words)
            if not 4 <= len(label) <= 40:
                continue
            tried = {urlsplit(c['url']).hostname for c in row.get('website_research', {}).get('candidates', [])}
            urls = [f'https://{label}as.no/', f'https://{label}-as.no/']
            yield row, body, [u for u in urls if urlsplit(u).hostname not in tried]


def main():
    import sys
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    items = list(inputs([Path(p) for p in sys.argv[2:]]))
    transport = Transport(output / 'snapshots', requests=900, seconds=480, timeout=7)
    def verify(item):
        original, body, urls = item
        org = original['organisation_number']
        row = envelope(org, 'legal-suffix-probe')
        row['claims'] = [c for c in original['claims'] if c['field'] == 'leadership']
        attempted = []
        for url in urls:
            if resolves(url):
                attempted.append(url)
                if crawl_site(row, body, transport, 6, origin='name_guess', url=url):
                    break
        return {'org': org, 'name': body.get('navn'), 'resolving': attempted,
                'verified': row.get('website_research', {}).get('verification'),
                'errors': row['errors'], 'envelope': row if row.get('website_research', {}).get('verification') else None}
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(verify, items))
    report = {'eligible_companies': len(items), 'hypotheses': sum(len(item[2]) for item in items),
              'requests': transport.requests, 'companies_with_resolving_domain': sum(bool(r['resolving']) for r in results),
              'verified': [r for r in results if r['verified']],
              'unsuccessful': [r for r in results if r['resolving'] and not r['verified']]}
    (output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print({k: (len(v) if isinstance(v, list) else v) for k, v in report.items()})


if __name__ == '__main__':
    main()
