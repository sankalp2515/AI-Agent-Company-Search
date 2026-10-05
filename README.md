# OrgLens

Evidence-first research agent for Norwegian companies. Accepts an evaluator-owned batch of organisation numbers, retrieves public official records, verifies company sites, preserves immutable source snapshots, and emits one terminal result per company. Includes a portable responsive evidence viewer with search, comparison and JSON download.

Requires Python 3.12+ and uv. No API key or model is needed for the submitted default configuration.

## Install from a clean checkout

```sh
python -m pip install uv==0.10.9
uv sync --frozen
```

## One evaluator command

```sh
uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --max-requests 1800 --max-seconds 2400
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

The agent uses deterministic tool selection and evidence-bounded synthesis. It does not fabricate missing values or rely on generative claims. Jobs require a dated JSON-LD JobPosting, unexpired validity where given, and exact legal hiring-organisation name. Missing jobs are not reported as a zero job count.

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
