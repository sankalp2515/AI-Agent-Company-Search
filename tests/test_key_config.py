"""Configuration-driven keys: keyless by default, every documented key picked up automatically."""
import sys
import threading

import pytest

from orglens.agent import ChainSearch, ProviderError, call_chat, chat_body, providers_from_env, reply_text

KEYS = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
        "GEMINI_MODEL", "GROQ_API_KEY", "NVIDIA_API_KEY", "NVDIA_API_KEY", "COHERE_API_KEY", "CLOUDFLARE_API_KEY",
        "Cloudflare_API_KEY", "CLOUDFLARE_ACCOUNT_ID", "AccountID", "MISTRAL_API_KEY", "SERPAPI_API_KEY",
        "SERPAPI_API_KEY_2", "TAVILY_API_KEY", "BRAVE_API_KEY", "ORGLENS_KEYS", "ORGLENS_MAX_SEARCH_QUERIES",
        "ORGLENS_MAX_MODEL_CALLS", "ORGLENS_MODEL_PROVIDERS")


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)  # no .env file is read
    return monkeypatch


def test_generic_openai_gemini_and_anthropic_keys_are_detected(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "k1")
    clean_env.setenv("OPENAI_BASE_URL", "https://llm.example.test/v1/")
    clean_env.setenv("OPENAI_MODEL", "some-model")
    clean_env.setenv("GEMINI_API_KEY", "k2")
    clean_env.setenv("ANTHROPIC_API_KEY", "k3")
    found = providers_from_env("openai,anthropic,gemini,groq")
    assert [p["name"] for p in found] == ["openai", "anthropic", "gemini"]
    assert found[0]["url"] == "https://llm.example.test/v1/chat/completions"
    assert found[0]["model"] == "some-model"
    assert found[2]["url"].startswith("https://generativelanguage.googleapis.com/")


@pytest.mark.parametrize("base", ["http://llm.example.test/v1", "https://user:pw@llm.example.test/v1", "https://x.test/v1?key=1", "ftp://x"])
def test_unsafe_openai_base_url_is_never_given_the_key(clean_env, base):
    clean_env.setenv("OPENAI_API_KEY", "k1")
    clean_env.setenv("OPENAI_BASE_URL", base)
    assert providers_from_env("openai", require=False) == []


def test_no_keys_means_no_providers_without_error(clean_env):
    assert providers_from_env("openai,anthropic,gemini,groq", require=False) == []
    with pytest.raises(ValueError):
        providers_from_env("openai")


def test_reasoning_models_get_completion_token_parameters():
    body = chat_body({"name": "openai", "model": "gpt-5-mini"}, [], 384)
    assert "max_completion_tokens" in body and "max_tokens" not in body and "temperature" not in body
    body = chat_body({"name": "openai", "model": "gpt-4.1-mini"}, [], 384)
    assert body["max_tokens"] == 384 and body["temperature"] == 0
    assert body["response_format"] == {"type": "json_object"}


def test_rejected_parameter_is_adapted_once():
    provider = {"name": "openai", "model": "new-model", "url": "https://x.test", "key": "k"}
    bodies = []

    def caller(url, key, body, timeout):
        bodies.append(body)
        if "max_tokens" in body:
            raise ProviderError(400, ["max_tokens"])
        return {"choices": [{"message": {"content": "```json\n{\"a\": 1}\n```"}}]}

    payload = call_chat(provider, [], 100, caller, 5)
    assert len(bodies) == 2 and "max_completion_tokens" in bodies[1]
    assert reply_text(provider, payload) == '{"a": 1}'


def test_agent_search_shares_the_discovery_query_cap():
    class Provider:
        endpoint = "https://search.test"
        disabled = False

        def search(self, query, timeout):
            return ["https://company.test/"]

    class Shared:
        lock = threading.Lock()
        calls = 2

    class Transport:
        deadline = float("inf")

        def reserve(self, url):
            pass

    chain = ChainSearch([Provider()], max_queries=3, shared=Shared)
    assert chain.search("q", Transport()) == ["https://company.test/"]
    with pytest.raises(RuntimeError):
        chain.search("q", Transport())


def _run_cli(monkeypatch, tmp_path, extra=()):
    import orglens.cli as cli
    seen = {}

    def fake_run_batch(orgs, output, **kwargs):
        seen.update(kwargs)
        return [], {"validation": {"passed": True}}

    monkeypatch.setattr(cli, "run_batch", fake_run_batch)
    monkeypatch.setattr(cli, "render", lambda rows, path: None)
    source = tmp_path / "in.txt"
    source.write_text("123456789\n987654321\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["orglens", "run", "--input", str(source), "--output", str(tmp_path / "o"), *extra])
    with pytest.raises(SystemExit):
        cli.main()
    return seen


def test_official_command_without_keys_is_keyless(clean_env, tmp_path):
    seen = _run_cli(clean_env, tmp_path, ["--strategy", "balanced", "--pages", "8", "--requests-per-company", "20"])
    assert seen["discovery"] is None and seen["agent"] is None and seen["quote_selector"] is None


def test_official_command_with_keys_uses_all_of_them(clean_env, tmp_path):
    clean_env.setenv("SERPAPI_API_KEY", "s" * 20)
    clean_env.setenv("GEMINI_API_KEY", "g" * 20)
    seen = _run_cli(clean_env, tmp_path, ["--strategy", "balanced"])
    assert seen["discovery"] is not None and seen["discovery"].max_queries == 2  # 70% of 2 per company, rest for the agent
    assert seen["agent"].search.max_queries == 4
    assert seen["agent"] is not None and seen["agent"].router.max_calls == 6      # 3 per company
    assert seen["quote_selector"] is not None and seen["quote_selector"].provider["name"] == "gemini"


def test_model_key_alone_selects_quotes_but_no_agent(clean_env, tmp_path):
    clean_env.setenv("OPENAI_API_KEY", "o" * 20)
    seen = _run_cli(clean_env, tmp_path)
    assert seen["discovery"] is None and seen["agent"] is None and seen["quote_selector"] is not None


def test_keys_off_ignores_present_keys(clean_env, tmp_path):
    clean_env.setenv("SERPAPI_API_KEY", "s" * 20)
    clean_env.setenv("OPENAI_API_KEY", "o" * 20)
    seen = _run_cli(clean_env, tmp_path, ["--keys", "off"])
    assert seen["discovery"] is None and seen["agent"] is None and seen["quote_selector"] is None


def test_report_lists_services_but_never_key_values(clean_env, tmp_path):
    import json
    clean_env.setenv("TAVILY_API_KEY", "tvly-secret-value-123")
    clean_env.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-value-456")
    import orglens.cli as cli

    def fake_run_batch(orgs, output, **kwargs):
        from pathlib import Path
        Path(output).mkdir(parents=True, exist_ok=True)
        (Path(output) / "envelopes.jsonl").write_text("", encoding="utf-8")
        return [], {"validation": {"passed": True}}

    clean_env.setattr(cli, "run_batch", fake_run_batch)
    clean_env.setattr(cli, "render", lambda rows, path: None)
    source = tmp_path / "in.txt"
    source.write_text("123456789\n", encoding="utf-8")
    clean_env.setattr(sys, "argv", ["orglens", "run", "--input", str(source), "--output", str(tmp_path / "o")])
    with pytest.raises(SystemExit):
        cli.main()
    text = (tmp_path / "o" / "run-report.json").read_text(encoding="utf-8")
    report = json.loads(text)
    assert report["external_services"]["search_providers"] == ["tavily"]
    assert report["external_services"]["model_providers"][0]["provider"] == "anthropic"
    assert "secret-value" not in text


def test_serpapi_google_redirect_links_fall_back_to_the_displayed_host():
    from orglens.discovery import candidate_roots
    body = {"organic_results": [
        {"link": "https://www.google.no/goto?url=CAESabc", "displayed_link": "https://www.example-firma.no › om-oss"},
        {"link": "https://www.google.no/url?sa=t&url=CAESdef", "displayed_link": "no url here"},
        {"link": "https://www.proff.no/x", "displayed_link": "https://www.proff.no"}]}
    assert candidate_roots(body, preserve_paths=True) == ["https://www.example-firma.no/"]


def test_tool_use_failure_is_retried_with_tools_disabled():
    provider = {"name": "openai", "model": "m", "url": "https://x.test", "key": "k"}
    bodies = []

    def caller(url, key, body, timeout):
        bodies.append(body)
        if "tool_choice" not in body:
            raise ProviderError(400, ["model", "tool_use_failed"])
        return {"choices": [{"message": {"content": "{}"}}]}

    call_chat(provider, [], 50, caller, 5)
    assert bodies[-1]["tool_choice"] == "none"


def test_retired_default_model_moves_to_the_next_one(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "g")
    provider = providers_from_env("gemini")[0]
    first = provider["model"]
    seen = []

    def caller(url, key, body, timeout):
        seen.append(body["model"])
        if body["model"] == first:
            raise ProviderError(404, ["model"])
        return {"choices": [{"message": {"content": "{}"}}]}

    call_chat(provider, [], 50, caller, 5)
    assert seen[0] == first and seen[1] != first and provider["model"] == seen[1]


def test_explicit_model_has_no_silent_fallback(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "g")
    clean_env.setenv("GEMINI_MODEL", "my-model")
    provider = providers_from_env("gemini")[0]
    assert provider["model"] == "my-model" and "fallback_models" not in provider
