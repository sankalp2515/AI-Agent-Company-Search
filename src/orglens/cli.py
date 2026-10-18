from __future__ import annotations

import argparse
import gzip
import json
import random
import os
import math
from pathlib import Path

from .core import read_inputs, run_batch, validate, write_rows
from .navjobs import NavJobs
from .viewer import render


def main():
    from .agent import load_env
    load_env()
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
    run.add_argument("--pages", type=int, default=5)
    run.add_argument("--strategy", choices=("baseline", "balanced"), default="baseline", help="Experimental bounded external-first allocation; baseline preserves original phase order")
    run.add_argument("--modules", default="financials,leadership,locations,jobs,website")
    run.add_argument("--nav-days", type=int, default=40, help="Window of NAV job-feed changes indexed for active ads")
    run.add_argument("--no-guess", action="store_true", help="Disable keyless name-derived website candidates")
    run.add_argument("--registry", help="Evaluator frozen BRREG original-object JSONL or semicolon CSV")
    run.add_argument("--registry-retrieved-at", help="Actual timestamp of supplied registry snapshot")
    run.add_argument("--replay", help="Offline extraction from a previous run directory; not a fresh live run")
    run.add_argument("--discover", action="store_true", help="Opt-in search discovery (SerpAPI, Tavily) using keys from the environment; not part of the evaluator command")
    run.add_argument("--no-discover", action="store_true", help="Force-disable search discovery")
    run.add_argument("--discover-brave", action="store_true", help="Opt-in search; BRAVE_API_KEY and declared costs required")
    run.add_argument("--search-cost-per-request", type=float)
    run.add_argument("--max-api-cost", type=float, default=0)
    run.add_argument("--ai", action="store_true", help="Model-directed research with Tavily; API usage consumes account allowances")
    run.add_argument("--extract-ai", action="store_true", help="Bounded model selection of literal description quotes from already verified sites")
    run.add_argument("--providers", default="groq,nvidia,cloudflare,cohere", help="Ordered fallback chain; Mistral opt-in until its quota is available")
    run.add_argument("--max-model-calls", type=int, default=100)
    run.add_argument("--max-search-queries", type=int, default=25)
    run.add_argument("--agent-steps", type=int, default=6)
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
    simulate = sub.add_parser("simulate", help="Local contract gates and reviewed-reference scoring; NOT the official evaluator")
    simulate.add_argument("--input", required=True)
    simulate.add_argument("--envelopes", required=True)
    simulate.add_argument("--snapshots", required=True)
    simulate.add_argument("--report", required=True)
    simulate.add_argument("--reference", help="Independent reviewed reference JSON, never auto-generated from this run")
    simulate.add_argument("--output", default="out/simulation.json")
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
        if set(modules) - {"financials", "leadership", "locations", "jobs", "website"}:
            parser.error("Unknown module")
        previous = [json.loads(line) for line in Path(args.previous).read_text(encoding="utf-8").splitlines() if line.strip()] if args.previous else None
        discovery = None
        agent = None
        quote_selector = None
        if args.extract_ai:
            if args.replay:parser.error('Model quote selection cannot be used in offline replay')
            from .agent import providers_from_env
            from .quotes import QuoteSelector
            quote_selector = QuoteSelector(providers_from_env(args.providers.split(','))[0], args.max_model_calls)
        if args.ai:
            if args.replay or args.discover_brave:
                parser.error("AI mode cannot be combined with offline replay or Brave discovery")
            if min(args.max_model_calls, args.max_search_queries, args.agent_steps) < 1 or args.agent_steps > 12:
                parser.error("AI caps must be positive and steps <=12")
            from .agent import ModelRouter, TavilySearch, ResearchAgent, providers_from_env
            agent = ResearchAgent(ModelRouter(providers_from_env(args.providers.split(",")), args.max_model_calls),
                                  TavilySearch(os.environ.get("TAVILY_API_KEY"), args.max_search_queries), args.agent_steps)
        if args.discover_brave:
            if args.replay:
                parser.error("Paid discovery cannot be used in offline replay")
            rate = args.search_cost_per_request
            if rate is None or not math.isfinite(rate) or rate <= 0 or not math.isfinite(args.max_api_cost) or args.max_api_cost <= 0:
                parser.error("Provide positive finite --search-cost-per-request and --max-api-cost")
            from .discovery import BraveDiscovery
            discovery = BraveDiscovery(os.environ.get("BRAVE_API_KEY"), rate, args.max_api_cost)
        elif args.discover and not args.no_discover and not args.replay:
            # Opt-in only: the evaluator command must stay keyless and reproducible.
            from .discovery import build_discovery_from_env
            discovery = build_discovery_from_env(unit_cost=args.search_cost_per_request or 0.0,
                                                 max_cost=args.max_api_cost or 0.0, max_queries=args.max_search_queries)
        rows, report = run_batch(read_inputs(args.input), args.output, run_id=args.run_id,
                                 requests=args.max_requests, seconds=args.max_seconds, workers=args.workers,
                                 previous=previous, pages=args.pages, modules=modules,
                                 registry=args.registry, registry_retrieved_at=args.registry_retrieved_at, replay=args.replay, discovery=discovery, agent=agent,
                                 jobs_source=NavJobs(days=args.nav_days) if "jobs" in modules and not args.replay else None, guesses=not args.no_guess, strategy=args.strategy, quote_selector=quote_selector)
        render(rows, Path(args.output) / "index.html")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(0 if report["validation"]["passed"] else 1)
    elif args.command == "validate":
        rows = [json.loads(line) for line in Path(args.envelopes).read_text(encoding="utf-8").splitlines() if line.strip()]
        report = validate(rows, read_inputs(args.input), args.snapshots)
        print(json.dumps(report, indent=2))
        raise SystemExit(0 if report["passed"] else 1)
    elif args.command == "simulate":
        from .simulator import simulate_run
        from .core import write_json
        rows = [json.loads(line) for line in Path(args.envelopes).read_text(encoding="utf-8").splitlines() if line.strip()]
        reference = json.loads(Path(args.reference).read_text(encoding="utf-8")) if args.reference else None
        result = simulate_run(rows, read_inputs(args.input), args.snapshots,
                              json.loads(Path(args.report).read_text(encoding="utf-8")), reference)
        write_json(args.output, result)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["operational_gates_passed"] else 1)
    else:
        rows = [json.loads(line) for line in Path(args.envelopes).read_text(encoding="utf-8").splitlines() if line.strip()]
        render(rows, Path(args.output))


if __name__ == "__main__":
    main()
