# Proposed V14 claim-checking comparison

**Status: draft for owner review; no V14 model calls authorized or executed.**
This proposal changes the V13 prompt Chad explicitly selected. It does not alter
the completed V13 run, its human reference, the rubric or course thresholds.

The [second assessed run](BASELINE-BUDGET-RESULTS.md) completed all fifty first
attempts, but agreement is D1 50%, D2 85%, D3 65%, D4 90%, D5 85% and D6 60%.
Request delivery and rating accuracy are separate outcomes.

## Concrete change

[The complete draft prompt](../prompts/judge-v14-claims-draft.md) preserves V13 and
adds checks for the observed failure mechanisms:

- Trace essential actions through to the required output, including checking a
  reported numerical result against a supplied formula.
- Check the order of validation and access, and whether the stated hazard and
  precaution actually match.
- Inspect API owners, members, arguments and return types throughout the answer
  and tips, rather than accepting a list of familiar names.
- Inspect every tip; a useful tip does not cancel a materially incorrect one.

Keep D4 and D5 unchanged. In particular, do not redefine D4's professional-review
anchor merely to match the human's use of scope for two substituted equations.
Retain that interpretation disagreement and all original ratings explicitly.

These instructions are a hypothesis, not a demonstrated fix. V13 already contains
related instructions, and a longer prompt might not improve the model's behavior.

## Bounded development comparison

Use the existing ten confirmation cases and their attributed frozen reviews as
**known development cases**. They have already been exposed; this would not be
fresh confirmation or assessed calibration. Do not use the fifty assessed items
as an extra uncounted prompt trial. Only one of three assessed versions remains.

| Boundary | Proposed value |
| --- | --- |
| Cases | The same ten frozen confirmation cases, unchanged |
| Arms | V13 control and V14 draft, same model and case bodies |
| Model | Selected Qwen3.5-122B-A10B Q4_K_M, identical verified weights |
| Runtime | Same pinned build, context 16384, one slot, reasoning on, deepseek format, 4096 thinking-token cap |
| Requests | JSON mode, temperature 0.1, maximum 8192 output tokens, timeout 300 seconds |
| Budget | Twenty first requests; at most two attempts per case/arm, forty starts total |
| Failure boundary | Stop after two consecutive unsuccessful responses; unknown outcomes consume attempts and require inspection |
| Order | Frozen case order, V13 then V14 for each case |
| Model inputs | No human labels, review notes, other arm's output or prior model judgments |
| Evidence | Separate durable start/outcome ledgers, raw responses, exact public explanations and comparison receipt |

Before any inference, freeze the code, both prompts, human-reference identity,
case inputs, budget and archive. Verify all twenty input/output token reservations
fit without truncation, and verify the owned runtime before every start. A failed
preflight stops without changing the prompt or output allowance mid-run.

The original unrestricted V13 confirmation result is not the matched control:
the 4096 cap must be shared by both new arms. Retain all previous failures and
development history. Do not merge any output into either assessed version.

## Decision after the comparison

Advancement requires complete coverage, at least 8/10 agreement in every dimension,
more matching ratings than the matched V13 control, and no new safety/API false
approval relative to that control. Inspect all public explanations, including
matching decisions, for unsupported claims and misdescriptions. Numeric thresholds
alone do not establish qualification.

If the draft fails, retain the result and stop this allocation. If it improves,
prepare the evidence and an explicit proposal for the third and final assessed
version with an amended selection receipt. This proposal does not authorize that
full assessed run, generator correction or any change to human ratings.

No new human review is needed for this development comparison. Approval would
authorize preparing and executing only the bounded two-arm comparison above.
