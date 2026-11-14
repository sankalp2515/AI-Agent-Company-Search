#!/usr/bin/env python3
"""Site data for the version 2 JBOX site, from one envelopes file.

Same published facts and privacy rules as export_jbox_data.py. Adds a short description, a job count and
official inspections to the list, so the home page can filter and draw without opening each company.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_jbox_data as base  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
_describe = base.describe


def describe(claim, identity):
    value = claim["value"]
    if claim["field"] == "activity" and isinstance(value, dict) and value.get("kind") == "official_food_inspection":
        return "inspections", value.get("published_at", ""), value["headline"], None, "", ""
    if claim["field"] == "activity" and isinstance(value, dict) and value.get("kind") == "financial_change":
        return None
    if claim["field"] == "contact" and isinstance(value, dict) and value.get("type") == "person":
        return None  # a named private individual; the site has no need for it
    return _describe(claim, identity)


base.describe = describe
base.LEGAL_FORMS.update({"Allmennaksjeselskap": "Public limited company", "Samvirkeforetak": "Cooperative",
                         "Norskregistrert utenlandsk foretak": "Norwegian branch of a foreign company", "Ansvarlig selskap": "General partnership",
                         "Selskap med delt ansvar": "Partnership with shared liability", "Kommandittselskap": "Limited partnership"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--envelopes", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "jbox" / "site-data-v2")
    args = parser.parse_args()
    companies, files = [], {}
    for row in base.rows_from(args.envelopes):
        if not row.get("legal_identity"):
            continue
        company, facts, statements = base.company_tables(row, "v2", False)
        footprint = row.get("external_footprint") or {}
        text = (footprint.get("description") or {}).get("text") or ""
        company["description"] = " ".join(str(text).split())[:180]
        company["job_count"] = sum(fact["section"] == "hiring" for fact in facts)
        company["news_count"] = sum(fact["section"] == "news" for fact in facts)
        for fact in facts:
            fact.pop("org_number", None)
        for line in statements:
            line.pop("org_number", None)
        companies.append(company)
        files[company["org_number"]] = {"company": company, "facts": facts, "statements": statements}
    companies.sort(key=lambda item: (not item["website"], -item["fact_count"], item["name"]))
    (args.output / "company").mkdir(parents=True, exist_ok=True)
    drop = {"summary", "rechecked", "material_changes", "sample", "news_state"}
    index = [{key: value for key, value in item.items() if key not in drop} for item in companies]
    (args.output / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for org, record in files.items():
        (args.output / "company" / f"{org}.json").write_text(json.dumps(record, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"companies": len(companies), "facts": sum(len(f["facts"]) for f in files.values()),
                      "with_website": sum(bool(c["website"]) for c in companies), "with_jobs": sum(c["job_count"] > 0 for c in companies),
                      "with_news": sum(c["news_count"] > 0 for c in companies), "index_bytes": (args.output / "index.json").stat().st_size}))


if __name__ == "__main__":
    main()
