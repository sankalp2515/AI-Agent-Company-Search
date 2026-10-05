"""Honest local approximation. Hidden labels, field weights and evaluator are unavailable."""
import json

from .core import validate


def fact_key(org, claim):
    return json.dumps([org, claim["field"], claim["value"], claim.get("reporting_period")], sort_keys=True, ensure_ascii=False)


def daily_average(batches):
    """Local ranking arithmetic only; infrastructure cause must be independently reviewed."""
    scores = []
    for batch in batches:
        if batch.get("void_infrastructure_failure"):
            continue
        if batch.get("entrant_failure_after_clean_rerun"):
            scores.append(0)
        elif isinstance(batch.get("reviewed_score"), (int, float)) and 0 <= batch["reviewed_score"] <= 100:
            scores.append(batch["reviewed_score"])
        else:
            raise ValueError("Every nonvoid daily batch requires reviewed score or reproduced entrant failure")
    return {"local_daily_mean": sum(scores) / len(scores) if scores else None, "counted_batches": len(scores),
            "note": "Arithmetic approximation; no official scheduler, reference union or tie-break adjudication"}


def simulate_run(rows, orgs, snapshots, report, reference=None):
    structural = validate(rows, orgs, snapshots)
    gates = {"complete_outputs_and_evidence_structure": structural["passed"],
             "within_declared_request_budget": report["requests"] <= report["limits"]["requests"],
             "within_declared_time_budget": report["runtime_seconds"] <= report["limits"]["seconds"]}
    result = {"kind": "local_simulator_not_official_score", "operational_gates": gates,
              "operational_gates_passed": all(gates.values()), "structural_errors": structural["errors"],
              "official_qualification": "not_determined", "overall_score": None,
              "unverified": ["semantic evidence correctness", "exact-company attribution", "hidden reference recall",
                             "official field weights", "manual synthesis and UX review", "official budgets and billing"],
              "components": {"coverage_out_of_50": None, "precision_out_of_30": None,
                             "synthesis_out_of_12": None, "ux_out_of_8": None}}
    if not reference:
        result["note"] = "No independently reviewed reference; scores intentionally withheld. Structural validity is not precision."
        return result
    if not reference.get("reviewed_by") or not reference.get("reviewed_at") or not reference.get("provenance"):
        raise ValueError("Reference needs independent reviewer, date and provenance")
    families = reference.get("family_weights", {})
    if not families or any(not isinstance(v, (int, float)) or v <= 0 for v in families.values()):
        raise ValueError("Explicit positive local family weights required")
    if any(c.get("organisation_number") not in orgs for c in reference.get("claims", [])):
        raise ValueError("Reference contains company outside this input batch")
    found = {fact_key(r["organisation_number"], c) for r in rows for c in r["claims"]}
    per_family = {}
    for family, weight in families.items():
        refs = [c for c in reference.get("claims", []) if c["field"] == family or c["field"].startswith(family + ".")]
        keys = {fact_key(c["organisation_number"], c) for c in refs}
        positive_companies = {c["organisation_number"] for c in refs}
        covered = {c["organisation_number"] for c in refs if fact_key(c["organisation_number"], c) in found}
        matched = len(keys & found)
        recall = .7 * len(covered) / len(positive_companies) + .3 * matched / len(keys) if keys else None
        per_family[family] = {"company_recall": len(covered) / len(positive_companies) if positive_companies else None,
                              "claim_recall": matched / len(keys) if keys else None, "weighted_recall": recall, "weight": weight}
    measured = [v for v in per_family.values() if v["weighted_recall"] is not None]
    if measured:
        result["components"]["coverage_out_of_50"] = round(50 * sum(v["weighted_recall"] * v["weight"] for v in measured) / sum(v["weight"] for v in measured), 3)
    result["local_reference_coverage"] = per_family
    reviews = reference.get("publication_reviews", [])
    current_ids = {c["id"] for r in rows for c in r["claims"]}
    reviewed = {p["claim_id"] for p in reviews}
    if reviews and current_ids == reviewed and len(reviews) == len(reviewed):
        correct = sum(p.get("correct") is True and p.get("evidence_valid") is True and p.get("right_company") is True for p in reviews)
        result["components"]["precision_out_of_30"] = round(30 * correct / len(reviews), 3)
    violations = [p["claim_id"] for p in reviews if p.get("material_wrong_company") or p.get("fabricated_financial_value")]
    result["reviewed_integrity_violations"] = violations
    result["independent_review_complete"] = current_ids == reviewed
    for label, cap in (("synthesis", 12), ("ux", 8)):
        value = reference.get("manual_scores", {}).get(label)
        if value is not None:
            if not isinstance(value, (int, float)) or not 0 <= value <= cap:
                raise ValueError("Manual score outside component range")
            result["components"][f"{label}_out_of_{cap}"] = value
    if all(v is not None for v in result["components"].values()):
        result["overall_score"] = round(sum(result["components"].values()), 3)
        result["local_only_qualification_estimate"] = result["overall_score"] >= 65 and all(gates.values()) and not violations
    result["note"] = "User-reviewed local labels and weights, not Builderr labels. Unlisted facts are unreviewed, not automatically wrong."
    return result
