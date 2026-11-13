# Review the ten judge-qualification examples

**Current status:** Chad has personally verified and adopted all ten reviews.
The qualification reference is frozen with the original GPT-6 secondary-evaluator
attribution retained. Do not repeat this review. The Fedora v1 and Mac v2
comparisons completed, but Llama qualification remains pending. See the
[results and next experiment](JUDGE-QUALIFICATION-RESULTS.md) and
[current readiness](SOURCE-READINESS.md#current-next-action).
The instructions below document the completed review procedure.

Your task is to rate ten short technical answers using the existing D1–D6 rubric.
This prepares the human reference for comparing Llama-3.3-70B-Instruct with
Qwen3-30B-A3B. It is separate from the 20 baseline evaluations you already finished.

**Finish condition:** ten sets of six ratings, with your comments, are submitted
and recorded as your reviews. A low score is a valid review result. There is no
required number of passing answers.

## 1. Open the packet

Open [REVIEW-PACKET.md](../../artifacts/evidence/P1-03/qualification/llama-vs-qwen-v1/REVIEW-PACKET.md)
in your Markdown viewer or editor. On this workstation the complete path is:

```text
D:\_Repos\_AIA\artifacts\evidence\P1-03\qualification\llama-vs-qwen-v1\REVIEW-PACKET.md
```

You can paste that path into File Explorer's address bar. If Windows asks which
application to use, choose your text editor or Markdown viewer. A terminal,
Python setup and engineering applications are not needed for this reading step.
Herd can remain running with Llama loaded.

The packet contains ten new, synthetic examples: two each for ArcPy, Revit,
OpenSeesPy, FreeCAD and SciPy. Some contain intentional technical errors. Evaluate
the supplied answers; do not run the example code or fix it before scoring.
No expected scores or model judgments are included.

## 2. Prepare your answer sheet

Open [ANSWER-TEMPLATE.md](../../artifacts/evidence/P1-03/qualification/llama-vs-qwen-v1/ANSWER-TEMPLATE.md).
Use **Save As** to make a separate file named `MY-ANSWERS.md` in the same folder.
Enter your name and review date. Keep the original template and packet unchanged.

Alternatively, paste the template into a draft message and fill it out there.
No command-line label entry is required for this qualification packet.

## 3. Review Q01 through Q10

For each example:

1. Read its **Reference task**, which defines what the answer must accomplish.
2. Read all seven fields of the **Candidate answer to evaluate**, including its
   steps, safety information and tips.
3. Consult the matching source summary in the packet's **Source appendix**.
   Source links, pinned versions and attribution are included. These are also the
   reference summaries the two models will receive. They are not proof that the
   examples have been executed locally.
4. Replace each underscore on your answer sheet with `0` for fail or `1` for pass.
   Apply the complete rubric anchors printed at the start of the packet. Score
   each dimension independently.
5. Add a comment identifying the reasons for failures or explaining any ambiguity.
   If the supplied context cannot support a decision, leave that rating blank and
   describe what is missing. An unresolved rating will not count as a pass.

The dimension names are unchanged:

| Dimension | What to evaluate |
| --- | --- |
| D1 — Answer Completeness | Can the reader complete the stated task end to end? |
| D2 — Safety Specificity | Does the answer identify the relevant hazard and a concrete precaution? |
| D3 — API Realism | Are the required APIs real and available in the stated environment/version? |
| D4 — Scope Appropriateness | Does the answer handle required professional engineering review or sign-off correctly? |
| D5 — Context Clarity | Does it clearly address the stated equipment problem? |
| D6 — Tip Usefulness | Do tips add useful task-specific information beyond the steps? |

D4's existing rubric anchor concerns professional review/sign-off. Use that
anchor rather than silently substituting a new definition. A tutorial does not
automatically require sign-off just because it mentions engineering. This review
does not change any frozen baseline ratings.

## 4. Submit your reviews

Save `MY-ANSWERS.md`, then tell Codex **“The qualification reviews are ready in
MY-ANSWERS.md.”** Codex can read the local file directly. Alternatively, paste all
ten completed blocks here with their Q numbers or full item IDs.

Include whether you completed the reviews without seeing either model's
qualification judgments. State this only if true. No model comparisons had been
run when the original blank packet was handed off.

Codex will validate that all ten items have six explicit binary ratings and retain
your submitted comments with their attribution. Missing or ambiguous ratings
remain unresolved. Assistant-authored ratings will not fill any gaps. If you
request a correction after submission, it will be recorded as an explicit
amendment rather than erasing your original response.

## 5. What happens after submission

Codex freezes the completed qualification reference, then compares both models
using the same packet, rubric, prompt and request settings. Human ratings and
comments stay out of the model prompts. The approved budget is at most two
attempts per example per model: 40 requests total, including failed or unknown
attempts. The one earlier connectivity probe is separate and does not enter the
qualification results.

The current candidate is Llama-3.3-70B-Instruct Q4_K_M; the comparator is the fixed
Qwen3-30B-A3B Q4_K_M generator. Codex will identify when a Herd model switch is
needed. Herd settings and services remain under your control.

The comparison will report coverage, per-dimension agreement, schema failures,
unsupported claims and latency. This small authored set supports a selection
decision; it cannot establish assessed calibration or representative dataset
quality. If the evidence does not support stronger judgment, qualification stays
pending. Assessed calibration later uses the frozen 20 baseline reviews and the
50-item cohort, with at least 80% agreement in every dimension.

## Record locations

The review packet, source snapshot, blank template, model inputs, manifest and
verification receipt are retained outside Git in:

```text
D:\_Repos\_AIA\artifacts\evidence\P1-03\qualification\llama-vs-qwen-v1\
```

The manifest records the source/rubric/prompt hashes, ten item identities and
comparison budget. The baseline human reference remains unchanged. Do not rerun
collection, recreate `baseline-review-001`, or repeat its 20 reviews for this step.
