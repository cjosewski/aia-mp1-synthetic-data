# Review runbook — GPT-OSS judge-v3 disagreements

**Your task:** review five disputed rubric decisions across three saved technical
answers. Decide whether each judge decision and its explanation are supported by
the original task, complete answer and frozen rubric. Record your own assessment
and reasoning in the new response sheet.

This is a **post-result review**, sometimes called adjudication. The packet shows
your earlier reference ratings and both model versions, so it is not blind.
It cannot replace the later fresh blind confirmation or assessed calibration.
Your original reviews and the measured 55/60 result remain frozen.

**Finish condition:** all five review blocks contain your rating (`0`, `1` or
`U` for unresolved), an explanation-quality assessment and a specific reason;
your reviewer/date/assistance fields are complete; the saved file is returned.
An unresolved decision with a concrete reason is a valid submission. There is
no required number of agreements with either the old reference or the model.

## 1. Open the new review folder

On Windows, paste this path into File Explorer:

```text
R:\MP1-handoff\MP1-JUDGE-V3-REVIEW-20261113
```

If the R: drive is not mapped, use:

```text
\\192.168.0.55\aia\MP1-handoff\MP1-JUDGE-V3-REVIEW-20261113
```

On the Mac, in Finder press **Command-K**, connect to
`smb://192.168.0.55/aia`, then open **MP1-handoff → MP1-JUDGE-V3-REVIEW-20261113**.

Open `RUNBOOK.md` in that folder. It is a distribution copy of this guide.
Use your Markdown/text editor, such as VS Code. For a local working copy, copy
the entire folder to a convenient location on your computer; keep the NAS copy
and frozen source files intact. You can review on either machine.

No Terminal commands, Python setup, running model or engineering application are
needed. Read the saved technical examples; do not execute them or start another
evaluation. You do not need to repeat the twenty baseline reviews or the earlier
ten-example review.

## 2. Identify the files

| File | Purpose |
| --- | --- |
| `RUNBOOK.md` | This procedure; start here. |
| `REVIEW-PACKET.md` | Three complete case cards, the five disputed decisions, original rubric anchors and saved explanations. |
| `MY-REVIEW.md` | Blank editable response sheet. This is the file you fill in. |
| `ANSWER-TEMPLATE.md` | Untouched spare copy of the response sheet. |
| `context/ORIGINAL-TEN-CASE-PACKET.md` | All ten original cases and source appendix, if you want broader context. |
| `context/V3-JUDGMENTS.md` | Full saved v3 and archived comparator explanations. |
| `context/V2-JUDGMENTS.md` | Full earlier GPT-OSS v2 explanations. |
| `context/judge-v2.md`, `context/judge-v3.md` | The two system prompts, for optional inspection. |
| `review-manifest.json` | Input hashes and review scope for verification; no manual editing needed. |

Keep the packet, template, source context and manifest unchanged. Only edit
`MY-REVIEW.md`, or a new version of that response file.

## 3. Fill in the reviewer information

Open `MY-REVIEW.md` beside `REVIEW-PACKET.md`.

1. Enter your name and review date/time, including time zone if possible.
2. State any help used: other people, AI tools, documentation or application checks.
   Write `None` only if that is true. If you adopt an AI-assisted assessment,
   identify the assistance and state what you personally checked.
3. Read the exposure statement: this packet includes previous ratings and model
   judgments. Do not describe this review as blind or independent calibration.

The response sheet contains placeholders, not suggested decisions. Replace them
with your own assessment. You may agree with the frozen reference, agree with v3,
or leave a decision unresolved.

## 4. Review the five decisions

| Review ID | Original case | Dimension | Why it is on this review list |
| --- | --- | --- | --- |
| R01 | Q04 — Revit sheet inventory | D2 — Safety | V3 changed a prior failure to a pass; the frozen rating is fail. |
| R02 | Q04 — Revit sheet inventory | D3 — API realism | V3 changed a prior failure to a pass; the frozen rating is fail. |
| R03 | Q04 — Revit sheet inventory | D5 — Context | Both model versions fail it; the frozen rating is pass. |
| R04 | Q06 — ArcPy CRS metadata | D3 — API realism | V3 changed a prior failure to a pass; the frozen rating is fail. |
| R05 | Q05 — OpenSees interpretation | D5 — Context | Both model versions fail it; the frozen rating is pass. |

For each case card:

1. Read **Reference task** first to establish what was requested.
2. Read **all seven candidate fields**, including every step, safety note and tip.
   Evaluate the supplied answer without repairing it first.
3. Read the relevant **original pass/fail rubric anchors**. Those anchors govern
   the rating; neither a model explanation nor the revised prompt replaces them.
4. Consult the case's source summary and pinned version. The packet preserves
   the source context supplied to the judge. These summaries do not establish
   that an example was executed on your computer.
5. Compare the recorded reference, v2 and v3 decisions and explanations. Decide
   whether v3's explanation describes the actual candidate faithfully and whether
   that evidence supports the assigned dimension.
6. Fill in the matching R01–R05 block in your response sheet.

Use these response values:

- **Your rating:** `0` = the candidate fails this dimension; `1` = it passes;
  `U` = you cannot decide from the available evidence. These rate the candidate,
  not whether you like the model's writing.
- **V3 explanation:** `SUPPORTED`, `PARTLY SUPPORTED`, `UNSUPPORTED` or `UNCERTAIN`.
  This separately records the quality of the model's stated reason. A matching
  numerical rating can still have a poor explanation.
- **Evidence/reason:** identify the relevant field, step, source passage or rubric
  anchor. Explain why it supports your rating and explanation assessment.
- **Additional source or unresolved question:** give a link/version/section for
  anything you consulted, or state what evidence is missing. Enter `None` if none.

Useful checks for the three dimensions under review:

- **D2:** Which task-specific hazard matters, and does the stated precaution
  address it? Consider reporting/access/interpretation hazards as well as changes
  to stored data. Check the combined answer, not only `safety_info`.
- **D3:** Check the claimed member, owning object, returned interface and stated
  environment. Distinguish an unavailable member from incorrect use of an existing
  operation. Record uncertainty rather than guessing about an API.
- **D5:** Determine whether the problem is clear and the same task is being
  addressed. Explain any ambiguity or substituted objective/input. Keep the
  context decision distinct from a factual or procedural defect unless it also
  violates the context anchor.

Do not use the overall 91.7% agreement to decide an individual rating. In
particular, the saved D3 result passes every case; its 80% agreement alone does
not show that it detects API failures.

## 5. Save, pause or revise

Save `MY-REVIEW.md` as UTF-8 Markdown. You may stop between review blocks and
resume later; no model server or command needs to stay running.

Before submitting, check that R01–R05 each have all four fields completed and no
placeholder remains. An explicit `U` with a reason is preferable to an unsupported
binary rating. A short overall observation is optional.

You may edit your working sheet until you submit it. After submission, retain
that version. Use a new file such as `MY-REVIEW-v2.md` for corrections and explain
which review IDs changed. We will preserve the submitted history.

## 6. Return the review

If you edited locally, copy the response file back to the NAS review folder.
If a previously submitted file already exists there, use a new versioned filename
instead of overwriting it.

Tell Codex:

```text
My judge-v3 review is ready:
R:\MP1-handoff\MP1-JUDGE-V3-REVIEW-20261113\MY-REVIEW.md
```

Alternatively, provide the full UNC path or paste the five completed blocks here.
No export command, ZIP or model rerun is required for this reading review.

## 7. What happens afterward

Codex will validate the five responses, preserve the submission with attribution,
and record your conclusions separately from the original frozen reference.
Missing evidence remains unresolved; assistant decisions will not fill blanks.

A difference from your old rating will be recorded as a proposed adjudication,
not silently substituted into the old report. The historical 52/60 and 55/60
measurements remain reproducible. Any requested amendment receives its own
explicit record and effect on reporting.

Your review will inform the next judge-design decision and selection of a frozen
candidate for fresh blind confirmation. It does not authorize a new model run,
qualify the judge, or replace the course's twenty-label/fifty-item requirements.
