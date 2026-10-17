# Continue OrgLens from this exact workspace

## User request and current boundary

User: Sankalp Wanjari, `wanjarisankalp@gmail.com`. Project: OrgLens, Signalpost company research competition. Repository: https://github.com/sankalp2515/AI-Agent-Company-Search . Workspace: `E:\Codex Projects\Company-Search`.

The user explicitly asked Claude to continue the remaining implementation. Codex is completing only the already-started GitHub secret/history cleanup. **Do not restart the project or repeat the initial audit.** Do not call the agent ready merely because unit tests or envelopes validate. Optimize for supported exact-company external coverage and reliable execution; improve UX where it helps find, compare and verify facts.

## Security cleanup — do not undo

Read `docs/SECURITY-INCIDENT-2026-10-17.md`. Three Google-key alerts came from embedded keys in third-party website snapshots, not matches to local `.env`. All `submission/**/snapshots/` paths have been removed from rewritten normal branch history. `.gitignore` plus `scripts/check_secrets.py` plus CI prevent republishing them. Existing report/envelope hashes are preserved, not fabricated by redacting source bytes. Old public-package snapshot validation requires local original bytes now.

Backups are under ignored `out/security-history-backup.git` and `out/security-history-backup.bundle`; **never push these refs or restore the old history to GitHub**. Tracked WIP is also preserved in `out/claude-wip-before-history-purge.patch`; the current working tree already contains it, so do not blindly apply the patch again. GitHub cached old commits/alerts may survive a force-push; do not mark keys revoked.

No `.env` values or flagged keys should be printed, committed, pasted into prompts, or used to test validity. The broader scanner reports paths/types/counts only. New shell commands sometimes stalled for minutes, then recovered; pending commands may no longer have resumable IDs after turn changes.

## Current implementation changes — UNCOMMITTED, not submission verified

Read `git status --short` and review actual files before editing. These are intended unfinished changes, not unrelated user edits:

- `src/orglens/core.py`: exact-length JSON-LD org parsing (no suffix/LEI/DUNS masquerading); conflicting identifiers veto proof; removed registry partial-name and shared-director shortcuts; full legal name required for phone/address corroboration; bounded phone matching; full robots delay; parsed RSS/ISO date ordering; per-evidence/source-aware stale preservation across repeated refresh failures.
- `src/orglens/navjobs.py`: ranked conservative brand/locality candidate matching, optional exact-org indexing, malformed/failed/truncated feed handling, `row['research_sources']['nav_jobs']` metadata. Exact employer/subunit publication gate remains mandatory.
- `tests/test_coverage.py`: old expectation accepting director/domain-only evidence changed to rejection.
- `tests/test_integrity_fixes.py`: eight regression cases. Original red run observed **7 failed / 1 passed** before code edits. Post-edit verification must be checked or rerun.
- `tests/test_nav_coverage.py`: eight new cases; delegated agent observed all eight fail before implementation. Post-edit verification must be checked/rerun.
- `tests/test_viewer_workflow.py`: delegated UI agent wrote behavior tests, but **did not modify `viewer.py`** before its usage limit. This file may fail. It uses a small Node DOM boundary double and is not a real browser/layout test.

The security guard is a separate verified change: five focused tests failed when absent, then **5 passed** after implementation. Root will publish security changes and this handoff only. Agent/NAV/UI work stays local for you to finish, test and commit.

**Latest completed targeted check:** `tests/test_integrity_fixes.py tests/test_nav_coverage.py tests/test_coverage.py` returned **1 failed, 32 passed**. The remaining failure is `tests/test_nav_coverage.py::test_joined_employer_words_find_exact_entity`: feed employer `Uplink` was not discovered for legal name `UP LINK AS`; availability was `not_available` instead of `available`. Do not weaken the exact-orgnr publication gate to fix candidate discovery. All eight integrity regression tests passed in this run. See `out/claude-targeted-tests.txt`. The broader publishable working-tree scan covered 95 files with no findings. These are focused checks, not fresh smoke/scale or full-suite verification.

Review core refresh logic carefully: stale facts should survive multiple failed refreshes, while successful observation of removal must create a real change. Shared family availability (`activity`) cannot substitute for source success. New source metadata and exact source URL snapshots are available. Preserve original evidence across retries and detect legitimate additions/changes.

## Remaining implementation work, in order

1. Read current diffs and finish/test identity and source-aware refresh fixes. Strengthen same-home/customer-directory and group/parent adversarial cases; never weaken gates for coverage.
2. Verify NAV work and request caps. A feed page cap, detail failure or unqueried source cannot mean `not_available`. Brand candidate matching still requires detail orgnr/subunit proof.
3. Fix website coverage without weakening attribution: verify more contact/legal pages and permitted candidates, improve company news/careers extraction, exclude generic About/Privacy Article schema from dated news. Existing optional Tavily/AI discovery uses local keys but is not reproducible by the evaluator without organizer agreement. Do not spend or enable personal paid services silently.
4. Finish viewer behavior: no silent first-500 truncation, filtered profile/empty-state synchronization, stale facts readable with previous-evidence citations. Preserve existing style; avoid cosmetic redesign.
5. **Actually verify desktop/mobile** if browser tools are available. CUA Chrome and in-app creation repeatedly timed out; an old OrgLens tab was owned by another session. No desktop/mobile screenshot or layout verification has succeeded. Existing responsive CSS and DOM doubles do not establish mobile usability.
6. Run complete tests, a fresh 100-company smoke and refresh, plus 1,000–1,100 scale at explicit declared budgets. Use the actual evaluator full registry snapshot when available; the public universe is only eligibility data. Run reports must distinguish local tests from official runs.
7. Update README, SUBMISSION and readiness report to reflect corrected current behavior, exact pushed hash, source/cost disclosures, UI evidence and any remaining failures. Publish report/envelopes/viewer only after the secret guard passes; raw snapshots remain ignored/local.

## Existing evidence and baseline

Read `docs/SUBMISSION-AUDIT-2026-10-17.md` for detailed findings, architecture, rubric and priority. Before fixes, **49 tests passed** locally, clean checkout and Linux CI. Fresh seed 20261017: 100 inputs / 100 valid envelopes, 673 requests, 139.984 seconds, $0 API cost, 3,669 claims. 1,408 legal-name/financial claims matched retained original source values/org/currency/account type/period; 2,261 other claims were not adjudicated. Discovery: six websites, four descriptions, one company with jobs, two with company-published activity, five with linked profiles.

Saved 1,000-company run: 6,548 requests / 1,303.954 seconds under **20,000 requests / 5,400 seconds**. It does NOT prove adequate coverage with a 2,000-request official budget. Current contract leaves numeric official budgets to Builderr. Three official modules alone need roughly 3,000 requests for 1,000 companies even when frozen identity is supplied. Do not claim score/qualification from raw availability counts.

Local evidence: `out/audit-20261017/fresh`, saved runs `out/smoke-v5`, `out/scale-v5`, and other folders. Inspect reports for exact run provenance; do not assume identical code/settings. Public `submission/release` and older `artifacts`/`ai-artifacts` are historical. The old run IDs `official-smoke` etc. are developer labels, not official organizer scores.

## Commands to resume

```powershell
git status --short
git diff -- src/orglens/core.py src/orglens/navjobs.py tests/test_coverage.py
.venv\Scripts\python.exe -m pytest -q
git ls-files --cached --others --exclude-standard | Set-Content out/publish-files.txt
.venv\Scripts\python.exe scripts/check_secrets.py --file-list out/publish-files.txt
```

Check `out/claude-targeted-tests.txt`, `out/security-guard-red.txt`, `out/security-guard-green.txt` and `out/security-current-tree-scan.json` for completed results; rerun rather than infer pass from a queued command. Use `uv sync --frozen` on a clean clone. Existing candidate command:

```sh
uv run --frozen orglens run --input input.jsonl --output out/evaluation --run-id local --max-requests 2000 --max-seconds 2700
```

Those are historical test settings, not confirmed current official limits. Sampling example:

```sh
uv run --frozen orglens sample --universe challenge-materials/company-universe-2025.jsonl.gz --count 100 --seed 20261018 --output out/next-input.jsonl
```

## Rules and submission

Live primary sources: https://www.builderr.ai/challenges/signalpost ; https://www.builderr.ai/docs/signalpost-evaluation-harness.md ; https://www.builderr.ai/starter-briefs/signalpost-sources.md . Current rubric: 50 recall/coverage, 30 exact identity/evidence, 12 synthesis, 8 UX; qualification 65/100 official total. Recall uses 70% company / 30% claim recall within each external family against a checked union. A material wrong-company publication blocks an official result. No hidden reference or defensible official overall score is available locally.

Five versions total: initial plus four revised hashes. Contract says revisions close October 18, page says before October 18; main challenge October 21. Exact hour/timezone unknown. Current user date October 17, 2026, Asia/Calcutta. Do not lose time re-auditing the same context.

Contact/name filled in SUBMISSION.md: Sankalp Wanjari, wanjarisankalp@gmail.com, agent OrgLens. Email has NOT been sent. The previous verdict was FIX BEFORE SUBMISSION. Give a new evidence-based go/no-go after finishing and verifying the corrections; never promise an official win or manufacture a numeric score.
