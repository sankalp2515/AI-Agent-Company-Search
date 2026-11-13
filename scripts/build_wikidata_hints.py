#!/usr/bin/env python3
"""Build src/orglens/data/wikidata_websites.json.gz: official websites (P856) of Wikidata items that carry
a Norwegian organisation number (P2333).

A discovery hint only: a listed website is published only after the agent's normal identity proof.
Municipality sites are left out, because foundations and funds often point to the municipality that manages them.
Wikidata content is available under CC0 1.0.

Query used at https://query.wikidata.org/sparql:
    SELECT ?org ?site WHERE { ?item wdt:P2333 ?org . ?item wdt:P856 ?site }
"""
import argparse
import gzip
import json
import re
import urllib.parse
from datetime import date
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sparql_json", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "src" / "orglens" / "data" / "wikidata_websites.json.gz")
    parser.add_argument("--retrieved", default=date.today().isoformat())
    args = parser.parse_args()
    hints = {}
    for row in json.loads(args.sparql_json.read_text(encoding="utf-8"))["results"]["bindings"]:
        org = re.sub(r"\D", "", row.get("org", {}).get("value", ""))
        site = row.get("site", {}).get("value", "").strip()
        host = (urllib.parse.urlsplit(site).hostname or "").lower()
        if len(org) != 9 or not site.startswith(("http://", "https://")) or not host or host.endswith("kommune.no"):
            continue
        if site not in hints.setdefault(org, []):
            hints[org].append(site)
    hints = {org: sites[:2] for org, sites in sorted(hints.items())}
    payload = {"source": "Wikidata (P2333 Norwegian organisation number, P856 official website)", "licence": "CC0 1.0",
               "retrieved": args.retrieved, "hints": hints}
    args.output.write_bytes(gzip.compress(json.dumps(payload, separators=(",", ":")).encode("utf-8"), 9, mtime=0))
    print(json.dumps({"organisations": len(hints), "bytes": args.output.stat().st_size}))


if __name__ == "__main__":
    main()
