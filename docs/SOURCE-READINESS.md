# Assessed source and model readiness

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

Chad selected **Llama-3.3-70B-Instruct** for the judge role with the instruction,
"The model is going to be: Llama-3.3-70B-Instruct". This replaces the earlier
Qwen3-32B candidate. Selection is recorded; stronger-judge qualification remains
pending. Availability and model size do not establish stronger engineering judgment.

The completed Q4_K_M weights are now served by Herd. The external
`llama-preflight-20261113T011352Z/verification.json` records successful authenticated
WSL connectivity, the exact requested/reported model identity and one successful
structured-JSON probe (6.27 seconds, temperature 0.1, 4,096-token cap, 120-second
timeout, no retries). This diagnostic request is excluded from qualification and
assessed metrics. The server reports build `b12110-cd959bae9`, four slots and a
16,384-token context per slot; its properties and chat-template hash are retained.

The complete 42,520,398,816-byte file's SHA-256 is
`32df3baccb556f9840059b2528b2dee4d3d516b24afdfb9d0c56ff5f63e3a664`,
matching [Bartowski revision b6c5c9f](https://huggingface.co/bartowski/Llama-3.3-70B-Instruct-GGUF/blob/b6c5c9f176f3279204034e1d16d393105e95cb88/Llama-3.3-70B-Instruct-Q4_K_M.gguf).
No model or Herd setting was changed during verification. The earlier external
`judge-selection-llama-3.3-70b/selection.json` receipt preserves the owner instruction
and the partial-download state observed then. Neither receipt qualifies judge quality.

The qualification receipt requires the distinct upstream identity, weight checksum,
exact served ID, owner selection/basis, settings and hashes of comparison evidence.
Synthetic test receipts confer no qualification on real models.

## Current next action

Source approval and generator preflight are complete. Collection `baseline-001`
qualified after four batches and 200 first-attempt-valid responses. The
[baseline checkpoint](BASELINE-CHECKPOINT.md) records the frozen 50-item cohort
and the 20-item review queue. Those reviews are now complete, including seven
append-only amendments, and the blind human reference for `baseline-review-001`
is frozen. Its validated SHA-256 is
`1e555ed74a0417120ac4d16052c3082e02e8e03550c3e2e09a64eda89856e4a8`.

The ten-example qualification reference is now frozen at external
`qualification/llama-vs-qwen-v1/qualification-human-reference.json`. Chad stated,
"I personally reviewed and adopt all ten reviews." The original submission names
GPT-6 as its secondary evaluator; both that provenance and Chad's personal
verification are retained. These are AI-assisted, human-verified ratings, not
unaided human ratings. The reference SHA-256 is
`b86a7b139c1077a527f9e29a189aae41821add29e28b58f534e971e2ca81c65b`.

Llama's original Windows qualification phase stopped after both permitted attempts on the first
example timed out at 120 seconds. A third request had already started when the
runner was interrupted; its outcome is unknown and consumes an attempt. No valid
judgments were captured. `runs/llama/interruption.json` retains the exact state;
the Qwen phase had not started in that run. These are operational failures, not quality
scores or proof of inferior judgment.

Chad subsequently ran the portable Fedora comparison with explicit new-budget
authorization: 300-second timeout, at most forty additional requests, unchanged
frozen inputs and identical client settings for both models. Both models completed
ten first-attempt judgments with no transport failures. The returned evidence and
recomputed metrics passed audit on November 13. Llama matched 42/60 decisions;
Qwen matched 48/60. Llama falsely approved fourteen human-failing criteria, so this
evidence does not support its selection as the stronger judge. Neither pooled
agreement nor successful JSON output establishes assessed readiness.

The [qualification checkpoint](JUDGE-QUALIFICATION-RESULTS.md) owns the results,
limitations and next experiment. Chad authorized continued work; `judge-v2` is a
separate prompt revision measured in the returned Mac development comparison. It
does not alter the original prompt or frozen packet. Fresh blind confirmation
must follow any tuning on these known cases before claiming independent support.
Assessed judging and calibration remain pending; the frozen baseline reference
is preserved.

Chad moved the development evaluation to the Mac while Linux handles Herd updates.
Use the Mac handoff identified in the qualification checkpoint. It preserves GGUF
weight pins through standalone llama.cpp/Metal and replaces the unstarted Fedora
v2 package without adding a request budget. Platform/runtime differences mean
comparison with Fedora v1 cannot isolate the effect of the prompt change.

The Mac return passed audit: ten first-attempt judgments per model, no failures;
Llama 50/60 agreement and Qwen 51/60. Llama still falsely approves nine criteria,
and both models have D2 agreement of 7/10. Qualification remains pending. Preserve
the measured v2 protocol and prepare a distinct candidate comparison before any
new run; neither the aggregate scores nor faster serving authorize assessed judging.

The prepared [Mac runbook](GPTOSS-MAC-RUNBOOK.md) introduced GPT-OSS-20B MXFP4 as a
distinct screening candidate with verified weight provenance. It keeps judge-v2
and the frozen cases, reuses the archived Mac comparators and allocates at most
twenty new requests through explicit operator activation. This is preparation,
not a model measurement or a change to Chad's recorded judge selection. At that
preparation checkpoint native compatibility, stronger-judge support and fresh
blind confirmation remained pending.

Subsequent GPT-OSS return: native model/client operation passed with ten valid
first attempts. Audited agreement is 52/60, with zero false approvals and eight
false rejections; D5 is 7/10. It remains a development candidate, not a qualified
assessed judge. Cross-field evidence and rubric-boundary defects need attention;
the [qualification checkpoint](JUDGE-QUALIFICATION-RESULTS.md) owns the findings
and next proposed experiment. Frozen reviews and judge-v2 remain unchanged.

Owner-authorized judge-v3 follow-up completed remotely on the same Mac, model and
runtime: ten valid first attempts, 55/60 agreement, three false approvals and two
false rejections. All six development dimensions reach 80%, but D3 now passes
both human-failing API cases and a safety failure is newly approved. The frozen
rubric/references remain unchanged; v3 is measured development evidence, not a
qualified judge or an automatic default change. Review the regressions before
fresh blind confirmation and assessed calibration.

Chad's subsequent five-decision post-result review reaffirms every frozen rating
and confirms the remaining three false approvals/two false rejections. No label
amendment or metric change followed. This disclosed review is not fresh blind
confirmation; stronger-judge qualification remains pending targeted correction
and independent evidence. The completed response and attribution are preserved
outside Git and on the NAS.

The subsequent owner-authorized judge-v4 experiment completed ten valid first
attempts on the same Mac/model/runtime. It matches 52/60 decisions, with three
false approvals and five false rejections. API agreement improves to 10/10, but
the confirmed safety miss remains and context falls to 6/10. It does not satisfy
the predeclared development advancement condition. Preserve the complete run and
all earlier references; no fresh blind or assessed judging starts from this
result. The next work item is an explicit evidence-checking protocol, as described
in the qualification checkpoint. No additional human review is needed now.
