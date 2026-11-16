# P1-03 — Everything needed from Chad

Updated November 15, 2026. This is your consolidated instruction sheet.
The [live project checklist](https://github.com/cjosewski/aia-plan/issues/4) tracks
completion. This file explains your actions; Codex handles the implementation,
model runs, analysis and evidence preparation.

**The ten reviews and your judge selection are complete. The Mac is free.** The
[assessed run](ASSESSED-BASELINE-RESULTS.md) stopped when thinking consumed the
entire output allowance. Your current action is one decision: approve or decline
the [prepared two-case thinking-budget test](REASONING-BUDGET-PROBE.md). Approval
is needed because it changes the runtime settings you explicitly froze. No new
ratings or repeat review are needed for this decision.
Actions 2–4 happen later, when the relevant material is ready. Conditional items
at the end apply only if an unresolved decision or failed evaluation requires them.

| Action | When | What you provide |
| --- | --- | --- |
| 1. Review ten fresh confirmation answers | **Complete and frozen** | No further action; original ratings, pass reasons and comments retained |
| 1b. Select the assessed judge | **Complete and recorded** | Qwen3.5 with frozen V13/settings and reported errors retained |
| 1c. Decide on the limited thinking-budget probe | **Ready for your decision** | Approve a 4096 thinking-token cap on two saved cases, at most four requests; no automatic full rerun |
| 2. Review twenty corrected-dataset answers | After Codex qualifies/calibrates the judge and creates the corrected dataset | Twenty authentic reviews in a new packet Codex will provide |
| 3. Review and record the final demonstration | After final results and charts are ready | A reviewed 90–180 second demonstration video |
| 4. Complete the coaching/submission step | When the evidence package and demonstration are ready | Instructor/coach decision, date, reviewer name and any requested changes |

Allow roughly **3–5 hours of your involvement** across the planned reviews and
demo, depending on reference checking. Coaching scheduling and any extra review
round are separate. This is an estimate, not a completion guarantee.

## Action 1 — Completed ten-case review (retained instructions)

The submitted file was `\\192.168.0.55\aia\Handoff\P1-03\MY-ANSWERS.md`.
The instructions below describe the completed review, not a request to repeat it.

### What you are evaluating

You are judging the quality of ten supplied engineering-code answers against
their reference tasks and the supplied six-dimensional rubric. These are fresh
challenge examples for checking the proposed judge model. They cover ArcPy,
Revit, FreeCAD, OpenSeesPy and SciPy.

You are reading and scoring the answers. You do not need to execute their code,
start Herd, open an engineering application, install software or run a terminal
command. There is no target number of passes or failures. Your earlier baseline
and qualification reviews are already retained; this action concerns the fresh
packet identified below.

### Step 1 — Open the correct folder

On the **Mac**:

1. Open Finder.
2. Choose **Go → Go to Folder**, or press **Shift–Command–G**.
3. Paste this path and press Return:

```text
~/AIA/MP1-handoff/qwen35-v4-blind-confirmation-v1
```

Other available copies:

| Location | Folder |
| --- | --- |
| Windows workstation | `D:\_Repos\_AIA\artifacts\evidence\P1-03\qualification\qwen35-v4-blind-confirmation-v1` |
| NAS from Windows | `\\192.168.0.55\aia\MP1-handoff\qwen35-v4-blind-confirmation-v1` |

Choose **one copy** to edit so your answers stay together.

### Step 2 — Open the instructions, questions and answer file

Open these three files from that folder:

- `RUNBOOK.md` — the packet's detailed instructions.
- `REVIEW-PACKET.md` — the rubric, reference tasks, complete candidate answers and
  source notes.
- `MY-ANSWERS.md` — the file you edit and submit.

Use a text editor such as VS Code. If using TextEdit, keep the document as plain
text with its `.md` extension; **Format → Make Plain Text** is available when
needed. Save as UTF-8 if the editor asks for an encoding.

The packet ID must remain `qwen35-v4-blind-confirmation-v1`. Keep the item IDs,
headings and rating-line structure in `MY-ANSWERS.md` unchanged.

### Step 3 — Fill in the declarations at the top

Complete these entries in your own words:

| Entry | What to enter |
| --- | --- |
| Reviewer | Your name |
| Review date | The date you complete the review, preferably `YYYY-MM-DD` |
| Assistance used | Sources, people or tools you used, or `NONE` |
| Personal review/adoption declaration | `Yes` only if you personally reviewed and adopt the ratings and comments |
| Blind-review declaration | `Yes` only if you completed your review before seeing either comparison model's judgments for these examples |

If a declaration is not true, describe the situation and tell Codex. An exposed
or incomplete review needs an explicit disposition; it must not be represented
as an independent blind review.

### Step 4 — Review C01 and enter your ratings

1. In `REVIEW-PACKET.md`, read C01's **Reference task**.
2. Read all seven fields of its **Candidate answer to evaluate**: question,
   answer, equipment problem, tools, steps, safety information and tips.
3. Apply each rubric dimension separately. Credit information wherever it occurs
   in the supplied answer. Evaluate the answer as supplied rather than silently
   correcting it before scoring.
4. In C01's matching block in `MY-ANSWERS.md`, replace each underscore with your
   own **0** for fail or **1** for pass:

```text
D1=_ | D2=_ | D3=_ | D4=_ | D5=_ | D6=_

Comment: ____________________
```

This is a blank format example, not suggested scores. Use the rubric table in the
packet as the scoring authority. Its dimensions are:

| Dimension | What the supplied rubric evaluates |
| --- | --- |
| D1 — Answer Completeness | Tools, concrete actions, hazards and advice needed to complete the task end to end |
| D2 — Safety Specificity | The task-specific hazard and a concrete precaution |
| D3 — API Realism | Whether required APIs/libraries exist and are available in the stated installation/version |
| D4 — Scope Appropriateness | When the engineering result needs licensed-engineer review or sign-off |
| D5 — Context Clarity | Sufficient context and an answer that directly addresses the equipment problem |
| D6 — Tip Usefulness | Nonobvious, task-specific advice beyond the steps |

5. Replace the comment placeholder with a brief explanation of the decisive
   technical facts. Identify the relevant field, step, API or mathematical
   requirement where useful. Every item needs a comment, including all-pass items.
6. Save the file.

Use the source appendix and authoritative references when needed. Disclose
assistance honestly and personally verify decisions you adopt. During this blind
review, do not ask Qwen3.5-122B-A10B or Qwen3-30B-A3B to score these examples.

### Step 5 — Repeat for C02 through C10

Complete all ten blocks. Save after each item; you can close the editor and resume
later. If you cannot resolve a rating, leave its underscore in place and explain
the uncertainty in the comment. Tell Codex which item/dimension is unresolved.
Codex will not fill the missing rating as a human judgment.

### Step 6 — Check and submit

Before submitting, verify:

- [ ] Your name, review date and assistance are entered.
- [ ] The adoption and blind-review declarations accurately describe your review.
- [ ] All ten original item IDs remain, in order.
- [ ] Each item has six ratings and a comment, or clearly identified uncertainty.
- [ ] You saved the `.md` file in the copy you chose.

Then send this message, adapting the path if necessary:

> The ten confirmation reviews are complete. I personally reviewed and adopt
> the ratings and comments. The file is saved at
> `~/AIA/MP1-handoff/qwen35-v4-blind-confirmation-v1/MY-ANSWERS.md`.

If some decisions remain unresolved, say that instead of declaring completion.
You can revise your answers directly before submission. After Codex freezes the
submission, request an explicit amendment; the original review will be preserved.

### What Codex does after your submission

Codex checks completeness and attribution, preserves your exact file, freezes the
reference and packages the committed comparison software. It then drives the Mac
comparison, checks every attempt and public explanation, and documents whether
the candidate supports a stronger-judge selection. The next stages use the
qualified judge on the full baseline and perform the required calibration.

Your standing permission already covers this work and Mac use. Codex will
announce before starting an owned model server or taking desktop control. Your
remaining role is to report any change in machine availability or permissions.

## Action 2 — Review twenty corrected answers later

**Wait for a new packet from Codex. These answers are not ready yet.**

After qualification and baseline calibration, Codex will identify the measured
weaknesses, revise the generator, collect a new corrected dataset and prepare
twenty selected answers for your review.

When Codex supplies the new folder and runbook:

1. Open that new packet and its answer file.
2. Read each reference task and complete candidate answer.
3. Enter your own D1–D6 ratings and comments using the same frozen rubric.
4. Record assistance and exposure accurately. Complete your ratings before seeing
   the model judge's results for those items.
5. Save and tell Codex the actual file path, identifying any unresolved ratings.

Codex handles the corrected-dataset model calls, comparison calculations, required
charts and evidence checks. Your twenty authentic reviews are the human part of
that stage. A new generator iteration may require another fresh review round;
Codex will explain the measured reason and provide a new packet if that happens.

## Action 3 — Review and record the final demonstration later

**Wait until Codex provides the final results, charts and narration outline.**

1. Review the supplied summary for accuracy and confirm what you want to say.
2. Record a **90–180 second** demonstration using the final saved outputs. Codex
   will prepare the sequence and can assist with recording setup.
3. Cover the pipeline, authentic human reviews, judge agreement, generator change,
   before/after results and any remaining limitations. Use actual final values.
4. Save the original video in the final handoff location Codex supplies and send
   its path. Codex will verify its duration and retain its checksum.

The detailed sequence is in the
[demo runbook](https://github.com/cjosewski/aia-mp1-synthetic-data/blob/main/docs/DEMO-RUNBOOK.md).
Preparation can be automated; your narration/review and the final submission
decision remain yours.

## Action 4 — Complete the coaching/submission step later

**Wait for Codex to identify the final package as ready for review.**

1. Use the prepared version intended for instructor review. Codex will check the
   package against the recorded source-sharing permissions before handoff.
2. Bring the report, five charts, demonstration and reproducibility instructions
   to the required coaching review or the instructor's prescribed submission route.
3. Report the outcome to Codex: reviewer name, date, the specific project/material
   reviewed, approval or requested changes, and any stated conditions.
4. Provide the existing decision text or its location when available. If the
   decision was verbal, identify it as verbal and summarize it accurately.

For clarity, a final outcome can be reported in this format:

```text
P1-03 final review
Reviewer/instructor:
Date:
Materials reviewed:
Decision: accepted / changes requested / pending
Conditions or requested changes:
Evidence location, or verbal-decision summary:
```

Codex will record acceptance and close P1-03 when the actual remaining requirements
and any explicit instructor dispositions support that conclusion.

## Conditional decisions — only if still unresolved or relevant

These are not requests to repeat an approval you already obtained. If your
existing instructor approval resolved one of these points, send the decision or
tell Codex exactly what it covered so the record can be reconciled.

| Topic | What may be needed from you | When |
| --- | --- | --- |
| Engineering adaptation and benchmark | Confirm whether existing approval covers engineering-code Q&A, D3 API realism, D4 engineering sign-off, and whether a separate replacement benchmark dataset is required | At the next suitable instructor/coaching contact if not already resolved |
| Required SDD format | Provide a specific required template or missing section if the instructor prescribes one | Only if such a requirement exists; an SDD is already written |
| Exactly 80% failure reduction | Obtain an explicit decision on equality if the measured result lands exactly at 80%; the current implementation uses strictly greater than 80% | Only if the final result reaches that boundary |
| An unmet measured threshold | Review the actual result and any concrete correction or instructor-disposition question Codex prepares | Only if a required criterion remains unmet |
| Additional confirmation review | Complete a new clearly identified packet if the current judge comparison fails and a revised protocol needs fresh confirmation | Only after Codex explains the result; existing reviews stay preserved |
| A material change in execution approach | Decide on a specific proposed change involving new cost, hosted inference or a new permission boundary | Only if the authorized local approach cannot complete the work |

Codex will handle model selection from the evidence within the authorized local
workflow. Routine coding, test runs, GitHub updates, model dispatch, calibration,
chart generation and package verification do not require another approval from you.

## Quick checklist

- [x] Complete and submit the ten fresh confirmation reviews.
- [x] Select the assessed judge with the measured limitations retained.
- [ ] **Now:** decide on the prepared two-case thinking-budget probe.
- [ ] **Later:** complete the twenty corrected-dataset reviews when provided.
- [ ] **Later:** review the final results and record/review the demonstration.
- [ ] **Later:** provide the final coaching/instructor decision and any conditions.
- [ ] **If applicable:** supply an existing unresolved instructor decision or respond
  to a concrete follow-up request.

Canonical instruction file:
[CHAD-ACTIONS-P1-03.md](https://github.com/cjosewski/aia-mp1-synthetic-data/blob/main/docs/CHAD-ACTIONS-P1-03.md).
Copies named `P1-03-CHAD-ACTIONS.md` in the Mac/NAS handoff folder are convenience
copies of this dated instruction sheet. Record ratings in the designated answer
file rather than in this checklist.
