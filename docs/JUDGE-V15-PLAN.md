# V15 task-contract development comparison

November 17, 2026. Authorized by Chad's instruction to try to meet the original
80%-in-every-dimension criterion. This is one bounded experiment, not an unlimited
prompt search or a claim of successful calibration.

## Hypothesis and controls

The [V15 prompt](../prompts/judge-v15-task-contract.md) replaces V13's extended
instructions with a concise task-contract evaluation. It retains the six rubric
anchors, distinguishes essential completion from optional refinements, checks
API ownership without treating missing documentation as disproof, and evaluates
whether the answer addresses contextual distinctions required by the task.
V13's categorical separation of context from correctness may have caused it to
credit shared subject matter while missing a required contextual distinction.
This interpretation is a hypothesis to test, not permission to copy human labels.
D4 remains professional review/sign-off; the known human interpretation difference
on two baseline examples is preserved rather than silently re-scored.

Use the same ten previously reviewed confirmation cases as **exposed development
data**, with an alternating matched V13 control. Preserve exact user messages,
reference task/source context and the frozen reporting-only human reference.
No assessed baseline items, human notes, label values or prior judgments enter
the model requests. This screen cannot establish independent generalization.

- Model: the pinned Qwen3.5-122B-A10B Q4_K_M and existing native Mac build/template.
- Settings: temperature 0.1, 8192 total output tokens, 4096 thinking-token cap,
  16384 context, one slot, reasoning on/deepseek format, 300-second timeout.
- Budget: twenty initial requests (ten per arm), two attempts per case/arm,
  maximum forty starts. Unknown outcomes consume budget and require inspection.
- Stop after two consecutive unsuccessful responses; no automatic recovery or
  extra allocation. Verify owned runtime before each request.
- Freeze committed code, prompt bytes, plan, original inputs and owner statement
  before inference. Token preflight must pass without truncation. Preserve every
  start, completion/error and explanation. Do not change Herd services.

Python, dependencies and tests run in WSL2 Ubuntu. The Mac runs only the owned
native inference server; an SSH loopback tunnel carries requests. Both arms use
this same arrangement. Before inference, verify both model-shard hashes, the
pinned native template/build, all twenty token reservations and the server's
PID/parent/command. Recheck ownership before every start. An existing listener
prevents launch; only the launched child process may be stopped during cleanup.

## Advancement and stop condition

Require complete coverage, at least 8/10 matches in every dimension, more matches
than the matched V13 control, and no new safety/API false approval. Inspect all
120 public explanations, including matching decisions, for factual support and
invented candidate descriptions. Software checks do not prove semantic accuracy.

On failure, retain the complete result and stop this allocation; do not use the
remaining full-baseline attempt. On success, prepare fresh blind confirmation and
request only the authentic human review needed for it. The already-exposed cases
cannot serve as that confirmation. Subsequent assessed runs must use one frozen
qualified judge for both cohorts under the restored original acceptance policy.

The current corrected-cohort packet remains available for human review independently
of this development run. Neither its labels nor its unmeasured results are used
to tune V15. No inference has been performed at this preparation checkpoint.

Preparation passed 468 locked WSL tests, Ruff and launcher syntax checks. The V15
prompt byte SHA-256 is `0ff6b3170ff6a412d5c7846dc936e5ff699820c1f212d5592419eba2abe8b28d`.
These checks establish implementation behavior, not model accuracy.
