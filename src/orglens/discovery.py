"""Multi-provider search discovery with automatic fallback chain.
Discovered URLs are transient candidate hints only; every candidate must
pass strict exact-entity verification in crawl_site before publication.
"""
from __future__ import annotations

import json
import os
import re
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal

import certifi

from .names import AGGREGATORS

ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

EXCLUDED = AGGREGATORS | {
    "brreg.no", "proff.no", "purehelp.no", "linkedin.com", "facebook.com", "instagram.com",
    "indeed.com", "glassdoor.com", "unstop.com", "1881.no", "gulesider.no", "yelp.com",
    "youtube.com", "wikipedia.org", "vexter.no", "kredittsjekk.no", "allabolag.se",
    "forvalt.no", "regnskapstall.no", "bedriftsdatabasen.no", "eniro.no", "firmview.no",
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Credentialed search requests never follow redirects, so keys cannot reach another host."""
    def redirect_request(self, *args, **kwargs):
        return None


def _open(req, timeout, ctx):
    return urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=ctx)).open(req, timeout=timeout)


def candidate_roots(body):
    """Extract candidate root URLs from Brave, Tavily, SerpAPI, or raw URL collections."""
    roots = []
    urls = []
    if isinstance(body, dict):
        kg = body.get("knowledge_graph")
        if isinstance(kg, dict):
            site = kg.get("website") or kg.get("website_url")
            if site:
                urls.append(site)
        items = []
        if "web" in body and isinstance(body["web"], dict):
            items.extend(body["web"].get("results", []))
        if "results" in body and isinstance(body["results"], list):
            items.extend(body["results"])
        if "organic_results" in body and isinstance(body["organic_results"], list):
            items.extend(body["organic_results"])
        for item in items:
            if isinstance(item, dict):
                u = item.get("url") or item.get("link")
                if u:
                    urls.append(u)
            elif isinstance(item, str):
                urls.append(item)
    elif isinstance(body, (list, tuple)):
        urls.extend(body)

    for raw_url in urls:
        if not isinstance(raw_url, str):
            continue
        p = urllib.parse.urlsplit(raw_url.strip())
        host = (p.hostname or "").lower()
        if not host or p.username or p.password or any(host == x or host.endswith("." + x) for x in EXCLUDED):
            continue
        if p.scheme not in {"http", "https"}:
            continue
        # Deduplicate and promote to root https URL
        root = urllib.parse.urlunsplit(("https", p.netloc, "/", "", ""))
        if root not in roots:
            roots.append(root)
    return roots[:3]


def make_company_query(company):
    """Format search query combining company legal name and municipality."""
    name = (company.get("navn") or company.get("legal_name") or "").strip()
    addr = company.get("forretningsadresse") or company.get("postadresse") or {}
    kommune = (addr.get("kommune") or company.get("municipality") or "").strip()
    orgnr = company.get("organisasjonsnummer") or company.get("organisation_number") or ""
    parts = []
    if name:
        parts.append(name)
    if kommune and kommune.lower() not in (name.lower()):
        parts.append(kommune)
    if not parts and orgnr:
        parts.append(orgnr)
    return " ".join(parts).strip()


class SerpApiProvider:
    """Google Search for Norway (gl=no, hl=no) via SerpAPI."""
    endpoint = "https://serpapi.com/search.json"

    def __init__(self, key, label="serpapi"):
        self.key = key
        self.label = label
        self.disabled = False
        self.ctx = ssl.create_default_context(cafile=certifi.where())

    def search(self, query, timeout):
        if self.disabled or not self.key:
            return []
        params = {
            "q": query,
            "api_key": self.key,
            "engine": "google",
            "google_domain": "google.no",
            "gl": "no",
            "hl": "no",
            "num": 4,
        }
        url = self.endpoint + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "OrgLens/0.2 discovery", "Accept": "application/json"})
        try:
            with _open(req, timeout, self.ctx) as resp:
                raw = resp.read(2_000_001)
                if len(raw) > 2_000_000:
                    return []
                data = json.loads(raw.decode("utf-8", errors="replace"))
                if "error" in data:
                    err = str(data["error"]).lower()
                    if any(t in err for t in ("exhaust", "quota", "plan", "searches", "rate")):
                        self.disabled = True
                    return []
                return candidate_roots(data)
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 402, 403, 429}:
                self.disabled = True
            return []
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return []


class TavilyProvider:
    """Fast web search via Tavily API."""
    endpoint = "https://api.tavily.com/search"

    def __init__(self, key, label="tavily"):
        self.key = key
        self.label = label
        self.disabled = False
        self.ctx = ssl.create_default_context(cafile=certifi.where())

    def search(self, query, timeout):
        if self.disabled or not self.key:
            return []
        payload = json.dumps({
            "query": query,
            "search_depth": "basic",
            "max_results": 4,
            "include_answer": False,
            "include_raw_content": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                "User-Agent": "OrgLens/0.2 discovery",
                "Accept": "application/json",
            },
        )
        try:
            with _open(req, timeout, self.ctx) as resp:
                raw = resp.read(2_000_001)
                if len(raw) > 2_000_000:
                    return []
                data = json.loads(raw.decode("utf-8", errors="replace"))
                return candidate_roots(data)
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 402, 403, 429, 432, 433}:
                self.disabled = True
            return []
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return []


class MultiSearchDiscovery:
    """Ordered fallback chain across search providers with strict budgets and caps."""
    def __init__(self, providers, unit_cost=0.0, max_cost=0.0):
        self.providers = providers
        self.unit_cost = Decimal(str(unit_cost))
        self.max_cost = Decimal(str(max_cost))
        self.spent = Decimal("0")
        self.calls = 0
        self.lock = threading.Lock()
        self.local = threading.local()
        names = [getattr(p, "label", p.__class__.__name__) for p in self.providers]
        self.provider_name = f"multi_search ({', '.join(names)})"

    def discover(self, company, transport):
        if transport.requests >= transport.limit:
            return []
        remaining_time = max(0.1, transport.deadline - time.monotonic() - 15)
        if remaining_time <= 1.0:
            return []
        timeout = min(12.0, remaining_time)

        query = make_company_query(company)
        if not query:
            return []

        for provider in self.providers:
            if getattr(provider, "disabled", False):
                continue
            with self.lock:
                if self.max_cost > 0 and self.spent + self.unit_cost > self.max_cost:
                    return []
                transport.reserve(getattr(provider, "endpoint", "search"))

            candidates = provider.search(query, timeout)
            with self.lock:
                self.spent += self.unit_cost
                self.calls += 1
                self.local.calls = getattr(self.local, "calls", 0) + 1

            if candidates:
                return candidates

        return []


class BraveDiscovery:
    """Legacy Brave Web Search connector kept for backward compatibility."""
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
        self.provider_name = "Brave Web Search"
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
        return candidate_roots(payload)


def build_discovery_from_env(unit_cost=0.0, max_cost=0.0):
    """Instantiate ordered provider chain from environment variables."""
    providers = []
    # 1. Primary: SerpAPI Key 1 (highest Norwegian entity precision)
    k1 = os.environ.get("SERPAPI_API_KEY")
    if k1:
        providers.append(SerpApiProvider(k1, label="serpapi-1"))

    # 2. Secondary: SerpAPI Key 2 (fallback when Key 1 quota is reached)
    k2 = os.environ.get("SERPAPI_API_KEY_2")
    if k2 and k2 != k1:
        providers.append(SerpApiProvider(k2, label="serpapi-2"))

    # 3. Tertiary: Tavily (large 1,000 requests allowance)
    tk = os.environ.get("TAVILY_API_KEY")
    if tk:
        providers.append(TavilyProvider(tk, label="tavily"))

    if not providers:
        return None

    return MultiSearchDiscovery(providers, unit_cost=unit_cost, max_cost=max_cost)
