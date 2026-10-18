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
GENERIC_EMPLOYER_WORDS = {"norge", "norway", "norsk", "service", "services", "holding", "group", "gruppen", "invest", "kommune"}


def norm_employer(name):
    words = re.findall(r"[a-z0-9]+", translit(name))
    return " ".join(w for w in words if w not in LEGAL_FORMS)


class NavJobs:
    def __init__(self, days=45, max_pages=200, segments=6, max_ads_per_company=10, max_candidate_details=4, max_detail_requests=None):
        self.days = days
        self.max_pages = max_pages
        self.segments = segments
        self.max_ads = max_ads_per_company
        self.max_candidate_details = max_candidate_details
        self.max_detail_requests = max_detail_requests
        self.token = None
        self.index = {}  # normalized business name -> {uuid: feed item}
        self.org_index = {}
        self.word_index = {}
        self.compact_index = {}
        self.pages = 0
        self.state = "not_loaded"
        self.error = None
        self.lock = threading.Lock()
        self.details = 0
        self.complete_segments = 0
        self.response_cache = {}
        self.response_locks = {}
        self.cache_hits = 0

    def cached_get(self, transport, url, source_class="official_public_api", headers=None, detail=False):
        """One in-run fetch per URL, including concurrent companies; never relabel old evidence fresh."""
        with self.lock:
            lock = self.response_locks.setdefault(url, threading.Lock())
        with lock:
            with self.lock:
                if url in self.response_cache:
                    self.cache_hits += 1
                    return self.response_cache[url]
                if detail:
                    if self.max_detail_requests is not None and self.details >= self.max_detail_requests:
                        return {"source_url": url, "status": 0, "error": "NAV detail module budget exhausted"}
                    self.details += 1
            snapshot = transport.get(url, source_class, headers=headers) if headers else transport.get(url, source_class)
            # All consumers see the same run observation. Failed observations remain explicit;
            # source-wide retry policy belongs to the next refresh, not each namesake company.
            with self.lock:
                self.response_cache[url] = snapshot
            return snapshot

    def headers(self):
        return {"Authorization": "Bearer " + self.token, "Accept": "application/json"}

    def load(self, transport, page_cap=None):
        """Index active ads modified within the window; latest entry per ad wins."""
        cap = min(self.max_pages, page_cap if page_cap is not None else self.max_pages)
        self.index, self.org_index, self.word_index, self.compact_index = {}, {}, {}, {}
        self.pages, self.complete_segments = 0, 0
        self.response_cache, self.response_locks = {}, {}
        self.details, self.cache_hits = 0, 0
        self.error = None
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
                    return items, False, "NAV feed request failed"
                try:
                    body = json.loads(snap["text"])
                    if not isinstance(body, dict) or not isinstance(body.get("items"), list):
                        raise ValueError("invalid feed")
                    for item in body["items"]:
                        if not isinstance(item, dict) or not isinstance(item.get("_feed_entry"), dict):
                            raise ValueError("invalid feed item")
                        modified = datetime.fromisoformat(item["date_modified"])
                        if modified.tzinfo is None:
                            raise ValueError("missing timezone")
                except (ValueError, TypeError, KeyError):
                    return items, False, "NAV feed response malformed"
                with self.lock:
                    self.pages += 1
                done = False
                for item in body.get("items", []):
                    modified = datetime.fromisoformat(item.get("date_modified", "1970-01-01T00:00:00+00:00"))
                    if modified >= end:
                        done = True
                        break
                    items.append(item)
                if done or not body.get("next_url"):
                    return items, True, None
                if not isinstance(body["next_url"], str) or not body["next_url"].startswith("/api/v1/"):
                    return items, False, "NAV feed pagination URL malformed"
                url, headers = BASE + body["next_url"], self.headers()
            return items, False, "NAV feed page limit reached"

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.segments) as pool:
            for items, complete, error in pool.map(walk, bounds):
                self.complete_segments += int(complete)
                if error:
                    self.error = error
                for item in items:
                    entry = item.get("_feed_entry") or {}
                    uuid = entry.get("uuid")
                    if uuid:
                        previous = latest.get(uuid)
                        if previous is None or item.get("date_modified", "") >= previous.get("date_modified", ""):
                            latest[uuid] = item
        for uuid, item in latest.items():
            entry = item["_feed_entry"]
            if entry.get("status") != "ACTIVE":
                continue
            name = entry.get("businessName")
            if isinstance(name, str) and name:
                key = norm_employer(name)
                self.index.setdefault(key, {})[uuid] = item
                if len(key.replace(" ", "")) >= 4:
                    self.compact_index.setdefault(key.replace(" ", ""), set()).add(key)
                for word in key.split():
                    if len(word) >= 5 and word not in GENERIC_EMPLOYER_WORDS:
                        self.word_index.setdefault(word, set()).add(key)
            employer = entry.get("employer") if isinstance(entry.get("employer"), dict) else {}
            # Some feed versions include identifiers; they only discover candidates.
            for value in (entry.get("orgnr"), entry.get("businessOrgNumber"), employer.get("orgnr")):
                orgnr = re.sub(r"\D", "", str(value or ""))
                if len(orgnr) == 9:
                    self.org_index.setdefault(orgnr, {})[uuid] = item
        self.state = "loaded" if self.complete_segments == self.segments else ("partial" if self.pages else "failed")

    def candidates(self, names, orgnrs=()):
        """Rank discovery hints only; every result still needs employer identity proof."""
        found = {}
        for org in orgnrs:
            for uuid, item in self.org_index.get(str(org), {}).items():
                found[uuid] = (1000, item)
        for name in names:
            key = norm_employer(name)
            if len(key) >= 3:
                possible = {key}
                words = set(key.split())
                for word in words:
                    possible.update(self.word_index.get(word, ()))
                # "UP LINK" and "Uplink" are the same spelling once spaces are ignored.
                possible.update(self.compact_index.get(key.replace(" ", ""), ()))
                for candidate in sorted(possible):
                    overlap = words.intersection(candidate.split())
                    score = 100 if candidate == key else 10 * len(overlap)
                    compact, other = key.replace(" ", ""), candidate.replace(" ", "")
                    if compact in other or other in compact:
                        score += 50
                    for uuid, item in self.index.get(candidate, {}).items():
                        if score > found.get(uuid, (-1, None))[0]:
                            found[uuid] = (score, item)
        return [item for _, item in sorted(found.values(), key=lambda pair: (-pair[0], pair[1].get("url", "")))]

    def research(self, row, body, transport, claim):
        """Publish active ads whose detail record names this exact employer orgnr."""
        research = {"state": "completed", "organisation_number": row["organisation_number"], "feed_state": self.state}
        row.setdefault("research_sources", {})["nav_jobs"] = research
        if self.state not in {"loaded", "partial"}:
            # An unqueried or unloaded source is a failed check, never "ambiguous" (wrong-company doubt) or "not_available".
            state = "failed"
            research.update(state="failed" if self.state == "failed" else "not_queried", availability=state)
            row["availability"]["jobs"] = row["availability"].get("jobs") if row["availability"].get("jobs") == "available" else state
            if self.error:
                row["errors"].append({"module": "nav_jobs", "message": self.error})
            return []
        org = row["organisation_number"]
        units = {str(c["value"].get("organisation_number")): c["value"].get("name") for c in row["claims"]
                 if c["field"] == "locations" and isinstance(c["value"], dict)}
        names = [body.get("navn", "")] + [n for n in units.values() if n] + [h.get("navn", "") for h in body.get("historiskeNavn", [])[-2:]]
        accepted, homepages, detail_failures = 0, [], 0
        candidates = self.candidates(names, [org, *units])
        limit = min(self.max_ads * 2, self.max_candidate_details)
        partial = self.state == "partial" or len(candidates) > limit
        researched = 0
        for item in candidates[:limit]:
            if accepted >= self.max_ads:
                partial = True
                break
            researched += 1
            snap = self.cached_get(transport, BASE + item["url"], headers=self.headers(), detail=True)
            if snap.get("status") != 200:
                detail_failures += 1
                continue
            try:
                detail = json.loads(snap["text"])
                ad = detail["ad_content"]
                employer = ad["employer"]
                if not isinstance(ad, dict) or not isinstance(employer, dict):
                    raise ValueError("invalid ad")
            except (ValueError, TypeError, KeyError):
                detail_failures += 1
                continue
            employer_org = re.sub(r"\D", "", str(employer.get("orgnr") or ""))
            parent_snap = None
            if employer_org != org and employer_org not in units and len(employer_org) == 9:
                # NAV usually names the workplace; prove it is a registered subunit of this exact entity.
                parent_snap = self.cached_get(transport, "https://data.brreg.no/enhetsregisteret/api/underenheter/" + employer_org, "official_registry")
                try:
                    unit = json.loads(parent_snap["text"]) if parent_snap.get("status") == 200 else {}
                except ValueError:
                    unit = {}
                if not isinstance(unit, dict):
                    unit = {}
                if not unit:
                    detail_failures += 1
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
            row["availability"]["jobs"] = "failed" if detail_failures or partial else "not_available"
        research.update(state="partial" if partial or detail_failures else "completed",
                        availability="available" if accepted else ("failed" if detail_failures or partial else "not_available"),
                        candidate_count=len(candidates), detail_requests=researched, accepted_ads=accepted)
        return homepages

    def report(self):
        return {"source": "NAV Job Vacancy Feed (pam-stilling-feed.nav.no)", "state": self.state, "window_days": self.days,
                "feed_pages": self.pages, "detail_requests": self.details,
                "cache_hits": self.cache_hits, "max_candidate_details": self.max_candidate_details,
                "max_detail_requests": self.max_detail_requests,
                "completed_segments": self.complete_segments, "total_segments": self.segments, "error": self.error,
                "indexed_active_employers": len(self.index), "indexed_active_ads": sum(len(v) for v in self.index.values()),
                "token": "NAV_FEED_TOKEN" if os.environ.get("NAV_FEED_TOKEN") else "NAV published public token"}
