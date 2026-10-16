# OrgLens

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
- Budgets: `--max-requests` and `--max-seconds` are hard caps shared by every HTTP request. The values above match the published daily limits (2,000 outbound requests, 45 minutes). The agent spreads its remaining budget across the companies still waiting, so a larger batch makes each company's research shallower; the run never drops a company.
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
- **Financials, leadership and locations:** every company is covered from official records.
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
