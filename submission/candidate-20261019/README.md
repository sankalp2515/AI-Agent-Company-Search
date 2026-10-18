# Revision candidate verification

Prepared 19 October 2026. These are engineering checks, not an official score.

- `smoke-run-report.json`: exact current-source live, keyless run; 100/100 terminal envelopes; evidence validation passed; 919 requests; 167.844 seconds under a 900-second / 2,000-request cap. All 100 identities, accounts, leadership and locations returned. External coverage: 9 websites, 8 descriptions, 4 companies with social profiles, no jobs. This remains a material coverage limitation.
- `smoke-input.jsonl`: public local test inputs. Official runs must instead use Builderr's supplied inputs.
- `tests.xml`: 125 passing regression tests. Browser layout inspection is a separate check, described in the submission instructions.
- `source-manifest.json`: SHA-256 fingerprints of every executable source file and locked dependency declarations used by the live runs.

Reproduce the smoke run after the declared install:

```sh
uv run --frozen orglens run --input submission/candidate-20261019/smoke-input.jsonl --output out/smoke --run-id smoke --strategy balanced --pages 8 --max-requests 2000 --max-seconds 900 --no-discover
```

The generated `index.html` is the evidence-viewer entrypoint. Run outputs and raw evidence remain in ignored `out/`; raw source snapshots are deliberately not published in Git. The run report is sufficient for the organizer's requested smoke evidence. It does not certify semantic precision or qualification. $0 external API cost excludes compute and bandwidth.

The previous 1,100-company attempt produced valid artifacts but no completion report. It is not presented as a completed release run. The new release scale check is evaluated separately.
