# Local qualification experiments — 18 October 2026

The target is a valid official score of at least 65/100 and recall above the published leader's 35.77/50. No official result establishes either target for OrgLens yet. All changes in this experiment remain local; nothing has been pushed or submitted.

## What the experiments established

The largest improvement came from allocating requests to external research before the expensive NAV scan. Search helps some unresolved companies, but accepting a search result as a company website without proving the publisher introduced unacceptable directory/platform matches. Those matches were rejected and covered by regression tests.

| Development configuration, same 20 inputs | Requests / 400 cap | Websites | Descriptions | Decision |
| --- | ---: | ---: | ---: | --- |
| Original phase order / original NAV detail policy | 400 | 0 | 0 | Reject this allocation at this budget |
| External-first allocation and bounded NAV details | 355 | 13 | 8 | Retain allocation strategy |
| Search plus initial quote selector | 395 | 17 | 12 | Reject: three directory/platform ownership mistakes; model calls failed |
| Publisher checks and search | 392 | 15 | 10 | Retain publisher checks; JSON request still failed |
| Deeper crawl and corrected quote selector | 395 | 15 | 14 | Retain as development candidate; 4 literal selections in 5 model attempts |

These are strategy-bundle comparisons, not isolated causal estimates. Live source responses and timing varied. All runs returned every input and passed structural/snapshot validation; that validation alone does not establish factual precision.

## Reserved public examples

Before changing the strategy, the organizer-authored 100-profile sample was divided with seed `20261018` into development 20, validation 30 and holdout 50. The original HTML, its SHA-256, reference extraction and split are preserved under ignored `out/qualification-lab/`. Company numbers are test inputs, never production routing rules.

The 30-company validation run returned 30/30 results in 120.265 seconds with 417 requests. It found 15 websites and 14 descriptions. Historical host agreement was 15/29 positive websites; social URL agreement was 9/22 URLs across 5/11 positive companies. This weaker result is retained, not discarded.

The 50-company holdout returned 50/50 results in 274.094 seconds with 924 requests. It found 40 websites, 38 descriptions, 26 companies with linked profiles, and one company with a verified job ad. Against the historical sample:

- 39/49 positive website hosts matched (79.59%). The other accepted host was `studix.no`; its source shows the requested exact organisation number, while the historical example used `studix.com`.
- 46/54 social URLs matched across 19/24 positive companies. Applying the published 70% company / 30% fact arithmetic to **this social family only** gives 80.97%.
- No combined score out of 50 or 100 is inferred. News, jobs, descriptions and other reference families lack complete independently reviewed current labels. Host agreement is not independent legal-identity proof.

The holdout was audited after running. It exposed a third-party patent-news paragraph incorrectly selected as a company description. The publication gate now excludes news/blog/post containers from description candidates, and the prompt explicitly rejects third-party news. A saved-source regression reproduces the original observation and verifies that the paragraph is no longer published. Consequently, the pre-audit count of 38 descriptions is not certification of the latest candidate.

## Publication and efficiency changes

- Search documents are candidate hints. A deep result first requires ownership proof on the site's root/contact pages before its content can be used. Known business directories and ticket platforms are excluded.
- Company-name normalization applies to both source text and legal names. National/division qualifiers remain significant. Corroboration still requires a registered phone or complete registered address; an approximate name alone cannot authorize publication.
- Name evidence uses the actual source span, preserving its original case, accents and punctuation. It must not quote an uppercased registered name that does not occur literally on the page.
- The optional model can select an existing paragraph index or abstain. It cannot author facts, invent URLs, change numerical accounts, or override entity checks. Usage, failed attempts and unverified billing remain visible.
- Facebook posts, stories and photo endpoints are not profiles. Bare numeric links additionally need explicit profile-link context, rather than an unlabelled embedded image.
- Facebook `profile.php` links retain their required numeric `id`; absent, nonnumeric or duplicate IDs are rejected. Tracking parameters are removed without erasing profile identity.
- Social evidence locators retain the original anchor href or JSON-LD `sameAs` value, while profile URLs are normalized separately.
- Generic `Article` markup on careers and sales-terms pages is excluded from news. Explicit `NewsArticle` reporting about a career programme remains eligible. The saved smoke audit exposed this distinction; the pre-fix activity totals must not be described as reviewed news coverage.
- RSS/Atom parsing preserves the actual article URL and publication date. The previous HTML parser could substitute the feed URL or choose an Atom self link.
- Within-run website and NAV caches share exact observations and original timestamps. A refresh creates a new cache. Stage-budget failures are not cached as successful observations.
- Saved-source replay recognizes both requested and observed redirect destination URLs, retaining original timestamps and hashes. This fixes a replay omission; it does not fetch new evidence.
- Snapshot validation hashes each unique snapshot once per invocation using four bounded I/O workers. A later invocation rechecks bytes and detects corruption; no validation result is reused across refreshes.
- Search requests reserve query and declared cost allowances atomically before concurrent calls. NAV candidate details and total detail requests are bounded, with incomplete research left explicit.

## Smoke, scale and reproducibility

The first random 100-company candidate smoke test completed 100/100 results, 1,324 requests, 370.782 seconds, 11 websites and 10 descriptions. A later run completed 100/100, 1,292 requests and 617.235 seconds, with 10 websites and 8 descriptions. Both used a 2,000-request and 900-second local cap. The runtime variation and modest random-universe coverage remain material limitations.

The newest live smoke attempt (`current-smoke100`) completed 100/100 with valid snapshots, 1,327 requests and 876.141 seconds against the same 900-second cap. It found 12 websites, 10 descriptions and 7 companies with linked profiles, but no jobs. It started before the latest static-news, locator, replay and validation corrections; it is not an exact final-source run. The narrow time margin is a readiness concern. A saved-source check of the latest extraction corrections returned 100/100 valid envelopes; it is explicitly replay, disables jobs/search/model calls, and does not establish fresh coverage or billing.

The 1,100-company live scale attempt used a 20,000-request / 2,700-second local cap. It wrote all 1,100 terminal envelopes, containing 117 websites, 93 descriptions, 70 companies with linked profiles and 5 with jobs. It did not leave a completion report, so it is **not a certified completed scale run**. Independent snapshot validation is being recorded separately; it cannot recover the original request accounting or prove timely process completion. These are engineering limits, not confirmed official budgets. The historical scale run used 20,000 requests / 5,400 seconds; runtime comparisons must disclose that difference.

Verification artifacts and exact commands are in ignored `out/qualification-lab/`. The source fingerprint captured before the two latest numeric-profile/name-span corrections is in `candidate-manifest.json`. Do not describe a run made before those corrections as a final run at the latest code. Clean-source installation and the final scale audit are separate checks. No new exact Git commit or official result is claimed by this report.

Independent validation of the 1,100 saved envelopes passed all snapshot checks in 429.015 seconds. This was a separate check, not recovery of the missing original report. The current validator is checked separately against those same files, with the explicit caveat that prior reads and storage/cache conditions prevent attributing any runtime difference solely to the code change.

The regression suite currently has **125 passing tests**, including identity conflicts, source spans, selector output validation, request/cost races, shared cache behavior, feed URLs, query-based Facebook identity, literal social locators, static-page/news distinction, redirect replay, validation deduplication/corruption, unknown-value preservation, batch completion and viewer workflows. The earlier publishable-file secret scan found no credentials; a repeat scan of the current candidate is recorded separately. Raw source snapshots, environment files and history backups remain excluded from Git.

## User experience

The portable HTML viewer supports search, filtering, source links and locators, stale facts, JSONL export and two-company comparison. A compact comparison overview places websites, employees and dated financial values together; missing values stay explicit. Desktop and 390-pixel mobile layouts were inspected in a real browser without horizontal overflow. Screenshots remain local under `out/qualification-lab/`. UI implementation does not establish an evaluator-awarded UX score.

## Cost and remaining external dependencies

Measured Groq usage on the holdout was 7,625 input and 746 output tokens. At the [published GPT-OSS 20B list prices](https://console.groq.com/docs/models), that model-token component is approximately $0.000796. This excludes search, other services, and invoice verification. Search made 12 requests on the holdout and 60 on the first smoke test. A zero configured search rate is not proof of zero billing. No complete official-run cost is established.

The [challenge page](https://www.builderr.ai/challenges/signalpost) permits model usage and says organizer-supplied credentials are available on request. Our personal service credentials are not a reproducible submission dependency. Confirm the organizer-supported model/search credentials, exact resource limits, version-1 feedback and UX entrypoint before freezing a revision command.

As checked on 18 October, the page header advertises an October 21 close, while the revision paragraph still says before October 18. Do not assume the revision window was extended. The board still lists the October 17 provisional leader at 70.43 overall / 35.77 recall and explicitly does not declare qualification. We have not contacted Builderr or sent a revision.

## Current decision

Keep this candidate local. Qualification and recall targets remain unproved. Before using another revision, improve external source coverage on reviewed examples, establish the official resource and credential contract, obtain version-1 evaluator feedback, and complete a live scale run at the exact frozen source with a completion report and adequate time margin. The current 1,100-envelope artifact audit is useful evidence of completeness, but cannot replace that run. A successful test suite or polished viewer alone cannot certify 65/100.
