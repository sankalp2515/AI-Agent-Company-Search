import io
import json
import time
import urllib.error

import pytest

import orglens.discovery as discovery
from orglens.discovery import ModelWebSearchProvider, MultiSearchDiscovery, model_search_prompt, model_search_providers_from_env

COMPANY = {"navn": "FJORD TOURS AS", "organisasjonsnummer": "912345678", "forretningsadresse": {"kommune": "BERGEN"}}


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fake_open(payload, seen):
    def _open(req, timeout, ctx):
        seen.append({"url": req.full_url, "headers": dict(req.header_items()), "body": json.loads(req.data)})
        if isinstance(payload, Exception):
            raise payload
        return Response(json.dumps(payload).encode())
    return _open


def http_error(code, body=b"{}"):
    return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(body))


OPENAI = {"output": [
    {"type": "web_search_call", "action": {"type": "search", "sources": [
        {"type": "url", "url": "https://www.proff.no/selskap/fjord-tours-as/912345678"},
        {"type": "url", "url": "https://www.fjordtours.no/om-oss"}]}},
    {"type": "message", "content": [{"type": "output_text", "text": "The official website is https://www.fjordtours.no.",
                                      "annotations": [{"type": "url_citation", "url": "https://www.fjordtours.no/om-oss", "title": "Om oss"}]}]}]}

ANTHROPIC = {"content": [
    {"type": "server_tool_use", "id": "srvtoolu_1", "name": "web_search", "input": {"query": "FJORD TOURS AS"}},
    {"type": "web_search_tool_result", "tool_use_id": "srvtoolu_1", "content": [
        {"type": "web_search_result", "url": "https://fjordtours.no/kontakt", "title": "Kontakt"},
        {"type": "web_search_result", "url": "https://www.facebook.com/fjordtours", "title": "Facebook"}]},
    {"type": "text", "text": "fjordtours.no"}]}

GEMINI = {"candidates": [{"content": {"parts": [{"text": "The website is fjordtours.no."}]},
                          "groundingMetadata": {"groundingChunks": [
                              {"web": {"uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc", "title": "fjordtours.no"}},
                              {"web": {"uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/def", "title": "proff.no"}}]}}]}


@pytest.mark.parametrize("family,payload", [("openai", OPENAI), ("anthropic", ANTHROPIC), ("gemini", GEMINI)])
def test_each_family_returns_the_cited_company_site_and_drops_directories(monkeypatch, family, payload):
    seen = []
    monkeypatch.setattr(discovery, "_open", fake_open(payload, seen))
    provider = ModelWebSearchProvider(family, "k" * 20, "model-x")
    roots = provider.search_company(COMPANY, "FJORD TOURS AS BERGEN", 10)
    hosts = [r.split("/")[2].removeprefix("www.") for r in roots]
    assert hosts[0] == "fjordtours.no"
    assert not any(h.endswith(("proff.no", "facebook.com", "vertexaisearch.cloud.google.com")) for h in hosts)
    request = seen[0]
    # The key only ever goes to the provider's own fixed endpoint, with the organisation number in the prompt.
    assert request["url"].startswith({"openai": "https://api.openai.com/", "anthropic": "https://api.anthropic.com/",
                                      "gemini": "https://generativelanguage.googleapis.com/"}[family])
    assert "912345678" in json.dumps(request["body"])


def test_request_bodies_enable_each_providers_web_search():
    openai, _ = ModelWebSearchProvider("openai", "k", "m").request("p")
    anthropic, headers = ModelWebSearchProvider("anthropic", "k", "m").request("p")
    gemini, _ = ModelWebSearchProvider("gemini", "k", "m").request("p")
    assert openai["tools"] == [{"type": "web_search"}]
    assert anthropic["tools"][0]["type"] == "web_search_20250305" and anthropic["tools"][0]["max_uses"] == 1
    assert headers["anthropic-version"]
    assert gemini["tools"] == [{"google_search": {}}]


def test_prompt_names_company_orgnr_and_place():
    prompt = model_search_prompt(COMPANY, "")
    assert "FJORD TOURS AS" in prompt and "912345678" in prompt and "BERGEN" in prompt


@pytest.mark.parametrize("code,body,disabled", [
    (401, b"{}", True), (403, b"{}", True), (400, b"{}", True), (404, b"{}", True),
    (429, b'{"error":{"code":"insufficient_quota"}}', True), (429, b'{"error":"slow down"}', False)])
def test_errors_never_raise_and_switch_off_only_when_permanent(monkeypatch, code, body, disabled):
    monkeypatch.setattr(discovery, "_open", fake_open(http_error(code, body), []))
    provider = ModelWebSearchProvider("openai", "k" * 20, "m")
    assert provider.search_company(COMPANY, "q", 5) == []
    assert provider.disabled is disabled
    if not disabled:
        assert provider.cooldown_until > time.monotonic()


def test_timeouts_and_bad_json_return_no_candidates(monkeypatch):
    monkeypatch.setattr(discovery, "_open", fake_open(TimeoutError(), []))
    assert ModelWebSearchProvider("gemini", "k", "m").search_company(COMPANY, "q", 5) == []
    monkeypatch.setattr(discovery, "_open", lambda req, timeout, ctx: Response(b"not json"))
    assert ModelWebSearchProvider("gemini", "k", "m").search_company(COMPANY, "q", 5) == []


def test_discovery_passes_the_company_and_a_longer_timeout_to_model_search(monkeypatch):
    calls = []

    class Model(ModelWebSearchProvider):
        def search_company(self, company, query, timeout):
            calls.append((company["organisasjonsnummer"], timeout))
            return ["https://fjordtours.no/"]

    class Transport:
        requests, limit = 0, 100
        deadline = time.monotonic() + 120
        def reserve(self, url): self.requests += 1

    chain = MultiSearchDiscovery([Model("anthropic", "k", "m")], max_queries=2)
    assert list(chain.discover_batches(COMPANY, Transport())) == [["https://fjordtours.no/"]]
    assert calls[0][0] == "912345678" and calls[0][1] > 12


def test_providers_from_env(monkeypatch):
    for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL",
                "GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL"):
        monkeypatch.delenv(key, raising=False)
    assert model_search_providers_from_env() == []
    monkeypatch.setenv("OPENAI_API_KEY", "o" * 20)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a" * 20)
    monkeypatch.setenv("GEMINI_API_KEY", "g" * 20)
    assert [p.label for p in model_search_providers_from_env()] == ["openai-web-search", "anthropic-web-search", "gemini-web-search"]
    monkeypatch.setenv("OPENAI_BASE_URL", "https://llm.example.org/v1")
    assert [p.family for p in model_search_providers_from_env()] == ["anthropic", "gemini"]


def test_each_company_gets_its_share_so_early_companies_cannot_spend_the_whole_cap():
    class Provider:
        disabled = False
        endpoint = "https://search.test/"
        def __init__(self): self.calls = 0
        def search(self, query, timeout):
            self.calls += 1
            return []

    class Transport:
        requests, limit = 0, 100
        deadline = time.monotonic() + 120
        def reserve(self, url): self.requests += 1

    providers = [Provider(), Provider(), Provider()]
    chain = MultiSearchDiscovery(providers, max_queries=4)
    chain.per_company = 2
    for name in ("Alpha AS", "Beta AS"):
        list(chain.discover_batches({"navn": name}, Transport()))
    # Two queries each: the second company is still searched, and the third provider is a fallback only.
    assert [p.calls for p in providers] == [2, 2, 0] and chain.calls == 4


def test_a_provider_cooling_down_after_a_rate_limit_is_skipped_without_spending_a_query():
    class Provider:
        disabled = False
        endpoint = "https://search.test/"
        def __init__(self, cooldown): self.cooldown_until, self.calls = cooldown, 0
        def search(self, query, timeout):
            self.calls += 1
            return ["https://alpha.test/"]

    class Transport:
        requests, limit = 0, 100
        deadline = time.monotonic() + 120
        def reserve(self, url): self.requests += 1

    cooling, ready = Provider(time.monotonic() + 60), Provider(0.0)
    chain = MultiSearchDiscovery([cooling, ready], max_queries=4)
    chain.per_company = 1
    assert list(chain.discover_batches({"navn": "Alpha AS"}, Transport())) == [["https://alpha.test/"]]
    assert cooling.calls == 0 and ready.calls == 1 and chain.calls == 1
