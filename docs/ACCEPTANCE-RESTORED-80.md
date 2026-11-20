# Original calibration criterion restored — November 17, 2026

Chad directed: "The orign 80% in every dimension. Let's try to get it there."
This supersedes the November 16 70%-overall operational amendment. The current
criterion is again **at least 80% agreement separately in D1, D2, D3, D4, D5 and
D6**, with complete coverage and the existing cohort/review requirements.

Use the existing policy `course-per-dimension-80-v1`. New calibration and analysis
CLI reports default to this policy. The historical owner policy remains available
explicitly to replay earlier evidence; no saved result, rubric, human label or
prompt is overwritten. This decision restores the original rule, not a new scoring
rubric. Other dataset-quality and improvement thresholds are unchanged.

The saved baseline remains 10, 17, 13, 18, 17 and 12 matches out of twenty. D1 needs
six additional matches, D3 three and D6 four, without losing the other dimensions'
thresholds. **M4 is reopened.** Its earlier completion was under the now-superseded
owner policy. The corrected fifty-item cohort and blank twenty-item review packet
remain preserved; they do not establish quality improvement or calibrated judging.

## Authorized next attempt

The owner authorized trying to restore the original standard. Execute one bounded
[V15 development comparison](JUDGE-V15-PLAN.md), within the existing local-only,
immutable-evidence and authentic-review constraints. This instruction permits the
new development attempt without repeating the earlier approval question.

The last full assessed-baseline version remains unused during development. Do not
spend it on a failed development candidate. A successful screen requires semantic
audit and fresh independent confirmation before a revised judge is frozen for
both baseline and corrected evaluation. Human reference ratings cannot be supplied
to model requests or changed to improve agreement.

Requalifying a judge may change the worst baseline segment. Recheck the M5 target
against that measured baseline before claiming the existing correction fulfills
Phase B; retain the completed collection even if another correction is needed.

## Verification checkpoint

All **468 locked WSL tests pass**, including restored CLI defaults, per-dimension
boundary checks, historical owner-policy replay, paired request isolation, bounded
failures and remote process-ownership checks. Ruff and shell syntax checks pass.
The saved results were reassessed without inference in new receipt
`assessments/baseline-review-001/calibration/baseline-qwen35-v13-restored80-004/report.json`.
It is `pending`, solely for `per_dimension_agreement_not_met`. Raw evidence remains
outside Git; the prior receipt is not rewritten.

## Superseded for completion: November 20, 2026

Chad reported that the instructor approved completing MP1 without a calibrated judge. Before/after is measured on his blind human reviews under the new AEC rubric, and LLM judges are reported descriptively. The 80%-per-dimension criterion above therefore no longer gates completion. It and every measured result remain the historical record. M4 is recorded as not met under this criterion.
