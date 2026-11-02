"""Regressions for Builderr's October 2026 audit feedback."""
from orglens.core import claim, envelope, external_footprint, extract_site_facts, finish, run_batch, soup_text, synthesize
from test_integrity_fixes import snapshot


def fin(row, field, amount, end, kind="SELSKAP"):
    claim(row, "financials." + field, {"amount": amount, "currency": "NOK", "account_type": kind}, snapshot("{}"),
          {"json_pointer": f"/{end}/{field}"}, {"fraDato": end[:4] + "-01-01", "tilDato": end})


def test_summary_uses_one_newest_period_even_when_a_figure_is_missing():
    row = envelope("123456789", "t")
    row["legal_identity"]["latest_accounts_year"] = "2025"
    fin(row, "revenue", 100, "2024-12-31")
    fin(row, "annual_result", 5, "2024-12-31")
    fin(row, "annual_result", 7, "2025-12-31")
    fin(row, "revenue", 999, "2025-12-31", kind="KONSERN")
    text = [s["text"] for s in synthesize(row)["statements"] if s["kind"] == "financials"][0]
    assert "2025-01-01 to 2025-12-31" in text and "SELSKAP" in text and "2024" not in text


def test_older_figures_are_never_called_latest_when_registry_lists_newer_filing():
    row = envelope("123456789", "t")
    claim(row, "latest_accounts_year", "2025", snapshot("{}"), {"json_pointer": "/sisteInnsendteAarsregnskap"})
    row["legal_identity"]["latest_accounts_year"] = "2025"
    fin(row, "revenue", 100, "2024-12-31")
    texts = [s["text"] for s in synthesize(row)["statements"] if s["kind"] == "financials"]
    assert texts[0].startswith("Most recent accounts figures available")
    assert "2025" in texts[1] and "not the latest filing" in texts[1]


def site_pages(html):
    soup, text = soup_text(html)
    return [(snapshot(html, "https://acmebakeri.no/"), soup, text)]


def test_social_links_must_belong_to_the_company_and_careers_page_is_published():
    row = envelope("123456789", "t")
    row["availability"] = {}
    html = ('<footer><a href="https://www.facebook.com/acmebakeri">Facebook</a>'
            '<a href="https://www.linkedin.com/company/webagency-design">Laget av Webagency</a>'
            '<a href="/karriere">Karriere</a></footer>')
    extract_site_facts(row, {"navn": "ACME BAKERI AS"}, site_pages(html), "labelled_organisation_number")
    profiles = [c["value"]["url"] for c in row["claims"] if c["field"] == "owned_profiles"]
    assert profiles == ["https://www.facebook.com/acmebakeri"]
    assert [c["value"] for c in row["claims"] if c["field"] == "careers_page"] == ["https://acmebakeri.no/karriere"]


def test_external_footprint_names_families_plainly_and_excludes_registry_events():
    row = envelope("123456789", "t")
    claim(row, "official_website", "https://acme.no/", snapshot("{}"), {"text_quote": "Org.nr 123456789"}, identity_method="labelled_organisation_number")
    claim(row, "owned_profiles", {"platform": "facebook", "url": "https://facebook.com/acme"}, snapshot("{}"), {"link_href": "x"})
    claim(row, "activity", {"headline": "Registered for VAT", "published_at": "2020-01-01", "kind": "official_registry_event"}, snapshot("{}"), {"json_pointer": "/x"})
    claim(row, "activity", {"headline": "Vi åpner ny butikk i Bergen", "published_at": "2026-09-01", "kind": "company_owned_feed_item", "url": "https://acme.no/nyheter/1"}, snapshot("{}"), {"feed_item": 0})
    footprint = external_footprint(row)
    assert footprint["website"]["url"] == "https://acme.no/"
    assert footprint["social_links"][0]["platform"] == "facebook"
    assert [n["headline"] for n in footprint["news"]] == ["Vi åpner ny butikk i Bergen"]
    assert footprint["news"][0]["evidence_ids"]


def test_registry_file_without_timestamp_is_accepted_and_labelled(tmp_path):
    path = tmp_path / "registry.csv"
    path.write_text('organisasjonsnummer;navn;organisasjonsform.kode\n123456789;Example AS;AS\n', encoding="utf-8")
    rows, report = run_batch(["123456789"], tmp_path / "out", run_id="t", modules=(), registry=path)
    assert report["registry_snapshot"]["retrieved_at_source"] == "file_modified_time"
    assert rows[0]["legal_identity"]["legal_name"] == "Example AS"


def test_group_site_listing_the_subsidiary_is_not_its_own_website():
    import threading
    import orglens.core as core
    pages = {"https://www.groupholding.no/robots.txt": (404, ""),
             "https://www.groupholding.no/": (200, '<h1>Group Holding</h1><a href="/kontakt">Kontakt</a>'),
             "https://www.groupholding.no/kontakt": (200, "<p>Fjordbakst Vest AS, Strandgaten 9, 5013 Bergen, tlf 55 55 55 55</p>")}

    class T:
        lock = threading.Lock()
        host_delays = {}

        def get(self, url, source_class="x", headers=None):
            code, html = pages.get(url, (404, ""))
            return {**snapshot(html, url), "status": code, "content_type": "text/html"}

    row = envelope("123456789", "t")
    body = {"navn": "FJORDBAKST VEST AS", "telefon": "55555555", "organisasjonsform": {"kode": "AS"},
            "forretningsadresse": {"adresse": ["Strandgaten 9"], "postnummer": "5013"}}
    assert not core.crawl_site(row, body, T(), 3, origin="registry", url="https://www.groupholding.no/")
    assert row["availability"]["official_website"] == "ambiguous"


def test_static_contact_and_privacy_pages_are_never_news_even_with_article_schema():
    row = envelope("123456789", "t")
    row["availability"] = {}
    pages = []
    for html, url in (("<p>home</p>", "https://alfa.no/"),
                      ('<script type="application/ld+json">{"@type":"NewsArticle","headline":"Kontakt oss - Alfa","datePublished":"2026-02-10"}</script>', "https://alfa.no/start/"),
                      ('<script type="application/ld+json">{"@type":"Article","headline":"Personvernerklæring","datePublished":"2026-01-10"}</script>', "https://alfa.no/personvernerklaering/")):
        soup, text = soup_text(html)
        pages.append((snapshot(html, url), soup, text))
    extract_site_facts(row, {"navn": "ALFA AS"}, pages, "labelled_organisation_number")
    assert [c for c in row["claims"] if c["field"] == "activity"] == []


def test_news_dates_are_iso_and_old_or_future_items_are_dropped():
    from orglens.core import news_date
    assert news_date("2026-11-02CET13:25") == "2026-11-02"
    assert news_date("Fri, 30 Oct 2026 10:00:00 +0000") == "2026-10-30"
    assert news_date("Wed, 20 Dec 2017 11:13:51 +0000") is None
    assert news_date("2099-01-01") is None
