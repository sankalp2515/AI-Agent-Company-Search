"""Network fallback, legal-statement proof, domain hypotheses and summary wording."""
from bs4 import BeautifulSoup

from orglens.core import FIELDS, alternate_addresses, declared_domain_legal_statement, digest, drop_lost_snapshots, english_legal_form, explicit_publish_date, parse_sitemap, registered_officers_on_pages, validate, SITEMAP_ARTICLE, SITEMAP_CAREERS
from orglens.core import international_office_listing, news_about_company, note_timed_out_candidate
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
    assert drop_lost_snapshots(rows, tmp_path) == 1
    assert [s["id"] for s in rows[0]["source_snapshots"]] == ["s1"]
    assert "https://junk.no/" in rows[0]["errors"][0]["message"]
    assert validate(rows, ["123456789"], tmp_path)["passed"]


def test_fact_does_not_outlive_its_lost_evidence(tmp_path):
    rows, cited, _ = batch_with_snapshots(tmp_path)
    (tmp_path / (cited + ".bin")).write_bytes(b"changed")
    assert drop_lost_snapshots(rows, tmp_path) == 1
    assert rows[0]["claims"] == [] and rows[0]["evidence"] == []
    assert rows[0]["availability"]["legal_identity"] == "failed"
    assert validate(rows, ["123456789"], tmp_path)["passed"]


def test_validator_alone_still_catches_later_tampering(tmp_path):
    rows, cited, _ = batch_with_snapshots(tmp_path)
    (tmp_path / (cited + ".bin")).write_bytes(b"changed")
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


INSPECTIONS = """orgnummer;navn;poststed;tilsynid;dato;total_karakter
123456789;Egon;OSLO;a;05012026;0
123456789;Egon;OSLO;b;05022026;2
987654321;Filial;BERGEN;c;05032026;3
111111111;Other;BODO;d;05032026;1
123456789;Bad date;OSLO;e;notadate;1
123456789;Not graded;OSLO;f;05032026;5
"""


def inspection_row(*units):
    return {"organisation_number": "123456789", "availability": {}, "claims": [{"field": "locations", "value": {"organisation_number": u}} for u in units]}


def run_inspections(row):
    from orglens.openrecords import FoodInspections, parse_inspections
    source = FoodInspections()
    source.by_org, source.state, source.snapshot = parse_inspections(INSPECTIONS), "loaded", {"id": "s"}
    claims = []
    count = source.research(row, lambda r, field, value, snap, locator, period=None, identity_method=None: claims.append((value, identity_method)), lambda d: d)
    return count, claims


def test_inspections_use_only_the_exact_number_or_a_registered_workplace():
    count, claims = run_inspections(inspection_row("987654321"))
    assert count == 3
    assert [c[0]["published_at"] for c in claims] == ["2026-03-05", "2026-02-05", "2026-01-05"]
    assert claims[0][1] == "official_record_registered_subunit" and claims[1][1] == "official_record_exact_orgnr"
    assert all("Other" not in c[0]["headline"] and "Not graded" not in c[0]["headline"] for c in claims)


def test_inspection_outcome_is_reported_in_plain_words():
    _, claims = run_inspections(inspection_row())
    assert "violations requiring follow-up" in claims[0][0]["headline"]
    assert claims[0][0]["kind"] == "official_food_inspection"


def test_only_timeouts_are_queued_for_a_late_retry():
    row = {"errors": [{"message": "<urlopen error timed out>"}], "website_research": {"candidates": []}}
    note_timed_out_candidate(row, "https://x.no/", "registry", 0)
    note_timed_out_candidate(row, "https://x.no/", "registry", 0)
    assert row["website_research"]["timed_out"] == [{"url": "https://x.no/", "origin": "registry"}]
    other = {"errors": [{"message": "certificate verify failed"}], "website_research": {"candidates": []}}
    note_timed_out_candidate(other, "https://y.no/", "registry", 0)
    assert "timed_out" not in other["website_research"]


def test_rules_and_plans_are_not_news():
    body = {"navn": "SOFIENBERGGATE 13", "naeringskode1": {"kode": "68.209"}}
    assert not news_about_company(body, "Vedtekter – Husordensregler")
    assert not news_about_company(body, "Årsplan 2026-2027")
    assert news_about_company(body, "Nytt tak på bygget")


def test_foreign_group_office_list_cannot_prove_a_national_subsidiary():
    assert international_office_listing("https://sportradar.com/about/locations/", "https://sportradar.com/")
    assert not international_office_listing("https://wanderingowl.com/kontakt", "https://wanderingowl.com/")
    assert not international_office_listing("https://reflexetikett.no/lokasjoner/", "https://reflexetikett.no/")


def test_holding_pages_are_not_company_sites():
    from orglens.core import parked_page
    assert parked_page("energa.no is registered, but the owner currently does not have a website")
    assert parked_page("Kommer snart")
    assert not parked_page("Vi er et elektrofirma i Arendal. " * 100 + "Kommer snart: ny avdeling.")
    assert not parked_page("Vi er et elektrofirma i Arendal med 20 ansatte.")


def test_domain_reseller_ad_pages_are_not_company_sites():
    from orglens.core import parked_page
    lander = '<meta name="description" content="eline.no has been informing visitors about topics such as CRM."><a href="https://example.test/?dn=eline.no&pid=ABC">x</a>'
    assert parked_page("eline.no Kontakt oss", lander)
    assert parked_page("mercator.no", '<a href="https://example.test/?dn=mercator.no&amp;pid=ABC">x</a>')
    assert not parked_page("Vi er et elektrofirma i Arendal med 20 ansatte.", "<html><a href='/?page=2&pid=7'>neste</a></html>")
    assert not parked_page("Lang artikkel. " * 500, '<a href="https://example.test/?dn=eline.no&pid=ABC">x</a>')


def test_declared_homepage_needs_more_than_one_shared_brand_word():
    from orglens.names import domain_covers_name
    assert domain_covers_name("https://snohettaregnskap.no/", "SNØHETTA REGNSKAP ALVDAL FOLLDAL AS")
    assert domain_covers_name("https://www.kingorides.com", "KINGO AS")
    for url, name in [("https://www.firdasea.no", "FIRDA EIENDOM AS"), ("https://hobbyboat.no/", "HOBBY BOAT EIENDOM AS"),
                      ("https://www.bring.no", "BRING WAREHOUSING AS"), ("https://www.crownrelo.com", "CROWN WORLDWIDE MOVERS AS"),
                      ("https://www.lenovo.com/no/no/", "LENOVO TECHNOLOGY B.V. NUF"), ("https://acme.no/", "ACME INVEST AS"),
                      ("https://www.storebrand.no/", "VERDIPAPIRFONDET STOREBRAND GLOBAL VALUE")]:
        assert not domain_covers_name(url, name), name


def test_norwegian_letters_match_every_domain_spelling():
    from orglens.names import domain_is_full_name, domain_matches_name
    assert domain_is_full_name("https://www.tjaralin.no", "TJÆRALIN AS")
    assert domain_is_full_name("https://tjaeralin.no", "TJÆRALIN AS")
    assert domain_is_full_name("https://hoevikbygg.no", "HØVIK BYGG AS")
    assert domain_matches_name("https://www.snohettaregnskap.no", "SNØHETTA REGNSKAP ALVDAL FOLLDAL AS")
    assert not domain_matches_name("https://www.usbl.no", "KROKEN BORETTSLAG")
    assert not domain_is_full_name("https://annetfirma.no", "TJÆRALIN AS")


def test_available_soon_is_a_holding_page():
    from orglens.core import parked_page
    assert parked_page("Site will be available soon. Thank you for your patience!")


def test_only_companies_cut_short_get_the_resume_pass():
    from orglens.core import website_cut_short
    base = {"errors": [], "website_research": {"candidates": [{"url": "https://a.no"}]}}
    assert website_cut_short({**base, "availability": {"official_website": "failed"}, "errors": [{"module": "website", "message": "Website research budget exhausted"}]})
    assert website_cut_short({"errors": [], "availability": {"official_website": "failed"}})
    assert not website_cut_short({**base, "availability": {"official_website": "available"}})
    assert not website_cut_short({**base, "availability": {"official_website": "failed"}})
    assert not website_cut_short({**base, "availability": {"official_website": "ambiguous"}, "errors": [{"module": "website", "message": "no proof"}]})


def test_a_company_named_after_its_head_gets_no_proof_from_that_name():
    from orglens.core import named_after_person
    assert named_after_person("MARTIN GRAN AS", "Martin Gran")
    assert named_after_person("ØYVIND RUUD AS", "Øyvind Ruud Ruud")
    assert not named_after_person("TANNLEGE LILLY DAHLSTRÖM AS", "Lilly Dahlström")
    assert not named_after_person("RUUD TREVARE AS", "Øyvind Ruud Ruud")
    assert not named_after_person("NUMBERS AS", "Ingve Sørheim")


def test_expired_domain_is_a_holding_page():
    from orglens.core import parked_page
    assert parked_page("www.dataconsultants.no has expired")
