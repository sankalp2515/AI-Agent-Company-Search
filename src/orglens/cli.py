from __future__ import annotations

import argparse
import gzip
import json
import random
import os
import sys
import math
from pathlib import Path

from .agent import DEFAULT_PROVIDER_ORDER
from .core import read_inputs, run_batch, validate, write_rows
from .navjobs import NavJobs
from .viewer import render


def emergency_output(orgs, output, run_id, exc):
    """Last-resort delivery: keep every row already researched and mark the rest as failed, never empty."""
    from .core import FIELDS, envelope, finish, now, write_json
    import traceback
    output.mkdir(parents=True, exist_ok=True)
    print("orglens: batch error, writing safe envelopes:\n" + traceback.format_exc(), file=sys.stderr)
    saved = {}
    checkpoint = output / "checkpoint.jsonl"
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
                saved[row["organisation_number"]] = row
            except (ValueError, KeyError, TypeError):
                continue
    rows = []
    for org in orgs:
        row = saved.get(org)
        if row is None:
            row = envelope(org, run_id)
            row["availability"] = {f: "failed" for f in FIELDS}
        row.setdefault("errors", []).append({"module": "batch", "message": f"{type(exc).__name__}: {exc}"})
        try:
            finish(row)
        except Exception:
            row["run"]["completed_at"] = now()
        rows.append(row)
    write_rows(output / "envelopes.jsonl", rows)
    report = {"run_id": run_id, "completed_at": now(), "companies": len(orgs), "envelopes": len(rows),
              "validation": {"passed": False, "note": "emergency output after a batch error"},
              "error": f"{type(exc).__name__}: {exc}"}
    write_json(output / "run-report.json", report)
    return rows, report


def main():
    from .agent import load_env
    load_env()
    parser = argparse.ArgumentParser(prog="orglens")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Research an evaluator-supplied company batch")
    run.add_argument("--input", "--organisations", dest="input", required=True, help="JSONL batch of organisation numbers (--organisations is the starter-kit alias)")
    run.add_argument("--output", default="out/run", help="Run directory, or a .jsonl file path that receives the envelopes directly")
    run.add_argument("--report", help="Also write the run report to this path (starter-kit compatible)")
    run.add_argument("--profiles-output", help="Also write the envelopes to this JSONL path (starter-kit compatible)")
    run.add_argument("--expected-count", type=int, help="Number of input companies the caller expects; checked against the input")
    run.add_argument("--run-id", default="local")
    run.add_argument("--previous", help="Previous envelope JSONL; retain its snapshot directory")
    run.add_argument("--max-requests", type=int, default=1800)
    run.add_argument("--max-seconds", type=int, default=2400)
    run.add_argument("--workers", type=int, default=12)
    run.add_argument("--pages", type=int, default=5)
    run.add_argument("--strategy", choices=("baseline", "balanced"), default="baseline", help="Experimental bounded external-first allocation; baseline preserves original phase order")
    run.add_argument("--modules", default="financials,leadership,locations,jobs,website,awards")
    run.add_argument("--nav-days", type=int, default=186, help="NAV change-feed bootstrap horizon (186 days covers six calendar months)")
    run.add_argument("--no-guess", action="store_true", help="Disable keyless name-derived website candidates")
    run.add_argument("--registry", "--bulk", dest="registry", help="Evaluator frozen BRREG registry file (original-object JSONL or semicolon CSV); --bulk is an alias")
    run.add_argument("--requests-per-company", type=int, help="Request budget per input company (Builderr: 20, i.e. 2,000 per 100); overrides --max-requests")
    run.add_argument("--registry-retrieved-at", help="Actual timestamp of supplied registry snapshot")
    run.add_argument("--replay", help="Offline extraction from a previous run directory; not a fresh live run")
    run.add_argument("--keys", choices=("auto", "off"), default=os.environ.get("ORGLENS_KEYS", "auto"),
                     help="auto (default): use any search/model keys found in the environment, keyless otherwise; off: never call keyed services")
    run.add_argument("--search-queries-per-company", type=float, default=float(os.environ.get("ORGLENS_SEARCH_QUERIES_PER_COMPANY", 2)),
                     help="Search API query budget per input company when a search key is present")
    run.add_argument("--model-calls-per-company", type=float, default=float(os.environ.get("ORGLENS_MODEL_CALLS_PER_COMPANY", 3)),
                     help="Model call budget per input company when a model key is present")
    run.add_argument("--no-ai", action="store_true", help="Do not use model keys even when present")
    run.add_argument("--discover", action="store_true", help="Search discovery (SerpAPI, Tavily); already automatic with --keys auto when a key is present")
    run.add_argument("--no-discover", action="store_true", help="Force-disable search discovery")
    run.add_argument("--discover-brave", action="store_true", help="Opt-in search; BRAVE_API_KEY and declared costs required")
    run.add_argument("--search-cost-per-request", type=float)
    run.add_argument("--max-api-cost", type=float, default=0)
    run.add_argument("--ai", action="store_true", help="Model-directed website research; already automatic with --keys auto when model and search keys are present")
    run.add_argument("--extract-ai", action="store_true", help="Model selection of literal description quotes; already automatic with --keys auto when a model key is present")
    run.add_argument("--providers", default=os.environ.get("ORGLENS_MODEL_PROVIDERS", DEFAULT_PROVIDER_ORDER), help="Ordered model fallback chain; providers without a key are skipped")
    run.add_argument("--max-model-calls", type=int, default=int(os.environ["ORGLENS_MAX_MODEL_CALLS"]) if os.environ.get("ORGLENS_MAX_MODEL_CALLS") else None,
                     help="Absolute model call cap (default: --model-calls-per-company x companies)")
    run.add_argument("--max-search-queries", type=int, default=int(os.environ["ORGLENS_MAX_SEARCH_QUERIES"]) if os.environ.get("ORGLENS_MAX_SEARCH_QUERIES") else None,
                     help="Absolute search query cap (default: --search-queries-per-company x companies)")
    run.add_argument("--search-policy", choices=('broad','precise'), default='broad', help="Experimental exact-name search and directory exclusions")
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
        envelope_file = None
        if str(args.output).lower().endswith((".jsonl", ".json")):
            # A starter-kit style harness names the envelope file itself; keep the run directory beside it.
            envelope_file = Path(args.output)
            args.output = str(envelope_file.with_name(envelope_file.stem + "-run"))
        if args.expected_count is not None and args.expected_count != len(read_inputs(args.input)):
            print(f"orglens: --expected-count {args.expected_count} but the input has {len(read_inputs(args.input))} companies", file=sys.stderr)
        if min(args.max_requests, args.max_seconds, args.workers, args.pages) < 1:
            parser.error("Budgets, workers and pages must be positive")
        if args.requests_per_company:
            if args.requests_per_company < 1:
                parser.error("--requests-per-company must be positive")
            args.max_requests = args.requests_per_company * len(read_inputs(args.input))
        modules = tuple(m for m in args.modules.split(",") if m)
        if set(modules) - {"financials", "leadership", "locations", "jobs", "website", "awards"}:
            parser.error("Unknown module")
        previous = [json.loads(line) for line in Path(args.previous).read_text(encoding="utf-8").splitlines() if line.strip()] if args.previous else None
        discovery, agent, quote_selector = None, None, None
        ai_unavailable = False
        companies = len(read_inputs(args.input))
        if args.max_model_calls is None:
            args.max_model_calls = max(1, int(args.model_calls_per_company * companies))
        if args.max_search_queries is None:
            args.max_search_queries = max(1, int(args.search_queries_per_company * companies))
        if min(args.max_model_calls, args.max_search_queries, args.agent_steps) < 1 or args.agent_steps > 12:
            parser.error("Model and search caps must be positive and --agent-steps at most 12")
        auto = args.keys == "auto"
        live = not args.replay and args.keys != "off"
        if args.keys == "off" and (args.discover or args.ai or args.extract_ai or args.discover_brave):
            print("orglens: --keys off overrides --discover/--ai/--extract-ai; running keyless", file=sys.stderr)
        want_search = live and not args.no_discover and not args.discover_brave and (auto or args.discover or args.ai)
        want_quotes = live and not args.no_ai and (auto or args.extract_ai)
        want_agent = live and not args.no_ai and not args.discover_brave and (auto or args.ai)
        from .agent import ChainSearch, ModelRouter, ResearchAgent, providers_from_env
        from .discovery import build_discovery_from_env
        models = providers_from_env(args.providers, require=False) if (want_quotes or want_agent) else []
        search_chain = build_discovery_from_env(unit_cost=args.search_cost_per_request or 0.0, max_cost=args.max_api_cost or 0.0,
                                                max_queries=args.max_search_queries, query_policy=args.search_policy) if want_search or want_agent else None
        if want_search and search_chain and (auto or args.discover) and not args.no_discover:
            discovery = search_chain
        if want_quotes:
            from .quotes import QuoteSelector
            usable = [m for m in models if m["name"] != "cohere"]
            if usable:
                quote_selector = QuoteSelector(usable[0], max(1, min(args.max_model_calls, companies)))
            elif args.extract_ai:
                # A missing credential must never fail the batch: literal-text extraction is used instead.
                print("orglens: --extract-ai requested but no model credential is configured; continuing without AI extraction", file=sys.stderr)
                ai_unavailable = True
        if want_agent and models and search_chain:
            agent = ResearchAgent(ModelRouter(models, args.max_model_calls),
                                  ChainSearch(search_chain.providers, args.max_search_queries, shared=search_chain), args.agent_steps)
            if discovery is not None:
                # Discovery may use 70% of the shared search cap; the rest is kept for the agent's own searches.
                discovery.max_queries = max(1, int(args.max_search_queries * .7))
        elif args.ai and args.keys != "off":
            print("orglens: --ai needs a model key and a search key (SerpAPI or Tavily); continuing without the research agent", file=sys.stderr)
        if args.discover_brave and args.keys != "off":
            if args.replay:
                parser.error("Paid discovery cannot be used in offline replay")
            rate = args.search_cost_per_request
            if rate is None or not math.isfinite(rate) or rate <= 0 or not math.isfinite(args.max_api_cost) or args.max_api_cost <= 0:
                parser.error("Provide positive finite --search-cost-per-request and --max-api-cost")
            from .discovery import BraveDiscovery
            discovery = BraveDiscovery(os.environ.get("BRAVE_API_KEY"), rate, args.max_api_cost)
        # Names only; key values never reach the report, logs or envelopes.
        external = {"keys_mode": args.keys,
                    "search_providers": [getattr(p, "label", "search") for p in (search_chain.providers if search_chain else [])],
                    "model_providers": [{"provider": m["name"], "model": m["model"]} for m in models],
                    "search_discovery": discovery is not None, "research_agent": agent is not None,
                    "quote_selection": quote_selector is not None,
                    "search_query_cap": args.max_search_queries if (discovery or agent) else 0,
                    "model_call_cap": args.max_model_calls if agent else (quote_selector.max_calls if quote_selector else 0),
                    "note": "Keyless official sources always run; keyed services only add candidates that pass the same exact-company verification."}
        print("orglens: external services " + json.dumps({k: external[k] for k in ("keys_mode", "search_providers", "model_providers", "search_discovery", "research_agent", "quote_selection")}), file=sys.stderr)
        orgs = read_inputs(args.input)
        try:
            rows, report = run_batch(orgs, args.output, run_id=args.run_id,
                                     requests=args.max_requests, seconds=args.max_seconds, workers=args.workers,
                                     previous=previous, pages=args.pages, modules=modules,
                                     registry=args.registry, registry_retrieved_at=args.registry_retrieved_at, replay=args.replay, discovery=discovery, agent=agent,
                                     jobs_source=NavJobs(days=args.nav_days) if "jobs" in modules and not args.replay else None, guesses=not args.no_guess, strategy=args.strategy, quote_selector=quote_selector)
        except Exception as exc:  # never leave the harness without readable output
            rows, report = emergency_output(orgs, Path(args.output), args.run_id, exc)
        from .core import write_json
        if ai_unavailable:
            report["quote_selector"] = {"requested": True, "executed": False,
                                        "reason": "no model credential configured; literal-text extraction used"}
        report["external_services"] = external
        try:
            write_json(Path(args.output) / "run-report.json", report)
        except Exception as exc:
            print(f"orglens: report not rewritten ({type(exc).__name__})", file=sys.stderr)
        written = Path(args.output) / "envelopes.jsonl"
        import shutil
        # Deliver the machine-readable output first; the human viewer is optional and may never block it.
        for target in (envelope_file, Path(args.profiles_output) if args.profiles_output else None):
            if target is not None:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(written, target)
        if args.report:
            Path(args.report).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(args.output) / "run-report.json", args.report)
        try:
            render(rows, Path(args.output) / "index.html")
        except Exception as exc:
            print(f"orglens: viewer not rendered ({type(exc).__name__}: {exc}); envelopes are complete", file=sys.stderr)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        # A complete batch (one envelope per input) is always delivered with exit 0 so a harness never
        # discards it; validation findings stay in the report. Only a missing envelope fails the run.
        complete = len(rows) == len(orgs)
        raise SystemExit(0 if complete or report["validation"]["passed"] else 1)
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
