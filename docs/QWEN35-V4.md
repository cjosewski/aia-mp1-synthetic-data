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

## Frozen package and verification

The final allocation includes all 180 prior starts. **375 locked WSL tests**, Ruff
lint/format and launcher syntax pass. An exact comparison confirms that V13 only
changes V10's heading and copies V4's D1/D2 paragraphs; all user messages are
unchanged. The preparatory helper initially shadowed its input-list variable while
checking those prompt differences, failing before producing a plan, archive or
model request. That partial preparation is preserved at `MP1-QWEN35-V4-MAC/`.

The corrected helper uses a new exclusive directory. The executable package
`qualification/MP1-QWEN35-V4R1-MAC.zip` freezes 183 files from commit `e2f22f3`.
Its Mac and NAS copies match. Plan SHA-256:
`a2ab73107d6b9efa09e78c16f9f8fc95e960d3394d31a74bf7edf2cc11da4f8c`.
Archive SHA-256:
`495abac1b8271a67c622fe7a9f8d91239c5a288cd0e886d1155664ff16f7cd82`.
Native preflight and execution completed successfully.

## Measured result

Ten valid first attempts match **57/60** frozen ratings. D1–D6 matches are
**9, 9, 10, 10, 9, 10** out of ten, and the first five match 28/30. There are no
retries, truncations, timeouts or unknown outcomes. Cumulative starts are **190**.
All 183 frozen files and the complete ledger replay verify. The owned server
stopped and port 8081 was free before archiving.

All sixty public explanations were audited. Three errors remain: case 02 D2
overextends a reporting hazard for a disposable geometry exercise; case 05 D1
credits execution stages despite an incorrect requested interpretation; case 06
D5 mistakes guessed metadata for a different objective. These are two false
rejections and one completeness false approval. No safety/API false approvals
occur. The other 57 explanations identify supplied facts and support their
matching decisions, including the null hazard, dictionary access and altered ODE.

Advance only to fresh blind confirmation. The numerical gate permits residual
disagreement; the semantic audit retains the three erroneous anchor applications
and verifies the matching explanations rather than asserting all sixty are sound.
This small reused development set cannot establish generalization or superiority.
Neither the prompt nor the human ratings will be changed for confirmation.

Return archive: `qualification/MP1-QWEN35-V4R1-RETURN.zip`, SHA-256
`3fa6b7617f29492c6a88e5e30906e67bd42074dae2265f5c8fb574c39ac407c7`.
Audit: `qualification/mp1-qwen35-v4r1-return-audit/`, including all public review
rows and the assistant's explicit semantic decision. Return, audit and fresh
packet total 250 verified NAS files. They are local evidence, excluded from Git.

The [confirmation runbook](QWEN35-CONFIRMATION-RUNBOOK.md) describes the next human
dependency. Ten new, unscored examples were authored after the protocol freeze,
checked against 235 prior records and the approved tasks for exact duplication,
and balanced across all five categories. Domain/concept overlap remains; no
representative-sampling or semantic-independence claim is made. Neither comparison
model has received these cases. Authentic reviews must be frozen first.
