"""Measure public procurement website hints; candidate URLs still need OrgLens verification."""
import argparse
import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen

API = 'https://api.ted.europa.eu/v3/notices/search'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    orgs = [json.loads(s)['organisation_number'] for s in Path(args.input).read_text(encoding='utf-8').splitlines() if s.strip()]
    if any(not re.fullmatch('[0-9]{9}', org) for org in orgs):
        raise ValueError('Expected exact Norwegian company IDs')
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    report = {'companies_checked': len(orgs), 'requests': 0, 'notices': [], 'failures': [],
              'note': 'Search projections are discovery hints, not verified entity-to-URL facts.'}
    for offset in range(0, len(orgs), 100):
        batch = orgs[offset:offset+100]
        # Both common corporate-ID renderings. Final publication always needs exact identity verification.
        query = '(' + ' OR '.join('winner-identifier = "' + identifier + '"'
                                  for org in batch for identifier in [org, 'NO'+org]) + ')'
        page = 1
        while page <= 5:
            payload = {'query': query, 'fields': ['publication-number', 'publication-date', 'winner-identifier',
                       'winner-name', 'winner-internet-address', 'notice-title', 'links'],
                       'limit': 250, 'page': page, 'scope': 'ALL', 'checkQuerySyntax': True}
            report['requests'] += 1
            try:
                req = Request(API, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json',
                              'User-Agent': 'OrgLens-recall-experiment/1.0'})
                with urlopen(req, timeout=30) as response:
                    raw = response.read(8*1024*1024)
                (out / f'{offset}-{page}.json').write_bytes(raw)
                data = json.loads(raw)
                if data.get('timedOut'):
                    report['failures'].append({'offset': offset, 'page': page, 'error': 'upstream timedOut'})
                notices = data.get('notices', [])
                report['notices'].extend(notices)
                if len(notices) < 250:
                    break
                page += 1
            except Exception as exc:
                report['failures'].append({'offset': offset, 'page': page, 'error': str(exc)})
                break
            finally:
                time.sleep(.3)
        print('checked', min(offset+100,len(orgs)), 'notices', len(report['notices']), flush=True)
    (out / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print('requests',report['requests'],'notices',len(report['notices']),'failures',len(report['failures']))


if __name__ == '__main__':
    main()
