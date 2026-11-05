"""Official open records keyed by organisation number.

Food Safety Authority inspection results (Smilefjes), CC BY 4.0. The exact organisation number is
the identity, so no name matching is involved. The authority withdraws invalidated inspections from
this file and asks users to refresh daily, so every run reads it live and never reuses a saved copy.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime

FOOD_INSPECTIONS_URL = "https://smilefjes.mattilsynet.no/api/tilsyn.csv"
FOOD_INSPECTIONS_MAX_BYTES = 40_000_000
OUTCOMES = {"0": "no violations found (smiling face)", "1": "minor violations not requiring follow-up (smiling face)",
            "2": "violations requiring follow-up (straight face)", "3": "serious violations (sad face)"}


def parse_inspections(text):
    """Inspections by organisation number. Rows without a usable number, date or outcome are ignored."""
    delimiter = ";" if text[:500].count(";") > text[:500].count(",") else ","
    found = {}
    for row in csv.DictReader(io.StringIO(text), delimiter=delimiter):
        org = re.sub(r"\D", "", str(row.get("orgnummer") or ""))
        outcome = OUTCOMES.get(str(row.get("total_karakter") or "").strip())
        try:
            date = datetime.strptime(str(row.get("dato") or "").strip(), "%d%m%Y").date().isoformat()
        except ValueError:
            continue
        if len(org) != 9 or not outcome:
            continue
        found.setdefault(org, []).append({"date": date, "raw_date": row.get("dato"), "name": str(row.get("navn") or "").strip(),
                                          "town": str(row.get("poststed") or "").strip().title(), "outcome": outcome,
                                          "inspection_id": row.get("tilsynid"), "unit": org})
    return found


class FoodInspections:
    def __init__(self, per_company=3):
        self.per_company = per_company
        self.snapshot = None
        self.by_org = {}
        self.state = "not_loaded"

    def load(self, transport):
        self.snapshot = transport.get(FOOD_INSPECTIONS_URL, "official_public_api")
        if self.snapshot.get("status") != 200:
            self.state = "failed"
            return
        self.by_org = parse_inspections(self.snapshot["text"])
        self.state = "loaded" if self.by_org else "failed"

    def research(self, row, claim, news_date):
        """Publish the newest inspections of this exact entity or a registered workplace it owns."""
        if self.state != "loaded":
            return 0
        org = row["organisation_number"]
        units = {org} | {str(c["value"].get("organisation_number")) for c in row["claims"]
                         if c["field"] == "locations" and isinstance(c["value"], dict)}
        items = sorted((item for unit in units for item in self.by_org.get(unit, [])), key=lambda item: item["date"], reverse=True)
        published = 0
        for item in items:
            if published >= self.per_company:
                break
            date = news_date(item["date"])
            if not date:
                continue
            place = item["name"] + (f", {item['town']}" if item["town"] else "")
            claim(row, "activity", {"headline": f"Food safety inspection of {place}: {item['outcome']}", "published_at": date,
                                    "url": f"{FOOD_INSPECTIONS_URL}#{item['inspection_id']}", "kind": "official_food_inspection",
                                    "outcome": item["outcome"], "workplace": item["name"]},
                  self.snapshot, {"csv_key": "tilsynid", "csv_value": item["inspection_id"], "matched_orgnr": item["unit"], "date_quote": item["raw_date"]},
                  period={"published_at": date},
                  identity_method="official_record_exact_orgnr" if item["unit"] == org else "official_record_registered_subunit")
            row["availability"]["activity"] = "available"
            published += 1
        return published
