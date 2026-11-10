# Reference pack prepared for source-use review

Prepared November 10, 2026. The external `engineering-v1` review draft contains
50 original task briefs, ten per category, five reference summaries, and 28
upstream source/license artifacts. Its approval fields are empty and its
`allowed_uses` lists are empty. It cannot be used for assessed generation yet.

## Proposed selection

| Category | Reference target | Permission evidence and scope |
| --- | --- | --- |
| GIS scripting | ArcPy, ArcGIS Pro 3.6+ cheat sheet 3R0 | [Esri repository license](https://github.com/Esri/arcpy/blob/b4332c5c46a59c80c50fcbd37689de7d3b5bee4a/LICENSE.txt): Apache-2.0; retain the PDF's copyright/trademark notices |
| AEC automation | Revit API 2025, The Building Coder Samples | [Author's MIT license](https://github.com/jeremytammik/the_building_coder_samples/blob/cf3748045978bc35fcae88417c3024209be44fbe/License.md); retain selected sample headers. This does not license Revit itself |
| Structural analysis | OpenSeesPy documentation snapshot declaring version 3.5.1.3 | [OpenSeesPy terms](https://github.com/zhuminjie/OpenSeesPyDoc/blob/ce0d8f1ded3c722119c44d5b3a2073c9dce47828/LICENSE) and [Regents documentation terms](https://opensees.github.io/OpenSeesDocumentation/developer/license.html); proposed use is local noncommercial coursework only, pending the owner's scope decision |
| CAD APIs | FreeCAD 1.0.2 Part source examples | [License](https://github.com/FreeCAD/FreeCAD/blob/256fc7eff3379911ab5daf88e10182c509aa8052/LICENSE) and selected source headers; LGPL-2.0-or-later, with notices and corresponding source snapshots retained |
| Simulation | SciPy 1.16.1 `solve_ivp` | [BSD-3-Clause license](https://github.com/scipy/scipy/blob/0cf8e9541b1a2457992bf4ec2c0c669da373e497/LICENSE.txt); original, explicitly defined nonmedical ODE exercises |

The draft preserves ArcPy, Revit and OpenSees topics. It does not substitute QGIS
or IfcOpenShell. Versions are frozen reference targets, not claims about the latest
release or software installed locally. The limited installation check found no
ArcGIS Pro executable, Revit folder or FreeCAD folder in the inspected locations.
OpenSeesPy package compatibility and all engineering-runtime execution remain
unverified. Preparing the reference text did not install these applications.

The separate RevitSdkSamples repository was excluded from the pack: its root MIT
label coexists with an SDK EULA and restrictive sample headers. Instead, this draft
uses the author's explicitly MIT-licensed Building Coder collection. The ArcPy
cheat sheet contains contradictory speed descriptions for the two Describe
variants; the summary preserves their return types and omits a speed ranking.

## Review the actual artifacts

All paths below are relative to workspace
`artifacts/evidence/P1-03/references/preparation-20261110/`, outside Git:

- `REFERENCE-REVIEW.md`: readable reference notes, installation assumptions and
  all 50 task briefs. Review this first.
- `engineering-v1.draft.json`: machine-readable draft; deliberately not cleared.
- `provenance.json`: pinned upstream URLs, saved-file hashes and source-text hashes.
- `upstream/` and `ArcPy-Cheatsheet.pdf`: source/license evidence; text snapshots
  are normalized to UTF-8/LF and the PDF retains its original downloaded bytes.
- `draft-validation.json`: category counts, distinct briefs, reference links,
  hashes and empty approval-field checks.
- `source-check.txt`: actual CLI refusal of the unapproved pack.

The draft SHA-256 is
`a947287d42f8028ae9a0a4899a9ca4183f7ac361eb8778264ad57bfdd1416d45`.
No answers, human scores or judge outputs have been generated from it. The
validation checks structure and provenance; they do not establish legal permission
or engineering correctness. The 50-task set is an authored exercise inventory,
not a claim of an external engineering benchmark.

## Decision to record

The proposed use is **local, noncommercial coursework**: reference-grounded
generation, Chad's human review, local judge context and retained local evidence.
Keep the pack and reference-bearing outputs local; public/commercial corpus
export is not included. Preserve all source notices. In particular, the
OpenSees documentation terms must fit the actual educational use; an owner
decision cannot grant rights beyond those terms. If the scope does not fit,
replace or obtain permission for that material before collection.

The [approved plan](assessed-collection-plan.md#implementation-sequence-and-ownership)
assigns source-use decisions to Chad. Record his decision against this concrete
draft before populating approval fields. No further implementation-plan approval
is needed for this preparation work.

After an affirmative source-use decision, create the approved version at
`artifacts/evidence/P1-03/references/engineering-v1.json`, retain the draft, make
license-evidence paths unambiguous from that new location, record the actual
decision/time and permitted uses, and run `source-check`. Then pin the generator
artifact and prepare its local configuration before starting the baseline.
Stronger-judge selection remains a separate owner/model-qualification step; it
can proceed while the baseline's authentic human reviews are collected.
