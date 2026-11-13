"""Measure dated, company-specific posts from WordPress's advertised REST API."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from orglens.core import Transport, availability, fetch_robots, envelope, linked_news_subject, news_date, news_url_ok, soup_text


def candidates(run):
    for line in (run / 'envelopes.jsonl').read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        site = (row.get('external_footprint', {}).get('website') or {}).get('url')
        if not site:
            continue
        snap = next((s for s in row['source_snapshots'] if s['source_url'] == site and s['status'] == 200), None)
        if not snap or not (run / snap['snapshot_path']).exists():
            continue
        parsed, _ = soup_text((run / snap['snapshot_path']).read_bytes().decode(snap.get('charset') or 'utf-8', errors='replace'))
        api = parsed.select_one('link[rel="https://api.w.org/"][href]')
        if api:
            url = urljoin(site, api['href'])
            if urlsplit(url).hostname == urlsplit(site).hostname and urlsplit(url).scheme == 'https':
                yield row, site, url


def probe(item, transport):
    row, site, url = item
    parts = urlsplit(url)
    base = f'{parts.scheme}://{parts.netloc}/'
    endpoint = url.rstrip('/') + '/wp/v2/posts?per_page=20&_fields=link,title,date,excerpt'
    org = row['organisation_number']
    result = {'organisation_number': org, 'site': site, 'posts': [], 'endpoint': endpoint}
    robot, state = fetch_robots(envelope(org, 'probe'), base, parts.hostname, transport)
    if not robot or not robot.can_fetch('OrgLens', endpoint):
        return {**result, 'status': state if not robot else 'blocked'}
    snapshot = transport.get(endpoint, 'company_owned')
    if availability(snapshot) != 'available':
        return {**result, 'status': availability(snapshot)}
    if urlsplit(snapshot['source_url']).hostname != parts.hostname:
        return {**result, 'status': 'cross_host_redirect'}
    try:
        posts = json.loads(snapshot['text'])
    except ValueError:
        return {**result, 'status': 'invalid'}
    if not isinstance(posts, list):
        return {**result, 'status': 'invalid'}
    existing = {str(c['value'].get('url', '')).rstrip('/') for c in row['claims'] if c['field'] == 'activity'}
    body = {'navn': row['legal_identity'].get('legal_name'), 'naeringskode1': row['legal_identity'].get('industry')}
    for post in posts:
        title = soup_text(post.get('title', {}).get('rendered', ''))[1]
        lead = soup_text(post.get('excerpt', {}).get('rendered', ''))[1]
        href = post.get('link', '')
        date = news_date(post.get('date'))
        if date and href.rstrip('/') not in existing and news_url_ok(href, site) and linked_news_subject(body, title, lead):
            result['posts'].append({'title': title, 'date': date, 'url': href, 'lead': lead[:650]})
    return {**result, 'status': 'available', 'prior_news': bool(existing - {''})}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('runs', nargs='+', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    items = {}
    for run in args.runs:
        for item in candidates(run):
            items.setdefault(item[0]['organisation_number'], item)
    transport = Transport(args.output / 'snapshots', requests=500, seconds=240)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda item: probe(item, transport), items.values()))
    report = {'candidates': len(items), 'requests': transport.requests,
              'companies_with_new_posts': sum(bool(r['posts']) for r in results),
              'new_posts': sum(len(r['posts']) for r in results), 'results': results}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print({k: v for k,v in report.items() if k != 'results'})


if __name__ == '__main__':
    main()
