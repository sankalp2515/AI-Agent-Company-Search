# Signalpost submission — OrgLens v2

> **Status 18 October 2026: participant reports version 1 submitted.** Its pinned executable commit is retained below. The organizer acknowledgement/score has not been inspected. See [the current revision strategy](docs/REVISION-STRATEGY-2026-10-18.md); later GitHub pushes do not update the frozen submission automatically.

| Required item | Value |
|---|---|
| Agent | OrgLens v2: evidence-first Norwegian company research agent |
| Repository | https://github.com/sankalp2515/AI-Agent-Company-Search |
| Exact commit | `29daa24c8ee9ef330ebc8c721168f6b2dce800d6` |
| Install | `uv sync --frozen` |
| One run command | `uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --max-requests 2000 --max-seconds 2700` |
| Profiles | 100-company smoke result plus live refresh in `submission/release/smoke` and `submission/release/refresh`. 1,100 company profiles in `submission/release/scale` (envelopes gzipped, viewer `index.html`). Tight-budget stress report in `submission/release/stress-1100-at-2000-requests-run-report.json` |
| Models | None required. The default agent is deterministic and tool-using; synthesis is fixed templates over verified claims. Optional `--ai` mode (Groq/NVIDIA/Cloudflare/Cohere + Tavily) is not part of the evaluator command |
| APIs | Brønnøysundregistrene (Enhetsregisteret entities, roles, subunits; Regnskapsregisteret accounts), NAV Job Vacancy Feed (public token or `NAV_FEED_TOKEN`), and company-owned websites under robots.txt. All free, no keys |
| Licences | MIT code; dependencies beautifulsoup4 (MIT), soupsieve (MIT), certifi (MPL-2.0); official data under NLOD/NAV terms. See SOURCE-RIGHTS.md |
| Expected cost per official run | **$0 external API cost** (no keys). Measured: 100 companies use 1,510 requests and 253 s; 1,100 companies use 15,451 requests and 1,976 s. Under a 2,000-request cap, 1,100 companies complete in 238 s with unqueried families reported as `failed`. Set `--max-requests` and `--max-seconds` to Builderr's actual limits. Compute and bandwidth are excluded |
| Contact | Sankalp Wanjari — wanjarisankalp@gmail.com |

## Before sending

1. Exact commit 29daa24c8ee9ef330ebc8c721168f6b2dce800d6 was verified from a clean GitHub clone: locked install, 80 tests and a live run producing valid envelopes and the viewer. Later implementation commit `0f51c30342dfc6cdbba3c8c94c1aae9c7301348c` adds opt-in search; it is not automatically part of submitted version 1.
2. Ask Builderr to confirm the official request/time budget and any frozen registry snapshot. When a snapshot is supplied, append `--registry <path> --registry-retrieved-at <timestamp>`.
3. Up to four revised hashes are allowed after version 1 (five versions total). On today's date, 18 October 2026, confirm whether revisions are still accepted: the contract says close October 18 while the challenge page says before October 18. Exact hour/timezone is unspecified.

## Original version-1 email template (historical; participant reports submission)

To: submit@builderr.ai
Subject: Signalpost entry — OrgLens v2 — Sankalp Wanjari

Hello Builderr,

Please evaluate OrgLens v2, an evidence-first agent for Norwegian company research.

- Repository: https://github.com/sankalp2515/AI-Agent-Company-Search
- Exact commit: 29daa24c8ee9ef330ebc8c721168f6b2dce800d6
- Install: `uv sync --frozen`
- Run: `uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --max-requests 2000 --max-seconds 2700`

It needs no API keys and has $0 external API cost.

For every company, it combines:

- official identity, accounts, roles and workplaces;
- active job ads from NAV's official feed, published only when the employer organisation number matches exactly;
- a verified company website found without a search API, published only with an exact identity proof;
- site-derived description, social profiles, contacts and dated activity;
- a cited narrative summary.

The repository includes the 100-company smoke result, a live refresh (0 changes), 1,100 company profiles, a tight-budget stress report and a responsive evidence viewer (`index.html`) that was verified on desktop and mobile.

Could you confirm the official request/time budget, and whether a frozen registry snapshot will be supplied?

Contact: Sankalp Wanjari — wanjarisankalp@gmail.com

Thank you.
