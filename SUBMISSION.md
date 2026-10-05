# Signalpost submission preparation

Agent: OrgLens. Participant/team contact and public repository URL: pending user-provided values.

Exact commit: recorded in `submission/release.json` after local release creation. Do not submit an uncommitted working tree or substitute a later revision silently.

Install: `uv sync --frozen`

Run: `uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --ai --workers 2 --max-model-calls 300 --max-search-queries 50 --max-requests 2000 --max-seconds 2700`

Adjust time/request budgets to the actual organizer-supplied limits. For supplied frozen registry input append `--registry registry.jsonl --registry-retrieved-at ACTUAL_TIMESTAMP`. The current public contract does not supply the final evaluator's exact schema or numerical budget.

Models/APIs/licences: Groq/NVIDIA openai/gpt-oss-20b, Cloudflare @cf/meta/llama-3.1-8b-instruct-fp8-fast, Cohere command-r7b-12-2024, Tavily basic search, public BRREG identity/roles/subunits/accounts endpoints and verified company pages. Mistral mistral-small-2603 optional, not enabled by default. Models decide search/inspection/completion and select verified claims; deterministic gates and rendering prohibit invented published facts. MIT implementation and pinned Python dependencies. Hosted model/API terms are separate from the application licence; confirm trial, commercial and evaluator usage terms. See SOURCE-RIGHTS.md and PROVIDER-VERIFICATION.md.

Expected external API cost: measured tokens, model attempts, Tavily credit reservations and Cloudflare neurons appear in run reports. $0 is conditional on remaining free/trial allocations and disabled paid overage, NOT a verified invoice or reproducible official-run price. Partial retail-price sensitivity is reported separately; NVIDIA/Cohere retail pricing is unverified, so a complete paid estimate is withheld. Organizer-supplied keys and quotas still need confirmation. Compute, bandwidth and storage are excluded.

Required evidence: exact smoke-test input, final envelope output, run report, preserved snapshots, responsive index.html, regression report and release manifest. No precomputed profiles are presented as official scoring inputs.

## Email draft — not sent

To: submit@builderr.ai

Subject: Signalpost entry — OrgLens — [PARTICIPANT NAME]

Hello Builderr,

Please evaluate OrgLens, our evidence-first Norwegian company research agent.

Repository: [PUBLIC REPOSITORY URL]
Exact commit: [RELEASE HASH]
Contact: [PARTICIPANT EMAIL]

Install with `uv sync --frozen`. Run with the single command above against your supplied organisation-number batch. The repository includes the 100-company live smoke report, envelope outputs and preserved evidence artifacts. OrgLens returns exactly one terminal result per input and includes availability states, source/date/hash evidence, refresh diffs and a responsive comparison viewer.

This version uses a bounded multi-provider LLM research loop and Tavily candidate discovery. Its report declares measured API usage, model IDs, free-allowance assumptions and partial paid-price estimates; the official expected price requires your evaluator credential/quota arrangement. Source and licence declarations are in SOURCE-RIGHTS.md; known limitations are explicit in LIMITATIONS.md. Please supply the current evaluator limits, exact frozen registry/input/output contract and supported model/search credentials so we can confirm compatibility.

Thank you,
[PARTICIPANT NAME]

## Organizer questions — not sent

Confirm new-entry deadline timestamp/timezone, official batch size and resource limits, frozen registry format and timestamp, formal output schema, supported evaluator credentials, field weights, viewer startup expectations, JBOX bonus criteria, eligibility and repository/licensing requirements. Current documents conflict with Unstop and some archived starter guidance, so do not invent these answers.
