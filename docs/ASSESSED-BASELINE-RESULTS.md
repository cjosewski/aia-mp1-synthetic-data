# Qwen3.5 V13 assessed baseline — interrupted result

November 15, 2026 local time (November 16 UTC). **The Mac is free:** the owned
server is stopped, its PID is gone and port 8081 has no listener. Chad's selection
of Qwen3.5 with frozen V13/settings is recorded and remains intact.

The run stopped at its predefined two-consecutive-failure boundary. It does not
establish calibration readiness. No prompt, setting, rating or attempt budget was
changed during execution.

## What happened

Three responses each consumed all 8192 completion tokens in reasoning, returned
`finish_reason: length`, and contained zero final-answer characters. They finished
in 213.3, 218.9 and 212.6 seconds, below the 300-second timeout. Increasing the
timeout alone would not address this observed output-limit failure.

`baseline-001-b01-item-0015` failed its first attempt and succeeded on its sole
retry. `baseline-001-b01-item-0028` exhausted both attempts. The next item was not
started, and the launcher released its owned server.

| Measure | Observed result |
| --- | ---: |
| Planned population | 50 |
| Items attempted | 12 |
| Valid initial judgments | 10/12 attempted items |
| Items never started | 38 |
| Complete final judgments | 11/50 |
| Request starts / recorded outcomes | 14/14 |
| Retry starts / successful recoveries | 2/1 |
| Retained incomplete responses | 3 |
| Requests with unknown outcome | 0 |
| Recorded request time | 2123.6 seconds (35.4 minutes) |

The 10/12 initial result must not be reported as 10/10 or replaced by final
retention. Coverage remains incomplete. Baseline generation's original 200/200
initial schema-valid responses are a separate, unchanged measurement.

## Partial human comparison and public explanations

Only **2 of the 20 frozen human-reviewed items** received complete judgments.
Their matching counts are D1 **1/2**, D2 **2/2**, D3 **0/2**, D4 **2/2**, D5 **2/2**,
and D6 **1/2**. These are partial observations, not full calibration rates.

- `b01-item-0013`: human D3=1, judge D3=0. The judge interprets a sentence ending
  "area=3.5 (in²) for the Truss element" as an invalid area argument to material
  creation, although no such literal API call is shown. Preserve this interpretation
  concern. D1 matches at 0, but its explanation uses that same interpretation rather
  than the human's missing explicit linkage and incomplete analysis workflow.
- `b01-item-0023`: the judge passes all six dimensions; the human fails D1/D3/D6.
  Its explanations credit listed stages, familiar API names and validation tips
  without addressing the missing analysis configuration, Tcl-style initialization,
  omitted reaction calculation and material/area error identified in the human notes.

All four disagreements, including three false approvals and one false rejection
relative to the human reference, are retained. This targeted explanation inspection
is assistant analysis, not new human scoring. No broad semantic audit of all 66
completed public justifications is claimed.

The pending report cites incomplete coverage, insufficient observed per-dimension
agreement and the incomplete judge run. The original 20 reviews remain frozen.
The ten-case confirmation errors and selection limitations also remain retained.

## Verification and retained evidence

Run: `assessments/baseline-review-001/judges/baseline-qwen35-v13-001/`.
Pending report: `assessments/baseline-review-001/calibration/baseline-qwen35-v13-agreement-001/`.
Both were imported only after verifying all original source and reference files.

- Frozen implementation: `4b01978d772db8a83317c5f5338693db9c21d014`.
- Native plan: `fa1b157fe4f0336a6eeed633597163950d878b1da8095950f7cd5e08573a1c85`.
- All **188** frozen bundle files verify against the original manifest.
- Human-reference identity remains
  `1e555ed74a0417120ac4d16052c3082e02e8e03550c3e2e09a64eda89856e4a8`.
- Return: `qualification/MP1-QWEN35-BASELINE-RETURN.zip`, SHA-256
  `bffaf6dafa763ecc0909677162b79fa23dccb6c8e585cef05f5c3adc616f2975`.
- NAS copy: `\\192.168.0.55\aia\Handoff\P1-03\operator\MP1-QWEN35-BASELINE-RETURN.zip`.
- Replay, import receipt and output metadata:
  `qualification/baseline-return-audit-20261116-v2/`.

The native ledger, raw responses, public judgments, exact source files, prompt,
runtime observations and server-release receipt are preserved. The three failures
have complete outcomes; no third attempt of the exhausted item is permitted.
The current offline suite passes 430 tests, including the proposed probe's approval
and server-ownership checks; these tests are not additional model measurements.

The offline analysis `analysis/baseline-qwen35-v13-partial-001/` records the same
pending state, with five charts and their CSV tables. Plots explicitly say
"PRELIMINARY — INCOMPLETE", show the observed sample sizes and leave corrected
measurements as NA. Report identity:
`b31f66c584319006262029a21011c6c7c152993bd59c256d6cb9e7da26706f4e`.

## Next decision

The installed pinned runtime documents an explicit thinking-token budget. A
[two-case probe](REASONING-BUDGET-PROBE.md#measured-result) was subsequently
approved and completed both cases on their first attempt with a 4096 thinking cap.
It retains the 8192 total allowance and V13 prompt. A
[new full-run runtime amendment](BASELINE-BUDGET-AMENDMENT.md) was subsequently
approved and [completed](BASELINE-BUDGET-RESULTS.md). That run delivers 50/50 valid
first attempts but fails three agreement thresholds. Neither later run replaces
this interrupted record or its retained failures.
