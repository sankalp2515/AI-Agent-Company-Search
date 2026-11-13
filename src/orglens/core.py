from __future__ import annotations

import concurrent.futures
import csv
import gzip
import hashlib
import ipaddress
import json
import re
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import warnings

import certifi
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

STATES = {"available", "not_available", "blocked", "not_applicable", "ambiguous", "failed"}
ENTITY = "https://data.brreg.no/enhetsregisteret/api/enheter/"
FIELDS = ("legal_identity", "financials", "leadership", "locations", "official_website", "description", "jobs", "activity", "owned_profiles", "contact")
SITE_FIELDS = ("official_website", "description", "activity", "owned_profiles", "contact")
ORG_LABEL = r"(?:organisasjons(?:nummer|nr)|organisation\s+number|organization\s+number|org(?:anisasjons)?[.\s]*(?:nr|nummer|number))"
UA = "OrgLens/0.1 (Norwegian company research; public sources only)"
from .openrecords import FOOD_INSPECTIONS_MAX_BYTES, FOOD_INSPECTIONS_URL, FoodInspections

MAX_BYTES = 4_000_000
MAX_READ_SECONDS = 25
# Named official bulk files only. Everything else keeps the general limit.
LARGE_RESPONSE_LIMITS = {FOOD_INSPECTIONS_URL: FOOD_INSPECTIONS_MAX_BYTES}
TLS = ssl.create_default_context(cafile=certifi.where())  # pinned CA bundle, identical on every OS
FAST_HOSTS = {"data.brreg.no", "pam-stilling-feed.nav.no"}


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
        self.site_cache = {}
        self.site_cache_locks = {}
        self.site_cache_hits = 0

    def reserve(self, url):
        host = urllib.parse.urlsplit(url).hostname
        with self.lock:
            if self.requests >= self.limit or time.monotonic() >= self.deadline:
                raise BudgetExceeded("Run request/time budget exhausted")
            lock = self.host_locks.setdefault(host, threading.Lock())
        with lock:
            # Respect public hosts with a modest request-start rate.
            delay = self.host_times.get(host, 0) + self.host_delays.get(host, 0.1 if host in FAST_HOSTS else 0.35) - time.monotonic()
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

    def get(self, url, source_class="official_registry", headers=None):
        if source_class != "company_owned" or headers:
            return self._get(url, source_class, headers)
        with self.lock:
            lock = self.site_cache_locks.setdefault(url, threading.Lock())
        with lock:
            with self.lock:
                cached = self.site_cache.get(url)
                if cached is not None:
                    self.site_cache_hits += 1
                    return dict(cached)
            snapshot = self._get(url, source_class, headers)
            if snapshot.get('status') in {200, 404, 410}:
                with self.lock:
                    self.site_cache[url] = dict(snapshot)
            return snapshot

    def _get(self, url, source_class="official_registry", headers=None):
        started = time.monotonic()
        requested = url
        origin_host = urllib.parse.urlsplit(url).hostname
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

                opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=TLS))
                extra = headers if headers and urllib.parse.urlsplit(url).hostname == origin_host else {}
                # Credentials never follow a redirect to another host.
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/html,text/plain;q=0.8", **extra})
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
                    # Chunked read with a wall-clock cap: a trickling server cannot hold a worker past the budget.
                    read_started, buffer = time.monotonic(), bytearray()
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        buffer += chunk
                        if len(buffer) > LARGE_RESPONSE_LIMITS.get(requested, MAX_BYTES):
                            raise ValueError("Response exceeds safe snapshot limit")
                        if time.monotonic() - read_started > MAX_READ_SECONDS or time.monotonic() >= self.deadline:
                            raise ValueError("Response body too slow; abandoned")
                    raw = bytes(buffer)
                    charset = response.headers.get_content_charset() or "utf-8"
                    content_type = response.headers.get_content_type()
                    retry_after = response.headers.get('Retry-After')
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
                        "retry_after": retry_after,
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


def activity_identity(value):
    if not isinstance(value,dict) or not value.get('url') or not value.get('published_at'):
        return None
    date=parsed_date(value['published_at'])
    if date.year<1900:
        return None
    url=urllib.parse.urlsplit(value['url'])
    return urllib.parse.urlunsplit((url.scheme,url.netloc.lower(),url.path.rstrip('/'),url.query,'')),date.date().isoformat()


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
    if field == 'activity':
        key=activity_identity(value)
        if key:
            existing=next((c for c in row['claims'] if c['field']=='activity' and activity_identity(c['value'])==key),None)
            if existing:
                if eid not in existing['evidence_ids']:existing['evidence_ids'].append(eid)
                return
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
    official_extras(row, body, snapshot)
    return body


def official_extras(row, body, snapshot):
    """Further registry facts that cost no extra request: purpose, capital, phone, group link and dated events."""
    purpose = body.get("aktivitet") or body.get("vedtektsfestetFormaal")
    if purpose:
        key = "aktivitet" if body.get("aktivitet") else "vedtektsfestetFormaal"
        claim(row, "registered_activity", " ".join(purpose) if isinstance(purpose, list) else str(purpose), snapshot, {"json_pointer": "/" + key})
    extra = [code for code in (body.get("naeringskode2"), body.get("naeringskode3")) if code]
    if extra:
        claim(row, "secondary_industries", extra, snapshot, {"json_pointer": "/naeringskode2"})
    for field, key in (("founded_on", "stiftelsesdato"), ("municipality", None), ("in_group", "erIKonsern"), ("parent_organisation_number", "overordnetEnhet")):
        value = (body.get("forretningsadresse") or {}).get("kommune") if field == "municipality" else body.get(key)
        if value not in (None, ""):
            row["legal_identity"][field] = value
            claim(row, field, value, snapshot, {"json_pointer": "/forretningsadresse/kommune" if field == "municipality" else "/" + key})
    capital = body.get("kapital")
    if isinstance(capital, dict) and capital.get("belop") is not None:
        claim(row, "share_capital", {"amount": capital.get("belop"), "currency": capital.get("valuta"), "type": capital.get("type"), "effective": capital.get("innfortDato")},
              snapshot, {"json_pointer": "/kapital"}, period={"effective": capital.get("innfortDato")})
    for kind, key in (("phone", "telefon"), ("mobile", "mobil"), ("email", "epostadresse")):
        if body.get(key):
            claim(row, "contact", {"type": kind, "value": body[key], "source": "Enhetsregisteret"}, snapshot, {"json_pointer": "/" + key})
            row["availability"]["contact"] = "available"
    events = []
    for date_key, label in (("registreringsdatoEnhetsregisteret", "Registered in the Central Coordinating Register"), ("registreringsdatoForetaksregisteret", "Registered in the Register of Business Enterprises"),
                            ("registreringsdatoMerverdiavgiftsregisteret", "Registered for VAT"), ("vedtektsdato", "Articles of association dated"),
                            ("registreringsdatoAntallAnsatteEnhetsregisteret", "Registered employee count updated")):
        if body.get(date_key):
            events.append((str(body[date_key])[:10], label, "/" + date_key))
    if isinstance(capital, dict) and capital.get("innfortDato"):
        events.append((str(capital["innfortDato"])[:10], "Share capital registered as " + fmt_amount_exact(capital.get("belop"), capital.get("valuta")), "/kapital/innfortDato"))
    for i, old in enumerate(body.get("historiskeNavn") or []):
        if old.get("tilDato"):
            events.append((str(old["tilDato"])[:10], f"Changed name from {old.get('navn')}", f"/historiskeNavn/{i}"))
    for date, label, pointer in sorted(events, reverse=True)[:8]:
        claim(row, "activity", {"headline": label, "published_at": date, "kind": "official_registry_event"}, snapshot, {"json_pointer": pointer}, period={"date": date})
    if events:
        row["availability"]["activity"] = "available"


def nested(body, path):
    for key in path:
        if not isinstance(body, dict):
            return None
        body = body.get(key)
    return body


def fetch_official(transport, url, attempts=3):
    """Official endpoints: bounded retries on throttling, server errors and transport failures."""
    for attempt in range(attempts):
        snap = transport.get(url)
        if snap.get("budget_exhausted") or snap.get("status") not in {0, 429, 500, 502, 503, 504} or attempt == attempts - 1:
            return snap
        lock = getattr(transport, "lock", None)
        if lock is None:
            return snap
        with lock:
            # Shared retry allowance: a source-wide outage must not stall the whole batch.
            left = getattr(transport, "retries_left", max(20, getattr(transport, "limit", 0) // 40))
            if left <= 0:
                return snap
            transport.retries_left = left - 1
        time.sleep(1.5 * (attempt + 1))
    return snap


def official(row, transport, module):
    org = row["organisation_number"]
    urls = {"financials": f"https://data.brreg.no/regnskapsregisteret/regnskap/{org}",
            "leadership": ENTITY + org + "/roller", "locations": f"https://data.brreg.no/enhetsregisteret/api/underenheter?overordnetEnhet={org}&size=100"}
    snap = fetch_official(transport, urls[module])
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
                if not display:
                    # The register returns a firm's name as a list of name parts.
                    firm = (role.get("enhet") or {}).get("navn")
                    display = " ".join(str(part) for part in firm if part) if isinstance(firm, list) else firm
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


RESTRICTED = {"linkedin.com", "facebook.com", "instagram.com", "indeed.com", "glassdoor.com", "tiktok.com", "x.com", "twitter.com"}
SOCIAL = {"linkedin.com": "linkedin", "facebook.com": "facebook", "instagram.com": "instagram", "x.com": "x", "twitter.com": "x",
          "youtube.com": "youtube", "tiktok.com": "tiktok", "pinterest.com": "pinterest", "vimeo.com": "vimeo", "github.com": "github"}
CONTACT_TERMS = ("kontakt", "contact", "om-oss", "om_oss", "omoss", "about", "personvern", "privacy", "vilkar", "salgsbetingelser", "impressum")
MORE_TERMS = ("career", "karriere", "jobb", "jobs", "stilling", "ledig", "news", "nyhet", "aktuelt", "blogg", "blog", "presse")
MVA = r"\bNO[\s-]*((?:\d[\s.]*){9})\s*MVA\b"
TRUSTED_ORIGINS = {"registry", "nav_employer"}


def labelled_numbers(text):
    found = [re.sub(r"\D", "", m.group(1)) for m in re.finditer(ORG_LABEL + r"\s*[:.#-]?\s*((?:\d[\s.]*){9})(?!\d)", text, re.I)]
    found += [re.sub(r"\D", "", m.group(1)) for m in re.finditer(MVA, text, re.I)]
    return [f for f in found if len(f) == 9]


def jsonld_nodes(html):
    nodes = []
    for script in BeautifulSoup(html, "html.parser").find_all("script", attrs={"type": "application/ld+json"}):
        try:
            graph = json.loads(script.string or script.get_text())
        except (ValueError, TypeError):
            continue
        for node in graph if isinstance(graph, list) else [graph]:
            if isinstance(node, dict):
                nodes.extend(child for child in node.get("@graph", [node]) if isinstance(child, dict))
    return nodes


def node_types(node):
    typ = node.get("@type")
    return typ if isinstance(typ, list) else [typ]


def jsonld_org_ids(node):
    values = []
    # LEI/DUNS and suffixes of foreign identifiers are not Norwegian org numbers.
    for key in ("taxID", "vatID", "identifier"):
        raw = node.get(key)
        for item in raw if isinstance(raw, list) else [raw]:
            if isinstance(item, dict):
                kind = str(item.get("propertyID") or "").lower()
                if kind and not any(x in kind for x in ("org", "vat", "tax", "brreg")):
                    continue
                item = item.get("value")
            if item:
                match = re.fullmatch(r"(?:NO\s*)?((?:\d[\s.]*){9})(?:\s*MVA)?", str(item).strip(), re.I)
                if match:
                    values.append(re.sub(r"\D", "", match[1]))
    return values


def social_profile(url):
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or "").lower().removeprefix("www.").removeprefix("m.").removeprefix("no.")
    platform = next((v for k, v in SOCIAL.items() if host == k or host.endswith("." + k)), None)
    path = p.path.rstrip("/")
    if not platform or p.scheme not in {"http", "https"} or not path or path.count("/") > 3:
        return None
    lowered = path.lower()
    if platform == "facebook" and (re.fullmatch(r"/\d+_\d+", lowered) or lowered in {"/photo.php", "/story.php", "/permalink.php", "/video.php", "/photo", "/reel"}):
        return None
    if any(x in lowered for x in ("sharer", "/share", "intent/", "/plugins", "dialog/", "/hashtag", "/watch", "/p/", "/reel", "/status/", "/posts/", "/events/")):
        return None
    if lowered in {"/home", "/login", "/privacy", "/legal", "/policies", "/terms"}:
        return None
    query = ""
    if platform == "facebook" and lowered == "/profile.php":
        identifiers = urllib.parse.parse_qs(p.query, keep_blank_values=True).get("id", [])
        if len(identifiers) != 1 or not re.fullmatch(r"[0-9]+", identifiers[0]):
            return None
        query = urllib.parse.urlencode({"id": identifiers[0]})
    return {"platform": platform, "url": urllib.parse.urlunsplit(("https", p.netloc.lower().removeprefix("m."), path, query, ""))}


def proof_on_pages(org, legal_name, pages):
    """Return (snapshot, locator, method) proving the exact entity, or a conflict marker."""
    from .names import text_contains_name, distinctive, name_tokens
    if conflicting_number(org, pages):
        return None
    found = site_identity_proof(org, pages)
    if found:
        return found[0], found[1], "labelled_organisation_number"
    for i, (snapshot, soup, text) in enumerate(pages):
        numbers = set(labelled_numbers(text))
        if numbers == {org}:
            url = snapshot["source_url"].lower()
            # Subpages count only when they are the company's own contact/about/terms page about itself.
            names_here = text_contains_name(text, legal_name) or any(t in translit_text(text) for t in distinctive(name_tokens(legal_name)))
            if i == 0 or (any(t in url for t in CONTACT_TERMS) and names_here):
                match = re.search(ORG_LABEL + r"\s*[:.#-]?\s*((?:\d[\s.]*){9})(?!\d)|" + MVA, text, re.I)
                return snapshot, {"text_quote": match.group(0) if match else org, "page_role": "home" if i == 0 else "contact_or_about"}, "labelled_organisation_number"
        for node in jsonld_nodes(snapshot["text"]):
            if any(t in ("Organization", "LocalBusiness", "Corporation", "Store", "ProfessionalService") for t in node_types(node)) and org in jsonld_org_ids(node):
                return snapshot, {"jsonld": {k: node.get(k) for k in ("@type", "name", "taxID", "vatID", "identifier")}}, "jsonld_organisation_identifier"
    return None


def translit_text(text):
    from .names import translit
    return " ".join(re.findall(r"[a-z0-9]+", translit(text)))


def conflicting_number(org, pages):
    numbers = set()
    for i, (snapshot, soup, text) in enumerate(pages):
        visible = [text] if i == 0 else [" ".join(f.stripped_strings) for f in soup.select('footer, [role="contentinfo"]')]
        for chunk in visible:
            numbers |= set(labelled_numbers(chunk))
        for node in jsonld_nodes(snapshot["text"]):
            if any(t in ("Organization", "LocalBusiness", "Corporation", "Store", "ProfessionalService") for t in node_types(node)):
                numbers.update(jsonld_org_ids(node))
    return bool(numbers - {org})


def leader_names(row):
    """Registered natural-person roles; external auditor/accountant firms are excluded."""
    names = []
    for c in row["claims"]:
        if c["field"] == "leadership" and isinstance(c["value"], dict):
            role = str(c["value"].get("role") or "").lower()
            name = str(c["value"].get("name") or "")
            if any(x in role for x in ("revisor", "regnskapsf")) or re.search(r"\b(AS|ASA|ANS|DA|SA)\b", name):
                continue
            parts = name.split()
            if len(parts) >= 2 and len(parts[-1]) >= 3:
                names.append((parts[0], parts[-1], name))
    return names


def leader_on_pages(row, pages):
    for first, last, full in leader_names(row):
        pattern = re.compile(r"\b" + re.escape(first) + r"\b(?:\s+\w+\.?){0,2}\s+" + re.escape(last) + r"\b", re.I)
        for snapshot, soup, text in pages:
            match = pattern.search(text)
            if match:
                return snapshot, {"text_quote": match.group(0), "corroboration": f"registered role holder {full} named on site"}
    return None


OPERATING_ROLES = ("daglig leder", "innehaver", "administrerende")


def operating_leader_on_pages(row, pages, legal):
    """Operating head (CEO/owner) named on a site that also names the company itself."""
    from .names import distinctive, name_tokens
    words = distinctive(name_tokens(legal)) or name_tokens(legal)
    heads = [c for c in row["claims"] if c["field"] == "leadership" and isinstance(c["value"], dict)
             and any(r in str(c["value"].get("role") or "").lower() for r in OPERATING_ROLES)]
    for c in heads:
        parts = str(c["value"].get("name") or "").split()
        if len(parts) < 2 or len(parts[-1]) < 3 or re.search(r"\b(AS|ASA|ANS|DA|SA)\b", " ".join(parts)):
            continue
        pattern = re.compile(r"\b" + re.escape(parts[0]) + r"\b(?:\s+\w+\.?){0,2}\s+" + re.escape(parts[-1]) + r"\b", re.I)
        for snapshot, soup, text in pages:
            match = pattern.search(text)
            if match and words and all(w in translit_text(text).split() for w in words[:2]):
                return snapshot, {"text_quote": match.group(0), "corroboration": f"registered {c['value'].get('role')} named on a site whose domain spells the full legal name"}
    return None


def registered_officers_on_pages(row, pages):
    """Two different registered officers named on a site whose domain spells the company name.

    One shared person can be a coincidence or a sister company. Both people, on a domain equal
    to this exact name, is specific. Firms holding a role, such as auditors, do not count."""
    officers = {}
    for c in row["claims"]:
        value = c["value"] if c["field"] == "leadership" and isinstance(c["value"], dict) else {}
        role = str(value.get("role") or "").lower()
        parts = str(value.get("name") or "").split()
        if len(parts) >= 2 and len(parts[-1]) >= 3 and any(r in role for r in ("daglig leder", "innehaver", "styrets leder", "styremedlem", "nestleder"))                 and not re.search(r"\b(?:AS|ASA|ANS|DA|SA)\b", " ".join(parts)):
            officers[(parts[0].casefold(), parts[-1].casefold())] = parts
    for snapshot, soup, text in pages:
        found = []
        for parts in officers.values():
            match = re.search(r"\b" + re.escape(parts[0]) + r"\b(?:\s+\w+\.?){0,2}\s+" + re.escape(parts[-1]) + r"\b", text, re.I)
            if match:
                found.append(match.group(0))
        if len(found) >= 2:
            return snapshot, {"text_quote": "; ".join(found[:3]), "corroboration": "two registered officers named on a domain spelling the company name"}, "name_domain_and_two_registered_officers"
    return None


def named_after_person(legal_name, person):
    """MARTIN GRAN AS with a head called Martin Gran: the name on the page repeats the domain, so it proves nothing.
    Anyone with that name would pass, such as an arbitrator in California at martingran.com."""
    from .names import name_tokens
    company = set(name_tokens(legal_name))
    return bool(company) and company <= set(name_tokens(person))


def corroborated(body, pages, row=None, domain_named=False):
    from .names import matched_name_span, text_contains_name
    legal = body.get("navn", "")
    if pages and not domain_named:
        primary = pages[0][1]
        publisher_labels = [n.get_text(' ', strip=True) for n in primary.select('title, h1')]
        publisher_labels += [n.get('content', '') for n in primary.select('meta[property="og:site_name"]')]
        if any(publisher_labels) and not any(text_contains_name(label, legal) for label in publisher_labels):
            # A subsidiary/acquisition mention plus a shared address or contact
            # cannot turn the parent's whole website into the requested company.
            return None
    if row is not None and domain_named is True:
        # domain_named=True only when the domain spells the complete legal name (see crawl_site).
        found = operating_leader_on_pages(row, pages, legal)
        if found and not named_after_person(legal, found[1].get("text_quote", "")):
            return found[0], found[1], "full_name_domain_and_registered_operating_head"
    # A shared director, partial-name domain or registry URL alone is a candidate, not proof.
    legal_flat = translit_text(legal)
    phone = re.sub(r"\D", "", str(body.get("telefon") or body.get("mobil") or ""))[-8:]
    address = body.get("forretningsadresse") or {}
    postcode = str(address.get("postnummer", ""))
    streets = [translit_text(x) for x in address.get("adresse", []) if not str(x).lower().startswith("c/o")]
    for snapshot, soup, text in pages:
        actual_name = matched_name_span(text, legal)
        if not legal_flat or actual_name is None:
            continue
        flat = " " + translit_text(text) + " "
        tokens = re.findall(r"(?<!\w)(?:\+47[ .-]*|0047[ .-]*)?(?:\d[ .-]*){8}(?!\w)", text)
        for a in soup.select('a[href^="tel:"]'):
            tokens.append(a.get("href", "")[4:])
        matched_phone = next((v for v in tokens if re.sub(r"\D", "", v).removeprefix("0047").removeprefix("47") == phone or re.sub(r"\D", "", v) == phone), None)
        if len(phone) == 8 and matched_phone:
            return snapshot, {"text_quote": actual_name, "registered_legal_name": legal, "phone_quote": matched_phone, "corroboration": "full legal name + bounded registered phone"}, "legal_name_and_registered_phone"
        if postcode and " " + postcode + " " in flat and any(len(s) >= 5 and " " + s + " " in flat for s in streets):
            return snapshot, {"text_quote": actual_name, "registered_legal_name": legal, "corroboration": "exact legal name + registered street and postcode"}, "legal_name_and_registered_address"
    return None


def site_fail(row, state, message=None):
    for field in SITE_FIELDS:
        if row["availability"].get(field) != "available":
            row["availability"][field] = state
    if message:
        row["errors"].append({"module": "website", "message": message})


def fetch_robots(row, base, host, transport):
    for attempt in range(2):
        robot_snap = transport.get(urllib.parse.urljoin(base, "robots.txt"), "company_owned")
        attach(row, robot_snap)
        if (attempt or robot_snap.get('status') not in {0,429,500,502,503,504}
                or robot_snap.get('budget_exhausted') or time.monotonic() >= getattr(transport,'deadline',float('inf'))-2):
            break
        delay = 1.0 if robot_snap.get('status') == 429 else 0.0
        if robot_snap.get('retry_after'):
            try:
                delay=max(delay,float(robot_snap['retry_after']))
            except ValueError:
                try:delay=max(delay,parsedate_to_datetime(robot_snap['retry_after']).timestamp()-time.time())
                except (ValueError,TypeError,OverflowError):break
        if delay > 5 or time.monotonic()+delay >= getattr(transport,'deadline',float('inf'))-2:
            break
        if delay:time.sleep(delay)
    robot = urllib.robotparser.RobotFileParser()
    code = robot_snap["status"]
    if code == 429:
        return None, 'blocked'
    if code == 200:
        robot.parse(robot_snap["text"].splitlines())
        crawl_delay = robot.crawl_delay(UA) or robot.crawl_delay("*") or 0
        request_rate = robot.request_rate(UA) or robot.request_rate("*")
        gap = max(.35, crawl_delay, request_rate.seconds / request_rate.requests if request_rate else 0)
        with transport.lock:
            transport.host_delays[host] = max(transport.host_delays.get(host, 0), gap)
        return robot, None
    if 400 <= code < 500:
        # RFC 9309: an unavailable (4xx) robots.txt places no restriction.
        robot.parse([])
        return robot, None
    return None, availability(robot_snap)


SELF_DECLARED_ORIGINS = {"registry", "registry_email", "nav_employer", "previous"}


def alternate_addresses(url, origin=None):
    """The same host's other usual addresses, tried only after a connection or certificate failure.

    Plain HTTP is only for a domain the company itself declared. Unencrypted guessed domains are
    mostly parked or compromised: two served malware-flagged scripts in testing, and none proved."""
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not host:
        return []
    other = host[4:] if host.startswith("www.") else "www." + host
    rest = (parts.path, parts.query, "")
    addresses = [urllib.parse.urlunsplit(("https", other, *rest))]
    if origin in SELF_DECLARED_ORIGINS:
        addresses.append(urllib.parse.urlunsplit(("http", host, *rest)))
    return addresses


OFFICE_LIST_PATH = re.compile(r"locations?|offices?|kontorer|lokasjoner|avdelinger|where-we-are|find-us|worldwide|global", re.I)


def international_office_listing(page_url, site_url):
    """A foreign-domain page listing offices shows a group's reach, not this entity's own website."""
    host = (urllib.parse.urlsplit(site_url).hostname or "").lower()
    if host.endswith(".no"):
        return False
    return bool(OFFICE_LIST_PATH.search(urllib.parse.urlsplit(page_url).path))


PARKED_PAGE = re.compile(r"is registered,? but|owner currently does not have|domain (?:name )?(?:is )?(?:for sale|parked)|buy this domain|this domain (?:is|may be)|"
                         r"domenet (?:er )?(?:registrert|parkert|til salgs)|account (?:has been )?suspended|under construction|kommer snart|coming soon|available soon|has expired|ingen nettside|hosted by one\.com|default web page", re.I)


AD_LANDER = re.compile(r"[?&](?:amp;)?dn=[a-z0-9.-]+\.[a-z]{2,}&(?:amp;)?pid=|has been informing visitors about topics|most relevant links on all topics related to", re.I)


BOILERPLATE_DESCRIPTION = re.compile(r"create-react-app|created using|just another wordpress|powered by|default description", re.I)


def page_names_company(legal_name, pages, labels):
    """A declared domain with a hosting provider's default page on it has no company content."""
    from .names import name_tokens
    flat = translit_text(" ".join([*labels, *(visible for _, _, visible in pages)]))
    # "Håndverker 1" on the page names HÅNDVERKER1 AS.
    return any(len(token) >= 3 and re.search(r"(?<![a-z0-9])" + re.sub(r"(?<=[a-z])(?=\d)", " ?", re.escape(token)), flat) for token in name_tokens(legal_name))


def parked_page(text, html=""):
    """A short holding page or a domain reseller's ad page says a domain exists, not that a company publishes anything there."""
    return (len(text) < 2000 and bool(PARKED_PAGE.search(text))) or (len(text) < 5000 and bool(AD_LANDER.search(html)))


def website_cut_short(row):
    """The website stage's time share ran out before this company's research could finish."""
    if row["availability"].get("official_website") == "available":
        return False
    errors = [e for e in row["errors"] if e.get("module") == "website"]
    return any("budget" in e.get("message", "").lower() for e in errors) or (
        row["availability"].get("official_website") == "failed" and not (row.get("website_research") or {}).get("candidates"))


def note_timed_out_candidate(row, url, origin, errors_before):
    """Remember a candidate lost to a timeout. A slow moment says nothing about the company."""
    if not any("timed out" in str(e.get("message")) for e in row["errors"][errors_before:]):
        return
    pending = row.setdefault("website_research", {"candidates": []}).setdefault("timed_out", [])
    if not any(item["url"] == url for item in pending):
        pending.append({"url": url, "origin": origin})


def retry_timed_out_candidates(row, body, transport, page_limit):
    """One late attempt at each timed-out candidate, on its original address only."""
    research = row.get("website_research") or {}
    for item in list(research.get("timed_out", [])):
        if time.monotonic() >= getattr(transport, "deadline", float("inf")) or getattr(transport, "requests", 0) >= getattr(transport, "limit", float("inf")):
            return False
        before = dict(row["availability"])
        errors = list(row["errors"])
        if crawl_site(row, body, transport, page_limit, origin=item["origin"], url=item["url"], _address_fallback=True):
            research["retry_recovered"] = item["url"]
            return True
        for field in SITE_FIELDS:
            row["availability"][field] = before.get(field, "not_available")
        row["errors"] = errors
    return False


def declared_domain_legal_statement(org, legal_name, pages):
    """The site's own legal page states this exact legal name directly followed by this exact number.

    Shared sites name several companies, so `numbers == {org}` cannot hold there. Only for a domain
    the company itself declared in the register: a parent's site listing subsidiaries stays unproven."""
    from .names import matched_name_span
    for snapshot, soup, text in pages[1:]:
        if not re.search(r"personvern|privacy|vilkar|vilk%c3%a5r|terms|kontakt|contact|om-oss|about|gdpr|cookie", snapshot["source_url"].lower()):
            continue
        name = matched_name_span(text, legal_name)
        numbers = set(labelled_numbers(text))
        if not name or org not in numbers or len(numbers) > 3:
            continue
        match = re.search(re.escape(name) + r"(?:\s+(?:AS|ASA|SA|DA|ANS|NUF|KS|BA))?[\s,;:()\-–]{0,6}" + ORG_LABEL + r"\s*[:.#-]?\s*(?:NO\s*)?((?:\d[\s.]*){9})(?!\d)", text, re.I)
        if match and re.sub(r"\D", "", match.group(1)) == org:
            return snapshot, {"text_quote": match.group(0), "page_role": "legal_statement"}, "legal_name_adjacent_organisation_number"
    return None


SITEMAP_ARTICLE = re.compile(r"/(?:news|nyheter|nyhet|nytt|aktuelt|presse|press|blogg?|blogs|artikler?|articles?|innlegg)/.+|/20\d\d/\d{1,2}/.+", re.I)
SITEMAP_CAREERS = re.compile(r"^/(?:[a-z]{2}/)?(?:karriere|careers?|jobb-hos-oss|jobbe-hos-oss|ledige-stillinger|ledig-stilling|stillinger|jobs?)/?$", re.I)
SITEMAP_IDENTITY = re.compile(r"kontakt|contact|om-oss|omoss|about|personvern|privacy|vilkar|impressum|salgsbetingelser", re.I)
SITEMAP_PEOPLE = re.compile(r"team|ansatte|people|medarbeidere|hvem-er-vi|bedriften|selskapet|firmaet|historie|ledelse", re.I)


def parse_sitemap(text):
    """(page entries, child sitemap URLs). A sitemap only points to pages; it proves nothing itself."""
    import xml.etree.ElementTree as ET
    if re.search(r"<!DOCTYPE|<!ENTITY", text[:4000], re.I):
        return [], []
    try:
        root = ET.fromstring(text)
    except (ET.ParseError, ValueError):
        return [], []
    pages, children = [], []
    for node in root:
        kind = node.tag.rsplit("}", 1)[-1]
        fields = {child.tag.rsplit("}", 1)[-1]: (child.text or "").strip() for child in node}
        if kind == "sitemap" and fields.get("loc"):
            children.append(fields["loc"])
        elif kind == "url" and fields.get("loc"):
            pages.append((fields["loc"], fields.get("lastmod", "")))
    return pages, children


def site_sitemap(row, base, robot, transport, site_host, max_files=4):
    """Bounded read of a site's own sitemap: declared files first, then the usual addresses."""
    from .names import registrable
    declared = list(robot.site_maps() or []) if robot else []
    queue = declared[:3] or [urllib.parse.urljoin(base, "sitemap.xml"), urllib.parse.urljoin(base, "wp-sitemap.xml")]
    pages, seen, fetched = {}, set(), 0
    while queue and fetched < max_files:
        target = queue.pop(0)
        if target in seen or target.endswith(".gz") or registrable(urllib.parse.urlsplit(target).hostname) != registrable(site_host):
            continue
        seen.add(target)
        fetched += 1
        snap = transport.get(target, "company_owned")
        attach(row, snap)
        if availability(snap) != "available":
            continue
        found, children = parse_sitemap(snap["text"])
        for page_url, lastmod in found[:5000]:
            if registrable(urllib.parse.urlsplit(page_url).hostname) == registrable(site_host):
                pages.setdefault(page_url.split("#")[0], lastmod)
        queue.extend(sorted(children, key=lambda u: 0 if re.search(r"post|news|nyhet|artik|blog|page", u, re.I) else 1))
        if pages and not declared:
            queue = [u for u in queue if not u.endswith("wp-sitemap.xml")]
    return pages


def crawl_site(row, body, transport, page_limit=4, origin="registry", url=None, _address_fallback=False):
    """Verify one candidate site; on proof publish website and site-derived facts. Returns True when verified."""
    from .names import is_aggregator, registrable, domain_covers_name, domain_matches_name, text_contains_name, domain_is_full_name, domain_spells_name, NO_GUESS_FORMS, national_mismatch
    raw_url = url or body.get("hjemmeside")
    for field in SITE_FIELDS:
        row["availability"].setdefault(field, "not_available")
    if not raw_url:
        return False
    url = raw_url if re.match(r"^https?://", raw_url, re.I) else "https://" + raw_url.strip()
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or "").lower()
    if any(host == h or host.endswith("." + h) for h in RESTRICTED):
        site_fail(row, "blocked", "Restricted platform is not enabled as a collection source")
        return False
    if is_aggregator(url):
        site_fail(row, "ambiguous", f"Candidate {host} is a directory/platform, not a company-owned site")
        return False
    base = urllib.parse.urlunsplit((p.scheme, p.netloc, "/", "", ""))
    discovered_page = None
    if origin == "search" and (p.path not in {"", "/"} or p.query):
        # A search hit identifies a document, not its publisher. Prove the site's
        # owner at its root/contact pages before using the discovered document.
        # Otherwise a directory's customer number becomes the site's identity.
        discovered_page, url = url, base
    errors_before = len(row["errors"])
    robot, state = fetch_robots(row, base, host, transport)
    if robot is None:
        if state == "failed" and not _address_fallback:
            # The address failed, not the identity check. Certificate valid only for
            # the www host and HTTP-only hosting are common on small company sites.
            # Certificate checks stay on, and each address must pass the same proof.
            for alternate in alternate_addresses(url, origin):
                if crawl_site(row, body, transport, page_limit, origin=origin, url=alternate, _address_fallback=True):
                    return True
            note_timed_out_candidate(row, raw_url, origin, errors_before)
        site_fail(row, state)
        return False
    if not robot.can_fetch(UA, url):
        site_fail(row, "blocked", f"robots.txt disallows {host}")
        return False
    home = transport.get(url, "company_owned")
    attach(row, home)
    if availability(home) != "available":
        if home.get("status") == 0 and not _address_fallback:
            for alternate in alternate_addresses(url, origin):
                if crawl_site(row, body, transport, page_limit, origin=origin, url=alternate, _address_fallback=True):
                    return True
            note_timed_out_candidate(row, raw_url, origin, errors_before)
        site_fail(row, availability(home))
        return False
    final_host = (urllib.parse.urlsplit(home["source_url"]).hostname or "").lower()
    if registrable(final_host) != registrable(host):
        # A redirect to another registrable domain is a new, untrusted candidate.
        if is_aggregator(home["source_url"]):
            site_fail(row, "ambiguous", f"{host} redirects to a directory/platform")
            return False
        origin = "redirect"
    soup, text = soup_text(home["text"])
    if parked_page(text, home["text"]):
        site_fail(row, "not_available", f"{final_host}: holding page, no company content")
        return False
    legal_name = body.get('navn','')
    publisher_labels = [n.get_text(' ',strip=True) for n in soup.select('title,h1')]
    publisher_labels += [n.get('content','') for n in soup.select('meta[property="og:site_name"]')]
    if (origin == 'registry' and page_limit >= 3 and not domain_is_full_name(home['source_url'],legal_name)
            and not any(text_contains_name(label,legal_name) for label in publisher_labels)):
        # A registered URL can become a group portal. Follow an explicitly linked
        # complete-name domain, then independently prove that target's identity.
        for link in soup.find_all('a',href=True):
            target=urllib.parse.urljoin(home['source_url'],link['href'])
            if registrable(urllib.parse.urlsplit(target).hostname)==registrable(final_host) or not domain_is_full_name(target,legal_name):
                continue
            row.setdefault('website_research',{}).setdefault('registered_hub_candidates',[]).append({'source_url':home['source_url'],'candidate':target})
            if crawl_site(row,body,transport,page_limit-1,origin='registered_hub_link',url=target):
                return True
            site_fail(row,'ambiguous','Registered group portal links a specific company site, but its identity remains unverified')
            return False
    pages = [(home, soup, text)]
    links, extra = [], []
    feed = soup.find("link", attrs={"type": re.compile("rss|atom", re.I), "href": True})
    for a in soup.find_all("a", href=True):
        target = urllib.parse.urljoin(home["source_url"], a["href"]).split("#")[0]
        target_p = urllib.parse.urlsplit(target)
        if registrable(target_p.hostname) != registrable(final_host) or target_p.scheme not in {"http", "https"} or target == home["source_url"]:
            continue
        label = (target_p.path + " " + a.get_text(" ")).lower()
        if any(t in label for t in CONTACT_TERMS) and target not in links:
            links.append(target)
        elif any(t in label for t in MORE_TERMS) and target not in extra:
            extra.append(target)
    links.sort(key=lambda x: 0 if any(t in x.lower() for t in ("kontakt", "contact")) else 1 if any(t in x.lower() for t in ("om-oss", "about", "omoss")) else 2)

    def fetch(target):
        if not robot.can_fetch(UA, target):
            return
        snap = transport.get(target, "company_owned")
        attach(row, snap)
        if availability(snap) == "available" and registrable(urllib.parse.urlsplit(snap["source_url"]).hostname) == registrable(final_host) and "html" in snap.get("content_type", "html"):
            parsed, visible = soup_text(snap["text"])
            pages.append((snap, parsed, visible))
            return pages[-1]

    budget = max(1, page_limit - 1)
    initial_contacts = links[:min(2, budget)]
    for target in initial_contacts:
        fetch(target)
    used_contacts = len(initial_contacts)
    legal = body.get("navn", "")
    org = row["organisation_number"]
    proof = proof_on_pages(org, legal, pages)
    conflict = conflicting_number(org, pages)
    form = ((body.get("organisasjonsform") or {}).get("kode") or "").upper()
    # Housing associations and similar entities usually list a property manager's site and phone:
    # only an exact organisation-number proof is accepted for them.
    managed = form in NO_GUESS_FORMS or national_mismatch(home["source_url"], legal)
    if not proof and not conflict and not managed:
        proof = corroborated(body, pages, row, domain_is_full_name(home["source_url"], legal))
    if not proof and not conflict and not managed and origin == "registry":
        # The company's own Enhetsregisteret homepage declaration, with the complete core name on the domain or page.
        # The domain itself must carry the name: a declared parent/group domain (e.g. a brand page on the
        # international parent's site) is not the Norwegian entity's own website.
        if (domain_is_full_name(home["source_url"], legal) and page_names_company(legal, pages, publisher_labels)) or (
                domain_matches_name(home["source_url"], legal) and any(text_contains_name(t, legal) for _, _, t in pages)):
            proof = home, {"declared_by": "Enhetsregisteret hjemmeside", "declared_value": raw_url,
                           "name_check": "complete core legal name in domain or page text"}, "registry_declared_homepage"
    # Some companies put their legal identifier only in a privacy/legal page.
    # Spend bounded extra identity work only when the first contact pages fail.
    while not proof and not conflict and used_contacts < min(len(links), budget, 4):
        fetch(links[used_contacts])
        used_contacts += 1
        proof = proof_on_pages(org, legal, pages)
        conflict = conflicting_number(org, pages)
        if not proof and not conflict and not managed:
            proof = corroborated(body, pages, row, domain_is_full_name(home['source_url'], legal))
    if not proof and not conflict and not managed and origin in {"registry", "registry_email"}:
        proof = declared_domain_legal_statement(org, legal, pages)
    sitemap_pages = None
    named_domain = domain_is_full_name(home["source_url"], legal)
    spelled_domain = named_domain or domain_spells_name(home["source_url"], legal)
    if not proof and not conflict and not managed and spelled_domain:
        proof = registered_officers_on_pages(row, pages)
    if (not proof and not conflict and page_limit >= 5 and (spelled_domain or domain_matches_name(home["source_url"], legal)
                                                            or any(text_contains_name(t, legal) for _, _, t in pages))):
        # The linked pages did not settle identity. The site's own map often lists its legal and
        # about pages, and a site named after the company may name its head on a page of its menu.
        sitemap_pages = site_sitemap(row, base, robot, transport, final_host)
        opened = {s["source_url"].rstrip("/") for s, _, _ in pages}
        listed = sorted(sitemap_pages, key=lambda u: (0 if SITEMAP_IDENTITY.search(urllib.parse.urlsplit(u).path) else 1, len(u)))
        further = [u for u in listed if SITEMAP_IDENTITY.search(urllib.parse.urlsplit(u).path)
                   or SITEMAP_PEOPLE.search(urllib.parse.urlsplit(u).path)]
        if spelled_domain:
            menu = [urllib.parse.urljoin(home["source_url"], a["href"]).split("#")[0] for nav in soup.select("nav, header") for a in nav.find_all("a", href=True)]
            further += [u for u in dict.fromkeys(menu) if registrable(urllib.parse.urlsplit(u).hostname) == registrable(final_host)
                        and u.rstrip("/") != home["source_url"].rstrip("/") and not re.search(r"\.(?:pdf|png|jpe?g|svg|zip)$|/(?:cart|checkout|login|logg-inn|handlekurv|account|konto|min-side)/?$", u, re.I)]
        tried = 0
        for target in dict.fromkeys(further):
            if tried >= 3 or proof or conflict:
                break
            if target.rstrip("/") in opened:
                continue
            opened.add(target.rstrip("/"))
            tried += 1
            fetch(target)
            proof = proof_on_pages(org, legal, pages)
            conflict = conflicting_number(org, pages)
            if not proof and not conflict and not managed:
                proof = corroborated(body, pages, row, named_domain)
            if not proof and not conflict and not managed and spelled_domain:
                proof = registered_officers_on_pages(row, pages)
            if not proof and not conflict and not managed and origin in {"registry", "registry_email"}:
                proof = declared_domain_legal_statement(org, legal, pages)
    declared = origin == "registry" and not managed
    if not proof and not conflict and declared and domain_covers_name(home["source_url"], legal) and page_names_company(legal, pages, publisher_labels):
        # The company declared this address against its exact organisation number, and the domain carries its name.
        proof = home, {"declared_by": "Enhetsregisteret hjemmeside", "declared_value": raw_url,
                       "name_check": "at least two words of the legal name in the domain"}, "registry_declared_homepage"
    if not proof:
        site_fail(row, "ambiguous", f"{final_host}: " + ("site shows a different organisation number" if conflict else "no exact organisation-number proof on company pages"))
        return False
    proof_snap, proof_locator, method = proof
    if method in {"legal_name_and_registered_phone", "legal_name_and_registered_address"}:
        if international_office_listing(proof_snap["source_url"], home["source_url"]):
            site_fail(row, "ambiguous", f"{final_host}: registered details appear only on an international office listing (possible group site)")
            return False
    weak = method in {"legal_name_and_registered_phone", "legal_name_and_registered_address"} or (
        isinstance(proof_locator, dict) and proof_locator.get("page_role") == "contact_or_about")
    # A company's own declaration answers the parent-group question that these two guards ask of an undeclared domain.
    if weak and not declared and not domain_matches_name(home["source_url"], legal):
        # Weaker proofs on a domain that does not carry the company's name usually mean a parent-group or
        # portfolio site listing this entity: publishing its social accounts, news or jobs would be wrong.
        site_fail(row, "ambiguous", f"{final_host}: identity shown only on a page of a differently named domain (possible parent/group site)")
        return False
    if weak and not declared and not domain_is_full_name(home["source_url"], legal) and not any(text_contains_name(label, legal) for label in publisher_labels):
        # A shared brand word is not publisher scope: "Fjordbakst Group" listing "Fjordbakst Vest AS"
        # on its contact page is the group's site. The homepage itself must name this company.
        site_fail(row, "ambiguous", f"{final_host}: homepage names a different publisher than {legal} (possible parent/group site)")
        return False
    for field in SITE_FIELDS:
        if row["availability"].get(field) != "available":
            row["availability"][field] = "not_available"
    claim(row, "official_website", home["source_url"], proof_snap, proof_locator, identity_method=method)
    row["availability"]["official_website"] = "available"
    row.setdefault("website_research", {})["verification"] = {"url": home["source_url"], "method": method, "origin": origin}
    remaining_links = ([discovered_page] if discovered_page and discovered_page != home["source_url"] else []) + links[used_contacts:] + extra
    remaining_links.sort(key=lambda u: 0 if u == discovered_page else 1 if any(t in u.lower() for t in ('news','nyhet','aktuelt','presse','blog','/articles','/artikler')) else 2 if any(t in u.lower() for t in MORE_TERMS) else 3)
    # Follow a bounded second hop from an explicit news index. A larger first-hop
    # crawl otherwise fills its budget with static pages while missing every post.
    queue = [(u, None) for u in remaining_links]
    visited = {s['source_url'].rstrip('/') for s, _, _ in pages}
    article_slots = 2
    for _ in range(max(0, budget - used_contacts)):
        while queue and queue[0][0].rstrip('/') in visited:
            queue.pop(0)
        if not queue:
            break
        target, context = queue.pop(0)
        visited.add(target.rstrip('/'))
        fetched = fetch(target)
        if not fetched:
            continue
        if context:
            fetched[0]['news_context'] = context
            # attach() has already retained this same observation; preserve the
            # link provenance without changing its bytes or retrieval timestamp.
            for stored in row['source_snapshots']:
                if stored['id'] == fetched[0]['id']:
                    stored['news_context'] = context
        if article_slots:
            additions = news_index_links(fetched[0], fetched[1], home['source_url'])
            additions = [(u, {'index_url': fetched[0]['source_url'], 'link_label': label})
                         for u, label in additions if u.rstrip('/') not in visited][:article_slots]
            article_slots -= len(additions)
            queue[0:0] = additions
    if sitemap_pages is None:
        sitemap_pages = site_sitemap(row, base, robot, transport, final_host) if page_limit >= 5 else {}
    articles = sorted(((u, m) for u, m in sitemap_pages.items() if SITEMAP_ARTICLE.search(urllib.parse.urlsplit(u).path)
                       and not urllib.parse.urlsplit(u).query and not re.search(r"\.(?:pdf|png|jpe?g|svg|zip)$", u, re.I)),
                      key=lambda entry: entry[1] or "", reverse=True)
    opened = {s["source_url"].rstrip("/") for s, _, _ in pages}
    taken = 0
    for article_url, _ in articles:
        if taken >= 6:
            break
        if article_url.rstrip("/") in opened or not robot.can_fetch(UA, article_url):
            continue
        taken += 1
        fetched = fetch(article_url)
        if fetched:
            context = {"index_url": "sitemap", "link_label": "listed in the site's sitemap", "via": "sitemap"}
            fetched[0]["news_context"] = context
            for stored in row["source_snapshots"]:
                if stored["id"] == fetched[0]["id"]:
                    stored["news_context"] = context
    sitemap_careers = next((u for u in sitemap_pages if SITEMAP_CAREERS.search(urllib.parse.urlsplit(u).path)), None)
    careers_page = fetch(sitemap_careers) if sitemap_careers and sitemap_careers.rstrip("/") not in opened else None
    if feed is not None and robot.can_fetch(UA, urllib.parse.urljoin(home["source_url"], feed["href"])):
        feed_url = urllib.parse.urljoin(home["source_url"], feed["href"])
        if registrable(urllib.parse.urlsplit(feed_url).hostname) == registrable(final_host) and "comments" not in feed_url:
            feed_snap = transport.get(feed_url, "company_owned")
            attach(row, feed_snap)
            if availability(feed_snap) == "available":
                extract_feed(row, feed_snap, body, site_url=home["source_url"])
    elif feed is None and "wp-content" in home["text"]:
        # WordPress serves a dated post feed at /feed/ even when the theme does not link it.
        feed_url = urllib.parse.urljoin(urllib.parse.urlunsplit(urllib.parse.urlsplit(home["source_url"])[:2] + ("/", "", "")), "feed/")
        if robot.can_fetch(UA, feed_url):
            feed_snap = transport.get(feed_url, "company_owned")
            attach(row, feed_snap)
            if availability(feed_snap) == "available" and "<rss" in feed_snap["text"][:2000].lower():
                extract_feed(row, feed_snap, body, site_url=home["source_url"])
    extract_site_facts(row, body, pages, method, getattr(transport, "quote_selector", None), transport)
    if careers_page and not any(c["field"] == "careers_page" for c in row["claims"]):
        claim(row, "careers_page", careers_page[0]["source_url"], careers_page[0], {"sitemap_loc": sitemap_careers}, identity_method="sitemap_of_verified_company_site")
    return True


NEWS_MAX_AGE_DAYS = 3 * 366
# Each dated item is a separately scored fact, and a feed or news page is already fetched, so more items cost no requests.
NEWS_ITEMS_PER_SOURCE = 20
# A complete 45-day NAV index took 81 pages on 4 November 2026; leave headroom for busy weeks.
NAV_FEED_PAGE_CAP = 600


def news_date(raw):
    """ISO date for a published news item, or None when unusable (unparseable, future or older than three years)."""
    text = str(raw or "")
    match = re.match(r"(\d{4}-\d{2}-\d{2})", text)
    when = parsed_date(match.group(1) if match else text)
    today = datetime.now(timezone.utc)
    if when.year < 2000 or when.date() > today.date() or (today - when).days > NEWS_MAX_AGE_DAYS:
        return None
    return when.date().isoformat()


STATIC_PAGE = re.compile(r"om[- ]?oss|about|privacy|personvern|cookie|vilk[aå]r|terms|salgsbetingelser|kj[oø]psbetingelser|career|karriere|"
                         r"ledige[- /]stillinger|kontakt|contact|forside|home|kategori|category|/tag/|/shop|/produkt|/product")
# Broadcasting, newspaper/periodical publishing and news agencies: their articles are editorial output, not news about the company.
MEDIA_INDUSTRY = re.compile(r"^(?:58\.1[34]|60\.|63\.9)")


def news_url_ok(url, site_url):
    """One acceptance rule for every news path: an individual article URL on the verified site, never a static page."""
    from .names import registrable
    parts = urllib.parse.urlsplit(str(url or ""))
    if parts.scheme not in {"http", "https"} or registrable(parts.hostname) != registrable(urllib.parse.urlsplit(site_url).hostname):
        return False
    path = parts.path.rstrip("/").lower()
    if not path or re.search(r"/(?:feed|rss|atom)(?:\.xml)?$", path):
        return False
    if re.fullmatch(r"(?:contact|kontakt|privacy(?:-policy)?|personvern(?:erklaering)?|terms(?:-and-conditions)?|om-oss|about|shop|products?)", path.rsplit("/", 1)[-1]):
        return False
    if re.search(r"/(?:news|nyheter|nyhet|nytt|aktuelt|presse|press|blogg?|artikler?|articles?|innlegg)/[^/]+|/20\d\d/\d{1,2}/[^/]+", path):
        return True  # inside a news section or a dated permalink
    if re.search(r"/(?:news|nyheter|nyhet|aktuelt|presse|press|blogg?|artikler?|innlegg|arkiv|archive)$", path):
        return False  # the section index lists posts; it is not one
    return not any(STATIC_PAGE.match(segment) for segment in path.split("/") if segment)


def news_about_company(body, title, summary=""):
    """Media companies publish stories about others; keep only their items that name the company itself."""
    from .names import name_tokens, distinctive
    if re.search(r'^(?:how\s+to\b|how\s+can\b|tips\b|slik\b|guide\b|\d+\s+.*\b(?:tips|traits|ways|steps)\b)', title.strip(), re.I):
        return False
    if re.search(r'\b(?:vedtekter|husordens?regler|årsplan|åpningstider|prisliste)\b', title, re.I):
        return False
    code = str(((body or {}).get("naeringskode1") or {}).get("kode") or "")
    if not MEDIA_INDUSTRY.match(code):
        return True
    words = distinctive(name_tokens((body or {}).get("navn", ""))) or name_tokens((body or {}).get("navn", ""))
    text = translit_text(title + " " + summary)
    return bool(words) and all(w in text for w in words)


NEWS_INDEX = re.compile(r'/(?:news|nyheter|nytt|aktuelt|blogg?|presse|press|articles?|artikler?)/?$', re.I)


def news_index_links(snap, parsed, site_url):
    """Literal article-card URLs on an explicit news index; never external publishers."""
    if not NEWS_INDEX.search(urllib.parse.urlsplit(snap['source_url']).path):
        return []
    found = {}
    for link in parsed.find_all('a', href=True):
        if link.find_parent(['nav', 'header', 'footer', 'aside']):
            continue
        label = link.get_text(' ', strip=True)
        url = urllib.parse.urljoin(snap['source_url'], link['href']).split('#')[0]
        parts = urllib.parse.urlsplit(url)
        if (parts.scheme not in {'https', 'http'} or parts.query
                or parts.hostname != urllib.parse.urlsplit(site_url).hostname
                or not parts.path.rstrip('/') or NEWS_INDEX.search(parts.path)
                or STATIC_PAGE.search(parts.path) or re.search(r'\.(?:pdf|png|jpe?g|svg|zip)$', parts.path, re.I)
                or not 20 <= len(label) <= 300 or len(label.split()) < 3):
            continue
        found.setdefault(url, label)
    return sorted(found.items(), key=lambda pair: 0 if re.search(r'press release|pressemelding', pair[1], re.I) else 1)


def literal_dateline(text):
    """Only a leading dateline, not an event date buried in prose."""
    months = {w: i for i, words in enumerate([
        'januar january jan', 'februar february feb', 'mars march mar', 'april apr', 'mai may',
        'juni june jun', 'juli july jul', 'august aug', 'september sept sep', 'oktober october okt oct',
        'november nov', 'desember december des dec'], 1) for w in words.split()}
    raw = re.sub(r'^(?:published|publisert)\s*:?\s*', '', text.strip(), flags=re.I)
    match = re.fullmatch(r'(\d{4}-\d{2}-\d{2}|\d{1,2}\.\d{1,2}\.\d{4}|\d{1,2}(?:st|nd|rd|th)?\.?\s+(?:of\s+)?(?:'
                         + '|'.join(sorted(months, key=len, reverse=True)) + r')\.?\s+\d{4})(?:\s*,\s*[^\d]{1,80})?', raw, re.I)
    if not match:
        return None
    quote = match[1]
    try:
        cleaned = re.sub(r'(?<=\d)(?:st|nd|rd|th)\b|\bof\s+', '', quote, flags=re.I).replace('.', '')
        if re.search(r'[a-z]', cleaned, re.I):
            day, month, year = cleaned.lower().split()
            parsed = datetime(int(year), months[month], int(day)).date()
        else:
            parsed = datetime.strptime(quote, '%Y-%m-%d' if '-' in quote else '%d.%m.%Y').date()
    except (ValueError, KeyError):
        return None
    iso = news_date(parsed.isoformat())
    return (iso, quote) if iso else None


def linked_news_subject(body, headline, summary=''):
    """A publisher suffix or an instructional blog post is not company news."""
    from .names import text_contains_name
    legal = body.get('navn', '')
    title = headline.strip()
    for separator in (' | ', ' — ', ' – ', ' - '):
        pieces = title.rsplit(separator, 1)
        if len(pieces) == 2 and text_contains_name(pieces[1], legal):
            title = pieces[0]
    if re.search(r'^(?:how\s+to\b|how\s+can\b|tips\b|slik\b|guide\b|\d+\s+.*\b(?:tips|traits|ways|steps)\b)', title, re.I):
        return False
    if text_contains_name(title, legal):
        return True
    event = re.search(r'\b(?:launch\w*|open\w*|appoint\w*|becomes?|new|partnership\w*|partner\w*|sign\w*|join\w*|acquir\w*|invest\w*|award\w*|fund\w*|expan\w*|secur\w*|lanser\w*|åpn\w*|ansatt\w*|samarbeid\w*|etabler\w*|overtar|tildel\w*|vinner|ansett\w*)\b', title, re.I)
    return bool(event and (text_contains_name(summary, legal) or re.match(r'^(?:we|our|vi|vår)\b', title, re.I)))


def explicit_publish_date(parsed, heading):
    """A publication date the page itself states in markup, never a sitemap lastmod."""
    for meta in parsed.select('meta[property="article:published_time"], meta[name="article:published_time"], meta[itemprop="datePublished"]'):
        raw = str(meta.get("content") or "")
        if news_date(raw):
            return news_date(raw), raw, "meta_published_time"
    node = heading.find_next("time", attrs={"datetime": True})
    if node is not None and not node.find_parent(["nav", "footer", "aside"]) and news_date(node["datetime"]):
        return news_date(node["datetime"]), node["datetime"], "time_after_headline"
    return None


def extract_linked_article(row, snap, parsed, body, site_url):
    """A verified-site article reached from a news card or the site's sitemap, with a stated date."""
    from .names import text_contains_name
    context = snap.get('news_context')
    if not context:
        return
    via_sitemap = context.get('via') == 'sitemap'
    if not via_sitemap and not NEWS_INDEX.search(urllib.parse.urlsplit(context.get('index_url', '')).path):
        return
    if urllib.parse.urlsplit(snap['source_url']).hostname != urllib.parse.urlsplit(site_url).hostname:
        return
    if any(c['field'] == 'activity' and isinstance(c['value'], dict) and c['value'].get('url') == snap['source_url'] for c in row['claims']):
        return
    headings = [h for h in parsed.find_all('h1') if not h.find_parent(['nav', 'header', 'footer', 'aside'])]
    if len(headings) != 1:
        return
    heading = headings[0]
    title = heading.get_text(' ', strip=True)
    if STATIC_PAGE.search(urllib.parse.urlsplit(snap['source_url']).path):
        return
    following = [n for n in heading.find_all_next(['h2', 'h3', 'p', 'time'], limit=10)
                 if not n.find_parent(['nav', 'header', 'footer', 'aside'])]
    lead = ' '.join(n.get_text(' ', strip=True) for n in following[:4])
    if via_sitemap:
        # The site's own article section and a stated date are the evidence. Media companies
        # publish about others, so news_about_company still applies, as do instructional titles.
        if (not 8 <= len(title) <= 500 or len(title.split()) < 2 or not news_url_ok(snap['source_url'], site_url)
                or not news_about_company(body, title, lead)):
            return
    elif (not 20 <= len(title) <= 500 or len(title.split()) < 4 or not text_contains_name(title + ' ' + lead, body.get('navn', ''))
            or not news_about_company(body, title, lead) or not linked_news_subject(body, title, lead)):
        # Without a sitemap listing, the article itself must name this company near the headline.
        return
    found = None
    for node in following[:4]:
        date = literal_dateline(node.get_text(' ', strip=True))
        if date:
            found = (date[0], date[1], 'dateline')
            break
    found = found or explicit_publish_date(parsed, heading)
    if not found:
        return
    iso, quote, source = found
    kind = 'company_owned_sitemap_article' if via_sitemap else 'company_owned_linked_article'
    claim(row, 'activity', {'headline': title[:300], 'published_at': iso, 'published_raw': quote,
          'url': snap['source_url'], 'kind': kind}, snap,
          {'news_index_url': context['index_url'], 'link_label': context['link_label'],
           'headline_quote': title, 'date_quote': quote, 'date_source': source}, period={'published_at': iso},
          identity_method='verified_site_sitemap_and_stated_date' if via_sitemap else 'verified_site_news_link_and_literal_dateline')
    row['availability']['activity'] = 'available'


def extract_feed(row, snap, body=None, site_url=None):
    import xml.etree.ElementTree as ET
    try:
        if re.search(r'<!DOCTYPE|<!ENTITY', snap['text'], re.I):
            return
        root = ET.fromstring(snap['text'])
    except (ET.ParseError, ValueError):
        return
    count = 0
    local = lambda tag: tag.rsplit('}', 1)[-1].lower()
    for item in root.iter():
        if local(item.tag) not in {'item', 'entry'}:
            continue
        children = {local(n.tag): n for n in item}
        content = lambda key: ''.join(children[key].itertext()).strip() if key in children else ''
        title = content('title')
        date = content('pubdate') or content('published') or content('date')
        if not title or not date or len(title.split()) < 3:
            continue
        if parsed_date(date).date() > datetime.now(timezone.utc).date() or parsed_date(date).year < 2000:
            continue
        links = [n for n in item if local(n.tag) == 'link' and n.get('rel', 'alternate') == 'alternate']
        href = next((n.get('href') or (n.text or '').strip() for n in links if n.get('href') or (n.text or '').strip()), None)
        if not href:
            continue  # an item without its own article link is not a citable post
        href = urllib.parse.urljoin(snap['source_url'], href)
        if not news_url_ok(href, site_url or snap['source_url']):
            continue
        summary = re.sub(r"<[^>]+>", " ", content('description') or content('summary'))
        if not news_about_company(body, title, summary):
            continue
        iso = news_date(date)
        if not iso:
            continue
        claim(row, "activity", {"headline": title[:300], "published_at": iso, "published_raw": date, "url": href,
                                "kind": "company_owned_feed_item"}, snap, {"feed_item": count, "title": title[:120]},
              period={"published_at": date}, identity_method="verified_company_site_feed")
        row["availability"]["activity"] = "available"
        count += 1
        if count >= NEWS_ITEMS_PER_SOURCE:
            break


def extract_dated_news_cards(row, snap, parsed, body=None, site_url=None):
    """Literal dated cards on an already verified site; no inferred event dates."""
    from .names import registrable
    months = {word:month for month,words in enumerate([
        'januar january jan','februar february feb','mars march mar','april apr','mai may',
        'juni june jun','juli july jul','august aug','september sept sep','oktober october okt oct',
        'november nov','desember december des dec'],1) for word in words.split()}
    month_pattern='|'.join(sorted(months,key=len,reverse=True))
    date_pattern = re.compile(r'(?<!\d)(?:\d{4}-\d{2}-\d{2}|\d{1,2}\.\d{1,2}\.\d{4}|\d{1,2}\.?\s+(?:'+month_pattern+r')\.?\s+\d{4})(?!\d)',re.I)
    news_path = re.compile(r'/(?:news|nyheter|nyhet|aktuelt|blog|blogg|presse|press|articles?)(?:/|[-_])', re.I)
    known = {(c['value'].get('url'), parsed_date(c['value'].get('published_at')).date().isoformat())
             for c in row['claims'] if c['field']=='activity' and isinstance(c['value'],dict)}
    count=0
    for text_node in parsed.find_all(string=date_pattern):
        if text_node.find_parent(['nav','header','footer','aside','script','style']):
            continue
        match=date_pattern.search(str(text_node))
        raw_date=match.group()
        try:
            if re.search(r'[a-z]',raw_date,re.I):
                day,month,year=raw_date.replace('.','').lower().split()
                date=datetime(int(year),months[month],int(day)).date()
            else:
                date=datetime.strptime(raw_date,'%Y-%m-%d' if '-' in raw_date else '%d.%m.%Y').date()
        except ValueError:
            continue
        if date.year < 1990 or date > datetime.now(timezone.utc).date():
            continue
        for parent in list(text_node.parents)[:4]:
            if parent.name in {'main','body','html','nav','header','footer','aside'}:
                break
            if len(parent.get_text(' ',strip=True)) > 2400 or len(date_pattern.findall(parent.get_text(' ',strip=True))) != 1:
                continue
            links=[]
            for link in parent.find_all('a',href=True):
                url=urllib.parse.urljoin(snap['source_url'],link['href'])
                label=link.get_text(' ',strip=True)
                if not 12 <= len(label) <= 300 or not news_path.search(urllib.parse.urlsplit(url).path):
                    continue
                if registrable(urllib.parse.urlsplit(url).hostname) != registrable(urllib.parse.urlsplit(snap['source_url']).hostname):
                    continue
                if parent.name not in {'article','li'} and link.parent is not parent and not (link.parent.name in {'h1','h2','h3','h4'} and link.parent.parent is parent):
                    continue
                links.append((link,url,label))
            if len(links)!=1:
                continue
            link,url,label=links[0]
            if not news_url_ok(url, site_url or snap['source_url']) or not news_about_company(body, label, parent.get_text(' ',strip=True)):
                continue
            key=(url,date.isoformat())
            if key not in known and news_date(date.isoformat()):
                claim(row,'activity',{'headline':label,'published_at':date.isoformat(),'url':url,'kind':'company_owned_news_card'},snap,
                      {'link_href':link['href'],'text_quote':label,'date_quote':raw_date},period={'published_at':date.isoformat()},identity_method='verified_company_site_dated_card')
                row['availability']['activity']='available'
                known.add(key);count+=1
            break
        if count>=NEWS_ITEMS_PER_SOURCE:
            break


CREDIT_CONTEXT = re.compile(r"(?:levert|laget|utviklet|designet|design|produsert|driftet|levert)\s+(?:av|by)\b|made\s+by|developed\s+by|designed\s+by|"
                            r"powered\s+by|built\s+by|created\s+by|website\s+by|web\s*design|webbyr[aå]|nettside\s+av|hjemmeside\s+av|reklamebyr[aå]|(?:web|digital|design)\s*agency", re.I)


def vendor_credit(anchor):
    """True when a link sits in a site-credit line (agency, developer, platform) rather than the company's own links."""
    for node in [anchor, *list(anchor.parents)[:2]]:
        if node is not anchor and len(node.find_all("a")) > 1:
            break  # a shared footer or link list: one credit line must not taint the company's own links
        text = node.get_text(" ", strip=True) if hasattr(node, "get_text") else ""
        if text and len(text) <= 160 and CREDIT_CONTEXT.search(text + " " + str(anchor.get("title", "")) + " " + str(anchor.get("aria-label", ""))):
            return True
    return False


def extract_site_facts(row, body, pages, method, quote_selector=None, transport=None):
    from .names import core_name
    org = row["organisation_number"]
    home, home_soup, _ = pages[0]
    legal_core = core_name(body.get("navn", ""))
    socials, emails, phones = {}, {}, {}
    for snap, parsed, visible in pages:
        numbers = set(labelled_numbers(visible))
        if numbers and org not in numbers:
            continue  # page belongs to another legal entity
        if snap is home:
            description = None
            for selector, attr in (('meta[name="description"]', "content"), ('meta[property="og:description"]', "content")):
                node = parsed.select_one(selector)
                if node and len(node.get(attr, "").strip()) >= 20 and not BOILERPLATE_DESCRIPTION.search(node.get(attr)):
                    description = (node.get(attr).strip(), selector)
                    break
            if description:
                claim(row, "description", description[0][:1000], snap, {"css_selector": description[1], "attribute": "content"}, identity_method="verified_company_site")
                row["availability"]["description"] = "available"
            site_name = parsed.select_one('meta[property="og:site_name"]')
            if site_name and site_name.get("content", "").strip() and len(site_name["content"].strip()) <= 80:
                claim(row, "public_brand", site_name["content"].strip(), snap, {"css_selector": 'meta[property="og:site_name"]', "attribute": "content"}, identity_method="verified_company_site")
        for a in parsed.find_all("a", href=True):
            href = a["href"].strip()
            if href.lower().startswith("mailto:"):
                email = urllib.parse.unquote(href[7:].split("?")[0]).strip().lower()
                if re.fullmatch(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", email):
                    emails.setdefault(email, snap)
            elif href.lower().startswith("tel:"):
                digits = re.sub(r"[^\d+]", "", href[4:])
                if 8 <= len(digits.lstrip("+")) <= 12:
                    phones.setdefault(digits, snap)
            else:
                profile = social_profile(urllib.parse.urljoin(snap["source_url"], href))
                if profile and vendor_credit(a):
                    continue  # "website made by <agency>": the agency's account, not the company's
                if profile:
                    if profile['platform'] == 'facebook' and re.fullmatch(r'/\d+', urllib.parse.urlsplit(profile['url']).path):
                        # Bare numeric URLs can be photos as well as pages. Require
                        # an explicit profile link context; an embedded feed image
                        # alone cannot establish a company-linked profile.
                        label = ' '.join([a.get_text(' ',strip=True), str(a.get('aria-label','')), str(a.get('title',''))])
                        context = a.find_parent(['footer']) or a.find_parent(class_=re.compile(r'social|sosial',re.I))
                        if not context and not re.search(r'facebook|f[øo]lg oss|follow us',label,re.I):
                            continue
                    socials.setdefault(profile["url"].lower(), (profile, snap, {"link_href": href}))
        for node in jsonld_nodes(snap["text"]):
            types = node_types(node)
            if any(t in ("Organization", "LocalBusiness", "Corporation") for t in types):
                same_as = node.get("sameAs", [])
                for linked in [same_as] if isinstance(same_as, str) else same_as if isinstance(same_as, list) else []:
                    profile = social_profile(linked) if isinstance(linked, str) else None
                    if profile:
                        socials.setdefault(profile["url"].lower(), (profile, snap, {"jsonld": {"sameAs": linked}}))
                if snap is home and node.get("description") and row["availability"].get("description") != "available" and len(str(node["description"])) >= 20:
                    claim(row, "description", str(node["description"])[:1000], snap, {"jsonld": "Organization.description"}, identity_method="verified_company_site")
                    row["availability"]["description"] = "available"
            if "JobPosting" in types and node.get("title") and node.get("datePosted"):
                hiring = node.get("hiringOrganization") or {}
                if not isinstance(hiring, dict) or core_name(hiring.get("name", "")) != legal_core:
                    continue
                expires = node.get("validThrough")
                if expires and str(expires)[:10] < now()[:10]:
                    continue
                claim(row, "jobs", {"title": node["title"], "date_posted": node["datePosted"], "valid_through": expires,
                      "url": node.get("url", snap["source_url"]), "source": "company website JobPosting"}, snap,
                      {"jsonld": {k: node.get(k) for k in ("title", "datePosted", "validThrough")}}, identity_method="verified_site_and_exact_hiring_name")
                row["availability"]["jobs"] = "available"
            article_url = str(node.get("url") or snap["source_url"])
            static_page = STATIC_PAGE.search((urllib.parse.urlsplit(article_url).path + " " + str(node.get("headline") or "")).lower())
            if any(t in ("NewsArticle", "Article", "BlogPosting", "PressRelease") for t in types) and node.get("headline") and node.get("datePublished")                     and news_url_ok(article_url, home["source_url"]) and news_about_company(body, str(node["headline"]), str(node.get("description") or ""))                     and (not snap.get('news_context') or linked_news_subject(body, str(node['headline']), str(node.get('description') or '')))                     and (not static_page or (("NewsArticle" in types or "PressRelease" in types)
                         and re.search(r"/(?:news|nyheter|nyhet|aktuelt|presse|press|blogg?|artikler?)/", urllib.parse.urlsplit(article_url).path.lower())))                     and snap is not pages[0][0]:
                if not news_date(node["datePublished"]):
                    continue
                claim(row, "activity", {"headline": str(node["headline"])[:300], "published_at": news_date(node["datePublished"]), "published_raw": node["datePublished"], "url": article_url,
                      "kind": "company_owned_article"}, snap, {"jsonld": {k: node.get(k) for k in ("headline", "datePublished")}}, identity_method="verified_company_site")
                row["availability"]["activity"] = "available"
        url = snap["source_url"].lower()
        if snap is not home and any(t in url for t in ("news", "nyhet", "aktuelt", "blogg", "blog", "presse")):
            seen = 0
            for t in parsed.find_all("time", attrs={"datetime": True}):
                container = t.find_parent(["article", "li"]) or t.parent
                heading = container.find(["h1", "h2", "h3", "h4", "a"]) if container else None
                title = heading.get_text(" ", strip=True) if heading else ""
                if not re.match(r"\d{4}-\d{2}-\d{2}", t["datetime"]) or len(title) < 8 or len(title.split()) < 3                         or parsed_date(t["datetime"]).date() > datetime.now(timezone.utc).date():
                    continue
                link = heading.get("href") if heading and heading.name == "a" else (heading.find("a", href=True) or {}).get("href") if heading else None
                # Without a link the item can only be the page itself, which must then be an article page.
                article = urllib.parse.urljoin(snap["source_url"], link) if link else snap["source_url"]
                if not news_date(t["datetime"]) or not news_url_ok(article, home["source_url"]) or not news_about_company(body, title):
                    continue
                claim(row, "activity", {"headline": title[:300], "published_at": news_date(t["datetime"]), "published_raw": t["datetime"], "url": article,
                      "kind": "company_news_page_item"}, snap, {"css_selector": "time[datetime]", "datetime": t["datetime"], "text_quote": title[:120]}, identity_method="verified_company_site")
                row["availability"]["activity"] = "available"
                seen += 1
                if seen >= 6:
                    break
        extract_dated_news_cards(row,snap,parsed,body,home["source_url"])
        if snap is not home:
            extract_linked_article(row, snap, parsed, body, home['source_url'])
    from .names import name_tokens, translit, registrable
    site_label = translit(registrable(urllib.parse.urlsplit(home["source_url"]).hostname).split(".")[0]).replace("-", "")
    brand = next((c["value"] for c in row["claims"] if c["field"] == "public_brand" and isinstance(c["value"], str)), "")
    own_words = {t for t in name_tokens(body.get("navn", "")) + name_tokens(brand) if len(t) >= 4} | ({site_label} if len(site_label) >= 4 else set())
    own_compact = {"".join(name_tokens(body.get("navn", ""))), "".join(name_tokens(brand)), site_label} - {""}

    def belongs(profile):
        handle = re.sub(r"[^a-z0-9]", "", translit(urllib.parse.urlsplit(profile["url"]).path.rsplit("/", 1)[-1] or ""))
        if not handle:
            return False
        if "profile.php" in profile["url"] or re.fullmatch(r"[0-9]{8,}", handle):
            return True  # numeric page id published by the verified site itself
        if len(handle) >= 3 and handle in own_compact:
            return True  # exact verified brand/domain, not an ambiguous short substring
        return any(w in handle for w in own_words) or any(len(handle) >= 4 and handle in c for c in own_compact)

    socials = {k: v for k, v in socials.items() if belongs(v[0])}
    for key, (profile, snap, locator) in list(socials.items())[:10]:
        claim(row, "owned_profiles", {"platform": profile["platform"], "url": profile["url"], "relation": "linked from verified company website; profile content not fetched"},
              snap, locator, identity_method="outbound_link_on_verified_company_site")
        row["availability"]["owned_profiles"] = "available"
    careers = None
    for snap, parsed, visible in pages:
        if careers:
            break
        for a in parsed.find_all("a", href=True):
            target = urllib.parse.urljoin(snap["source_url"], a["href"]).split("#")[0]
            label = (urllib.parse.urlsplit(target).path + " " + a.get_text(" ", strip=True)).lower()
            if registrable(urllib.parse.urlsplit(target).hostname) == registrable(urllib.parse.urlsplit(home["source_url"]).hostname) \
                    and re.search(r"karriere|career|ledige[- ]stillinger|jobb[- ]hos|jobs?\b|stillinger", label):
                careers = (target, snap, a.get_text(" ", strip=True)[:120])
                break
    if careers:
        claim(row, "careers_page", careers[0], careers[1], {"link_href": careers[0], "text_quote": careers[2]}, identity_method="link_on_verified_company_site")
    for email, snap in list(emails.items())[:3]:
        claim(row, "contact", {"type": "email", "value": email}, snap, {"link_href": "mailto:" + email}, identity_method="verified_company_site")
        row["availability"]["contact"] = "available"
    for phone, snap in list(phones.items())[:3]:
        claim(row, "contact", {"type": "phone", "value": phone}, snap, {"link_href": "tel:" + phone}, identity_method="verified_company_site")
        row["availability"]["contact"] = "available"
    if row["availability"].get("description") != "available":
        def description_quote(node):
            quote = node.get_text(' ', strip=True)
            if not 60 <= len(quote) <= 1200 or re.search(r'cookie|personvern|privacy|samtykke|javascript|nettleser|all rights reserved', quote, re.I):
                return None
            for parent in [node, *node.parents]:
                if parent.name in {'nav', 'header', 'footer', 'aside'}:
                    return None
                classes = parent.get('class', [])
                classes = classes if isinstance(classes, list) else [classes]
                if re.search(r'(?:^|[-_\s])(blog|news|nyhet|post)(?:[-_\s]|$)', ' '.join(classes), re.I):
                    return None
            return quote
        # Literal company-authored prose is useful when metadata is absent. Restrict
        # this fallback to page main content; navigation/cookie/footer text is not a profile.
        for snap, parsed, visible in pages:
            if re.search(r"personvern|privacy|cookie|vilkar|terms|gdpr", snap["source_url"], re.I):
                continue
            if set(labelled_numbers(visible)) - {org}:
                continue
            options=[]
            selector='main p, [role="main"] p, article p'
            for paragraph in parsed.select(selector):
                quote = description_quote(paragraph)
                if quote and quote not in options:options.append(quote)
            if not options and snap is home:
                # Older/Squarespace themes often omit semantic main/article tags.
                # Admit a literal company-introduction paragraph, never arbitrary
                # navigation, a vendor credit or a news article's opening sentence.
                from .names import text_contains_name
                for paragraph in parsed.find_all('p'):
                    quote = description_quote(paragraph)
                    if (quote and text_contains_name(quote, body.get('navn', ''))
                            and re.search(r'\b(?:er|is|tilbyr|leverer|provides|offers|develops|founded)\b', quote, re.I)):
                        options.append(quote)
                        break
            if quote_selector and transport:
                # More sites use nested divs instead of semantic main/paragraph tags.
                # The model may select an existing source span, never author one.
                for node in parsed.select('p, div, section'):
                    if node.find_parent(['nav','header','footer','aside']) or node.find(['p','div','section']):continue
                    quote=description_quote(node)
                    if quote and quote not in options:options.append(quote)
                quote=quote_selector.select_description(body.get('navn',''),options,transport)
            else:
                quote=options[0] if options else None
            if quote and quote in options and quote in visible:
                claim(row, "description", quote, snap, {"text_quote": quote}, identity_method="verified_company_site_model_selected_quote" if quote_selector else "verified_company_site_literal_text")
                row["availability"]["description"] = "available"
                return


_OSM_HINTS = None


def osm_websites(legal_name, legal_form_code=None):
    """Websites OpenStreetMap mappers recorded for a business with exactly this core name.

    A hint only, tried like a name guess and published only after the normal identity proof. Chains,
    brands and housing associations are excluded. Data (c) OpenStreetMap contributors, ODbL."""
    global _OSM_HINTS
    from .names import NO_GUESS_FORMS, name_tokens
    if (legal_form_code or "").upper() in NO_GUESS_FORMS:
        return []
    if _OSM_HINTS is None:
        path = Path(__file__).with_name("data") / "osm_websites.json.gz"
        try:
            _OSM_HINTS = json.loads(gzip.decompress(path.read_bytes()))["hints"]
        except (OSError, ValueError, KeyError):
            _OSM_HINTS = {}
    found = []
    for website, _postcode in _OSM_HINTS.get("".join(name_tokens(legal_name)), []):
        if website not in found:
            found.append(website)
    return found[:2]


def research_website(row, body, transport, page_limit=4, extra=(), guesses=True, max_guess_fetches=2, only_extra=False):
    """Candidate ladder: registry homepage, NAV-verified employer homepage, previous verified site, name guesses."""
    from .names import guess_domains, resolves, registrable
    candidates, seen = [], set()

    def add(url, origin):
        if not url:
            return
        url = url if re.match(r"^https?://", url, re.I) else "https://" + url.strip()
        key = registrable(urllib.parse.urlsplit(url).hostname)
        if key and key not in seen:
            seen.add(key)
            candidates.append((url, origin))

    if only_extra:
        # Skip domains the first pass already tried.
        seen.update(registrable(urllib.parse.urlsplit(c["url"]).hostname) for c in row.get("website_research", {}).get("candidates", []))
    else:
        add(body.get("hjemmeside"), "registry")
    for url in extra:
        add(url, "nav_employer")
    if not only_extra:
        add(body.get("_previous_website"), "previous")
    personal_mail = {'gmail.com', 'googlemail.com', 'hotmail.com', 'hotmail.no', 'outlook.com', 'live.com', 'live.no',
                     'msn.com', 'yahoo.com', 'yahoo.no', 'icloud.com', 'me.com', 'mac.com', 'proton.me', 'protonmail.com', 'online.no',
                     'lyse.net', 'getmail.no', 'broadpark.no', 'c2i.net', 'altibox.no', 'sdsl.no', 'frisurf.no', 'tele2.no', 'start.no'}
    for domain in [] if only_extra else re.findall(r'@([a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+)', str(body.get('epostadresse') or ''), re.I):
        if domain.lower() not in personal_mail:
            # A registered contact domain is a hypothesis, never publisher proof.
            # Accountants, managers and group domains must still pass crawl_site.
            add('https://' + domain.lower() + '/', 'registry_email')
    research = row.setdefault("website_research", {"candidates": []})
    for field in SITE_FIELDS:
        row["availability"].setdefault(field, "not_available")
    for url, origin in candidates:
        if time.monotonic() >= getattr(transport,'deadline',float('inf')) or getattr(transport,'requests',0) >= getattr(transport,'limit',float('inf')):
            site_fail(row,'failed','Website research budget exhausted')
            return False
        research["candidates"].append({"url": url, "origin": origin})
        if crawl_site(row, body, transport, page_limit, origin=origin, url=url):
            return True
    if not guesses:
        return False
    fetched = 0
    form = (body.get("organisasjonsform") or {}).get("kode")
    hypotheses = [(u, 'osm_name') for u in osm_websites(body.get('navn', ''), form)]
    hypotheses += [(u, 'name_guess') for u in guess_domains(body.get('navn', ''), form)]
    for old in (body.get('historiskeNavn') or [])[-2:]:
        hypotheses.extend((u, 'historical_name_guess') for u in guess_domains(old.get('navn', ''), form))
    for url, guess_origin in hypotheses:
        if time.monotonic() >= getattr(transport,'deadline',float('inf')) or getattr(transport,'requests',0) >= getattr(transport,'limit',float('inf')):
            break
        if fetched >= max_guess_fetches:
            break
        key = registrable(urllib.parse.urlsplit(url).hostname)
        if key in seen or not resolves(url):
            continue
        seen.add(key)
        fetched += 1
        research["candidates"].append({"url": url, "origin": guess_origin})
        before = dict(row["availability"])
        if crawl_site(row, body, transport, page_limit, origin=guess_origin, url=url):
            return True
        # An unverified guess is not evidence about the company; restore prior states.
        for field in SITE_FIELDS:
            row["availability"][field] = before.get(field, "not_available")
        row["errors"] = [e for e in row["errors"] if not (e.get("module") == "website" and key in e.get("message", ""))]
    return False


FAMILY = {"public_brand": "official_website", "registered_activity": "legal_identity", "secondary_industries": "legal_identity", "share_capital": "legal_identity"}


def family_of(field):
    return "financials" if field.startswith("financials.") else field if field in FIELDS else FAMILY.get(field, "legal_identity")


ENGLISH_LEGAL_FORMS = {"AS": "a private limited company", "ASA": "a public limited company", "ANS": "a general partnership",
                       "DA": "a partnership with shared liability", "ENK": "a sole proprietorship", "NUF": "a Norwegian branch of a foreign company",
                       "SA": "a cooperative", "STI": "a foundation", "BRL": "a housing cooperative", "ESEK": "a condominium association",
                       "KS": "a limited partnership", "FLI": "an association", "BA": "a company with limited liability",
                       "SPA": "a savings bank", "KOMM": "a municipality", "ORGL": "an organisational unit"}
ENGLISH_ROLES = {"Daglig leder": "managing director", "Styrets leder": "chair of the board", "Nestleder": "deputy chair",
                 "Styremedlem": "board member", "Varamedlem": "deputy board member", "Regnskapsfører": "accountant",
                 "Revisor": "auditor", "Forretningsfører": "business manager", "Innehaver": "owner", "Kontaktperson": "contact person"}


def english_legal_form(form):
    """The register's form in English, keeping its Norwegian name so the source term stays checkable."""
    if not isinstance(form, dict):
        return "a Norwegian registered entity"
    norwegian = str(form.get("beskrivelse") or form.get("kode") or "").lower()
    english = ENGLISH_LEGAL_FORMS.get(str(form.get("kode") or "").upper())
    if english:
        return f"{english} ({norwegian})" if norwegian else english
    return f"registered as {norwegian}" if norwegian else "a Norwegian registered entity"


def fmt_amount_exact(amount, currency=None):
    """A full figure for a sentence: 30000.0 becomes NOK 30,000."""
    if isinstance(amount, (int, float)) and not isinstance(amount, bool):
        shown = f"{amount:,.0f}" if float(amount).is_integer() else f"{amount:,.2f}"
    else:
        shown = str(amount)
    return f"{currency or ''} {shown}".strip()


def fmt_amount(value):
    amount = value.get("amount")
    if not isinstance(amount, (int, float)):
        return str(amount)
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    for size, unit in ((1e9, " bn"), (1e6, " m"), (1e3, " k")):
        if amount >= size:
            return f"{value.get('currency') or ''} {sign}{amount / size:,.1f}{unit}".strip()
    return f"{value.get('currency') or ''} {sign}{amount:,.0f}".strip()


def parsed_date(value):
    """Normalize ISO and RSS dates for ordering; retain raw dates on claims."""
    try:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            dt = parsedate_to_datetime(str(value))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return datetime.min.replace(tzinfo=timezone.utc)


def financial_health(latest):
    """Two standard ratios from one period's filed figures, with the claims they rest on.

    Operating margin needs positive revenue. Equity ratio needs positive total assets. Nothing is
    estimated: a ratio appears only when both of its figures were filed for the same period."""
    amount = lambda key: (latest.get(key) or {}).get("value", {}).get("amount")
    said, used = [], []
    revenue, operating, equity, assets = amount("revenue"), amount("operating_result"), amount("equity"), amount("assets")
    if isinstance(revenue, (int, float)) and isinstance(operating, (int, float)) and revenue > 0:
        said.append(f"operating margin {operating / revenue:.1%}")
        used += [latest["revenue"], latest["operating_result"]]
    if isinstance(equity, (int, float)) and isinstance(assets, (int, float)) and assets > 0:
        said.append(f"equity ratio {equity / assets:.1%}" + (", so liabilities exceed assets" if equity < 0 else ""))
        used += [latest["equity"], latest["assets"]]
    return said, used


def synthesize(row):
    """Deterministic, evidence-cited narrative. Every statement renders only verified claims."""
    by = {}
    for c in row["claims"]:
        by.setdefault(c["field"], []).append(c)

    def first(field):
        return (by.get(field) or [None])[0]

    statements = []

    def say(text, claims, kind):
        claims = [c for c in claims if c]
        if claims:
            statements.append({"text": text, "kind": kind, "evidence_ids": sorted({e for c in claims for e in c["evidence_ids"]}), "claim_ids": [c["id"] for c in claims]})

    name, form, industry, municipality = first("legal_name"), first("legal_form"), first("industry"), first("municipality")
    if name:
        lead = f"{name['value']} is " + english_legal_form(form["value"] if form else None)
        details = []
        if industry and isinstance(industry["value"], dict) and str(industry["value"].get("kode")) != "00.000":
            details.append(f"registered under {str(industry['value'].get('beskrivelse', '')).lower()} (NACE {industry['value'].get('kode')})")
        if municipality:
            details.append(f"based in {str(municipality['value']).title()}")
        founded = first("founded_on") or first("registered_on")
        if founded:
            details.append(f"{'founded' if founded['field'] == 'founded_on' else 'registered'} {founded['value']}")
        say(lead + (" " + ", ".join(details) if details else "") + ".", [name, form, industry, municipality, founded], "identity")
    description, purpose, brand = first("description"), first("registered_activity"), first("public_brand")
    if description:
        say(f"Its verified website describes it as: “{' '.join(str(description['value']).split())[:280]}”" + (f" Public brand: {brand['value']}." if brand else ""), [description, brand], "what_it_does")
    if purpose:
        say(f"Registered activity: {purpose['value'][:280].rstrip('.')}.", [purpose], "what_it_does")
    flags = [c for c in (first("bankrupt"), first("liquidating")) if c and c["value"] is True]
    if flags:
        say("Warning: the registry flags this entity as " + " and ".join("bankrupt" if c["field"] == "bankrupt" else "under liquidation" for c in flags) + ".", flags, "risk")
    fin = [c for c in row["claims"] if c["field"].startswith("financials.") and isinstance(c.get("reporting_period"), dict)]
    latest = {}
    if fin:
        # One newest period only (company accounts preferred over group accounts): never mix years in a sentence.
        def rank(c):
            return (str(c["reporting_period"].get("tilDato") or ""), str(c["value"].get("account_type") or "").upper() == "SELSKAP")
        newest = max(fin, key=rank)
        end, kind = newest["reporting_period"].get("tilDato"), newest["value"].get("account_type")
        latest = {c["field"].split(".", 1)[1]: c for c in fin
                  if c["reporting_period"].get("tilDato") == end and c["value"].get("account_type") == kind}
    if latest:
        sample = next(iter(latest.values()))
        period = sample["reporting_period"]
        bits = [f"{label} {fmt_amount(latest[key]['value'])}" for key, label in (("revenue", "revenue"), ("operating_result", "operating result"), ("annual_result", "net result"), ("assets", "total assets"), ("equity", "equity")) if key in latest]
        verdict = ""
        result = latest.get("annual_result", {}).get("value", {}).get("amount") if "annual_result" in latest else None
        if isinstance(result, (int, float)):
            verdict = " The period closed with a " + ("profit." if result > 0 else "loss." if result < 0 else "break-even result.")
        equity = latest.get("equity", {}).get("value", {}).get("amount") if "equity" in latest else None
        if isinstance(equity, (int, float)) and equity < 0:
            verdict += " Reported equity is negative."
        year = str(period.get("tilDato") or "")[:4]
        registry_year = str(row["legal_identity"].get("latest_accounts_year") or "")
        label = "Latest filed accounts" if not registry_year or registry_year <= year else "Most recent accounts figures available"
        account_kind = {"SELSKAP": "company", "KONSERN": "group"}.get(str(sample["value"].get("account_type") or "").upper(), "company")
        say(f"{label} ({period.get('fraDato')} to {period.get('tilDato')}, {account_kind} accounts): " + ", ".join(bits) + "." + verdict, list(latest.values()), "financials")
        previous_year = str(int(year) - 1) if year.isdigit() else ""
        earlier = {c["field"].split(".", 1)[1]: c for c in fin if str(c["reporting_period"].get("tilDato") or "").startswith(previous_year + "-12")
                   and c["value"].get("account_type") == kind} if previous_year else {}
        moves, moved = [], []
        for key, label in (("revenue", "revenue"), ("annual_result", "net result"), ("equity", "equity")):
            now_value = (latest.get(key) or {}).get("value", {}).get("amount")
            old_value = (earlier.get(key) or {}).get("value", {}).get("amount")
            if not isinstance(now_value, (int, float)) or not isinstance(old_value, (int, float)):
                continue
            text = f"{label} went from {fmt_amount(earlier[key]['value'])} to {fmt_amount(latest[key]['value'])}"
            if old_value > 0 and now_value > 0:
                text += f" ({(now_value - old_value) / old_value:+.0%})"
            moves.append(text)
            moved += [latest[key], earlier[key]]
        if moves:
            say(f"Change from {previous_year} to {year}: " + "; ".join(moves) + ".", moved, "financial_change")
        health, used = financial_health(latest)
        if health:
            say(f"Financial position in {year}: " + "; ".join(health) + ". Calculated from the filed figures above.", used, "financial_health")
        if registry_year and year and registry_year > year:
            first_claim = next((c for c in row["claims"] if c["field"] == "latest_accounts_year"), None)
            say(f"The register records a {registry_year} annual-accounts filing, but Regnskapsregisteret did not return its figures at retrieval time; {year} figures are shown and are not the latest filing.",
                [first_claim] if first_claim else list(latest.values())[:1], "financials")
    employees = first("employees")
    if employees is not None:
        say(f"Registered employees: {employees['value']}.", [employees], "size")
    leaders = by.get("leadership", [])
    if leaders:
        priority = ("daglig leder", "styrets leder", "innehaver", "kontaktperson", "nestleder", "styremedlem")
        ranked = sorted(leaders, key=lambda c: next((i for i, p in enumerate(priority) if p in str(c["value"].get("role", "")).lower()), 99))
        shown = ranked[:4]
        say("Leadership in the official register: " + "; ".join(f"{c['value'].get('name')} ({ENGLISH_ROLES.get(c['value'].get('role'), c['value'].get('role'))})" for c in shown) + (f"; plus {len(leaders) - len(shown)} further role{'s' if len(leaders) - len(shown) != 1 else ''}." if len(leaders) > len(shown) else "."), shown, "leadership")
    places = by.get("locations", [])
    if places:
        cities = sorted({str((c["value"].get("address") or {}).get("poststed") or "").title() for c in places} - {""})
        say(f"{len(places)} registered workplace{'s' if len(places) != 1 else ''}" + (f" in {', '.join(cities[:6])}" + (" and more" if len(cities) > 6 else "") if cities else "") + ".", places[:6], "footprint")
    site, profiles = first("official_website"), by.get("owned_profiles", [])
    if site:
        method = next((e.get("identity_method") for e in row["evidence"] if e["id"] in site["evidence_ids"]), "verified")
        say(f"Official website {site['value']} (identity check: {str(method).replace('_', ' ')})" + (f"; company-linked profiles on {', '.join(sorted({c['value'].get('platform') for c in profiles}))}." if profiles else "."), [site] + profiles[:5], "footprint")
    jobs = by.get("jobs", [])
    if jobs:
        titles = "; ".join(str(c["value"].get("title"))[:90] for c in jobs[:3])
        say(f"Appears to be hiring: {len(jobs)} active job ad{'s' if len(jobs) != 1 else ''} with an exact employer match ({titles}).", jobs[:3], "hiring")
    activity = by.get("activity", [])
    news = sorted([c for c in activity if c["value"].get("kind") not in {"official_registry_event", "official_food_inspection"}], key=lambda c: parsed_date(c["value"].get("published_at")), reverse=True)
    inspections = sorted([c for c in activity if c["value"].get("kind") == "official_food_inspection"], key=lambda c: parsed_date(c["value"].get("published_at")), reverse=True)
    events = sorted([c for c in activity if c["value"].get("kind") == "official_registry_event"], key=lambda c: parsed_date(c["value"].get("published_at")), reverse=True)
    if news:
        say(f"Latest company-published activity: “{news[0]['value'].get('headline')}” ({parsed_date(news[0]['value'].get('published_at')).date().isoformat()}).", news[:1], "activity")
    if inspections:
        say(f"Latest official food safety inspection ({inspections[0]['value'].get('published_at')}), {inspections[0]['value'].get('workplace')}: {inspections[0]['value'].get('outcome')}.", inspections[:1], "activity")
    if events:
        say(f"Most recent registry event: {events[0]['value'].get('headline')} ({events[0]['value'].get('published_at')}).", events[:1], "activity")
    if row.get("changes"):
        changed = sorted({c["field"] for c in row["changes"]})
        statements.append({"text": f"Since the previous run, {len(row['changes'])} material change(s) were detected in: {', '.join(changed[:8])}.", "kind": "changes",
                           "evidence_ids": sorted({e for ch in row["changes"] for c in ch.get("current_claims", []) for e in c["evidence_ids"]}), "claim_ids": []})
    labels = {"official_website": "verified website", "description": "website description", "jobs": "active job ads", "activity": "dated public activity",
              "owned_profiles": "company-owned social profiles", "contact": "contact details", "financials": "filed accounts", "leadership": "registered roles", "locations": "registered workplaces"}
    unknown = [(f, s) for f, s in row["availability"].items() if s != "available" and f in labels]
    if unknown:
        statements.append({"text": "Not established from checked sources: " + "; ".join(f"{labels[f]} ({s.replace('_', ' ')})" for f, s in unknown) + ". Missing information is not treated as zero.",
                           "kind": "unknowns", "evidence_ids": [], "claim_ids": []})
    return {"text": " ".join(s["text"] for s in statements), "statements": statements,
            "unknowns": [{"field": k, "state": v} for k, v in row["availability"].items() if v != "available"],
            "changes": len(row.get("changes", [])), "method": "evidence_bounded_templates_v2"}


def external_footprint(row):
    """Plainly named view of external families; every entry points back to its claim and evidence."""
    ev = {e["id"]: e for e in row["evidence"]}

    def item(c, **fields):
        e = ev.get((c.get("evidence_ids") or [None])[0], {})
        return {**fields, "claim_id": c["id"], "evidence_ids": c["evidence_ids"], "source_url": e.get("source_url"),
                "retrieved_at": e.get("retrieved_at"), "identity_method": e.get("identity_method")}

    by = {}
    for c in row["claims"]:
        by.setdefault(c["field"], []).append(c)
    site = (by.get("official_website") or [None])[0]
    news = [c for c in by.get("activity", []) if isinstance(c["value"], dict) and c["value"].get("kind") != "official_registry_event"]
    return {
        "website": item(site, url=site["value"]) if site else None,
        "social_links": [item(c, platform=c["value"].get("platform"), url=c["value"].get("url")) for c in by.get("owned_profiles", [])],
        "news": [item(c, headline=c["value"].get("headline"), published_at=c["value"].get("published_at"), url=c["value"].get("url"))
                 for c in sorted(news, key=lambda c: parsed_date(c["value"].get("published_at")), reverse=True)],
        "job_postings": [item(c, title=c["value"].get("title"), date_posted=c["value"].get("date_posted"),
                              valid_through=c["value"].get("valid_through"), url=c["value"].get("url"), source=c["value"].get("source"))
                         for c in by.get("jobs", [])],
        "careers_page": item(by["careers_page"][0], url=by["careers_page"][0]["value"]) if by.get("careers_page") else None,
        "description": item(by["description"][0], text=by["description"][0]["value"]) if by.get("description") else None,
        "availability": {k: row["availability"].get(k) for k in ("official_website", "owned_profiles", "activity", "jobs", "description")},
    }


def finish(row, previous=None):
    for field in FIELDS:
        row["availability"].setdefault(field, "failed")
    row["run"]["completed_at"] = now()
    row["availability_status"] = "available" if row["legal_identity"] else row["availability"]["legal_identity"]
    # Diff field sets, not source hashes or volatile retrieval timestamps.
    previous = previous or {}
    old_refresh = previous.get("refresh") or {}
    prior_evidence = {e["id"]: e for e in [*old_refresh.get("previous_evidence", []), *previous.get("evidence", [])]}
    prior_snapshots = {s["id"]: s for s in [*old_refresh.get("previous_snapshots", []), *previous.get("source_snapshots", [])]}
    old_claims = {c["id"]: c for c in [*old_refresh.get("last_known_claims", []), *previous.get("claims", [])]}
    before = {}
    for c in old_claims.values():
        before.setdefault(c["field"], []).append(c)
    after = {}
    for c in row["claims"]:
        after.setdefault(c["field"], []).append(c)
    retained = []
    for field, old in before.items():
        family = family_of(field)
        current = after.get(field, [])
        current_ids = {c["id"] for c in current}
        comparable = []
        for c in old:
            failed = row["availability"].get(family) in {"failed", "blocked", "ambiguous"}
            evidence = [prior_evidence[e] for e in c["evidence_ids"] if e in prior_evidence]
            for ev in evidence:
                if ev.get("source_class") in {"company_owned", "official_public_api"} and c["id"] not in current_ids:
                    observed = [s for s in row["source_snapshots"] if ev["source_url"] in {s.get("source_url"), s.get("requested_url")}]
                    # A successful registry response says nothing about a failed news feed.
                    source_state = (row.get("research_sources", {}).get("nav_jobs") or {}).get("state") if ev.get("source_class") == "official_public_api" else None
                    failed = failed or not observed or any(s.get("status") != 200 for s in observed) or source_state in {"partial", "failed"}
            if failed and c["id"] not in current_ids:
                retained.append({**c, "stale": True})
            else:
                comparable.append(c)
        if comparable and sorted(digest({"value": c["value"], "period": c.get("reporting_period")}) for c in comparable) != sorted(digest({"value": c["value"], "period": c.get("reporting_period")}) for c in current):
            row["changes"].append({"field": field, "type": "changed" if current else "removed",
                                   "previous_claims": comparable, "current_claims": current})
        elif not comparable and current:
            # New observations of a family whose older source was unavailable are additions,
            # not evidence that its retained claims were removed.
            row["changes"].append({"field": field, "type": "added", "previous_claims": [], "current_claims": current})
    if previous:
        for field in after.keys() - before.keys():
            row["changes"].append({"field": field, "type": "added", "previous_claims": [], "current_claims": after[field]})
    row["refresh"] = {"previous_run_id": previous.get("run", {}).get("run_id"), "material_changes": len(row["changes"]),
                       "last_known_claims": retained, "previous_evidence": list(prior_evidence.values()),
                       "previous_snapshots": list(prior_snapshots.values())}
    facts = {c["field"]: c for c in row["claims"]}
    observed_periods = [c.get("reporting_period") for c in row["claims"] if c["field"].startswith("financials.")]
    ends = [p.get("tilDato") for p in observed_periods if isinstance(p, dict) and p.get("tilDato")]
    latest_end = max(ends, default=None)
    expected_year = str(row["legal_identity"].get("latest_accounts_year") or "")
    row["financial_freshness"] = {"latest_observed_period_end": latest_end, "registry_latest_filing_year": expected_year or None,
                                  "latest_filing_covered": bool(latest_end and expected_year and str(latest_end)[:4] == expected_year)}
    if latest_end and expected_year and str(latest_end)[:4] != expected_year:
        row["errors"].append({"module": "financials", "message": f"Accounts retrieved end {latest_end}; registry indicates filing year {expected_year}. Latest filing values remain unverified."})
    row["summary"] = synthesize(row)
    row["external_footprint"] = external_footprint(row)
    row["field_availability"] = {"employees": "available" if "employees" in facts else "not_available",
                                 "latest_filing_values": "available" if row["financial_freshness"]["latest_filing_covered"] else "not_available"}
    for field, state in row["field_availability"].items():
        if state != "available":
            row["summary"]["unknowns"].append({"field": field, "state": state})
    return row


def validate(rows, orgs, snapshots=None):
    errors = []
    snapshot_hashes = []
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
                snapshot_hashes.append(s["content_sha256"])
    if snapshot_hashes:
        def intact(sha):
            path = Path(snapshots) / (sha + ".bin")
            try:
                return path.exists() and digest(path.read_bytes()) == sha
            except OSError:
                return False
        # Shared evidence is immutable within this check. Rehash it on every
        # validation invocation, with bounded I/O rather than serial file reads.
        unique = list(dict.fromkeys(snapshot_hashes))
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            checked = dict(zip(unique, pool.map(intact, unique)))
        for sha in snapshot_hashes:
            if not checked[sha]:
                errors.append("Snapshot missing or corrupted")
    return {"passed": not errors, "errors": errors, "envelopes": len(rows)}


def drop_lost_snapshots(rows, snapshots):
    """Security software can remove or alter a page from a compromised site after it was fetched.

    Facts must not outlive their evidence, and one such site must not invalidate a whole run. A page
    that cannot be read back leaves the envelope, along with any claim that has no other evidence, and
    the field says so. Validation stays strict, so later tampering with a finished run still fails."""
    dropped = 0
    for row in rows:
        lost = []
        for snap in row["source_snapshots"]:
            path = Path(snapshots) / (snap["content_sha256"] + ".bin")
            try:
                intact = path.exists() and digest(path.read_bytes()) == snap["content_sha256"]
            except OSError:
                intact = False
            if not intact:
                lost.append(snap)
        if not lost:
            continue
        dropped += len(lost)
        lost_ids = {snap["id"] for snap in lost}
        row["source_snapshots"] = [snap for snap in row["source_snapshots"] if snap["id"] not in lost_ids]
        gone = {e["id"] for e in row["evidence"] if e.get("snapshot_id") in lost_ids}
        row["evidence"] = [e for e in row["evidence"] if e["id"] not in gone]
        kept = []
        for item in row["claims"]:
            item["evidence_ids"] = [e for e in item["evidence_ids"] if e not in gone]
            if item["evidence_ids"]:
                kept.append(item)
            else:
                family = family_of(item["field"])
                if not any(other is not item and family_of(other["field"]) == family and set(other["evidence_ids"]) - gone for other in row["claims"]):
                    row["availability"][family] = "failed"
        row["claims"] = kept
        for snap in lost:
            row["errors"].append({"module": "evidence", "message": f"Retrieved page unavailable after fetch; nothing is published from it: {snap.get('source_url')}"})
    return dropped


def run_batch(orgs, output, *, run_id, requests=1800, seconds=2400, workers=12, previous=None, pages=4, modules=("financials", "leadership", "locations", "jobs", "website"), registry=None, registry_retrieved_at=None, replay=None, discovery=None, agent=None, jobs_source=None, guesses=True, strategy="baseline", quote_selector=None):
    if strategy not in {"baseline", "balanced"}:
        raise ValueError("Unknown research strategy")
    if agent and replay:
        raise ValueError("AI network research is not allowed in offline replay")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if replay:
        from .replay import ReplayTransport
        transport = ReplayTransport(output / "snapshots", replay, requests, seconds)
    else:
        # Reserve time to write envelopes, validate evidence and render the viewer inside --max-seconds.
        transport = Transport(output / "snapshots", requests, max(30, seconds - max(60, seconds * 0.08)))
    started = time.monotonic()
    network_deadline = transport.deadline
    transport.quote_selector = quote_selector
    rows = [envelope(org, run_id) for org in orgs]
    bodies = {}
    prior = {r["organisation_number"]: r for r in previous or []}
    replay_seeds = {}
    if replay and (Path(replay) / "envelopes.jsonl").exists():
        replay_seeds = {r["organisation_number"]: r for r in (json.loads(line) for line in (Path(replay) / "envelopes.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())}
    registry_rows = {}
    registry_time_source = "supplied"
    if registry:
        if not registry_retrieved_at:
            # Builderr passes the frozen file without a timestamp; record its file time and say so.
            registry_retrieved_at = datetime.fromtimestamp(Path(registry).stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z")
            registry_time_source = "file_modified_time"
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
                    body = anchor(row, fetch_official(transport, ENTITY + org))
                if body:
                    # A previous discovered website is a candidate, never fresh evidence.
                    seed_row = prior.get(org) or replay_seeds.get(org)
                    if seed_row:
                        seed = next((c["value"] for c in seed_row.get("claims", []) if c["field"] == "official_website"), None)
                        if isinstance(seed, str):
                            body = {**body, "_previous_website": seed}
                    bodies[row["organisation_number"]] = body
            elif module == "website":
                body = bodies[row["organisation_number"]]
                remaining = transport.limit - transport.requests
                pending = max(1, sum(1 for r in rows if r["organisation_number"] in bodies and "website_research" not in r))
                # Adaptive depth: never let early companies starve later ones of requests.
                share = remaining / pending
                depth = max(2, min(pages, int(share) - 2))
                research_website(row, body, transport, depth, extra=nav_homepages.get(row["organisation_number"], ()),
                                 guesses=guesses and share >= (3 if strategy == "balanced" else 6), max_guess_fetches=3 if share >= 15 else 2 if share >= 10 else 1)
            elif module == "website_retry":
                retry_timed_out_candidates(row, bodies[row["organisation_number"]], transport, pages)
            elif module == "food_inspections":
                food_inspections.research(row, claim, news_date)
            elif module == "website_hints":
                # Second, bounded pass: NAV employer homepages exist only after the jobs phase.
                body = bodies[row["organisation_number"]]
                research_website(row, body, transport, max(2, min(pages, 4)), extra=nav_homepages.get(row["organisation_number"], ()),
                                 guesses=False, only_extra=True)
            elif module in {"jobs", "jobs_depth"}:
                if jobs_source is None:
                    row["availability"]["jobs"] = row["availability"].get("jobs", "not_available")
                else:
                    if nav_thread is not None:
                        nav_thread.join()
                    nav_homepages[row["organisation_number"]] = jobs_source.research(row, bodies[row["organisation_number"]], transport, claim)
            elif module == "agent":
                agent.research(row, bodies[row["organisation_number"]], transport, pages)
            elif module == "discovery":
                body = bodies[row["organisation_number"]]
                calls_before = getattr(discovery.local, "calls", 0)
                try:
                    batches = discovery.discover_batches(body, transport) if hasattr(discovery,'discover_batches') else (discovery.discover(body, transport),)
                    row["operations"]["third_party_cost_usd"] = float(discovery.unit_cost)
                    inspected = set()
                    for candidates in batches:
                        for candidate in candidates:
                            if candidate in inspected:
                                continue
                            inspected.add(candidate)
                            crawl_site(row, body, transport, pages, origin="search", url=candidate)
                            if row["availability"].get("official_website") == "available":
                                break
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

    nav_homepages, nav_thread = {}, None
    stage_metrics = []
    food_inspections = FoodInspections()
    if strategy == "balanced":
        # Reserve the early opportunity for source-backed external facts. Official
        # identities and current leaders anchor website verification before research.
        phase_order = ("identity", *(("leadership",) if "leadership" in modules else ()), *(("website",) if "website" in modules else ()),
                       *(("discovery",) if discovery else ()), *(("agent",) if agent else ()),
                       *(m for m in modules if m not in {"website", "jobs", "leadership"}),
                       *(("food_inspections",) if "locations" in modules and not replay else ()),
                       *(("jobs",) if "jobs" in modules else ()))
        if jobs_source:
            jobs_source.max_detail_requests = max(1, requests // 5)
    else:
        phase_order = ("identity", *modules, *(("discovery",) if discovery else ()), *(("agent",) if agent else ()))
    # Breadth before depth prevents early entities consuming every request.
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for stage_index,module in enumerate(phase_order):
            stage_begin, stage_clock = transport.requests, time.monotonic()
            transport.limit = requests
            transport.deadline = network_deadline
            if strategy == 'balanced':
                remaining_seconds=max(0,network_deadline-time.monotonic())
                if module in {'website','discovery','agent'}:
                    time_fraction={'website':.45,'discovery':.35,'agent':.25}[module]
                    transport.deadline=min(network_deadline,time.monotonic()+remaining_seconds*time_fraction)
                elif module in {'financials','leadership','locations'}:
                    records_left=sum(m in {'financials','leadership','locations'} for m in phase_order[stage_index:])
                    jobs_reserve=min(120,max(30,seconds*.1)) if 'jobs' in phase_order[stage_index+1:] else 0
                    allowance=max(1,(remaining_seconds-jobs_reserve)/max(1,records_left))
                    transport.deadline=min(network_deadline,time.monotonic()+allowance)
            stage_time_ceiling=round(max(0,transport.deadline-started),3)
            if strategy == "balanced" and module == "leadership" and "website" in modules:
                # Leaders improve verification, but a very small run budget must
                # still leave requests for the first website breadth pass.
                transport.limit = max(stage_begin, requests - len(bodies))
            if strategy == "balanced" and module in {"website", "discovery", "agent"}:
                fraction = .60 if module == "website" else .30
                transport.limit = min(requests, stage_begin + max(1, int((requests-stage_begin) * fraction)))
            if module == "food_inspections":
                food_inspections.load(transport)
            if strategy == "balanced" and module == "jobs" and jobs_source and not replay:
                remaining = max(0, requests - transport.requests)
                detail_reserve = min(max(40, 2 * len(rows)), remaining // 3)
                jobs_source.load(transport, min(NAV_FEED_PAGE_CAP, max(0, remaining - detail_reserve)))
            if strategy == "baseline" and module != "identity" and jobs_source is not None and nav_thread is None and "jobs" in modules and not replay:
                # The shared job index loads once per run, overlapping the official-record phases.
                official_cost = sum(1 for m in modules if m in {"financials", "leadership", "locations"}) * len(bodies)
                cap = min(NAV_FEED_PAGE_CAP, int(max(0, transport.limit - transport.requests - official_cost - 6 * len(bodies)) * 0.12))
                nav_thread = threading.Thread(target=jobs_source.load, args=(transport, cap), daemon=True)
                nav_thread.start()
            selected = rows if module == "identity" else [r for r in rows if r["organisation_number"] in bodies]
            if module == "discovery":
                selected = [r for r in selected if r["availability"].get("official_website") != "available"]
            list(pool.map(lambda r: task(r, module), selected))
            family = {"identity": "legal_identity"}.get(module, module)
            if family in {"legal_identity", "financials", "leadership", "locations"} and not replay:
                # Second chance after a cool-down: official endpoints throw transient 5xx bursts under load.
                again = [r for r in rows if r["availability"].get(family) == "failed"
                         and (module == "identity" or r["organisation_number"] in bodies)]
                if again and transport.requests < transport.limit and time.monotonic() < transport.deadline - 60:
                    time.sleep(8)
                    with transport.lock:
                        transport.retries_left = max(getattr(transport, "retries_left", 0), len(again))
                    list(pool.map(lambda r: task(r, module), again))
            write_rows(output / "checkpoint.jsonl", rows)
            stage_metrics.append({"stage": module, "requests": transport.requests-stage_begin, "seconds": round(time.monotonic()-stage_clock, 1),
                                  "request_ceiling": transport.limit,"time_ceiling_seconds":stage_time_ceiling})
        deeper = [r for r in rows if r["organisation_number"] in bodies
                  and (r.get("research_sources", {}).get("nav_jobs", {}).get("candidate_count", 0)
                       > r.get("research_sources", {}).get("nav_jobs", {}).get("detail_requests", 0))
                  and r.get("research_sources", {}).get("nav_jobs", {}).get("accepted_ads", 0) < getattr(jobs_source, "max_ads", 10)]
        if strategy == "balanced" and jobs_source and deeper and not replay and time.monotonic() < network_deadline - 30 and transport.requests < requests - 50:
            # Every company has had its breadth pass. Spend only remaining budget on depth,
            # prioritizing companies not yet covered, with a global detail ceiling.
            deeper.sort(key=lambda r: r["availability"].get("jobs") == "available")
            stage_begin, stage_clock = transport.requests, time.monotonic()
            transport.limit, transport.deadline = requests, network_deadline
            jobs_source.max_candidate_details = 12
            jobs_source.max_detail_requests = max(jobs_source.details, min(requests // 3, jobs_source.details + (requests - transport.requests - 50) // 2))
            list(pool.map(lambda r: task(r, "jobs_depth"), deeper))
            stage_metrics.append({"stage":"jobs_depth", "companies":len(deeper), "requests":transport.requests-stage_begin,
                                  "seconds":round(time.monotonic()-stage_clock,1), "request_ceiling":transport.limit,
                                  "time_ceiling_seconds":round(max(0,transport.deadline-started),3)})
        unfinished = [r for r in rows if r["organisation_number"] in bodies and website_cut_short(r)]
        if strategy == "balanced" and "website" in modules and unfinished and not replay and time.monotonic() < network_deadline - 120:
            # A slow network must not cost companies their only website pass while run time remains.
            stage_begin, stage_clock = transport.requests, time.monotonic()
            transport.limit, transport.deadline = requests, network_deadline - 60
            for row in unfinished:
                row["errors"] = [e for e in row["errors"] if not (e.get("module") == "website" and "budget" in e.get("message", "").lower())]
            list(pool.map(lambda r: task(r, "website"), unfinished))
            stage_metrics.append({"stage": "website_resume", "requests": transport.requests-stage_begin, "companies": len(unfinished),
                                  "seconds": round(time.monotonic()-stage_clock, 1), "request_ceiling": transport.limit,
                                  "time_ceiling_seconds": round(max(0, transport.deadline-started), 3)})
        hinted = [r for r in rows if r["organisation_number"] in bodies and nav_homepages.get(r["organisation_number"])
                  and r["availability"].get("official_website") != "available"]
        if strategy == "balanced" and hinted and not replay and time.monotonic() < network_deadline - 30:
            stage_begin = transport.requests
            transport.limit, transport.deadline = requests, network_deadline
            list(pool.map(lambda r: task(r, "website_hints"), hinted))
            stage_metrics.append({"stage": "website_hints", "requests": transport.requests-stage_begin, "companies": len(hinted),
                                  "request_ceiling": transport.limit, "time_ceiling_seconds": round(max(0, transport.deadline-started), 3)})
        retryable = [r for r in rows if r["organisation_number"] in bodies and r["availability"].get("official_website") != "available"
                     and (r.get("website_research") or {}).get("timed_out")]
        if strategy == "balanced" and retryable and not replay and time.monotonic() < network_deadline - 120:
            stage_begin, stage_clock = transport.requests, time.monotonic()
            # Insurance against a network blip, capped because it has recovered little in calm runs.
            transport.limit, transport.deadline = requests, min(network_deadline - 60, time.monotonic() + 90)
            list(pool.map(lambda r: task(r, "website_retry"), retryable))
            stage_metrics.append({"stage": "website_retry", "requests": transport.requests-stage_begin, "companies": len(retryable),
                                  "recovered": sum(bool(r["website_research"].get("retry_recovered")) for r in retryable),
                                  "seconds": round(time.monotonic()-stage_clock, 1), "request_ceiling": transport.limit,
                                  "time_ceiling_seconds": round(max(0, transport.deadline-started), 3)})
        transport.limit = requests
        transport.deadline = network_deadline
    dropped_snapshots = drop_lost_snapshots(rows, output / "snapshots")
    for row in rows:
        finish(row, prior.get(row["organisation_number"]))
        if row.get("agent", {}).get("selected_claim_ids"):
            # Model choices highlight verified claims; the cited narrative stays deterministic.
            row["summary"]["model_selected_claim_ids"] = [c["id"] for c in row["claims"] if c["id"] in set(row["agent"]["selected_claim_ids"])]
        # Count all observations including redirects. Fetch failures have run-level accounting.
    write_rows(output / "envelopes.jsonl", rows)
    validation = validate(rows, orgs, output / "snapshots")
    # Security software scans asynchronously, so a page can vanish after the first pass above.
    for _ in range(3):
        if validation["passed"]:
            break
        held = {row["organisation_number"]: len(row["source_snapshots"]) for row in rows}
        lost_late = drop_lost_snapshots(rows, output / "snapshots")
        if not lost_late:
            break
        dropped_snapshots += lost_late
        for row in rows:
            if len(row["source_snapshots"]) != held[row["organisation_number"]]:
                row["changes"] = []
                finish(row, prior.get(row["organisation_number"]))
                row["errors"] = list({(e.get("module"), e.get("message")): e for e in row["errors"]}.values())
        write_rows(output / "envelopes.jsonl", rows)
        validation = validate(rows, orgs, output / "snapshots")
    durations = sorted(r["operations"]["runtime_ms"] for r in rows)
    report = {"run_id": run_id, "completed_at": now(), "companies": len(orgs), "envelopes": len(rows),
              "validation": validation, "dropped_snapshots": dropped_snapshots, "requests": transport.requests, "bytes": transport.bytes,
              "runtime_seconds": round(time.monotonic() - started, 3), "third_party_cost_usd": float(discovery.spent) if discovery else 0,
              "limits": {"requests": requests, "seconds": seconds}, "p50_company_ms": durations[len(durations)//2],
              "p95_company_ms": durations[min(len(durations)-1, int(len(durations)*.95))],
              "coverage": {f: sum(r["availability"][f] == "available" for r in rows) for f in FIELDS},
              "states": {s: sum(v == s for r in rows for v in r["availability"].values()) for s in STATES},
              "score": None, "score_note": "Operational smoke test; no hidden labels or official competition score"}
    report["registry_snapshot"] = {"path": str(registry), "retrieved_at": registry_retrieved_at, "retrieved_at_source": registry_time_source, "sha256": snapshot_hash} if registry else None
    report["external_footprint_coverage"] = {k: sum(bool((r.get("external_footprint") or {}).get(k)) for r in rows)
                                             for k in ("website", "social_links", "news", "job_postings", "careers_page", "description")}
    report["strategy"] = strategy
    report["company_source_cache"] = {"scope": "this run only", "hits": transport.site_cache_hits,
                                      "unique_urls": len(transport.site_cache),
                                      "note": "Shared observations retain their original retrieval time and exact bytes; refresh fetches again."}
    report["stages"] = stage_metrics
    report["mode"] = "saved_source_replay" if replay else "live"
    report["replay_source"] = str(replay) if replay else None
    report["agent"] = agent.report() if agent else None
    report["quote_selector"] = quote_selector.report() if quote_selector else None
    if quote_selector and quote_selector.calls:
        report["third_party_cost_usd"] = None
    if agent:
        from .costs import estimate_costs
        report["third_party_cost_usd"] = None
        report["cost_estimate"] = estimate_costs(report["agent"], len(orgs))
        report["agent"]["companies_with_model_calls"] = sum(bool(r.get("agent", {}).get("model_calls")) for r in rows)
        report["agent"]["completed_tool_loops"] = sum(r.get("agent", {}).get("status") == "completed" for r in rows)
    report["jobs_source"] = jobs_source.report() if jobs_source else None
    report["website_methods"] = {}
    for r in rows:
        method = (r.get("website_research") or {}).get("verification", {}).get("method")
        if method:
            report["website_methods"][method] = report["website_methods"].get(method, 0) + 1
    report["discovery"] = {"provider": getattr(discovery, "provider_name", "Brave Web Search"), "queries": discovery.calls, "declared_unit_cost": float(discovery.unit_cost),
                           "max_cost_usd": float(discovery.max_cost), "live_verified": False} if discovery else None
    if discovery and discovery.calls and not discovery.unit_cost:
        report["third_party_cost_usd"] = None
        report["discovery"]["billing_note"] = "Query usage measured, provider rate/free allowance unverified; zero declared rate is not proof of zero cost."
    write_json(output / "run-report.json", report)
    return rows, report
