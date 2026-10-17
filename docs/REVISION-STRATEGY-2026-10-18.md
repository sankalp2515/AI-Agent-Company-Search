# OrgLens: version 1 review and revision strategy

Reviewed 18 October 2026, Asia/Calcutta. User reports version 1 has been submitted. No organizer acknowledgement or private score was available in this workspace.

## Current version and push state

- Documented submitted commit: `29daa24c8ee9ef330ebc8c721168f6b2dce800d6`.
- Latest implementation on local and GitHub `main`: `0f51c30342dfc6cdbba3c8c94c1aae9c7301348c`.
- The intervening implementation adds opt-in search discovery. It does not change version 1 already frozen with the organizer. A Git push is not a revised competition submission.
- Fresh full local suite: **87 passed in 16.03 seconds**; GitHub CI for the latest implementation also passed.
- Working tree was clean when the review began. No further implementation was silently applied during this research task.

## What version 1 actually does

The declared run command has neither `--ai` nor `--discover`. Both release reports have `agent: null` and `discovery: null`. Version 1 therefore runs deterministic tools and cited summary templates, not an LLM. Optional AI code is real but inactive under that command. The newer search implementation is also opt-in.

This choice made a no-key, $0 external-API baseline reproducible and isolated factual publication from model mistakes. It also left discovery and unstructured extraction weak. The right next step is a measured hybrid: deterministic identity/accounts/evidence, model help on unresolved research tasks, independently validated source spans. Adding a model to every company regardless of need is not a scoring improvement by itself.

## Measured bottlenecks

These are recalculated from release envelopes and run reports; source bytes were not re-adjudicated in this review. See `research-20261018/measured-analysis.json` under `submission/`.

| Metric | 100-company smoke | 1,100-company scale |
|---|---:|---:|
| Valid envelopes | 100 | 1,100 |
| Published claims | 3,780 | 41,551 |
| HTTP requests | 1,510 | 15,451 |
| Runtime seconds | 252.609 | 1,975.781 |
| Websites | 8 | 115 |
| Website descriptions | 7 | 67 |
| Linked social profile companies | 3 | 70 |
| Companies with job claims | 0 | 5 |
| Job claims | 0 | 6 |
| NAV detail requests | 411 | 4,264 |
| NAV detail share of all HTTP requests | 27.2% | 27.6% |
| Companies with company-published activity | 3 | 36 |

At scale this is **710.7 NAV detail requests per published job**. Some rejected candidates are necessary to enforce identity, but this yield demands candidate ranking, detail caching/deduplication and a global module cap before more candidates are added. The 100-company run spent 411 detail requests for no jobs.

Activity availability of 100/100 or 1,099/1,100 is mostly official registry history, not broad recent public news. Scale claims contain 5,596 registry events versus 189 company activity items. These categories must remain separate in evaluation and presentation.

At the documented 2,000-request cap, the saved 1,100-company stress run had 1,100 identity results and 895 available financial states, but **zero roles, workplaces, websites, descriptions, jobs or linked profiles**. Returning every envelope is operationally useful; it does not establish competitive research quality. Builderr's current numerical budget is unspecified. Confirm it and use the supplied full frozen registry anchor. It saves identity requests but cannot alone solve all module costs.

The prior same-100 search experiment, documented in `CLAUDE-WORKLOG.md`, raised websites from 8 to 10 using 62 queries and hit the 2,000-request cap at about 453 seconds. That is **31 search queries per additional verified website**, before counting source fetches. The five-company example added no website beyond the keyless baseline. The worklog's earlier near-100% hit and 15–20 recall-point statements were not measured official recall and must not guide submission claims.

## Current board and rules

The [live challenge](https://www.builderr.ai/challenges/signalpost) now reports an October 17 review: 57 submissions, 43 scored provisionally, 14 held, zero qualified. Karthik leads at **70.43***: recall 35.77, evidence 27.46, synthesis 7.20, UX 0.00. The asterisk explains a 300-company validated-evidence round with recall scaled from 40 available points to 50, excluding unavailable review/rating/sentiment evidence. It is not a declaration of qualification or a winner. This replaces the older October 5 / 60.80 comparison in historical reports.

Governing contract remains [scoring version 2](https://www.builderr.ai/docs/signalpost-evaluation-harness.md): 50 recall/coverage, 30 exact identity/evidence, 12 synthesis, 8 UX; 65 overall on a valid official run. The hidden checked collection determines recall. Company discovery rates are not recall denominators. UX being implemented is not proof that the evaluator awards eight points or even opens the intended file correctly; supply its exact launch/view instructions.

There are up to four revisions after version 1, not an entitlement to use them after the cutoff. Contract says revisions close October 18; page says before October 18. Today is October 18 locally; exact hour/timezone is unstated. Confirm whether revisions are still accepted and when each freezes before spending remaining slots. The main challenge closes October 21, a different date.

## Downloadable materials worth using

**Firecrawl attempt:** no Firecrawl MCP tool or runnable CLI was exposed in this session. A local installation was found at `E:\Firecrawl\firecrawl`; an isolated localhost-only Docker stack was started using its existing images, with model credentials disabled. The API never became reachable on port 3002 while waiting on the message broker. Shutdown was requested for that task-specific stack. No Firecrawl scrape succeeded. Documents were retrieved directly over HTTPS instead; do not label those downloads as Firecrawl output. No paid Firecrawl request was made. Existing unrelated Docker applications were not intentionally altered.

Fresh downloads and hashes are recorded in the research manifest. Full downloaded texts/archive remain in ignored `out/research-20261018`; original third-party documents are not copied into the public report.

| Material | What to extract from it | Caution |
|---|---|---|
| [Current contract](https://www.builderr.ai/docs/signalpost-evaluation-harness.md) | Envelope requirements, equal batch, frozen registry, evidence, revision policy | It leaves numeric budgets to official runs |
| [Research playbook](https://www.builderr.ai/starter-briefs/signalpost-agent-playbook.md) | Identity graph, source ladder, static/sitemap first, extraction layers, selective LLM | Architecture reference, not mandatory framework |
| [Learning harness](https://www.builderr.ai/starter-briefs/signalpost-learning-harness.md) | Development/validation split, strategy attempts, promotion rules, frozen policies | Hidden-score tuning is not allowed |
| [Source policy](https://www.builderr.ai/starter-briefs/signalpost-sources.md) | Permitted APIs/pages, exact attribution, retained provenance | Search snippets are not claim evidence |
| [Full brief](https://www.builderr.ai/starter-briefs/signalpost.md) | Participant checklist and current high-level score | Resolve conflicts against current contract |
| [Runnable archive](https://www.builderr.ai/signalpost-starter-kit.tar.gz) | Batch runner, refresh replay, connector examples, research code, output contract | Older proxy scorers are not the official evaluator |
| [Eligible company universe](https://www.builderr.ai/signalpost-company-universe-2025.jsonl.gz) | Sample unseen eligible companies and holdouts | Eligibility list is not the full identity registry |
| [Public product sample](https://www.builderr.ai/signalpost) | Source-first answers, questions, category layout and unknowns | UI inspiration, not ground truth for unseen companies |

The freshly downloaded archive matches the old SHA-256 `d48da9910ea7de07d2bf51ab265539a35fe07002a6c1ca5787df81316dfabbf6`. No new magic scorer appeared. Bundled `docs/external-footprint-loop.md` and `scripts/score_competition_v3.py` use **55/15/10/12/8** proxy weights, conflicting with the current **50/30/12/8** contract. They contain useful strategy examples, not governing qualification thresholds. Their experimental LinkedIn results do not grant access rights or prove OrgLens can repeat them.

## Why this apparently simple problem is hard

The registry lookup is straightforward and common to everyone. The scored discovery task is to find independently supportable signals across fragmented websites/brands/subunits, resolve them to exactly the requested legal entity, distinguish missing from blocked/unqueried, preserve dated evidence, and finish a fresh batch within shared constraints. An empty company website, a holding company, a brand owned by several entities, and a third-party recruiter create different failure modes. More pages or more model prose cannot substitute for supported exact-company facts.

The provisional board shows the distinction clearly: even a score above 65 is not a qualified official result. Our aim should be reproducible supported coverage, not a higher self-reported local number.

## Recommended four revision objectives

These are proposed engineering milestones, conditional on remaining submission time. Do not consume a version for an unverified bundle of new components.

### Revision 2 — buy back research budget

1. Cache each NAV detail by UUID within a run and index its exact employer org/subunit after a single verified fetch. Bound fuzzy candidate details globally and per company; skip broad generic-name candidates. Keep `failed`/partial states truthful.
2. Obtain official request/time budget and frozen registry interface. Reserve nonzero requests for website discovery before optional deep roles/subunits; use fair per-company or per-stage allocation so late modules are not starved.
3. Record request-to-supported-claim yield by connector. Treat substantial reduction from 4,264 NAV detail requests with no lost validated job claims on the same sample as the first measurable target.
4. Validate on the same smoke plus a held-out set. Do not conclude fewer wrong-company facts just because less was published; inspect rejected and accepted cases.

### Revision 3 — improve exact external discovery and extraction

1. Query only unresolved companies with high-value candidates, using legal name, municipality and site-derived aliases; prioritize useful deep links rather than reducing all search results to roots.
2. Expand verified-site sitemap/contact/careers/news/locations paths and readable text extraction. Preserve proof pages, dates, locators and raw local bytes.
3. Use Firecrawl/browser rendering only when static HTML demonstrably lacks usable content. Preserve the evidence/provenance boundary; rendered markdown is not automatically the original HTTP response.
4. Test PDFs only where financial/latest-filing gaps or public reports are actual opportunities. Do not replace working official numerical extraction with model estimates.
5. Require a gain in independently checked external company-field opportunities at the same budget and zero new material wrong-company publications. Personal search keys require an evaluator-supported credential plan.

### Revision 4 — add targeted AI where the rules help

Builderr explicitly permits LLMs and offers model keys for scoring on request. The submitted keyless choice is an implementation tradeoff, not a competition restriction. The old private multi-provider trial chain should not be the reproduction foundation.

Use a small bounded model with organizer-supported credentials to choose the next useful page, propose source-backed brand aliases, extract otherwise unparsed dated roles/locations/news with literal evidence spans, and produce concise synthesis from accepted claims. Deterministic publication code must verify spans, exact entity, typed values, timestamps and periods; the model cannot override them.

Current `--ai` needs work before promotion:

- Global defaults are 100 model calls and 25 search queries, which cannot supply a multi-step loop for every company in a 1,100-company batch. Target unresolved companies rather than imply equal full AI research.
- The loop stops searching/inspecting after a website is verified. It is mostly root discovery, not deep company intelligence research.
- The model highlights verified claim IDs; the rendered narrative remains a deterministic template. Enabling the flag alone does not add richer extraction or model-written synthesis.
- Agent research is scheduled after existing website and discovery phases, when low request budgets may already be exhausted.
- Search binds both orgnr and legal name into every model query, which may favor directories; candidate query reformulations need controlled validation.
- Optional search accounting defaults to a declared unit cost and cap of zero. A zero report is not proof of free provider usage. Concurrent cost reservations also need an atomic reserve-before-call check before using a paid cap.

Use one measured provider first, request/response token caps, a wall-clock allowance, and an explicit per-run cost declaration. Compare deterministic, search-only and targeted-AI configurations on identical inputs. Promote AI only when it adds supported facts per request/dollar without changing wrong-company behavior. No specific model/pricing recommendation was verified in this review.

### Revision 5 — freeze proven output and evaluator presentation

Carry only winning measured strategies, perform a clean install, fresh smoke/refresh and scale at actual official limits, inspect source-span correctness and wrong-company cases, and verify the exact desktop/mobile viewer path. Ensure the evaluator knows where `index.html` is and how claims/dates/stale facts are inspected. Freeze a new exact hash and run command, declarations and cost. Retain the previous valid version for rollback; do not submit an unstable final rewrite.

## Immediate organizer questions (draft only, not sent)

Ask for version-1 receipt and actual run report/category feedback; revision cutoff hour/timezone and whether a revision sent today is accepted; official batch size and request/time/API budget; full frozen registry path/schema/timestamp; organizer-supported model and search keys; exact UX entrypoint expected by the evaluator. These answers are more actionable than guessing a score from the public board. User permission is still needed before sending this message externally.

## Score targets without manufactured scoring

Arithmetic examples only: with evidence 28, synthesis 10 and UX 7, qualification needs recall 20/50; with the maximum 30+12+8, recall 15 suffices. Those are scenarios, not measured OrgLens scores or separate thresholds. No official OrgLens score or qualification probability can be computed from the available artifacts. The concrete diagnosis is **operational version 1 submitted; external coverage not yet demonstrated qualification-competitive, especially under a tight budget**.
