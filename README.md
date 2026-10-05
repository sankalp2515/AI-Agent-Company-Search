# OrgLens

Evidence-first research agent for Norwegian companies. Accepts an evaluator-owned batch of organisation numbers, retrieves public official records, verifies company sites, preserves immutable source snapshots, and emits one terminal result per company. Includes a portable responsive evidence viewer with search, comparison and JSON download.

Requires Python 3.12+ and uv. AI mode requires a configured model key and Tavily key; the deterministic baseline remains available without keys. Local `.env` is loaded without executing its contents, and existing process environment variables take precedence.

## Install from a clean checkout

```sh
python -m pip install uv==0.10.9
uv sync --frozen
```

## One evaluator command

```sh
uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --ai --workers 2 --max-model-calls 300 --max-search-queries 50 --max-requests 2000 --max-seconds 2700
```

Replace the input path with Builderr's supplied batch. JSONL objects with `organisation_number`, JSON arrays or text files with one number per line are accepted. Batch size is inferred; no hardcoded 100-company limit. Adjust explicit budgets to the actual evaluator limits; the current organizer contract does not confirm Unstop's older numerical limits.

The default request budget is conservative. For a large official batch use the supplied frozen registry snapshot to avoid spending one network request per identity. Original official-object JSONL is supported:

```sh
uv run --frozen orglens run --input input.jsonl --registry registry.jsonl --registry-retrieved-at 2026-10-05T00:00:00Z --output out/evaluation --run-id official --max-requests 2000 --max-seconds 2400
```

Use the real snapshot timestamp, never the example date above. Exact snapshot format/budgets require organizer confirmation. When a supplied snapshot lacks a company, live registry identity lookup is used.

## Outputs

- `envelopes.jsonl`: one result per input, in input order.
- `run-report.json`: completion, coverage states, requests, costs and runtime; not an official score.
- `snapshots/*.bin`: immutable exact response bytes addressed by SHA-256.
- `checkpoint.jsonl`: partial per-phase recovery artifact; not a final result.
- `index.html`: self-contained responsive viewer; open directly in a browser.

Keep the entire output directory. Evidence spans/pointers and content hashes refer to these snapshots. Earlier output directories must also be retained for refresh verification.

```sh
uv run --frozen orglens validate --input input.jsonl --envelopes out/evaluation/envelopes.jsonl --snapshots out/evaluation/snapshots
uv run --frozen orglens run --input input.jsonl --output out/refresh --previous out/evaluation/envelopes.jsonl --run-id refresh
uv run --frozen pytest -q
```

## Local sample

Download the official universe from https://builderr.ai/signalpost-company-universe-2025.jsonl.gz. The competition package includes the exact smoke-test inputs; the universe download is only for additional testing.

```sh
uv run --frozen orglens sample --universe signalpost-company-universe-2025.jsonl.gz --count 100 --seed 20261005 --output data/smoke-input.jsonl
uv run --frozen orglens run --input data/smoke-input.jsonl --output out/smoke --run-id smoke --max-requests 1600 --max-seconds 1200
```

## Research policy

Registry organisation numbers anchor legal identity. Website publication requires one unambiguous labelled exact organisation number on the homepage or in a site footer. Name/address coincidences, customer-directory mentions, search snippets and URL similarity never authorize publication. Parent, property-manager and group websites are withheld when exact legal ownership is uncertain.

Static public HTML and JSON-LD only. Robots denial and inaccessible robots policies stop site research. Redirect destinations are validated; private/local/reserved IPs, credentials in URLs and nonstandard ports are rejected. No LinkedIn, Meta, Indeed or similar platform scraping. Company news is labelled company-owned activity, not independent sentiment.

With `--ai`, a real model chooses search, candidate inspection and completion actions from observed state. Groq, NVIDIA, Cloudflare and Cohere are a bounded fallback chain; authentication failures disable a provider, and rate limits trigger independent cooldowns. Mistral is opt-in because live generation returned 429. Model calls and search calls count toward the shared request/time budget. A global attempt cap stops further AI work while retaining complete deterministic baseline results. Therefore a capped large run can contain companies without model calls; the report discloses this.

Models select verified claim fields for the summary; code resolves their evidence and renders facts. Arbitrary model-generated prose and numbers are not published. All facts retain deterministic verification. Jobs require a dated JSON-LD JobPosting, unexpired validity where given, and exact legal hiring-organisation name. Missing jobs are not reported as a zero job count.

## AI configuration, cost and simulation

Copy `.env.example` to a local `.env` and populate credentials without committing them. Supported aliases include the existing `NVDIA_API_KEY`, `Cloudflare_API_KEY` and `AccountID`. `--providers` sets the fallback order. The default models were verified live; model IDs may be overridden with `GROQ_MODEL`, `NVIDIA_MODEL`, `CLOUDFLARE_MODEL`, `COHERE_MODEL`, or `MISTRAL_MODEL`. Overrides require separate model/terms verification before submission. No paid-account upgrade is performed. The application cannot prevent a provider charging an already-paid account: disable paid overage in account dashboards.

Tavily basic search is enabled only in AI mode, using `TAVILY_API_KEY`. It does not publish snippets or provider-generated answers. SerpAPI is not integrated. The cost report separates measured usage, conditional free-allowance cost, partial retail estimates and unverified invoice cost. Never claim a complete paid-price estimate when a provider's tariff is unknown.

```sh
uv run --frozen orglens simulate --input input.jsonl --envelopes out/evaluation/envelopes.jsonl --snapshots out/evaluation/snapshots --report out/evaluation/run-report.json --output out/simulation.json
```

This simulator checks batch membership, evidence references/hashes and declared budgets. It is NOT Builderr's evaluator. Optional `--reference reviewed-reference.json` supplies independently reviewed claims, local field-family weights, per-publication correctness/evidence/company reviews and manual synthesis/UX scores. Without those labels, it intentionally reports no score. See `SIMULATOR.md`. Clean install and regression tests do not establish semantic accuracy or qualification.

## Submission

See [SUBMISSION.md](SUBMISSION.md), [SOURCE-RIGHTS.md](SOURCE-RIGHTS.md), [EVALUATION.md](EVALUATION.md), and [LIMITATIONS.md](LIMITATIONS.md). Outputs are operational test artifacts, not qualification evidence. Final repository URL and participant contact details must be filled before sending. No automatic submission or email is performed.

## Optional discovery and reproducible replay

An opt-in Brave Search adapter is included to find candidate sites when registry links are missing or invalid. It is disabled by default and has not been live-tested because no key was supplied. Set `BRAVE_API_KEY` securely, confirm your plan permits this use, and explicitly provide the real unit price and spending cap:

```sh
uv run --frozen orglens run --input input.jsonl --output out/discovery --discover-brave --search-cost-per-request YOUR_PLAN_UNIT_PRICE --max-api-cost YOUR_APPROVED_CAP
```

Replace price/cap placeholders with numbers. There is no default price assumption. Provider results remain in memory; only independently fetched company pages become evidence. Search calls consume the same outbound-request budget, credentials are sent only to the fixed HTTPS API endpoint, and redirects are disabled for the authenticated request. Contract tests cover filtering and cost caps; live provider performance is unverified.

Replay does not contact sources or claim freshness. It preserves the original retrieval times:

```sh
uv run --frozen orglens run --input input.jsonl --output out/replay --replay out/evaluation --run-id replay
```
