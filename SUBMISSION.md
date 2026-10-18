# Signalpost revision candidate — OrgLens

Prepared 19 October 2026. This is a local release candidate, not a submitted revision or an official qualification result. The historical version-1 submission is retained in [the archive](docs/SUBMISSION-V1-HISTORICAL.md).

| Required item | Value |
| --- | --- |
| Agent | OrgLens — evidence-first Norwegian company research |
| Repository | https://github.com/sankalp2515/AI-Agent-Company-Search |
| Exact revision | Use the full hash returned by `git rev-parse HEAD` on this release; the release handoff gives the pinned hash. A local commit must be pushed before Builderr can fetch it. |
| Install | `python -m pip install uv==0.10.9` then `uv sync --frozen` |
| Smoke report | [Current 100-company report](submission/candidate-20261019/smoke-run-report.json) |
| Models in declared command | None required. Optional AI modes are described below. |
| External API cost | $0 for the declared keyless command; compute and bandwidth excluded. |
| APIs | Enhetsregisteret, Regnskapsregisteret, NAV Job Vacancy Feed and verified company websites under robots.txt. NAV's published public token is fetched at runtime. No personal account credential is required. |
| Licences | MIT application; beautifulsoup4/soupsieve MIT; certifi MPL-2.0; official data and website access as documented in [SOURCE-RIGHTS.md](SOURCE-RIGHTS.md). |
| Contact | Sankalp Wanjari — wanjarisankalp@gmail.com |

## One evaluator command

```sh
uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --strategy balanced --pages 8 --max-requests 20000 --max-seconds 1800 --no-discover
```

The 20,000-request / 1,800-second limits are local engineering settings, **not confirmed official allowances**. Builderr must substitute its actual shared limits. If a frozen registry is supplied, add `--registry registry.jsonl --registry-retrieved-at <actual retrieval timestamp>`. Inputs are always the evaluator-supplied company numbers; the local sample never controls official runs.

Open `out/evaluation/index.html` directly on desktop or mobile to search companies, compare two profiles, inspect dated accounts, follow citations and expand evidence locators. The viewer is self-contained and requires no frontend installation or external hosting. Missing data stays explicit.

## Why this revision should improve the entry

- External research runs before the costly job-feed detail work. Stage budgets and NAV detail caps preserve research breadth.
- Publisher checks reject directories, platforms and conflicting company identities. Search-result mentions alone cannot prove a company's website.
- Source spans, feed URLs, Facebook profile IDs and social evidence locators preserve the actual evidence.
- Static careers/terms pages are excluded from generic news markup. Refresh caches are per run; saved-source replay retains original retrieval dates.
- Shared snapshot validation hashes once per invocation with bounded concurrency, while rechecking corruption on every later validation.
- The responsive viewer adds a compact, cited comparison overview. [Desktop](docs/images/comparison-desktop.png) and [mobile](docs/images/comparison-mobile.png) inspection captures use earlier development data; they illustrate the current viewer layout, not fresh research.

See [the experiment record](docs/QUALIFICATION-EXPERIMENTS-2026-10-18.md) for retained failures and limits. Structural validation and smoke coverage do not establish an official score or factual precision.

## Optional AI and search

`--extract-ai --providers groq --max-model-calls 60` enables bounded literal-quotation selection from an already verified website. The model selects a paragraph index or abstains; it cannot author claims or override identity checks. `--discover --max-search-queries 60` enables search candidates through configured providers. The declared keyless command enables neither option.

Local experiments used Groq `openai/gpt-oss-20b` plus optional SerpAPI/Tavily search. Provider model licences and service terms are separate from the application licence. Model token usage is recorded, but a complete paid official-run cost is not verified. Use an AI/search revision only when Builderr agrees to reproducible credentials and budgets. Do not send personal keys or raw snapshots in Git.

## Revision acceptance

The live challenge header says October 21, but its revision paragraph still says up to four revised hashes **before October 18**. On October 19, acceptance of another revision requires Builderr's clarification. This repository makes no assumption that the revision window was extended. No email or revised entry has been sent by this task.
