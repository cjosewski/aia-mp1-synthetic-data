# M4 contract-source follow-up

November 17, 2026. Eight preparation holds are removed through more precise
source bindings. The current packet has **358 checks: 310 prepared questions
and 48 remaining holds**, including one empty binding. Prepared questions are
not verified facts. M4 remains open; no model evaluation or human rating changed.

## What changed

| Case suffix | Checks | Evidence supplied |
| --- | --- | --- |
| b01-item-0050 | K0013, K0016, K0026 | SciPy 1.16.1 argument checks, vectorization wrappers, RK initialization/assignment and NumPy 2.3.1 assignment/view semantics |
| b02-item-0014 | K0017 | FreeCAD 1.0.2 GUI console construction and registration, including its hidden-dock condition |
| b02-item-0019 | K0013, K0015 | FreeCAD 1.0.2 Windows support statement and GUI console implementation |
| b02-item-0047 | K0005, K0015 | Already retained structural-framing category and instance-filter sample |

The last two holds were mistakes in our preparation. The retained
`NumberStructuralFraming` example already contained the exact category filter;
the earlier wall/door-only objection was stale. This correction changes source
bindings and preparation dispositions, not the candidate or frozen human review.
[Pinned sample](https://github.com/jeremytammik/the_building_coder_samples/blob/cf3748045978bc35fcae88417c3024209be44fbe/BuildingCoder/CmdListMarks.cs).

FreeCAD's console implementation establishes availability subject to its GUI
configuration. Its README supports the proposed Windows environment, without
claiming this machine has that version installed.
[Console implementation](https://github.com/FreeCAD/FreeCAD/blob/256fc7eff3379911ab5daf88e10182c509aa8052/src/Gui/MainWindow.cpp),
[platform statement](https://github.com/FreeCAD/FreeCAD/blob/256fc7eff3379911ab5daf88e10182c509aa8052/README.md).
The installed local Revit version is 2027; it was not used as proof of 2025 behavior.

## SciPy research check

A standalone, assistant-authored WSL probe used SciPy 1.16.1, NumPy 2.3.1,
RK45, `vectorized=False`, two initial state values and three constant RHS cases:

| Derivative length | Observed outcome |
| --- | --- |
| Two, conforming | Reached 0.1 successfully |
| One, nonconforming but broadcastable | Reached 0.1 successfully |
| Three, nonbroadcastable | Raised `ValueError` |

This is a counterexample to a blanket claim that every derivative dimension
mismatch raises `ValueError`. It does **not** make the malformed RHS valid,
establish behavior for every solver, or demonstrate a crash. The result and
script are retained as research only, outside the model source context.
The verifier instead receives licensed implementation excerpts and NumPy's
documented assignment/view behavior. The callback paths also supply relevant
evidence for the advice to avoid modifying RHS inputs.
[SciPy callback wrappers](https://github.com/scipy/scipy/blob/v1.16.1/scipy/integrate/_ivp/base.py),
[RK implementation](https://github.com/scipy/scipy/blob/v1.16.1/scipy/integrate/_ivp/rk.py),
[NumPy indexing](https://github.com/numpy/numpy/blob/v2.3.1/doc/source/user/basics.indexing.rst).

The research check is not execution of the frozen candidate, a model-quality
measurement, or a new human label. It supplies no rubric score. No source finding
overwrites the earlier accepted human review, including this case's six passes.

## Preservation and remaining work

The separate evidence directory is
`artifacts/evidence/P1-03/qualification/m4-recovery-contract-followup-20261117/`.
It retains both intermediate `packet-contracts` and current `packet-final`.
Only eight child source bindings change; all 358 IDs, subjects, questions,
dimensions, parent checks and 41 reasoning notes are preserved. New input and
plan hashes record the source additions, with explicit predecessor links.
All preparation entries retain null fact verdicts and false fact-audit acceptance.

Eight downloaded Git blobs are retained and verified. Seven files enter the
source snapshot with licenses/provenance; an unused GUI source remains research
only. Read-only replay checks both ten-case revisions, exact source bytes and
permissions, frozen candidate/task/rubric text and **539 entries across four
previous seals**. No application or prompt changed, so no new application test
suite result is claimed. The earlier implementation's 593 exercised tests remain
its recorded validation.

| Category | Remaining preparation holds |
| --- | ---: |
| GIS | 14 |
| AEC | 13 |
| Structural | 14 |
| CAD | 2 |
| Simulation | 5 |
| **Total** | **48** |

Remaining holds concern exact cursor/geometry contracts, Revit parameter and
transaction behavior, OpenSees units/failure behavior, FreeCAD attachment and
geometry prerequisites, and SciPy warning/instability/preference claims. Keep
their uncertainty explicit. Next, resolve shared contracts and audit whether
remaining questions overstate the actual candidate claims before preflight.
Any necessary protocol change must be recorded before live execution.

Execution remains disabled. The twenty-start development trial is unallocated
and unstarted; all three assessed allocations remain consumed. There were
**zero model calls and no Mac use**; cumulative starts remain 388. The original
80%-in-every-dimension criterion, V15's D1 70% / D6 65% failures and the preserved
M5 packet are unchanged. No new action is needed from Chad for this source work.
