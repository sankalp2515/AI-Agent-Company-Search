import concurrent.futures
import socket
import time

import pytest

from orglens.core import BudgetExceeded, Transport, public_url


def test_private_destination_is_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(ValueError):
        public_url("https://example.com")
    with pytest.raises(ValueError):
        public_url("file:///etc/passwd")
    with pytest.raises(ValueError):
        public_url("https://user:password@example.com")


def test_concurrent_request_reservations_never_exceed_cap(tmp_path):
    transport = Transport(tmp_path, requests=5, seconds=20)
    def reserve(i):
        try:
            transport.reserve(f"https://host{i}.example")
            return True
        except BudgetExceeded:
            return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        accepted = list(pool.map(reserve, range(50)))
    assert sum(accepted) == transport.requests == 5


def test_expired_budget_does_not_resolve_or_contact_hosts(tmp_path, monkeypatch):
    transport = Transport(tmp_path, requests=5, seconds=1)
    transport.deadline = time.monotonic() - 1
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: pytest.fail("DNS used after deadline"))
    result = transport.get("https://example.com")
    assert result["budget_exhausted"]
    assert transport.requests == 0


def test_large_robots_delay_cannot_overrun_deadline(tmp_path):
    transport = Transport(tmp_path, requests=5, seconds=1)
    transport.host_times["example.com"] = time.monotonic()
    transport.host_delays["example.com"] = 3600
    began = time.monotonic()
    with pytest.raises(BudgetExceeded):
        transport.reserve("https://example.com")
    assert time.monotonic() - began < .2
