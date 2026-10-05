import io
import json
import time

import pytest

from orglens.discovery import BraveDiscovery, candidate_roots


def test_discovery_filters_platforms_and_deduplicates_domains():
    payload = {"web": {"results": [{"url": "https://linkedin.com/company/x"}, {"url": "https://example.no/about"},
                                   {"url": "https://example.no/contact"}, {"url": "https://user:secret@evil.test"}, {"url": "file:///x"}]}}
    assert candidate_roots(payload) == ["https://example.no/"]


def test_search_response_is_transient_and_cost_cap_is_strict(tmp_path):
    class Opener:
        def open(self, request, timeout):
            assert request.get_header("X-subscription-token") == "test-key"
            return io.BytesIO(json.dumps({"web": {"results": [{"url": "https://example.no"}]}}).encode())
    class Transport:
        deadline = time.monotonic() + 30
        def reserve(self, url):
            pass
    search = BraveDiscovery("test-key", .005, .005, Opener())
    body = {"organisasjonsnummer": "123456789", "navn": "Example AS"}
    assert search.discover(body, Transport()) == ["https://example.no/"]
    with pytest.raises(RuntimeError):
        search.discover(body, Transport())
    assert float(search.spent) == .005
    assert search.calls == 1
    assert list(tmp_path.iterdir()) == []
