# M4 bounded source-ID development trial

November 18, 2026. Prepared under Chad's instruction to continue closing the
rating gap. **Historical plan; execution stopped after one rejected fact audit.**
See the [result](M4-SOURCE-ID-TRIAL-RESULT.md). This is a new
development protocol after three rejected exact-offset trials, not a fourth
assessed allocation. The twenty original human labels, unchanged D1–D6 rubric,
V13/V15 results and restored 80%-in-every-dimension criterion remain frozen.

## Fixed inputs and allocation

- Ten exposed cases, two per category, in the corrected packet with SHA-256
  `f405cee4dea56404401b56136ae259808e66a308d9982e516103a6227f251b3d`.
  It has 358 checks, sixteen explicitly insufficient claims and zero holds or
  source gaps. The old rejected journals remain separate and immutable.
- `recovery-source-refs-v1`: the verifier returns only frozen source IDs and
  versions, statuses and explanations. The scorer uses frozen candidate passage
  IDs and effects for every routed check. Application validation and separate
  attributed technical audits remain required; ID validity is not truth.
- Source-ID implementation hash
  `acf740fd78f25c31c489a617f24ed97d6716fa88736a8db38a5d13ae97f86a5c`
  at Git commit `fcd9ab1`. The new journal must freeze this exact hash.
- Prepared facts prompt SHA-256
  `6f0d76b2ea16bbeefdabd0e135428c6bc2fa4d48dc7256f8bd4c0709b252fd10`;
  prepared score prompt SHA-256
  `9fe33ea813a5ae2204273c7a750622dc4b78294e534c5796f4da7c1939568a4a`.
  Both are stored outside Git in the source-ID offline qualification directory.
  Neither contains human ratings, reviewer comments or previous judge decisions.
- Qwen3.5-122B-A10B-Q4_K_M with the two previously pinned local model shards.
  Use a new owned Mac server on loopback 8082, 65,536 context, one slot,
  reasoning on with DeepSeek formatting and budget 4096. Use a dedicated Windows
  loopback SSH tunnel on 18082. Do not alter Herd settings or other services.
- Temperature 0.1, output allowance 16,384 tokens and 1,200-second client
  timeout. Check actual schema-bearing wire token fit before every start and
  persist the ownership, model-file and token receipts. One request per released
  stage; no hidden retries or automatic technical acceptance.
- Maximum **20 model starts**: facts then, only after an accepted technical
  fact audit, score for each of ten cases. A malformed response consumes its
  slot. An unknown transport outcome consumes its slot and stops. Two consecutive
  structural failures or one technical-audit rejection stop this trial.

## Decision gate

Advance only after ten complete, technically audited pairs, at least 8/10
agreement in **each** D1–D6, more total matches than V15 on those same cases,
no dimension regression, no increase in false approvals, zero D2/D3 false
approvals and no unsupported decisive finding. This is exposed development
evidence only. A distinct assessed extension must still score the original
twenty frozen human reviews and reach at least 16/20 agreement in every
dimension with complete coverage before M4 can close.

The ArcGIS Pro 3.7 `arcpy` runtime probe remains license-blocked and supplies
no positive API evidence. The sixteen declared unknown claims remain
insufficient. Human labels are never inferred from assistant technical audits.
