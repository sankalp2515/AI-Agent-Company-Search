from __future__ import annotations

import argparse
import gzip
import json
import random
import os
import math
from pathlib import Path

from .core import read_inputs, run_batch, validate, write_rows
from .viewer import render


def main():
    parser = argparse.ArgumentParser(prog="orglens")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Research an evaluator-supplied company batch")
    run.add_argument("--input", required=True)
    run.add_argument("--output", default="out/run")
    run.add_argument("--run-id", default="local")
    run.add_argument("--previous", help="Previous envelope JSONL; retain its snapshot directory")
    run.add_argument("--max-requests", type=int, default=1800)
    run.add_argument("--max-seconds", type=int, default=2400)
    run.add_argument("--workers", type=int, default=12)
    run.add_argument("--pages", type=int, default=4)
    run.add_argument("--modules", default="financials,leadership,locations,website")
    run.add_argument("--registry", help="Evaluator frozen BRREG original-object JSONL or semicolon CSV")
    run.add_argument("--registry-retrieved-at", help="Actual timestamp of supplied registry snapshot")
    run.add_argument("--replay", help="Offline extraction from a previous run directory; not a fresh live run")
    run.add_argument("--discover-brave", action="store_true", help="Opt-in search; BRAVE_API_KEY and declared costs required")
    run.add_argument("--search-cost-per-request", type=float)
    run.add_argument("--max-api-cost", type=float, default=0)
    sample = sub.add_parser("sample", help="Create a reproducible local test sample, never used in official evaluation")
    sample.add_argument("--universe", required=True)
    sample.add_argument("--count", type=int, default=100)
    sample.add_argument("--seed", type=int, default=20261005)
    sample.add_argument("--output", default="data/smoke-input.jsonl")
    check = sub.add_parser("validate")
    check.add_argument("--input", required=True)
    check.add_argument("--envelopes", required=True)
    check.add_argument("--snapshots")
    view = sub.add_parser("view")
    view.add_argument("--envelopes", required=True)
    view.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "sample":
        if args.count < 1:
            parser.error("Count must be positive")
        rng = random.Random(args.seed)
        reservoir = []
        with gzip.open(args.universe, "rt", encoding="utf-8") as stream:
            for i, line in enumerate(stream):
                item = json.loads(line)
                if i < args.count:
                    reservoir.append(item)
                else:
                    j = rng.randint(0, i)
                    if j < args.count:
                        reservoir[j] = item
        if len(reservoir) != args.count:
            parser.error("Requested more companies than universe contains")
        write_rows(args.output, reservoir)
        print(json.dumps({"sample": args.output, "companies": len(reservoir), "seed": args.seed}))
    elif args.command == "run":
        if min(args.max_requests, args.max_seconds, args.workers, args.pages) < 1:
            parser.error("Budgets, workers and pages must be positive")
        modules = tuple(m for m in args.modules.split(",") if m)
        if set(modules) - {"financials", "leadership", "locations", "website"}:
            parser.error("Unknown module")
        previous = [json.loads(line) for line in Path(args.previous).read_text(encoding="utf-8").splitlines() if line.strip()] if args.previous else None
        discovery = None
        if args.discover_brave:
            if args.replay:
                parser.error("Paid discovery cannot be used in offline replay")
            rate = args.search_cost_per_request
            if rate is None or not math.isfinite(rate) or rate <= 0 or not math.isfinite(args.max_api_cost) or args.max_api_cost <= 0:
                parser.error("Provide positive finite --search-cost-per-request and --max-api-cost")
            from .discovery import BraveDiscovery
            discovery = BraveDiscovery(os.environ.get("BRAVE_API_KEY"), rate, args.max_api_cost)
        rows, report = run_batch(read_inputs(args.input), args.output, run_id=args.run_id,
                                 requests=args.max_requests, seconds=args.max_seconds, workers=args.workers,
                                 previous=previous, pages=args.pages, modules=modules,
                                 registry=args.registry, registry_retrieved_at=args.registry_retrieved_at, replay=args.replay, discovery=discovery)
        render(rows, Path(args.output) / "index.html")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(0 if report["validation"]["passed"] else 1)
    elif args.command == "validate":
        rows = [json.loads(line) for line in Path(args.envelopes).read_text(encoding="utf-8").splitlines() if line.strip()]
        report = validate(rows, read_inputs(args.input), args.snapshots)
        print(json.dumps(report, indent=2))
        raise SystemExit(0 if report["passed"] else 1)
    else:
        rows = [json.loads(line) for line in Path(args.envelopes).read_text(encoding="utf-8").splitlines() if line.strip()]
        render(rows, Path(args.output))


if __name__ == "__main__":
    main()
