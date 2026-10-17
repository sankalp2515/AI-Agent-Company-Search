# Embedded website keys in public evidence snapshots

## Findings

GitHub secret scanning reported three Google API key alerts. Selected alert metadata and evidence URL metadata traced the matches to retained third-party pages on `skantrans.no`, `scanslep.no` and `seeyou.no`. Maps-related code was observed on the first and third domains. No matching key value equals any configured local `.env` value in the in-memory comparison. No flagged key was printed, tested, used or revoked.

This is evidence of embedded third-party website credentials being republished with raw page bytes, not evidence that the maintainer's configured provider credentials were exposed. It does not establish whether the third-party keys are restricted or still active. The previous configured-value-only scan did not cover this risk adequately.

## Remediation

- Preserved a full Git mirror and bundle locally under ignored `out/` before rewriting history.
- Removed every `submission/**/snapshots/` path from the rewritten branch history; exact retained responses are no longer a public artifact. Reports, envelopes and evidence hashes remain, but public-clone snapshot validation/replay of old packages now requires privately retained original bytes.
- Added a Git ignore rule and a tested scanner rejecting public raw snapshots, configured private values and common credential patterns. CI invokes the scanner against tracked files.
- Kept unfinished identity/refresh/NAV edits local for Claude; they are not part of this security-only publication.

Do not redact a raw snapshot and keep claiming its original hash or complete evidence fidelity. Raw evidence must remain in ignored local storage or separately controlled storage. The challenge permits a public 100-company run report; publishing full raw pages is unnecessary.

## Remaining boundaries

A force-push removes the snapshots from normal branch history; it cannot revoke third-party keys or erase other people's clones. GitHub may retain cached commit/blob views and secret-scanning records. No alert is labelled revoked or false-positive without supporting evidence. Contact GitHub Support if cached historical views also require removal. Do not import the recovery backup into GitHub: it intentionally contains the pre-cleanup history.

Local recovery locations:

- `out/security-history-backup.git` — mirror at old commit `e7c56653a9098bfb260d68b36759b0b454b35dfb`.
- `out/security-history-backup.bundle` — backup of all original refs.
- `out/claude-wip-before-history-purge.patch` — tracked unfinished code changes before history cleanup.

Treat these backups as local-only. Earlier audit reports reference historical commit hashes that changed during the purge. They are historical records, not instructions to restore old public history.
