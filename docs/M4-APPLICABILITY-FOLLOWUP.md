# M4 applicability review and exact-version research

Historical checkpoint. The subsequent [runtime-evidence implementation](M4-RUNTIME-EVIDENCE.md)
provides explicit empirical bindings for ten checks, leaving 33 preparation holds.

November 17, 2026. Five preparation holds are removed, leaving **43 holds across
358 checks**, including one empty binding. There are 315 prepared questions and
43 attributed reasoning notes. No model findings or rubric scores were produced;
your frozen reviews are unchanged. M4 still fails the original D1/D6 thresholds.

## Preparation corrections

Three ArcPy checks now bind the retained geometry/token and cursor sections:
`b02-item-0011` K0008, K0019 and K0020. The source describes geometry-property
ownership, geometry retrieval using `SHAPE@`, and cleanup on leaving a cursor
context. Exact coordinate-tuple and precision questions remain held. The cleanup
question no longer adds an unlimited guarantee for unrelated resources or abnormal
process termination.

Two checks move to attributed workflow reasoning while retaining their IDs,
subjects and required dimensions. `b02-item-0007` K0032 concerns keeping formatted
text for an audit trail, not a promise of safe numeric round-trip conversion.
`b02-item-0019` K0025 recommends up-to-date valid geometry before interpreting
volume, not a promise that a getter rejects every invalid shape. Their separate
API questions remain required. These corrections remove requirements invented
during preparation; they do not award either candidate a pass.

## OpenSees research results

A predeclared ten-case standalone WSL probe pinned **both** `openseespy` and
`openseespylinux` to **3.5.1.3**, using Python 3.10.22. The engine reports 3.5.1.
Pinning only the meta-package would allow a newer backend; the separate lock
prevents that substitution. Official package metadata and wheel hashes are retained.

| Predetermined case | Observed result |
| --- | --- |
| Two-DOF node with two fixity flags | Created two constraints |
| Same node with a third flag of zero or one | Also created two constraints; third flag had no observed effect |
| Same node with only one flag | Setup exception and an invalid-count warning |
| Stable truss with normal flags | Analysis returned zero |
| Stable truss with a third flag of zero or one | Analysis returned zero and the same displacement as the control |
| Same truss with negative area | Initialized and analysis returned zero, with negative displacement |
| Same truss with modulus reduced by 1,000 | Analysis returned zero; displacement increased by 1,000 |
| Duplicate existing constraint | Setup exception with an explicit already-constrained diagnostic; analysis was not attempted |

Node-definition calls returned `None` in these cases. That is not a DOF-query
result. Successful execution does not make negative area physically valid or
validate declared units. These small examples establish only their recorded
outcomes, not behavior of every build, model, constraint handler or input.

The extra-flag result conflicts with both the candidate's necessary-singularity
claim and the earlier reviewer-comment statement that extra flags necessarily
cause an argument-count error. **This is a rationale discrepancy, not an edit to
the frozen human ratings.** No result from this probe is presented as calibrated
model agreement or as an engineering-design validation.

## Environment incident and recovery

The first probe command unintentionally inherited the project's
`UV_PROJECT_ENVIRONMENT`. It temporarily replaced the project environment with
Python 3.10. The locked project environment was restored to Python 3.12.16, and
the probe now uses an explicitly separate environment. **94 recovery-pipeline
tests pass** after restoration. Repository dependency files and locks are unchanged.

The original identity captured the wrapper hash. A separate follow-up captured
the native module hash in the isolated environment using the same locked wheel
versions. That later identity is not represented as a capture from the original
process. The incident and provenance limitation remain in the external record.

## Evidence and next step

Evidence is outside Git at
`artifacts/evidence/P1-03/qualification/m4-recovery-applicability-20261117/`.
The current `packet-scope` preserves all parent text, candidate/task/rubric content,
child IDs, subjects and dimension routing. Five questions/bindings change and two
explicitly attributed notes are added. Replay checks all ten packets, research
case accounting and **815 entries across five previous seals**.

Remaining holds: GIS 11, AEC 12, structural 14, CAD 1 and simulation 5.
All preparation fact verdicts remain null and accepting audit flags false.
The probe remains research-only, outside model context. The
[measured-evidence supplement](M4-EMPIRICAL-EVIDENCE-PLAN.md) specifies the next
implementation: separate empirical evidence with complete provenance and limits,
without pretending it is primary API documentation. This should allow applicable
runtime questions to be addressed explicitly; documentary gaps remain separate.

No Mac or Herd changes, no model calls and no new scores. Cumulative starts remain
388. The twenty-start development trial remains unallocated and unstarted, all
three assessed allocations remain consumed, and the M5 packet is preserved.
