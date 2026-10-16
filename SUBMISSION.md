# Signalpost submission — OrgLens v2

> **HOLD — FIX BEFORE SUBMISSION (17 October 2026).** This is a prepared package and unsent email draft, not a submission or qualification claim. See [the independent audit](docs/SUBMISSION-AUDIT-2026-10-17.md). Agent code remains unchanged during this audit.

| Required item | Value |
|---|---|
| Agent | OrgLens v2: evidence-first Norwegian company research agent |
| Repository | https://github.com/sankalp2515/AI-Agent-Company-Search |
| Audited executable commit | `a6cc772f9d367e3115af97374ab72e22180f3208` (later documentation commits do not fix the audited defects) |
| Install | `uv sync --frozen` |
| One run command | `uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --max-requests 2000 --max-seconds 2700` |
| Profiles | 100-company smoke result plus live refresh in `submission/release/smoke` and `submission/release/refresh`. 1,000 company profiles in `submission/release/scale` |
| Models | None required. The default agent is deterministic and tool-using; synthesis is fixed templates over verified claims. Optional `--ai` mode (Groq/NVIDIA/Cloudflare/Cohere + Tavily) is not part of the evaluator command |
| APIs | Brønnøysundregistrene (Enhetsregisteret entities, roles, subunits; Regnskapsregisteret accounts), NAV Job Vacancy Feed (public token or `NAV_FEED_TOKEN`), and company-owned websites under robots.txt. All free, no keys |
| Licences | MIT code; dependencies beautifulsoup4 (MIT), soupsieve (MIT), certifi (MPL-2.0); official data under NLOD/NAV terms. See SOURCE-RIGHTS.md |
| Expected cost per official run | **$0 external API cost** for the default command. Fresh 100-company audit: 673 HTTP requests / 139.984 seconds. Saved 1,000-company run: 6,548 requests / 1,303.954 seconds under a 20,000-request / 5,400-second allowance. Current official numerical limits are supplied by Builderr and remain unconfirmed; the command's 2,000 / 2,700 caps are historical test settings. Compute and bandwidth are excluded |
| Contact | Sankalp Wanjari — wanjarisankalp@gmail.com |

## Before sending

1. Correct the identity and mixed-source refresh defects in the audit; rerun its reproductions and fresh smoke test.
2. Confirm Builderr's current budget, exact output contract and registry snapshot format; use `--registry` and its actual `--registry-retrieved-at` timestamp when supplied. The public eligible-universe list is not a full registry snapshot.
3. Test 1,000 and 1,100 companies at that budget. Complete envelopes with failed fields do not establish adequate coverage.
4. Verify search, comparison, evidence inspection and export on desktop and mobile; review snapshot redistribution rights.
5. Freeze the corrected commit and replace the hash in the email. First submission plus four revisions are allowed, five versions total. Contract says revisions close 18 October 2026; page says before October 18. Main challenge closes October 21. Exact cutoff timezone is unspecified: clarify it rather than assume local midnight.

## Email draft (not sent)

To: submit@builderr.ai
Subject: Signalpost entry — OrgLens v2 — Sankalp Wanjari

Hello Builderr,

Please evaluate OrgLens v2, an evidence-first agent for Norwegian company research.

- Repository: https://github.com/sankalp2515/AI-Agent-Company-Search
- Exact commit: [REPLACE WITH CORRECTED, VERIFIED COMMIT — current audited code is a6cc772f9d367e3115af97374ab72e22180f3208]
- Install: `uv sync --frozen`
- Run: `uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --max-requests 2000 --max-seconds 2700`

It needs no API keys and has $0 external API cost.

For every company, it combines:

- official identity, accounts, roles and workplaces;
- active job ads from NAV's official feed, published only when the employer organisation number matches exactly;
- a verified company website found without a search API, published only with an exact identity proof;
- site-derived description, social profiles, contacts and dated activity;
- a cited narrative summary.

The repository includes the 100-company smoke result, a live refresh (0 false changes), 1,000 company profiles and a responsive evidence viewer (`index.html`).

Contact: Sankalp Wanjari — wanjarisankalp@gmail.com

Thank you.
