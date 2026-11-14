# Qwen3.5 V4: completion and hazard checks within V10

This bounded follow-up requires the completed, audited V3 result before packaging.
Chad's continuing P1-03 authorization covers it. All human references and the
engineering-v1 rubric remain unchanged.

The measured V2/V3 explanations expose a prompt tradeoff: V4's explicit D2
hazard matching rejects the null hazard, while V10's context instructions correct
earlier D3/D5 distinctions but its shorter D2 instruction credits an unrelated
read-only precaution. V3 also calls the CRS procedure complete despite identifying
its invalid return-type access. These findings motivate changing D1 and D2.

`judge-v13-hazards.md` preserves the complete V10 prompt apart from its version
heading and D1/D2 paragraphs. Both paragraphs are copied from the existing V4
prompt, including the instruction not to invent unrelated hypothetical hazards. No
case-specific examples, identifiers, ratings or reviewer comments are added.
The hypothesis is that explicit completion and material-hazard checks will
preserve the context distinction while removing false approvals. These two
instruction changes are combined; do not claim to isolate their separate effects.

Keep the same ten original user messages, order, canonical schema, pinned Qwen
weights, Mac/build/template, thinking mode, temperature 0.1, 8192 output tokens,
300-second timeout, 16384 context and one slot. Native preflight must verify
identity and token fit before the first request. Frozen packages and results
remain separate; never compose favorable decisions from different experiments.

Allocate at most twenty new starts after V3's verified completed total of 180,
for a ceiling of 200. This includes V3's rejected token-limit completion and its
successful retry. Allow at most two attempts per case and stop after two
consecutive invalid/transport outcomes. Unknown outcomes, exhausted budgets,
changed identities or overflow stop dispatch. Preserve all starts and raw results;
stop only the owned server.

Inspect every public justification, including matching decisions. Advance only
with complete coverage, at least 80% agreement in every dimension, no safety/API
false approvals and explanations that support their decisions. Preserve failure
as failure. A promising known-case screen only permits preparing fresh blind
confirmation with authentic reviews before either model's calls; it does not
qualify the judge or start assessed calibration. Existing unused drafts stay
excluded, and no human review is requested during this development experiment.
