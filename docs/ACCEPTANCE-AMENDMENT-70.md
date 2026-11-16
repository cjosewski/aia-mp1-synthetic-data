# Owner acceptance amendment — 70% overall agreement

November 16, 2026. Chad Josewski directed:

> This can't go on. I'm changing the acceptance criteria to 70%. No instructor approval is needed.

Chad then confirmed: **"Yes. 70% overall agreement."**

The operative calibration rule is at least 70% matching human/judge criterion
ratings across all six dimensions combined. It replaces the 80%-in-each-dimension
acceptance gate for both baseline and corrected cohorts. No additional instructor
approval is required for this owner-directed project amendment. Other dataset
quality and improvement targets are unchanged.

Policy ID: `owner-overall-70-20261116`. Twenty complete human reviews require at
least 84/120 matches. This measures agreement with human ratings, not the fraction
of generated answers passing the quality rubric.

## Reassessment of saved results

| Measure | Saved baseline result | Role under the amendment |
| --- | ---: | --- |
| Combined agreement | 87/120 = 72.5% | Pass: at least 70% |
| D1 agreement | 10/20 = 50% | Reported limitation |
| D2 agreement | 17/20 = 85% | Reported limitation |
| D3 agreement | 13/20 = 65% | Reported limitation |
| D4 agreement | 18/20 = 90% | Reported limitation |
| D5 agreement | 17/20 = 85% | Reported limitation |
| D6 agreement | 12/20 = 60% | Reported limitation |

These counts come from the [completed baseline report](BASELINE-BUDGET-RESULTS.md).
All fifty items have judgments and all twenty frozen human reviews were compared.
All thirty-three disagreements are false approvals. The safety dimension misses
all three human-rated failures despite 85% agreement. These limitations remain
visible; the amendment changes acceptance, not model accuracy.

## Implementation and preservation

The `calibrate` CLI and analysis `report` CLI default to this owner policy. Use
`--acceptance-policy course-per-dimension-80-v1` to reproduce the original rule.
Python helpers retain their original default for historical callers; pass
`acceptance_policy="owner-overall-70-20261116"` for the amended rule. New receipts
record the policy, its hash, overall counts and original per-dimension verdict.
Analysis replay uses the recorded policy; old reports retain their original
behavior. Baseline and corrected comparisons must use the same policy.

The scoring rubric remains `engineering-v1`: its anchors, original threshold
metadata and frozen hash are preserved. The separate acceptance policy supersedes
only its agreement gate. Complete coverage, twenty authentic frozen reviews,
fifty balanced items, distinct qualified judge and evidence checks remain required.

Re-evaluating acceptance requires no model run. Original reports, rubric snapshots,
human labels, outputs and hashes remain unchanged. A new validated receipt records
operational readiness under the amendment. This does not claim the original course
criterion was met. The next stage is generator correction using the frozen V13
judge and its existing model/settings, followed by new authentic human review.

## Verified completion

M4 is complete under the amended policy. The new receipt is **ready**, with
87/120 matches, complete coverage and no remaining readiness reasons. No model
request or new assessed judge version was used. All sixteen existing assessment
files and seventy-nine entries in the prior baseline/V14 seals remain unchanged.
Both the original calibration and analysis reports replay successfully.

Evidence paths below are relative to workspace `artifacts/evidence/P1-03/`:

- Receipt: `assessments/baseline-review-001/calibration/baseline-qwen35-v13-owner70-003/report.json`.
- Analysis and five updated charts: `analysis/baseline-qwen35-v13-owner70-003/`.
- Verification, M5 frozen controls and seal: `qualification/owner-acceptance70-20261116/`.
- Receipt SHA-256: `5215941da49b840f01be19304288b264d2944f4ed46ab45bcec8a9c2b91a7eeb`.
- Audit seal SHA-256: `bfc080c77bdd1617b8c3edf05a68a1cf14074ae3e31b602b4bf8bc5c4e6409b6`.

Verification: **449 locked WSL tests pass**, including exact 70% boundaries,
historical replay, CLI defaults, mismatched-policy rejection and incomplete or
diagnostic evidence remaining ineligible. The analysis remains overall pending
because the corrected cohort is not yet measured; this does not reopen M4.
The [M5 plan](M5-CORRECTION-PLAN.md) and generator v2 prompt are prepared.
