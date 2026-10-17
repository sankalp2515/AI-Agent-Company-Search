import json

from orglens.core import (claim, conflicting_number, corroborated, envelope, labelled_numbers, proof_on_pages,
                          social_profile, soup_text, synthesize)
from orglens.names import domain_matches_name, guess_domains, name_tokens
from orglens.navjobs import NavJobs


def snap(text="{}", url="https://example.no/"):
    return {"id": "s" + str(abs(hash(url + text)))[:8], "source_url": url, "source_class": "company_owned", "retrieved_at": "2026-10-16T00:00:00Z",
            "content_sha256": "0" * 64, "status": 200, "text": text}


def page(html, url="https://example.no/"):
    soup, text = soup_text(html)
    return (snap(html, url), soup, text)


def test_norwegian_vat_format_is_identity_evidence():
    assert labelled_numbers("Example AS · NO 123 456 789 MVA") == ["123456789"]
    assert labelled_numbers("Call 123 456 789") == []


def test_customer_directory_subpage_cannot_prove_identity():
    pages = [page("<h1>Manager AS</h1>"), page("<h1>Our clients</h1><p>Example AS Org.nr 123456789</p>", "https://example.no/kunder")]
    assert proof_on_pages("123456789", "Example AS", pages) is None


def test_own_contact_page_can_prove_identity():
    pages = [page("<h1>Example</h1>"), page("<h1>Kontakt Example</h1><p>Example AS Org.nr 123456789</p>", "https://example.no/kontakt")]
    found = proof_on_pages("123456789", "Example AS", pages)
    assert found and found[2] == "labelled_organisation_number"


def test_jsonld_tax_id_proves_identity():
    html = '<script type="application/ld+json">{"@type":"Organization","name":"Example","vatID":"NO123456789MVA"}</script>'
    assert proof_on_pages("123456789", "Example AS", [page(html)])[2] == "jsonld_organisation_identifier"


def test_property_manager_number_is_a_conflict():
    assert conflicting_number("123456789", [page("<footer>OBOS Org.nr 987654321</footer>")])


def test_registered_leader_alone_cannot_corroborate_a_name_bearing_domain():
    row = envelope("123456789", "t")
    claim(row, "leadership", {"name": "Kari Nordmann", "role": "Daglig leder"}, snap(), {"json_pointer": "/x"})
    pages = [page("<p>Kontakt: Kari Nordmann, daglig leder</p>")]
    assert corroborated({"navn": "Example AS"}, pages, row, domain_named=True) is None
    assert corroborated({"navn": "Example AS"}, pages, row, domain_named=False) is None


def test_auditor_firms_are_not_leader_evidence():
    row = envelope("123456789", "t")
    claim(row, "leadership", {"name": "Revisjon Partner AS", "role": "Revisor"}, snap(), {"json_pointer": "/x"})
    assert corroborated({"navn": "Example AS"}, [page("<p>Revisjon Partner AS</p>")], row, True) is None


def test_social_profile_normalization_rejects_share_links():
    assert social_profile("https://www.facebook.com/examplebakery/")["platform"] == "facebook"
    assert social_profile("https://www.facebook.com/sharer/sharer.php?u=x") is None
    assert social_profile("https://www.linkedin.com/company/example-as")["url"] == "https://www.linkedin.com/company/example-as"
    assert social_profile("https://facebook.com/") is None


def test_domain_guesses_skip_housing_associations_and_strip_legal_forms():
    assert guess_domains("SAMEIET KURVEIEN 17-19-21", "ESEK") == []
    assert guess_domains("CHARLOTTES HOBBY AS", "AS")[0] == "https://charlotteshobby.no/"
    assert name_tokens("Haukåsen Fjellgard AS") == ["haukasen", "fjellgard"]
    assert domain_matches_name("https://www.uplink.no", "UP LINK AS")
    assert not domain_matches_name("https://www.obos.no", "SAMEIET KURVEIEN 17-19-21")


class FakeTransport:
    def __init__(self, details):
        self.details = details

    def get(self, url, source_class="x", headers=None):
        key = url.rsplit("/", 1)[-1]
        if key not in self.details:
            return {**snap("{}", url), "status": 404}
        return {**snap(json.dumps(self.details[key]), url), "status": 200}


def test_nav_jobs_require_exact_employer_orgnr():
    nav = NavJobs()
    nav.state, nav.token = "loaded", "t"
    nav.index = {"example": {"a": {"url": "/api/v1/feedentry/a"}, "b": {"url": "/api/v1/feedentry/b"}}}
    ad = lambda org: {"ad_content": {"title": "Baker", "published": "2026-10-01", "expires": "2099-01-01", "employer": {"orgnr": org}, "link": "https://arbeidsplassen.nav.no/x"}}
    row = envelope("123456789", "t")
    row["availability"] = {}
    nav.research(row, {"navn": "Example AS"}, FakeTransport({"a": ad("123456789"), "b": ad("999999999")}), claim)
    jobs = [c for c in row["claims"] if c["field"] == "jobs"]
    assert len(jobs) == 1 and row["availability"]["jobs"] == "available"


def test_summary_cites_every_statement():
    row = envelope("123456789", "t")
    claim(row, "legal_name", "Example AS", snap(), {"json_pointer": "/navn"})
    claim(row, "financials.annual_result", {"amount": -5, "currency": "NOK"}, snap(), {"json_pointer": "/r"}, {"fraDato": "2025-01-01", "tilDato": "2025-12-31"})
    row["availability"] = {"jobs": "not_available"}
    summary = synthesize(row)
    assert "loss" in summary["text"] and "not treated as zero" in summary["text"]
    assert all(s["evidence_ids"] for s in summary["statements"] if s["kind"] not in {"unknowns", "changes"})


def test_partial_name_domain_needs_more_than_a_shared_board_member():
    from orglens.names import domain_is_full_name
    assert domain_is_full_name("https://myrepartnere.no/", "MYRE & PARTNERE AS")
    assert not domain_is_full_name("https://norsvin.com/", "NORSVIN INVEST AS")


def test_housing_association_rejects_property_manager_site(monkeypatch, tmp_path):
    import orglens.core as core
    pages = {"https://www.manager.no/robots.txt": (404, ""),
             "https://www.manager.no": (200, "<h1>Manager</h1><p>SOLBO BORETTSLAG tel 22 33 44 55</p>")}

    class T:
        lock = __import__("threading").Lock()
        host_delays = {}

        def get(self, url, source_class="x", headers=None):
            code, html = pages.get(url, (404, ""))
            return {**snap(html, url), "status": code, "content_type": "text/html"}

    row = envelope("951559091", "t")
    body = {"navn": "SOLBO BORETTSLAG", "telefon": "22334455", "organisasjonsform": {"kode": "BRL"}, "hjemmeside": "www.manager.no"}
    assert not core.crawl_site(row, body, T(), 3, origin="registry")
    assert row["availability"]["official_website"] == "ambiguous"


def test_national_subsidiary_cannot_claim_international_parent_domain():
    from orglens.names import domain_is_full_name
    assert not domain_is_full_name("https://eddagroup.com/", "EDDA GROUP NORWAY AS")
    assert domain_is_full_name("https://eddagroup.no/", "EDDA GROUP NORWAY AS")
