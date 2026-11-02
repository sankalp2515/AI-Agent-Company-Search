# Signalpost submission — OrgLens version 3

Prepared 3 November 2026 in response to Builderr's audit of version 2 (`84223ae`).

| Required item | Value |
| --- | --- |
| Agent | OrgLens — evidence-first Norwegian company research |
| Repository | https://github.com/sankalp2515/AI-Agent-Company-Search |
| Exact commit | `e5d5a013512d8c4535f469dc3a361dc629a01571` (verified from a clean GitHub clone: locked install, 164 tests, keyless run with `--bulk`; Linux CI green) |
| Install | `uv sync --frozen` |
| One command | `uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --strategy balanced --pages 8 --requests-per-company 20 --max-seconds 2700` |
| Frozen registry | Append `--bulk <registry file>`. `--registry` is the same option. `--registry-retrieved-at <timestamp>` is optional; without it, the file's own time is recorded and labelled as such. |
| Models / search | None. The command is keyless. Optional `--discover` / `--extract-ai` modes exist but are not used. |
| APIs | Brønnøysundregistrene (Enhetsregisteret entities, roles, subunits; Regnskapsregisteret accounts), NAV Job Vacancy Feed (published public token), and verified company websites under robots.txt |
| Licences | MIT application; beautifulsoup4/soupsieve MIT; certifi MPL-2.0; data-source terms in [SOURCE-RIGHTS.md](SOURCE-RIGHTS.md) |
| Cost | $0 external API cost |
| Contact | Sankalp Wanjari — wanjarisankalp@gmail.com |

## How each audit point is addressed

| Builderr feedback | Change in version 3 |
| --- | --- |
| Fit 2,000 requests per 100 companies | `--requests-per-company 20` sets the cap from the batch size. The NAV job index is capped at 60 pages, so it can't starve company research. |
| 2024 called latest when 2025 existed | Summaries use one newest period (company accounts preferred) and never mix years or account types. If the register lists a newer filing than the accounts API returned, the summary says so explicitly. |
| Not a parent group's website | Weaker proofs (legal name plus phone or address, or an org number on a sub-page) now also require a domain carrying the company's name. Group or portfolio pages are rejected, so their social accounts, news and jobs are never published. |
| Real, dated news only | Dates must be publication dates; a feed's `updated` is not used. Contact, privacy and terms pages are never news. One-word or menu items, future dates and items older than three years are dropped. Dates are normalised to ISO, and the raw value is kept in the evidence. |
| No social, news or jobs seen | Every envelope now has a plainly named `external_footprint` section: `website`, `social_links`, `news`, `job_postings`, `careers_page` and `description`, each linked to its evidence. Social links must belong to the company, which excludes web-agency credits and unrelated accounts. Careers pages linked from the verified site are published. WordPress sites' post feeds are read. |
| Registry file | `--bulk` is accepted, and the retrieval timestamp is optional. |

## Verification (local, not an official score)

All runs used the exact command above, with no keys: 20 requests per company and 2,700 seconds.

| Run | Valid | Requests used / allowed | Runtime | Website | Social links | News | Careers page | Description | Contact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100-company smoke (seed 20261005) | 100/100 | 969 / 2,000 | 250 s | 9 | 4 | 2 | 1 | 8 | 39 |
| Live refresh of the same 100 | 100/100 | 965 / 2,000 | 246 s | 9 | 4 | 2 | 1 | 8 | 39 |
| Fresh 300-company sample (seed 20261103) | 300/300 | 2,598 / 6,000 | 553 s | 32 | 14 | 2 | 6 | 25 | 106 |

- **Refresh:** 0 changes and 0 false stale facts. Accounts, roles and workplaces are returned for every company.
- **Tests:** 164 pass.
- **Evidence:** every verified website and every news item in the 300 sample was reviewed by hand. News items are dated posts from the last three years; static and menu pages are excluded.
- **Artifacts:** in `submission/release/` (smoke, refresh, and 300-company profiles with viewer). Raw snapshots stay local.
