"""Produce an honest release audit, including excluded preliminary site matches."""
import argparse
import json
from pathlib import Path


def read(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preliminary", required=True)
    parser.add_argument("--audited", required=True)
    parser.add_argument("--refresh", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    before = read(args.preliminary)
    after = read(args.audited)
    refresh = read(args.refresh)
    old_sites = {r["organisation_number"] for r in before if r["availability"]["official_website"] == "available"}
    new_sites = {r["organisation_number"] for r in after if r["availability"]["official_website"] == "available"}
    accepted = []
    for row in after:
        for c in row["claims"]:
            if c["field"] == "official_website":
                accepted.append({"organisation_number": row["organisation_number"], "legal_name": row["legal_identity"].get("legal_name"),
                                 "website": c["value"], "identity_evidence": [e for e in row["evidence"] if e["id"] in c["evidence_ids"]]})
    report = {"companies": len(after), "mode": "final_policy_on_saved_live_sources", "accepted_websites": accepted,
              "excluded_preliminary_matches": sorted(old_sites - new_sites), "unchanged_replay_changes": sum(len(r["changes"]) for r in refresh),
              "refresh_idempotent": not any(r["changes"] for r in refresh), "official_score": None,
              "manual_audit_note": "Review preserved exact-number quotes and source URLs; no universal wrong-company rate is claimed."}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "accepted_websites"}, indent=2))
    raise SystemExit(0 if report["refresh_idempotent"] else 1)


if __name__ == "__main__":
    main()
