# Proposed limited-thinking feasibility probe

**Status: prepared for owner approval; no model requests authorized or executed.**

The [frozen assessed run](ASSESSED-BASELINE-RESULTS.md) retained three responses
that used all 8192 tokens in reasoning and returned no final ratings. The pinned
`llama-server` build's captured `--help` documents `--reasoning-budget N`: default
`-1` is unrestricted, and positive N sets a thinking-token budget.

## Exact proposed change

Add **`--reasoning-budget 4096`** to the dedicated project server's existing launch
command. Retain Qwen3.5-122B-A10B Q4_K_M, V13, JSON mode, temperature 0.1, total
output allowance 8192, timeout 300 seconds, context 16384, one slot, reasoning on
and deepseek response format. The hypothesis is that ending thinking earlier will
leave enough output allowance for the six public ratings and explanations.

Use only the two affected saved inputs, in this order:

1. `baseline-001-b01-item-0015`
2. `baseline-001-b01-item-0028`

Copy their exact messages from the original frozen native plan. Supply no human
labels, reviewer notes or earlier model judgments to the model. This is a
development-only feasibility check on known cases, not another assessed run or a
fresh independent confirmation.

## Bounds and decision rule

- At most two starts per case, four total; stop after two consecutive unsuccessful
  responses or any unknown request outcome. Preserve every response and failure.
- Verify frozen source files, exact inputs, model weights, native template,
  context fit and the owned server's actual command line before inference.
- Success requires two complete schema-valid judgments from the expected model.
  Inspect output limits and public explanations afterward; technical success alone
  does not establish accurate judging or calibration.
- The original assessed run remains interrupted and immutable. Its exhausted item
  receives no extra assessed attempt. A subsequent assessed revision requires an
  explicitly recorded runtime amendment and a new run identity.
- No automatic full 50-item run follows this probe. Report the measured outcome
  and a concrete next-step recommendation first.

## Approval and Mac use

The package refuses execution without an attributed owner-approval receipt bound
to its frozen plan. Approval is needed because the requested 4096 thinking cap
changes the runtime settings Chad explicitly froze in his selection instruction.
This requirement comes from that instruction, not a new skill approval rule.

Approval text:

> Approve the two-case Qwen3.5 thinking-budget probe with a 4096 thinking-token cap and at most four requests. Preserve the frozen assessed run and all errors.

Codex will announce Mac use before the approved probe, stop only its owned server,
verify the return and announce when the Mac is free. The Mac is currently free.
