# Firecrawl-guided follow-up

The user requested continued experiments using Firecrawl to discover crawling patterns. All work remains on `codex/score-experiments-20261105`, based on the submitted V4 commit. Nothing was pushed, merged into main, emailed or submitted. The earlier README records the first experiment; this document describes the subsequent work.

## What Firecrawl revealed

Firecrawl search, scrape, map and a bounded crawl were used for diagnosis. These observations describe the returned pages and links, not Firecrawl's proprietary implementation.

| Observed pattern | Example | Action |
|---|---|---|
| The homepage leads to a news index, whose cards lead to individual articles | [Norsk e-Fuel news](https://www.norsk-e-fuel.com/articles) | Follow at most two article cards inside the existing page budget; prioritize press releases. |
| A publication dateline can be visible HTML rather than JSON-LD or a time element | [CEO transition](https://www.norsk-e-fuel.com/ceo_transition) has a 2 November 2026 dateline and a different appointment effective date | Extract a leading literal dateline near the article headline. Preserve its quote and index-link provenance. Do not infer dates from event prose. |
| Older sites omit semantic main/article markup and description metadata | [MetodeData](https://www.metodedata.no/) | Admit bounded company-introduction paragraphs that name the legal company and contain a descriptive verb; exclude navigation, footer, cookie and news containers. |
| Company websites can survive a legal name change | Former MARITIM INSTALLASJON's domain redirects to [Steinly Marin Senja](https://www.senja.steinly.no) | Derive additional candidates from the register's last two historical names, under the existing fetch ceiling. Require proof of the current entity. |
| An apparently relevant domain may belong to a different company or group | [Oslo Pumpeservice](https://oslopumpeservice.no/) versus PUMPEHUS AS; Marineholmen and Pergården group/portfolio pages | Retain identity safeguards. Shared phone numbers, group mentions and directory results do not establish publisher ownership. |
| Rendering or a remote proxy can retrieve a site our transport cannot | [Barnas Håp](https://barnashap.com/) returned content through Firecrawl; the agent received 403 responses | Record the access limitation. Do not disable TLS, bypass robots or silently add a personal Firecrawl credential to the official run. |
| Discovery can require a domain outside simple .no/.com guesses | [EDIT's website](https://www.edit.land/) appeared in search | Keep it as research evidence of the discovery gap. No company-specific URL list was added to the agent. |

The Grünerhaven restaurant was also investigated as a possible registered trading-brand case. Its legal-company relationship was not sufficiently corroborated by the collected workplace records, so no permissive brand-alias rule was introduced.

## Implemented rules and safeguards

The second-hop crawl stays within `--pages 8`: it reallocates remaining first-hop work rather than appending an unbounded crawl. Only explicit news-index paths qualify. Article links must be on the verified host, outside navigation/footer regions, with a meaningful label. Static routes, external destinations, files and index pages are excluded. Newly followed articles must name the company in their headline or lead and supply an acceptable date; company-specific JSON-LD announcements remain supported.

An audit of the first fresh smoke run caught two Quantum Leap Grow leadership-advice posts. Their metadata titles ended with the publisher's name, but they were not company announcements. That apparent increase from two to three news-covered companies was rejected. The final policy strips publisher suffixes as subject evidence, rejects obvious instructional headlines consistently across news extraction paths, and requires a company/event subject for the newly followed route. This correction is covered by metadata and feed regressions. Rejected outputs remain ignored local experiment data, not a release candidate.

Historical names are discovery hints only. In the positive case, the current STEINLY MARIN SENJA AS organisation number `997870506` appears on the destination page. A different legal entity on an old-name domain still fails verification. The standalone normal-CLI probe verified this site in 11/20 requests, without a manually supplied URL. The broader historical-name probe tested 296 domain hypotheses: 35 resolved across 27 companies; its component crawl used 181 requests and found one current-entity-verified site. This selected probe is not random recall measurement.

## Measurements and provenance

The original 300-company cohort and five selected diagnostic employers remain separate. The latter test job retrieval and are not counted as random coverage gains. Machine-readable measurements are in `firecrawl-results/` and `firecrawl-results/summary.json`.

| Original 300: companies with evidence | Submitted V4 | First isolated experiment | Firecrawl-guided experiment |
|---|---:|---:|---:|
| Verified website | 32 | 34 | 35 |
| Website description | 25 | 27 | 30 |
| Company-owned social links | 14 | 16 | 16 |
| Dated company news | 1 | 1 | 2 |
| Active jobs | 0 | 0 | 0 |

These are local extraction counts, not competition recall points or an official score. The live cohort observations were collected at different times; network variation is not a controlled speed comparison.

| Completed check | Valid results | Requests / cap | Seconds | External API cost |
|---|---:|---:|---:|---:|
| Full 300 + 5 diagnostic live run | 305/305 | 2,667 / 6,100 | 554.604 | $0 |
| Final-policy clean-clone live smoke | 100/100 | 1,124 / 2,000 | 357.202 | $0 |
| Final-policy historical source replay | 1,100/1,100 | 0 HTTP | 163.306 | $0 |

The five selected job cases returned 18 active postings across 5/5 companies. No previously accepted original-cohort website was lost. The final smoke retains two news-covered companies; the rejected advice-post gain is absent. Valid envelopes mean every input has a terminal result, including unavailable/ambiguous/failed fields, not that every requested fact was found.

The paired 34-site replay uses the same archived responses and restricted-DNS adapter for both policies. The control was `ecd555d` and the candidate `8be3442`; this isolates the news and description logic from the earlier leadership change. On the subset the adapter could reverify, websites stayed 22, descriptions increased 18→20, and news-covered companies increased 1→2. The live 34-site component verified all 34 sites, with 29 descriptions and two companies with news. The limited replay does not reproduce live site coverage.

The full live 305-company follow-up uses runtime `5a1a017bed8428d1d4694715bfaf69a9dfd475fa`. The subsequent precision-only change is `c78fa6509199926ff1f42d274e82bba8d03ad1e7`. `final-policy-audit.json` re-extracts accepted full-batch news from the exact saved bytes under that final policy. It is a policy audit, not another live full-batch run. The final 100-company smoke and final historical 1,100-company replay execute the final precision policy directly. Replay measures extraction/terminal envelopes, not live NAV or fresh network scaling.

**195 tests pass**, including in the independent locked clone. Targeted tests cover second-hop budgets, publication versus effective dates, foreign/other-company links, instructional posts and publisher suffixes, literal descriptions, and historical-name identity. The original test suite remains intact. The two initial positive crawl/description tests failed against the first isolated runtime before implementation. A saved-source refresh of the two new announcements produced zero duplicate claims and zero material changes.

## Running and remaining work

The evaluator command remains:

```
uv sync --frozen
uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --strategy balanced --pages 8 --requests-per-company 20 --max-seconds 2700 --no-discover
```

Append `--bulk <frozen-registry-file>` when supplied. These live measurements fetched identities normally without a frozen registry. Historical-name discovery depends on historical names being present in the supplied or fetched register records.

Firecrawl was used through the connected research tool and consumes that service's research credits. **It is not a dependency or credential requirement of the official command.** Official-command measurements have $0 model/search API costs. Full source bytes and envelopes remain in ignored local `out/experiments/firecrawl-patterns/` directories; only small reports are retained in Git. No UI redesign or source-identity relaxation was made.

The final tracked-file secret scan checked 190 files, including comparison against locally configured private values without printing them, and returned zero findings. Raw snapshots remain excluded.

The main remaining opportunity is reproducible discovery beyond registry, email, NAV and name-derived domain hints. The organizer's answer on supported model-based web search, alongside actual official subscores, will determine whether that route can be used for a final revision. These experiments strengthen the candidate but do not establish qualification or leaderboard rank.
