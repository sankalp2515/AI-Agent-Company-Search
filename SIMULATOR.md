# Local evaluation harness — not the official evaluator

Current official contract, checked 5 October 2026: 50 coverage, 30 precision/evidence, 12 synthesis, 8 UX; qualification 65/100 on an official valid run. The older Unstop 35/30/20/10/5 weighting and 21/35 gate conflict with the current organizer page. The latter explicitly says no separate dimension thresholds. Its board header still says 1,000+ profiles, but the detailed submission section explicitly says a 100-company smoke report and no precomputed profile manifest. Obtain written organizer confirmation if Unstop controls registration requirements separately.

The supplied 45-minute, 2,000-request and $10 limits are a legacy stress-test scenario, NOT confirmed current official limits. CLI budgets are configurable. A current shared run may exceed 1,000 companies. A local score cannot predict the hidden checked union or reproduce unavailable official family weights/rubrics.

## What is implemented

- Exact batch membership/order and one terminal envelope per input, including exhausted-budget cases.
- Six availability states, non-empty claim evidence, source/date/locator/reporting-period checks and immutable snapshot SHA validation.
- Declared runtime/request gate checks.
- Optional local coverage formula: 70% positive-company recall + 30% individual-fact recall within each locally weighted family.
- Optional precision proxy only after every publication is independently reviewed. Unmatched reference claims do not automatically make extra discoveries false.
- Material wrong-company and fabricated-financial review flags block local qualification estimates.
- Manual reviewed synthesis/UX scores, never awarded merely because UI or summaries exist.
- Refresh/idempotence and model/search failure fixtures in pytest; saved-source replay preserves actual old dates.

## Independent reference schema

```json
{
  "reviewed_by": "Independent reviewer name",
  "reviewed_at": "ACTUAL_TIMESTAMP",
  "provenance": "Describe sources, snapshots, sampling and review methodology",
  "family_weights": {"description": 1, "jobs": 1, "activity": 1},
  "claims": [
    {"organisation_number": "123456789", "field": "description", "value": "Exact normalized reviewed fact", "reporting_period": null}
  ],
  "publication_reviews": [
    {"claim_id": "actual_output_claim_id", "correct": true, "evidence_valid": true, "right_company": true, "material_wrong_company": false, "fabricated_financial_value": false}
  ],
  "manual_scores": {"synthesis": 0, "ux": 0}
}
```

The example has no real labels and is not a valid benchmark. Do not generate ground truth from the same agent outputs and call that independent verification. Coverage currently matches exact normalized field/value/period tuples; paraphrase/semantic equivalence requires human normalization. One field family with no positives is omitted rather than assigned arbitrary zero recall. Tiny references are poor predictors and must be reported as such.

Official ranking averages scheduled daily tests and has infrastructure rerun exceptions. This implementation evaluates one local run; it does not reproduce organizer scheduling, shared-union construction or official daily ranking. No local pass authorizes a prize claim. The separate JBOX bonus requires a qualifying JBOX-built agent; this Python agent currently does not claim JBOX eligibility.
