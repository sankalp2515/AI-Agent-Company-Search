# OrgLens architecture

## Active evaluator path

`orglens` is the console entry point declared in `pyproject.toml`. `src/orglens/cli.py` reads the supplied input and calls `run_batch` in `core.py`, then generates the HTML viewer. It does not choose an official company list.

```text
Evaluator input → input validation → official registry identity
                                      ↓
                 filed accounts → roles → workplaces
                                      ↓
                          shared NAV job index
                                      ↓
                 website candidates → identity gate → extraction
                                      ↓
                 refresh diff → cited templates → validation
                                      ↓
            envelopes.jsonl + run-report.json + snapshots + index.html
```

Research is phased across all companies using a worker pool. HTTP transport shares request counters, per-host pacing and a deadline. A source failure produces explicit states and errors. Final envelope completion is distinct from research success.

## Components

| Component | Responsibility | Active by default |
|---|---|---|
| `core.py` | Transport, registry anchoring, official records, site crawl, extraction, synthesis, refresh, validation | Yes |
| `names.py` | Norwegian name normalization, domain hypotheses and directory exclusions | Yes |
| `navjobs.py` | Shared NAV feed index and employer/subunit attribution | Yes |
| `viewer.py` | Self-contained browser viewer | Yes |
| `agent.py` | Model-directed tool loop and provider fallback | Only `--ai` |
| `discovery.py` | Brave candidate discovery with declared cost | Only `--discover-brave` |
| `costs.py` | Optional provider cost estimates | AI mode |
| `replay.py` | Extract from retained observations without live fetches | Only `--replay` |
| `simulator.py` | Local operational checks and independently supplied reference scoring | Only `simulate` |

## Evidence and refresh

Each claim references evidence with a source URL, retrieval timestamp, content hash, extraction locator and identity method. Raw response bytes live in content-addressed `.bin` files. Financial claims preserve the original period, currency and account type. Previous results supply change comparisons and last-known evidence; they are not relabelled as fresh observations.

The validator checks membership, states, evidence references and snapshot hashes. It does not independently establish semantic support or exact-company attribution. The audit documents matching and mixed-source refresh defects in the current implementation.

## Optional AI mode

`--ai` enables a model-directed research loop with configured provider fallback and Tavily URL discovery. Published facts still pass through deterministic extraction. The default evaluator command does not execute a language model. Personal model/search credentials are not part of the reproducible default submission.

## Boundaries

Static HTML only; no browser rendering or PDF extraction. Workplaces are limited to the first 100 endpoint results. Research has checkpoints but no resume command. The supplied frozen registry must contain original BRREG objects or supported CSV columns; the eligible-universe list alone is not a substitute.
