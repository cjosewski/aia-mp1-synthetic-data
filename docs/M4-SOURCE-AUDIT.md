# M4 recovery source and checklist audit

Subsequent checkpoint: [evidence v2](M4-EVIDENCE-V2.md) implements the role
distinctions and prepares child questions for all 83 flagged spans. The original
audit and sealed packet below remain unchanged; child applicability review remains.

November 17, 2026. All **175 spans across ten development cases** received an
attributed assistant source review. Thirteen of eighteen missing source bindings
were repaired; **five remain unbound**. **83 spans need splitting** before a
verifier can answer one question per claim. This completes the source audit of
the draft, not preparation of a model-ready checklist.

No model calls, Mac use, new scores or human-label changes occurred. M4 remains
open at the recorded V15 result: 79.2% overall, D1 70% and D6 65%, below the
required 80% separately in every dimension. The proposed twenty-start development
trial remains unallocated and unstarted; no fourth assessed run is authorized
by this audit. The corrected M5 cohort and review packet remain preserved.

## Audit result

These classes describe evidence preparation, not supported/contradicted verdicts
or D1–D6 decisions. An API source can establish why a candidate is incorrect.

| Review class | Spans | Meaning |
| --- | ---: | --- |
| Applicable API evidence (A) | 53 | An applicable source is identified for inspection; no automatic pass |
| Task/context comparison (T) | 37 | Compare with the unchanged original task |
| Reasoning/general advice (R) | 21 | Requires an explicit mathematical or workflow basis |
| Partial/mixed coverage (P) | 51 | A source addresses only part of the statement |
| Unresolved behavior (U) | 13 | Exact runtime behavior or asserted contract remains unestablished |
| **Total** | **175** | **83 spans also carry a split-required flag** |

The new `packet-r2` preserves candidate text, task context, rubric, check subjects
and dimension routing. It adds source excerpts and separate review notes. Every
entry retains `accepted_for_model_dispatch: false`. No `Observations`, accepting
`FactAudit`, scores or accepting score audit were manufactured.

The thirteen binding repairs cover two OpenSees version statements, two Revit
project/runtime-target statements, null-safe wall-area retrieval, two Revit
parameter-access statements, four ArcPy version/import/workspace statements,
cone dimension validation and Matplotlib library identity. **A repaired binding
does not establish the complete statement**, installed software or runtime behavior.

The five remaining unbound checks, with the common `baseline-001-` prefix omitted:

| Item | Check | Appropriate evidence still needed |
| --- | --- | --- |
| b01-item-0013 | K0003 | Explicit unit-consistency reasoning |
| b01-item-0013 | K0012 | Rationale for documenting unit assumptions |
| b02-item-0007 | K0013 | Disposable-file/workflow precaution |
| b02-item-0040 | K0011 | Direct comparison of mathematical coefficients with the task |
| b02-item-0040 | K0013 | Separate plotting/API claims from analytic identities |

The current v1 contract treats these candidate passages as technical claims
requiring primary API excerpts. Attaching unrelated documentation would conceal
that mismatch. A protocol revision must represent the actual evidence basis,
preserve mandatory coverage and leave unsupported API assertions unresolved.
The other partial and unresolved entries remain work even where bindings exist.

## Findings that change the verification approach

**FreeCAD's `Part.Cone` exists.** The pinned 1.0.2 source registers `ConePy` as
`Part.Cone`; its constructor wraps a geometric surface. The reviewed overloads
do not accept the candidate's `Height` keyword. The requested parametric
`Part::Cone` document object has separate Radius1, Radius2 and Height properties.
The audit records wrong object/arguments without incorrectly calling an existing
API nonexistent. Frozen human ratings remain unchanged.
[Module registration](https://github.com/FreeCAD/FreeCAD/blob/256fc7eff3379911ab5daf88e10182c509aa8052/src/Mod/Part/App/AppPart.cpp),
[surface constructor](https://github.com/FreeCAD/FreeCAD/blob/256fc7eff3379911ab5daf88e10182c509aa8052/src/Mod/Part/App/ConePyImp.cpp),
[document primitive](https://github.com/FreeCAD/FreeCAD/blob/256fc7eff3379911ab5daf88e10182c509aa8052/src/Mod/Part/App/PrimitiveFeature.cpp).

**Several gaps were retrieval misses.** The retained Revit wall sample already
shows null-safe `HOST_AREA_COMPUTED` access, and the retained ArcPy cheat sheet
contains import and workspace setup. Keyword matching failed to bind these
passages. Revit examples are still partial contracts: a missing member in a
sample does not prove nonexistence. Exact 2025 `Parameter.HasValue` member-page
retrieval remained unavailable; `FamilyType.HasValue(parameter)` is a different
owner and cannot substitute as proof. The official parameter guide supports
distinguishing measured numeric values from string storage access.
[Autodesk parameter guide](https://help.autodesk.com/cloudhelp/2025/ENU/Revit-API/files/Revit_API_Developers_Guide/Basic_Interaction_with_Revit_Elements/Parameters/Revit_API_Revit_API_Developers_Guide_Basic_Interaction_with_Revit_Elements_Parameters_Parameter_html.html).

**Runtime claims require narrower conclusions.** Pinned OpenSeesPy documentation
identifies `printModel()` rather than Python's built-in `print`. It does not settle
the exact extra-fixity-argument behavior of the installed binary. The audit does
not replace a claimed inevitable singularity with an unmeasured inevitable
exception. Similarly, the retained SciPy documentation does not establish every
claimed shape exception, silent corruption, tolerance-induced instability or
universal solver preference.

**Task drift is independently checkable.** A retained Decimal calculation uses
50-digit precision to compare the exact exponential solutions and unchanged
task coefficients, initial conditions and intervals. It is an assistant-authored
mathematical derivation, not a solver run or primary API quotation. It remains
outside model inputs pending the appropriate evidence contract. Generic unit and
workflow advice needs the same explicit distinction between reasoning and API proof.

## Provenance and verification

Fourteen additional files were retrieved from pinned FreeCAD, Building Coder,
OpenSeesPy documentation and Matplotlib sources. Their downloaded bytes match
Git blob IDs and SHA-256 receipts. Applicable license/copyright notices and reuse
scope are retained with the packet. Public ArcGIS and Autodesk web pages were
used as research references only: their text was not imported into model context,
and public accessibility was not treated as permission to redistribute it.

Evidence is outside Git at
`artifacts/evidence/P1-03/qualification/m4-recovery-source-audit-20261117/`.
It includes per-case `AUDITED-CHECKLIST.md`, attributed `source-audit.json`,
revised draft inputs/plans, exact excerpts, a source catalog, download receipts,
the mathematical derivation and replay/preservation receipts. The original
preparation packet is unchanged; all **106 entries in its previous seal** verify.
Read-only replay validates all ten revised plans, exact source bytes and unchanged
candidate/task/rubric content. This is evidence verification, not another model
quality measurement. Application code and prompts are unchanged; the preceding
implementation checkpoint's **553 passing WSL tests** remain its recorded result.

Two authoring-script syntax errors were corrected before artifact creation;
the failed invocations made no model requests or partial packet. The completed
packet and independent read-only replay both succeeded.

## Next implementation work

1. Revise the isolated development evidence contract to distinguish API proof,
   original-task comparisons, derived mathematics and workflow reasoning. Keep
   missing factual evidence unresolved and preserve the unchanged rubric.
2. Split the 83 flagged spans, carry their lineage forward and re-audit completeness,
   applicability and source permissions. Resolve remaining factual gaps without
   borrowing frozen reviewer decisions as evidence.
3. Prepare durable staged transport, target-tokenizer preflight and a frozen,
   bounded development package before any inference. Development results remain
   ineligible for assessed calibration.

No new action is needed from Chad for this offline work.
