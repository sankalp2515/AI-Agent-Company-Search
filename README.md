<div align="center">

# OrgLens

**Evidence-first company research for Norway. Every input gets a result. Every published fact has a source.**

[![Checks](https://github.com/sankalp2515/AI-Agent-Company-Search/actions/workflows/check.yml/badge.svg)](https://github.com/sankalp2515/AI-Agent-Company-Search/actions/workflows/check.yml)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

[Quick start](#install-clean-machine) · [Evidence viewer](#evidence-viewer) · [Architecture](docs/ARCHITECTURE.md) · [Independent audit](docs/SUBMISSION-AUDIT-2026-10-17.md) · [Submission](SUBMISSION.md) · [Contributing](CONTRIBUTING.md)

</div>

> **Submission status, 17 October 2026: FIX BEFORE SUBMISSION.** A fresh 100-company test completes, but adversarial tests expose exact-company matching and refresh defects. See the [audit and prioritized fixes](docs/SUBMISSION-AUDIT-2026-10-17.md). Passing CI and smoke tests do not establish qualification.

Evidence-first research agent for Norwegian companies. Give it a batch of organisation numbers. For each company it returns one terminal envelope with:

- legal identity
- filed accounts
- leadership and workplaces
- a verified website, company-linked social profiles and contact details
- active job ads and dated activity
- refresh changes

Every claim carries a source URL, retrieval time, SHA-256 of the exact response bytes, an evidence locator and an identity method. Unknowns are explicit states (`available`, `not_available`, `blocked`, `not_applicable`, `ambiguous`, `failed`) and are never turned into zero.

The default command needs **no API keys and has $0 external API cost**.

## Install (clean machine)

Requires Python 3.12+ and uv.

```sh
python -m pip install uv==0.10.9
uv sync --frozen
```

## One evaluator command

```sh
uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --max-requests 2000 --max-seconds 2700
```

- Input: JSONL objects with `organisation_number`, a JSON array, or a text file with one number per line. Batch size is inferred from the input.
- Budgets: `--max-requests` and `--max-seconds` constrain HTTP requests. The values above are conservative historical test settings, **not confirmed current official limits**. Builderr supplies the official budget. A larger batch makes research shallower; returning all envelopes does not mean every company received complete research. DNS and final output processing are not strictly bounded by the HTTP deadline.
- Frozen registry snapshot: if Builderr supplies one, append `--registry registry.jsonl --registry-retrieved-at <actual timestamp>`. This saves one request per company.
- Refresh: append `--previous out/evaluation/envelopes.jsonl`. Changes are computed on field/value sets, so an unchanged source never produces a false change. If a refresh fails, the previous claims are kept and marked stale.

Outputs in `--output`:

- `envelopes.jsonl`: one result per input, in input order.
- `run-report.json`: coverage, states, requests, p50/p95 runtime, identity methods and job-feed statistics.
- `snapshots/`: immutable response bytes, addressed by hash.
- `index.html`: a self-contained viewer for desktop and mobile. It supports search, filters, comparing two companies and downloading the JSON. Every sentence and fact links to its source.

```sh
uv run --frozen orglens validate --input input.jsonl --envelopes out/evaluation/envelopes.jsonl --snapshots out/evaluation/snapshots
uv run --frozen pytest -q
```

## How the agent researches a company

The agent runs in phases. Each phase covers every company before the next phase starts, so early companies cannot use up the budget.

1. **Identity anchor.** Enhetsregisteret, or the frozen snapshot, supplies the legal name, form, industry, address, employees, founding date, registered activity, share capital, phone, group membership and dated registry events. All of this comes from one response.
2. **Official records.** Regnskapsregisteret supplies the latest filed accounts, keeping period, currency and account type. Roles supply leadership. Subunits supply workplaces.
3. **Jobs: NAV Job Vacancy Feed.** The official feed of Norway's public job board is indexed once per run, using parallel date segments. Ads whose employer name matches the company or one of its workplaces are fetched. An ad is published only if its employer organisation number equals the company, or belongs to a workplace that Enhetsregisteret lists as the company's subunit.
4. **Website ladder.** Candidates are tried in order:
   1. the registry-declared homepage
   2. the employer homepage from an orgnr-verified NAV ad
   3. the website verified in the previous run
   4. name-derived domain hypotheses, checked by DNS first

   A candidate is published only with an exact identity proof:
   - a labelled organisation number or the `NO … MVA` VAT format on the homepage, in the footer, or on the company's own contact/about page;
   - or a JSON-LD organisation identifier;
   - or the full-name domain or full legal name, together with the registered phone, the registered address, or a person listed in the company's official roles.

   These candidates are always rejected:
   - directories and platforms
   - pages showing a conflicting organisation number
   - property-manager sites for housing associations
5. **Site facts** come only from verified sites, under robots.txt. They are the description (meta, OpenGraph or JSON-LD), public brand, outbound social profile links, email and phone, JSON-LD job postings, RSS/Atom items, JSON-LD articles, and dated items on news pages.
6. **Synthesis.** A fixed set of templates builds a cited narrative: what the company does, its latest filed numbers (profit or loss, negative equity), leaders, footprint, hiring, latest activity, changes since the last run and what remains unknown. Every statement lists its evidence IDs. No model writes facts.

Optional `--ai` mode (model-directed search with Tavily) from the earlier version is still available. It needs personal keys and is not part of the evaluator command.

The identity rules above describe the intended behavior. The audit reproduced weaker registry/name and JSON-LD paths in the current implementation; they must be corrected before claiming reliable exact-entity attribution.

## Evidence viewer

Every completed run writes `index.html` next to its JSONL results. Open that local file in a browser. The repository includes a [100-company example](submission/release/smoke/index.html); GitHub displays its source, so download it to use the viewer.

- Search companies by name, organisation number, city or industry.
- Filter for verified websites, hiring, linked profiles and changes.
- Select two companies and compare their profiles.
- Follow cited sources and inspect retrieval dates, evidence locators and hashes.
- Inspect explicit unknown states, stale facts and reported changes; export JSONL.

The viewer contains responsive CSS and needs no server, JavaScript framework, CDN or API key. Desktop/mobile interactions have **not** been verified in the 17 October audit because the browser automation connection failed. A UI exists; full UX points are not established.

## Fresh verification (17 October 2026)

| Check | Observed result |
|---|---|
| Fresh random batch, seed 20261017 | 100 inputs / 100 valid terminal envelopes |
| Runtime / HTTP requests / external API charge | 139.984 seconds / 673 / $0 |
| Websites / descriptions / companies with jobs | 6 / 4 / 1 |
| Companies with company-published activity / linked social profiles | 2 / 5 |
| Legal-name and financial claims checked against source bytes | 1,408 correct of 1,408 checked; 3,669 total claims |
| Regression tests | 49 passed locally, in a clean checkout, and in Linux CI |

The checked claims cover 38.4% of this run's claims and do not establish the correctness of unreviewed external facts. [Audit evidence](submission/audit-20261017/) includes the run report, claim checks and reproducible adversarial cases. No official score is claimed.

## Measured results (live, 16 October 2026)

| Run | Companies | Valid | Requests | Runtime | Website | Description | Social | Jobs | Activity | Contact |
|---|---|---|---|---|---|---|---|---|---|---|
| 100-company smoke (seed 20261005) | 100 | yes | 736 | 145 s | 10 | 8 | 4 | 0 | 100 | 39 |
| Live refresh of the same 100 | 100 | yes | 737 | 137 s | 10 | 8 | 4 | 0 | 100 | 39 |
| 1,000-company scale (seed 20261006) | 1,000 | yes | 6,548 | 22 min | 147 | 92 | 100 | 4 | 999 | 414 |
| Previous version, same 100 | 100 | yes | 635 | 363 s | 1 | 1 | 0 | 0 | 0 | 0 |

In the 1,000-company run, identity, accounts, roles and workplaces are 1,000 / 998 / 999 / 1,000. The 147 websites were verified by:

- labelled organisation number: 41
- registered role holder named on a full-name domain: 55
- legal name plus registered phone: 25
- legal name plus registered address: 14
- registry declaration: 9
- JSON-LD identifier: 2
- NAV employer homepage: 1

- **Refresh:** 0 changes against the previous run, so the false-change rate is 0.
- **Smoke-test websites:** all 10 published websites were reviewed by hand. One property-manager match found during development was removed, and that case is now a regression test.
- **NAV jobs on a hiring sample:** across 40 universe companies whose name appears among active NAV employers, 36 received exact-orgnr-verified job ads. Only about 1–2 % of random companies advertise on NAV, which is why the random smoke batch shows 0.
- **Financials, leadership and locations:** the smoke batch has an available state for each; the scale batch has 998 / 999 / 1,000 respectively. An available state can represent an empty successful endpoint response and is not fact-level recall.
- Release artifacts are in `submission/release/`: the smoke, refresh and scale runs, each with a viewer and run report, plus test results and SHA-256 hashes.

These are operational measurements, not Builderr's score: the official checked collection is not available locally.

## Repository map

- `src/orglens/core.py`: transport, identity anchor, official records, website ladder, site extraction, synthesis, refresh and validation.
- `src/orglens/navjobs.py`: the NAV job-feed connector.
- `src/orglens/names.py`: name normalisation, domain hypotheses and the directory blocklist.
- `src/orglens/viewer.py`: the portable viewer.
- `tests/`: 49 regression tests covering wrong-company gates, missing-vs-zero, evidence integrity, refresh, URL safety and viewer injection safety.
- `scripts/package_release.py`: validates runs and packages `submission/release/` with only evidence-referenced snapshots.

See [SUBMISSION.md](SUBMISSION.md), [SOURCE-RIGHTS.md](SOURCE-RIGHTS.md) and [LIMITATIONS.md](LIMITATIONS.md).

## Documentation

| Document | Purpose |
|---|---|
| [Current audit](docs/SUBMISSION-AUDIT-2026-10-17.md) | Readiness verdict, measured evidence, defects and next steps |
| [Architecture](docs/ARCHITECTURE.md) | Active command path, storage and optional AI mode |
| [Submission checklist](SUBMISSION.md) | Candidate commit, command, costs, contact and unsent email |
| [Source rights](SOURCE-RIGHTS.md) | Source access, licences, caches and provider disclosure |
| [Security](SECURITY.md) | URL controls, credentials and known security boundaries |
| [Data schema](DATA_SCHEMA.md) | Envelope and evidence model |
| [Limitations](LIMITATIONS.md) | Coverage and operational limitations |
| [Changelog](CHANGELOG.md) | Implementation and audit milestones |

Earlier build reports and `submission/artifacts` / `submission/ai-artifacts` describe historical versions. The default candidate is the deterministic v2 implementation; optional model-assisted runs are separate evidence.

MIT-licensed application code. Third-party data and snapshots retain their original rights. Maintainer: Sankalp Wanjari, wanjarisankalp@gmail.com.
