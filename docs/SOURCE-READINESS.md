# Assessed source and model readiness — November 10, 2026

Software readiness and corpus permission are separate. The source loader requires
a real, attributed, versioned reference pack. The existing [source manifest](../config/sources.json)
remains cleared only for smoke use. The separate `engineering-v1` reference pack
is now approved for local noncommercial assessed coursework and passes validation.

## Source review

The [prepared reference-pack review](REFERENCE-PACK-REVIEW.md) now identifies exact
sources, licenses and revisions for ArcPy, Revit, OpenSeesPy, FreeCAD and SciPy.
It preserves the named ArcPy/Revit/OpenSees topics. The earlier QGIS/IfcOpenShell
alternatives are not used in this draft.

External receipt `references/preparation-20261110/` contains 50 distinct task
briefs (ten per category), five authored reference summaries, installation
assumptions and 28 source/license artifacts with hashes. Chad approved this concrete
pack on November 10. `references/engineering-v1-approval.json` records the actual
reply, scope and hashes; the original draft remains unchanged. The approved use is
local, noncommercial coursework with notices retained, including the narrower
OpenSees documentation terms. No unrestricted downstream corpus/export permission
is claimed.

The source-check CLI still refuses the original pending draft and reports ready
for approved `references/engineering-v1.json`: 50 tasks and five sources.
Reference versions are explicit targets; local installation and engineering
execution have not been verified. This approval covers the reference-grounded
coursework, not claims of executed engineering examples.

The engineering benchmark question remains explicit. Owner-reported assignment
acceptance is preserved; it is not an undocumented waiver of that specific question.
See [requirements](requirements.md#source-permissions-and-benchmark-decision).

## Model review

The generator remains Qwen3-30B-A3B Q4_K_M. Its full local SHA-256 is
`9f1a24700a339b09c06009b729b5c809e0b64c213b8af5b711b3dbdfd0c5ba48`,
matching the file metadata at
[Unsloth revision d5b1d57](https://huggingface.co/unsloth/Qwen3-30B-A3B-GGUF/tree/d5b1d57bd0b504ac62ae6c725904e96ef228dc74).
Ignored `config/assessed.local.json` pins this identity and the approved pack.

Receipt `baseline-preflight-20261110/` records authenticated WSL connectivity,
the requested/served model match, server build `b12110-cd959bae9`, a 16,384-token
slot context, template hash and default sampling settings. No server setting was
changed. One 64-token diagnostic probe exhausted its budget during reasoning;
the retained second probe passed JSON parsing and model-identity checks with the
approved 4,096-token cap. Both are excluded from assessed collection metrics.
The actual baseline uses temperature 0.6, timeout 120 seconds and two attempts
per slot. A fresh offline verification passed 185 tests, Ruff and CLI checks.

No stronger judge has been selected or qualified. Files observed in the configured
share include Qwen3-30B-A3B, Llama-3.1-8B and GPT-OSS-20B. The approved plan names
Qwen3-32B as another candidate to investigate. Availability and model size do not
establish stronger engineering judgment. No model was downloaded or switched for
this software verification.

The qualification receipt requires the distinct upstream identity, weight checksum,
exact served ID, owner selection/basis, settings and hashes of comparison evidence.
Synthetic test receipts confer no qualification on real models.

## Current next action

Source approval and generator preflight are complete. Collection `baseline-001`
qualified after four batches and 200 first-attempt-valid responses. The
[baseline checkpoint](BASELINE-CHECKPOINT.md) records the frozen 50-item cohort
and ready 20-item review queue. Chad completes those blind reviews next.
Stronger-judge qualification can proceed alongside human baseline review. Freeze
the 20 independent human reviews before any assessed judge run.
