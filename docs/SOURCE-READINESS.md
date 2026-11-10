# Assessed source and model readiness — November 10, 2026

Software readiness and corpus permission are separate. The source loader requires
a real, attributed, versioned reference pack. The existing [source manifest](../config/sources.json)
remains cleared only for smoke use. No production reference pack has been promoted
to assessed status.

## Source review

| Category / candidate | Evidence inspected | Remaining work before pack approval |
| --- | --- | --- |
| GIS — QGIS | The [3.40 PyQGIS introduction](https://docs.qgis.org/3.40/en/docs/pyqgis_developer_cookbook/intro.html) identifies GFDL 1.3-or-later for the document and snippets; it also marks that version end-of-life | Select the intended supported installation/version, pin excerpts and attribution/license material; map ten task briefs |
| AEC — IfcOpenShell / Dynamo; issue also names Revit | [IfcOpenShell's introduction](https://docs.ifcopenshell.org/introduction.html) and [v0.8.0 COPYING](https://github.com/IfcOpenShell/IfcOpenShell/blob/v0.8.0/COPYING) provide starting evidence, not verified coverage of every documentation page | Resolve document-specific terms/version and disposition of Revit/ArcPy source requirements before claiming a substitution complete |
| Structural — OpenSees | The official [documentation license page](https://opensees.github.io/OpenSeesDocumentation/developer/license.html) includes use restrictions and notice obligations | Resolve the actual permitted coursework and downstream reuse scope; public access does not establish unrestricted corpus/export permission |
| CAD — FreeCAD | The project's [license page](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/License.md) distinguishes CC-BY-3.0 documentation from the application license; this mirror is archived | Pin the API/software revision and current source, retain attribution and verify each selected page's terms |
| Simulation — open nonmedical numerical simulation | No exact versioned reference set selected yet | Select the target, verify documentation terms/installation assumptions, then map ten task briefs |

These are findings and remaining tasks, not blanket legal conclusions or approvals.
No retrieved API text has been copied into the production corpus. Each admitted
source needs the metadata described in [the assessed runbook](ASSESSED-RUNBOOK.md).
An incomplete category blocks assessed collection, but not offline software tests.

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

Finish the versioned source pack and source-scope disposition, then record actual
use approval. Baseline collection can follow that gate; stronger-judge qualification
can proceed alongside human baseline review. Freeze the 20 independent human
reviews before any assessed judge run.
