# Qwen3.5 V13 baseline with a 4096 thinking-token cap

November 16, 2026. **Execution completed; calibration failed. The Mac is free.**
All fifty judgments arrived on their first attempt. The owned server stopped,
its PID was absent and port 8081 had no listener. Herd was not changed.

The [approved runtime amendment](BASELINE-BUDGET-AMENDMENT.md) kept the V13 prompt,
model weights, original fifty-item cohort and twenty frozen human reviews intact.
The thinking cap addressed completion in this run, but did not establish rating
accuracy. The earlier interrupted run and its three token-limit failures remain
unchanged; this is a separate second assessed version.

## Full human comparison

Every dimension needs at least 16/20 matches. All twenty selected human reviews
were compared; none are missing. A false approval means human=0 and judge=1.

| Dimension | Matches | Agreement | False approvals | Threshold met |
| --- | ---: | ---: | ---: | --- |
| D1 — Completeness | 10/20 | 50% | 10 | No |
| D2 — Safety | 17/20 | 85% | 3 | Yes |
| D3 — API realism | 13/20 | 65% | 7 | No |
| D4 — Scope | 18/20 | 90% | 2 | Yes |
| D5 — Context | 17/20 | 85% | 3 | Yes |
| D6 — Tips | 12/20 | 60% | 8 | No |
| **Total** | **87/120** | **72.5%** | **33** | **Calibration not ready** |

There were no false rejections. The judge detected only 13 of the 46 human-rated
failures. D2 illustrates why agreement alone needs context: the judge approved
every reviewed item's safety dimension, missing all three human-identified safety
failures despite 85% agreement. The original human result remains 74/120 passing
criteria and four all-six passes; those are answer-quality measures, not agreement.

The calibration report's status is `pending`, with the sole readiness reason
`per_dimension_agreement_not_met`. Coverage and eligibility checks passed.
M4 remains incomplete; this judge must not be used as a calibrated basis for M5.

## Public-explanation findings

The audit inspected the candidate, task brief, frozen human record and all six
public justifications for each human-paired item: twenty items and 120 explanations.
It did not independently audit the remaining thirty population items, execute
generated code or perform a new external API review. It creates no human labels.

- **Completeness:** named stages or a reported result were often credited without
  checking essential implementation details or the supplied analytical formula.
  Examples include the Mark update, CRS preservation and cooling result.
- **API realism:** explanations often listed familiar API names without checking
  owners, arguments or return types. The cone constructor, Revit parameter access
  and tuple/spatial-reference usage retain the defects identified in human notes.
- **Safety and tips:** useful-looking precautions or tips sometimes masked a
  contradictory instruction elsewhere. The unknown-CRS WGS84 recommendation and
  null parameter access were approved. Invalid transaction and inspection tips
  were also overlooked.
- **Matching decisions can still have weak explanations:** some matched failures
  use a different basis from the human review; some matched passes credit a
  questionable instruction. The detailed audit retains these limitations.
- **D4 interpretation:** the human failed two substituted mathematical problems
  for scope, while the frozen rubric and V13 define D4 around professional review
  or sign-off. The judge caught the substitutions in D1/D5 but passed D4. Preserve
  this difference rather than silently changing the rubric or human ratings.

## Execution and evidence

| Measure | Observed result |
| --- | ---: |
| Planned / complete judgments | 50/50 |
| Valid first attempts / initial slots | 50/50 |
| Starts / recorded outcomes | 50/50 |
| Retries / failures / unknown outcomes | 0 / 0 / 0 |
| Recorded request time | 5672.7 seconds, 94.5 minutes |
| Request duration range | 86.3–118.6 seconds |
| Completion tokens | 222,615 total; 3,363–4,624 per request |
| Final finish reasons | 50 `stop` |

All **206 frozen files** matched the original bundle. Runtime preflight verified
the weights, all fifty token reservations and the owned 4096-cap command. The
calibration replay matched the returned report. Every original canonical input
was checked before importing only the new judge/report directories. Four interim
inspection snapshots matched exact prefixes of the final ledger.

Evidence paths below are relative to workspace `artifacts/evidence/P1-03/`:

- Judge: `assessments/baseline-review-001/judges/baseline-qwen35-v13-budget4096-002/`.
- Calibration: `assessments/baseline-review-001/calibration/baseline-qwen35-v13-budget4096-agreement-002/`.
- Audit: `qualification/budgeted-baseline-audit-20261116/`, including replay,
  import receipt, execution summary and detailed semantic review.
- Return: `qualification/MP1-QWEN35-BASELINE-B4096-RETURN.zip`, SHA-256
  `d18d32459a5b17d3215653788e9fd2fb399c3126ab6e3bbec9f8bfe16287522a`.
- Human-reference identity, unchanged:
  `1e555ed74a0417120ac4d16052c3082e02e8e03550c3e2e09a64eda89856e4a8`.
- Frozen implementation: `43d35918193c677538a3f31244625423fb1debd9`.
- Native plan: `44e980f3bf4424c30b15ec412a0915a24433bc47849fb7a11857685f3d907100`.

The verified NAS return is under
`\\192.168.0.55\aia\Handoff\P1-03\operator\MP1-QWEN35-BASELINE-B4096-RETURN.zip`.
Raw evidence remains excluded from Git. The implementation checkpoint passed
435 locked WSL tests before inference; no code changed during the run.

The offline analysis `analysis/baseline-qwen35-v13-budget4096-002/` contains five
PNG charts, five SVGs and five CSV tables. Report identity:
`0011eb4d764e34d0c2a96d36d51cc527a2cb86a91cb542dc18eae82957f779de`.
The charts retain the preliminary/incomplete comparison label because calibration
failed and no corrected cohort exists; baseline judgment coverage itself is complete.
Corrected measurements remain NA.

This uncalibrated judge reports 32/50 all-six passes in the population, with
dimension pass counts 41, 50, 40, 49, 47 and 46. These are retained model outputs,
not accepted population-quality evidence or permission to proceed with correction.
The baseline generator's 200/200 initial schema-valid responses are unchanged.

## Next step

[The concrete V14 proposal](JUDGE-V14-PROPOSAL.md) and complete draft prompt address
the observed claim-checking failures without changing the rubric or human labels.
It proposes a bounded comparison on the ten existing confirmation cases, now
explicitly treated as known development data, with a matched capped V13 control.
It does not consume the one remaining assessed version or claim fresh validation.

Chad subsequently approved that comparison. Its [complete result](JUDGE-V14-RESULTS.md)
is 55/60 for V14 versus 56/60 for the capped V13 control, with one improvement and
two regressions, including a new safety false approval. V14 does not advance.
No third assessed version has started, and the original baseline result is unchanged.
