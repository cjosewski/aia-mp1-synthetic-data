# M4 recovery: evidence checks before dimension scores

Subsequent revision: [evidence v2](M4-EVIDENCE-V2.md) implements distinct evidence
kinds and child-check lineage after the source audit. The v1 contract below is
preserved for replay; v2 remains offline and its real-item drafts unaccepted.

November 17, 2026. **Offline design and contract prototype implemented; live
execution is not enabled.** No new model calls, Mac use, review changes or assessed
allocation. Cumulative recorded starts remain 388. M4 remains open.
The subsequent [preparation/scoring checkpoint](M4-RECOVERY-PREPARATION.md)
adds ten draft checklists and offline scoring with explicit audit lineage;
source completeness and live execution remain pending.

## Problem and intended change

[V15's original-baseline result](V15-BASELINE-RESULTS.md) is 95/120 (79.2%),
including D1 70% and D6 65%. It misses all three human-identified safety failures.
The 93.3% small confirmation result did not transfer. Repeating a wording-only
change is not the next experiment.

The [V8.1 verifier](JUDGE-V81-VERIFIER.md) exposed a second problem: the model
could produce valid source IDs while bundling claims, overlooking source gaps,
or classifying API statements as procedures to avoid the primary-source rule.
Its scorer then confused candidate, source and rubric roles in two failed outputs.
Neither a JSON-valid response nor a matching final rating establishes a sound
explanation. V15 also produced matching ratings with incorrect reasons.

This recovery separates three questions:

1. Did the application account for the task and every candidate passage, including
   every tip, using unchanged text and permitted retained sources?
2. Does each cited source actually support the specific claim for the required
   version, object, parameter type, prerequisites and units?
3. Given those findings, what does each **unchanged rubric dimension** require?

Only the first question has an automated structural answer. The other two need
semantic review and measured evaluation. Facts alone cannot become judgments.
The subsequent offline scorer can emit an audited development judgment shape,
but never human labels or an eligible calibration receipt.

## Implemented offline boundary

The isolated [recovery_checks.py](../src/aia_mp1/recovery_checks.py) reuses V8's
source-artifact, exact excerpt, permission-receipt and typed-catalog validation.
Historical V8/V8.1 validators and assessed defaults are unchanged.

A separately prepared `recovery-offline-v1` checklist pins the exact fact input
and rubric hashes. Application IDs `K0001`, `K0002`, etc. identify fixed checks.
Each check contains an exact subject span, question, dimension review routing and
allowed source/version bindings. The model cannot change those roles or routing.
The whitelist schema has no rating, reviewer or human-reference fields. Text
fields still require an audit for accidental answer-key leakage.

Every non-whitespace character in `R.task` and every candidate passage must be
covered exactly once, without overlapping spans. Offsets are zero-based Unicode
character offsets into the retained passage, with an exclusive end. They are
distinct from V8's UTF-8 byte offsets into original source files. Quotes preserve
whitespace exactly. Checks should separate atomic claims; character coverage
**does not prove semantic completeness or atomicity**.

| Subject | Fixed kind / minimum dimension review | Permitted evidence |
| --- | --- | --- |
| Reference task | `task_obligation`, D1 | Frozen task or retained primary excerpt |
| Question / equipment problem | `context`, D5 | Frozen task or retained primary excerpt |
| Answer, tools and steps | `technical_claim`, D1 and D3 | Retained primary excerpts |
| Safety text | `technical_claim`, D1, D2 and D3 | Retained primary excerpts |
| Every tip | `technical_claim`, D1, D3 and D6 | Retained primary excerpts |

These mappings require review in the listed dimensions; they do not assign a
failure to every dimension when a claim is wrong. Extra review dimensions may
be included. D4 professional-review applicability still needs explicit treatment
in the scoring stage; the fact checklist alone is not a six-dimension judgment.
Technical assertions embedded in a question/problem must receive primary-source
bindings during preparation and semantic audit, rather than using task agreement
as proof of API behavior. The parser does not recognize technical prose.

An empty binding list is an explicit source gap. It is valid to record the gap,
but it blocks a conclusive observation. Authored summaries, rubric text and
candidate assertions cannot stand in for primary technical evidence. Binding a
version proves only that the retained version label is unchanged, not that the
source applies to the task's version or that its licensing assertion is correct.
Those judgments remain part of the source audit.

The response supplies only the canonical checklist hash and exactly one
observation per check: `supported`, `contradicted` or `insufficient`, exact source
citations and a public explanation. Non-insufficient conclusions need at least
one bound citation. Missing, duplicate, foreign and altered references fail.
Uncertainty remains unresolved; it cannot silently become a pass. Contradictions
are retained without automatic dimension ratings. Even a fully valid response
reports `calibration_eligible: false` and `semantic_audit: required`.

## Semantic audit and proposed scoring stage

Before inference, prepare checks from task, candidate, rubric and permission-cleared
sources, excluding human ratings/comments and earlier judge outputs from model
inputs. Development cases are already exposed to the project team; disclose this
as targeted development, never independent confirmation. Freeze and inspect the
checklist before sending it to a model. No checklist should encode an expected
rating or tell the verifier which answer to reach.

For each technical claim, inspect API owner, returned object/value, storage type,
argument contract, prerequisites, units and version as applicable. Split compound
claims. Identify source gaps explicitly. A member absent from a partial excerpt
is not evidence that the member does not exist. A quotation about a neighboring
method is not support. Inspect task obligations against the **whole candidate**
before declaring an essential step missing; code snippets are not universally
required by the rubric. Keep mathematical givens unchanged and independently
check any decisive numerical claim. Record every unsupported decisive conclusion.

The offline scorer receives the frozen checklist and findings. Its output
has six application-defined dimension keys and check-ID dispositions;
it is not asked to reproduce rubric text as an ID or choose interchangeable
candidate/source namespaces. Application code must attach the frozen rubric and
original candidate evidence. All relevant findings, including tips and conflicts,
must have dispositions. An unresolved decisive fact prevents canonical projection.
A disagreement about a finding needs evidence and a recorded explanation, not
silent omission. Contradictions do not mechanically determine unrelated scores.

Do not redefine D4 to resolve the known difference between task-scope comments
and the frozen professional-sign-off anchor. Retain that discrepancy, the original
human ratings and their effect on agreement. Similarly, never change human D1/D6
ratings to fit the new checklist. Explanation accuracy and binary agreement are
separate reported outcomes.

**Implemented offline:** ten draft source/checklists, semantic-audit receipt
contracts and simplified scoring/projection; see the preparation checkpoint.
Actual semantic audits, complete source coverage, staged transport integration,
token preflight and a frozen execution package remain pending. The CLI below has
no execution switch. This is not a repaired live V8 run or a qualified judge.

## Proposed bounded development trial — not allocated or started

Offline request preparation is now available in `recovery_wire.py`. It captures
the locked Instructor serialization separately for recovery `Observations` and
`Scores`, retaining the complete schema-bearing request and fingerprints of the
logical request, schema and wire body. Verification regenerates the wire and
rejects drift, including timeout changes that do not appear in the HTTP body.
Only an intercepted local mock is used; this module has no live endpoint or
dispatch capability. It does not establish token fit, allocate starts, validate
source applicability or replace the required durable scheduler and semantic
audits. Historical V8 schemas, allocation and transport remain unchanged.

Ten focused synthetic tests pass, covering schema selection, input preservation,
settings/schema/body drift, unsupported fields/stages and malformed messages.

`recovery_schedule.py` separately replays the proposed ten-case, twenty-start
schedule. Every stage has one attempt; failed verification skips its scorer,
unknown outcomes prevent further starts, two consecutive structural failures
stop the schedule, and a rejected semantic audit halts it. Successful structural
validation waits for an audit before advancing. All ten cases remain in the
coverage denominator. Six synthetic schedule tests pass. This pure state machine
has no persistence or dispatch and does not authenticate audit receipts; the
future durable runner must derive events from the actual artifact validators.

`recovery_ledger.py` now persists that schedule in an external, single-writer
journal with full artifact payloads, a hash chain, implementation identity and
an independently checked head. Reopening a start without a finish preserves the
unknown outcome and blocks another start. Changed payloads, incomplete tails,
event/head mismatches and symlink journal files fail inspection; there is no
automatic repair. Seven focused synthetic tests cover these cases, retention,
payload mismatches and writer exclusion. This is storage, not semantic approval:
the runner must still derive completion/audit statuses from the real validators
and enforce source/runtime/token preflight. No live dispatch is connected.

The accepting fact-audit adapter in `recovery_audit_bridge.py` now binds the
waiting verifier completion to frozen plan/input/rubric hashes. It parses the
retained raw chat completion and invokes `build_scoring_input`, including the
version-specific source, reasoning and runtime-applicability audit checks. Only
successful validation appends an accepting event. Invalid or stale artifacts
leave the journal unchanged and scoring blocked.

The accepting score-audit adapter reconstructs observations, the accepted fact
audit, and scores from saved journal payloads. It revalidates the source bundle
and requires the scorer start to bind the exact released scoring input. Only a
complete, accepted six-dimension review advances to the next case. Twelve focused
synthetic tests cover both adapters, including changed source permissions, stale
scoring inputs and unresolved scores. Live request/runtime preflight remains
runner work. An accepted technical
audit is not an authentic human label or permission to dispatch; the resulting
development judgment remains ineligible for assessed calibration.

Score-audit integration verification: **674 tests passed in 119.53 seconds** in
the locked WSL environment with the analysis extra and ReportLab. Focused tests
passed 12/12; Ruff lint/format and `git diff --check` passed. These are software
checks only; no model requests or real review acceptances were produced.

`record_completion` now derives response-schema validity from the retained raw
chat completion and the pending stage's schema. It requires the exact durable
start identity, preserves malformed replies, and does not accept a caller's
validity flag. Schema-valid responses still wait for semantic review. Missing
outcomes stay pending; late or duplicate completions cannot finish a different
request. Malformed responses consume their slot and the existing two-consecutive-
failure stop applies without reducing the ten-case denominator. Transport
exception capture is described below; live dispatch remains unimplemented.
Response-recording verification: **677 tests passed in 127.65 seconds** in the
locked WSL environment; Ruff lint/format and `git diff --check` passed. No live
requests or changes to frozen ratings were made.

`reject_audit` records an attributed, nonblank technical objection against the
exact completion awaiting review. Either stage can be rejected at the first
decisive problem without completing an accepting audit. The journal preserves
the original response, records the rejection reason, and halts the entire trial;
reopening cannot release another request. The review origin is disclosed, but
does not authenticate the reviewer or create a human rating. Stale, empty and
duplicate rejections are refused. No real technical rejection was authored by
these synthetic tests.
Rejection integration verification: **679 tests passed in 127.63 seconds** in
locked WSL; 17 focused adapter tests, Ruff lint/format and `git diff --check`
also passed. No live requests or authentic human labels were produced.

Transport exceptions now have a dedicated durable journal event. The event binds
the sole pending start and preserves the exception class without request/header
or exception-message contents. It does not claim whether the server received or
finished the request. The consumed start remains unknown and the schedule halts;
reopening cannot retry it, append another start, or automatically accept a late
response. Later evidence requires separate inspection. This is failure-recording
support, not the live dispatch implementation.
Verification: **681 tests passed in 123.08 seconds** in locked WSL, including
32 focused journal/schedule/audit tests. Ruff lint/format and diff checks passed;
no real transport failures or inference requests were generated by these tests.

`recovery_transport.dispatch_next` connects one new journal slot to the existing
single-attempt Instructor client. It checks frozen transport settings, endpoint,
case binding and the prepared wire; its transport writes and checkpoints the
start immediately before network access. A failed checkpoint prevents sending.
The exact schema-bearing wire is checked at that boundary, with no SDK/transport
retry. Returned bodies use existing credential redaction and completion recording;
transport exceptions use the durable unknown-outcome stop. A caller cannot
redispatch a pending or already consumed slot. Scorer starts retain their scoring
input hash for the later acceptance audit.

This is an **internal transport adapter**, not an operator command or an experiment
authorization. The top-level runner must still construct frozen prompts/inputs,
clear source holds, verify actual model/runtime identity, run fresh token-fit
checks. A transport policy or schema-valid
response alone does not satisfy these gates. No real journal is allocated and
no live evaluation has used the adapter.

`recovery_preflight.preflight_next` rebuilds the next request through the frozen
packet and accepted-fact gates, then checks the live server build, full default
settings, chat template, single slot and model path against frozen properties.
The model listing and health must agree. It renders and tokenizes the exact
schema-bearing wire and includes the full requested output allowance. A second
server observation and journal-head check detect changes during that operation.
Oversized inputs are reported as not fitting, with no model start. This is a
read-only evidence producer, not an execution permit: remote process ownership,
weight identity, persistence and dispatch-boundary integration remain required.
The same construction handles the actual accepted fact memo when scoring is next.
`recovery_process.preflight_owned` surrounds that HTTP preflight with read-only
native Mac process observations through the trusted SSH reader. It checks the
recorded parent relationship against the live process, confirms that the same
PID owns the frozen port, and requires the exact executable/model/loopback host,
context, slot and reasoning arguments. PID and process start time must remain
unchanged across the observations. PID files alone are not accepted as ownership.
The adapter starts, signals and reconfigures no service; `kill -0` only checks
that the recorded launcher exists. Remote paths with ambiguous whitespace in
the observed command are rejected rather than guessed.

The owned-process wrapper also hashes every frozen model shard and the executable.
Split GGUF coverage must begin at shard one and include every named shard; omitted
or duplicate files are rejected before remote reads. Captures retain size, mtime,
inode and SHA-256; metadata must be unchanged during each hash and is checked
again after HTTP preflight. Matching on-disk files are not a memory inspection
or a hash of all dynamically linked runtime libraries.

The SSH tunnel's endpoint mapping, persisted receipts and the final dispatch
boundary remain open. These checks do not authorize inference. The proposed
uncertainty policy is not enabled. Hashing uses read-only shell commands through
the trusted SSH reader, with a 600-second limit per file and no automatic retry.
File-check verification: **732 tests passed in 136.95 seconds** in locked WSL.
After adding two post-preflight metadata assertions, all **38 focused runtime,
process, file and journal tests passed in 5.60 seconds**. Lint, formatting and
diff checks pass. Captures were synthetic; no Mac connection or inference ran.
Process-check verification: **722 tests passed in 148.93 seconds** in locked
WSL Ubuntu; 26 focused process/preflight/journal tests passed. Synthetic captures
exercise wrong parent/listener, duplicate listeners, changed port/context/budget,
invalid paths and a process restart during preflight. Ruff lint/format and diff
checks pass. No remote machine was contacted by this verification.
Preflight verification: **712 tests passed in 146.46 seconds** in locked WSL;
the focused preflight/request/journal set passed 19 tests. Synthetic checks cover
overflow, changed templates/build/context, drift during tokenization and changed
preparation before any HTTP request. Ruff lint/format and diff checks pass.

The transport now compares each returned completion envelope's model name with
the frozen request. A missing, blank or different name retains the redacted raw
response in a `response_identity_failure` journal event and halts all remaining
slots. It does not offer the response for a technical audit, grant a retry or
classify the received response as an unknown transport outcome. This check
applies to either stage. Matching names still do not prove loaded-weight identity;
fresh runtime and file-identity checks remain necessary. No aliases are inferred.
Identity-stop verification: **705 tests passed in 138.81 seconds** in locked
WSL Ubuntu, including retained wrong/missing/blank model responses and refusal
of subsequent dispatch. The focused transport/schedule/journal set passed all
27 tests. Ruff lint/format and diff checks pass. All transport was synthetic;
no model starts or quality measurements were added.
Verification: **690 tests passed in 128.67 seconds** in locked WSL. After adding
the reused transport helper to the journal's implementation fingerprint, all
18 transport/journal tests passed again in 5.38 seconds. Ruff lint/format and
diff checks passed. The nine new transport tests use synthetic intercepted HTTP.

`recovery_packet.inspect_packet` replays the complete ten-case preparation set,
requiring two cases per category, distinct safe case IDs, exact source-backed
drafts, matching structural reports, and attributed preparation entries for every
check. It rejects hidden holds, omitted checks and preparation records that claim
fact acceptance. Its fingerprint binds the selection, rubric, case inputs/plans
and preparation reviews. `require_ready` additionally refuses unresolved holds
or source gaps, and can require an exact previously frozen fingerprint. A ready
preparation packet still requires semantic audits and runtime/dispatch preflight;
it is neither execution authorization nor calibration evidence.
The actual latest packet replays all ten cases and 358 checks, with 20 holds and
no source gaps; `require_ready` correctly refuses it. Receipt:
`qualification/m4-packet-gate-20261118/verification.json`. Software verification:
**699 tests passed in 127.63 seconds** in locked WSL, including nine new packet
adversaries; Ruff lint/format and diff checks passed. No inference calls occurred.

`recovery_requests.prepare_next` now joins the packet gate to deterministic
request construction. It requires the manifest's exact packet fingerprint,
case bindings/order, transport settings and both stage prompts. Verifier inputs
are rebuilt from verified evidence; scorer inputs are reconstructed from the
saved accepted fact response/audit and checked again against the source bundle.
Review commentary is excluded from model input. Pending requests or outstanding
audits cannot release a new prepared request. The output includes the actual
Instructor wire receipt but remains execution-disabled until fresh runtime/model
identity and token-fit checks are connected. No real recovery journal has been
allocated or dispatched.
Verification: **702 tests passed in 132.37 seconds** in locked WSL; the focused
request/audit suite passed 20 tests. Ruff lint/format and diff checks passed.
The new request tests cover both stages, pending/audit barriers, excluded audit
commentary and preparation drift, using synthetic data only.

Prepare ten previously exposed original-baseline cases, two per category. Include
all three known human D2 failures and cases that distinguish missing obligations,
invalid tips and valid API claims wrongly rejected. Publish the exact item list
and selection rule before any calls. This deliberately targeted set is biased
toward known failures and cannot establish assessed readiness.

Use the already saved V15 decisions for those same items as the paired comparator;
do not spend new control calls or describe the comparison as a contemporaneous
randomized experiment. Candidate model proposed: pinned Qwen3.5-122B-A10B, so the
experiment changes verification procedure rather than model and procedure at
once. Freeze weights/build/template/settings anew before execution; current
runtime availability is not assumed. Do not fall back to hosted models.

Proposed ceiling: **20 starts total**, one verifier and one scorer per case,
**one attempt per stage**, no retries. A failed/unresolved verifier skips its
scorer without donating that allowance. Stop on two consecutive structural
failures, any unknown request outcome, source/runtime drift, context overflow or
the ceiling. Also stop on the first semantic audit finding of an unsupported
decisive claim or ignored decisive uncertainty; inspect each verifier before its
scorer. A stopped run retains all scheduled cases in the coverage denominator.
No schema repair, truncated context, selective rerun or silent budget extension.

Carry forward durable start/outcome records, exact requests/raw completions,
single-writer protection, unknown-outcome accounting and explicit transport
failure retention from the existing staged implementation. Exact wire token
preflight must include sources, checklist, response schema and downstream memo.
If it will not fit, revise and freeze the protocol **before** a request; do not
silently drop claims. Changes to Herd services remain outside this project.

The [November 18 draft sizing measurement](M4-TOKEN-SIZING.md) finds five compact
verifier inputs larger than the previous 16,384-token context, with a maximum
of 43,519 input tokens before instructions/schema/output. Compact JSON alone
does not resolve the context constraint. No inference was attempted.
The subsequent separately owned 65,536-token Mac capacity check fits all ten
draft fact requests including actual template/schema and an 8,192-token output
allowance (maximum total 52,498). This is preparation only: final freeze, source
holds, model identity and the actual scorer memo still require preflight. The
temporary server/tunnel were stopped and no inference allocation was consumed.

Advance only with ten complete audited pairs, at least 8/10 agreement in every
dimension, no D2/D3 false approvals, more total matches than paired saved V15,
no dimension decrease, no increase in false approvals, and no unsupported
decisive findings. Report false rejections, rationales, source gaps and exposure
limitations even if those gates pass. This is a development screen, not a claim
that a sample of ten certifies reliability.

Passing supports a separately frozen confirmation design, not automatic assessed
calls. The previous three assessed allocations remain consumed. A further full
baseline needs an explicit recorded allocation extension and the unchanged
>=80%-in-each-dimension rule, with fifty retained items and twenty authentic
reviews. No repeat human review is requested for this offline task. M5 remains
preserved and unqualified until M4 succeeds.

## Offline use and verification

### November 18 structural runtime bindings

`m4-structural-bindings-20261118/packet-structural` binds three previously held
questions to existing v3 runtime captures: b01-item-0013 K0013/K0024 use the
positive and scaled-modulus runs, and b02-item-0008 K0018 uses recorded node-call
returns. These are explicitly classified as runtime observations, not API
documentation. The original questions retain their focus with added limits.

Both E=29000 and E=29 cases initialized and analyzed successfully; the recorded
displacement ratio is 1000. That does not make E=29 universally invalid: it may
represent a different material, and no physical unit labels were supplied to the
engine. Logged node-definition returns are null, distinct from printed model
information and configured DOF counts. The verifier must decide what these
limited observations establish and report residual uncertainty; the explicit
runtime-applicability audit remains required.

All ten cases replay: **358 checks, 342 prepared questions, 16 holds and zero empty
bindings**. Candidate/task text, dimensions, parent/check identities and every
runtime record are unchanged. No rerun, accepting fact audit, model score or human
rating was produced. NAS archive `Handoff/P1-03/operator/m4-structural-bindings-20261118`
has **176 verified files**, manifest SHA-256
`7b58e82212085565f41a3a79061e9915ea3812a38a7fc6710ac5c51177006a52`.
Previous packets remain intact; changed requests need fresh exact token preflight.

### November 18 FreeCAD document-creation binding

The subsequent `m4-freecad-attachment-20261118/packet-freecad` adds a byte-exact
excerpt of `DocumentPy::addObject` from the already retained, permission-cleared
FreeCAD 1.0.2 source to the cone item's K0023 bindings. It also binds the retained
`Part::Cone` property implementation. Together with the existing example and
`ConePy` constructor source, this covers the distinction between conical geometry
and document-object creation without inventing an absent `Part.Cone` API.

The check's question, subject and dimensions are unchanged. Candidate/task text
and human ratings are unchanged. All ten cases replay through the packet gate:
**358 checks, 339 prepared questions, 19 holds and no empty source bindings**.
This clears a preparation hold, not a factual verdict or accepting audit.
No inference or new runtime experiment occurred.

NAS archive: `Handoff/P1-03/operator/m4-freecad-attachment-20261118`, **176 files
verified**, manifest SHA-256
`e98ff00803e267abf51c58d999788b841d1255d1891051748c5b90a15574c627`.
The previous simulation-scope packet remains intact. Updated input bytes require
new exact token preflight before execution.

### November 18 simulation scope revision

The separately archived `m4-simulation-scope-20261118/packet-simulation-scope`
revises only the question for `baseline-001-b02-item-0040` K0016. The earlier
preparation hold demanded evidence about every non-implicit result, while the
candidate describes a stiffness-related failure scenario. The new question
distinguishes that scenario from a universal assertion, still requires primary
evidence, and explicitly forbids inferring a particular failed numerical run.
It preserves the separate original-task/substituted-system comparison.

All ten packets replayed successfully: **358 checks, 338 prepared questions,
20 holds**. Candidate/reference/source inputs and human labels are unchanged;
there are no new observations, accepted fact audits, scores or model calls.
The four other simulation holds remain: unspecified convergence warnings,
unqualified BDF preference, shape-related corruption/crashes, and claimed
tolerance-induced instability. Prepared questions are not verified facts.

The preceding unit-convention packet remains intact. The new revision is copied
to NAS `Handoff/P1-03/operator/m4-simulation-scope-20261118`, with **175 files
verified**, including its manifest. Manifest SHA-256:
`cb2398927887588ee2acc0682295f58446b8fb64642e954810d07cd63da34545`.
Its modified verifier request must be re-preflighted before execution; the earlier
64k sizing result concerns the prior draft bytes.

Run inside the repository's locked WSL Ubuntu environment:

```bash
uv run --locked python -m aia_mp1.recovery_checks \
  --input /EXTERNAL/fact-input.json \
  --rubric config/rubric.json \
  --sources /EXTERNAL/retained-sources \
  --plan /EXTERNAL/check-plan.json \
  --observations /EXTERNAL/observations.json
```

Paths are placeholders, not a prepared operator packet. Omit `--observations` to
inspect source coverage only. Output goes to stdout; inputs are never written.
Exit 0 means structural checks completed without source gaps/unresolved findings,
**not** truth, calibration or permission to execute. Exit 1 reports known gaps;
exit 2 reports invalid input without echoing its contents. Preserve any real
plans/responses/reports outside Git, separately from sealed historical artifacts.

Synthetic adversarial tests exercise skipped tips/task/steps, source-role
substitution, changed versions and bytes, overlapping spans, incomplete responses,
invented citations, foreign checklist lineage, unresolved evidence, and misleading
but structurally valid citations. Full-suite validation is recorded with the
implementation commit. No real source finding or model quality measurement is
produced by these tests.

Verification: **525 tests passed in 109.98 seconds** in locked WSL Ubuntu with
the analysis extra and optional ReportLab renderer, including 26 new recovery
tests. Ruff lint/format and the offline CLI help check pass. No live requests.
