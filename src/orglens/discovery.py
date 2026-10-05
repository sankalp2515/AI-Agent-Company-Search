"""Opt-in paid discovery. Results are transient candidates, never claim evidence."""
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal

ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
EXCLUDED = {"brreg.no", "proff.no", "purehelp.no", "linkedin.com", "facebook.com", "instagram.com", "indeed.com", "glassdoor.com", "unstop.com", "1881.no", "gulesider.no", "yelp.com", "youtube.com", "wikipedia.org"}


def candidate_roots(body):
    roots = []
    for result in (body.get("web") or {}).get("results", []):
        p = urllib.parse.urlsplit(result.get("url", ""))
        host = (p.hostname or "").lower()
        if p.scheme != "https" or not host or p.username or p.password or any(host == x or host.endswith("." + x) for x in EXCLUDED):
            continue
        root = urllib.parse.urlunsplit(("https", p.netloc, "/", "", ""))
        if root not in roots:
            roots.append(root)
    return roots[:2]


class BraveDiscovery:
    def __init__(self, key, cost_per_request, max_cost, opener=None):
        if not key or Decimal(str(cost_per_request)) <= 0 or Decimal(str(max_cost)) <= 0:
            raise ValueError("Discovery requires an API key, positive declared per-request cost and spending cap")
        self.key = key
        self.unit_cost = Decimal(str(cost_per_request))
        self.max_cost = Decimal(str(max_cost))
        self.spent = Decimal("0")
        self.lock = threading.Lock()
        self.local = threading.local()
        self.calls = 0
        if opener is None:
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *a, **k):
                    return None
            opener = urllib.request.build_opener(NoRedirect())
        self.opener = opener

    def discover(self, company, transport):
        query = f'"{company["organisasjonsnummer"]}" "{company.get("navn", "")}"'
        url = ENDPOINT + "?" + urllib.parse.urlencode({"q": query, "country": "NO", "count": 5})
        with self.lock:
            if self.spent + self.unit_cost > self.max_cost:
                raise RuntimeError("Declared search API spending cap exhausted")
            transport.reserve(ENDPOINT)
            self.spent += self.unit_cost
            self.calls += 1
            self.local.calls = getattr(self.local, "calls", 0) + 1
        request = urllib.request.Request(url, headers={"Accept": "application/json", "X-Subscription-Token": self.key})
        with self.opener.open(request, timeout=min(12, max(.1, transport.deadline - time.monotonic()))) as response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("Discovery response too large")
            payload = json.loads(raw)
        # No query, snippets, rank or provider response is written to disk.
        return candidate_roots(payload)
