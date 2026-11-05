#!/usr/bin/env python3
"""Flatten released OrgLens envelopes into seed tables for the JBOX Signalpost site.

Reads only the released artifacts. Every published fact keeps its source, retrieval time,
reporting period and place in the source. Mobile numbers and sole traders' contact details
are left out because they can identify a private person.
"""
import argparse
import csv
import gzip
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

METHODS = {
    "official_organisation_endpoint": "Looked up directly by organisation number in the official register",
    "labelled_organisation_number": "The company's site shows this exact organisation number",
    "legal_name_and_registered_address": "The site shows the full legal name and the registered address",
    "legal_name_and_registered_phone": "The site shows the full legal name and the registered phone number",
    "registry_declared_homepage": "The official register lists this site for the company",
    "jsonld_organisation_identifier": "The site's structured data declares this organisation number",
    "verified_company_site": "Found on the company's verified website",
    "verified_company_site_feed": "Published in the feed of the company's verified website",
    "verified_company_site_literal_text": "Quoted word for word from the company's verified website",
    "outbound_link_on_verified_company_site": "Linked from the company's verified website",
    "link_on_verified_company_site": "Linked from the company's verified website",
}
FINANCIALS = {
    "financials.revenue": "Revenue",
    "financials.operating_result": "Operating result",
    "financials.annual_result": "Net result",
    "financials.assets": "Total assets",
    "financials.equity": "Equity",
}
SIMPLE = {
    "legal_name": ("identity", "Legal name"),
    "public_brand": ("identity", "Public brand"),
    "registered_on": ("identity", "Registered on"),
    "founded_on": ("identity", "Founded on"),
    "municipality": ("identity", "Municipality"),
    "registered_activity": ("identity", "Registered activity"),
    "latest_accounts_year": ("identity", "Latest filed accounts year"),
    "employees": ("identity", "Employees in the register"),
    "official_website": ("web", "Official website"),
    "careers_page": ("web", "Careers page"),
    "description": ("web", "Company's own description"),
}
FLAGS = {"bankrupt": "Bankruptcy", "liquidating": "Liquidation", "in_group": "Part of a group"}
FACT_COLUMNS = ["id", "org_number", "section", "label", "value_text", "value_number", "unit", "period", "link_url",
                "source_url", "source_name", "source_class", "retrieved_at", "where_in_source", "identity_check", "content_sha256"]
AVAILABILITY = ["official_website", "owned_profiles", "activity", "description", "jobs", "financials", "leadership", "locations", "contact"]
LEGAL_FORMS = {"Aksjeselskap": "Limited company", "Eierseksjonssameie": "Condominium association", "Borettslag": "Housing cooperative",
               "Forening/lag/innretning": "Association", "Stiftelse": "Foundation", "Enkeltpersonforetak": "Sole proprietorship"}
ROLES = {"Daglig leder": "Managing director", "Styrets leder": "Chair of the board", "Nestleder": "Deputy chair", "Styremedlem": "Board member",
         "Varamedlem": "Deputy board member", "Regnskapsfører": "Accountant", "Revisor": "Auditor", "Forretningsfører": "Business manager",
         "Innehaver": "Owner", "Kontaktperson": "Contact person"}
PLATFORMS = {"linkedin": "LinkedIn", "youtube": "YouTube", "tiktok": "TikTok"}


def clean(text):
    """Role holders that are firms reach the summary as a printed list, such as ['BDO AS']."""
    text = re.sub(r"\[((?:'[^']*'(?:, )?)+)\]", lambda match: ", ".join(re.findall(r"'([^']*)'", match[1])), str(text))
    for norwegian, english in LEGAL_FORMS.items():
        text = re.sub(rf"\bis an? {re.escape(norwegian.lower())}\b", f"is a {english.lower()} ({norwegian.lower()})", text)
    for norwegian, english in ROLES.items():
        text = text.replace(f"({norwegian})", f"({english})")
    text = text.replace("SELSKAP accounts", "company accounts").replace("KONSERN accounts", "group accounts").replace(" in uoppgitt (NACE 00.000)", "")
    text = re.sub(r"\b(\d+)\.0 NOK\b", lambda match: f"NOK {int(match[1]):,}", text)
    return text.replace("plus 1 further roles", "plus 1 further role")


def clean_industry(text):
    return "Not specified in the register" if text == "Uoppgitt" else text


def english_form(norwegian):
    return f"{LEGAL_FORMS[norwegian]} ({norwegian})" if norwegian in LEGAL_FORMS else norwegian


def address(value):
    if not value:
        return ""
    return ", ".join(part for part in [" ".join(value.get("adresse") or []), value.get("postnummer"), value.get("poststed")] if part)


def period_text(period):
    if not period:
        return ""
    if period.get("tilDato"):
        return f'{period.get("fraDato", "")} to {period["tilDato"]}'
    return period.get("date", "")


def source_name(evidence):
    url = evidence["source_url"]
    if "regnskapsregisteret" in url:
        return "Regnskapsregisteret (annual accounts)"
    if evidence["source_class"] == "official_registry":
        return "Enhetsregisteret (official company register)"
    return url.split("//", 1)[-1].split("/", 1)[0].removeprefix("www.")


def where(locator):
    locator = locator or {}
    if locator.get("json_pointer"):
        return f'Field {locator["json_pointer"]} in the register record'
    if locator.get("text_quote"):
        return f'Page text: "{str(locator["text_quote"])[:180]}"'
    if locator.get("link_href"):
        return f'Link on the page: {locator["link_href"]}'
    if locator.get("title"):
        return f'Feed item: "{locator["title"]}"'
    if locator.get("declared_by"):
        return f'Website field in {locator["declared_by"]}'
    if locator.get("css_selector"):
        return f'Page element: {locator["css_selector"]}'
    if "jsonld" in locator:
        return "Structured data on the page"
    return ""


def describe(claim, identity):
    """Return section, label, text, number, unit and link, or None for a fact the site leaves out."""
    field, value = claim["field"], claim["value"]
    if field in FINANCIALS:
        return "financials", FINANCIALS[field], "", value["amount"], value["currency"], ""
    if field in FLAGS:
        return "identity", FLAGS[field], "Yes" if value else "No", None, "", ""
    if field in SIMPLE:
        section, label = SIMPLE[field]
        if field in {"official_website", "careers_page"}:
            return section, label, value, None, "", value
        if field == "employees":
            return section, label, "", value, "people", ""
        return section, label, str(value)[:280], None, "", ""
    if field in {"legal_form", "industry"}:
        if field == "legal_form":
            return "identity", "Legal form", english_form(value.get("beskrivelse", "")), None, "", ""
        return "identity", "Industry", clean_industry(value.get("beskrivelse", "")), None, "", ""
    if field == "secondary_industries":
        return "identity", "Other industries", "; ".join(item["beskrivelse"] for item in value), None, "", ""
    if field == "business_address":
        return "identity", "Business address", address(value), None, "", ""
    if field == "share_capital":
        return "identity", "Share capital", "", value["amount"], value["currency"], ""
    if field == "contact":
        if value["type"] == "mobile" or (identity.get("legal_form") or {}).get("kode") == "ENK":
            return None
        return "identity", f'Contact {value["type"]}', value["value"], None, "", ""
    if field == "leadership":
        return "people", ROLES.get(value["role"], value["role"]), clean(value["name"]), None, "", ""
    if field == "locations":
        return "workplaces", value["name"], address(value.get("address")), None, "", ""
    if field == "owned_profiles":
        return "web", PLATFORMS.get(value["platform"], value["platform"].capitalize()), value["url"], None, "", value["url"]
    if field == "activity":
        if value.get("kind") == "official_registry_event":
            return "registry_events", value.get("published_at", ""), clean(value["headline"]), None, "", ""
        return "news", value.get("published_at", ""), value["headline"], None, "", value.get("url", "")
    if field == "jobs":
        return "hiring", value.get("title", "Job ad"), value.get("employer", ""), None, "", value.get("url", "")
    return None


def company_tables(row, sample, rechecked):
    identity = row["legal_identity"]
    evidence = {item["id"]: item for item in row["evidence"]}
    org, facts, latest = row["organisation_number"], [], {}
    for claim in row["claims"]:
        described = describe(claim, identity)
        if not described or not claim.get("evidence_ids"):
            continue
        source = evidence[claim["evidence_ids"][0]]
        section, label, text, number, unit, link = described
        facts.append(dict(zip(FACT_COLUMNS, [claim["id"], org, section, label, text, number, unit, period_text(claim.get("reporting_period")), link,
                                             source["source_url"], source_name(source), source["source_class"], source["retrieved_at"],
                                             where(source.get("locator")), METHODS.get(source.get("identity_method"), ""), source["content_sha256"]])))
        if claim["field"] in FINANCIALS:
            end = claim["reporting_period"]["tilDato"]
            if claim["field"] not in latest or end > latest[claim["field"]][0]:
                latest[claim["field"]] = (end, claim["value"]["amount"])
    published = {fact["id"] for fact in facts}
    statements = [{"org_number": org, "position": index, "kind": item.get("kind", ""), "text": clean(item["text"]),
                   "fact_ids": "|".join(claim for claim in item.get("claim_ids", []) if claim in published)}
                  for index, item in enumerate(row["summary"].get("statements", []))]
    footprint = row["external_footprint"]
    state = row["availability"]
    company = {
        "org_number": org, "name": identity["legal_name"], "legal_form": english_form((identity.get("legal_form") or {}).get("beskrivelse", "")),
        "industry_code": (identity.get("industry") or {}).get("kode", ""), "industry": clean_industry((identity.get("industry") or {}).get("beskrivelse", "")),
        "municipality": identity.get("municipality", ""), "address": address(identity.get("business_address")),
        "founded_on": identity.get("founded_on", ""), "employees": identity.get("employees", ""),
        "latest_period_end": max((value[0] for value in latest.values()), default=""),
        "revenue": latest.get("financials.revenue", ("", ""))[1], "operating_result": latest.get("financials.operating_result", ("", ""))[1],
        "net_result": latest.get("financials.annual_result", ("", ""))[1], "assets": latest.get("financials.assets", ("", ""))[1],
        "equity": latest.get("financials.equity", ("", ""))[1], "website": (footprint.get("website") or {}).get("url", ""),
        "profile_count": len(footprint.get("social_links") or []), "news_count": len(footprint.get("news") or []),
        "summary": clean(row["summary"]["text"]), "fact_count": len(facts), "last_checked": row["run"].get("completed_at", ""),
        "rechecked": rechecked, "material_changes": row["refresh"].get("material_changes", 0), "sample": sample,
    }
    company.update({f"state_{key}": state.get(key, "not_available") for key in AVAILABILITY})
    company["news_state"] = footprint["availability"].get("activity", "not_available") if footprint.get("news") else "not_available"
    return company, facts, statements


def rows_from(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=ROOT / "submission" / "release")
    parser.add_argument("--output", type=Path, default=ROOT / "jbox" / "seed")
    parser.add_argument("--sample-orgs", default="941009697,915313760,988106542,917191530,979570023,971062029")
    args = parser.parse_args()
    companies, facts, statements = [], [], []
    for path, sample, rechecked in [(args.release / "smoke" / "envelopes.jsonl", "smoke", True), (args.release / "scale" / "envelopes.jsonl.gz", "scale", False)]:
        for row in rows_from(path):
            company, company_facts, company_statements = company_tables(row, sample, rechecked)
            companies.append(company)
            facts.extend(company_facts)
            statements.extend(company_statements)
    companies.sort(key=lambda item: (not item["website"], -item["fact_count"], item["name"]))
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "companies.csv", companies)
    write_csv(args.output / "facts.csv", facts)
    write_csv(args.output / "statements.csv", statements)
    bundle = {"companies": companies, "facts": facts, "statements": statements}
    (args.output / "signalpost-data.json").write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    chosen = set(args.sample_orgs.split(","))
    sample = {"companies": [item for item in companies if item["org_number"] in chosen],
              "facts": [item for item in facts if item["org_number"] in chosen],
              "statements": [item for item in statements if item["org_number"] in chosen]}
    (args.output / "sample-6-companies.json").write_text(json.dumps(sample, ensure_ascii=False), encoding="utf-8")
    site = args.output.parent / "site-data"
    (site / "company").mkdir(parents=True, exist_ok=True)
    (site / "index.json").write_text(json.dumps([{key: value for key, value in item.items() if key != "summary"} for item in companies], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for item in companies:
        org = item["org_number"]
        record = {"company": item, "facts": [fact for fact in facts if fact["org_number"] == org], "statements": [line for line in statements if line["org_number"] == org]}
        (site / "company" / f"{org}.json").write_text(json.dumps(record, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"companies": len(companies), "facts": len(facts), "statements": len(statements), "with_website": sum(bool(item["website"]) for item in companies)}))


if __name__ == "__main__":
    main()
