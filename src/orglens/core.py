from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import ipaddress
import json
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

STATES = {"available", "not_available", "blocked", "not_applicable", "ambiguous", "failed"}
ENTITY = "https://data.brreg.no/enhetsregisteret/api/enheter/"
FIELDS = ("legal_identity", "financials", "leadership", "locations", "official_website", "description", "jobs", "activity", "owned_profiles")
ORG_LABEL = r"(?:organisasjons(?:nummer|nr)|organisation\s+number|organization\s+number|org(?:anisasjons)?[.\s]*(?:nr|nummer|number))"
UA = "OrgLens/0.1 (Norwegian company research; public sources only)"
MAX_BYTES = 4_000_000


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    temp.replace(path)


def read_inputs(path):
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix == ".json":
        body = json.loads(text)
        values = body if isinstance(body, list) else body["organisation_numbers"]
    elif path.suffix == ".jsonl":
        values = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        values = [line.strip() for line in text.splitlines() if line.strip()]
    result = []
    for item in values:
        value = item.get("organisation_number", item.get("organisasjonsnummer")) if isinstance(item, dict) else item
        org = re.sub(r"[\s-]", "", str(value))
        if not re.fullmatch(r"[0-9]{9}", org):
            raise ValueError(f"Invalid organisation number: {value!r}")
        result.append(org)
    if not result or len(result) != len(set(result)):
        raise ValueError("Input must be nonempty and organisation numbers unique")
    return result


def public_url(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password or p.port not in {None, 80, 443}:
        raise ValueError("Only public HTTP(S) URLs on standard ports are allowed")
    addresses = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("Nonpublic destination rejected")


class BudgetExceeded(RuntimeError):
    pass


class Transport:
    def __init__(self, root, requests=1800, seconds=2400, timeout=12):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.limit = requests
        self.deadline = time.monotonic() + seconds
        self.timeout = timeout
        self.requests = 0
        self.bytes = 0
        self.lock = threading.Lock()
        self.host_locks = {}
        self.host_times = {}
        self.host_delays = {}
        self.local = threading.local()

    def reserve(self, url):
        host = urllib.parse.urlsplit(url).hostname
        with self.lock:
            if self.requests >= self.limit or time.monotonic() >= self.deadline:
                raise BudgetExceeded("Run request/time budget exhausted")
            lock = self.host_locks.setdefault(host, threading.Lock())
        with lock:
            # Respect public hosts with a modest request-start rate.
            delay = self.host_times.get(host, 0) + self.host_delays.get(host, 0.1 if host == "data.brreg.no" else 0.35) - time.monotonic()
            if delay > 0:
                if delay >= self.deadline - time.monotonic():
                    raise BudgetExceeded("Host crawl delay exceeds remaining time budget")
                time.sleep(delay)
            with self.lock:
                if self.requests >= self.limit or time.monotonic() >= self.deadline:
                    raise BudgetExceeded("Run request/time budget exhausted")
                self.requests += 1
                self.local.requests = getattr(self.local, "requests", 0) + 1
                self.host_times[host] = time.monotonic()

    def get(self, url, source_class="official_registry"):
        started = time.monotonic()
        requested = url
        chain = []
        try:
            for _ in range(6):
                if self.requests >= self.limit or time.monotonic() >= self.deadline:
                    raise BudgetExceeded("Run request/time budget exhausted")
                public_url(url)
                self.reserve(url)

                class NoRedirect(urllib.request.HTTPRedirectHandler):
                    def redirect_request(self, *args, **kwargs):
                        return None

                opener = urllib.request.build_opener(NoRedirect())
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/html,text/plain;q=0.8"})
                try:
                    response = opener.open(req, timeout=min(self.timeout, max(0.1, self.deadline - time.monotonic())))
                except urllib.error.HTTPError as exc:
                    response = exc
                with response:
                    status = response.code
                    if status in {301, 302, 303, 307, 308}:
                        chain.append({"url": url, "status": status})
                        url = urllib.parse.urljoin(url, response.headers["Location"])
                        continue
                    raw = response.read(MAX_BYTES + 1)
                    if len(raw) > MAX_BYTES:
                        raise ValueError("Response exceeds safe snapshot limit")
                    charset = response.headers.get_content_charset() or "utf-8"
                    content_type = response.headers.get_content_type()
                sha = digest(raw)
                # Immutable snapshots: identical bytes share storage, observations retain retrieval time.
                dest = self.root / (sha + ".bin")
                if not dest.exists():
                    dest.write_bytes(raw)
                with self.lock:
                    self.bytes += len(raw)
                return {"id": digest({"url": url, "hash": sha})[:24], "requested_url": requested,
                        "source_url": url, "redirect_chain": chain, "status": status,
                        "retrieved_at": now(), "content_sha256": sha, "snapshot_path": f"snapshots/{sha}.bin",
                        "source_class": source_class, "content_type": content_type, "charset": charset,
                        "text": raw.decode(charset, errors="replace"), "elapsed_ms": int((time.monotonic() - started) * 1000)}
            raise ValueError("Redirect limit exceeded")
        except (BudgetExceeded, ValueError, OSError, urllib.error.URLError) as exc:
            return {"source_url": requested, "retrieved_at": now(), "status": 0,
                    "availability": "blocked" if isinstance(exc, ValueError) else "failed",
                    "error": str(exc), "budget_exhausted": isinstance(exc, BudgetExceeded)}


def availability(snapshot):
    code = snapshot["status"]
    if code == 200:
        return "available"
    if code in {404, 410}:
        return "not_available"
    if code in {401, 403, 429, 451}:
        return "blocked"
    return snapshot.get("availability", "failed")


def envelope(org, run_id):
    return {"schema_version": "1.0", "organisation_number": org,
            "run": {"run_id": run_id, "started_at": now(), "terminal_status": "completed"},
            "legal_identity": {}, "claims": [], "evidence": [], "availability": {},
            "changes": [], "errors": [], "source_snapshots": [], "summary": {},
            "operations": {"requests": 0, "runtime_ms": 0, "third_party_cost_usd": 0}}


def attach(row, snapshot):
    if "content_sha256" not in snapshot:
        row["errors"].append({"source_url": snapshot["source_url"], "message": snapshot.get("error", "fetch failed")})
        return None
    safe = {key: value for key, value in snapshot.items() if key != "text"}
    if not any(item["id"] == safe["id"] for item in row["source_snapshots"]):
        row["source_snapshots"].append(safe)
    return safe["id"]


def claim(row, field, value, snapshot, locator, period=None, identity_method="official_organisation_endpoint"):
    if value is None or value == "":
        return
    sid = attach(row, snapshot)
    if snapshot.get("source_row_key"):
        locator = {**locator, "source_row_key": snapshot["source_row_key"], "snapshot_format": snapshot.get("snapshot_format", "jsonl")}
    if not sid:
        raise ValueError("Cannot publish a claim without snapshot evidence")
    eid = digest({"snapshot": sid, "locator": locator})[:24]
    ev = {"id": eid, "snapshot_id": sid, "source_url": snapshot["source_url"],
          "source_class": snapshot["source_class"], "retrieved_at": snapshot["retrieved_at"],
          "content_sha256": snapshot["content_sha256"], "locator": locator,
          "reporting_period": period, "extraction_method": "deterministic_v1", "identity_method": identity_method}
    if not any(item["id"] == eid for item in row["evidence"]):
        row["evidence"].append(ev)
    cid = digest({"org": row["organisation_number"], "field": field, "value": value, "period": period})[:24]
    if not any(item["id"] == cid for item in row["claims"]):
        row["claims"].append({"id": cid, "field": field, "value": value, "availability": "available", "evidence_ids": [eid], "reporting_period": period})


def json_body(snapshot):
    return json.loads(snapshot["text"])


def anchor(row, snapshot):
    attach(row, snapshot)
    row["availability"]["legal_identity"] = availability(snapshot)
    if availability(snapshot) != "available":
        return None
    body = json_body(snapshot)
    if str(body.get("organisasjonsnummer")) != row["organisation_number"]:
        row["availability"]["legal_identity"] = "ambiguous"
        row["errors"].append({"message": "Registry returned a different organisation number"})
        return None
    mapping = {"legal_name": "navn", "legal_form": "organisasjonsform", "industry": "naeringskode1",
               "employees": "antallAnsatte", "business_address": "forretningsadresse", "registered_on": "registreringsdatoEnhetsregisteret",
               "bankrupt": "konkurs", "liquidating": "underAvvikling", "latest_accounts_year": "sisteInnsendteAarsregnskap"}
    for field, key in mapping.items():
        if key in body:
            row["legal_identity"][field] = body[key]
            claim(row, field, body[key], snapshot, {"json_pointer": "/" + key})
    return body


def nested(body, path):
    for key in path:
        if not isinstance(body, dict):
            return None
        body = body.get(key)
    return body


def official(row, transport, module):
    org = row["organisation_number"]
    urls = {"financials": f"https://data.brreg.no/regnskapsregisteret/regnskap/{org}",
            "leadership": ENTITY + org + "/roller", "locations": f"https://data.brreg.no/enhetsregisteret/api/underenheter?overordnetEnhet={org}&size=100"}
    snap = transport.get(urls[module])
    attach(row, snap)
    row["availability"][module] = availability(snap)
    if availability(snap) != "available":
        return
    body = json_body(snap)
    if module == "financials":
        if not isinstance(body, list):
            raise ValueError("Unknown accounts response shape")
        paths = {"revenue": ["resultatregnskapResultat", "driftsresultat", "driftsinntekter", "sumDriftsinntekter"],
                 "operating_result": ["resultatregnskapResultat", "driftsresultat", "driftsresultat"],
                 "annual_result": ["resultatregnskapResultat", "aarsresultat"], "assets": ["eiendeler", "sumEiendeler"],
                 "equity": ["egenkapitalGjeld", "egenkapital", "sumEgenkapital"]}
        for i, record in enumerate(body):
            reported_org = str((record.get("virksomhet") or {}).get("organisasjonsnummer", ""))
            if reported_org != org:
                row["availability"][module] = "ambiguous"
                row["errors"].append({"module": module, "message": "Accounts identify a different legal organisation; record withheld"})
                continue
            # Group and company accounts are kept distinct with original type, currency and period.
            period = record.get("regnskapsperiode")
            if not period:
                continue
            for field, path in paths.items():
                value = nested(record, path)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    claim(row, "financials." + field, {"amount": value, "currency": record.get("valuta"),
                          "account_type": record.get("regnskapstype")}, snap,
                          {"json_pointer": f"/{i}/" + "/".join(path)}, period)
        if row["availability"][module] != "ambiguous" and not any(c["field"].startswith("financials.") for c in row["claims"]):
            row["availability"][module] = "not_available"
    elif module == "leadership":
        for i, group in enumerate(body.get("rollegrupper", [])):
            for j, role in enumerate(group.get("roller", [])):
                if role.get("avregistrert"):
                    continue
                name = (role.get("person") or {}).get("navn") or {}
                display = " ".join(str(name[k]) for k in ("fornavn", "mellomnavn", "etternavn") if name.get(k))
                display = display or (role.get("enhet") or {}).get("navn")
                if display:
                    claim(row, "leadership", {"name": display, "role": (role.get("type") or {}).get("beskrivelse"),
                          "last_changed": group.get("sistEndret")}, snap, {"json_pointer": f"/rollegrupper/{i}/roller/{j}"})
    else:
        for i, unit in enumerate((body.get("_embedded") or {}).get("underenheter", [])):
            if str(unit.get("overordnetEnhet")) != org:
                continue
            claim(row, "locations", {"organisation_number": unit.get("organisasjonsnummer"), "name": unit.get("navn"),
                  "address": unit.get("beliggenhetsadresse")}, snap, {"json_pointer": f"/_embedded/underenheter/{i}"})
        if (body.get("page") or {}).get("totalPages", 1) > 1:
            row["errors"].append({"module": "locations", "message": "First 100 workplaces only; further pages not fetched"})


def soup_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("script,style,noscript,svg"):
        node.decompose()
    return soup, " ".join(soup.stripped_strings)


def identity_proof(org, text):
    # A number is identity evidence only beside a legal organisation label; arbitrary digits never match.
    pattern = ORG_LABEL + r"\s*[:.#-]?\s*((?:\d[\s.]*){9})(?!\d)"
    found = [re.sub(r"\D", "", match.group(1)) for match in re.finditer(pattern, text, re.I)]
    return org in found and len(set(found)) == 1


def site_identity_proof(org, pages):
    """The exact number must identify the homepage or a site-wide footer, not a customer directory."""
    for i, (snapshot, soup, text) in enumerate(pages):
        candidates = [(text, {"text_quote": text})] if i == 0 else []
        for footer in soup.select('footer, [role="contentinfo"]'):
            visible = " ".join(footer.stripped_strings)
            candidates.append((visible, {"css_selector": 'footer, [role="contentinfo"]', "text_quote": visible}))
        for visible, locator in candidates:
            if identity_proof(org, visible):
                match = re.search(ORG_LABEL + r"\s*[:.#-]?\s*((?:\d[\s.]*){9})(?!\d)", visible, re.I)
                if match:
                    locator["text_quote"] = match.group(0)
                return snapshot, locator
    return None


def corroborated_identity(body, text):
    """Registry-linked domain + exact full legal name + full street and postcode."""
    def normalized(value):
        return " ".join(re.findall(r"[\w]+", str(value).casefold()))
    name = normalized(body.get("navn", ""))
    address = body.get("forretningsadresse") or {}
    postcode = str(address.get("postnummer", ""))
    streets = [normalized(x) for x in address.get("adresse", []) if not str(x).lower().startswith("c/o")]
    visible = " " + normalized(text) + " "
    if re.search(ORG_LABEL + r"[\s:.#-]*(?:\d[\s.]*){9}", text, re.I):
        # A conflicting legal number outweighs an otherwise matching name/address.
        return False
    return bool(len(name) >= 8 and " " + name + " " in visible and postcode and " " + postcode + " " in visible
                and any(len(s) >= 5 and " " + s + " " in visible for s in streets))


def crawl_site(row, body, transport, page_limit=4):
    raw_url = body.get("hjemmeside")
    for field in ("official_website", "description", "jobs", "activity", "owned_profiles"):
        row["availability"][field] = "not_available"
    if not raw_url:
        return
    url = raw_url if re.match(r"^https?://", raw_url, re.I) else "https://" + raw_url
    p = urllib.parse.urlsplit(url)
    restricted = {"linkedin.com", "facebook.com", "instagram.com", "indeed.com", "glassdoor.com", "tiktok.com", "x.com", "twitter.com"}
    host = (p.hostname or "").lower()
    if any(host == h or host.endswith("." + h) for h in restricted):
        for field in ("official_website", "description", "jobs", "activity", "owned_profiles"):
            row["availability"][field] = "blocked"
        row["errors"].append({"module": "website", "message": "Restricted platform is not enabled as a collection source"})
        return
    base = urllib.parse.urlunsplit((p.scheme, p.netloc, "/", "", ""))
    robot_snap = transport.get(urllib.parse.urljoin(base, "robots.txt"), "company_owned")
    attach(row, robot_snap)
    robot = urllib.robotparser.RobotFileParser()
    if robot_snap["status"] == 200:
        robot.parse(robot_snap["text"].splitlines())
        crawl_delay = robot.crawl_delay(UA) or robot.crawl_delay("*") or 0
        request_rate = robot.request_rate(UA) or robot.request_rate("*")
        gap = max(.35, crawl_delay, request_rate.seconds / request_rate.requests if request_rate else 0)
        with transport.lock:
            transport.host_delays[host] = max(transport.host_delays.get(host, 0), gap)
    elif robot_snap["status"] in {404, 410}:
        robot.parse([])
    else:
        for field in ("official_website", "description", "jobs", "activity", "owned_profiles"):
            row["availability"][field] = availability(robot_snap)
        return
    if not robot.can_fetch(UA, url):
        for field in ("official_website", "description", "jobs", "activity", "owned_profiles"):
            row["availability"][field] = "blocked"
        return
    home = transport.get(url, "company_owned")
    attach(row, home)
    row["availability"]["official_website"] = availability(home)
    if availability(home) != "available":
        for field in ("description", "jobs", "activity", "owned_profiles"):
            row["availability"][field] = availability(home)
        return
    if urllib.parse.urlsplit(home["source_url"]).hostname != p.hostname:
        # Do not reuse a different host's robots policy or trust redirected brands.
        for field in ("official_website", "description", "jobs", "activity", "owned_profiles"):
            row["availability"][field] = "ambiguous"
        return
    soup, text = soup_text(home["text"])
    pages = [(home, soup, text)]
    links = []
    terms = ("kontakt", "contact", "om-oss", "about", "career", "karriere", "jobb", "jobs", "news", "nyhet", "aktuelt")
    for a in soup.find_all("a", href=True):
        target = urllib.parse.urljoin(home["source_url"], a["href"]).split("#")[0]
        target_p = urllib.parse.urlsplit(target)
        if target_p.hostname == p.hostname and target_p.scheme in {"http", "https"} and any(term in (target + " " + a.get_text()).lower() for term in terms):
            if target not in links and target != home["source_url"]:
                links.append(target)
    links.sort(key=lambda x: 0 if any(t in x.lower() for t in ("kontakt", "contact", "about", "om-oss")) else 1)
    for target in links[:page_limit - 1]:
        if not robot.can_fetch(UA, target):
            continue
        snap = transport.get(target, "company_owned")
        attach(row, snap)
        if availability(snap) == "available" and urllib.parse.urlsplit(snap["source_url"]).hostname == p.hostname:
            parsed, visible = soup_text(snap["text"])
            pages.append((snap, parsed, visible))
    proof = site_identity_proof(row["organisation_number"], pages)
    method = "labelled_organisation_number"
    if not proof:
        for field in ("official_website", "description", "jobs", "activity", "owned_profiles"):
            row["availability"][field] = "ambiguous"
        row["errors"].append({"module": "website", "message": "No unambiguous labelled organisation number on company pages"})
        return
    proof_snap, proof_locator = proof
    claim(row, "official_website", home["source_url"], proof_snap, proof_locator, identity_method=method)
    row["availability"]["official_website"] = "available"
    for snap, parsed, visible in pages:
        # Additional explicit legal entities make a page ambiguous for company facts.
        if method == "labelled_organisation_number" and re.search(ORG_LABEL, visible, re.I) and not identity_proof(row["organisation_number"], visible):
            continue
        meta = parsed.find("meta", attrs={"name": "description"})
        description = meta.get("content", "").strip() if meta else ""
        if description and snap is home:
            claim(row, "description", description, snap, {"css_selector": "meta[name=description]", "attribute": "content"}, identity_method="verified_company_site")
            row["availability"]["description"] = "available"
        for script in BeautifulSoup(snap["text"], "html.parser").find_all("script", attrs={"type": "application/ld+json"}):
            try:
                graph = json.loads(script.string or script.get_text())
            except (ValueError, TypeError):
                continue
            nodes = graph if isinstance(graph, list) else [graph]
            nodes = [child for node in nodes if isinstance(node, dict) for child in node.get("@graph", [node])]
            for node in nodes:
                typ = node.get("@type")
                types = typ if isinstance(typ, list) else [typ]
                if "Organization" in types and str(node.get("taxID", "")).replace(" ", "") == row["organisation_number"]:
                    same_as = node.get("sameAs", [])
                    same_as = [same_as] if isinstance(same_as, str) else same_as
                    for linked in same_as:
                        if isinstance(linked, str) and urllib.parse.urlsplit(linked).scheme in {"http", "https"}:
                            claim(row, "owned_profiles", {"url": linked, "relation": "company_declared_sameAs; external content not fetched"},
                                  snap, {"jsonld": node}, identity_method="exact_taxID_on_verified_company_site")
                            row["availability"]["owned_profiles"] = "available"
                if "JobPosting" in types and node.get("title") and node.get("datePosted"):
                    hiring = node.get("hiringOrganization") or {}
                    legal_name = str(body.get("navn", "")).casefold()
                    if not isinstance(hiring, dict) or str(hiring.get("name", "")).casefold() != legal_name:
                        continue
                    expires = node.get("validThrough")
                    if expires and str(expires)[:10] < now()[:10]:
                        continue
                    claim(row, "jobs", {"title": node["title"], "date_posted": node["datePosted"], "valid_through": expires,
                          "url": node.get("url", snap["source_url"])}, snap,
                          {"jsonld": node}, identity_method="verified_site_and_exact_hiring_name")
                    row["availability"]["jobs"] = "available"
                if any(t in types for t in ("NewsArticle", "Article", "BlogPosting")) and node.get("headline") and node.get("datePublished"):
                    claim(row, "activity", {"headline": node["headline"], "published_at": node["datePublished"], "url": snap["source_url"]}, snap,
                          {"jsonld": node}, identity_method="verified_company_site")
                    row["availability"]["activity"] = "available"


def finish(row, previous=None):
    for field in FIELDS:
        row["availability"].setdefault(field, "failed")
    row["run"]["completed_at"] = now()
    row["availability_status"] = "available" if row["legal_identity"] else row["availability"]["legal_identity"]
    # Diff field sets, not source hashes or volatile retrieval timestamps.
    before = {}
    for c in (previous or {}).get("claims", []):
        before.setdefault(c["field"], []).append(c)
    after = {}
    for c in row["claims"]:
        after.setdefault(c["field"], []).append(c)
    retained = []
    for field, old in before.items():
        family = "financials" if field.startswith("financials.") else field if field in FIELDS else "legal_identity"
        if row["availability"].get(family) in {"failed", "blocked", "ambiguous"}:
            retained.extend({**c, "stale": True} for c in old)
            continue
        current = after.get(field, [])
        if sorted(digest({"value": c["value"], "period": c.get("reporting_period")}) for c in old) != sorted(digest({"value": c["value"], "period": c.get("reporting_period")}) for c in current):
            row["changes"].append({"field": field, "type": "changed" if current else "removed",
                                   "previous_claims": old, "current_claims": current})
    if previous:
        for field in after.keys() - before.keys():
            row["changes"].append({"field": field, "type": "added", "previous_claims": [], "current_claims": after[field]})
    row["refresh"] = {"previous_run_id": (previous or {}).get("run", {}).get("run_id"), "material_changes": len(row["changes"]),
                       "last_known_claims": retained, "previous_evidence": (previous or {}).get("evidence", []),
                       "previous_snapshots": (previous or {}).get("source_snapshots", [])}
    facts = {c["field"]: c for c in row["claims"]}
    observed_periods = [c.get("reporting_period") for c in row["claims"] if c["field"].startswith("financials.")]
    ends = [p.get("tilDato") for p in observed_periods if isinstance(p, dict) and p.get("tilDato")]
    latest_end = max(ends, default=None)
    expected_year = str(row["legal_identity"].get("latest_accounts_year") or "")
    row["financial_freshness"] = {"latest_observed_period_end": latest_end, "registry_latest_filing_year": expected_year or None,
                                  "latest_filing_covered": bool(latest_end and expected_year and str(latest_end)[:4] == expected_year)}
    if latest_end and expected_year and str(latest_end)[:4] != expected_year:
        row["errors"].append({"module": "financials", "message": f"Accounts retrieved end {latest_end}; registry indicates filing year {expected_year}. Latest filing values remain unverified."})
    sentences = []
    for field in ("legal_name", "industry", "employees", "description"):
        if field in facts:
            value = facts[field]["value"]
            if field == "industry" and isinstance(value, dict):
                value = value.get("beskrivelse", value.get("kode"))
            sentences.append({"text": f"{field.replace('_', ' ').capitalize()}: {value}",
                              "evidence_ids": facts[field]["evidence_ids"]})
    for field in ("financials.revenue", "financials.annual_result"):
        financial = [c for c in row["claims"] if c["field"] == field]
        financial.sort(key=lambda c: json.dumps(c.get("reporting_period"), sort_keys=True), reverse=True)
        if financial:
            c = financial[0]
            sentences.append({"text": f"Latest retrieved {field.split('.')[-1].replace('_', ' ')}: {c['value']['amount']:,} {c['value'].get('currency')}; period {json.dumps(c['reporting_period'], ensure_ascii=False)}; account type {c['value'].get('account_type')}", "evidence_ids": c["evidence_ids"]})
    row["summary"] = {"statements": sentences, "unknowns": [{"field": k, "state": v} for k, v in row["availability"].items() if v != "available"],
                      "changes": len(row["changes"]), "method": "evidence_bounded_templates"}
    row["field_availability"] = {"employees": "available" if "employees" in facts else "not_available",
                                 "latest_filing_values": "available" if row["financial_freshness"]["latest_filing_covered"] else "not_available"}
    for field, state in row["field_availability"].items():
        if state != "available":
            row["summary"]["unknowns"].append({"field": field, "state": state})
    return row


def validate(rows, orgs, snapshots=None):
    errors = []
    if [r["organisation_number"] for r in rows] != orgs:
        errors.append("Output membership/order differs from input")
    for row in rows:
        ev = {e["id"]: e for e in row["evidence"]}
        source_ids = {s["id"] for s in row["source_snapshots"]}
        if row["run"].get("terminal_status") != "completed" or not row["run"].get("completed_at"):
            errors.append("Missing terminal run metadata")
        if set(row["availability"]) != set(FIELDS) or any(v not in STATES for v in row["availability"].values()):
            errors.append(f"Invalid availability: {row['organisation_number']}")
        for c in row["claims"]:
            if not c["evidence_ids"] or any(e not in ev for e in c["evidence_ids"]):
                errors.append("Claim has missing evidence")
            if c["field"].startswith("financials.") and not c.get("reporting_period"):
                errors.append("Financial claim missing reporting period")
        for e in ev.values():
            if e.get("snapshot_id") not in source_ids:
                errors.append("Evidence references absent snapshot")
            if not all(e.get(k) for k in ("source_url", "retrieved_at", "content_sha256", "locator")):
                errors.append("Incomplete evidence")
        if snapshots:
            for s in row["source_snapshots"]:
                path = Path(snapshots) / (s["content_sha256"] + ".bin")
                if not path.exists() or digest(path.read_bytes()) != s["content_sha256"]:
                    errors.append("Snapshot missing or corrupted")
    return {"passed": not errors, "errors": errors, "envelopes": len(rows)}


def run_batch(orgs, output, *, run_id, requests=1800, seconds=2400, workers=12, previous=None, pages=4, modules=("financials", "leadership", "locations", "website"), registry=None, registry_retrieved_at=None, replay=None, discovery=None, agent=None):
    if agent and replay:
        raise ValueError("AI network research is not allowed in offline replay")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if replay:
        from .replay import ReplayTransport
        transport = ReplayTransport(output / "snapshots", replay, requests, seconds)
    else:
        transport = Transport(output / "snapshots", requests, seconds)
    started = time.monotonic()
    rows = [envelope(org, run_id) for org in orgs]
    bodies = {}
    prior = {r["organisation_number"]: r for r in previous or []}
    replay_seeds = {}
    if replay and (Path(replay) / "envelopes.jsonl").exists():
        replay_seeds = {r["organisation_number"]: r for r in (json.loads(line) for line in (Path(replay) / "envelopes.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())}
    registry_rows = {}
    if registry:
        if not registry_retrieved_at:
            raise ValueError("Frozen registry requires its actual retrieval timestamp")
        # JSONL accepts original official entity objects. CSV supports BRREG's public bulk layout.
        source = Path(registry)
        with source.open("rb") as source_bytes:
            snapshot_hash = hashlib.file_digest(source_bytes, "sha256").hexdigest()
        dest = transport.root / (snapshot_hash + ".bin")
        if not dest.exists():
            dest.write_bytes(source.read_bytes())
        wanted = set(orgs)
        with source.open(encoding="utf-8-sig", newline="") as handle:
            if source.suffix == ".csv":
                sample_text = handle.read(8192)
                handle.seek(0)
                dialect = csv.Sniffer().sniff(sample_text, delimiters=",;")
                iterable = csv.DictReader(handle, dialect=dialect)
            else:
                iterable = (json.loads(line) for line in handle if line.strip())
            for raw in iterable:
                org = str(raw.get("organisasjonsnummer", ""))
                if org in wanted:
                    if source.suffix == ".csv":
                        normalized = {}
                        for key, value in raw.items():
                            if not value or key is None:
                                continue
                            node = normalized
                            parts = key.split(".")
                            for part in parts[:-1]:
                                node = node.setdefault(part, {})
                            node[parts[-1]] = value
                        for key in ("konkurs", "underAvvikling"):
                            if key in normalized and str(normalized[key]).lower() in {"true", "false"}:
                                normalized[key] = str(normalized[key]).lower() == "true"
                        if str(normalized.get("antallAnsatte", "")).isdigit():
                            normalized["antallAnsatte"] = int(normalized["antallAnsatte"])
                        raw = normalized
                        address = raw.get("forretningsadresse")
                        if isinstance(address, dict) and isinstance(address.get("adresse"), str):
                            address["adresse"] = [address["adresse"]]
                    registry_rows[org] = raw

    def task(row, module):
        began = time.monotonic()
        before_requests = getattr(transport.local, "requests", 0)
        try:
            if module == "identity":
                org = row["organisation_number"]
                raw = registry_rows.get(org)
                if raw is not None:
                    local_snapshot = {"id": digest({"hash": snapshot_hash, "row": org})[:24], "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
                                      "source_class": "official_registry_frozen", "status": 200, "retrieved_at": registry_retrieved_at,
                                      "content_sha256": snapshot_hash, "snapshot_path": f"snapshots/{snapshot_hash}.bin",
                                      "source_row_key": org, "snapshot_format": source.suffix.lstrip("."), "text": json.dumps(raw)}
                    body = anchor(row, local_snapshot)
                else:
                    body = anchor(row, transport.get(ENTITY + org))
                if body:
                    # A previous discovered website is a candidate, never fresh evidence.
                    seed_row = prior.get(org) or replay_seeds.get(org)
                    if seed_row and not body.get("hjemmeside"):
                        seed = next((c["value"] for c in seed_row.get("claims", []) if c["field"] == "official_website"), None)
                        if isinstance(seed, str):
                            body = {**body, "hjemmeside": seed}
                    bodies[row["organisation_number"]] = body
            elif module == "website":
                crawl_site(row, bodies[row["organisation_number"]], transport, pages)
            elif module == "agent":
                agent.research(row, bodies[row["organisation_number"]], transport, pages)
            elif module == "discovery":
                body = bodies[row["organisation_number"]]
                calls_before = getattr(discovery.local, "calls", 0)
                try:
                    candidates = discovery.discover(body, transport)
                    row["operations"]["third_party_cost_usd"] = float(discovery.unit_cost)
                    for candidate in candidates:
                        crawl_site(row, {**body, "hjemmeside": candidate}, transport, pages)
                        if row["availability"].get("official_website") == "available":
                            break
                finally:
                    charged = getattr(discovery.local, "calls", 0) - calls_before
                    row["operations"]["third_party_cost_usd"] = float(discovery.unit_cost * charged)
            else:
                official(row, transport, module)
        except Exception as exc:
            field = "legal_identity" if module == "identity" else "official_website" if module in {"website", "discovery"} else module
            if field in FIELDS:
                row["availability"][field] = "failed"
            row["errors"].append({"module": module, "message": f"{type(exc).__name__}: {exc}"})
        row["operations"]["runtime_ms"] += int((time.monotonic() - began) * 1000)
        row["operations"]["requests"] += getattr(transport.local, "requests", 0) - before_requests

    # Breadth before depth prevents early entities consuming every request.
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for module in ("identity", *modules, *(("discovery",) if discovery else ()), *(("agent",) if agent else ())):
            selected = rows if module == "identity" else [r for r in rows if r["organisation_number"] in bodies]
            if module == "discovery":
                selected = [r for r in selected if r["availability"].get("official_website") != "available"]
            list(pool.map(lambda r: task(r, module), selected))
            write_rows(output / "checkpoint.jsonl", rows)
    for row in rows:
        finish(row, prior.get(row["organisation_number"]))
        if row.get("agent", {}).get("selected_claim_ids"):
            chosen = set(row["agent"]["selected_claim_ids"])
            statements = []
            for c in row["claims"]:
                if c["id"] in chosen:
                    statements.append({"text": f"{c['field']}: {json.dumps(c['value'], ensure_ascii=False)}" + (f"; reporting period: {json.dumps(c['reporting_period'], ensure_ascii=False)}" if c.get("reporting_period") else ""), "evidence_ids": c["evidence_ids"], "claim_id": c["id"]})
            row["summary"]["statements"] = statements
            row["summary"]["method"] = "model_selected_verified_claims; deterministic_fact_rendering"
        # Count all observations including redirects. Fetch failures have run-level accounting.
    write_rows(output / "envelopes.jsonl", rows)
    validation = validate(rows, orgs, output / "snapshots")
    durations = sorted(r["operations"]["runtime_ms"] for r in rows)
    report = {"run_id": run_id, "completed_at": now(), "companies": len(orgs), "envelopes": len(rows),
              "validation": validation, "requests": transport.requests, "bytes": transport.bytes,
              "runtime_seconds": round(time.monotonic() - started, 3), "third_party_cost_usd": float(discovery.spent) if discovery else 0,
              "limits": {"requests": requests, "seconds": seconds}, "p50_company_ms": durations[len(durations)//2],
              "p95_company_ms": durations[min(len(durations)-1, int(len(durations)*.95))],
              "coverage": {f: sum(r["availability"][f] == "available" for r in rows) for f in FIELDS},
              "states": {s: sum(v == s for r in rows for v in r["availability"].values()) for s in STATES},
              "score": None, "score_note": "Operational smoke test; no hidden labels or official competition score"}
    report["registry_snapshot"] = {"path": str(registry), "retrieved_at": registry_retrieved_at, "sha256": snapshot_hash} if registry else None
    report["mode"] = "saved_source_replay" if replay else "live"
    report["replay_source"] = str(replay) if replay else None
    report["agent"] = agent.report() if agent else None
    if agent:
        from .costs import estimate_costs
        report["third_party_cost_usd"] = None
        report["cost_estimate"] = estimate_costs(report["agent"], len(orgs))
        report["agent"]["companies_with_model_calls"] = sum(bool(r.get("agent", {}).get("model_calls")) for r in rows)
        report["agent"]["completed_tool_loops"] = sum(r.get("agent", {}).get("status") == "completed" for r in rows)
    report["discovery"] = {"provider": "Brave Web Search", "queries": discovery.calls, "declared_unit_cost": float(discovery.unit_cost),
                           "max_cost_usd": float(discovery.max_cost), "live_verified": False} if discovery else None
    write_json(output / "run-report.json", report)
    return rows, report
