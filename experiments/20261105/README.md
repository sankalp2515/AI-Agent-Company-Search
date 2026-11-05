# Isolated score experiments — 5 November 2026

This branch is an experiment based on submitted V4 `a408d146deb1b4d24031400d140cfb38c326a8d7`. It does not change the submitted commit, main, or the separate JBOX work. Nothing was pushed or submitted. These are operational and extraction checks, **not an official score or proof of qualification**.

## Decision

Keep the leadership-before-website fix, six-month NAV bootstrap, bounded job depth, and precision guards. Do not increase the default guess count or crawl depth on the evidence collected here. Website discovery remains the dominant gap: only 34 of the original 300 companies have a verified website. No measured result establishes 65/100 or 35+ recall points.

Before spending a final revision, obtain the active-commit/revision count and official subscores already requested in the submission email. The highest-impact next experiment is reproducible website discovery using an organizer-supported model/search mechanism, if permitted and provisioned. A model key alone does not establish permission or budget for built-in web search. Existing personal SerpAPI/Tavily credentials are excluded from this candidate.

## What changed

- Balanced research obtains registered leadership before verifying sites. Full legal-name domains can then be corroborated against the registered operating head during the first crawl, rather than missing that proof because roles arrived later. A small-budget reserve preserves the website breadth pass.
- NAV bootstrap covers 186 days rather than 40, with a shared page pool capped at 600 pages and a detail reserve. This is a bounded six-month change-feed scan, not a promise of an exhaustive job inventory. Partial scans remain explicit.
- Job candidates prioritize newer modifications. Every company receives its initial check before an optional deeper pass, with per-company and global detail limits. Inactive and expired ads are rejected; exact employer or officially proved workplace-parent relationships remain mandatory.
- Weak subsidiary/parent proofs require a matching homepage publisher label even when labels are absent. Foreign feed redirects cannot redefine the verified article publisher. Static routes and irrelevant media-company news cards are rejected.
- Correct the Norwegian web-agency credit regex and preserve exact three-letter social handles for the verified brand/domain.

No new dependency, UI rewrite, model call, paid search, or personal key was introduced.

## Controlled and live measurements

The first comparison uses the **same original 300 company IDs**, separating five deliberately added positive job cases. Submitted observations are from 3 November; new live observations are from 5 November, so this is not a simultaneous network A/B. A separate paired saved-source replay supports the causal leadership finding.

| Original 300: companies with evidence | Submitted V4 | Experiment |
|---|---:|---:|
| Verified website | 32 | 34 |
| Website description | 25 | 27 |
| Company-owned social links | 14 | 16 |
| Individual dated news | 1 | 1 |
| Active job postings | 0 | 0 |
| Careers page | 6 | 6 |

Social URLs increased from 24 to 28; news facts remained three. All 32 previously accepted websites remain accepted. The two added sites are ARBEIDSARK AS (`924859946`, arbeidsark.no) and MAGENT AS (`923377956`, magent.no), with registered operating-head corroboration. Financials matched the register's newest filing year for 299/300; the remaining case explicitly reports its freshness gap.

The five additional competition-universe employers are diagnostic positives, **not random validation data**. They returned 18 active, unexpired job postings across 5/5 companies. Every posting was checked against its saved NAV detail and an exact employer/registered-workplace relationship. In particular, ZOUQ SANDVIKA AS (`917363749`) returned the still-active September vacancy `00192017-ffa7-4937-9e88-65931ee2b80a`, missed by the old 40-day bootstrap. These 18 postings are not a gain on the original 300-company cohort.

| Run | Valid envelopes | Requests / cap | Seconds | External API cost |
|---|---:|---:|---:|---:|
| Live original 300 + 5 diagnostics | 305/305 | 2,566 / 6,100 | 556.575 | $0 |
| Fresh locked-clone original smoke | 100/100 | 1,115 / 2,000 | 354.405 | $0 |
| Historical saved-source scale replay | 1,100/1,100 | 0 HTTP | 178.919 | $0 |

Both live runs completed all six NAV segments, 368 feed pages. The clean 100-company run retained 9 websites, 8 descriptions, 4 companies with social links and 2 with news, matching submitted smoke coverage. Its larger bootstrap uses more requests than the submitted 822-request smoke, still comfortably within 2,000. It has 24 failed field states and 21 ambiguous field states; valid terminal envelopes do not mean complete facts or qualification. Live timing varies with the network and is not a controlled speed comparison.

The 1,100-company replay uses historical saved responses from 19 October and an adapter restricting DNS candidates to saved URLs. It verifies extraction/envelope integrity at scale, **not fresh network performance, job bootstrap scaling, or official recall**. Replay mode does not execute the live NAV source.

## Approaches tested and rejected or limited

1. **Paired replay of the original 300:** same saved source set and DNS adapter, submitted code versus candidate. Websites 21→23, descriptions 17→19, social-covered companies 8→10, no accepted website loss. The two additions are the same role-corroborated sites. Restricted archived routes mean replay does not reproduce full live coverage; do not compare replay 23 with live 32.
2. **More name guesses:** 890 previously untried legal-name hypotheses on original-cohort companies without sites; nine resolving hosts across seven companies. The bounded component crawl used 46 requests and found zero verified sites. No default expansion adopted. Resolving DNS is not identity evidence.
3. **Deeper crawl:** three known site/news cases fetched with 12-page settings (62 requests), then eight-versus-twelve paired extraction on those saved observations. Neither replay gained additional news from depth (three news facts in one company in both). The replay adapter reverified only two of three sites, so this small diagnostic is not a full depth benchmark. Keep eight pages.
4. **Job refresh:** saved-source re-extraction of all 18 accepted jobs, with repeated depth calls. Zero duplicate claims or material changes. When the job source was made unavailable, all 18 prior jobs remained last-known evidence, with no false removal. This is a component replay, not a live refresh.
5. **Behavioral regression:** all nine initial new regression tests fail against submitted code and pass against the candidate. Two further tests cover inactive ads and breadth-before-depth/shared-budget behavior. All original tests retained: **185 passed**, including a fresh locked install and test run in an independent clone.

## Reproduce the candidate

Runtime code was tested at `73ba0d63c39e71074e37ffdcd198fa6cb7126567`; tests-only commit `ecd555dbc4655dd46c4eb3d60c34e0e93b2345b6` adds two behavioral checks. Subsequent experiment-documentation commits do not change runtime code or dependencies.

```
uv sync --frozen
uv run --frozen pytest
uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --strategy balanced --pages 8 --requests-per-company 20 --max-seconds 2700 --no-discover
```

If provided, append `--bulk <frozen-registry-file>`. Live measurements here did not receive a frozen registry, so fetched their identities normally. Use evaluator-provided companies for an official run. `inputs-305.jsonl` is the local experiment fixture, not a submission manifest.

Tested source-tree hash: `ae3ffa289df9cfab3fd63f973b8439890053caf9`; tests tree: `b575aa5b1b3b4d7bb0f4620ed93b670967919ca6`; lockfile blob: `62348f6cb835e7ceaeb81d5c7fb4786fbece3468`.

Small reports and cohort comparisons are preserved in `results/`. Full envelopes, viewer pages and raw evidence remain in ignored local `out/experiments/` directories. Raw third-party snapshots are excluded from Git. The existing desktop/mobile viewer was not modified; source coverage and precision were prioritized over cosmetic changes.

NAV's documented active-ad horizon motivated the bootstrap: https://navikt.github.io/pam-stilling-feed/. Feed discovery alone never becomes an accepted job claim.

Tracked-file secret scanning passed (176 files, zero findings), including comparison with locally configured private values without printing those values. All 18 job claims also passed an independent check of the raw BRREG workplace-parent records.
