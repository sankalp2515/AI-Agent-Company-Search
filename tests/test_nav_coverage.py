import json

import pytest

from orglens.core import claim, envelope
from orglens.navjobs import BASE, NavJobs


class Transport:
    def __init__(self, responses):
        self.responses = responses
        self.urls = []

    def get(self, url, source_class="official_public_api", headers=None):
        self.urls.append(url)
        status, body = self.responses.get(url, (404, {}))
        return {"id": str(len(self.urls)), "source_url": url, "source_class": source_class,
                "status": status, "text": body if isinstance(body, str) else json.dumps(body),
                "retrieved_at": "2026-10-17T00:00:00Z", "content_sha256": "0" * 64}


def entry(uuid, name, **fields):
    return {"url": "/api/v1/feedentry/" + uuid, "date_modified": "2026-01-01T00:00:00+00:00",
            "_feed_entry": {"uuid": uuid, "status": "ACTIVE", "businessName": name, **fields}}


def loaded(items, monkeypatch):
    monkeypatch.setenv("NAV_FEED_TOKEN", "test-token")
    nav = NavJobs(segments=1)
    nav.load(Transport({BASE + "/api/v1/feed": (200, {"items": items})}))
    return nav


def ad(org):
    return {"ad_content": {"title": "Baker", "employer": {"orgnr": org}, "expires": "2099-01-01"}}


def test_brand_suffix_and_joined_name_candidates_are_verified(monkeypatch):
    nav = loaded([entry("brand", "Charlottes Hobby Oslo"), entry("wrong", "Charlottes Cafe")], monkeypatch)
    row = envelope("123456789", "t")
    nav.research(row, {"navn": "CHARLOTTES HOBBY AS"}, Transport({
        BASE + "/api/v1/feedentry/brand": (200, ad("123456789")),
        BASE + "/api/v1/feedentry/wrong": (200, ad("987654321")),
    }), claim)
    jobs = [c for c in row["claims"] if c["field"] == "jobs"]
    assert len(jobs) == 1
    assert row["availability"]["jobs"] == "available"
    assert nav.candidates(["CHAR LOTTES HOBBY AS"])


def test_feed_orgnr_discovers_unrelated_brand_but_detail_still_gates(monkeypatch):
    nav = loaded([entry("a", "Unrelated Brand", orgnr="123456789")], monkeypatch)
    row = envelope("123456789", "t")
    nav.research(row, {"navn": "Legal Entity AS"}, Transport({BASE + "/api/v1/feedentry/a": (200, ad("123456789"))}), claim)
    assert any(c["field"] == "jobs" for c in row["claims"])


@pytest.mark.parametrize("status,body", [(503, {}), (200, "bad json"), (200, []), (200, {"items": "bad"})])
def test_unusable_feed_does_not_claim_no_jobs(monkeypatch, status, body):
    monkeypatch.setenv("NAV_FEED_TOKEN", "test-token")
    nav = NavJobs(segments=1)
    nav.load(Transport({BASE + "/api/v1/feed": (status, body)}))
    row = envelope("123456789", "t")
    nav.research(row, {"navn": "Example AS"}, Transport({}), claim)
    assert row["availability"]["jobs"] == "failed"
    assert row["research_sources"]["nav_jobs"]["state"] == "failed"


def test_truncated_feed_marks_research_partial(monkeypatch):
    monkeypatch.setenv("NAV_FEED_TOKEN", "test-token")
    nav = NavJobs(segments=1, max_pages=1)
    nav.load(Transport({BASE + "/api/v1/feed": (200, {"items": [], "next_url": "/api/v1/feed?page=2"})}))
    row = envelope("123456789", "t")
    nav.research(row, {"navn": "Example AS"}, Transport({}), claim)
    assert row["availability"]["jobs"] == "failed"
    assert row["research_sources"]["nav_jobs"]["state"] == "partial"


def test_failed_detail_does_not_claim_no_jobs(monkeypatch):
    nav = loaded([entry("a", "Example")], monkeypatch)
    row = envelope("123456789", "t")
    nav.research(row, {"navn": "Example AS"}, Transport({}), claim)
    assert row["availability"]["jobs"] == "failed"
    assert row["research_sources"]["nav_jobs"]["state"] == "partial"


def test_joined_employer_words_find_exact_entity(monkeypatch):
    nav = loaded([entry("joined", "Uplink")], monkeypatch)
    row = envelope("123456789", "t")
    nav.research(row, {"navn": "UP LINK AS"}, Transport({BASE + "/api/v1/feedentry/joined": (200, ad("123456789"))}), claim)
    assert row["availability"]["jobs"] == "available"


def test_candidate_expansion_is_bounded_and_keeps_identity_gate(monkeypatch):
    nav = loaded([entry(str(i), "Charlottes " + str(i)) for i in range(25)], monkeypatch)
    nav.max_ads = 2
    row = envelope("123456789", "t")
    transport = Transport({BASE + "/api/v1/feedentry/" + str(i): (200, ad("987654321")) for i in range(25)})
    nav.research(row, {"navn": "Charlottes Hobby AS"}, transport, claim)
    assert not [c for c in row["claims"] if c["field"] == "jobs"]
    assert nav.details == 4
    assert row["research_sources"]["nav_jobs"]["state"] == "partial"
    assert row["availability"]["jobs"] != "not_available"


def test_budget_too_small_is_unknown_not_no_jobs(monkeypatch):
    monkeypatch.setenv("NAV_FEED_TOKEN", "test-token")
    nav = NavJobs()
    nav.load(Transport({}), page_cap=0)
    row = envelope("123456789", "t")
    nav.research(row, {"navn": "Example AS"}, Transport({}), claim)
    assert row["availability"]["jobs"] == "failed"
    assert row["research_sources"]["nav_jobs"]["state"] == "not_queried"
