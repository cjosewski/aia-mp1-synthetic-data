# M5 — corrected generator cohort

November 16, 2026. Proceed under the owner's [70% overall agreement amendment](ACCEPTANCE-AMENDMENT-70.md).
The baseline is the completed fifty-item V13 evaluation with twenty frozen human
reviews. Reassess its saved results under the amended policy; do not run a third
baseline judge version or replace V13 with V14.

## Measured target and correction

The highest baseline category/dimension judge failure rate is **AEC automation ×
D3 API realism: 4/10 failures (40%)**. The frozen human review separately identifies
parameter storage-type mistakes, confusion between elements and parameters, and
incorrect geometry/transaction API ownership. Human and judge measurements remain
separate; the judge's 33 false approvals remain a limitation of this comparison.

The [v2 generator prompt](../prompts/generator-assessed-v2.md) preserves the v1
instructions and adds one API-contract correction: explicitly check owner/member,
arguments and returned types; ensure consistent valid usage across answer, steps
and tips; place applicable guards before access; distinguish read/write transaction
requirements; preserve the supplied task givens. It does not supply human ratings,
baseline answers or corrected answer keys to generation.

Hypothesis: this correction reduces invented or misapplied APIs, especially in AEC
automation, without changing task requirements or introducing incompatible tips.
The prompt is prepared; no corrected generation or measured improvement is claimed.

## Fixed controls and execution

1. Freeze the new acceptance receipt and the original V13 judge identity. Retain
   Qwen3.5 weights, prompt, runtime settings, qualification and implementation from
   `baseline-qwen35-v13-budget4096-002`. Use its archived runtime for corrected
   judging; the acceptance/reporting amendment does not alter model inputs.
2. Generate with the original Qwen3-30B-A3B model/identity, temperature 0.6,
   4096 output tokens, two attempts/item, 120-second request timeout, original
   source pack, collection/gate/selection policy and category quotas. Only the
   generator prompt changes. Verify available runtime and model identity before
   starting; announce Mac use before any remote model operation.
3. Use new run/collection/cohort IDs and preserve every attempt. Collect fifty
   retained items, ten per category, within the existing bounded collection policy.
   Apply the existing deterministic selection and gates; do not select by scores.
4. Prepare a new blind twenty-item review packet for Chad. Freeze his authentic
   reviews before judging. This is the next necessary human task.
5. Judge all fifty corrected items with the frozen V13 judge. Evaluate both
   cohorts under `owner-overall-70-20261116`; require complete evidence and at
   least 70% overall agreement in the corrected cohort too.
6. Produce the comparison, five charts and reproducible evidence package. Report
   per-dimension agreement and false approvals alongside the overall acceptance.

## Remaining acceptance targets

The amendment changes only human/judge agreement. Preserve initial schema validity
>=95%, baseline overall failure >=15%, corrected overall pass >=80%, corrected
D1–D6 targets of 85/90/95/95/90/85%, and relative failure reduction strictly >80%.
The saved judge baseline has 18/50 overall failures. At the same corrected cohort
size, strictly >80% reduction requires at most **3/50 failures**, not merely the
ten failures allowed by the separate overall-pass floor.

No measured criterion is passed in advance. If the corrected cohort misses a
target, preserve and report it; do not silently amend another requirement. Final
demonstration and coaching/submission remain after the measured comparison.
