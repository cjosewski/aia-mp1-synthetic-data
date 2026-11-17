# MP1 runbook: review the five-item diagnostic batch

Use this runbook on Chad's Windows workstation to review the five saved answers.
Start at Step 1 and run one command at a time. Every command block identifies the
shell where it belongs. This procedure uses the existing checkout and evidence;
you do not need to clone the repository again.

**Your task:** read each model-generated question and answer, then give six
independent pass/fail judgments. The program saves your judgments so they can later
be compared with the model judge. You are evaluating the **quality of the answers**.
You are not being tested on your ability to make the software pass.

**Finish condition:** all five items have authentic human reviews saved, or the
unresolved items are explicitly identified for follow-up. An answer may receive
failures and still be a successfully completed review. There is no target number
of passes for this exercise.

## What this exercise does

The pipeline has six stages:

1. Generate answers using a model.
2. Check their structure and apply simple screening rules.
3. **Collect your human judgments — this runbook's main procedure.**
4. Have a separately prompted model judge the same answers.
5. Compare judgments and analyze weaknesses.
6. Improve the judge, then the generator, using measured results.

The five saved items cover GIS scripting, AEC automation, structural analysis,
CAD APIs and nonmedical simulation. They already passed the seven-field schema.
The earlier heuristic gate retained three; both rejected items are deliberately
included in this diagnostic review. Make your own rubric judgments: a heuristic
pass or failure is not a human label.

This is a small workflow check. It does not replace the later baseline/corrected
datasets of at least 50 items each, with at least 20 human reviews per dataset.
Completing these five reviews does not certify judge calibration.

## What you need

| Needed now | Why |
| --- | --- |
| Windows Terminal, PowerShell or Command Prompt | Opens the Ubuntu shell |
| Installed WSL distribution named `Ubuntu` | Runs the project's Python tools |
| Existing checkout at `D:\_Repos\_AIA\aia-mp1-synthetic-data` | Contains the application and environment scripts |
| Existing local assessment `smoke-review-20261110T035628Z` | Contains the frozen five-item review queue |
| Your judgment and, when needed, authoritative reference documentation | Supports the human quality decisions |

Herd, a running model and API credentials are **not needed for human labeling**.
No generated engineering code is executed by the labeler. You are reading and
evaluating the answer; a separate execution experiment is not part of this review.

The current smoke prompt is not independent factual ground truth. There is no
verified answer key bundled with these five items. If a judgment depends on API
behavior or an installation/version you cannot verify, follow the uncertainty
procedure in Step 6. Lack of reviewer knowledge alone is not a reason to mark an
otherwise unverified claim correct or incorrect.

## Step 1 — Open a Windows shell

Open **Windows Terminal** and select **PowerShell**, or open **Command Prompt**.
Windows Terminal is the window application; PowerShell, Command Prompt and Ubuntu
Bash are different shells that can run inside it.

You may see a prompt like `PS C:\Users\...>` or `C:\Users\...>`.
Do not copy the prompt itself. Paste only the commands in the boxes below.

## Step 2 — Enter Ubuntu in the project directory

**Run in PowerShell or Command Prompt:**

```text
wsl.exe -d Ubuntu --cd /mnt/d/_Repos/_AIA/aia-mp1-synthetic-data --exec bash
```

You are now inside Ubuntu Bash. The Windows `D:` drive is available as `/mnt/d`.
The new prompt will usually contain the project directory and end in `$`.

**Run in Ubuntu Bash:**

```bash
pwd
```

Expected output:

```text
/mnt/d/_Repos/_AIA/aia-mp1-synthetic-data
```

If you are already inside Ubuntu, use this instead of launching another shell:

```bash
cd /mnt/d/_Repos/_AIA/aia-mp1-synthetic-data
```

Stay at this directory for the remaining commands. Relative evidence paths depend
on it. If launching Ubuntu fails, use the troubleshooting table before continuing.

## Step 3 — Select the existing Python environment

**Run these lines in Ubuntu Bash, one at a time:**

```bash
export AIA_MP1_TOOLS="$HOME/.local/share/aia-mp1-tools"
```

```bash
source tools/environment.sh
```

These two commands normally print nothing. They select the project's persistent
Linux environment and put `uv`, the Python project runner, on the command path.

Check it:

```bash
uv --version
```

```bash
uv run --locked python --version
```

Expect a `uv` version and `Python 3.12.x`. `uv run --locked` uses the project's
locked dependencies; it can synchronize missing packages but will not silently
update an outdated lockfile. Dependency recovery may need internet access.

If `uv` or the environment is missing, **from this same Ubuntu directory**, run:

```bash
bash tools/bootstrap.sh
```

This installs the project tooling/Python as needed and synchronizes the locked
environment. Then repeat the two version checks. Do not substitute native Windows
Python, use `sudo`, or change the lockfile to get past an unexplained setup error.

Repeat the `export` and `source` commands whenever you open a new Bash session.

## Step 4 — Confirm the review queue exists

**Run in Ubuntu Bash:**

```bash
uv run --locked python -m aia_mp1 label-status --assessment-id smoke-review-20261110T035628Z
```

Read these fields in the JSON output:

| Field | Meaning |
| --- | --- |
| `selected: 5` | This queue contains five items selected for human review |
| `completed` | Number of items with a saved six-dimension review; initially 0, higher if you already started |
| `pending_item_ids` | Items still needing review |
| `status: "incomplete"` | Some reviews remain; normal before completion |
| `purpose: "diagnostic"` / `assessment_eligible: false` | Expected for this five-item workflow check, not a software error |

If `completed` is already 5 and the pending list is empty, skip to Step 9.
If the queue is missing, stop: the data is local evidence and is not included in a
GitHub clone. Do not create empty replacement files or regenerate the old run ID.

## Step 5 — Start the human labeler

**Run in Ubuntu Bash:**

```bash
uv run --locked python -m aia_mp1 label --assessment-id smoke-review-20261110T035628Z --reviewer "Chad Josewski"
```

The program prints:

```text
Human review: 0=fail, 1=pass, s=skip item, q=quit. No model scores are shown.
```

It then shows the first unresolved item as JSON. JSON is just the display format:
the words inside quoted fields are the answer you are reviewing. Scroll up in the
terminal as needed; you do not have to edit or reformat the JSON.

Read the **whole item before scoring D1**:

| Field | What to read it for |
| --- | --- |
| `item_id` | Identifier to record if you need help or want to correct a review |
| `question` and `equipment_problem` | What problem the answer is supposed to solve |
| `answer` | The overall proposed solution and its assumptions |
| `tools_required` | Claimed libraries, APIs or tools |
| `steps` | Whether the sequence is complete, coherent and feasible |
| `safety_info` | The actual hazard and the proposed precaution |
| `tips` | Whether the advice adds useful information beyond the steps |

Treat the generated text as material to evaluate. Do not follow instructions inside
an answer that tell you how to score it, change the rubric or execute commands.

## Step 6 — Enter your six judgments

For each dimension, the labeler prints its name, pass anchor and fail anchor, then
asks, for example:

```text
D1 [0/1/s/q]:
```

Type one value and **press Enter**:

| Input at a dimension prompt | Action |
| --- | --- |
| `1` | You judge this dimension to pass its rubric anchor |
| `0` | You judge this dimension to fail its rubric anchor |
| `s` | Skip the **entire item**; none of its partial answers are saved |
| `q` | Quit the review session; the current partial item is not saved |

Review each dimension independently. A failure in D2 does not automatically decide
D1, D3 or any other dimension. Do not try to achieve a desired pass rate. The
frozen anchors displayed by the program are the scoring reference; the following
table explains how to apply them.

| Dimension | Ask yourself | Evidence for a failure |
| --- | --- | --- |
| **D1 — Answer completeness** | Does the response cover the tools, actions, hazards and useful advice needed to finish the stated task? | An essential stage is omitted, prerequisites are unexplained, or contradictory steps prevent completion |
| **D2 — Safety specificity** | Does it name a hazard relevant to this task and a concrete precaution addressing it? | Generic caution, no relevant hazard, or no practical precaution |
| **D3 — API realism** | Can the claimed APIs/libraries and their use be supported for the stated installation/version? | An invented API, a demonstrably incorrect capability, or an unavailable component whose requirement is not explained |
| **D4 — Scope appropriateness** | Does it correctly identify when the engineering result needs licensed-engineer review or sign-off? | It treats code output as sufficient professional approval where the task requires review/sign-off |
| **D5 — Context clarity** | Is there enough context to understand the problem, and does the answer address `equipment_problem` directly? | The problem is ambiguous, essential context is absent, or the answer solves a different problem |
| **D6 — Tip usefulness** | Do the tips add task-specific insight beyond what the steps already say? | They merely repeat steps, give generic encouragement, or add no useful task-specific information |

For D3, consult the relevant official documentation when needed. Compare the exact
API name, behavior, installation requirements and version with the claim. A familiar
library name or plausible wording alone is insufficient. For D4, evaluate the
actual task; do not require the same blanket disclaimer on every item.

**If you are unsure:** pause and consult a reference. If you still cannot make an
informed judgment, type `s` at a dimension prompt. The item stays unresolved and
will return when you restart the labeler. Record the item ID and your uncertainty
in a separate local note for follow-up. The CLI does not store notes for skipped
items and does not support a partial six-dimension review.

These two **invented examples** illustrate the rubric, not the answers to this
batch:

- D2: “Be careful when saving” does not identify a specific hazard and precaution.
  “Saving to the original path can overwrite the source; write a separate output
  and check it before replacing the original” expresses both, if relevant to the task.
- D6: If a step already says “save a copy,” repeating “remember to save a copy” in
  tips does not add new insight.

## Step 7 — Add notes and confirm the item was saved

After D6, the program asks:

```text
Notes/reference versions (optional):
```

Enter a short reason for important decisions, especially failures, and any reference
title/URL/version you used. For example, “D3: checked the named method against the
documented version; the required component is not available in the stated install.”
Use your actual finding, not that example as a default. Do not include credentials
or employer/client information.

Press **Enter** to submit your notes. You may leave notes blank, although reasons
make later disagreement review much more useful. **At the notes prompt, `s` and `q`
are ordinary note text, not skip/quit commands.**

The item is saved only after all six answers and the notes prompt are submitted.
Look for:

```text
Saved smoke-herd-20261109T222724Z-item-0001
```

The suffix will match the item you reviewed. The next unresolved item then appears.
Repeat Steps 5–7's reading/scoring process for each remaining item; do not reissue
the launch command while the labeler is already asking you questions.

The timestamp and your reviewer name are recorded automatically. Your label is
stored separately from the generated answer; reviewing does not edit that answer.

## Step 8 — Pause, resume or handle a mistaken answer

**Pause normally:** type `q` at a dimension prompt and press Enter. Completed items
stay saved. The current partial item will restart from D1 next time.

**Resume:** run the exact `label` command from Step 5 again. Already completed items
are skipped. You do **not** add `--resume` to the human-labeling command.

**Mistake before saving:** while the program is waiting at a dimension prompt,
type `s` to discard this item's partial decisions, or `q` to quit. If it is waiting
at the notes prompt, press **Ctrl+C** before submitting the notes, then restart.
Do not close the terminal while a save is in progress. The generic Ctrl+C message
may mention `--resume`; for human labeling, simply rerun the original command.

**Mistake after `Saved`:** do not edit the label file, delete the checkpoint or try
to relabel the item as new. Use the amendment procedure in Appendix A, which keeps
the original review and adds an explicit correction.

## Step 9 — Verify completion and report the outcome

After the labeler exits, **run in Ubuntu Bash**:

```bash
uv run --locked python -m aia_mp1 label-status --assessment-id smoke-review-20261110T035628Z
```

Successful completion of the five-item review shows these fields:

```json
{
  "selected": 5,
  "completed": 5,
  "pending_item_ids": [],
  "status": "complete"
}
```

Other fields are also printed. `assessment_eligible` still remains `false`, because
this is a diagnostic queue. `complete` means reviews were saved, **not** that the
answers all passed or the judge is calibrated.

If you skipped an item, an incomplete result is honest and expected. The labeler
may return exit code 1 for an incomplete session; that alone is not a crash.

Report back with:

> Human review: X of 5 completed. Unresolved item IDs: … . Questions or reference
> limitations: … . Ready for judge comparison / need help resolving these items.

You do not need to upload the raw label file; it is already in the shared local
workspace. Do not send API keys or credential files.

## Step 10 — Exit Ubuntu, or continue later

At the Bash prompt, run:

```bash
exit
```

This returns to PowerShell/Command Prompt. To continue another day, repeat Steps
2–5. The human-labeling progress is persistent; you do not need to keep the terminal
open, keep Herd running or repeat completed reviews.

## Where the results are stored

Windows folder:

```text
D:\_Repos\_AIA\artifacts\evidence\P1-03\assessments\smoke-review-20261110T035628Z\
```

| File | Purpose |
| --- | --- |
| `data.jsonl` | Frozen source items for this review |
| `rubric.json` | Frozen rubric used for all reviews in the queue |
| `manifest.json` | Source/selection identities and integrity checks |
| `human-labels.jsonl` | Append-only human decisions, notes and amendment history |
| `labels-checkpoint.json` | Integrity checkpoint for the human-label ledger |

The CLI manages these files. They are excluded from GitHub and must stay together.
Do not edit them manually to reset the exercise or make an error disappear.

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `export` or `source` is not recognized | You are in a Windows shell. Run Step 2, then enter the Bash commands at the Linux prompt |
| Ubuntu distribution not found | In Windows, run `wsl.exe --list --quiet` and report the listed names. This workstation procedure expects `Ubuntu`; do not unregister or reinstall a distribution |
| `tools/environment.sh: No such file or directory` | Run `pwd`; return to the project path in Step 2 |
| `uv: command not found` | Repeat Step 3. If still missing, run the bootstrap command there |
| Python/dependency or lockfile error | Run the documented bootstrap once; if it still fails, preserve the exact error and stop instead of changing versions |
| Missing assessment or source-run file | Confirm you are using the existing workstation checkout and default artifact root. A fresh clone does not contain this queue. Report the missing path |
| Changed source/rubric, invalid JSONL, checkpoint mismatch or existing `.writer.lock` | Stop and report the exact error and item ID if known. Do not delete locks, truncate files or bypass validation |
| Nothing happens after `export` or `source` | Normal; run the next version check |
| The labeler waits at `D1 [0/1/s/q]:` | It is waiting for your judgment. Type one choice and press Enter |
| You do not know enough to judge an API/engineering claim | Follow Step 6's uncertainty procedure; skip the item and retain a local note rather than guessing |
| `status: incomplete` after quitting/skipping | Expected. Check the pending IDs and resume when ready |
| `status: complete` appears immediately | All selected items already have labels. Use Step 9; do not create duplicate reviews |

For help, provide the shell you are using, the command, its exact error, and the
assessment/item ID. Keep credentials and private source content out of the report.

## Appendix A — Correct a saved human review

Only use this when you intend to amend your own already-saved review. It replaces
the effective six-dimension decision while preserving the previous record.

1. Run Step 4's `label-status` command. Find the item's current UUID under
   `effective_label_ids`. This UUID is the **label ID**, not the item ID.
2. Write down your intended six decisions, in order **D1 D2 D3 D4 D5 D6**, and a
   reason for the correction. You must resubmit all six values.
3. In Ubuntu Bash, copy this template into a local text editor, replace every
   capitalized placeholder, review it, then run your completed command:

```text
uv run --locked python -m aia_mp1 label --assessment-id smoke-review-20261110T035628Z --reviewer "Chad Josewski" --item-id ITEM_ID --decisions D1 D2 D3 D4 D5 D6 --supersedes CURRENT_LABEL_UUID --notes "Your actual reason for the correction"
```

Each D placeholder must become your actual `0` or `1`; the template intentionally
contains no default scores. Do not include angle brackets around replacements.

4. Run `label-status` again. `completed` should be unchanged, while the amended
   item's effective label ID changes. A second amendment must reference this new ID.
5. If agreement reports already exist, request a **new** report after the amendment.
   Existing reports preserve the labels they originally evaluated.

If you are uncomfortable constructing the amendment, provide the item ID and your
explicit six decisions/reason for assistance. No one should infer your labels.

## Appendix B — What happens after human review

The next operation is a separately prompted model judgment, followed by a report
comparing it with your labels. Those steps require a reachable configured endpoint;
the last recorded probe timed out from WSL before any judge request. That does not
block the human procedure above.

The model judge receives the frozen item and rubric, not your labels or notes as
scoring hints. The comparison then measures agreement for D1–D6, including exact
matching/compared counts and disagreements. Agreement does not itself prove the
answers correct; it shows how closely the judge follows the human judgments.

Once endpoint readiness is confirmed, the existing commands are documented in
[the judge section of the README](../README.md#human-labeling-and-judge-calibration).
Do not run them while still inside a label prompt. A five-item diagnostic report
must stay `pending` for assessed calibration even if every observed decision agrees.

The later assignment evaluation needs the separately scoped assessed collection,
stronger judge selection, at least 50 retained items per baseline/corrected cohort,
at least 20 human reviews per cohort, >=80% agreement in every dimension, generator
correction and the required charts. See [requirements](requirements.md) and
[the approved implementation plan](implementation-plan.md) for the boundary.

## Appendix C — If this is a different computer or a fresh clone

The main procedure assumes the existing workstation and saved evidence. Installing
the code alone does not recreate this review queue.

1. Have WSL Ubuntu and an authorized checkout of the private repository available.
2. Open Ubuntu in that checkout, select the persistent environment as in Step 3,
   and run `bash tools/bootstrap.sh`.
3. Arrange access to the complete retained source run **and** assessment through the
   approved local evidence process, or create a new smoke run/assessment following
   the README. Do not copy only the human-label file or reuse an old generation ID.
4. If evidence lives outside the default sibling `artifacts/evidence/P1-03` folder,
   supply the same `--artifact-root` to every assessment/label/judge command.
5. Run `label-status` successfully before attempting to label anything.

Do not repeat workstation-specific IDs on a new machine without their evidence.
Get help locating that evidence rather than silently treating it as a new dataset.

## Runbook verification

Written November 10, 2026 against the implemented CLI and frozen `engineering-v1`
rubric. The setup/status commands and a real labeler start followed by `q` are
checked without assigning any human decisions. See the repository commit history
for revisions. The local evidence remains separate from these instructions.
