"""Regressions for the independent review of version 3 (4 November 2026)."""
import json
import threading
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

from orglens.core import crawl_site, envelope, extract_feed, extract_site_facts, news_url_ok, soup_text
from orglens.navjobs import BASE, NavJobs
from test_integrity_fixes import snapshot


def site(url, html):
    return {**snapshot(html), "source_url": url, "status": 200, "source_class": "company_owned", "content_type": "text/html"}


class Sites:
    lock = threading.Lock()
    host_delays = {}

    def __init__(self, pages):
        self.pages = pages

    def get(self, url, source_class="company_owned", headers=None):
        if url.endswith("/robots.txt"):
            return {**site(url, ""), "status": 404}
        html = self.pages.get(url)
        return site(url, html) if html else {**site(url, ""), "status": 404}


def test_shared_brand_parent_site_is_not_the_subsidiarys_website():
    transport = Sites({
        "https://fjordbakst.no/": '<title>Fjordbakst Group</title><h1>Fjordbakst Group</h1><a href="/kontakt">Kontakt</a>'
                                  '<footer><a href="https://linkedin.com/company/fjordbakst">LinkedIn</a></footer>',
        "https://fjordbakst.no/kontakt": "<h1>Our companies</h1><p>Fjordbakst Vest AS Org.nr 123456789</p>",
    })
    row = envelope("123456789", "t")
    assert not crawl_site(row, {"navn": "FJORDBAKST VEST AS"}, transport, 3, origin="search", url="https://fjordbakst.no/")
    assert not [c for c in row["claims"] if c["field"] in {"official_website", "owned_profiles"}]


def test_company_named_on_its_own_homepage_still_verifies_from_contact_page():
    transport = Sites({
        "https://fjordbakst.no/": '<title>Fjordbakst Vest</title><h1>Fjordbakst Vest AS</h1><a href="/kontakt">Kontakt</a>',
        "https://fjordbakst.no/kontakt": "<h1>Kontakt Fjordbakst Vest AS</h1><p>Org.nr 123456789</p>",
    })
    row = envelope("123456789", "t")
    assert crawl_site(row, {"navn": "FJORDBAKST VEST AS"}, transport, 3, origin="search", url="https://fjordbakst.no/")


def feed(link, title="Example opens a new bakery in Bergen", description=""):
    return ("<rss><channel><item><title>" + title + "</title><pubDate>Tue, 03 Nov 2026 10:00:00 +0000</pubDate>"
            + ("<link>" + link + "</link>" if link else "") + "<description>" + description + "</description></item></channel></rss>")


def news(xml, body=None):
    row = envelope("123456789", "t")
    extract_feed(row, {**snapshot(xml), "source_url": "https://example.no/feed/"}, body)
    return [c["value"]["url"] for c in row["claims"] if c["field"] == "activity"]


def test_feed_items_need_their_own_article_on_the_verified_site():
    assert news(feed("https://example.no/contact")) == []
    assert news(feed("https://unrelated-company.no/news/opening")) == []
    assert news(feed(None)) == []
    assert news(feed("https://example.no/nyheter/ny-bakeri-i-bergen")) == ["https://example.no/nyheter/ny-bakeri-i-bergen"]
    assert news(feed("https://example.no/2026/11/ny-bakeri")) == ["https://example.no/2026/11/ny-bakeri"]


def test_media_company_stories_about_others_are_not_company_news():
    radio = {"navn": "RADIO GRENLAND AS", "naeringskode1": {"kode": "60.100"}}
    assert news(feed("https://example.no/nyheter/pors", "Pors-sjefen er hes etter cupbragden"), radio) == []
    own = feed("https://example.no/nyheter/frekvens", "Radio Grenland får ny frekvens i Skien")
    assert news(own, radio) == ["https://example.no/nyheter/frekvens"]


def test_news_url_rule_rejects_index_and_static_pages():
    home = "https://example.no/"
    assert not news_url_ok("https://example.no/nyheter/", home)
    assert not news_url_ok("https://example.no/personvern", home)
    assert not news_url_ok("https://example.no/feed", home)
    assert news_url_ok("https://example.no/nyheter/om-oss-flytter", home)


def profiles(html):
    soup, text = soup_text(html)
    row = envelope("123456789", "t")
    row["availability"] = {}
    extract_site_facts(row, {"navn": "EXAMPLE AS"}, [(site("https://example.no/", html), soup, text)], "labelled_organisation_number")
    return [c["value"]["url"] for c in row["claims"] if c["field"] == "owned_profiles"]


def test_agency_credit_numeric_profile_is_not_the_companys():
    html = ('<h1>Example AS</h1><footer><p>Website made by agency '
            '<a href="https://facebook.com/profile.php?id=999888777">Agency Facebook</a></p></footer>')
    assert profiles(html) == []


def test_company_numeric_profile_next_to_a_credit_line_is_kept():
    html = ('<h1>Example AS</h1><footer><a href="https://facebook.com/profile.php?id=123123123">Facebook</a>'
            '<p>Nettside levert av <a href="https://webbyraa.no">Webbyrå</a></p></footer>')
    assert profiles(html) == ["https://facebook.com/profile.php?id=123123123"]


class SegmentedFeed:
    """One busy segment of eight pages, five quiet one-page segments."""

    def __init__(self, busy):
        self.busy = busy  # If-Modified-Since prefix of the oldest segment

    def get(self, url, source_class="official_public_api", headers=None):
        since = (headers or {}).get("If-Modified-Since")
        page = int(url.rsplit("=", 1)[1]) if "page=" in url else 0
        busy = since.startswith(self.busy) if since else "busy" in url
        nxt = ("/api/v1/feed?busy&page=" + str(page + 1)) if (busy and page < 7) else None
        body = {"items": [], "next_url": nxt}
        return {"id": url, "source_url": url, "status": 200, "text": json.dumps(body), "retrieved_at": "2026-11-04T00:00:00Z"}


def test_nav_page_pool_completes_uneven_segments(monkeypatch):
    monkeypatch.setenv("NAV_FEED_TOKEN", "test-token")
    nav = NavJobs(segments=6)
    oldest = datetime.now(timezone.utc) - timedelta(days=nav.days)
    nav.load(SegmentedFeed(format_datetime(oldest, usegmt=True)[:16]), 14)  # 8 + 5 pages fit in one pool; a fixed share of 2 per segment never could
    assert nav.complete_segments == 6 and nav.state == "loaded" and nav.pages == 13


def test_dated_article_page_is_its_own_news_item():
    html = '<h1>Example AS</h1><article><h1>Ny kabelhenger lansert i dag</h1><time datetime="2026-11-02">2. nov</time></article>'
    soup, text = soup_text(html)
    row = envelope("123456789", "t")
    row["availability"] = {}
    pages = [(site("https://example.no/", "<h1>Example AS</h1>"), *soup_text("<h1>Example AS</h1>")),
             (site("https://example.no/news/2026/11/kabelhenger", html), soup, text),
             (site("https://example.no/nyheter", html), soup, text)]
    extract_site_facts(row, {"navn": "EXAMPLE AS"}, pages, "labelled_organisation_number")
    urls = [c["value"]["url"] for c in row["claims"] if c["field"] == "activity"]
    assert urls == ["https://example.no/news/2026/11/kabelhenger"]  # the unlinked item on the index page is not an article
