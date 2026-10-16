# Audit evidence — 17 October 2026

Executable code under audit: `a6cc772f9d367e3115af97374ab72e22180f3208`. [Full report](../../docs/SUBMISSION-AUDIT-2026-10-17.md).

- `fresh-input.jsonl`: new 100-company sample, organizer universe reservoir seed 20261017.
- `fresh-run-report.json`: live operational report, 100 valid envelopes / 673 requests / 139.984 seconds / $0 API charge.
- `fresh-claim-audit.json`: 1,408 legal-name and financial claim comparisons against retained source bytes. Includes field counts and accepted website methods. The other 2,261 claims are not adjudicated.
- `claim-audit.json`: saved smoke/refresh claim checks and adverse synthetic reproductions.
- `replay-run-report.json`: clean-checkout saved-source run; three changes are discussed in the full report. This used `--no-guess` and is not a controlled identical-settings run.
- `reproduce_audit.py`: repeat saved evidence checks and adversarial cases without network calls or credentials. Run from the repository root using `uv run --frozen python submission/audit-20261017/reproduce_audit.py`. Writes to ignored `out/audit-reproduction/`. Bad behaviors are observations, not assertions that they are acceptable.

Fresh response bytes and complete fresh envelopes remain in the local ignored `out/audit-20261017/fresh` folder. This public package contains a run report as permitted by the submission rules, not a complete independently replayable fresh-source archive. The saved smoke and refresh envelopes and referenced bytes are separately available in `submission/release` and are used by the reproduction script.

The `official-smoke`, `official-refresh` and `official-scale` run IDs in old reports are local labels chosen by the developer. They do not indicate an official Builderr run.
