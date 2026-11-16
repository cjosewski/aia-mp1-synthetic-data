# Proposed 4096-thinking-token assessed baseline revision

**Status: owner approved; preparing the frozen execution package.** Chad replied
"Approved." to the proposal for the new 50-item calibration with the same 4096 cap.

The [approved two-case probe](REASONING-BUDGET-PROBE.md#measured-result) returned
two valid first attempts. It supports trying the same thinking cap in a new full
calibration. It does not establish full-cohort accuracy or erase the interrupted run.

## Exact revision

| Setting or boundary | Proposed value |
| --- | --- |
| Assessment | Existing frozen `baseline-review-001`, all 50 items |
| Human reference | Existing original 20 reviews; no edits or new labels |
| Model and weights | Same selected Qwen3.5-122B-A10B Q4_K_M, same verified hashes |
| Prompt and input messages | Frozen V13 and the original 50 messages, unchanged |
| Runtime change | Explicit `--reasoning-budget 4096`, replacing unrestricted thinking |
| Other runtime settings | Same pinned build, context 16384, one slot, reasoning on, deepseek format |
| Request settings | JSON mode, temperature 0.1, output maximum 8192, timeout 300 seconds |
| New judge identity | `baseline-qwen35-v13-budget4096-002` |
| New report identity | `baseline-qwen35-v13-budget4096-agreement-002` |
| Attempt budget | Two per item, at most 100 total; stop after two consecutive unsuccessful responses |
| Assessed version budget | Second of the existing maximum of three versions |
| Readiness | All 50 judgments complete, at least 16/20 human matches in each of D1–D6, all original eligibility checks |

Judge all 50 items anew under the amended runtime. Do not merge the old eleven
valid judgments or the two probe judgments into this version. Preserve the old
run's fourteen attempts, three token-limit failures, partial disagreement report
and all prior confirmation errors.

An attributed runtime amendment must bind this setting, the probe evidence and
the selected-model receipt. Freeze the new configuration, implementation and
full provenance package before inference. Verify the actual owned server command
and its 4096 budget before each start; retain bounded retries and unknown outcomes.
Report identifiers must be distinct from the original pending report.

The original 56/60 confirmation result describes the earlier unrestricted
configuration. The limited-thinking probe supplies only two known-case completion
observations, with one known human-rated item. The new full run must measure its
own agreement; no accuracy transfer from the earlier configuration is assumed.

## Owner decision

The earlier approval covered only the two-case probe. Chad has now explicitly
approved applying the changed runtime to all fifty assessed items. The attributed
receipt is `qualification/baseline-budget4096-owner-amendment.json`; the exact reply
is preserved separately from its recorded scope. No further approval is needed for
this bounded run.

Approved proposal:

> Approve a new 50-item assessed baseline calibration with Qwen3.5, frozen V13 and a 4096 thinking-token cap, under the existing two-attempt-per-item budget. Preserve all earlier runs, errors and human ratings.

Mac use has been announced. The package will bind the amended qualification,
implementation, new run/report IDs and every frozen input before inference.
