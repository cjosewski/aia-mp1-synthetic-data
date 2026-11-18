# M4 recovery: unresolved claims and the scoring boundary

November 18, 2026. **Proposed change, not enabled.** No new model starts,
human-label changes, accepted facts or calibration results.

## Finding

The latest ten-case preparation packet has 16 holds. The exported inventory at
workspace `artifacts/evidence/P1-03/qualification/m4-hold-audit-20261118/holds.json`
records each exact candidate span, question, source binding, reason and the
original plan/review file hashes. The sealed packet is unchanged.

| Group | Holds | What the present evidence establishes |
| --- | ---: | --- |
| ArcPy, two cases | 11 | Partial examples; exact cursor value/type, workspace and precision claims remain insufficiently covered. The proposed 3.7 experiment may supply bounded observations, subject to applicability to the frozen 3.6 tasks. |
| Revit, one case | 1 | The exact-version AsDouble documentation establishes a storage-type precondition, but does not establish the candidate's named InvalidCastException. |
| SciPy, two cases | 4 | Retained sources do not settle unspecified convergence-warning behavior, universal BDF preference, broad corruption/crash language, or tolerance-induced instability. |

The previous SciPy research probe recorded successful broadcasting for one
malformed RHS shape and ValueError for another. It did not establish memory
corruption or a process crash. It must not be relabeled as proof of either.
Likewise, absence of a named exception from a documentation excerpt does not
prove that the exception is impossible. A successful numerical example cannot
disprove a broad claim that instability *may* occur under unspecified conditions.

`build_scoring_input` currently rejects **any** unresolved fact before dimension
scoring. `require_ready` also rejects any preparation hold. These are local
recovery safeguards, not the assignment's 80%-per-dimension acceptance criterion.
Consequently, finishing transport software or approving the ArcPy probe alone
will not establish that the proposed recovery trial can complete. Five non-GIS
holds remain independently of the ArcPy result.

## Proposed explicit revision

Keep the existing strict protocol available for historical replay. Introduce a
separately versioned development protocol with the following rules:

1. Every candidate passage and all six dimensions remain covered. Source hashes,
   permission, scope, runtime applicability and authentic-human-reference rules
   remain unchanged. Missing permission or unverifiable artifact identity still
   blocks execution; it is not an ordinary factual uncertainty.
2. A preparation reviewer may explicitly classify a claim as evidence-insufficient.
   The claim, admitted evidence and precise limitation remain in the packet.
   This classification supplies neither a factual verdict nor a rubric rating.
3. The verifier may return insufficient. An audit can accept that the uncertainty
   was reported accurately without claiming that the candidate statement is true.
4. The scorer must address every insufficient finding in each routed dimension.
   It cannot use an insufficient finding as support for a pass or as proof of a
   defect. It must distinguish an established decisive defect from an unresolved
   claim. An unresolved claim's materiality requires a separate explicit audit.
5. A dimension may fail on an independently established decisive defect. It may
   pass only if the auditor establishes that the unresolved detail cannot change
   that rubric decision, with a candidate-specific explanation. If materiality
   itself remains uncertain, the dimension stays unresolved; no binary judgment
   is manufactured. Disagreement with a human rating does not justify overriding
   these rules.
6. Unresolved dimensions remain in all denominators and are reported separately.
   They never count as matches or quality passes. Complete audited coverage remains
   required for advancement; a partial result cannot qualify calibration.
7. Test unsupported-pass attempts, manufactured defects from uncertainty, omitted
   uncertain findings, unreviewed materiality, and uncertainty hidden in aggregate
   reports before any live development request. Record a new protocol identity,
   prompts and bounded allocation; preserve the strict predecessor and all errors.

This proposal does **not** lower the original 80% in every dimension, guarantee
that the ten-case trial will advance, or authorize a fourth assessed allocation.
The proposed twenty-start development limit remains unchanged. Any later assessed
extension still needs its own concrete recorded decision.

## Decision needed

Approve or decline this explicit change to the recovery's evidence-to-rating
rules before enabling it. Approval concerns handling honest uncertainty, not
accepting current candidate claims, human ratings or favorable model results.

If declined, the strict protocol remains active and all 16 holds must be resolved
through adequate evidence before it can run. No promise is made that broad,
underspecified claims admit a conclusive source-backed answer. The narrow ArcPy
Windows-Python exception is a separate pending decision in the owner runbook.
