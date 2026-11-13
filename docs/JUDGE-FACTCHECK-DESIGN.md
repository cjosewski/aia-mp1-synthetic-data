# Source-grounded judge experiment — V8 design

Status: design and draft prompts prepared November 13, 2026 following Chad's
“Go”. Not implemented, frozen for execution, or measured. No new inference is
part of this design checkpoint. The documented request total remains 92.

## Purpose and boundaries

The [fixed V7 screens](JUDGE-QUALIFICATION-RESULTS.md) produced valid passage
references but all three models approved an API defect. Citation validity did
not establish factual support. Test whether separating claim verification from
rubric scoring improves evidence use without turning technical errors into
unrelated context failures.

Preserve the seven-field candidate, task, rubric, frozen human ratings, prior
attempts and production judge defaults. Use the same five known development
cases, one per category. These cases are not fresh blind confirmation. Human
ratings and reviewer comments remain unavailable to either model stage.

## 1. Prepare a frozen reference bundle

Existing R.source passages are authored summaries of approved sources. They are
not verbatim primary documentation and do not explicitly support every claim.
Retain those passages unchanged and label their authority. Add exact excerpts
from the already pinned, permission-cleared primary artifacts where available.
Do not silently treat a task requirement, summary or source URL as API proof.

Each added excerpt has an application-assigned R.fact.N ID, source identifier,
revision/version, original artifact SHA-256, path and byte range (or page and
extraction method), exact extracted text and text SHA-256, retrieval date,
license/permission record and allowed use. Preserve the original artifact and
extraction receipt outside Git. Distinguish `task`, `authored_summary`,
`primary_excerpt` and `rubric` in the reference catalog. The application builds
and hashes the catalog; the model cannot supply its own authoritative sources.

Review coverage across every candidate field and list entry, including API
owner/member/arguments/return interface, task givens, actual hazards, procedural
dependencies and tips. Record a source gap when pinned material does not resolve
a claim. New material requires provenance and permission clearance before entry.
An absent member in a partial excerpt does not prove that member nonexistent.
Missing or conflicting evidence yields `insufficient`, not a forced conclusion.

Select relevant excerpts without expected ratings, correction keys or reviewer
comments in the model input. Preserve selection rationale externally and disclose
that this bundle was prepared after seeing known-case results. This remains
development evidence even with label-free messages. No live retrieval, candidate
execution, or model-generated source quotation is allowed during judging.

## 2. Stage A: verify material claims

The [draft verifier prompt](../prompts/judge-v8-facts-draft.md) requests facts,
not D1–D6 ratings. Input contains the complete candidate, original task/context,
typed reference catalog and exact C.* / R.* passage mappings. No prior judge
responses or expected labels are supplied.

Proposed strict response contract (all named fields required; extra fields rejected):

| Field | Type and meaning |
| --- | --- |
| `findings` | Array of claim records; may be empty only if every candidate passage is accounted for as a non-claim |
| `findings[].candidate_ids` | Nonempty unique C.* IDs locating the claim |
| `findings[].claim` | Nonblank concise description of the material claim |
| `findings[].kind` | `task_alignment`, `api_contract`, `procedure`, `hazard_precaution`, `professional_scope`, or `tip` |
| `findings[].task_refs` | Unique R.* IDs typed as task; empty allowed |
| `findings[].source_refs` | Unique R.* IDs typed as primary excerpt or authored summary; empty allowed |
| `findings[].status` | `supported`, `contradicted`, or `insufficient` |
| `findings[].explanation` | Concise public finding explaining evidence and its limits; nonblank |
| `non_claims` | Array of `{candidate_id, reason}` for passages containing no material claim; unique C.* IDs and nonblank reasons |

Every supplied C.* ID must occur in a finding or non_claims. Multiple findings
may cite the same passage; a non_claim cannot also appear in findings. A finding
needs at least one task/source reference unless its status is insufficient.
Rubric anchors are never factual support. A supported/contradicted API-contract
finding requires a primary excerpt, not solely task text or an authored summary.
The validator can enforce that citation role; an audit must still check entailment.

Check all assertions within a passage, including conflicting statements across
answer, steps and tips. Coverage of passage IDs does not demonstrate complete
semantic review. Valid arithmetic or deduction can be described briefly from
supplied givens; never claim execution or supply private reasoning. A claim may
be split into several findings if its parts have different support.

After validation, the application assigns F0001, F0002, etc. in response order
and binds the memo to the candidate, bundle, prompt, raw completion and accepted
attempt hashes. A valid insufficient finding is an outcome, not a retry trigger.

## 3. Stage B: score the rubric with an auditable memo

The [draft scorer prompt](../prompts/judge-v8-score-draft.md) receives the original
candidate, same references, frozen rubric and validated Stage A memo. Findings
are explicitly untrusted model assessments. The scorer can dispute them using
original evidence; they are not a replacement for reading the candidate.

Proposed strict wrapper:

| Field | Type and meaning |
| --- | --- |
| `status` | `ready` or `unresolved` |
| `judgment` | Existing V7 `PassageJudgment` when ready; null when unresolved |
| `dispositions` | Exactly one record per application-assigned F ID |
| `dispositions[].finding_id` | Existing F ID from this accepted Stage A attempt |
| `dispositions[].position` | `accepted`, `disputed`, or `needs_evidence` |
| `dispositions[].dimensions` | Unique affected D1–D6 IDs; empty only when irrelevant to all ratings |
| `dispositions[].reference_ids` | Unique supplied R.* IDs; disputes require task/source evidence, not only rubric anchors |
| `dispositions[].explanation` | Nonblank explanation of disposition, relevance and any independent anchor effects |
| `unresolved_reasons` | Nonblank strings; empty when ready, nonempty when unresolved |

An accepted insufficient finding or needs_evidence disposition affecting any
dimension requires unresolved status. If irrelevant, explain why; audit this
decision for hidden uncertainty. Additional material uncertainty found by the
scorer also requires unresolved status and an explicit reason. A disputed
finding needs affirmative evidence for the scorer's replacement interpretation.

Only ready output passing every wrapper and V7 check projects to canonical
Judgment. Keep unresolved raw output and memo; never substitute six binary
defaults or report partial dimensions as a completed case. Do not alter V7's
candidate evidence IDs, per-dimension requirement roles or strict binary type.
The augmented catalog must be validated separately because the existing V7 input
validator deliberately rejects extra keys. Preserve that validator and format.

Score anchors independently: incorrect implementation does not alone make the
context unclear (D5); a real API used for the wrong mathematical effect does not
alone prove an invented API (D3). D1 cannot approve a defective core procedure
merely because it has steps. D2 must evaluate the actual hazard and precaution,
D4 unjustified professional approval, and D6 the correctness of the tips. One
defect affects several dimensions only where each anchor is independently violated.

## 4. Matched experiment and bounded requests

Nominate the already pinned GPT-OSS-20B MXFP4 for this design: it achieved 27/30
on fixed V7 versus 23/30 for each alternative. This is a small-sample development
basis, not qualification or a general superiority claim. Preserve the archived
weight hash, Mac, llama.cpp build, embedded template, context 16,384, one slot,
temperature 0.1, 4,096-token output limit and 300-second timeout. Record all stage
schemas/settings in a new manifest before launch. No hosted fallback or Herd change.

For each of the same five cases, run:

1. Control: single-stage V7 scoring with the augmented reference bundle.
2. Treatment A: claim verification with that identical reference bundle.
3. Treatment B: rubric scoring using A's first accepted memo and that bundle.

Both arms use the identical typed passage catalog, including R.fact.N. Add a
separate input adapter that verifies it and strips neither original text nor
authority metadata. Control retains the V7 prompt/output contract. Audit the
adapter before use; changes in source content must not differ between arms.
Archived V7 is a historical comparator only because it used less source material.

Freeze ordering: original case order; odd-numbered cases control/A/B,
even-numbered cases A/B/control. Maximum two attempts per stage, **15 nominal
requests, 30 maximum new starts**, proposed cumulative ceiling **122 after 92**.
This allocation is proposed and unactivated at this design checkpoint; unused
prior allocations do not transfer. There are no extra model preflight requests.

Retry only transport, schema or lineage failures, using the identical request.
Never retry valid disagreement or uncertainty. Never regenerate A because B
disagrees or fails. A exhaustion leaves B skipped. Stop globally after two
consecutive transport/schema/lineage failures, any unknown outcome pending
inspection, the request ceiling, or completion of all scheduled stages. Structural
acceptance resets the consecutive-failure count, including a valid unresolved
response. Stop and preserve the receipt on runtime/model/input hash mismatch.

Each stage writes a durable start before dispatch. Resume consumes all starts,
including interrupted/unknown requests; no hidden Instructor repair or client
retry. Bind B to one accepted A attempt and identical item/bundle/runtime hashes.
Raw responses, errors, parsed records, resolved citations and canonical projections
are separate immutable artifacts outside Git. Freeze source adequacy and token
fit before execution; if the package cannot fit the declared context, revise the
protocol before launch, not during a run. Never silently truncate evidence.

## 5. Reporting and advancement

Keep all five selected cases in coverage denominators, including skipped and
unresolved cases. Report A structural acceptance/coverage and source adequacy;
control/B readiness; first-attempt acceptance versus recovery; failures, unknowns,
actual calls, tokens and latency. Distinguish schema-valid from ready. Agreement
uses resolved decisions with its denominator shown, plus coverage out of five;
do not count unresolved as a match, a binary failure, or a false approval.

Compare all six dimensions and false approvals/rejections for both arms. Report
matched-pair gains and regressions separately; do not compare different resolved
subsets without naming them. Audit every finding, disposition and explanation
against original passages, including unsupported matches to human ratings.
Source entailment and completeness are semantic audit tasks, not parser guarantees.

Advance only to broader development if both arms cover all five cases, treatment
matches at least 4/5 in every dimension, has zero D2/D3 false approvals, has more
total matches than control with no per-dimension decrease and no increase in
false approvals, and the semantic audit finds no unsupported decisive finding or
ignored material uncertainty. A tie does not establish benefit from extra stages.
Failure means preserve and diagnose, not auto-extend the budget. This is not a
statistical superiority claim. Fresh blind confirmation and assessed requirements
(20 authentic human labels, 50 retained items across all categories, complete
coverage and at least 80% agreement per dimension) remain separate gates.

## 6. Implementation sequence and verification

1. Implement strict response models, typed catalog adapter and canonical projection
   behind a separate development entry point. Keep assessed commands unchanged.
2. Implement immutable stage ledger, lineage/resume checks and paired reporting.
3. Prepare permission-cleared excerpts and coverage/gap receipt outside Git;
   review token fit and freeze package, prompts, sources, schemas and settings.
4. Run locked WSL project and portable tests, lint, package integrity and shell
   checks. Only then execute the bounded development experiment and audit it.
5. Archive the complete Mac folder and return/audit on the NAS, retaining previous
   runs; stop the owned server. No automatic subsequent experiment.

Tests must cover foreign/duplicate/missing C/R/F IDs; wrong authority roles;
task-only API proof; source hash changes; incomplete coverage or non-claim overlap;
foreign item/A lineage; ignored findings; unresolved-to-canonical rejection;
boolean ratings; disputed findings without evidence; valid insufficient results
without retries; unknown-outcome consumption; global stop/resume; skipped-stage
denominators and paired gains/regressions. Use explicitly synthetic fixtures for
contradictory fields, absent evidence, wrong mathematics with clear context, and
prompt injection inside supplied material. Structural checks must not be described
as automated proof of factual truth. No new human review is needed for implementation.
