"""Network fallback, legal-statement proof, domain hypotheses and summary wording."""
from bs4 import BeautifulSoup

from orglens.core import FIELDS, alternate_addresses, declared_domain_legal_statement, digest, drop_lost_unused_snapshots, english_legal_form, explicit_publish_date, parse_sitemap, registered_officers_on_pages, validate, SITEMAP_ARTICLE, SITEMAP_CAREERS
from orglens.names import domain_spells_name, guess_domains


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
           "availability": {field: "not_available" for field in FIELDS}, "errors": [],
           "claims": [{"field": "legal_name", "evidence_ids": ["e1"]}],
           "evidence": [{"id": "e1", "snapshot_id": "s1", "source_url": "https://x.no/", "retrieved_at": "t", "content_sha256": digest(cited), "locator": {"q": 1}}],
           "source_snapshots": [{"id": "s1", "content_sha256": digest(cited)}, {"id": "s2", "source_url": "https://junk.no/", "content_sha256": digest(unused)}]}
    return [row], digest(cited), digest(unused)


def test_lost_unused_page_is_recorded_and_the_run_stays_valid(tmp_path):
    rows, _, unused = batch_with_snapshots(tmp_path)
    (tmp_path / (unused + ".bin")).write_bytes(b"cleaned by antivirus")
    assert drop_lost_unused_snapshots(rows, tmp_path) == 1
    assert [s["id"] for s in rows[0]["source_snapshots"]] == ["s1"]
    assert "https://junk.no/" in rows[0]["errors"][0]["message"]
    assert validate(rows, ["123456789"], tmp_path)["passed"]


def test_altered_page_behind_a_published_fact_still_fails(tmp_path):
    rows, cited, _ = batch_with_snapshots(tmp_path)
    (tmp_path / (cited + ".bin")).write_bytes(b"changed")
    assert drop_lost_unused_snapshots(rows, tmp_path) == 0
    assert not validate(rows, ["123456789"], tmp_path)["passed"]


def test_sitemap_parsing_and_hostile_xml():
    xml = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://x.no/nyheter/a</loc><lastmod>2026-01-02</lastmod></url></urlset>'
    assert parse_sitemap(xml) == ([("https://x.no/nyheter/a", "2026-01-02")], [])
    index = '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://x.no/post.xml</loc></sitemap></sitemapindex>'
    assert parse_sitemap(index) == ([], ["https://x.no/post.xml"])
    assert parse_sitemap('<!DOCTYPE x [<!ENTITY a "b">]><urlset/>') == ([], [])
    assert parse_sitemap("not xml") == ([], [])


def test_sitemap_patterns_skip_section_pages_and_rental_listings():
    assert SITEMAP_ARTICLE.search("/artikler/ceramic-loop")
    assert not SITEMAP_ARTICLE.search("/nyheter/")
    assert SITEMAP_CAREERS.search("/ledig-stilling/")
    assert not SITEMAP_CAREERS.search("/ledige-lokaler/")


def test_publish_date_comes_from_the_page_not_a_guess():
    soup = BeautifulSoup('<meta property="article:published_time" content="2026-02-03T10:00:00Z"><h1>Ny avtale</h1>', "html.parser")
    assert explicit_publish_date(soup, soup.h1)[0] == "2026-02-03"
    soup = BeautifulSoup('<h1>Ny avtale</h1><footer><time datetime="2026-02-03">x</time></footer>', "html.parser")
    assert explicit_publish_date(soup, soup.h1) is None
    soup = BeautifulSoup('<h1>Ny avtale</h1><p>Avtalen gjelder fra 3. februar 2026.</p>', "html.parser")
    assert explicit_publish_date(soup, soup.h1) is None


def officers_row():
    people = [("Linn Maria Runeson", "Daglig leder"), ("Eric Thomas Reid", "Styrets leder"), ("ECIT SERVICES AS", "Regnskapsfører")]
    return {"claims": [{"field": "leadership", "value": {"name": n, "role": r}} for n, r in people]}


def test_short_name_domain_needs_two_people_on_one_page():
    assert domain_spells_name("https://www.edit.land/", "EDIT AS")
    assert not domain_spells_name("https://www.editing.no/", "EDIT AS")
    both = [page("https://www.edit.land/atelier", "Established by Linn Runeson and Eric Reid")]
    assert registered_officers_on_pages(officers_row(), both)[2] == "name_domain_and_two_registered_officers"
    one = [page("https://www.edit.land/atelier", "Established by Linn Runeson")]
    assert registered_officers_on_pages(officers_row(), one) is None
    split = [page("https://www.edit.land/a", "Linn Runeson"), page("https://www.edit.land/b", "Eric Reid")]
    assert registered_officers_on_pages(officers_row(), split) is None


def test_a_firm_role_holder_never_counts_as_an_officer():
    pages = [page("https://www.edit.land/", "Linn Runeson with ECIT SERVICES AS")]
    assert registered_officers_on_pages(officers_row(), pages) is None
