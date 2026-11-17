# Final V15 original-baseline result

November 17, 2026. **All fifty judgments completed; calibration failed. The Mac
is free.** V15 matches **95/120 ratings (79.2%)**, compared with V13's 87/120
(72.5%) on the same twenty frozen human reviews. D1 is **70%** and D6 **65%**;
both fail the restored **80% in every dimension** requirement. M4 remains open.

The [final allocation](V15-BASELINE-PLAN.md) used frozen V15, the selected
Qwen3.5-122B-A10B weights, the 4096 reasoning cap and the original fifty-item
baseline. No human rating, answer, rubric or threshold changed. The replacement
package used local port **18083**, forwarding to the owned Mac server on **8081**.
The priority Herd workload on 18081 was left untouched. The earlier zero-request
preflight interruption remains separately archived.

## Same-reference comparison

Each dimension needs at least 16/20 matches. All twenty human reviews and all
fifty population judgments are present. False approval means human=0, judge=1;
false rejection means human=1, judge=0.

| Dimension | V13 matches | V15 matches | V15 agreement | False approvals | False rejections | Meets 80% |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| D1 — Completeness | 10/20 | 14/20 | 70% | 6 | 0 | No |
| D2 — Safety | 17/20 | 17/20 | 85% | 3 | 0 | Yes |
| D3 — API realism | 13/20 | 16/20 | 80% | 3 | 1 | Yes |
| D4 — Scope | 18/20 | 18/20 | 90% | 2 | 0 | Yes |
| D5 — Context | 17/20 | 17/20 | 85% | 3 | 0 | Yes |
| D6 — Tips | 12/20 | 13/20 | 65% | 7 | 0 | No |
| **Total** | **87/120** | **95/120** | **79.2%** | **24** | **1** | **Not ready** |

Nine gained matches and one regression produce eight net matches, **+6.67
percentage points**. The judge detects 22/46 human-rated failures, versus V13's
13/46. It still misses **all three safety failures**, despite D2's passing
agreement percentage. The unchanged human answer-quality result is 74/120
passing criteria and four all-six passing items; that is a different metric.

The calibration report is `pending`, solely because
`per_dimension_agreement_not_met`. Complete coverage and eligibility passed.
The [discrepancy record](AGREEMENT-DISCREPANCY-20261117.md) now contains the direct
transfer result: exposed development 96.7% and fresh authored confirmation 93.3%
did **not** transfer to the original assessed baseline. Those smaller samples
remain separately labeled; neither replaces this 79.2% result or the saved V13
72.5% result.

## Explanation audit

All twenty human-paired answers and 120 V15 public explanations were inspected
against their tasks, frozen human records and V13 explanations. This does not
independently certify the other thirty population answers or execute engineering
code. One focused external Revit documentation check is identified in the local
audit; it did not change model inputs or labels.

- Grounded gains include the cooling temperature, curved-wall length, several
  API owner/type mismatches and the incorrect Mark-update tips.
- Two gained D1 matches have incorrect explanations. One misreads the Truss area
  assignment; another invents a claim that `Parameter.HasValue` does not exist.
  Autodesk documents that property in its [current API reference](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/2761a43b-3199-bbbb-6e6d-8ffd82febdec.htm)
  (assembly 26.4, not the pinned 2025 assembly). The frozen human finding concerns
  missing null handling. The audit retains the version limitation and the
  [2025 storage/accessor documentation](https://help.autodesk.com/cloudhelp/2025/ENU/Revit-API/files/Revit_API_Developers_Guide/Basic_Interaction_with_Revit_Elements/Parameters/Revit_API_Revit_API_Developers_Guide_Basic_Interaction_with_Revit_Elements_Parameters_Parameter_html.html).
- The single new false rejection is D3 on the Elastic material/Truss example,
  caused by misreading area as a material argument.
- Completeness still credits named stages without essential operations. Tips
  still receive credit when useful advice accompanies invalid advice. The Mark
  judgment explicitly excludes tip defects from D3 despite V15 saying to check
  tips there. These failures persist despite explicit prompt instructions.
- The two D4 disagreements remain an interpretation difference: the human labels
  task substitution as a scope failure, while the frozen D4 anchor and judge
  address professional review/sign-off. Neither side was silently rewritten.

## Execution and preservation

| Measure | Verified result |
| --- | ---: |
| Complete population / human comparisons | 50/50 / 20/20 |
| Valid first attempts / starts / outcomes | 50 / 50 / 50 |
| Retries / failed requests / unknown outcomes | 0 / 0 / 0 |
| Recorded request time | 5,311.27 seconds (88.52 minutes) |
| Request duration range | 39.62–116.67 seconds |
| Completion tokens / finish reasons | 209,729 / 50 `stop` |
| Cumulative recorded starts | 388 |
| Frozen package files verified | 244 |
| Earlier sealed entries verified unchanged | 990 |

The saved calibration and analysis replay exactly. Original canonical inputs
were checked before importing only the new judge, calibration and analysis
directories. The owned launcher exited successfully; server PID 22405 was absent,
Mac port 8081 was clear and the local 18083 tunnel had closed. No Herd service or
setting changed. The executing implementation passed **499 locked WSL tests**
before inference; no executing code changed during the run. Intentional offline
serialization messages in the client log are mock transport checks, not live
failed requests; the durable ledger accounts for every actual request.

The new baseline-only analysis contains five PNGs, five SVGs and five CSV tables.
Its incomplete banner concerns calibration and the unfinished comparison, not
missing baseline judgments. No corrected cohort is included in this report;
the existing corrected cohort remains preserved separately. Corrected quality,
agreement and relative failure reduction remain unmeasured.

The uncalibrated judge reports 23/50 population all-six passes and dimension pass
counts 33,49,35,50,46,40. Its worst segment remains AEC automation × D3, 6/10
failures, tied with AEC × D6 and selected by the declared tie-break order. This
matches the existing M5 correction's target but does not qualify the judge or
establish generator improvement.

## Evidence and next boundary

Paths are relative to workspace `artifacts/evidence/P1-03/`, outside Git:

- Judge: `assessments/baseline-review-001/judges/baseline-qwen35-v15-budget4096-003/`.
- Calibration: `assessments/baseline-review-001/calibration/baseline-qwen35-v15-budget4096-agreement-003/`.
- Analysis: `analysis/baseline-qwen35-v15-budget4096-003/`.
- Audit: `qualification/v15-baseline-audit-20261117/`, including all twenty public
  reviews, exact replay, paired changes, import receipt and preservation seal.
- Complete archive: `qualification/MP1-QWEN35-V15-BASELINE-003R1-COMPLETE.zip`;
  294 archived files, 315 sealed entries including the canonical import.
- Archive SHA-256: `97c47bd9bc59706e0ab89677bca9cf776d6666067c189a57c194aee2cc3b5cff`.
- Analysis SHA-256: `b5f97c70a395502c41043321baef0985e3b8455ef7de56bd5568a4f4d19d1ca7`.
- Frozen implementation: `54921e666ce9f6ed6049f61f56bdc14089cb09f6`.
- Plan SHA-256: `bb7ac51aba443803b798b77e3b4c8f67f1fc5eb013f5b67d0ad09d05ffc60066`.
- Unchanged human reference: `1e555ed74a0417120ac4d16052c3082e02e8e03550c3e2e09a64eda89856e4a8`.

The complete ZIP is checksum-verified on the NAS under
`\\192.168.0.55\aia\Handoff\P1-03\operator\`.

This closes the third and final allocated assessed run, **not P1-03**. M4 remains
open. Another wording-only rerun is not supported by these findings. A different
judge or verification protocol needs a concrete new bounded plan before further
assessed inference; the existing plan explicitly disallows an automatic fourth
version. Preserve the original 80%-per-dimension criterion and all human reviews.
The twenty M5 reviews can wait while judge calibration is unresolved. Final
comparison, demo and coaching acceptance remain outstanding.
