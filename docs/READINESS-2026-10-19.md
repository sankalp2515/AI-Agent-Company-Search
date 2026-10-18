# Revision handoff — 19 October 2026

Historical keyless release record. The newer [hybrid qualification candidate](QUALIFICATION-CANDIDATE-2026-10-19.md) and [current submission instructions](../SUBMISSION.md) supersede this release's test counts and recommended command. Metrics below remain tied to their original source.

OrgLens has a locally committed, reproducible revision candidate. Its executable source is verified; no official qualifying score has been measured. The release is not pushed or submitted by this task. See [SUBMISSION.md](../SUBMISSION.md) for the single run command, contact, licences, cost and viewer entrypoint.

## Verified evidence

The final implementation commit `75a51b179021c1414fae33e54a36f9103667f3d9` adds the last identity corrections to the earlier `159e512` candidate. A following release commit updates documentation and verification artifacts. [Source fingerprints](../submission/candidate-20261019/source-manifest.json) bind final smoke runs to the executable files, with explicit Git line-ending normalization; earlier scale/refresh runs are labelled separately.

- Full regression suite: 127 passing tests, including two new regressions for numbered entities and acquisition mentions.
- Fresh local clone at the final implementation commit: locked install into an empty Python 3.14 virtual environment, no `.env`, 127 passing tests, live 100-company run with all outputs and evidence validation passing.
- Final release smoke: 100/100 valid results, 915 requests, 175.000 seconds. Websites 9, descriptions 8, companies with linked profiles 4, jobs 0.
- Final clean-clone smoke: 100/100 valid results, 921 requests, 163.767 seconds. Websites 9, descriptions 8, companies with linked profiles 4, jobs 0. An earlier pre-guard clean run found only 4 sites after robots timeouts; the variation remains a coverage risk.
- Pre-guard live refresh at `159e512`: 100/100 valid results, 848 requests, 222.844 seconds. No duplicate claim IDs or reported fact changes. Failed refreshes retain old evidence with stale status. This is not claimed as a final-source refresh.
- The declared command uses no paid search/model API and no personal credential; external API cost is $0, excluding compute and bandwidth. Its optional AI modes are not enabled silently.

Published run reports are in [the candidate folder](../submission/candidate-20261019/README.md). Raw snapshots, personal keys and history backups remain excluded from Git. UI comparison inspection captures are included in the submission instructions; they are earlier development-data captures, not new research results or an awarded UX score.

## Improvement and limits

This revision prioritizes external research before costly NAV details, bounds network/API work, requires publisher identity before consuming search documents, preserves literal evidence locators and source dates, parses actual RSS/Atom article links, excludes common false news/profile records, and presents cited company comparisons on desktop and mobile. These address observed failures in the earlier approach.

The new scale audit exposed two further identity errors before the final release: KINLAND I AS lost its numbered qualifier, and an acquisition mention with a shared phone caused the parent's site to be assigned to HANS SYLTE AS. The final guard rejects both on their actual saved observations. It rejects 8 of 47 reviewed name/contact matches in total; the other six rejections are conservative abstentions, not confirmed wrong-company findings. Preserve the earlier scale metrics as pre-guard measurements, never as final identity certification.

The random smoke still has weak external coverage, and no independent full current reference proves recall above 35.77/50 or an overall 65/100. We cannot infer an official score from registry completeness, passing tests or viewer quality. Optional model-assisted extraction/search needs organizer-supported credentials and a verified cost budget before it becomes part of an official command.

The pre-guard live scale run completed 1,100/1,100 valid results in 1,288.421 seconds with 8,076 requests, within its local 1,800-second / 20,000-request cap. Its report is explicitly labelled pre-guard because the subsequent identity audit rejected some accepted sites. Final guard behavior is checked in a separate saved-source replay. There is no claim of a final-source live 1,100-company run. The final source does have two completed fresh 100-company runs, including its clean clone. A saved-source replay must never substitute for fresh research.

The final-source saved-scale replay completed 1,100/1,100 valid outputs in 101.891 seconds. It published no website for either audited wrong-company case. Its 68 websites and 46 descriptions reflect stricter rules and available replay paths with guesses/search/jobs disabled; they are not a fresh recall measurement. Final publishable-file scanning found no credentials. Evidence snapshots and history backups remain local and ignored.

## Before sending

The final release hash must be accessible on GitHub before the organizer can fetch it. Earlier instructions explicitly prohibit pushing, so it remains local until the user authorizes a push. Separately, the current page advertises October 21 but still limits revisions to before October 18. Builderr must confirm acceptance of a revision on October 19 and supply its actual shared request/time budget. Do not treat the local 20,000-request / 1,800-second settings as an official allowance.
