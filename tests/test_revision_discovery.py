"""Network fallback, legal-statement proof, domain hypotheses and summary wording."""
from bs4 import BeautifulSoup

from orglens.core import FIELDS, alternate_addresses, declared_domain_legal_statement, digest, english_legal_form, validate
from orglens.names import guess_domains


def page(url, text):
    return ({"source_url": url, "text": text}, BeautifulSoup(text, "html.parser"), text)


def test_alternates_keep_certificate_checks_and_never_downgrade_http_input():
    assert alternate_addresses("https://example.no/", "registry") == ["https://www.example.no/", "http://example.no/"]
    assert alternate_addresses("https://www.example.no/a", "registry_email") == ["https://example.no/a", "http://www.example.no/a"]
    assert alternate_addresses("http://example.no/", "registry") == []


def test_guessed_domains_never_fall_back_to_plain_http():
    assert alternate_addresses("https://example.no/", "name_guess") == ["https://www.example.no/"]
    assert alternate_addresses("https://example.no/", "historical_name_guess") == ["https://www.example.no/"]


def test_first_two_words_and_lone_first_word_survive_the_limit():
    amdam = guess_domains("AMDAM SAG OG HØVLERI AS")
    assert "https://amdamsag.no/" in amdam
    romsoes = guess_domains("ROMSØES CONDITORI AS")
    assert "https://romsoes.no/" in romsoes
    assert romsoes.index("https://romsoesconditori.no/") < romsoes.index("https://romsoes.no/")


def test_housing_forms_still_get_no_guesses():
    assert guess_domains("SOLBAKKEN BORETTSLAG", "BRL") == []


HOME = page("https://konsmohus.no/", "Konsmohus")


def statement(text, url="https://konsmohus.no/personvern/"):
    return [HOME, page(url, text)]


def test_exact_legal_name_beside_exact_number_on_a_shared_legal_page():
    pages = statement("Konsmo Fabrikker AS, org. nr: 950 167 866 Konsmo Eiendom AS, org. nr: 921 889 879")
    found = declared_domain_legal_statement("950167866", "KONSMO FABRIKKER AS", pages)
    assert found and found[2] == "legal_name_adjacent_organisation_number"


def test_number_beside_another_company_is_not_proof():
    pages = statement("Konsmo Fabrikker AS og Konsmo Eiendom AS, org. nr: 950 167 866")
    assert declared_domain_legal_statement("950167866", "KONSMO FABRIKKER AS", pages) is None


def test_different_number_is_not_proof():
    pages = statement("Konsmo Fabrikker AS, org. nr: 921 889 879")
    assert declared_domain_legal_statement("950167866", "KONSMO FABRIKKER AS", pages) is None


def test_portfolio_listing_many_companies_is_not_proof():
    listing = " ".join(f"Selskap {i} AS, org. nr: 92188987{i}" for i in range(4))
    pages = statement("Konsmo Fabrikker AS, org. nr: 950 167 866 " + listing)
    assert declared_domain_legal_statement("950167866", "KONSMO FABRIKKER AS", pages) is None


def test_ordinary_article_page_is_not_a_legal_statement():
    pages = statement("Konsmo Fabrikker AS, org. nr: 950 167 866", url="https://konsmohus.no/nyheter/kunde")
    assert declared_domain_legal_statement("950167866", "KONSMO FABRIKKER AS", pages) is None


def test_legal_form_wording():
    assert english_legal_form({"kode": "AS", "beskrivelse": "Aksjeselskap"}) == "a private limited company (aksjeselskap)"
    assert english_legal_form({"kode": "XYZ", "beskrivelse": "Noe annet"}) == "registered as noe annet"
    assert english_legal_form(None) == "a Norwegian registered entity"


def batch_with_snapshots(tmp_path):
    cited, unused = b"cited page", b"rejected page"
    for raw in (cited, unused):
        (tmp_path / (digest(raw) + ".bin")).write_bytes(raw)
    row = {"organisation_number": "123456789", "run": {"terminal_status": "completed", "completed_at": "2026-11-06T00:00:00Z"},
           "availability": {field: "not_available" for field in FIELDS},
           "claims": [{"field": "legal_name", "evidence_ids": ["e1"]}],
           "evidence": [{"id": "e1", "snapshot_id": "s1", "source_url": "https://x.no/", "retrieved_at": "t", "content_sha256": digest(cited), "locator": {"q": 1}}],
           "source_snapshots": [{"id": "s1", "content_sha256": digest(cited)}, {"id": "s2", "content_sha256": digest(unused)}]}
    return [row], digest(cited), digest(unused)


def test_lost_unused_snapshot_is_a_warning_not_a_failed_run(tmp_path):
    rows, _, unused = batch_with_snapshots(tmp_path)
    (tmp_path / (unused + ".bin")).unlink()
    result = validate(rows, ["123456789"], tmp_path)
    assert result["passed"] and len(result["warnings"]) == 1


def test_altered_snapshot_behind_a_published_fact_still_fails(tmp_path):
    rows, cited, _ = batch_with_snapshots(tmp_path)
    (tmp_path / (cited + ".bin")).write_bytes(b"changed")
    result = validate(rows, ["123456789"], tmp_path)
    assert not result["passed"] and result["errors"] == ["Snapshot missing or corrupted"]
