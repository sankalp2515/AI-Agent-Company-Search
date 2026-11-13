# OrgLens recall experiments, 14 November 2026

Local candidate `d5b9bcffd08056653e281aaa631e0956d59922bb` on `codex/recall-awards-20261106`, based on `529c815`. The candidate worktree is independent of Claude's later changes. The remote submission remains separate.

The [13 November leaderboard](https://www.builderr.ai/challenges/signalpost#scoring) reports Karthik at 33.39/50 recall and 69.27/100 overall. Its notice says the next rerun requires 65/100 overall and 95% checked-claim accuracy. The stated date for updated commits for that rerun is 15 November. The general challenge close is 16 November. The organizer uses its own checked pool and a scaling step. Local coverage counts cannot reproduce those points.

| Check | Result |
|---|---|
| Name-derived Norwegian domains with the legal suffix | The discovery probe tried 2,276 DNS hypotheses for 1,138 previously unverified companies. Eleven companies had a resolving candidate. The crawler spent 67 HTTP requests and verified two new websites. |
| Same two company inputs with the suffix fallback disabled | 0 websites, 24 requests, 17.813 seconds. |
| Same two inputs with the suffix fallback enabled | 2 websites, 2 descriptions, 1 company-linked Facebook profile, 41 requests. This is a selected-positive check. |
| Existing financial responses, replay of 100 companies | 272 debt claims across 99 companies and 274 pre-tax result claims across 100 companies. No new HTTP requests for either field. |
| Live comparison against historical Builderr public examples | 97/97 debt values and 93/93 pre-tax values agree on exact company, period, currency and account type. |
| Keyless combined smoke, earlier integration | 100/100 valid, 1,663/2,000 requests, 535 seconds, 12 websites, 3 companies with social profiles, 8 with 43 public award records. The older report's news count of 3 consisted of food inspections. |
| Keyless combined smoke, 14 November | 100/100 valid, 1,664/2,000 requests, 496 seconds, 11 websites, 3 companies with social profiles, 8 with 43 public award records. No active jobs or company articles were published on this input. Started before the final publisher headline and sitemap robots checks. |
| Frozen-registry combined smoke, 14 November | 100/100 valid, 1,570/2,000 requests, 483 seconds, 11 websites, 3 companies with social profiles and 8 with awards. It ran with the tightened site identity rules. The final instructional-headline filter landed after it started. |
| Keyless combined development run, earlier integration | 300/300 valid, 3,994/6,000 requests, 922 seconds, 34 websites, 16 companies with social links, 33 with 215 awards. |
| Keyless combined scale run, earlier integration | 1,100/1,100 valid, 13,294/22,000 requests, 2,470 seconds, 133 website candidates published under the earlier policy, 73 companies with social links, 34 with company articles, 19 with inspections, 6 with active jobs and 102 with awards. Later identity checks withheld some publishers on targeted replay. The old report grouped inspections into news. |
| Latest awards connector replay with a frozen registry | 1,100/1,100 valid, 16.578 seconds, 0 HTTP requests, 102 companies and 649 awards. |
| Live awards refresh of five previous positives | 5/5 valid, 10 requests, no material award changes. |
| Desktop/mobile browser check | Compared two profiles at 1280px and 390px, verified award filtering and source links, and confirmed no horizontal page overflow. |

Elenergi's [website](https://elenergi-as.no/) shows organisation number 926678930 and links its own Facebook profile. [Skifertak](https://www.skifertakas.no/) gives the exact legal name and registered street address and postcode. The fallback derives these candidates from the runtime input's legal name. It applies the same verification and requires the complete publisher name including AS for an address or phone match.

The 300-company article audit found three unrelated stories from Radio Grenland. The current gate requires media-company stories to name the entity as the subject in the headline. Food safety records and awards have dedicated output fields. The earlier 300-company run contained eight company article candidates, three of which the final media gate rejects on replay. Builderr determines whether public awards earn recall credit.

The scale audit found a hosting directory and four ambiguous legal publishers among six targeted cases. The final identity replay withheld those five and kept the verified RAK Arkitektur site. It also retained both legal-suffix discoveries in a separate replay. An expanded replay covered 16 selected weak-proof sites and retained eight. A separate article audit rejected 19 instructional headlines from the scale output. The locked test suite passed 242 tests with the stricter gates.

Further probes found no qualifying new posts from nine advertised WordPress APIs. The NTB pressroom sitemap gave two name/domain overlaps across the archived 300 and 1,100 cohorts. One was a franchise parent match and the other was Frelsesarmeen. Jobbnorge's 1,218 public listings produced an exact normalized employer-name match for Frelsesarmeen only. The public index did not expose employer organisation numbers, so these jobs were not published. The TED exact-identifier probe returned no rows and the Norway control also returned no rows, so it establishes no estimate of TED coverage.

The NTB release sitemap test compared 33,888 release URLs across 12 months with 888 eligible names. Three URL slugs matched. Reading the releases resolved those to a building address, a technology term, and a Swiss company, so no exact Norwegian-company news was recovered.

For reproducibility, use the evaluator command in the repository README. Local run reports, review notes and browser logs are in the ignored `out/awards-evaluation` directory. The branch contains code and reproduction scripts. The raw external responses and any HTML that may contain embedded tokens stay in the ignored directories.
