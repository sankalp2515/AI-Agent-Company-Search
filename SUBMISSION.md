# Signalpost submission — OrgLens version 4

Prepared 4 November 2026. It builds on version 3 (`e5d5a01`, Builderr's audit of version 2) and an independent review of version 3 ([docs/REVIEW-V3-2026-11-04.md](docs/REVIEW-V3-2026-11-04.md)).

| Required item | Value |
| --- | --- |
| Agent | OrgLens — evidence-first Norwegian company research |
| Repository | https://github.com/sankalp2515/AI-Agent-Company-Search |
| Exact commit | Recorded in the submission email (the commit that adds this file's version 4 text) |
| Install | `uv sync --frozen` |
| One command | `uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --strategy balanced --pages 8 --requests-per-company 20 --max-seconds 2700` |
| Frozen registry | Append `--bulk <registry file>`. `--registry` is the same option. `--registry-retrieved-at <timestamp>` is optional; without it, the file's own time is recorded and labelled as such. |
| Models / search | None. The command is keyless. Optional `--discover` / `--extract-ai` modes exist but are not used. |
| APIs | Brønnøysundregistrene (Enhetsregisteret entities, roles, subunits; Regnskapsregisteret accounts), NAV Job Vacancy Feed (published public token), and verified company websites under robots.txt |
| Licences | MIT application; beautifulsoup4/soupsieve MIT; certifi MPL-2.0; data-source terms in [SOURCE-RIGHTS.md](SOURCE-RIGHTS.md) |
| Cost | $0 external API cost |
| Contact | Sankalp Wanjari — wanjarisankalp@gmail.com |

## Changes in version 4

| Gap found in version 3 | Change |
| --- | --- |
| A parent group's site could pass for a subsidiary that shares its brand word (e.g. "Fjordbakst Group" listing "Fjordbakst Vest AS" on its contact page) | Weaker proofs (an organisation number on a sub-page, or name plus registered phone or address) now also require the homepage's title, heading or site name to name this company, unless the domain spells its full name. |
| Feed items could be contact pages, other companies' articles or items without an article link | One acceptance rule for every news path (feeds, article markup, news-page items, dated cards): an individual article on the verified site, never a section index, feed or static page. |
| A radio station's local stories were counted as news about the station | For broadcasters, newspaper publishers and news agencies (by registered industry code), only items that name the company count. |
| An agency's Facebook link in a "website made by" credit could be published as the company's | Links in a site-credit line are dropped; the company's own links in the same footer are kept. |
| The NAV job-ads feed never finished (0 of 6 time slices), so every job check was `failed` | Time slices share one page pool (up to 160 pages); the full feed now loads in about 80 pages and 83 requests. |
| One shared word ("eiendom") triggered NAV ad lookups, wasting requests and marking companies `failed` | Ads are looked up only for strong matches: same organisation number, near-identical spelling, or an employer name containing every word of ours. A complete feed with no match is an honest `not_available`. |
| Website research ran before NAV employer homepages were known | A short second website pass uses those homepages for companies still without a site. |

Every change has a regression test, plus a positive test so real company facts are still kept.

## Verification (local, not an official score)

All runs used the exact command above, with no keys: 20 requests per company and 2,700 seconds.

| Run | Valid | Requests used / allowed | Runtime | Website | Social links | News | Careers page | Job checks complete | Contact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100-company smoke (seed 20261005) | 100/100 | 822 / 2,000 | 670 s | 9 | 4 | 2 | 1 | 100/100 | 39 |
| Live refresh of the same 100 | 100/100 | 828 / 2,000 | 360 s | 9 | 4 | 2 | 1 | 100/100 | 39 |
| 300-company sample (seed 20261103) | 300/300 | 2,182 / 6,000 | 605 s | 32 | 14 | 1 | 6 | 300/300 | 106 |

- **Job-ads feed:** loaded completely (6/6 time slices, about 8,100 active ads) in every run. No company in these random samples had an active NAV ad, so job postings are 0 and every job check reads `not_available`, not `failed`.
- **Refresh:** 0 material changes.
- **Runtime:** almost all of it is website fetching, and it varies with the network: 468 s for the 100-company smoke and 333 s for the 300 sample. The run report now records seconds per stage.
- **Tests:** 174 pass.
- **Evidence:** every verified website and news item was reviewed by hand. News comes from Infrabeam, Maurvangen and Melbye, all dated posts on their own sites.
- **Artifacts:** in `submission/release/` (smoke, refresh, and 300-company profiles with viewer). Raw snapshots stay local.

## Open questions for Builderr

- Which commit is active for the next run.
- One rejected or ignored example each for social links, news and jobs, to confirm the evaluator reads `external_footprint` or the claims as intended.
- The organisation numbers of the 15 companies whose summaries called 2024 the latest year, to confirm that version 4 now handles them.
