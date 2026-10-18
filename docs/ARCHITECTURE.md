# OrgLens architecture

## Active evaluator path

`orglens` is the console entry point declared in `pyproject.toml`. `src/orglens/cli.py` reads the supplied input and calls `run_batch` in `core.py`, then generates the HTML viewer. It does not choose an official company list.

```text
Evaluator input → input validation → official registry identity
                                      ↓
                  website candidates → identity gate → extraction
                                      ↓
                 optional lazy search fallback → identity gate
                                      ↓
                       filed accounts → roles → workplaces
                                      ↓
                          shared NAV job index
                                      ↓
                 refresh diff → cited templates → validation
                                      ↓
            envelopes.jsonl + run-report.json + snapshots + index.html
```

This is the selected `balanced` strategy. The legacy `baseline` strategy retains the earlier records/jobs-first order. Research is phased across all companies using a worker pool. HTTP transport shares request counters, per-host pacing and a deadline. Balanced external stages have request/time ceilings; later records and jobs retain reserved time. A source failure produces explicit states and errors. Final envelope completion is distinct from research success.

## Components

| Component | Responsibility | Active by default |
|---|---|---|
| `core.py` | Transport, registry anchoring, official records, site crawl, extraction, synthesis, refresh, validation | Yes |
| `names.py` | Norwegian name normalization, domain hypotheses and directory exclusions | Yes |
| `navjobs.py` | Shared NAV feed index and employer/subunit attribution | Yes |
| `viewer.py` | Self-contained browser viewer | Yes |
| `agent.py` | Model-directed tool loop and provider fallback | Only `--ai` |
| `discovery.py` | Lazy SerpAPI/Tavily candidate fallback; legacy Brave with declared cost | `--discover` / `--discover-brave` |
| `quotes.py` | Bounded literal paragraph selection on an independently verified site | Only `--extract-ai` |
| `costs.py` | Optional provider cost estimates | AI mode |
| `replay.py` | Extract from retained observations without live fetches | Only `--replay` |
| `simulator.py` | Local operational checks and independently supplied reference scoring | Only `simulate` |

## Evidence and refresh

Each claim references evidence with a source URL, retrieval timestamp, content hash, extraction locator and identity method. Raw response bytes live in content-addressed `.bin` files. Financial claims preserve the original period, currency and account type. Previous results supply change comparisons and last-known evidence; they are not relabelled as fresh observations.

The validator checks membership, states, evidence references and snapshot hashes. It does not independently establish semantic support or exact-company attribution. Regression tests preserve the corrected identity, refresh and source-locator failures documented by the audits. News cards and article metadata share one article/date claim with multiple evidence records.

## Optional AI mode

The selected hybrid command enables `--extract-ai` for literal description selection and `--discover` for bounded search hints. A model chooses a paragraph index or abstains; it cannot author facts or override identity. `--ai` separately enables the legacy model-directed research loop. The keyless fallback executes no language model. Official hybrid evaluation needs organizer-approved model/search credentials; personal keys are not submitted.

## Boundaries

Static HTML only; no browser rendering or PDF extraction. Workplaces are limited to the first 100 endpoint results. Research has checkpoints but no resume command. The supplied frozen registry must contain original BRREG objects or supported CSV columns; the eligible-universe list alone is not a substitute.
