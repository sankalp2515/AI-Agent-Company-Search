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
