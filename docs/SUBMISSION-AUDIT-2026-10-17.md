# Signalpost independent submission audit — 17 October 2026

## 1. Executive Verdict

**FIX BEFORE SUBMISSION. Competition tier: NOT QUALIFIED / not yet qualification-competitive.** No official run has established 65/100. There is no defensible overall score from the available reference data. The highest-severity blocker is a demonstrated path that assigns a parent/group website to the requested legal entity. These are adversarial reproductions, not a proven wrong-company publication in the live sample.

Strongest demonstrated capability: reproducible official-data extraction, complete batch envelopes and verifiable source bytes. Largest competitive gap: sparse verified external discovery. A fresh 100-company run found six websites, four descriptions, one company with jobs and two with company-published activity.

Audited executable commit: **`a6cc772f9d367e3115af97374ab72e22180f3208`**. Pending work was committed and pushed first. Subsequent audit/documentation changes do not change `src/`, dependencies or the agent tests. Maintainer and contact: **Sankalp Wanjari — wanjarisankalp@gmail.com**. Agent name: **OrgLens**.

## 2. Rules & Version Verification

Retrieved current organizer [challenge page](https://www.builderr.ai/challenges/signalpost), [evaluation contract](https://www.builderr.ai/docs/signalpost-evaluation-harness.md), [brief](https://www.builderr.ai/starter-briefs/signalpost.md) and [source policy](https://www.builderr.ai/starter-briefs/signalpost-sources.md). Copies and SHA-256 hashes are retained with the audit evidence. The contract is scoring version 2, effective 26 August 2026.

- Governing weights: recall/coverage 50; precision/exact identity/evidence 30; synthesis 12; UX 8. Qualification requires an official total of at least 65. There are no separate category thresholds in this version.
- Recall within each external family uses 70% company recall and 30% claim recall against a checked shared collection. Raw availability rates are not recall.
- Submit code, exact commit, one command, a 100-company result or report, model/API/licence and cost disclosures, agent name and contact. Static profiles and a company manifest are not ranking inputs.
- Builderr supplies the official batch and frozen registry anchor; the set can grow. Contract examples say 1,000–1,100; the board's October 5 review says it used 1,500. Do not hardcode a batch size.
- Exactly one terminal envelope per input; all six states; evidence and periods; missing is not zero; idempotent refresh; safe source/secret handling. A material wrong-company publication or fabricated financial value blocks an official result.
- **Multiple versions are allowed: initial version plus four revised hashes, five total.** This is a revision allowance, not evidence of unlimited independent entries. Revisions apply only to later runs; earlier batch results remain in the average.
- The contract says revisions close **18 October 2026**; the challenge page says **before October 18**. Main challenge ends October 21. Neither retrieved text specifies the exact hour/timezone. Conservatively act before October 18 and clarify the cutoff with Builderr.
- Current documents leave numerical time/resource limits to Builderr. The older 45-minute / 2,000-request / $10 figures are provisional historical test bounds, not independently confirmed current limits.

The runnable [starter kit](https://www.builderr.ai/signalpost-starter-kit.tar.gz) was downloaded again. Its SHA-256 matches the previously inspected archive: `d48da9910ea7de07d2bf51ab265539a35fe07002a6c1ca5787df81316dfabbf6`. It includes a saved-response refresh demo, batch runner, output contract, source guidance, tests and optional external connectors. It is a baseline and learning aid, not the private evaluator or scoring reference. Its replay result does not qualify this agent. No starter implementation is imported by OrgLens.

## 3. Agent Implementation Assessment

Python 3.12+, uv lockfile, Beautiful Soup, standard-library HTTP/threading, certifi. CLI path: `cli.main → core.run_batch → viewer.render`.

| Area | Actual state |
|---|---|
| Official identity | Active; exact returned organisation number checked; optional full frozen registry supported |
| Financials | Active; numeric official fields, original currency/type/period; no missing-to-zero conversion |
| People / locations | Active roles and subunits; workplace pagination stops after first 100 |
| NAV jobs | Active shared feed; detail employer org or registered subunit required; name prefilter can miss brands |
| Website discovery | Registry/NAV/previous site/name-derived candidates; implemented attribution has reproduced weaknesses |
| Site extraction | Static HTML/JSON-LD, outbound profiles, contact, jobs, RSS/articles; no PDFs or rendered JS |
| Synthesis | Active cited templates; lexical date ordering can misidentify the latest event |
| Refresh | Field/value-set comparison and earlier evidence; mixed-source family failures mishandled |
| Reliability | Phased concurrency, request caps, pacing, retries, checkpoints; no resume; DNS/output can overrun nominal HTTP deadline |
| Models | Optional `--ai` loop exists; **not executed by the proposed evaluator command** |
| UX | Actual self-contained `index.html`; search/filter/compare/source inspector/export and responsive CSS in source |
| Validation | Membership, states, evidence links, snapshot hashes; not semantic claim validation or complete JSON Schema validation |

See [architecture](ARCHITECTURE.md) and source code. Earlier `--ai` reports are historical evidence for a different execution mode and are not credited to the default command.

## 4. Mandatory Qualification Checklist

| Requirement | Result | Evidence / boundary |
|---|---|---|
| Supplied unseen inputs, 100 terminal envelopes | PASS | Fresh seed 20261017, exact membership and snapshots validate |
| Larger input completion | PASS, scoped | 1,100 synthetic failure test; saved 1,000 live report exists. Actual current official budget not tested |
| Duplicate/invalid input behavior | PASS, scoped | Rejects duplicate or non-nine-digit input before running; checksum is not validated. Assumes eligible official inputs are unique |
| Robust exact-company publication | **FAIL** | Adversarial group-site, conflicting JSON-LD, phone and identifier suffix cases |
| Source references / retained bytes / dates | PASS structurally | Both saved 100-company sets and fresh set validate; semantic external evidence review incomplete |
| Financial source fidelity | PASS, scoped | 1,329 saved plus 1,308 fresh financial claims checked against exact retained responses |
| Missing distinct from zero | PASS | Existing tests and extraction checks |
| Refresh / source outage correctness | **FAIL** | Mixed-source activity outage loses stale facts; saved replay generates three changes |
| Pinned install and run command | PASS | Clean local clone installs, 49 tests pass; Ubuntu GitHub CI passes |
| Current official budget / exact supplied schema | NOT TESTED | Need organizer-supplied run contract; published local validator is not official harness |
| Source/secret controls | PASS documentation, incomplete assurance | Configured credential scan clean; documented DNS and robots boundaries; domain redistribution review outstanding |
| Desktop/mobile interactions | NOT TESTED | Browser webview attach timed out; static source inspected only |
| JBOX bonus | NOT APPLICABLE | No JBOX integration demonstrated |

## 5. Real Test Results

| Measurement | Saved smoke, Oct 16 | Fresh audit smoke, Oct 17 |
|---|---:|---:|
| Inputs / terminal envelopes | 100 / 100 | 100 / 100 |
| Published claims | 3,803 | 3,669 |
| Checked claims: legal names plus financials | 1,429 | 1,408 |
| Correct checked / incorrect checked | 1,429 / 0 | 1,408 / 0 |
| Financial claims checked | 1,329 | 1,308 |
| Legal/financial wrong-entity checked claims | 0 | 0 |
| Unsupported checked legal/financial claims | 0 | 0 |
| Remaining claims not semantically adjudicated | 2,374 | 2,261 |
| Available identity / accounts / roles / locations states | 100 / 100 / 100 / 100 | 100 / 99 / 100 / 100 |
| Websites / descriptions / companies with jobs | 10 / 8 / 0 | 6 / 4 / 1 |
| Company-published activity companies | 4 | 2 |
| Linked social profile companies / contact companies | 4 / 39 | 5 / 40 |
| Runtime seconds / HTTP requests | 144.688 / 736 | 139.984 / 673 |
| p50 / p95 cumulative company task time, milliseconds | 6,495 / 30,731 | 6,702 / 21,812 |
| External API cost, USD | 0 | 0 |
| Error records / failed family states | 41 / 6 | 25 / 7 |

Evidence completeness here means structural links and byte hashes passed for all envelopes. Financial checks compare the original numeric value, org number, currency, account type and period via its JSON pointer. They establish fidelity to official responses, not a separate accounting audit. There is no measured universal 100% precision claim; only 38.4% of fresh claims were adjudicated this way. Live external wrong-company and unsupported-claim counts remain unmeasured.

Saved live refresh: 100 envelopes, 737 requests, 136.656 seconds; reported zero changes between those two observations. Current clean-checkout saved-source replay: 100 envelopes, zero network requests, 21.601 seconds, **three activity changes** across three companies. The replay disabled guesses and lost some candidate observations, so it is not a fully controlled repeat of identical execution settings. The isolated mixed-source outage reproduction independently confirms a bug: registry activity keeps the family `available` and old website activity disappears without stale retention.

Saved 1,000-company live run: 1,000 envelopes, 6,548 requests, 1,303.954 seconds, $0; its configured allowance was **20,000 requests / 5,400 seconds**. Snapshot bytes for this scale release are not included in its published folder, so its semantic validity was not re-audited here. Do not describe it as passing a 2,000-request official run. Its website discovery rate is 147/1,000, not measured recall.

Existing suite: **49 passed**, also **49 passed in a fresh clone/new virtual environment** (Python 3.14.3 selected by uv), and [Linux CI passed](https://github.com/sankalp2515/AI-Agent-Company-Search/actions/runs/38974662125). Mocked provider/transport cases are not represented as live research. Browser verification failed to attach through available browser tools; no screenshot or tested mobile behavior is claimed.

## 6. Detailed Scoring

| Current category | Maximum | Defensible assessment | Basis |
|---|---:|---|---|
| Recall / coverage | 50 | **Not measured** | No independently checked opportunity set or official family weights. Fresh discovery rates alone cannot supply denominators |
| Precision / evidence | 30 | **No category score inferred** | 1,408/1,408 checked source-faithful legal/financial claims; external attribution remains unreviewed and adversarial failures exist |
| Synthesis | 12 | **8/12 provisional manual estimate** | Useful cited identity/accounts/unknowns; sparse recent intelligence, date ordering and refresh defects |
| UX | 8 | **4/8 provisional static estimate** | Implemented search/compare/source/date/status viewer; browser/mobile usability and full workflow unverified |
| TOTAL | 100 | **Not defensibly estimable** | Adding invented recall or precision points would manufacture a score |

The 12 provisional synthesis/UX points are subjective source-review estimates with low confidence, not an official subtotal or a score floor. Official score reproduced: **none**. Operational gates, the 38.4% claim-check coverage and official points are different measurements. These findings justify no-go without a fictional overall score.

Older Unstop compatibility is separate: coverage **not measured /35**; matching/evidence **not scored /30**; refresh **fails required outage behavior /20**; explanations **provisional 6/10**; usability **provisional static 2.5/5**. No historical total or 21/35 coverage-threshold pass is established. The older weighting is not the governing qualification rule.

## 7. Competitive Comparison

The retrieved public board remains reviewed **5 October 2026**: 37 submissions, 28 assessed, zero qualified. Leader Nikita: **60.80/100** = recall 13.82 + evidence 26.98 + synthesis 12 + UX 8. Highest displayed recall is Karthik #3 at 17.45/50, alongside lower synthesis/UX. Names are public board entries, not access to competitors' implementations.

This demonstrates the importance of external coverage: top entries already receive full synthesis and UX credit but still miss 65. It does not establish our recall or rank. OrgLens has no justified qualification-, top-three- or first-place-competitive claim yet. The next tier requires corrected integrity/refresh gates and materially broader independently checked external discovery on representative companies under actual run limits.

Even at the maximum other 50 points, qualification requires at least 15 recall points. That arithmetic is not a new separate threshold; a lower evidence/synthesis/UX total raises the recall needed for 65.

## 8. Critical Bugs and Weaknesses

Reproduction: `uv run --frozen python submission/audit-20261017/reproduce_audit.py`. It writes observations to ignored `out/audit-reproduction`, does not use network requests or private credentials, and does not alter implementation. The reproductions report current bad behavior; they intentionally are not passing product tests.

| ID / severity | Location | Observed failure / root cause | Expected behavior / fix / verification |
|---|---|---|---|
| ID-01 **P0** | `core.py:678–686`, `names.py:87` | Registry origin plus partial name token accepts `ACME Group` for `ACME INVEST AS`, then publishes a group description | Registry link generates a candidate; require exact legal attribution and label parent/group relationships. Regression must reject the same fixture and preserve real exact-org sites |
| ID-02 **P0** | `core.py:469`, `488–505`, `672–686` | Matching JSON-LD overrides conflicting footer; long identifiers truncated to final nine digits | Conflicts must stop publication or become ambiguous. Parse only exact supported Norwegian ID forms. Repro publishes website only; its conflicting-page description is suppressed |
| ID-03 **P1** | `core.py:563–566` | Unrelated `2233` and `4455` become registered phone `22334455` when all page digits concatenate | Match a bounded phone token/contact field, not page-wide digits; reject fixture and retain formatted genuine phone matches |
| RF-01 **P0** | `core.py:995–1008`, site failure state handling | Registry activity is available while website fails; old external activity becomes a change and is not retained stale | Track source/subfamily success; a failed source cannot prove removal. Verify unchanged, changed, removed, failed and conflicting sources separately |
| OP-01 **P1** | `core.py:1184–1187`, documented command | At 1,000 companies, accounts/roles/workplaces alone need ~3,000 requests even with frozen identity. Proposed cap is 2,000 | Obtain actual budget; use supplied registry, prioritize fairly across modules and verify 1,000/1,100 at that budget. Completion is not sufficient coverage |
| CV-01 **P1** | `navjobs.py:65–101,115–151`, `core.py:730–819` | Six websites and four descriptions in fresh 100; brand prefilter/limited static discovery. Registry events inflate activity availability | Expand permitted exact-entity discovery and extraction; evaluate added supported opportunities on a held-out labelled set. Do not weaken attribution |
| SY-01 **P1** | `core.py:964–969`, `extract_site_facts` | Lexical RSS dates choose Wed Jan 2025 ahead of Thu Jan 2026; generic About/Privacy Article schema is treated as activity | Normalize dates before sorting; separate static pages from news. Verify mixed RSS/ISO dates and current events |
| SC-01 **P1** | `core.py:589`, redirects at `core.py:632–639` | Robots crawl delay is clipped at 10 seconds; destination domain can be fetched under prior domain's policy | Honor full permitted delay or abstain under budget; check redirected host robots before collection. Existing policy documentation is not proof of compliance |
| EV-01 **P2** | `core.py:1031–1057`, `viewer.py:57` | Hash validation cannot establish semantic support; stale facts rendered as raw JSON; no browser QA | Add independent semantic review and test source/date/compare/mobile flows. Do not turn an availability counter into a recall score |

Expected benefit: identity and refresh fixes remove direct invalid-run risks; budget work prevents systematic failed research families; discovery improves the 50-point recall dimension; date and UX work improve supported usefulness. Numerical point gains are unknown without checked opportunities. Prioritize P0 gates first, then OP-01 and CV-01; cosmetic changes do not remedy them.

## 9. High-Impact Improvement Plan

1. **Mandatory integrity fixes:** remove partial-name publication, make conflicting IDs veto publication, stop suffix ID matching and match real phone tokens. Turn the audit fixtures into rejecting regression tests. Re-audit previously accepted websites under the corrected policy.
2. **Mandatory refresh fix:** distinguish registry activity from company activity and record source-level success. Retain old facts on fetch failure. Verify both sides of genuine change evidence and no false changes on repeat snapshots.
3. **Mandatory evaluator alignment:** confirm schema, frozen registry format and actual limits with Builderr; freeze a single command and test fresh 100 plus 1,000/1,100 at that budget. Add budget-aware phase allocation without pretending unqueried families were checked.
4. **Competitive coverage:** use permitted search/discovery with reproducible organizer credentials if required; add verified site news/careers/location/contact pages and brand/subunit-aware NAV candidates. Build an independent held-out reference sample. Accept a strategy only when it adds supported exact-company coverage at acceptable request/cost/runtime.
5. **Verification and polish:** normalize dates, exclude static policy pages from news, test viewer interactions on desktop/mobile, review redistribution rights, repeat the same evaluation, freeze corrected commit. No architecture rewrite is required by the present findings.

## 10. Submission Package Review

Public repository and code commit are published. Dependencies are locked; install/CLI/tests work in a new environment and Linux CI. Smoke/refresh envelopes plus evidence are under `submission/release`; a fresh report and claim checks are under `submission/audit-20261017`. Source and model/API disclosures exist. Default cost is $0 and no model key is required.

README now includes truthful status, CI/Python/licence badges, navigation, explicit UI instructions, measured data and architecture/contribution/security docs, using IntentSeal's presentation as a reference. Repository description/topics are configured. No unverified screenshot, qualification badge or official score was added.

Contact details are filled. The submission email remains unsent. Source rights are documented, but per-domain redistribution review remains outstanding; do not claim all snapshots are MIT data. `.env` is ignored. The pre-push scan covered 2,049 candidate files / 114,049,521 bytes and found no configured private credential values. That is a scoped scan, not proof of absence of all possible secrets throughout history.

## 11. Final Go/No-Go Decision

**NO-GO: do not submit this exact executable commit as a ready, reliable entry. FIX BEFORE SUBMISSION.** A passing smoke test establishes operability, while the reproduced identity and refresh cases violate the intended integrity requirements. Resolve ID-01, ID-02, ID-03 and RF-01, establish evaluator-budget feasibility, then rerun. No agent fixes were silently applied during this audit.

Revision timing is urgent. Five total versions are permitted, but activating defective code can expose later batches to failure/zero scores. Do not treat the revision allowance as evidence that shipping a known attribution defect is safe.

## 12. Submission Instructions

After the mandatory fixes and verification:

- Repository: https://github.com/sankalp2515/AI-Agent-Company-Search
- Exact commit: take the **corrected, pushed** hash with `git rev-parse HEAD`. Current audited code is `a6cc772f9d367e3115af97374ab72e22180f3208`, held for fixes.
- Install: `python -m pip install uv==0.10.9`, then `uv sync --frozen`.
- Current reproducible command: `uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --max-requests 2000 --max-seconds 2700`. Replace caps with confirmed official values before freezing the final command; append full `--registry registry.jsonl --registry-retrieved-at <actual timestamp>` if provided.
- Environment: none required for default mode. `NAV_FEED_TOKEN` optional; otherwise NAV published public token is used. Optional AI/search modes require separate reproducibility and cost disclosure and are not part of this command.
- Models: none in default mode. APIs: BRREG entities/accounts/roles/subunits, NAV feed and permitted company sites. Licence: MIT code, dependency/source-specific terms in SOURCE-RIGHTS.md. Cost: $0 third-party API charge for default mode; compute/bandwidth separate.
- Smoke evidence: `submission/release/smoke/run-report.json`, envelopes and snapshots; additional fresh report in `submission/audit-20261017/fresh-run-report.json`.
- Contact: Sankalp Wanjari, wanjarisankalp@gmail.com. Agent: OrgLens.
- Send the corrected package to `submit@builderr.ai` only after a go decision. The current draft in SUBMISSION.md is explicitly on hold. Five versions total; revision wording differs around October 18, main challenge closes October 21; exact cutoff time needs confirmation.

### Scope and remaining uncertainty

No private official reference, official numeric budgets, official evaluator adapter, comprehensive external fact adjudication, browser/mobile test or live 1,000-company rerun at current official limits was available in this audit. The full 49-test suite, fresh live 100, saved evidence checks, clean installation, Linux CI, source review and isolated adverse reproductions were performed. Those limits constrain score claims, but do not prevent a concrete no-go diagnosis.
