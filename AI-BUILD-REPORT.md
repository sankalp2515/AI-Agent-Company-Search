# OrgLens AI build and readiness — 5 October 2026

Implemented and locally tested. Not published, submitted, officially scored or qualification-certified. Participant/contact and repository decisions are deferred as requested.

## What is now an AI agent

`orglens run --ai` uses actual model decisions in a stateful observe/choose/execute loop: discover candidate URLs through Tavily, inspect permitted company pages, evaluate updated availability and finish by selecting verified claim fields. This is not assistant-prepared company data or fixed tool selection. The models cannot invent published financial values or override exact-company verification. A deterministic official-data foundation and evidence renderer are deliberate safety components of the hybrid agent.

Groq/NVIDIA GPT-OSS 20B, Cloudflare Llama 3.1 8B FP8-fast and Cohere Command R7B are live-tested fallbacks. Mistral model listing succeeds but generation returned 429, so it remains opt-in. JSON formats were tested with real research state; Groq built-in tools are disabled so only this application's bounded tools execute. Keys are read from environment/local .env, not embedded in code, browser or artifacts. No paid upgrade or external publication occurred.

## Final live random 100-company test

- 100/100 terminal envelopes; exact input membership and snapshot hashes passed.
- 635 total outbound requests, including model and search requests; 363.375 seconds.
- 141 model attempts; all 100 companies received model calls; 63 completed tool loops. The remaining loops stopped under validation, availability, cooldown or budget constraints. Terminal completion is not the same as full research completion.
- 20 Tavily basic queries/credit reservations, capped explicitly to conserve free allowances.
- Official identity/accounts/roles/subunit endpoints were available for all 100. Availability counters are not independent fact recall; an available endpoint does not prove a nonempty external field family.
- Zero verified websites/descriptions/jobs/activity/owned-profile fields in this final capped random run. This is a serious external-coverage limitation, not hidden by the working UI or official records.
- A separate three-company development discovery pilot used real search → inspection → completion and independently fetched/verified Charlottes Hobby's site and description. That is illustrative functionality, not representative recall or a current-code official score.

Reports/evidence are in `submission/ai-artifacts` after packaging. Repeating model decisions and live sources is nondeterministic; a new run is not expected to have identical request counts.

## Verification

35 regression tests passed in the workspace and a clean cloned checkout with fresh locked dependencies. Cases include rate-limit fallback, invalid JSON/action/summary rejection, shared search/model caps, wrong financial entity/missing identity, missing-vs-zero, evidence integrity, refresh behavior, source URL safety, injection-safe rendering, daily mean arithmetic and synthetic 1,000-company exhausted-AI-budget completion. The generated viewer JavaScript passed Node syntax checking.

A current-code 1,000-company saved-source replay returned all 1,000 profiles and passed snapshot/membership validation in 81.797 seconds. It made zero network requests and was not an AI inference run or fresh source test. The final live 100-company outputs were replayed for refresh/idempotence verification; original retrieval times remain preserved. All replay artifacts are labelled offline.

The local simulator checks operational contracts and optionally computes reviewed-reference local scoring. Without independently reviewed reference claims and publication/manual UX/synthesis reviews, it intentionally returns no score. It cannot reproduce Builderr's hidden collection, undisclosed family weights, human adjudication or infrastructure. No local pass implies 65/100 or prize eligibility.

## Expected costs

Measured final-run usage: Groq 24,740 input / 1,262 output tokens; NVIDIA 41,491 / 1,969; Cloudflare 21,680 / 437 and 104.5277 neurons; Cohere billed token units 28,730 / 660; 20 basic search credit reservations. Usage includes invalid-output attempts when provider counters were supplied; failed requests without usage are not assumed free.

Conditional cost within remaining free/trial allocations: $0, only if the accounts are genuinely free and paid overage is disabled. Account billing/remaining allowances were not verified. Known retail-price components total $0.163384 for this test, excluding unpriced NVIDIA/Cohere model usage. A same-workload linear 1,000-company sensitivity is $1.6338 for those known components only, NOT a complete official-run estimate. Official model/search credentials, unit rates, limits and workload need confirmation before a reproducible full cost declaration. No paid API service is inherently required by the challenge, but free quotas do not guarantee daily large-batch capacity.

## Rules, prizes and remaining readiness gaps

Current organizer detail sections require a 100-company smoke report, repository link, exact commit, one command, model/API/licence/cost declarations and contact. They say precomputed 1,000-profile manifests are not required. Current scoring is 50 coverage, 30 precision/evidence, 12 synthesis, 8 UX; qualification is at least 65 overall on an official valid run, without the older separate 21/35 gate. Unstop's older scoring, 100-company daily batch and numeric budget conflict with this contract; confirm final evaluator rules with organizers rather than assuming either numeric budget.

Main rewards require qualification and final ranking. JBOX's separate bonus additionally requires a qualifying JBOX-built agent; this Python implementation does not claim that bonus. A full SaaS product is not required; the reproducible agent and evidence viewer serve the specified workflow.

Remaining: materially improve external coverage and loop completion; independently audit public facts; confirm evaluator output/frozen-registry schema, budgets and reproducible provider credentials/terms; establish an independent local reference; complete repository access/contact choices and a final cost declaration. No guarantee of winning or qualification is justified by these tests.

## One runnable AI command

```sh
uv sync --frozen
uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --ai --workers 2 --max-model-calls 200 --max-search-queries 20 --max-requests 2000 --max-seconds 900
```

The install step is separate; the second line is the one agent command. These are tested local workload caps, not asserted official limits. Increase caps only within verified quota/cost allowances and organizer constraints. For a supplied official frozen registry use its real path/timestamp. See README and SUBMISSION for options.

Official sources: https://builderr.ai/challenges/signalpost , https://builderr.ai/guidelines , downloaded evaluation contract, and provider documentation linked in PROVIDER-VERIFICATION.md. Local exact release hash and archive checksum are recorded separately after packaging.
