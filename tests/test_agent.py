import json
import time

import pytest

from orglens.agent import ModelRouter, ProviderError, ResearchAgent, TavilySearch, load_env
from orglens.core import envelope, finish
from orglens.simulator import simulate_run


class Transport:
    def __init__(self):
        self.deadline = time.monotonic() + 60
        self.requests = 0

    def reserve(self, url):
        self.requests += 1


def providers():
    return [{"name": "groq", "url": "https://api.groq.com/openai/v1/chat/completions", "key": "secret", "model": "m"},
            {"name": "nvidia", "url": "https://integrate.api.nvidia.com/v1/chat/completions", "key": "secret", "model": "m"}]


def response(action):
    return {"choices": [{"message": {"content": json.dumps(action)}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}


def test_router_rate_limit_fallback_and_global_cap():
    def call(url, key, body, timeout):
        if "groq" in url:
            raise ProviderError(429)
        return response({"action": "finish", "claim_ids": []})
    router = ModelRouter(providers(), 2, call)
    trace, transport = [], Transport()
    assert router.decide({}, transport, trace)["action"] == "finish"
    assert transport.requests == 2
    assert trace[0]["http_status"] == 429
    assert "groq" in router.cooldowns
    with pytest.raises(RuntimeError):
        router.decide({}, transport, [])
    assert router.calls == 2


def test_router_invalid_json_falls_back_and_no_secrets():
    def call(url, key, body, timeout):
        if "groq" in url:
            return {"choices": [{"message": {"content": "not json secret"}}]}
        return response({"action": "finish", "claim_ids": []})
    trace = []
    ModelRouter(providers(), 2, call).decide({}, Transport(), trace)
    assert "secret" not in json.dumps(trace)
    assert trace[0]["status"] == "invalid_model_output"


def test_tavily_basic_budget_and_transient_results():
    def call(url, key, body, timeout):
        assert body["search_depth"] == "basic"
        assert body["auto_parameters"] is False
        return {"results": [{"url": "https://example.no/about", "content": "untrusted fabricated revenue"},
                            {"url": "https://linkedin.com/company/example"}]}
    search = TavilySearch("secret", 1, call)
    transport = Transport()
    assert search.search("company", transport) == ["https://example.no/"]
    with pytest.raises(RuntimeError):
        search.search("another", transport)
    assert search.credits == 1 and transport.requests == 1
    assert not hasattr(search, "results")


def test_agent_model_selects_search_inspect_finish(monkeypatch):
    actions = iter([{"action": "search", "query": "official website"}, {"action": "inspect", "candidate_index": 0},
                    {"action": "finish", "claim_ids": []}])
    class Router:
        def decide(self, state, transport, trace):
            trace.append({"status": "success"})
            return next(actions)
    class Search:
        def search(self, query, transport):
            assert '"123456789"' in query and '"Company AS"' in query
            return ["https://example.no/"]
    def crawl(row, body, transport, pages):
        row["availability"]["official_website"] = "ambiguous"
    monkeypatch.setattr("orglens.core.crawl_site", crawl)
    row = envelope("123456789", "test")
    ResearchAgent(Router(), Search()).research(row, {"navn": "Company AS"}, Transport(), 2)
    assert row["agent"]["status"] == "completed"
    assert len(row["agent"]["steps"]) == 3
    assert row["claims"] == []  # Model cannot publish a fabricated fact or override ambiguity.


def test_agent_rejects_fabricated_summary_ids():
    class Router:
        def decide(self, *args):
            return {"action": "finish", "claim_ids": ["fabricated"]}
    row = envelope("123456789", "test")
    ResearchAgent(Router(), None).research(row, {}, Transport(), 1)
    assert row["agent"]["status"] == "limited"
    assert row["agent"]["selected_claim_ids"] == []


def test_dotenv_no_execution_process_env_wins(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text('TEST_A="$(malicious)"\nTEST_B=file # comment\n')
    monkeypatch.setenv("TEST_B", "environment")
    monkeypatch.delenv("TEST_A", raising=False)
    load_env(path)
    import os
    assert os.environ["TEST_A"] == "$(malicious)"
    assert os.environ["TEST_B"] == "environment"


def test_simulator_without_labels_does_not_invent_score(tmp_path):
    row = finish(envelope("123456789", "test"))
    report = {"requests": 1, "runtime_seconds": 1, "limits": {"requests": 2, "seconds": 2}}
    result = simulate_run([row], ["123456789"], tmp_path, report)
    assert result["operational_gates_passed"]
    assert result["overall_score"] is None
    assert result["official_qualification"] == "not_determined"
    report["requests"] = 3
    assert not simulate_run([row], ["123456789"], tmp_path, report)["operational_gates_passed"]


def test_simulator_reviewer_required_and_reviewed_bad_identity_blocks(tmp_path):
    row = finish(envelope("123456789", "test"))
    row["claims"] = [{"id": "c", "field": "description", "value": "A", "evidence_ids": []}]
    report = {"requests": 1, "runtime_seconds": 1, "limits": {"requests": 2, "seconds": 2}}
    with pytest.raises(ValueError):
        simulate_run([row], ["123456789"], tmp_path, report, {"claims": []})
    reference = {"reviewed_by": "tester", "reviewed_at": "2026-10-05", "provenance": "synthetic independent fixture",
        "family_weights": {"description": 1}, "claims": [{"organisation_number": "123456789", "field": "description", "value": "A"}],
        "publication_reviews": [{"claim_id": "c", "correct": True, "evidence_valid": True, "right_company": False, "material_wrong_company": True}],
        "manual_scores": {"synthesis": 12, "ux": 8}}
    result = simulate_run([row], ["123456789"], tmp_path, report, reference)
    assert result["components"]["coverage_out_of_50"] == 50
    assert result["components"]["precision_out_of_30"] == 0
    assert not result["local_only_qualification_estimate"]


def test_costs_do_not_call_unpriced_provider_usage_free_invoice():
    from orglens.costs import estimate_costs
    result = estimate_costs({"model_usage": {"nvidia": {"successful_calls": 2}}, "search_credit_upper_bound": 3}, 3)
    assert result["complete_retail_estimate_usd"] is None
    assert result["actual_invoice_cost_usd"] is None
    assert result["known_retail_component_usd"] == .024


def test_ai_budget_exhaustion_still_returns_1000_terminal_envelopes(tmp_path, monkeypatch):
    from orglens.core import run_batch
    def anchor_stub(row, snapshot):
        row["legal_identity"] = {"legal_name": "Synthetic fixture"}
        row["availability"]["legal_identity"] = "available"
        return {"navn": "Synthetic fixture", "organisasjonsnummer": row["organisation_number"]}
    monkeypatch.setattr("orglens.core.anchor", anchor_stub)
    monkeypatch.setattr("orglens.core.Transport.get", lambda *args, **kwargs: {})
    agent = ResearchAgent(ModelRouter(providers(), 1, lambda *args: response({"action": "finish", "claim_fields": []})), TavilySearch("fake", 1))
    orgs = [str(100000000 + i) for i in range(1000)]
    rows, report = run_batch(orgs, tmp_path, run_id="synthetic-ai-scale", modules=(), workers=4, agent=agent, requests=10, seconds=60)
    assert len(rows) == 1000 and report["validation"]["passed"]
    assert report["agent"]["model_attempts"] == 1
    assert all(r["run"]["terminal_status"] == "completed" for r in rows)


def test_router_unknown_claim_fields_are_not_published():
    call = lambda *args: response({"action": "finish", "claim_fields": ["invented_revenue"]})
    router = ModelRouter(providers(), 2, call)
    with pytest.raises(RuntimeError):
        router.decide({"claims": [{"id": "real", "field": "legal_name"}]}, Transport(), [])
    assert all(e["status"] == "invalid_model_output" for e in router.events)


def test_daily_average_failure_zero_infrastructure_void():
    from orglens.simulator import daily_average
    result = daily_average([{"reviewed_score": 80}, {"entrant_failure_after_clean_rerun": True}, {"void_infrastructure_failure": True}])
    assert result["local_daily_mean"] == 40 and result["counted_batches"] == 2


def test_router_cooldown_wait_is_bounded_and_recovered(monkeypatch):
    router = ModelRouter(providers()[:1], 2, lambda *args: response({"action": "finish", "claim_fields": []}))
    router.next_at["groq"] = time.monotonic() + .01
    trace = []
    assert router.decide({}, Transport(), trace)["action"] == "finish"
    assert router.calls == 1


def test_financial_payload_wrong_company_and_missing_identity_withheld():
    from orglens.core import official, digest
    class Accounts:
        def __init__(self, org):
            self.org = org
        def get(self, url):
            body = [{"virksomhet": {"organisasjonsnummer": self.org}, "regnskapsperiode": {"fraDato": "2025-01-01", "tilDato": "2025-12-31"},
                     "resultatregnskapResultat": {"aarsresultat": 1000000}, "valuta": "NOK", "regnskapstype": "SELSKAP"}]
            return {"id": "a", "source_url": url, "source_class": "official_registry", "status": 200,
                    "retrieved_at": "2026-10-05", "content_sha256": digest(body), "text": json.dumps(body)}
    for wrong in ("987654321", ""):
        row = envelope("123456789", "test")
        official(row, Accounts(wrong), "financials")
        assert row["claims"] == [] and row["availability"]["financials"] == "ambiguous"
    row = envelope("123456789", "test")
    official(row, Accounts("123456789"), "financials")
    assert row["claims"][0]["value"]["amount"] == 1000000
    assert row["claims"][0]["reporting_period"]["tilDato"] == "2025-12-31"
