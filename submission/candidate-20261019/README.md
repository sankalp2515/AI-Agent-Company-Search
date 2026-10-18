# Revision candidate verification

Prepared 19 October 2026. These are engineering checks, not an official score.

- `smoke-run-report.json`: exact current-source live, keyless run; 100/100 terminal envelopes; evidence validation passed; 915 requests; 175.000 seconds under a 900-second / 2,000-request cap. All 100 identities, accounts, leadership and locations returned. External coverage: 9 websites, 8 descriptions, 4 companies with social profiles, no jobs. This remains a material coverage limitation.
- `smoke-input.jsonl`: public local test inputs. Official runs must instead use Builderr's supplied inputs.
- `tests.xml`: 127 passing regression tests. Browser layout inspection is a separate check, described in the submission instructions.
- `source-manifest.json`: SHA-256 fingerprints of every executable source file and locked dependency declarations used by the live runs.
- `clean-clone-smoke-run-report.json`: live run from a fresh local Git clone at implementation commit `75a51b179021c1414fae33e54a36f9103667f3d9`, empty Python 3.14 virtual environment and declared locked install, with no local `.env`. It returned 100/100 valid results in 163.767 seconds, with 9 websites and 8 descriptions. The clone also passed all 127 tests. An earlier pre-guard clean run found only 4 websites because of robots timeouts; source availability remains a coverage risk.
- `refresh-run-report.json` and `refresh-check.json`: pre-guard live refresh at implementation `159e512`, 100/100 valid results in 222.844 seconds, no duplicate claim IDs and no reported fact changes. Five companies retained last-known claims after failed refreshes. This tests existing refresh behavior, not a final-source refresh or complete fresh research.
- `identity-audit-recheck.json` and `identity-guard-regressions.json`: saved-source checks. The latest name/contact guard rejects 8 of 47 earlier scale matches, including the confirmed KINLAND I parent-brand and HANS SYLTE acquisition cases. Other rejections are conservative abstentions, not independently proved wrong companies. These are not fresh retrievals or an official score.

Reproduce the smoke run after the declared install:

```sh
uv run --frozen orglens run --input submission/candidate-20261019/smoke-input.jsonl --output out/smoke --run-id smoke --strategy balanced --pages 8 --max-requests 2000 --max-seconds 900 --no-discover
```

The generated `index.html` is the evidence-viewer entrypoint. Run outputs and raw evidence remain in ignored `out/`; raw source snapshots are deliberately not published in Git. The run report is sufficient for the organizer's requested smoke evidence. It does not certify semantic precision or qualification. $0 external API cost excludes compute and bandwidth.

`pre-identity-guard-scale-run-report.json` records a completed live scale run at `159e512`: 1,100/1,100 valid envelopes, 8,076 requests and 1,288.421 seconds against a 20,000-request / 1,800-second local cap. Its 90 websites include matches subsequently rejected by the identity audit. This report establishes operational completion of that earlier source, **not final identity precision or final-source live scale certification**. The final guard is checked separately against saved scale sources; replay is never presented as fresh research.

`final-identity-scale-replay-report.json` records 1,100/1,100 valid outputs in 101.891 seconds at the final source against saved observations, with guesses/search/model calls/jobs disabled. It found 68 websites and 46 descriptions from available replay observations; incomplete replay paths and stricter publisher rules can reduce coverage. These counts are not a fresh-run comparison. `final-replay-identity-check.json` confirms that neither of the two audited wrong-company cases publishes a website. This replay validates extraction and completion, not live scale time, current facts or qualification.

`secret-scan.json` is the final publishable-file scan. `artifact-hashes.json` fingerprints this folder's text review materials using SHA-256 after normalizing CRLF to LF, so Git checkout line-ending conversion does not invalidate them. Raw source snapshots and credentials are excluded.
