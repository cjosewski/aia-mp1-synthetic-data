# Qwen3.5 comparison with the existing V10 prompt

Execution requires the completed, audited V2 screen and a separately frozen
package. Chad's standing authorization covers this controlled development work;
no human ratings, rubric anchors or assessed defaults change.

V2's first six public judgments correctly reject the previously approved null
hazard but reject context in four cases. The existing `judge-v10-canonical.md`
distinguishes a wrong answer to an identifiable problem from a changed problem
more explicitly. It also explains why read-only settings cannot protect against
null dereferences or false data interpretations. Reuse that whole prompt without
edits, examples, case identifiers, expected labels or reviewer comments.

Keep all ten original user messages and their order, reference content, canonical
Judgment schema, verified split weights, native Mac/build/template, thinking mode,
temperature 0.1, 8192 output tokens, 300-second timeout, 16384 context and one slot
fixed. Only the system prompt changes from V4 to V10, including its existing
approximately 60-word public-justification instruction. Preflight must verify the
new prompt's token fit before inference.

Allocate at most twenty new starts after the verified completed V2 total of 169,
for a ceiling of 189. Packaging requires the verified completed V2 audit.
Allow two attempts per case, stop after two consecutive invalid/transport outcomes,
and stop on unknown outcomes, changed identities or token overflow. Preserve every
attempt and stop only the owned server.

Require complete coverage, at least 80% agreement in each dimension, no safety/API
false approvals and public explanations that support their decisions before
advancing. Inspect all sixty explanations, including matching decisions. A failed
screen remains failed; do not combine the best ratings from earlier runs.

If this protocol is promising, keep it frozen and prepare fresh confirmation inputs
across all five categories. Authentic human reviews must precede either model's
confirmation calls, with a matched generator comparison. All existing unused
reserve drafts remain excluded. No development score alone qualifies a judge or
establishes full fifty-item assessed calibration.

## Frozen package and verification

The V2 frozen-code replay verifies 169 prior starts. **374 locked WSL tests**,
Ruff lint/format and launcher syntax checks pass. The V10 prompt is unchanged;
all ten user messages match the earlier screens byte for byte.

`qualification/MP1-QWEN35-V3-MAC.zip` freezes 181 files. Local, NAS and Mac archive
hashes match. Plan SHA-256:
`095d36a9cf0e4103c719066bb992c3875aa3e5fc8bc4570de60ae572774fead6`.
Archive SHA-256:
`9362cb7643658adb7e8521bac7b1d576c6925709c210b8cf177164bf50e502ee`.
Native preflight and execution results remain pending.
