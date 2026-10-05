import json
from pathlib import Path

import pytest

from orglens.core import anchor, claim, digest, envelope, finish, identity_proof, read_inputs, validate, run_batch, Transport
from orglens.viewer import render


def snap(body):
    return {"id": "snapshot", "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/123456789", "source_class": "official_registry",
            "retrieved_at": "2026-10-05T00:00:00Z", "status": 200, "content_sha256": digest(body), "text": json.dumps(body), "redirect_chain": []}


def test_wrong_registry_identity_never_publishes():
    row = envelope("123456789", "test")
    assert anchor(row, snap({"organisasjonsnummer": "987654321", "navn": "Wrong company"})) is None
    assert row["claims"] == []
    assert row["availability"]["legal_identity"] == "ambiguous"


def test_org_identity_needs_label_and_rejects_multiple_entities():
    assert identity_proof("123456789", "Example AS Org.nr: 123 456 789 MVA")
    assert identity_proof("123456789", "Example AS Organisasjonsnr: 123 456 789")
    assert identity_proof("123456789", "Example AS Organisation number: 123456789")
    assert not identity_proof("123456789", "Phone 123456789 Example AS")
    assert not identity_proof("123456789", "Org.nr 123456789 Parent Org.nr 987654321")
    assert not identity_proof("123456789", "Org.nr 1234567890")


def test_missing_and_zero_are_distinct():
    row = envelope("123456789", "test")
    evidence = snap({"value": 0})
    claim(row, "revenue", None, evidence, {"json_pointer": "/value"})
    assert not row["claims"]
    claim(row, "revenue", 0, evidence, {"json_pointer": "/value"})
    assert row["claims"][0]["value"] == 0


def test_refresh_ignores_timestamp_and_retains_failed_previous():
    old = envelope("123456789", "old")
    claim(old, "legal_name", "Company AS", snap({}), {"json_pointer": "/navn"})
    old["availability"]["legal_identity"] = "available"
    finish(old)
    fresh = envelope("123456789", "new")
    claim(fresh, "legal_name", "Company AS", snap({}), {"json_pointer": "/navn"})
    fresh["availability"]["legal_identity"] = "available"
    finish(fresh, old)
    assert fresh["changes"] == []
    failed = finish(envelope("123456789", "failed"), old)
    assert failed["refresh"]["last_known_claims"][0]["value"] == "Company AS"
    assert failed["changes"] == []


def test_input_duplicates_and_wrong_membership(tmp_path):
    path = tmp_path / "input.txt"
    path.write_text("123456789\n123456789")
    with pytest.raises(ValueError):
        read_inputs(path)
    row = finish(envelope("123456789", "test"))
    assert not validate([row], ["987654321"])["passed"]


def test_1100_company_budget_failure_has_no_silent_drops(tmp_path, monkeypatch):
    monkeypatch.setattr(Transport, "get", lambda self, url, source_class="official_registry": {"source_url": url, "status": 0, "retrieved_at": "2026-10-05", "error": "Budget exhausted"})
    orgs = [str(100000000 + i) for i in range(1100)]
    rows, report = run_batch(orgs, tmp_path, run_id="stress", requests=1, seconds=1)
    assert len(rows) == 1100
    assert report["validation"]["passed"]
    assert all(r["availability"]["legal_identity"] == "failed" for r in rows)


def test_viewer_never_embeds_raw_script_terminator(tmp_path):
    path = tmp_path / "index.html"
    render([{"value": "</script><script>alert(1)</script>"}], path)
    assert "<script>alert(1)" not in path.read_text(encoding="utf-8")
