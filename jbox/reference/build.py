#!/usr/bin/env python3
"""Fill the design reference page with six real companies from the JBOX seed."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = json.loads((HERE.parent / "seed" / "sample-6-companies.json").read_text(encoding="utf-8"))
kept, counts = [], {}
for fact in data["facts"]:
    key = (fact["org_number"], fact["section"])
    counts[key] = counts.get(key, 0) + 1
    if fact["section"] in {"registry_events", "workplaces"} and counts[key] > 6:
        continue
    kept.append(fact)
data["facts"] = kept
ids = {fact["id"] for fact in kept}
for statement in data["statements"]:
    statement["fact_ids"] = "|".join(item for item in statement["fact_ids"].split("|") if item in ids)
payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
page = (HERE / "template.html").read_text(encoding="utf-8").replace("__DATA__", payload)
(HERE / "index.html").write_text(page, encoding="utf-8")
print(len(page))
