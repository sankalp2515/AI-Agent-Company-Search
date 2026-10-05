"""Measured usage and explicitly conditional cost estimates, not an invoice."""


def estimate_costs(agent_report, companies):
    # Official published prices verified 2026-10-05. Other retail tariffs unknown.
    usage = agent_report["model_usage"]
    known = 0.0
    unpriced = []
    for provider, item in usage.items():
        if provider == "groq":
            known += item["input_tokens"] * .075 / 1_000_000 + item["output_tokens"] * .30 / 1_000_000
        elif provider == "cloudflare":
            known += item["neurons"] * .011 / 1000
        else:
            if item["successful_calls"] or item.get("input_tokens", 0) or item.get("output_tokens", 0):
                unpriced.append(provider)
    search = agent_report["search_credit_upper_bound"] * .008
    return {"price_snapshot_date": "2026-10-05", "measured_companies": companies,
        "conditional_free_allowance_cost_usd": 0,
        "condition": "Only if every request is within remaining free/trial allocations and paid overage is disabled. Not verified by this app.",
        "known_retail_component_usd": round(known + search, 6),
        "unpriced_model_providers": unpriced,
        "complete_retail_estimate_usd": None if unpriced else round(known + search, 6),
        "actual_invoice_cost_usd": None,
        "hypothetical_same_workload_1000_company_known_component_usd": round((known + search) * 1000 / companies, 4) if companies else None,
        "extrapolation_warning": "Partial known-price sensitivity only, not an official-run quote. Caps, source mix, model fallbacks, provider quotas and batch size change workload.",
        "sources": ["https://console.groq.com/docs/models", "https://developers.cloudflare.com/workers-ai/platform/pricing/", "https://docs.tavily.com/documentation/api-credits"]}
