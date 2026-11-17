# M4 evidence contract v2 and child-check drafts

November 17, 2026. The offline contract now distinguishes API documentation,
original-task comparisons, mathematical derivations and workflow reasoning.
All **83 compound spans** flagged by the [source audit](M4-SOURCE-AUDIT.md) have
explicit child-question drafts. The ten cases now contain **357 checks**, linked
to all **175 unchanged parent spans**. This is a prepared decomposition, not a
claim that every question is already atomic or every citation applicable.

The frozen candidate/task/rubric content is unchanged. No model requests, Mac use,
human-label amendments, real-item observations or scores occurred. Cumulative
starts remain 388; M4 still fails the original per-dimension acceptance rule.
The proposed twenty-start development trial is unallocated and unstarted.

## Evidence roles and review gates

[recovery_evidence.py](../src/aia_mp1/recovery_evidence.py) introduces
`recovery-evidence-v2`, separately from the unchanged v1 checklist validator.
Each prepared child fixes its question, subject, evidence kind and bindings.
The model cannot change classification to bypass a missing API source.

| Evidence kind | Bound authority | Limit |
| --- | --- | --- |
| `api_contract` | Retained, permission-recorded `R.fact.*` excerpt | Task text or an authored note cannot establish an API contract |
| `task_comparison` | Unchanged `R.task`, version `frozen-task` | Agreement with the task does not prove API behavior or numerical correctness |
| `mathematical_derivation` | Attributed `E.N*` derivation with exact premises | Author assumptions and algebra still require checking; not primary documentation |
| `workflow_reasoning` | Attributed `E.N*` precaution/process rationale | General advice cannot prove a runtime outcome or technical interface |

A reasoning note contains its author, assistant/owner origin, creation time,
exact premises, reasoning and limitations. The complete record is fingerprinted.
Candidate premises remain stated givens, not independently verified facts.
Premises may cite only original candidate/task text or retained primary excerpts;
rubric text, authored reference summaries and other notes cannot become hidden
premises. Unbound notes are rejected. No supplied calculation or candidate code
is executed by the validator.

Exact citations into a note refer to its `reasoning` text, using zero-based
Unicode character offsets. Primary artifacts retain the existing byte/hash,
permission and extraction checks. Evidence with the wrong authority or changed
version fails validation. Empty bindings remain explicit gaps; they cannot support
a conclusive observation. Correctly typed evidence still requires semantic review.

The scorer accepts both protocol versions. V2 additionally requires an
`EvidenceFactAudit` with `evidence_kinds_reviewed` and
`authored_reasoning_checked`, alongside the existing complete-checklist,
source-applicability, no-label-leakage and per-check acceptance requirements.
A legacy audit cannot unlock v2 scoring. Classification mistakes or unsupported
reasoning must be rejected even when their JSON passes validation. Audit records
are attributed assertions, not automatic or independent proof of truth.

The verifier/scorer wire views retain note attribution, premises and limitations.
Unmeasured [fact](../prompts/recovery-facts-v2.md) and
[score](../prompts/recovery-score-v2.md) prompts explain these roles. V1 prompts
and historical inputs are preserved. The six frozen rubric anchors, D4 sign-off
interpretation, unresolved-score behavior and separate score audit are unchanged.
Every resulting development report remains `calibration_eligible: false`.

## Parent–child coverage

The embedded v1 parent is fingerprinted and validated against the same input and
rubric. Its nonoverlapping spans still cover every non-whitespace task/candidate
character. Each child must remain within its named parent; the union of children
must cover that parent's text. Required parent dimensions and kind cannot be
removed. Any child classified as an API claim also requires D3 review.

Children may share subject text when several propositions depend on the same
sentence or code expression. Their distinct questions specify what to inspect;
duplicate subject/question pairs are rejected. This avoids cutting off qualifying
words such as “for the Truss element” and accidentally assigning area to the
material. Shared text and coverage do not prove complete semantic decomposition.

The prepared packet retains the entire original parent span for each child, with
an explicit question and parent ID. Every classification/atomicity and source-
applicability acceptance flag remains false pending a new audit. Earlier source
review notes are kept outside the model-facing inputs; no reviewer ratings or
accepting audits were created for these cases.

## Prepared evidence and remaining gaps

| Evidence kind | Child checks | Unbound |
| --- | ---: | ---: |
| API contract | 187 | 3 |
| Task comparison | 125 | 0 |
| Mathematical derivation | 9 | 0 |
| Workflow reasoning | 36 | 31 |
| **Total** | **357** | **34** |

Seven attributed reasoning notes cover selected unit/disposable-copy precautions
and mathematical identities for the truss, stiff ODEs, cone and sphere. Geometry
formula coefficients were checked independently with rational arithmetic. These
notes remain unaccepted for semantic scoring; they are not new model measurements.

**The 34 child gaps are not comparable to the previous five unbound parent spans.**
Separating a mixed passage exposes missing evidence for individual propositions.
Existing primary bindings are carried forward only as retrieval candidates;
some need narrowing, replacement or an explicit insufficient finding even when
the list is nonempty. No source-retrieval count establishes factual completeness.

Evidence is outside Git at
`artifacts/evidence/P1-03/qualification/m4-recovery-evidence-v2-20261117/`.
Each case has the unchanged input, a v2 plan, structural report, child checklist,
draft verifier view and preparation status with exact lineage. The preparation
and read-only replay scripts are retained. There are no real-item observations,
scores, accepting fact audits or accepting score audits.

Replay verifies all ten v2 plans and wire drafts, all ten parent reports, unchanged
candidate/task/rubric content, all 83 requested decompositions and **250 entries
in the two previous seals**. Source copies are byte-identical to the sealed audit.

Verification: the full locked WSL suite passed **592 tests**, with one optional
PDF test skipped because ReportLab was absent. The follow-up with the optional
renderer passed **95 affected/optional tests**, including that skipped test and
all **40 new evidence-contract tests**. Thus all 593 collected tests were
exercised successfully across the two runs. Lint, format and CLI help checks pass.
The follow-up also checks rejection of a non-object plan after that guard was
added. This is software validation, not model quality or calibration evidence.

## Offline inspection and next work

Inside the locked WSL environment:

```bash
uv run --locked python -m aia_mp1.recovery_evidence \
  --input /EXTERNAL/input.json --rubric config/rubric.json \
  --sources /EXTERNAL/sources --plan /EXTERNAL/plan.json
```

Paths are placeholders for retained case files. The command reads only; exit 1
reports gaps, exit 2 invalid input, and exit 0 means structural inspection found
no gap—not semantic acceptance or execution permission. The scorer's existing
CLI selects the v1/v2 contract from the plan and requires the corresponding audit.

Next, review the child evidence classifications, supply defensible reasoning for
the 31 unbound workflow checks, and resolve or explicitly retain the three API
gaps and other partial sources. Re-audit question atomicity, applicability and
reasoning before staged transport, target-tokenizer preflight and a frozen bounded
development package. No new action is needed from Chad for this offline work.
