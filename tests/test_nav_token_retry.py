import time

from orglens.navjobs import NavJobs


class TokenTransport:
    deadline = float('inf')
    limit = 100
    requests = 0

    def __init__(self, first):
        self.first = first
        self.token_attempts = 0

    def get(self, url, source_class, headers=None):
        self.requests += 1
        if url.endswith('/publicToken'):
            self.token_attempts += 1
            if self.token_attempts == 1:
                return self.first
            token = 'eyJ' + 'a' * 10 + '.' + 'b' * 12 + '.' + 'c' * 20
            return {'status': 200, 'text': token}
        return {'status': 200, 'text': '{"items": []}'}


def test_transient_public_token_failure_gets_one_bounded_retry(monkeypatch):
    monkeypatch.delenv('NAV_FEED_TOKEN', raising=False)
    monkeypatch.setattr(time, 'sleep', lambda seconds: None)
    transport = TokenTransport({'status': 0})
    jobs = NavJobs(segments=1)
    jobs.load(transport, page_cap=1)
    assert jobs.state == 'loaded'
    assert transport.token_attempts == 2


def test_token_failure_at_budget_limit_is_not_retried(monkeypatch):
    monkeypatch.delenv('NAV_FEED_TOKEN', raising=False)
    transport = TokenTransport({'status': 0, 'budget_exhausted': True})
    jobs = NavJobs(segments=1)
    jobs.load(transport, page_cap=1)
    assert jobs.state == 'failed'
    assert transport.token_attempts == 1


def test_token_access_denial_is_not_retried(monkeypatch):
    monkeypatch.delenv('NAV_FEED_TOKEN', raising=False)
    transport = TokenTransport({'status': 403})
    jobs = NavJobs(segments=1)
    jobs.load(transport, page_cap=1)
    assert jobs.state == 'failed'
    assert transport.token_attempts == 1
