import io
import json
import time
import urllib.error
from decimal import Decimal
import pytest

from orglens.discovery import (
    candidate_roots,
    make_company_query,
    MultiSearchDiscovery,
    SerpApiProvider,
    TavilyProvider,
    build_discovery_from_env,
)


def test_candidate_roots_handles_serpapi_and_knowledge_graph():
    body = {
        "knowledge_graph": {"website": "https://company.no/about"},
        "organic_results": [
            {"link": "https://www.proff.no/selskap/x"},
            {"link": "https://company.no"},
            {"link": "http://other-company.no/index.html"},
            {"link": "https://facebook.com/company"},
        ]
    }
    roots = candidate_roots(body)
    assert roots == ["https://company.no/", "https://other-company.no/"]


def test_candidate_roots_handles_tavily_results():
    body = {
        "results": [
            {"url": "https://linkedin.com/in/foo"},
            {"url": "https://fresh-venture.no/page"},
            {"url": "https://vexter.no/selskap/123"},
        ]
    }
    roots = candidate_roots(body)
    assert roots == ["https://fresh-venture.no/"]


def test_make_company_query_formatting():
    c1 = {"navn": "CHARLOTTES HOBBY AS", "forretningsadresse": {"kommune": "HADSEL"}}
    assert make_company_query(c1) == "CHARLOTTES HOBBY AS HADSEL"

    # Does not duplicate if municipality is already in the name
    c2 = {"navn": "OSLO TANNLEGE AS", "forretningsadresse": {"kommune": "OSLO"}}
    assert make_company_query(c2) == "OSLO TANNLEGE AS"

    # Fallback to orgnr if no name
    c3 = {"organisasjonsnummer": "999888777"}
    assert make_company_query(c3) == "999888777"


def test_multi_search_fallback_on_failure():
    class DummyTransport:
        requests = 0
        limit = 100
        deadline = time.monotonic() + 60
        def reserve(self, url):
            self.requests += 1

    class FailingProvider:
        endpoint = "https://failing.api/search"
        disabled = False
        def __init__(self):
            self.called = 0
        def search(self, query, timeout):
            self.called += 1
            self.disabled = True
            return []

    class WorkingProvider:
        endpoint = "https://working.api/search"
        disabled = False
        def __init__(self):
            self.called = 0
        def search(self, query, timeout):
            self.called += 1
            return ["https://found-company.no/"]

    p1 = FailingProvider()
    p2 = WorkingProvider()
    discovery = MultiSearchDiscovery([p1, p2])

    company = {"navn": "Fjord Tours AS", "forretningsadresse": {"kommune": "BERGEN"}}
    transport = DummyTransport()

    # First call: p1 fails and gets disabled, p2 succeeds
    roots = discovery.discover(company, transport)
    assert roots == ["https://found-company.no/"]
    assert p1.called == 1
    assert p1.disabled is True
    assert p2.called == 1
    assert discovery.calls == 2

    # Second call: p1 is skipped because disabled, p2 handles directly
    roots2 = discovery.discover(company, transport)
    assert roots2 == ["https://found-company.no/"]
    assert p1.called == 1
    assert p2.called == 2


def test_multi_search_stops_when_first_provider_succeeds():
    class DummyTransport:
        requests = 0
        limit = 100
        deadline = time.monotonic() + 60
        def reserve(self, url):
            self.requests += 1

    class FirstProvider:
        endpoint = "https://first.api/search"
        disabled = False
        def __init__(self):
            self.called = 0
        def search(self, query, timeout):
            self.called += 1
            return ["https://primary-match.no/"]

    class SecondProvider:
        endpoint = "https://second.api/search"
        disabled = False
        def __init__(self):
            self.called = 0
        def search(self, query, timeout):
            self.called += 1
            return ["https://should-not-be-called.no/"]

    p1 = FirstProvider()
    p2 = SecondProvider()
    discovery = MultiSearchDiscovery([p1, p2])

    transport = DummyTransport()
    roots = discovery.discover({"navn": "Acme AS"}, transport)
    assert roots == ["https://primary-match.no/"]
    assert p1.called == 1
    assert p2.called == 0
    assert discovery.calls == 1


def test_build_discovery_from_env(monkeypatch):
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY_2", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    assert build_discovery_from_env() is None

    monkeypatch.setenv("SERPAPI_API_KEY", "test-serp-1")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily")
    disc = build_discovery_from_env()
    assert disc is not None
    assert len(disc.providers) == 2
    assert disc.providers[0].label == "serpapi-1"
    assert disc.providers[1].label == "tavily"


def test_evaluator_command_stays_keyless_even_when_keys_exist(monkeypatch, tmp_path):
    import sys
    import orglens.cli as cli
    seen = {}

    def fake_run_batch(orgs, output, **kwargs):
        seen["discovery"] = kwargs.get("discovery")
        return [], {"validation": {"passed": True}}

    monkeypatch.setenv("SERPAPI_API_KEY", "x" * 20)
    monkeypatch.setenv("TAVILY_API_KEY", "y" * 20)
    monkeypatch.setattr(cli, "run_batch", fake_run_batch)
    monkeypatch.setattr(cli, "render", lambda rows, path: None)
    source = tmp_path / "in.txt"
    source.write_text("123456789\n", encoding="utf-8")
    for extra, expected in (([], None), (["--discover"], "multi")):
        monkeypatch.setattr(sys, "argv", ["orglens", "run", "--input", str(source), "--output", str(tmp_path / "o"), *extra])
        try:
            cli.main()
        except SystemExit:
            pass
        assert (seen["discovery"] is None) if expected is None else seen["discovery"].provider_name.startswith(expected)
