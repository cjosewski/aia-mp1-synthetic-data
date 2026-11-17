# M4 child-check preparation review

Historical checkpoint. The subsequent [contract-source follow-up](M4-CONTRACT-FOLLOWUP.md)
removes eight holds, leaving 48 with the same 358 checks. The counts below remain
the recorded preparation-review result.

November 17, 2026. The evidence follow-up reduces **34 unbound checks to one**
and records a preparation disposition for **358 checks**. The review also identifies
**56 source-applicability holds**, including that one unbound check. The other
302 questions are prepared for a verifier; they are not verified facts or passing
rubric judgments. **The current packet is not ready for model execution.**

Candidate answers, original tasks, rubric and human reviews remain unchanged.
No model calls, new scores or Mac use occurred; cumulative starts remain 388.
M4 remains open at the recorded V15 baseline result, with D1 70% and D6 65% below
the original 80%-per-dimension requirement. The proposed twenty-start development
trial is still unallocated and unstarted.

## Evidence completed

The separate `packet-reviewed` revision contains 41 attributed reasoning notes,
up from seven. New notes address explicit field names, CRS provenance, unit
consistency, guard ordering, diagnostic comparisons and other workflow questions.
Each new note binds the exact candidate subject and original task, states its
assumptions and limitations, and supplies no candidate verdict. Conditional
reasoning cannot establish an API contract or an actual runtime outcome.

Licensed NumPy 2.3.1 source now supplies the missing `exp` contract and replaces
an unrelated solver citation for `shape`. Two source files and the BSD license
are retained with Git blob IDs, SHA-256 hashes and a permission receipt.
[Exponential documentation source](https://github.com/numpy/numpy/blob/v2.3.1/numpy/_core/code_generators/ufunc_docstrings.py),
[shape documentation source](https://github.com/numpy/numpy/blob/v2.3.1/numpy/_core/fromnumeric.py),
[license](https://github.com/numpy/numpy/blob/v2.3.1/LICENSE.txt).
The candidate specifies no NumPy version; these sources do not attest to an
installed runtime.

Existing licensed sources were also rebound more precisely: Revit storage/null
examples and instance filtering, FreeCAD imports, internal units and sphere
validation, and SciPy imports and result fields. Source text and its original
license/provenance remain intact. These repairs establish relevant evidence for
inspection, not automatic support for the candidate's conclusions.

An official OpenSees FAQ and its license were retrieved for research. The FAQ
discusses consistent input units, but its additional documentation reuse scope
was not silently assumed. Those two files remain outside model source context;
the corresponding primary binding remains unresolved. Research access and
dataset reuse are separate decisions.

## Corrections to our draft questions

The review corrects the preparation itself without changing human labels:

- Original-task checks now ask whether the **whole candidate fulfills the
  requirement**, rather than merely asking what the requirement says.
- The OpenSees unit-convention question no longer misreads advice to use
  consistent units as a claim that software automatically enforces them.
- Plotting purpose, prose import notation and a document-variable abbreviation
  move to workflow reasoning. Their separate API checks remain intact.
- Mathematical expectations may inform verification without adding a requirement
  to print numerical values when the task did not request that output.
- A suggested operating environment is not treated as a claim that this host
  has the software installed. Internal length units are not expanded into a claim
  about arbitrary GUI display settings.
- One additional API child separates a FreeCAD source-unit assertion from unit
  consistency advice. This accounts for the increase from 357 to 358 checks.

The unmeasured [verifier v3 prompt](../prompts/recovery-facts-v3.md) makes the
candidate-relative meaning of supported, contradicted and insufficient explicit.
It retains the existing response schema and evidence roles. Earlier prompts and
draft packets are preserved. Scorer code, scoring prompt and acceptance rules
are unchanged.

## Remaining source-applicability holds

| Category | Holds | Representative limitations |
| --- | ---: | --- |
| GIS | 14 | Exact cursor value types, geometry/tuple ownership, workspace scope and precision claims beyond the retained cheat sheet |
| AEC | 15 | Complete accessor and HasValue contracts, named exceptions, framing-specific selection and transaction outcome/member semantics |
| Structural | 14 | Unit enforcement, negative-area or extra-flag behavior, claimed singularity and exact diagnostic messages |
| CAD | 5 | GUI/platform availability, surface-to-document attachment and behavior for invalid shapes |
| Simulation | 8 | Universal mismatch exceptions, input mutation, crashes, instability, warnings and solver-preference claims |
| **Total** | **56** | **Includes the one empty source binding** |

These are preparation holds, **not 56 failed human criteria**. A nonempty list
of citations can still be insufficient for the precise proposition. An example
showing one valid operation cannot establish all failure behavior or prove that
an unlisted member does not exist. Every hold has an exact case/check ID and
reason in the external review records.

All entries retain `fact_verdict: null` and `fact_audit_accepted: false`.
No `Observations`, accepting fact audits, scores or score audits were fabricated.
All case-level execution flags remain false, including cases with prepared
questions. The current completeness gate prevents the proposed trial from
proceeding with these unresolved source holds.

## Preservation and validation

Evidence is outside Git at
`artifacts/evidence/P1-03/qualification/m4-recovery-semantic-audit-20261117/`.
Each case includes a reviewed checklist, versioned plan and wire draft, explicit
changes from the previous plan, and attributed preparation-review records.
Source additions update input/plan hashes; original candidate/task text, rubric,
parent check text and existing child subject/dimension routing are preserved.

Read-only WSL replay verifies all ten revised cases, five downloaded Git blobs,
source permissions and bytes, exact note premises, review/check coverage and
**385 entries across three previous seals**. The earlier 357 checks retain their
IDs and subjects within each case; the additional CAD check is appended.

No application code changed in this checkpoint. The previous implementation's
593 successfully exercised tests remain its recorded result; this source/prompt
revision is validated through artifact replay, not a claimed new test-suite run
or model-quality measurement. The interrupted session was resumed by checking
existing artifacts and repeating only the read-only replay.

## Next work

Resolve the shared primary contracts behind the 56 holds before transport or
token preflight. Prioritize exact Revit parameter/transaction contracts, ArcPy
cursor/geometry contracts and the asserted OpenSees/SciPy failure behavior.
Preserve uncertainty where a source cannot establish the claim. If those facts
cannot be established within the current evidence policy, record a concrete
protocol change before proposing a live trial; do not turn unresolved checks
into passes or silently change the 80%-per-dimension criterion.

No new action is needed from Chad for this offline follow-up. The corrected M5
cohort and review packet remain preserved.
