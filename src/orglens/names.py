"""Name normalisation and keyless website-candidate generation.

Candidates are only hypotheses. A candidate never becomes a published website
until crawl_site proves the exact legal entity on the fetched pages.
"""
from __future__ import annotations

import re
import socket
import urllib.parse

LEGAL_FORMS = {"stiftelsen", "as", "asa", "ans", "da", "enk", "sa", "ba", "nuf", "ks", "kf", "iks", "sf", "fli", "stiftelse",
               "sti", "bbl", "aksjeselskap", "allmennaksjeselskap", "norge", "norway", "avd", "avdeling", "filial"}
STOPWORDS = {"og", "and", "the", "of", "for", "i", "a", "&", "in", "til", "med", "co", "company"}
# Generic words that cannot carry identity on their own in a domain label.
GENERIC = {"holding", "holdings", "invest", "investment", "investering", "eiendom", "eiendommer", "property", "group",
           "gruppen", "consult", "consulting", "service", "services", "bygg", "transport", "handel", "drift", "utvikling",
           "partner", "partners", "capital", "kapital", "management", "solutions", "systems", "tech", "media", "design",
           "sameie", "sameiet", "borettslag", "boligsameie", "elektro", "regnskap", "norsk", "nordic", "nord", "sor", "vest",
           "ost", "oslo", "bergen", "trondheim", "stavanger"}
# Housing associations and similar entities almost never own a brand domain; guesses only add risk.
NO_GUESS_FORMS = {"ESEK", "BRL", "SAM", "KIRK", "ORGL", "PERS", "TVAM", "BO", "KOMM", "FYLK", "STAT", "SÆR", "IKJP"}
# Directories, aggregators, credit agencies and platforms are never a company's own website.
AGGREGATORS = {"brreg.no", "proff.no", "purehelp.no", "gulesider.no", "1881.no", "firmview.no", "kredittsjekk.no",
               "creditsafe.com", "forvalt.no", "allabolag.se", "bedriftsdatabasen.no", "finn.no", "regnskapstall.no",
               "firmabasen.no", "180.no", "opplysningen.no", "kompass.com", "dnb.com", "bisnode.no", "enento.no",
               "linkedin.com", "facebook.com", "instagram.com", "indeed.com", "glassdoor.com", "tiktok.com", "x.com",
               "twitter.com", "youtube.com", "wikipedia.org", "nav.no", "arbeidsplassen.no", "vibbo.no",
               "eurocampings.co.uk", "booking.com", "tripadvisor.com", "google.com", "yelp.com", "mittanbud.no",
               "anbudstorget.no", "legelisten.no", "utdanning.no", "visitnorway.com", "norgesbilen.no", "proffnett.no"}


def translit(value):
    value = str(value or "").casefold()
    for a, b in (("æ", "ae"), ("ø", "o"), ("å", "a"), ("ä", "a"), ("ö", "o"), ("ü", "u"), ("é", "e"), ("è", "e")):
        value = value.replace(a, b)
    return value


def name_tokens(name):
    """Distinctive tokens of a legal name, with legal-form words removed."""
    words = re.findall(r"[a-z0-9]+", translit(name))
    return [w for w in words if w not in LEGAL_FORMS and w not in STOPWORDS]


def core_name(name):
    return " ".join(name_tokens(name))


def distinctive(tokens):
    return [t for t in tokens if len(t) >= 4 and t not in GENERIC and not t.isdigit()]


def registrable(host):
    host = (host or "").lower().rstrip(".").removeprefix("www.")
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "net"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def is_aggregator(url):
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in AGGREGATORS)


def domain_matches_name(url, legal_name):
    """True when the domain label carries a distinctive part of the legal name."""
    label = translit(registrable(urllib.parse.urlsplit(url).hostname).split(".")[0]).replace("-", "")
    tokens = name_tokens(legal_name)
    joined = "".join(tokens)
    if len(joined) >= 4 and (joined in label or (len(label) >= 5 and label in joined)):
        return True
    return any(t in label for t in distinctive(tokens))


def national_mismatch(url, legal_name):
    """'X Norway AS' on a non-.no domain: usually the international parent's site."""
    national = set(re.findall(r"[a-z]+", translit(legal_name))) & {"norge", "norway", "norden", "scandinavia", "skandinavia"}
    return bool(national) and not registrable(urllib.parse.urlsplit(url).hostname).endswith(".no")


def domain_is_full_name(url, legal_name):
    """Domain label spells the complete core legal name (hyphens ignored)."""
    domain = registrable(urllib.parse.urlsplit(url).hostname)
    label = translit(domain.split(".")[0]).replace("-", "")
    joined = "".join(name_tokens(legal_name))
    national = set(re.findall(r"[a-z]+", translit(legal_name))) & {"norge", "norway", "norden", "scandinavia", "skandinavia"}
    if national and not domain.endswith(".no"):
        # "X Norway AS" on x.com is usually the international parent's site, not the Norwegian entity.
        return False
    return len(joined) >= 5 and label == joined


def text_contains_name(text, legal_name):
    """Full core legal name (all tokens, in order) appears in visible text."""
    core = core_name(legal_name)
    if len(core) < 4:
        return False
    visible = " " + " ".join(re.findall(r"[a-z0-9]+", translit(text))) + " "
    return " " + core + " " in visible


def guess_domains(legal_name, legal_form_code=None, limit=6):
    """Deterministic brand-domain hypotheses from the legal name only."""
    if (legal_form_code or "").upper() in NO_GUESS_FORMS:
        return []
    tokens = name_tokens(legal_name)
    if not tokens or len("".join(tokens)) < 4 or len(tokens) > 4:
        return []
    labels = []
    joined, hyphen = "".join(tokens), "-".join(tokens)
    labels.append(joined)
    if len(tokens) > 1:
        labels.append(hyphen)
    raw = re.findall(r"[a-z0-9æøå]+", str(legal_name).casefold())
    alt = "".join(w.replace("ø", "oe").replace("æ", "ae").replace("å", "aa") for w in raw if translit(w) in tokens)
    if alt and alt not in labels:
        labels.append(alt)
    if len(tokens) > 1 and len(tokens[0]) >= 6 and tokens[0] not in GENERIC:
        labels.append(tokens[0])
    out = []
    for i, label in enumerate(labels):
        if not 3 <= len(label) <= 63:
            continue
        single = len(tokens) > 1 and label == tokens[0]
        # A lone first word is a weak hypothesis: only the Norwegian TLD, and only after full-name domains.
        for tld in (("no",) if single else ("no", "com")):
            out.append(f"https://{label}.{tld}/")
    return out[:limit]


def resolves(url):
    host = urllib.parse.urlsplit(url).hostname
    try:
        return bool(socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
    except OSError:
        return False
