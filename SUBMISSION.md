# Signalpost revision candidate — OrgLens

Prepared 19 October 2026. The recommended score-focused candidate enables verified search and bounded AI extraction. It is locally committed, not pushed or submitted. [Version 1](docs/SUBMISSION-V1-HISTORICAL.md) and the [preceding keyless candidate](submission/candidate-20261019/README.md) remain historical records.

| Required item | Value |
| --- | --- |
| Agent | OrgLens — evidence-first Norwegian company research |
| Repository | https://github.com/sankalp2515/AI-Agent-Company-Search |
| Executable commit | `7aa6649274b0c7d290d5e3dfa90165ff8de9a1a9`; the following release commit adds reports/docs only. Use the full release hash from `git rev-parse HEAD` when submitting. It must first be accessible on GitHub. |
| Install | `python -m pip install uv==0.10.9` then `uv sync --frozen` |
| Smoke and verification | [Hybrid candidate artifacts](submission/candidate-20261019-hybrid/README.md), with source/run relationships |
| Model | Groq `openai/gpt-oss-20b`, bounded literal paragraph selection; no model-written claims |
| Search | Approved SerpAPI and/or Tavily credentials, supplied through the environment |
| Other APIs | Enhetsregisteret, Regnskapsregisteret, NAV Job Vacancy Feed and verified company websites under robots.txt |
| Cost | Plan-dependent. Tavily-only scenario: at most $9.60 list-price search with 1,200 basic queries, plus metered Groq tokens. Mixed-provider cost is not verified. See the cost declaration below. |
| Licences | MIT application; beautifulsoup4/soupsieve MIT; certifi MPL-2.0; model/provider and source terms separately declared in [SOURCE-RIGHTS.md](SOURCE-RIGHTS.md) |
| Contact | Sankalp Wanjari — wanjarisankalp@gmail.com |

## One command for the hybrid candidate

After Builderr supplies approved search/model credentials through its secret environment:

```sh
uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --strategy balanced --pages 8 --max-requests 20000 --max-seconds 1800 --discover --max-search-queries 1200 --extract-ai --providers groq --max-model-calls 400
```

The request/time/API caps are engineering settings, **not confirmed official allowances**. Substitute the supplied shared limits before freezing the submission command. The declared 1,200 search / 400 model caps are scale settings, not counts measured on an official batch. The fresh 100-company hybrid tests use 3,000 requests, 900 seconds, 160 searches and 80 model attempts.

Configure `GROQ_API_KEY` and the approved `SERPAPI_API_KEY` and/or `TAVILY_API_KEY`. Personal-account credentials are not a reproducible competition dependency. The CLI deliberately fails if AI extraction is requested without a configured model; do not omit credentials and assume an AI run happened. With multiple search providers, the next is queried only after the previous candidates fail verification. Inputs always come from Builderr's supplied company file.

If a frozen registry is supplied, append `--registry registry.jsonl --registry-retrieved-at <actual retrieval timestamp>`. For refresh, append `--previous <previous envelopes.jsonl>` and retain its snapshot directory.

## Cost declaration

The [experiment record](docs/QUALIFICATION-CANDIDATE-2026-10-19.md) links current primary pricing sources and retains measured tokens/query counts. At Tavily's published $0.008 per basic-search credit, 1,200 queries allocate up to $9.60 before taxes and plan/free-allowance effects. For that **Tavily-only** scenario, configure only the approved Tavily search key and append `--search-cost-per-request 0.008 --max-api-cost 9.60`. Do not apply that rate to a mixed SerpAPI subscription chain without checking its plan.

Groq's list-price token component is `input_tokens × 0.075 / 1,000,000 + output_tokens × 0.30 / 1,000,000` USD. The protected public 100-company run used 10,946 input / 877 output tokens, about $0.001084 for the model component. Actual scale usage is unknown. Search spending flags do not cap model billing. The report preserves measured usage and leaves unverified total billing null.

The keyless fallback remains runnable with no personal credential and $0 external API cost, excluding compute/bandwidth:

```sh
uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --strategy balanced --pages 8 --max-requests 20000 --max-seconds 1800 --no-discover
```

This fallback executes no LLM or search API. The measured random-sample gain from hybrid research remains modest; the stronger public-example results must not be substituted for that sample. Use the hybrid revision when approved search/model access is available.

## User experience and evidence

Open `out/evaluation/index.html` directly on desktop or mobile. It provides company search, filters, cited summaries, two-company comparison, evidence locators and JSON export. No frontend installation or hosting is required. [Desktop](docs/images/comparison-desktop.png) and [mobile](docs/images/comparison-mobile.png) captures show the unchanged viewer layout using earlier development data; they are not an awarded UX score.

All inputs receive a terminal envelope, including failed, blocked and ambiguous research. Sources retain retrieval time, reporting period and exact-byte hashes. Raw snapshots remain local and ignored because third-party responses can embed credentials; do not upload them to GitHub.

## Readiness and acceptance

The selected implementation passes 154 tests in the working checkout and a clean locked clone. [Current measurements](docs/QUALIFICATION-CANDIDATE-2026-10-19.md) distinguish live public examples, the weaker random smoke, saved-source scale checks and historical runs. No local aggregate score or official 65/100 result is asserted.

Before activation, Builderr must confirm approved provider credentials, the shared budgets and revision acceptance. The [live page](https://www.builderr.ai/challenges/signalpost) advertises October 21 but still says revised hashes before October 18. No revised email has been sent, and the current instruction prohibits pushing.
