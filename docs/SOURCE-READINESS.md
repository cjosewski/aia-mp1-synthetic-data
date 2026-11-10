# Assessed source and model readiness — November 10, 2026

Software readiness and corpus permission are separate. The source loader requires
a real, attributed, versioned reference pack. The existing [source manifest](../config/sources.json)
remains cleared only for smoke use. No production reference pack has been promoted
to assessed status.

## Source review

The [prepared reference-pack review](REFERENCE-PACK-REVIEW.md) now identifies exact
sources, licenses and revisions for ArcPy, Revit, OpenSeesPy, FreeCAD and SciPy.
It preserves the named ArcPy/Revit/OpenSees topics. The earlier QGIS/IfcOpenShell
alternatives are not used in this draft.

External receipt `references/preparation-20261110/` contains 50 distinct task
briefs (ten per category), five authored reference summaries, installation
assumptions and 28 source/license artifacts with hashes. The draft is intentionally
unapproved: owner source-use approval is not inferred from software approval.
The concrete proposal is local, noncommercial coursework with notices retained;
OpenSees' narrower documentation terms require the use-scope decision recorded
in that review. No unrestricted downstream corpus/export permission is claimed.

The source-check CLI refuses the pending draft. It has not entered a production
collection. Reference versions are explicit targets; local installation and
engineering execution have not been verified. Review the source-use proposal,
then promote a separately versioned approved pack and complete generator preflight.

The engineering benchmark question remains explicit. Owner-reported assignment
acceptance is preserved; it is not an undocumented waiver of that specific question.
See [requirements](requirements.md#source-permissions-and-benchmark-decision).

## Model review

The generator remains Qwen3-30B-A3B Q4_K_M. Its artifact checksum and upstream
identity must be filled in the assessed config; the served string alone does not
pin the weights.

No stronger judge has been selected or qualified. Files observed in the configured
share include Qwen3-30B-A3B, Llama-3.1-8B and GPT-OSS-20B. The approved plan names
Qwen3-32B as another candidate to investigate. Availability and model size do not
establish stronger engineering judgment. No model was downloaded or switched for
this software verification.

The qualification receipt requires the distinct upstream identity, weight checksum,
exact served ID, owner selection/basis, settings and hashes of comparison evidence.
Synthetic test receipts confer no qualification on real models.

## Current next action

Record the source-use decision against the prepared 50-task draft, then validate
the approved pack and pin the generator. Baseline collection can follow those gates; stronger-judge qualification
can proceed alongside human baseline review. Freeze the 20 independent human
reviews before any assessed judge run.
