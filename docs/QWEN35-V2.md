# Qwen3.5 follow-up with the existing V4 prompt

This is a controlled prompt comparison under Chad's standing authorization to
complete P1-03. Execution requires the completed, audited V1 screen and a new
frozen package; it cannot resume or replace V1's records.

V1's public explanations expose a safety miss: a read-only/disposable-model
precaution is credited while the proposed procedure still dereferences null.
The existing `judge-v4.md`, authored before Qwen3.5 was selected, explicitly
requires matching each material access/reporting hazard to its precaution and
distinguishes callable APIs used incorrectly from invented interfaces. Reuse that
entire prompt unchanged. This tests an existing operational interpretation of
the same rubric, not a new rubric or case-specific answer key.

Keep all ten original user messages, order, reference content, canonical Judgment
schema, Qwen3.5 split weights, Mac/build/template, thinking mode, temperature 0.1,
8192 output tokens, 300-second timeout, 16384 context and one slot unchanged.
Only the system prompt changes from V9 to V4, including V4's existing 40-word
public-justification instruction. No frozen human ratings or comments enter
model requests. Native preflight must verify every changed input's token fit.

Allocate at most twenty new starts after V1's verified cumulative total of 159,
for a ceiling of 179. Require the completed V1 audit to establish that count
before packaging. Allow at most two attempts per case, stop after two consecutive
invalid/transport outcomes, and stop on unknown outcomes, identity changes or
token overflow. Preserve all attempts and stop only the owned server.

Audit all sixty public explanations, not only disagreements. Advancement still
requires complete coverage, at least 80% agreement in each dimension, no safety
or API false approvals and explanations supporting the decisions. This known-case
comparison cannot itself qualify the judge or authorize assessed measurements.

The V1 reserve draft stays unused and unscored; it was authored under the earlier
protocol. If this changed protocol is promising, freeze it and then prepare new
blind confirmation inputs for authentic human review before either model sees
them. Preserve the baseline reference and all prior experiments unchanged.

## Frozen package and verification

The complete V1 replay establishes 159 prior starts. The V2 runner passes
**373 locked WSL tests**, Ruff lint/format and shell syntax checks. The V4 prompt
file has no changes; all ten complete user messages match V1 byte for byte.

`qualification/MP1-QWEN35-V2-MAC.zip` freezes 180 files. NAS and Mac copies match
the source archive. Plan SHA-256:
`0b5e7e4bd41dd562779a89def9d2b7c79e91dd56024d120f0a8db2f4c16ab571`.
Archive SHA-256:
`79749a3f1bee419e81fdd8615c4cdffe796332f01213c12852ac556e10184c80`.
Native preflight and execution results remain pending.
