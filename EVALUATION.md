# Verification and measured evidence

> Historical development notes follow. The [17 October independent audit](docs/SUBMISSION-AUDIT-2026-10-17.md) supersedes readiness claims here. The default candidate is deterministic v2, not the older optional AI submission. Current verdict: FIX BEFORE SUBMISSION.

AI upgrade: `--ai` now enables model-directed tool selection and Tavily discovery. New reports under `submission/ai-artifacts` supersede the deterministic baseline as AI submission evidence. The baseline metrics below remain historical and must not be described as LLM-agent runs. Coverage counters in run reports are availability-state counts, not independently measured fact recall. Hidden-label precision, coverage and qualification remain unverified.

The live smoke corpus is selected by seeded reservoir sampling from the organizer's 411,160-company universe. Seed 20261005 selects 100 companies. The independent scale sample uses seed 20261006 and selects 1,000; samples are operational exercises, not an independently labelled recall benchmark.

Regression suite covers wrong-company official responses, strict labelled-number identity, multiple-entity ambiguity, missing-versus-zero facts, unchanged and failed refreshes, duplicate input rejection, exact output membership, 1,100-company failure completion and viewer script-injection prevention. Further tests cover frozen-registry evidence and snapshot validity.

The first live smoke run emitted 100/100 envelopes, validated all evidence snapshot hashes, made 426 outbound requests, and finished in 66.078 seconds with $0 declared external API cost. External website coverage was zero in that sample; that is a coverage limitation, not a result to conceal.

The development scale run emitted 1,000/1,000 results in 683.485 seconds using 4,330 requests and $0 external API cost. Its request allowance was 6,000, not the unknown official evaluator budget. Initial external matching incorrectly accepted a property-manager directory through a name/address fallback. That fallback was removed and the precise failure became a regression test. The final-code saved-source replay accepted 10 websites (not the preliminary 14), 8 descriptions, 1 dated activity item and 1 company-declared owned-profile reference. Replay is labelled offline and preserves original retrieval times; it is not a new live result. Preliminary external assertions must not be submitted as final evidence.

Stored live results and run reports are packaged under `submission/artifacts/` once the final smoke/scale checks finish. See those reports for exact current metrics. No official score, recall percentage, or wrong-company error rate is inferred from completion. A manual evidence audit is required for published external claims.

Refresh compares field/value sets rather than response hashes or retrieval timestamps. Identical values cannot create false changes. Failed/blocked/ambiguous family refreshes retain prior supported claims as stale and preserve previous evidence. The default run always fetches fresh sources.

Clean install: locked uv sync and a second environment installation must both run the CLI and regression checks. Validation CLI checks output membership, valid states, evidence references and exact preserved snapshot hashes. These checks are necessary operational evidence, not sufficient to prove every natural-language claim.
