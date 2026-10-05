# Signalpost submission preparation

Agent: OrgLens. Participant/team contact and public repository URL: pending user-provided values.

Exact commit: recorded in `submission/release.json` after local release creation. Do not submit an uncommitted working tree or substitute a later revision silently.

Install: `uv sync --frozen`

Run: `uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --max-requests 1800 --max-seconds 2400`

Adjust time/request budgets to the actual organizer-supplied limits. For supplied frozen registry input append `--registry registry.jsonl --registry-retrieved-at ACTUAL_TIMESTAMP`. The current public contract does not supply the final evaluator's exact schema or numerical budget.

Models/APIs/licences: no LLM, no paid API, public BRREG identity/roles/subunits/accounts endpoints, verified public company pages, deterministic summaries, MIT implementation and locked dependencies. See SOURCE-RIGHTS.md for restrictions and deployment requirements.

Expected external API cost per batch: $0 for this configuration, including 100/1,000/1,100 companies. Runtime and request cost scale with source availability, retries/redirects and configured budgets; see actual reports. Compute, bandwidth, storage and any future paid provider are not included in that API number.

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

This version uses no LLM or paid external API. Expected external API cost is $0 per official run. Source and licence declarations are in SOURCE-RIGHTS.md; known limitations are explicit in LIMITATIONS.md. Please supply the current evaluator limits and exact frozen registry/input/output contract so we can confirm compatibility.

Thank you,
[PARTICIPANT NAME]

## Organizer questions — not sent

Confirm new-entry deadline timestamp/timezone, official batch size and resource limits, frozen registry format and timestamp, formal output schema, supported evaluator credentials, field weights, viewer startup expectations, JBOX bonus criteria, eligibility and repository/licensing requirements. Current documents conflict with Unstop and some archived starter guidance, so do not invent these answers.

