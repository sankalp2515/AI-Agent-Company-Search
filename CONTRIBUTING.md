# Contributing

Use Python 3.12+ and the locked environment:

```sh
python -m pip install uv==0.10.9
uv sync --frozen
uv run --frozen pytest -q
```

Describe the behavior you changed, the evidence supporting it and the command used to verify it. For research changes, measure exact-company attribution, supported coverage, requests and runtime on the same input before and after the change. Keep missing values distinct from zero and preserve original reporting periods.

Add regression cases for identity collisions, source failures and refresh behavior. Do not weaken identity rules to improve apparent coverage. Fixtures must be synthetic or have documented source rights. Never commit `.env`, personal API credentials or provider responses containing credentials.

The current audit is evaluation-only: its reproductions intentionally expose unresolved defects. They are not passing regression tests. Fixes should turn those cases into assertions that reject the bad behavior, then repeat the fresh smoke and evaluator-budget scale tests.
