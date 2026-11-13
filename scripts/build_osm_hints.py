#!/usr/bin/env python3
"""Build src/orglens/data/osm_websites.json.gz from an Overpass export of Norwegian businesses with a website.

The file is a discovery hint only: a matched website must still pass the agent's normal identity proof.
Names used by more than two places, or tagged as a brand, are left out because they point to a chain.
Data (c) OpenStreetMap contributors, available under the Open Database Licence (ODbL).

Overpass query used (area "Norge"): shop, craft, office, tourism, selected amenity and leisure objects
that have both `name` and `website`, output `center tags`.
"""
import argparse
import gzip
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from orglens.names import name_tokens  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("overpass_json", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "src" / "orglens" / "data" / "osm_websites.json.gz")
    parser.add_argument("--retrieved", default=date.today().isoformat())
    args = parser.parse_args()
    groups = defaultdict(list)
    for element in json.loads(args.overpass_json.read_text(encoding="utf-8"))["elements"]:
        tags = element.get("tags", {})
        website = (tags.get("website") or "").strip()
        key = "".join(name_tokens(tags.get("name", "")))
        if len(key) < 5 or not website.startswith(("http://", "https://")):
            continue
        groups[key].append((website, tags.get("addr:postcode", ""), bool(tags.get("brand") or tags.get("brand:wikidata"))))
    hints = {}
    for key, items in groups.items():
        if len(items) > 2 or any(branded for _, _, branded in items):
            continue
        hints[key] = [[website, postcode] for website, postcode, _ in items]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": "OpenStreetMap via Overpass API", "licence": "ODbL 1.0, (c) OpenStreetMap contributors",
               "retrieved": args.retrieved, "hints": hints}
    args.output.write_bytes(gzip.compress(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9, mtime=0))
    print(json.dumps({"names": len(hints), "bytes": args.output.stat().st_size}))


if __name__ == "__main__":
    main()
