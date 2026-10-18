"""Compare discoveries with Builderr's historical public profiles, never score qualification.

Reference is the DATA array from https://www.builderr.ai/signalpost. It is an
independent historical opportunity set, not a current exact-identity adjudicator.
Do not silently remove missed opportunities or call host agreement identity proof.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit,parse_qs


def url_key(url):
    p = urlsplit(str(url or ''))
    host=(p.hostname or '').lower().removeprefix('www.')
    path=p.path.rstrip('/')
    identity_query=tuple(parse_qs(p.query).get('id',[])) if host=='facebook.com' and path=='/profile.php' else ()
    return host,path,identity_query


def compare(rows, reference):
    refs = {str(r['org']): r for r in reference}
    if len({r['organisation_number'] for r in rows}) != len(rows):
        raise ValueError('Duplicate output company')
    sites, socials, mismatches, novel, descriptions = [], [], [], [], 0
    for row in rows:
        org = row['organisation_number']
        ref = refs[org]
        web = ref.get('web') or {}
        value = web.get('value') or {}
        claims = row['claims']
        found_sites = [c['value'] for c in claims if c['field'] == 'official_website']
        found_social = {url_key(c['value'].get('url')) for c in claims if c['field'] == 'owned_profiles'}
        wanted_social = {url_key(s['url']) for s in value.get('social_links', []) if s.get('url')}
        # A BRREG API URL on a not_found observation is not a positive website.
        expected = web.get('source') if web.get('status') == 'available' else None
        if expected and value:
            match = any(url_key(u)[0] == url_key(expected)[0] for u in found_sites)
            sites.append(match)
            if found_sites and not match:
                mismatches.append({'org': org, 'expected_historical_url': expected, 'found': found_sites,
                                   'review_required': 'May be a legitimate change, parent, directory, or wrong entity; inspect evidence.'})
        elif found_sites:
            novel.append({'org': org, 'found': found_sites})
        if wanted_social:
            socials.append({'company_covered': bool(found_social & wanted_social),
                            'matched': len(found_social & wanted_social), 'positive': len(wanted_social)})
        descriptions += any(c['field'] == 'description' for c in claims)
    def metric(companies, covered, facts, matched):
        return {'positive_companies': companies, 'covered_companies': covered,
                'reference_facts': facts, 'matched_facts': matched,
                'company_recall': covered/companies if companies else None,
                'fact_recall': matched/facts if facts else None,
                '70_30_recall': .7*covered/companies+.3*matched/facts if companies and facts else None}
    return {'kind': 'historical_public_opportunity_comparison', 'companies': len(rows),
            'website_host_agreement': metric(len(sites), sum(sites), len(sites), sum(sites)),
            'social_url_agreement': metric(len(socials), sum(s['company_covered'] for s in socials),
                                          sum(s['positive'] for s in socials), sum(s['matched'] for s in socials)),
            'description_companies_unscored': descriptions, 'website_mismatches_to_review': mismatches,
            'new_websites_to_review': novel, 'overall_score': None, 'official_recall_out_of_50': None,
            'qualification': 'not_determined',
            'limitations': ['Historical public sample is enriched and may be stale or misattributed.',
                           'URL agreement is not independent proof of source ownership or factual precision.',
                           'No current labels for news, jobs, descriptions, locations or reviews; no aggregate recall invented.',
                           'Official reference union, family weights, budgets, synthesis and UX ratings are unavailable.']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--envelopes', required=True)
    p.add_argument('--reference', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    rows = [json.loads(s) for s in Path(args.envelopes).read_text(encoding='utf-8').splitlines() if s.strip()]
    result = compare(rows, json.loads(Path(args.reference).read_text(encoding='utf-8')))
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
