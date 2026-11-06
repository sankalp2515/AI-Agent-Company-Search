# Revision candidate, 6 November 2026

Based on the isolated experiment `691a1b4`. Firecrawl was used only as an answer key for research. It is not a runtime dependency, and no company-specific URL was added.

## Changes

- Fix summary wording: firm role holders no longer print as lists, legal forms and roles are in English, amounts are formatted.
- After a connection or certificate failure, try the host's `www` or bare address. Plain HTTP is tried only for domains the company declared itself.
- Add first-two-word domain guesses and stop the lone-first-word guess being cut off by the limit.
- Accept the exact legal name directly followed by the exact organisation number on a legal or contact page, only for a domain the company declared.
- Skip common Norwegian ISP mail domains as website candidates.

## Rejected

- A late retry pass: 482 requests, no sites recovered.
- Plain HTTP on guessed domains: two guessed domains served pages that Windows Defender flagged, and none produced a verified site.
- Wikidata lookup by organisation number: no hits in 300 companies.
- Accepting a registered address and managing director without the company's name: this matches sister companies.

## Validation on 300 companies unused in tuning

Versions ran one after another on 6 November, so this is not a simultaneous comparison.

| Companies with | V4 | Experiment | Revision |
|---|---:|---:|---:|
| Verified website | 32 | 35 | 37 |
| Description | 26 | 29 | 31 |
| Social links | 19 | 19 | 20 |
| Dated news | 5 | 6 | 6 |
| Active jobs | 0 | 0 | 0 |
| Requests (limit 6,000) | 2,212 | 2,573 | 2,828 |
| Seconds (limit 2,700) | 350 | 548 | 611 |

These are local counts, not official scores.

## Second round

Added after the first validation, using new companies each time:

- Read each site's own sitemap and menu to reach legal, about, article and careers pages. Articles need a date the page itself states, never a sitemap `lastmod`.
- Accept two registered officers on a domain that spells the company name.
- State year-on-year change in filed accounts in summaries.
- Add dated food safety inspections from Mattilsynet by exact organisation number.
- Broaden NAV name candidates. The ad's organisation number still decides identity.
- Retry timed-out candidates once. Reject holding pages and foreign office listings. Keep legal text out of descriptions and bylaws out of news.
- A page that cannot be read back after fetching now removes the facts that depend on it, instead of failing the whole run.

### 1,000 companies unused in any tuning

Commit `a2cf748` against submitted V4, same input, run one after the other on 6 November. Defects found in this run's added sites were then fixed, so later commits differ slightly.

| Companies with | V4 | Candidate |
|---|---:|---:|
| Verified website | 104 | 117 |
| Description | 81 | 88 |
| Social links | 67 | 72 |
| Dated news or official activity | 22 | 41 |
| Active jobs | 6 | 6 |
| Careers page | 17 | 16 |
| Any external fact | 108 | 132 |
| Requests (limit 20,000) | 7,211 | 11,283 |
| Seconds (limit 2,700) | 1,026 | 2,154 |

V4 exited with a validation failure on this machine because antivirus altered a downloaded page. The candidate exited cleanly with 15 pages dropped and recorded.

### Rejected or not adopted

- Norid domain lookups: the terms restrict permitted uses and forbid commercial use, and anonymous RDAP does not reveal holders.
- Reading every active NAV ad: 9,650 requests for 2 extra job companies across 1,600.
- Search through personal keys: 200 queries added 1 site on 300 random companies, and it cannot run officially. Some Tavily responses were unusable, so this understates search somewhat.
- Using an inspection's trade name to prove a website: it would tie a franchise chain's site to one franchisee.

Local counts, not official scores.
