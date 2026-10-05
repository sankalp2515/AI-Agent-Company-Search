import json

from orglens.core import anchor, claim, corroborated_identity, digest, envelope, finish, official, run_batch, validate, site_identity_proof, soup_text


def snapshot(body):
    return {"id": "s", "status": 200, "source_url": "https://data.brreg.no/example", "source_class": "official_registry",
            "retrieved_at": "2026-10-05T00:00:00Z", "content_sha256": digest(body), "text": json.dumps(body)}


def test_address_gate_requires_every_component_and_no_conflicting_org():
    body = {"navn": "EXAMPLE COMPANY AS", "forretningsadresse": {"adresse": ["Storgata 12"], "postnummer": "0123"}}
    assert corroborated_identity(body, "Example Company AS, Storgata 12, 0123 Oslo")
    assert not corroborated_identity(body, "Example Company AS, Storgata 99, 0123 Oslo")
    assert not corroborated_identity(body, "Example Company AS, Storgata 12, 9999 Oslo")
    assert not corroborated_identity(body, "Example Company AS, Storgata 12, 0123 Oslo, Org.nr 987654321")


def test_equal_financial_values_in_different_periods_are_not_deduplicated():
    row = envelope("123456789", "x")
    for period in ({"fraDato": "2024-01-01", "tilDato": "2024-12-31"}, {"fraDato": "2025-01-01", "tilDato": "2025-12-31"}):
        claim(row, "financials.revenue", {"amount": 0, "currency": "NOK"}, snapshot({}), {"json_pointer": "/a"}, period)
    assert len(row["claims"]) == 2


def test_accounts_without_reporting_period_are_not_published():
    class Fake:
        def get(self, url):
            return snapshot([{"resultatregnskapResultat": {"aarsresultat": 17}}])
    row = envelope("123456789", "x")
    official(row, Fake(), "financials")
    assert row["claims"] == []
    assert row["availability"]["financials"] == "not_available"


def test_frozen_registry_is_evidence_and_makes_no_identity_request(tmp_path):
    path = tmp_path / "registry.jsonl"
    path.write_text(json.dumps({"organisasjonsnummer": "123456789", "navn": "Example AS"}) + "\n", encoding="utf-8")
    rows, report = run_batch(["123456789"], tmp_path / "result", run_id="frozen", modules=(), registry=path, registry_retrieved_at="2026-10-04T00:00:00Z")
    assert report["requests"] == 0
    assert report["validation"]["passed"]
    assert rows[0]["legal_identity"]["legal_name"] == "Example AS"
    evidence = rows[0]["evidence"][0]
    assert evidence["retrieved_at"] == "2026-10-04T00:00:00Z"


def test_snapshot_corruption_is_detected(tmp_path):
    row = envelope("123456789", "x")
    anchor(row, snapshot({"organisasjonsnummer": "123456789", "navn": "Example"}))
    finish(row)
    assert not validate([row], ["123456789"], tmp_path)["passed"]


def test_real_change_carries_both_evidence_sides():
    old = envelope("123456789", "old")
    old["availability"]["legal_identity"] = "available"
    claim(old, "employees", 4, snapshot({"value": 4}), {"json_pointer": "/value"})
    finish(old)
    fresh = envelope("123456789", "fresh")
    fresh["availability"]["legal_identity"] = "available"
    claim(fresh, "employees", 5, snapshot({"value": 5}), {"json_pointer": "/value"})
    finish(fresh, old)
    assert len(fresh["changes"]) == 1
    assert fresh["changes"][0]["previous_claims"][0]["value"] == 4
    assert fresh["changes"][0]["current_claims"][0]["value"] == 5
    assert fresh["refresh"]["previous_evidence"]


def test_frozen_csv_preserves_types_and_row_evidence(tmp_path):
    path = tmp_path / "registry.csv"
    path.write_text('organisasjonsnummer;navn;antallAnsatte;konkurs;organisasjonsform.kode\n123456789;Example AS;0;false;AS\n', encoding="utf-8")
    rows, report = run_batch(["123456789"], tmp_path / "result", run_id="csv", modules=(), registry=path, registry_retrieved_at="2026-10-04T00:00:00Z")
    assert rows[0]["legal_identity"]["employees"] == 0
    assert rows[0]["legal_identity"]["bankrupt"] is False
    assert rows[0]["evidence"][0]["locator"]["source_row_key"] == "123456789"
    assert report["validation"]["passed"]


def test_customer_directory_cannot_claim_the_property_managers_domain():
    home, text = soup_text('<h1>Property Manager AS</h1><footer>Manager address 0123 Oslo</footer>')
    directory, directory_text = soup_text('<h1>Our clients</h1><p>Example Housing Association, Storgata 12, 0123 Oslo. Org.nr 123456789</p><footer>Property Manager AS</footer>')
    assert site_identity_proof("123456789", [(snapshot({}), home, text), (snapshot({}), directory, directory_text)]) is None
    owned, owned_text = soup_text('<h1>Example company</h1><footer>Org.nr 123456789</footer>')
    assert site_identity_proof("123456789", [(snapshot({}), owned, owned_text)])
