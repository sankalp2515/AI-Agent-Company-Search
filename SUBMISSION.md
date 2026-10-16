# Signalpost submission — OrgLens v2

| Required item | Value |
|---|---|
| Agent | OrgLens v2: evidence-first Norwegian company research agent |
| Repository | `[PUBLIC REPOSITORY URL]` |
| Exact commit | `[COMMIT HASH]` (take it from `git rev-parse HEAD` after pushing) |
| Install | `uv sync --frozen` |
| One run command | `uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --max-requests 2000 --max-seconds 2700` |
| Profiles | 100-company smoke result plus live refresh in `submission/release/smoke` and `submission/release/refresh`. 1,000 company profiles in `submission/release/scale` |
| Models | None required. The default agent is deterministic and tool-using; synthesis is fixed templates over verified claims. Optional `--ai` mode (Groq/NVIDIA/Cloudflare/Cohere + Tavily) is not part of the evaluator command |
| APIs | Brønnøysundregistrene (Enhetsregisteret entities, roles, subunits; Regnskapsregisteret accounts), NAV Job Vacancy Feed (public token or `NAV_FEED_TOKEN`), and company-owned websites under robots.txt. All free, no keys |
| Licences | MIT code; dependencies beautifulsoup4 (MIT), soupsieve (MIT), certifi (MPL-2.0); official data under NLOD/NAV terms. See SOURCE-RIGHTS.md |
| Expected cost per official run | **$0 external API cost**. About 7 HTTP requests per company. A 100-company batch uses about 740 requests and 2.5 minutes, within the 2,000-request / 45-minute / $10 limits. Compute and bandwidth are excluded |
| Contact | `[NAME, EMAIL]` |

## Email draft (not sent)

To: submit@builderr.ai
Subject: Signalpost entry — OrgLens v2 — [NAME]

Hello Builderr,

Please evaluate OrgLens v2, an evidence-first agent for Norwegian company research.

- Repository: [URL]
- Exact commit: [HASH]
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

Contact: [NAME, EMAIL]

Thank you.
