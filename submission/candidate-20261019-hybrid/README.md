# OrgLens hybrid revision candidate

Executable commit: `7aa6649274b0c7d290d5e3dfa90165ff8de9a1a9`. Release documentation can follow this commit without changing its executable fingerprint. This candidate remains local; no push or revised submission is authorized by the current instruction.

See [the measured experiment record](../../docs/QUALIFICATION-CANDIDATE-2026-10-19.md) and [submission instructions](../../SUBMISSION.md). Raw snapshots, personal keys and history backups are excluded. Run reports preserve failures and never manufacture a qualification score.

The public example cohort is enriched and previously reviewed. The random smoke cohort is broader and has much lower external coverage. Saved-source scale replay checks extraction and output completeness; it does not establish fresh scale recall or network performance.

The source manifest lists exact run/source relationships. Older reports in `candidate-20261019/` belong to the preceding keyless release and remain historical evidence.

| Artifact | Measured result |
| --- | --- |
| [Broader live smoke](smoke-run-report.json) | 100/100 valid, 389.937 seconds, 1,702 requests; 12 websites, 10 descriptions, 6 companies with profiles; NAV index completed |
| [Live public examples](public100-run-report.json) | 100/100 valid, 483.250 seconds, 1,535 requests; 73 websites, 61 descriptions, 45 companies with profiles; NAV public-token failure retained |
| [External news/evidence audit](final-public100-audit.json) | 24 companies / 134 news facts; all 32 dated-card evidence records retain literal date/headline/link; no article/date duplicates found |
| [Historical URL comparison](final-public100-comparison.json) | 71/97 website hosts; 73/91 social URLs across 35/44 positive companies; social-family 70/30 arithmetic 79.75%; no overall score inferred |
| [Saved-source scale](scale-replay-run-report.json) | 1,100/1,100 valid in 192.734 seconds; zero network calls; not a live scale result |
| [Pre-correction random run](prior-random-run-report.json) | 100/100 valid, 11 websites / 9 descriptions; NAV failure retained; source explicitly predates final fallback/token changes |
| [Earlier clean-clone live identity check](clean-live-run-report.json) | 3/3 valid; correct KAEFER child site; abstentions on the two previously audited problem cases; exact source labelled in manifest |

The selected implementation also passes all 154 tests in a locked local clone. [Source fingerprints](source-manifest.json) bind executable files and reports using LF-normalized UTF-8 text, matching Git's canonical files. Raw snapshots remain available only in ignored local storage; public run reports alone cannot replay or independently validate those bytes.

The two historical website disagreements are preserved: Studix's currently verified `.no` domain differs from the old `.com` example; KAEFER Energy's independently verified company site replaces the old group portal. Do not "fix" these by copying historical URLs.
