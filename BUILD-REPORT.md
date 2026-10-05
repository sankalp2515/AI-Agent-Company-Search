# OrgLens build handoff

Prepared 5 October 2026. Local implementation and submission artifacts are complete; remote publication and submission have not been performed.

## Delivered

- Batch research CLI accepting fresh organisation numbers, without a fixed batch size.
- Official identity, financial accounts with periods, leadership and registered workplaces.
- Conservative website identity proof, static pages, structured jobs and dated activity, declared profile links.
- Immutable source bytes, hashes, retrieval timestamps, source locators and explicit availability states.
- Configurable shared request/time limits, private-destination protection, robots checks and per-host pacing.
- Evidence-bounded summaries, latest-filing freshness warnings, previous/current changes and stale-value retention.
- Offline replay with preserved original retrieval dates and no network fallback.
- Portable responsive evidence viewer with search, comparison, expandable sources and JSON export.
- Optional disabled Brave candidate discovery with declared costs, hard spending cap and no stored search snippets.
- Locked dependencies, regression suite, clean-environment install, CI configuration, output schema, source/licence declarations and submission email draft.

## Measured checks

Final live smoke: 100 inputs/100 results. Exact metrics are in `submission/artifacts/smoke/run-report.json`. All stored snapshot hashes and output membership were checked. This is execution evidence, not proof of official qualification.

Development live scale: 1,000 inputs/1,000 results; 4,330 requests, 683.485 seconds and $0 paid API cost. That used a 6,000-request development allowance. The final-policy offline re-extraction accepted 10 company sites and excluded four preliminary matches, including a property-manager directory contamination. The incorrect fallback was removed and regression-tested. Do not use preliminary profiles as the evaluated artifact.

Identical-source refresh: 1,000/1,000 results and zero changes. Both prior and current evidence remain traceable. Exact audit is in `submission/artifacts/external-audit.json`.

Regression results are stored as JUnit XML. Tests cover identity contamination, missing/zero amounts, reporting periods, frozen CSV/JSONL, source corruption, worker failures/budget completion, private URLs, budget races, discovery costs, script-injection defense and refresh idempotence.

## Remaining release inputs

1. Participant/team name and contact email.
2. Remote repository name/visibility and authority to publish it. Local exact commit and bundle are prepared separately in `submission/release.json`.
3. Organizer confirmation of actual time/request/cost limits, frozen registry format, output compatibility and deadline timezone. Questions/email draft are in SUBMISSION.md.
4. For competitive coverage improvement, a permitted search-provider key, plan rights and approved spending cap. An LLM key is optional and not required for this version. The search connector is contract-tested but unverified live.

The default version is reproducible with $0 declared external API cost. External coverage is still limited; it is not honest to claim this code already meets the 65-point threshold or will win. Broad registry coverage and correct execution are established. Qualification needs Builderr's official run; substantial discovery coverage remains the highest-priority improvement.

## Run

`uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id official --max-requests 1800 --max-seconds 2400`

Use the actual supplied batch and budgets. Include the frozen registry flags when provided. Keep source snapshot folders with the outputs. Read README.md for installation and optional replay/discovery.
