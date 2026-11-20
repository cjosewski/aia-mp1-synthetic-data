# AEC rubric v2 — owner interview record

Working record of Chad's answers, November 20, 2026. These are the owner's
decisions, captured in order. The assembled rubric is drafted from them,
reviewed independently, then frozen as a dated amendment. The original course
rubric (`config/aec-course/rubric.json`) and the November 18 D3 anchor are
preserved unchanged.

**Integrity rule:** freeze the rubric before the baseline re-review or any
corrected generation, and never edit it after seeing review results.

## Framing

1. **Intended reader.** An AEC professional with little coding experience. They
   know the engineering domain but rarely write code, and need every step,
   including environment setup and how to run the script.
2. **Evidence standard.** Reviewers judge by reading the answer against the
   version-pinned documentation. Running the code is not required. This works
   for all five libraries and is the same standard any judge will use.
3. **Dimensions (eight).**
   1. Task fidelity
   2. Procedural completeness
   3. API correctness
   4. Result verification
   5. Data/model safety
   6. Professional boundary
   7. Tip usefulness
   8. Clarity for non-coders

   Each needs pass/fail lines and tie-breaks with the dimensions that share its
   territory.

## Dimensions

### 1. Task fidelity

- **Pass:** the answer addresses the brief's specific problem: the same
  software, version, objects and intended result. In addition, the `question`
  and `equipment_problem` fields restate the problem accurately (environment,
  symptom, intended result), so the item stands on its own. This absorbs the
  old D5.
- **Fail:** the answer solves a different or broader problem, or the framing
  fields misstate it.
- **Tie-break with completeness:** ignoring an explicit constraint in the
  brief (for example "read-only" or "use the supplied scratch database") fails
  **Task fidelity**, not completeness.

### 2. Procedural completeness

- **Pass (runnable end to end):** says where and how to run the script (for
  example the ArcGIS Pro Python window or the FreeCAD console), lists
  prerequisites and gives every step in order. The reader can finish without
  filling gaps.
- **Break-a-step rule** (owner, November 20): "API errors only count against
  D1 when they break a step."
  - **A wrong result breaks the step.** A call that runs without error but
    produces the wrong object or value (for example a default-size cone instead
    of the requested dimensions) fails **completeness and API correctness**.
  - **An ancillary defect does not.** A defect that breaks only an optional or
    ancillary step (an extra example, an optional check) while the main
    procedure works leaves completeness passing. It is scored under API
    correctness only.

### 3. API correctness

- **Base anchor:** the November 18 owner-defined anchor, retained. The code can
  compile or run as applicable and behaves as claimed in the stated versions.
  Required calls, tools and members exist, and their signatures, order and
  meanings are correct. The required versions can be installed together. A
  concrete incompatibility fails it.
- **Scope:** everything the reader runs: the main steps, extra examples, and
  any code inside `tips` or `safety_info`. Prose mentions of an API are not
  checked.
- **Documentation gap:** pass unless shown wrong. Only a concrete, documented
  incompatibility fails; absence from the pinned docs is not proof an API is
  wrong.
- **Version tie-break:** using a member that exists only in another version
  than the brief states fails **API correctness**. Task fidelity fails only when
  the answer explicitly targets a different version or software.

### 4. Result verification

- **Pass:** a concrete check **and** the expected outcome (an expected value,
  count or state) tied to the task's intended result. The reader can tell
  success from failure.
- **Location:** anywhere in the answer (`answer`, `steps` or `tips`).
- **Missing verification (confirmed):** an answer with no verification fails
  **Result verification only**, not completeness.

### 5. Data/model safety

- **Pass (field-bound):** `safety_info` names the specific risk of this
  operation to the model or data (irreversible edit, wrong target, excess
  scope, overwritten output) **and** a specific safeguard that addresses it
  (work on a copy, transaction or rollback, read-only first, scope to a
  selection). Only `safety_info` counts. This replaces the old D2.
- **Read-only tasks:** `safety_info` states that the task is read-only **and**
  names any real residual risk with its safeguard (for example scanning the
  wrong database, file locks, slow full scans).
- **Read-only with genuinely no residual risk (confirmed):** an accurate
  statement that nothing is modified passes.

### 6. Professional boundary

- **Pass:** when results feed design or code-compliance decisions (structural
  capacity, loads, code checks, issued drawings), the answer says they need
  review by a qualified engineer and does not present the script's output as
  final.
- **No overreach:** the answer never claims the script satisfies a code or
  standard, or replaces engineering judgment. This replaces the old D4.
- **No engineering decision involved:** passes automatically.
- **No-overreach scope (confirmed):** the no-overreach rule is checked only
  when results feed design or code-compliance decisions. Answers with no such
  decision pass automatically. (The owner chose this over the assistant's
  initial reading.)

### 7. Tip usefulness

- **Aggregation (every tip adds value):** each tip must be non-obvious,
  task-specific technical advice beyond the steps (a pitfall, a version
  gotcha, a units or performance note). A single repeated-step or generic tip
  fails the set. This replaces the old D6.
- **A tip with an API error** fails both **API correctness** and **Tip
  usefulness**.

### 8. Clarity for non-coders

- **Pass (followable without coding):** domain and API terms are explained on
  first use, code is commented step by step, and each step says what it does
  and why. There are no unexplained leaps.
- **Tie-break with completeness:** a needed step that is present but too vague
  to execute (for example "set up the environment" with no specifics) fails
  **completeness**. Clarity judges only the readability of steps the reader
  can follow.

## Global rules

- **Overall pass:** an answer passes overall only if **all eight** dimensions
  pass. This carries over the course rule "all dimensions pass". The
  >80% relative overall-failure reduction target is measured on it.
- **Binary decisions:** each dimension is scored pass/fail.

## Review round (independent five-lens review, 109 confirmed findings)

The review records are in
`../artifacts/evidence/.rubric-v2-review-20261120/`.

- **Q1. Task brief:** shown. Reviewers and any judge see the per-item task
  statement from the approved 50-task pack beside the seven fields. It is
  worded identically for baseline and corrected items. "The brief" means this
  task brief.
- **Q2. Field lists:** pointers, not binding. Evidence anywhere in `answer`,
  `tools_required`, `steps`, `safety_info` or `tips` counts, except where the
  three location rules restrict it (safety: `safety_info` only; verification:
  answer, steps or tips; API correctness: what the reader runs). `question` and
  `equipment_problem` are judged only by fidelity's restatement test.
- **Q3. Documentation set:** the publisher's official reference for the brief's
  stated versions, plus the same publisher's release notes, changelogs and
  migration or deprecation guides. These are used only to show when a member
  was added, changed or removed.
- **Q4. Complete listings:** a member that is absent from the pinned page
  listing all of a class's or module's members (inherited included), and
  mentioned nowhere else in the pinned docs, is **shown wrong** and fails API
  correctness. Exceptions: members the answer's own code defines. Absence from
  guides, examples or partial pages is still not proof. The complete-listing
  page per library must be named before the freeze. Completeness follows the
  same rule for a required step.
- **Q5. Per-dimension minimums:** the course values carry over to their
  successors as minimums on the corrected run's human labels:

  | Dimension | Minimum pass rate |
  | --- | --- |
  | Fidelity | 0.90 |
  | Completeness | 0.85 |
  | API correctness | 0.95 |
  | Safety | 0.90 |
  | Professional boundary | 0.95 |
  | Tips | 0.85 |

  Verification and clarity are pending the owner's value (or none).
- **Q6. Reader's starting point:** the brief's host program or runtime is
  installed and licensed at the stated version (Python for standalone scripts),
  and the reader can open a terminal and change folders. Every other install or
  configuration is a step. The answer names where the code runs and gives the
  exact commands. Modules bundled with the host (for example arcpy) need no
  install step.
- **Q7. Data-dependent expected outcome:** when the correct value comes from
  the reader's own data, a stated expected form is enough (for example one row
  per layer with its name and a whole-number count). The pass line's "tell
  success from failure" is qualified accordingly for such results.
- **Q8. New output files:** a script that only writes new output files and
  changes nothing existing is read-only for safety. If its code could overwrite
  an existing file at the output path, that is a real residual risk to name
  with a safeguard (a new file name or an existence check). Adding to or
  changing something that already exists is a modifying task.
- **Q9. Real residual risk (read-only tasks):** a residual risk must be named
  only when the brief or code gives it a concrete basis:
  - several candidate datasets, or a live or production source (wrong target);
  - a file or model others may have open (locks);
  - data the brief describes as large (slow scans);
  - any hazard that makes computed or reported values wrong (for example a
    unit or coordinate-system mismatch).

  A reader-set path is not a basis on its own.
- **Q10. Terms clarity requires to be explained:** programming and API terms
  (for example cursor, transaction, virtual environment) plus the target
  application's data-model terms (for example feature class, document object,
  IFC entity). Engineering terms need no explanation. The fail anchor names the
  same classes of term.
- **Q11. Wrong tips:** a tip fails if the brief or the pinned documentation
  contradicts its claim (pass unless shown wrong, as for API correctness).
  "Misleading" is dropped. This adds to failing for being obvious, generic, a
  repeated step, or an API error in code.
- **Q12. Professional boundary trigger:** the dimension applies only when the
  brief says its results will be used for a design or code-compliance
  decision. Otherwise it passes automatically. Each brief is classified once,
  from the brief alone, and the list is frozen with the rubric.
- **Q13. Overlapping defects:** a defect that fails two dimensions with no
  tie-break covering the pair fails **only the dimension it most directly
  concerns**: one recorded failure per defect. An off-target answer fails task
  fidelity only, and the other dimensions judge it against what it sets out to
  do. The owner's explicit tie-breaks still apply:
  - a wrong result fails completeness and API correctness;
  - a tip with an API error fails tips and API correctness.

  Tie-break 4 reads: "fails API correctness and no other dimension, except that
  code in a tip also fails tip usefulness."
- **Q5 follow-up:** the verification minimum is 0.85 and the clarity minimum
  is 0.85.
- **Readings R1–R13** (from the review's wording fixes): all accepted as
  listed.
- **Freeze prerequisites** (both resolved in the freeze round below):
  1. A fixed reviewer documentation list per library: official reference plus
     change notes, version-pinned, including each library's complete
     member-listing pages (Q3, Q4).
  2. A one-time classification of the 50 task briefs for the
     professional-boundary trigger, made from the brief text alone (Q12).

## Freeze round (owner answers, November 20)

The assembled draft was revised twice by independent reviewers (19 wording
fixes) before these questions were asked.

- **F1. Target version:** only three briefs state a version
  (aec_automation-01 Revit 2025, cad_apis-01 FreeCAD 1.0.2, simulation-01
  SciPy 1.16.1). For the other 47, "the brief's stated version" is the
  reference pack's approved target for the brief's category: ArcGIS Pro 3.6,
  Revit 2025, OpenSeesPy 3.5.1.3, FreeCAD 1.0.2 and SciPy 1.16.1. Helper
  software with no target (NumPy, Python) is checked at versions that work
  with that target.
- **F2. Reviewer documentation list:** accepted as proposed. This includes the
  complete-listing pages, the OpenSeesPy command chapters at the pinned
  documentation commit, and FreeCAD's 1.0.2 source binding and property files.
  FreeCAD wiki pages are pinned to their last revision on or before
  2025-08-06, the 1.0.2 release date. For Revit, the online 2025 API reference
  governs, and members added in any 2025.x update count.
- **F3. Professional-boundary triggers:** the classification is confirmed;
  none of the 50 briefs trigger. The dimension stays in the rubric, passes
  automatically on every item of this pack, and is reported as not exercised.
  Overall pass still requires all eight.
- **F4. Off-target version:** an answer that explicitly targets another
  version or software than its brief fails task fidelity only, and its code is
  checked against the version it targets (Q13). This replaces the review fix
  that also judged its API correctness against the brief's version.

## Freeze

The rubric is frozen in `config/aec-course/rubric-v2.json`, which pins this
record by sha256. The rubric's own sha256 is recorded in `ITERATION_LOG.md`
under "Rubric v2 frozen". Neither file is edited after the freeze; any change
is a new, dated version.
