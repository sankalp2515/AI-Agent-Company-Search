"""NAV Job Vacancy Feed (arbeidsplassen.nav.no) connector.

Official Norwegian public-sector feed, free under NAV's terms of use. Feed pages are
candidate discovery only: an ad is published as a job claim only after its detail
record names the exact organisation number (or one of the company's registered
subunits) as employer. Credentials: NAV_FEED_TOKEN if set, otherwise NAV's
published public token fetched at run time.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

from .names import translit, LEGAL_FORMS

BASE = "https://pam-stilling-feed.nav.no"


def norm_employer(name):
    words = re.findall(r"[a-z0-9]+", translit(name))
    return " ".join(w for w in words if w not in LEGAL_FORMS)


class NavJobs:
    def __init__(self, days=45, max_pages=200, segments=6, max_ads_per_company=10):
        self.days = days
        self.max_pages = max_pages
        self.segments = segments
        self.max_ads = max_ads_per_company
        self.token = None
        self.index = {}  # normalized business name -> {uuid: feed item}
        self.pages = 0
        self.state = "not_loaded"
        self.error = None
        self.lock = threading.Lock()
        self.details = 0

    def headers(self):
        return {"Authorization": "Bearer " + self.token, "Accept": "application/json"}

    def load(self, transport, page_cap=None):
        """Index active ads modified within the window; latest entry per ad wins."""
        cap = min(self.max_pages, page_cap if page_cap is not None else self.max_pages)
        if cap < self.segments:
            self.state = "not_loaded"
            self.error = "Request budget too small for the NAV feed index"
            return
        self.token = os.environ.get("NAV_FEED_TOKEN")
        if not self.token:
            snap = transport.get(BASE + "/api/publicToken", "official_public_api")
            if snap.get("status") != 200:
                self.state, self.error = "failed", "NAV public token unavailable"
                return
            match = re.search(r"eyJ[\w-]+\.[\w-]+\.[\w-]+", snap["text"])
            if not match:
                self.state, self.error = "failed", "NAV public token not found"
                return
            self.token = match.group(0)
        now = datetime.now(timezone.utc)
        starts = [now - timedelta(days=self.days) + timedelta(days=self.days) * i / self.segments for i in range(self.segments)]
        bounds = list(zip(starts, starts[1:] + [now + timedelta(days=1)]))
        latest = {}
        per_segment = max(1, cap // self.segments)

        def walk(segment):
            begin, end = segment
            url, headers = BASE + "/api/v1/feed", {**self.headers(), "If-Modified-Since": format_datetime(begin, usegmt=True)}
            items = []
            for _ in range(per_segment):
                snap = transport.get(url, "official_public_api", headers=headers)
                if snap.get("status") != 200:
                    break
                with self.lock:
                    self.pages += 1
                body = json.loads(snap["text"])
                done = False
                for item in body.get("items", []):
                    modified = datetime.fromisoformat(item.get("date_modified", "1970-01-01T00:00:00+00:00"))
                    if modified >= end:
                        done = True
                        break
                    items.append(item)
                if done or not body.get("next_url"):
                    break
                url, headers = BASE + body["next_url"], self.headers()
            return items

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.segments) as pool:
            for items in pool.map(walk, bounds):
                for item in items:
                    entry = item.get("_feed_entry") or {}
                    uuid = entry.get("uuid")
                    if uuid:
                        previous = latest.get(uuid)
                        if previous is None or item.get("date_modified", "") >= previous.get("date_modified", ""):
                            latest[uuid] = item
        for uuid, item in latest.items():
            entry = item["_feed_entry"]
            if entry.get("status") != "ACTIVE" or not entry.get("businessName"):
                continue
            self.index.setdefault(norm_employer(entry["businessName"]), {})[uuid] = item
        self.state = "loaded" if self.pages else "failed"

    def candidates(self, names):
        found = {}
        for name in names:
            key = norm_employer(name)
            if len(key) >= 3:
                found.update(self.index.get(key, {}))
        return list(found.values())

    def research(self, row, body, transport, claim):
        """Publish active ads whose detail record names this exact employer orgnr."""
        if self.state != "loaded":
            row["availability"]["jobs"] = row["availability"].get("jobs") if row["availability"].get("jobs") == "available" else ("failed" if self.state == "failed" else "not_available")
            if self.error:
                row["errors"].append({"module": "nav_jobs", "message": self.error})
            return []
        org = row["organisation_number"]
        units = {str(c["value"].get("organisation_number")): c["value"].get("name") for c in row["claims"]
                 if c["field"] == "locations" and isinstance(c["value"], dict)}
        names = [body.get("navn", "")] + [n for n in units.values() if n] + [h.get("navn", "") for h in body.get("historiskeNavn", [])[-2:]]
        accepted, homepages = 0, []
        for item in self.candidates(names)[: self.max_ads * 2]:
            if accepted >= self.max_ads:
                break
            snap = transport.get(BASE + item["url"], "official_public_api", headers=self.headers())
            with self.lock:
                self.details += 1
            if snap.get("status") != 200:
                continue
            detail = json.loads(snap["text"])
            ad = detail.get("ad_content") or {}
            employer = ad.get("employer") or {}
            employer_org = re.sub(r"\D", "", str(employer.get("orgnr") or ""))
            parent_snap = None
            if employer_org != org and employer_org not in units and len(employer_org) == 9:
                # NAV usually names the workplace; prove it is a registered subunit of this exact entity.
                parent_snap = transport.get("https://data.brreg.no/enhetsregisteret/api/underenheter/" + employer_org)
                try:
                    unit = json.loads(parent_snap["text"]) if parent_snap.get("status") == 200 else {}
                except ValueError:
                    unit = {}
                if str(unit.get("overordnetEnhet")) == org:
                    units[employer_org] = unit.get("navn")
                    claim(row, "locations", {"organisation_number": employer_org, "name": unit.get("navn"), "address": unit.get("beliggenhetsadresse")},
                          parent_snap, {"json_pointer": "/overordnetEnhet"})
            if employer_org != org and employer_org not in units:
                continue
            expires = str(ad.get("expires") or ad.get("applicationDue") or "")
            if expires and expires[:10] < datetime.now(timezone.utc).date().isoformat():
                continue
            location = ", ".join(sorted({w.get("city") or w.get("municipal") or "" for w in ad.get("workLocations", []) if w.get("city") or w.get("municipal")}))
            value = {"title": ad.get("title"), "job_title": ad.get("jobtitle"), "date_posted": ad.get("published"),
                     "valid_through": ad.get("expires"), "location": location or None,
                     "employment": " / ".join(x for x in (ad.get("engagementtype"), ad.get("extent")) if x) or None,
                     "url": ad.get("link"), "source": "NAV arbeidsplassen",
                     "employer_unit": None if employer_org == org else {"organisation_number": employer_org, "name": units.get(employer_org)}}
            claim(row, "jobs", value, snap, {"json_pointer": "/ad_content/employer/orgnr", "matched_orgnr": employer_org},
                  period={"published": ad.get("published"), "expires": ad.get("expires")},
                  identity_method="nav_ad_employer_orgnr_exact" if employer_org == org else "nav_ad_employer_registered_subunit")
            accepted += 1
            if employer.get("homepage"):
                homepages.append(employer["homepage"])
        if accepted:
            row["availability"]["jobs"] = "available"
        elif row["availability"].get("jobs") != "available":
            row["availability"]["jobs"] = "not_available"
        return homepages

    def report(self):
        return {"source": "NAV Job Vacancy Feed (pam-stilling-feed.nav.no)", "state": self.state, "window_days": self.days,
                "feed_pages": self.pages, "detail_requests": self.details,
                "indexed_active_employers": len(self.index), "indexed_active_ads": sum(len(v) for v in self.index.values()),
                "token": "NAV_FEED_TOKEN" if os.environ.get("NAV_FEED_TOKEN") else "NAV published public token"}
