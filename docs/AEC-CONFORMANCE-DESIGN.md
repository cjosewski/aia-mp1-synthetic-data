# AEC conformance revision design

November 20, 2026. The stopped [wire comparison](AEC-WIRE-DOCS-RESULTS.md)
produced no validated judgment. This design proposes a separate response
contract that retains the canonical judgment shape and validators while using
native schema constraints for field and evidence references. **Implementation,
native grammar acceptance, live request preflight and inference have not been
performed.** No new run or protocol is frozen, and no quality improvement is
measured.

## Problem and scope

The first wire judgment fit its context budget but included an extra safety
field, copied candidate content into task quotations and used page-only IDs in
place of passage IDs. Prompting with a JSON schema did not prevent those errors.
The locked Instructor JSON handler sends `response_format: {type: json_object}`;
the canonical response schema appears in system text but is not supplied as the
server's native schema constraint.

The proposed revision keeps the same ten cases, original task/candidate/reference
text, six rubric anchors, publisher reader, lookup policy and local model
settings. It changes the allowed response contract and native decoding request.
It is **not a lossless formatting revision**. Existing raw returns remain
unchanged and are never repaired, adopted or rescored.

## Minimal response contract

Retain `GroundedJudgment`, its original field names and types, the six binary
ratings, semantic notes and `validate_grounding`. Derive a separate native schema
for each case and the actual passages shown:

| Field | Proposed native constraint |
| --- | --- |
| Object keys | Explicit `additionalProperties: false` on every object; preserve canonical required fields. |
| `task_quote` in task checks and bindings | `const` equal to the complete original task brief, rather than asking the model to reproduce a selected span. Notes still interpret the task; the constant is not a correctness finding. |
| Candidate references | `enum` of the existing deterministic candidate field/list-entry IDs; safety references restricted to `safety_info`. |
| Tip references | Original tip IDs only; canonical validation still checks complete ordered coverage and inclusion of the finding's own tip ID. |
| Documentation `passage_id` | Actual shown `P#.E#` values or null, never a page-only ID. |
| Optional documentation `quote` | Null. The complete shown passage text remains available and resolves through its ID; no copied quotation is required. |
| Ratings and explanations | Original canonical types and rubric; no deterministic decision or supplied answer. |

The complete task must fit the unchanged 360-character field limit. Reject a
longer task before dispatch; never truncate it. Constraining the optional quote
to null removes quote-level locality: audit must inspect the resolved full
passage and its relevance to the claim. A full-task constant prevents foreign
text in that field, but establishes neither coverage nor correct entailment.

Resolve shared definitions before specializing them so the safety restriction
does not accidentally restrict other evidence fields. Keep all original checks
for duplicate IDs, nonempty supported/contradicted evidence, task provenance,
tip order and missing-passage uncertainty. Native constraints supplement those
checks. They do not replace them or derive binary decisions. The untouched raw
response must first validate against the exact case-specific constrained schema,
then the unchanged canonical Pydantic model and unchanged grounding checks. Bind
the overlay hash to the case and shown-page hashes; there is no repair or fallback.

The contract introduces no case-specific gold answers, hand-authored semantic
checklists or additional model stage. Human labels, prior ratings and technical
audit conclusions remain outside every model request. A missing page or anchor
still provides no proof that an API is absent or a candidate claim is false.

## Native feasibility and limits

Research inspected official source at llama.cpp commit
`cd959bae99ff4bed22bef2604f45241c09bbb8c8`, matching the retained native build
`b12110-cd959bae9`, plus installed Instructor 1.17.0, Pydantic 2.14.3,
OpenAI 2.54.0 and HTTPX 0.28.1.

The pinned chat parser accepts
`response_format: {type: json_schema, json_schema: {name: GroundedJudgment, schema: …}}`.
The nested `schema` is essential. Its parser does not use the wrapper's `strict`
flag as an additional enforcement mechanism. The schema converter implements
closed objects, `const`, `enum`, simple nullable alternatives and homogeneous
bounded arrays. This supports the proposed minimal overlay by source inspection.
[Chat parser](https://github.com/ggml-org/llama.cpp/blob/cd959bae99ff4bed22bef2604f45241c09bbb8c8/tools/server/server-common.cpp#L1378-L1405)
· [Schema builder](https://github.com/ggml-org/llama.cpp/blob/cd959bae99ff4bed22bef2604f45241c09bbb8c8/common/json-schema.cpp#L145-L340).

This is a subset of JSON Schema. Unsupported features can be silently ignored;
`oneOf` does not provide full exclusive-match semantics, and conditional
dependencies and uniqueness constraints cannot be assumed. Avoid
`if`/`then`/`else`, `dependentSchemas`, `uniqueItems` and tuple-based tip-order
constraints. Prefer a finite expanded native schema with explicit constraints,
then retain canonical validation of every response.
[Converter limits](https://github.com/ggml-org/llama.cpp/blob/cd959bae99ff4bed22bef2604f45241c09bbb8c8/grammars/README.md#L179-L224).

The retained Qwen template matches the pinned specialized Qwen3.5 parser. That
parser composes the reasoning section with a schema-constrained final JSON
section; it does not require disabling deepseek reasoning. This is source-level
evidence of compatibility, not an executed test of constrained decoding with
the installed model/build.
[Qwen parser](https://github.com/ggml-org/llama.cpp/blob/cd959bae99ff4bed22bef2604f45241c09bbb8c8/common/parsers/qwen3-coder.cpp#L13-L95).

`/apply-template` uses the same chat-parameter parser as completions and
constructs the chat session/grammar without inference. A later preflight must
submit the complete transformed request, including its native schema, then
measure the returned prompt with `/tokenize`. Successful parsing and token fit
would still not demonstrate valid generation or sound judgments. No standalone
native grammar validator was available in the checked installation; none was
built or installed in this design round.
[Template endpoint](https://github.com/ggml-org/llama.cpp/blob/cd959bae99ff4bed22bef2604f45241c09bbb8c8/tools/server/server-context.cpp#L6351-L6371).

## Offline proof and native normalization still required

The external prototype derived 21 logical schemas from the actual retained first
case and historical/stress fixtures. All ten original task briefs are 188–257
characters, within the unchanged 360-character limit. One wholly synthetic valid
response passed constrained-schema validation, then the locked canonical model
and grounding checks. Sixteen independent synthetic schema faults and the
unchanged rejected wire response were rejected; four stale bindings were
rejected. Four further cross-field faults passed the schema and were rejected by
the original grounding validator, demonstrating why that stage remains necessary.

The proof used preinstalled system `jsonschema` 4.23.0 for the logical schema and
the locked Pydantic environment for canonical validation. It installed no
package and is not a new production dependency decision or full test-suite run.
Three historical fixtures contain inadmissible duplicate legacy URLs and serve
only as schema diagnostics. The 21 schemas do not represent 21 valid new lookups.

**The logical schemas are not yet native-ready.** Pinned llama.cpp processes
`anyOf` before a sibling `const` or `enum`. The prototype's nullable `quote` plus
`const: null`, and nullable `passage_id` plus an enum, therefore need explicit
normalization before native use. Produce a native equivalent with `quote` as a
null type/constant and `passage_id` as a direct enum of actual IDs plus null.
Retain requiredness and annotations, prove acceptance equivalence to the logical
constrained schema, bind both identities, and validate returned raw JSON against
the logical schema before canonical validation. Do not send the prototype
unchanged and assume native enforcement.

Logical schemas measure 4,686–4,903 UTF-8 bytes, or 3,734–3,871 after factoring.
Those are byte counts, not token counts. Native grammar acceptance, compilation
cost, prompt fit and output conformance remain unmeasured.

## Implementation and verification plan

1. Add separate modules and tests; preserve all 21 frozen wire sources. Snapshot
   the stopped wire run's final 45 files, including its completion receipt.
   Resolve the original control and completed online baseline through the
   existing lineage. An incomplete parent is not a scored baseline.
2. Build the case/passages overlay and a guarded one-shot transport using the
   existing adapter pattern. Retain Instructor and the original Pydantic model;
   avoid a global library patch. Keep explicit schema instructions because the
   native schema field is not automatically inserted into the model prompt.
3. Freeze the new contract, source identities and request construction. Capture
   both original Instructor and transmitted request bodies/hashes. Bind the
   logical/native schema identities to the exact fit receipt and durable start.
   Any factored native schema must expand exactly to the new normalized native
   schema, with its equivalence to the logical overlay separately verified; do
   not compare it to the older broader canonical schema. Preserve raw
   responses/errors before canonical parsing and grounding validation.
4. Verify synthetic valid/invalid contracts, shared-definition isolation, allowed
   IDs/nulls, exact wire identity, lineage tampering, partial replay, unknown
   outcomes and one-attempt enforcement. A Python validation check is not a
   native grammar check.
5. After implementation review, use a fresh verified runtime for native grammar
   acceptance and exact request preflight. Preserve
   16,384 context tokens, 8,192 output tokens, 1,200 reserve tokens, the 4,096-token
   reasoning budget, twenty model starts and thirty publisher page allocations.
   No context increase, reduced output budget or extra repair call is proposed.
6. A later bounded trial requires a frozen protocol and passing exact preflight.
   Invalid or unknown outcomes consume their starts; never synthesize ratings.
   Report validated judgments against all ten selected cases, compare complete
   results to the original control and completed online method, and retain the
   existing independent explanation audit.

## Semantic boundary and evidence

Earlier [source-reference work](M4-SOURCE-REFERENCE-REDESIGN.md) already showed
that simpler IDs can solve copying failures without ensuring correct technical
judgment. The [candidate-applicability diagnostic](M4-CANDIDATE-CHALLENGE-RESULT.md)
found that a valid API reference did not establish that the candidate obtained
the required object. Those lessons motivate retaining technical audit; their
separate multi-stage procedures and historical acceptance additions are not
imported into this design.

Complete ten-case coverage and at least **8/10 agreement separately in every
dimension**, with the existing explanation audit, remain the development gate.
The separate assessed baseline remains 12, 15, 12, 17, 13 and 11 matches out of
20, with only D4 reaching 16/20. M4 remains open.

Private design artifacts are under
`../artifacts/evidence/.conformance-design-20261120/`.
`native-constraints-research.md` records the detailed support matrix, required
request envelope and implementation recommendation. Its receipt binds the
research and installed library snapshot; three source manifests bind the pinned
official source downloads. `prototype-results.json`, `schema-candidates.json` and
`prototype-verification.json` retain the separate logical-schema proof and hash
readback. `prototype-native-caveat.json` separately records the required native
normalization; the Python proof remains unchanged. No raw candidate response or
human label is published
here. The 1,031-test result remains the earlier wire preparation checkpoint;
this design does not claim a new full-suite result.

## Implementation status — November 20, 2026

The revision is implemented offline in two new modules. All 21 frozen wire
sources are unchanged.

- `tools/aec_conformance_docs.py` derives the logical overlay, the native view
  and the factored transmitted schema for each case and its shown passages. It
  proves the overlay is the canonical schema plus exactly the listed
  restrictions. It also proves the native view differs only at `quote` and
  `passage_id`, with identical accepted values, titles, requiredness and
  property order. A lint rejects any node where the pinned builder's precedence
  would ignore a sibling, and every unknown keyword. The lint runs on both the
  native and the factored schema. The subset validator checks untouched raw
  text, rejecting duplicate keys, NaN and bool/integer confusion. Then come the
  unchanged `GroundedJudgment` and `validate_grounding`. There is no equality
  gate on canonical normalization, and no repair or fallback.
- `tools/screen_aec_conformance_docs.py` runs as
  `api-development-qwen-conformance-docs-001`. It accepts the stopped wire
  parent only in its reviewed final state: 45 files, protocol `c1456135…`,
  completion receipt `40ccfbdc…` and manifest digest `2c0549f1…`. It resolves
  the compact, grounded and completed-online ancestors through their recorded
  hashes. The inherited protocol fields must equal the parent's.
- Before any model start, the runner builds a dry contract for every case. The
  contract enforces a complete task within the 360-character limit and one to
  eight original tips.
- Each request keeps the measured Instructor wire. Its system text shows the
  factored case schema, and it sends
  `response_format: {type: json_schema, json_schema: {name, schema}}`.
- The durable start binds the contract (case, shown pages, canonical, logical,
  native and factored hashes), both wires, the protocol and the fit receipt.
- A native template rejection becomes a recorded failure before any judgment
  start.
- **Failure policy (owner decision, November 20): continue and count as
  failed.** This replaces the frozen wire runner's stop-on-first-invalid
  behavior.
  - A case whose lookup, page or judgment allocation was consumed without
    yielding a validated judgment is recorded in `{case}-{stage}-failed.json`.
    Such outcomes include unknown, transport, client, contract, canonical and
    grounding failures.
  - The remaining cases still run. The report lists `failed_cases`, and a failed
    case counts as a non-match in every dimension against the denominator of
    ten.
  - Unconsumed failures still stop the run before any slot is spent: fit,
    native rejection, deployment, service and contract construction. So do
    evidence-integrity faults, such as changed inputs, hash mismatches or a
    wrong model, which are never absorbed as model failures.

Verification: 61 contract and 27 runner tests, all synthetic. One test
interprets the transmitted schema with the pinned builder's precedence and
matches the logical overlay on every fault, while the unnormalized overlay would
accept a copied quote. Full locked suite: **1,118 passed, 1 skipped** (optional
`reportlab`).

A read-only check on the retained first case found that the conformance request
changes only the system schema text and `response_format`. The system text
grew from 12,157 to 13,056 bytes; this is a byte count, not a token count. The
factored case schema is 3,725 bytes, against 2,826 for the factored canonical
schema. A dry run against the real evidence passed lineage, parent identity,
source pins and inherited-protocol equality, and wrote nothing.

Independent implementation review found one high-severity false rejection.
Pydantic strips justification whitespace, so my extra equality gate would have
rejected valid answers. That finding and the medium/low findings are fixed.

**At the implementation checkpoint, not yet performed (all were performed
later; see below):** freezing the protocol (`prepare` on the real root), a
fresh verified runtime, native grammar acceptance, exact `/apply-template` plus
`/tokenize` preflight, and any inference. Python checks are not native
enforcement evidence.

**Executed November 20.** `prepare` must precede `preflight`, which reads the
frozen protocol. The bounded trial ran and failed the development gate. It
produced 8 of 10 validated judgments and agreement of **0, 3, 7, 8, 6 and 4 of
ten**. See the [result](AEC-CONFORMANCE-DOCS-RESULTS.md).
