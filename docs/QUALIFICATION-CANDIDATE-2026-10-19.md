# Score-focused revision — 19 October 2026

Use verified discovery, bounded AI quotation selection and protected source budgets as the next candidate. Adding an unrestricted LLM is not the missing ingredient. The observed failures were wrong publisher attribution, missed source formats, premature search termination and sources losing their time allocation.

The implementation is pinned at `7aa6649274b0c7d290d5e3dfa90165ff8de9a1a9`. Later release documentation does not change its executable source. Nothing in this work pushes or submits a revision.

## Changes that address the score

| Observed problem | Implemented response |
| --- | --- |
| A registry URL can become a group portal | Follow an explicitly linked complete-name company domain and independently verify it. KAEFER Energy now resolves to `kaeferenergy.no` with its exact organisation number; an unverified child cannot authorize the group portal. |
| Search returned plausible URLs but none verified | Lazily try the next configured search provider after identity rejection. Stop when a candidate verifies; preserve global query, request, time and declared spending limits. |
| Real news cards lacked schema or `time` elements | Parse literal ISO, Norwegian numeric and Norwegian/English month-name dates beside one internal news headline. Reject ambiguous containers, invalid/future dates and navigation/footer dates. |
| The same article appeared in a card and schema | Merge article/date duplicates and retain both evidence sources. |
| Privacy pages consumed crawl depth after identity was established | Prioritize news and hiring once identity is proven. Extra legal pages remain available when identity is unresolved. |
| Search could leave no time for records or jobs | Bound external stages and reserve time for accounts, leadership, locations and NAV. Restore the run deadline between stages. |
| One transient request disabled a whole source | Retry robots checks once within budget, respect throttling/backoff, and retry a transient NAV public-token failure once. Never bypass access denials or robots rules. |
| Registered email domains were ignored | Treat a non-personal email domain as another candidate, requiring the same publisher proof. Manager/accountant domains are not proof. |
| Models could invent descriptions or domain names | Permit only an index selecting an existing paragraph on an already verified site, or abstention. Model-generated domain guessing was rejected. |

## Experiments retained, including failures

The public example cohort and the random-universe smoke cohort have very different opportunity rates. They must not be pooled or compared as if they were equivalent samples. The public cohort has already been used for development and review; it is not an untouched holdout or a current independent gold set.

- Broad versus precise search on the same development 20: both found 15 websites, 13 descriptions and 9 companies with social links. Precise search used 453 requests / 152.359 seconds versus broad's 418 / 129.593. Broad remains the selected policy; precise remains an opt-in experiment.
- Model domain probe: all proposed domains failed DNS. None was published. This does not support promoting LLM domain guessing.
- Registered-email-only random smoke: 100/100 valid outputs, but only 4 websites after source failures. It is retained as a failed isolated improvement, not hidden behind the better public sample.
- First public hybrid: 100/100, 861.047 seconds, 1,399 requests, 72 websites, 60 descriptions, 43 companies with profiles, 16 companies / 102 external news facts, no completed NAV index.
- Protected-stage public hybrid: 100/100, 444.203 seconds, 1,814 requests, 73 websites, 61 descriptions, 44 companies with profiles, 23 companies / 126 external news facts, 3 companies with jobs and all six NAV segments completed. This predates the final group-hub and fallback/token corrections.
- Broader random hybrid before the fallback/token correction: 100/100, 359.625 seconds, 1,348 requests, 11 websites, 9 descriptions, 5 companies with profiles, 3 companies / 14 external news facts. Accounts, leaders and locations covered all 100. NAV's initial public-token request failed; the source is honestly marked failed, not empty.

These are bundle comparisons under changing live responses, not isolated causal estimates. Report `activity` includes official registry events; the external news counts above explicitly exclude them.

## Identity and evidence verification

The final implementation's public 100-company run completed 100/100 valid results in 483.250 seconds using 1,535 requests: 73 websites, 61 descriptions, 45 companies with profiles and 24 companies / 134 external news facts. It used 69 search attempts and 21 model attempts (12 selections; 10,946 input / 877 output tokens). The additional search fallback has not established a separate causal coverage improvement; source responses also varied. The corrected KAEFER domain contributes independently verified company-specific news and social links.

The final implementation's broader random smoke completed **100/100 valid outputs in 389.937 seconds**, using 1,702 requests, 121 searches and 8 model attempts (1 selection; 3,242 input / 338 output tokens). It returned 12 websites, 10 descriptions, 6 companies with profiles, 3 companies / 14 external news facts, and accounts/leaders/locations for all 100. NAV completed all six segments / 83 pages and 99 detail checks; no exact-employer job claim was published. Incomplete candidate checks remain explicit. Compared with the preceding random run, one additional site is published: HAUKÅSEN FJELLGARD AS (`829275872`) at `haukasenlodge.no`, verified by its exact organisation number. The random-sample gain is modest and does not establish 65/100.

NAV's public-token request failed before a counted HTTP request in that full run, despite the bounded retry. Zero jobs there is a failed-source observation, not proof that the companies have no jobs. A separately instrumented one-company CLI run at the same implementation successfully fetched the token, completed all six segments / 83 pages, and indexed 9,177 active ads. Direct endpoint checks also succeeded. The intermittent full-run failure remains a reliability risk; a registered `NAV_FEED_TOKEN` supplied by the organizer avoids depending on the public-token lookup. Do not describe this failure as conclusively diagnosed or fixed.

The final-source 1,100-company saved-source replay returned 1,100/1,100 valid envelopes in 192.734 seconds. It preserved dates and hashes, made no network requests and disabled discovery/models/jobs/guesses. Its 69 websites / 46 descriptions describe extractable saved observations, not fresh scale coverage. A final-source live 1,100-company hybrid run under agreed official limits remains unmeasured.

The suite passes 154 tests. A fresh local clone at the pinned implementation installed only the declared locked dependencies into an empty virtual environment and passed the same 154 tests. A preceding clean-clone live check at the same website implementation returned 3/3 valid profiles: it selected KAEFER Energy's exact-number site and abstained on the previously audited KINLAND I / HANS SYLTE problem cases.

All 32 dated-card evidence records in the protected public run retain a literal source date, headline and original anchor href; the separate audit found no article/date duplicates. This checks evidence preservation, not universal factual precision. Exact response snapshots remain local and ignored because third-party HTML can embed credentials.

The release scan checked 158 publishable files against configured private values and known credential patterns with no findings. Raw snapshots and history backups remain excluded; this is a scoped scan, not a claim that third-party pages contain no secrets.

The portable viewer supports desktop/mobile search, comparison, source verification, unknowns and refresh changes. Its layout was inspected in the preceding release and is unchanged. Screenshots in `docs/images/` show layout, not an evaluator-awarded UX score.

## What 65 requires

The [published rubric](https://www.builderr.ai/challenges/signalpost) gives 50 recall, 30 precision, 12 synthesis and 8 UX points. For planning, 28 recall + 28 precision + 6 synthesis + 4 UX would total 66. These are targets, **not measured ratings**. The implementation addresses all four dimensions; preserving exact company identity remains a separate qualification requirement.

Historical website/social URL agreement only measures those opportunities. It does not establish overall recall, synthesis, UX or 65/100. A new company website can correctly disagree with an old example; a matching old URL can still be a wrong-company group portal. The corrected KAEFER case demonstrates why copying public-example URLs is unsafe.

The latest checked board lists 57 submissions and zero qualified entries; its leader's 70.43 / 35.77 recall is explicitly provisional and does not declare qualification. Beating the provisional recall figure and obtaining an official qualifying run remain separate goals.

## Reproducible activation and cost

The earlier keyless command deliberately did not use an LLM or paid search. The score-focused command must explicitly enable `--discover --extract-ai --providers groq`; merely having API keys does not activate them. Groq uses `openai/gpt-oss-20b` to select source quotations. It never writes accounts, establishes ownership or authors published facts.

Builderr must supply/approve reproducible model **and search** credentials. The challenge offers model keys on request and prohibits depending on a participant's personal service account. Model-key availability does not itself confirm a search-provider allowance.

For a Tavily-only cost scenario, basic searches use one credit, and its [published pay-as-you-go rate](https://www.tavily.com/pricing) is $0.008 per credit. A cap of 1,200 basic searches therefore allocates up to $9.60 for search at that list rate, excluding taxes, subscriptions and free allowances. Set only the approved Tavily search credential for that scenario; a mixed SerpAPI/Tavily chain has different billing and requires its own declared rate.

Groq's [published model rates](https://console.groq.com/docs/model/openai/gpt-oss-20b) are $0.075 per million input tokens and $0.30 per million output tokens. The protected public run's 10,946 input / 877 output tokens imply about $0.001084 for that model-token component at list rates. This is not its complete API invoice or a guaranteed scale cost. Token usage varies with verified sites; the report records actual tokens and attempts. `--max-api-cost` caps declared search spending, not model billing.

Do not rely on unverified free allowances. Confirm the organizer's actual model/search budget and account plan, substitute the supplied run limits, and request an official run at the accessible exact hash. The page still advertises October 21 while its revision text says before October 18; acceptance of a new revision on October 19 needs confirmation. No revised submission has been sent by this task.

Final run artifacts and source fingerprints are listed in [the hybrid candidate folder](../submission/candidate-20261019-hybrid/README.md).
