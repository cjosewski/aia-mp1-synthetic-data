# Proposed 4096-thinking-token assessed baseline revision

**Status: prepared decision record; approval and execution pending.**

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

The latest approval covered the two-case probe, capped at four requests. Applying
the changed runtime to all fifty assessed items needs an explicit amendment to the
earlier frozen-settings selection. This comes from the scope of Chad's instructions,
not a skill requirement.

Proposed approval text:

> Approve a new 50-item assessed baseline calibration with Qwen3.5, frozen V13 and a 4096 thinking-token cap, under the existing two-attempt-per-item budget. Preserve all earlier runs, errors and human ratings.

The Mac is free. Codex will announce its use before an approved full run. No full
run has been started, and no approval receipt for this amendment has been created.
