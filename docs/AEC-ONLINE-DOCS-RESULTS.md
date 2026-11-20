# AEC model-directed documentation comparison

**Completed November 19, 2026, Eastern time.** The documentation-enabled Qwen
judge did not pass the development gate. Agreement was **2, 3, 9, 9, 8 and 8 of
ten** for D1–D6, compared with **3, 4, 8, 9, 8 and 8** for the matched source-aware
control. Completeness and safety fell further below the required 8/10, and the
explanation audit found material errors. The method does not advance to assessed
judging or generator correction.

## Method and comparison population

The hypothesis was that direct access to versioned publisher documentation would
help the existing judge verify concrete API claims while preserving task and
rubric coverage. For each answer, Qwen selected one to three publisher pages and
a literal search string. The Fedora reader returned saved passages; a second
model call produced D1–D6 decisions and explanations. No document index or vector
database was used. The generator was not changed.

Run `api-development-qwen-online-docs-002`, its interrupted predecessor `001`,
and the source-aware control `api-development-comparison-001` use the same ten
answers and frozen development reference. All item suffixes below have the
prefix `baseline-001-b04-item-`.

| Specialty | Item suffixes |
| --- | --- |
| GIS scripting | `0006`, `0011` |
| AEC automation | `0047`, `0007` |
| Structural analysis | `0018`, `0028` |
| CAD APIs | `0024`, `0014` |
| Simulation | `0045`, `0005` |

The frozen order is `0006`, `0047`, `0018`, `0024`, `0045`, `0011`, `0007`,
`0028`, `0014`, `0005`. Prompts, rubric, lookup inputs, judge settings and human
reference match the predecessor. Run 002 pins all 34 predecessor files, including
its lock and unmatched judgment start; it does not inherit those attempts as new
results. Run 001 retains ten consumed starts, nine returns and one unknown
judgment outcome. Its four returned judgments are not a ten-case agreement rate.

## Measured result

Run 002 completed **20 starts and 20 valid returns**: ten lookups and ten
six-dimensional judgments, with one attempt per case per stage. All **29 requested
pages opened** within the thirty-page limit. Twelve nonempty search strings did
not match; those requests supplied the beginning of the page instead. An opened
page or matched search string alone does not establish support for a claim.

| Dimension | Control matches / 10 | Documentation matches / 10 | Corrections | Regressions | At least 8/10 |
| --- | ---: | ---: | ---: | ---: | --- |
| D1 Answer completeness | 3 | 2 | 1 | 2 | No |
| D2 Safety specificity | 4 | 3 | 0 | 1 | No |
| D3 Version-specific API correctness | 8 | 9 | 1 | 0 | Yes |
| D4 Scope appropriateness | 9 | 9 | 0 | 0 | Yes |
| D5 Context clarity | 8 | 8 | 0 | 0 | Yes |
| D6 Tip usefulness | 8 | 8 | 1 | 1 | Yes |

Corrections and regressions compare each new binary decision with the control
against the same frozen human decision. Across the six dimensions there were
three corrections and four regressions. These are observed development results;
the experiment did not estimate repeat-to-repeat variation.

## Explanation audit

Assistant technical audits reviewed all ten saved judgments against the actual
candidate fields, task/reference context and judge-visible passages. They did
not assign replacement human ratings or execute candidate code. Selected findings
show why the explanation gate also failed:

- **OpenSees `0018`:** the completeness explanation substituted time-series-before-
  pattern ordering for the omitted pattern-before-load instruction required by
  the task. It also approved a tip calling kN, m and Pa a consistent unit set.
  Dimensional reasoning identifies the missing conversion; no numerical error
  was measured. The API explanation attributed a described load invocation to a
  candidate that supplied none, rather than identifying an executed invalid call.
- **SciPy `0045`:** the judge approved a tip treating solver success as proof that
  the final time was reached. The supplied reference explicitly distinguishes
  terminal-event success from reaching the endpoint. The selected `solve_ivp`
  passage did not show the return semantics credited to it. This is both a missed
  substantive tip defect and a citation overreach, not just an unsuccessful search.
- **ArcPy `0006`:** the safety explanation attributed an explicit context-manager
  precaution to `safety_info`; that instruction appeared in the answer and steps.
  The named field warned about failure to close the cursor. The audit preserves
  the useful whole-answer guidance while identifying the field-attribution error.
- **Revit `0007`:** the tip explanation incorrectly claimed `Document.GetUnits()`
  did not exist. Autodesk's [Revit 2025 Units guide](https://help.autodesk.com/cloudhelp/2025/ENU/Revit-API/files/Revit_API_Developers_Guide/Introduction/Application_and_Document/Revit_API_Revit_API_Developers_Guide_Introduction_Application_and_Document_Units_html.html)
  demonstrates that method. This was an **audit-only source**, not a passage shown
  to the judge. The remaining `AsValueString` fallback advice for nonnumeric
  storage types is underspecified: it could mean choosing a different accessor,
  so the wording alone does not establish an invalid call. The explanation should
  resolve that ambiguity rather than give blanket credit.

Other findings distinguish missing citation support from demonstrably false
claims. A generic `Describe` excerpt does not prove the absence of a particular
datatype's property. A source may support a valid API elsewhere even when the
specific cited passage does not. The FreeCAD audit also preserves the distinction
between an existing constructor with an incorrect signature and a nonexistent
API. These concerns do not automatically reverse the frozen binary decisions.
The separate citation inventory includes both bracketed and unbracketed page IDs;
no unknown page IDs were found, but valid IDs did not ensure evidential support.

## Runtime and verification

Python ran on native Fedora 44 using the locked Python 3.12.16 environment.
Qwen3.5-122B-A10B Q4_K_M ran on the dedicated Mac service with build
`b12110-cd959bae9`, 16,384-token context, one slot, a 4,096-token reasoning budget
and judge temperature 0.1. Both shards were verified by full SHA-256 checks.

The first four-hour deployment expired **before any scoring calls**. A separately
verified renewal and `execution-start.json` established the active process,
tunnel and deployment lineage before dispatch. The original deployment receipt
was preserved. After scoring, the renewed server and dedicated tunnel stopped;
Mac port 8082 and Fedora port 18082 were confirmed closed. Offline replay then
returned exit code 0 and reproduced the identical report hash. The executing
source was unchanged since the **883-test** locked suite passed.

An independent numerical audit recomputed the agreement and paired changes from
the saved raw returns and frozen reference, and verified the case identities,
attempt/page accounting, predecessor hashes and runtime/replay/cleanup links.

All 16,634 original transferred evidence files were reverified after the
comparison. Raw requests, completions, publisher passages and frozen human labels
remain outside Git under `artifacts/evidence/P1-03/`.

| Evidence under `aec-course/api-development-qwen-online-docs-002/` | SHA-256 |
| --- | --- |
| `protocol.json` | `09d4975431be8efbd4be4ec25690b24bdde88b4d858ad756ebed7471ec4ac84b` |
| `deployment-renewal-01.json` | `74b550c12235d04fcc736bf8932d561e66b563f18a4501206ee8674107734578` |
| `report.json` | `67997b908f5df163d3200613bbce88ece91d873e134447cd438978ce6e90d867` |
| `execution-completion.json` | `821ae93316fce220770d43a3f4d83b566c551bcd1e335cb81ab4230b8064c7f4` |

The completion receipt binds execution, renewal, report, replay, cleanup and
audits. `comparison-summary.json` records the paired counts and page outcomes;
`citation-inventory.json` records the broader page-reference scan. The first-half
and second-half audits must be read with their separate
`explanation-audit-first-half-refinements.json` and
`explanation-audit-second-half-refinements.json` records in the same run directory.
The original-evidence verification and `independent-online-docs-002-audit.json`
are retained beside the migration receipts. See the [AEC runbook](AEC-COURSE-RUNBOOK.md#model-directed-online-documentation)
for offline replay.

## Decision and proposed next step

Do not promote this method. Repair documentation selection and citation support,
then task-obligation and candidate-field grounding, before another predeclared
development comparison. At the November 19 decision, that revision was a proposal.
The [November 20 preparation](AEC-GROUNDED-DOCS-PLAN.md) now implements the separate
method. Its [bounded attempt](AEC-GROUNDED-DOCS-RESULTS.md) stopped after one
lookup and three page opens because the first judgment request exceeded context;
no judgment started and no new agreement was measured.

The assessed baseline is separate: **12, 15, 12, 17, 13 and 11 matches out of 20**
for D1–D6 across a fifty-item cohort. Its requirement remains **16/20 in every
dimension**; only D4 qualifies. M4 stays open, and generator correction, a fresh
assessed cohort and the final comparison remain downstream of calibration.
