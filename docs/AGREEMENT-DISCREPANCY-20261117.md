# Agreement discrepancy: assessed baseline versus V15 development

Recorded November 17, 2026, after Chad raised this concern:

> I think it's important to log the discrpency. The previous test logged 74%. Not it's > 90%.

**Disposition: the apparent increase is not a measured full-baseline improvement.**
The saved assessed report records **72.5% agreement**, and the V15 development
report records **96.7% agreement on a different, smaller, exposed set**. The gap
must remain visible in project reporting. V15 has not been measured on the full
assessed baseline; M4 remains open.

## Reconciled measurements

| Measurement | Items with human comparison | Matching ratings | D1–D6 agreement | Interpretation |
| --- | ---: | ---: | --- | --- |
| November 16 assessed baseline, Qwen3.5/V13 | 20 selected from a fifty-item judged cohort | 87/120 = **72.5%** | 50%, 85%, 65%, 90%, 85%, 60% | Fails original criterion in D1, D3 and D6 |
| November 17 development, matched Qwen3.5/V13 control | 10 previously reviewed authored challenge examples | 57/60 = **95%** | 90%, 100%, 100%, 100%, 80%, 100% | Same prompt version as the assessed baseline, different examples/reference |
| November 17 development, Qwen3.5/V15 | The same 10 development examples as the control | 58/60 = **96.7%** | 90%, 100%, 90%, 100%, 100%, 100% | Development screen only; two false rejections retained |

The exact **74%** recalled in the concern was not found in the checked baseline
and development reports or the repository's results summaries. The frozen human
baseline review separately records **74 passing ratings out of 120 (61.7%)**;
that is answer quality, not human/judge agreement. This is a possible source of
numerical confusion, not an assertion about which earlier display Chad saw.
The original concern is retained above rather than silently rewritten.

## What the comparison does and does not establish

The two V15-experiment arms are directly paired: identical ten examples, frozen
human reference, user messages, model weights and runtime/settings; only the
judge prompt differs. The measured gain is **1/60, or 1.67 percentage points**:
three improvements offset by two regressions. The regressions falsely reject a
valid Revit transaction attribute in D1 and D3. No error was removed from the
denominator to obtain the higher score.

The assessed-to-development difference is **24.17 percentage points**, but it is
not an estimate of prompt improvement. V13 already reaches 95% on the development
set without the V15 prompt. Changing the examples and human reference changes
what is measured. The assessed examples are generated cohort items; the small
development set consists of authored challenges that have been reused during
prompt development. The six ratings for an item are also related judgments, not
six independent test items.

These observations identify a comparison limitation, not a complete causal
explanation. Differences in case difficulty, error patterns, human/rubric
interpretation, repeated development exposure and model sampling may contribute.
Their individual contributions have not been isolated. Reuse creates a risk of
overfitting to the development examples even though human labels and prior
judgments were excluded from model requests. The matched control also varied
between runs: 56/60 in the V14 experiment and 57/60 in the V15 experiment.
A single paired result does not establish a reliable general improvement.

The model identity and recorded numerical settings remain pinned; the V15
experiment used a WSL client through an SSH tunnel to the owned native Mac
server. These controls improve traceability but do not make different datasets
interchangeable. The rubric and frozen human ratings were not changed to raise
agreement. Changing the acceptance threshold affects the pass/fail decision,
not any measured percentage.

## Required follow-through

1. Keep **72.5% assessed baseline** and **96.7% exposed development** separately
   labeled in summaries. Do not present them as a before/after improvement pair.
2. Freeze Chad's ten new blind confirmation reviews before either comparison
   model receives those examples. Report all outcomes and limitations; the new
   authored challenge set is still not a substitute for assessed calibration.
3. If confirmation supports selection, freeze V15 and its settings before the
   remaining assessed run. Score the original fifty-item baseline and compare
   against the same twenty frozen human reviews. Report paired V13/V15 changes,
   per-dimension counts, false approvals/rejections and public-explanation issues.
4. Require at least **16/20 agreements in every dimension**, plus complete
   eligible coverage. A high pooled percentage cannot hide a failing dimension.
   Preserve a failed result if the development score does not transfer.

The measurement distinction is reconciled; transfer of V15 performance to the
assessed baseline remains **unverified**. No additional inference, changed human
rating or revised review-packet content is part of this documentation update.

## Evidence

- [Assessed baseline result](BASELINE-BUDGET-RESULTS.md): raw calibration report
  `assessments/baseline-review-001/calibration/baseline-qwen35-v13-budget4096-agreement-002/report.json`.
- [V15 development result](JUDGE-V15-RESULTS.md): raw paired report
  `qualification/MP1-QWEN35-V15-20261117/results/report.json`.
- [V14 comparison](JUDGE-V14-RESULTS.md) retains the preceding V13 control result.
- [Restored acceptance rule](ACCEPTANCE-RESTORED-80.md) retains the historical
  amendment without changing measured results.

Raw paths are relative to workspace `artifacts/evidence/P1-03/`, outside Git.
The dated discrepancy verification receipt records the source-file hashes and
recomputed counts under `qualification/agreement-discrepancy-20261117/`.
