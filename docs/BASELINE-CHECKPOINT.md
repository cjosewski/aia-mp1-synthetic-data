# Assessed baseline ready for human review — November 10, 2026

Collection `baseline-001` completed successfully under the approved policy.
The frozen cohort `baseline-cohort-001` contains 50 items, exactly ten per
category. Assessment `baseline-review-001` selects 20 items, four per category,
with zero human labels and zero assessed judge runs. Chad's next action is
[the blind review in runbook Step 6](ASSESSED-RUNBOOK.md#6-complete-the-20-blind-human-reviews).
The collection and queue already exist; do not recreate them.

## Observed collection results

| Batch | Initial responses schema-valid | Passed batch heuristic screening |
| --- | ---: | ---: |
| baseline-001-b01 | 50/50 | 23 |
| baseline-001-b02 | 50/50 | 24 |
| baseline-001-b03 | 50/50 | 27 |
| baseline-001-b04 | 50/50 | 24 |
| Total | 200/200 (100%) | 98 |

The collector stopped after four of the permitted five batches. It made 200
generation requests, with no retries, unresolved requests or reported model
mismatches. The approved prompt, reference pack, model, settings, gate rules and
category targets remained fixed throughout.

Across all candidates, 102 items have a D2 heuristic rejection reason, nine have
a cross-batch duplicate reason, and 45 are eligible quota surplus. Rejection
reasons overlap: six duplicate items also have D2 failures. Consequently, 105
items were excluded for rejection/duplication, 45 were surplus and 50 entered
the cohort. All attempts and decisions remain saved, including surplus.

These D2 checks detect particular hazard/precaution terms. They are screening
results, not human safety scores or the assignment's six-dimensional baseline
failure rate. Human review and qualified judging remain unmeasured. This
checkpoint does not claim M3/M4 completion, calibration success or instructor
acceptance of adaptations.

## Reproducibility and evidence

Source-use approval and scope are recorded in
[REFERENCE-PACK-REVIEW.md](REFERENCE-PACK-REVIEW.md). Generator identity,
full-file checksum, exact upstream revision and runtime preflight are described
in [SOURCE-READINESS.md](SOURCE-READINESS.md). The original 17 diagnostic files
and the reviewed source draft were verified unchanged.

The fresh WSL verification passed 185 tests, Ruff checks, format checks and CLI
help checks. The 64-token diagnostic JSON probe failed by exhausting its cap
during reasoning; the second probe passed with the approved 4,096-token cap.
Both probes are retained and excluded from the 200 assessed requests.

Raw evidence is outside Git under workspace `artifacts/evidence/P1-03/`:

- `baseline-preflight-20261110/`: approval/config/weight checks, runtime
  properties, probe attempts, offline verification, collection verification,
  cohort/assessment receipts and `handoff.json`.
- `references/engineering-v1.json` and `engineering-v1-approval.json`: approved
  source pack and actual owner decision; the preparation draft remains separate.
- `baseline-001-b01/` through `baseline-001-b04/`: immutable attempts, data,
  source contexts and batch gates.
- `collections/baseline-001/`: frozen collection inputs and bounded membership.
- `cohorts/baseline-cohort-001/`: frozen balanced cohort.
- `assessments/baseline-review-001/`: frozen population/selection and empty
  human-label ledger ready for Chad's actual reviews.

Cohort SHA-256:
`3a269db978112a7aa993ecc07d46f3774853157a7ec8558b40884ad9da454741`.
Assessment manifest SHA-256:
`dd0cfe746464e441ce42f1dfd706af7b65e10a2c3b8b2b304709b877a4f06932`.

After 20 authentic blind reviews, Chad declares and freezes the reference using
runbook Step 7. A distinct stronger judge still needs selection and qualification
before assessed judging. No judge output has been produced for this cohort.
