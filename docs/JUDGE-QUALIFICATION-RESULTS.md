# Judge qualification — November 13 checkpoint

The GPT-OSS judge-v3 Mac experiment completed successfully: **55/60 agreement,
three false approvals and two false rejections**. Field coverage improved, but
safety/API defect detection regressed. Every dimension is at least 80% on the ten
known cases; this does not establish qualification. The generator, prior measured
prompts, rubric, cohort and human references remain unchanged. Do not rerun a
completed package or advance to assessed judging.

## GPT-OSS judge-v3 returned results

Chad authorized remote execution with "Go for it. I'll stand by." after SSH
setup. A separate twenty-request ceiling followed 53 documented starts; ten new
first attempts were used, bringing the documented total to 63. The earlier Mac
working folders matched their audited records with no additional attempts there.
No desktop control or Herd changes occurred. The dedicated server was stopped
before export, and the port was checked afterward.

Return `MP1-results-2026-11-13T174104724949+0000.zip` has SHA-256
`d856debaa0bc708ca7af367d6720cc23839c3ef4f80b1be3978a9a4bde8740b8`.
The external `qualification/gptoss-v3-return-review-20261113/` audit verifies
the frozen inputs/reference, bundle/policy/model/runtime, all attempt lineages,
raw/parsed JSON equality and all four report rows. Ten first attempts were valid,
with no errors, retries, truncation or unknown outcomes. Offline preparation
passed 204 tests, Ruff, shell syntax and package integrity checks.

Only the [judge-v3 system instructions](../prompts/judge-v3.md) changed. The
ten user messages, rubric, labels, weights, embedded template, runtime properties
and client settings were held constant. V3 requires checking evidence across all
seven fields and applying each rubric anchor independently. It contains no case
IDs, expected decisions or human comments. The default judge remains unchanged.

| Dimension / measure | GPT-OSS v2 | GPT-OSS v3 |
| --- | ---: | ---: |
| D1 — Completeness | 8/10 | 10/10 |
| D2 — Safety | 9/10 | 9/10 |
| D3 — API realism | 9/10 | 8/10 |
| D4 — Scope | 10/10 | 10/10 |
| D5 — Context | 7/10 | 8/10 |
| D6 — Tips | 9/10 | 10/10 |
| Agreement | 52/60 (86.7%) | 55/60 (91.7%) |
| False approvals | 0 | 3 |
| False rejections | 8 | 2 |

Six decisions gained agreement and three lost it. Mean request time was 13.1
seconds, totaling 130.5 seconds. This single run uses stochastic sampling; it
does not establish repeatability or a definitive causal effect for every change.

The new false approvals concern a null-dereference safeguard and two API
owner/return-interface defects. D3 predicts pass for all ten cases, including
both human-failing API cases. Its 80% agreement therefore detects neither failure;
the threshold alone is inadequate evidence of reliable judgment. D2 retains 90%
by exchanging a false rejection for a false approval. Two D5 false rejections
remain, and matching scores can still have weak explanations.

Retain v3 as development evidence rather than promote it to the assessed judge.
Review these safety/API regressions before selecting a frozen candidate for fresh
blind confirmation. No further iteration or model request followed this run.
The NAS archive is `MP1-handoff/completed-runs/gptoss-v3-2026-11-13T174104724949+0000/`.

## GPT-OSS Mac returned results

Return `MP1-results-2026-11-13T161049817190+0000.zip` has SHA-256
`acc61d5382c9061a49c7830939e974e04ba124e6e11055dd5e70a02b5cd6e85d`.
The external `qualification/gptoss-return-review-20261113/` audit validates bundle,
policy, frozen inputs/reference, model/runtime identity, attempt lineage and
raw/parsed judgment equality. Independent recomputation matches all three rows
of the returned report. All ten GPT-OSS first attempts were valid; no errors,
retries, truncation or unknown outcomes occurred. No new inference ran during review.

| Dimension / measure | GPT-OSS Mac v2 | Llama Mac v2 | Qwen Mac v2 |
| --- | ---: | ---: | ---: |
| D1 — Completeness | 8/10 | 7/10 | 9/10 |
| D2 — Safety | 9/10 | 7/10 | 7/10 |
| D3 — API realism | 9/10 | 8/10 | 8/10 |
| D4 — Scope | 10/10 | 10/10 | 10/10 |
| D5 — Context | 7/10 | 9/10 | 8/10 |
| D6 — Tips | 9/10 | 9/10 | 9/10 |
| Total agreement | 52/60 (86.7%) | 50/60 (83.3%) | 51/60 (85%) |
| False approvals | 0 | 9 | 3 |
| False rejections | 8 | 1 | 6 |

GPT-OSS gains nine matches and loses seven versus Llama; it gains six and loses
five versus Qwen. The eight disagreements include overlooking information in the
steps/safety/tips fields and extending procedural failures into context failures.
Some matching decisions also have inaccurate explanations of what the payload
contains. These are findings against the frozen reference, not revised labels.

The same Mac, Python version, llama.cpp `b12110-cd959bae9`, one slot, context
16,384 and default sampling parameters are recorded. Client settings remain
temperature 0.1, 4,096 tokens and 300 seconds. Mean request time is 11.4 seconds
(114.0 seconds total). Model templates/reasoning differ; this is a historical
development comparison, not a controlled speed benchmark or independent calibration.

The next proposed experiment is a general instruction revision for cross-field
evidence coverage and independent rubric boundaries. Keep v2 and these results
immutable; do not insert known answers or reuse the remaining allowance for a new
experiment. Fresh blind confirmation remains necessary before qualification.
At this earlier checkpoint the supplied ledgers accounted for 53 starts. Subsequent
SSH inspection found no additional attempts in either known Mac working folder;
the v3 experiment above adds ten. This was not a whole-machine search.

## GPT-OSS preparation record — completed by the return above

The [Mac runbook](GPTOSS-MAC-RUNBOOK.md) prepares one GPT-OSS-20B MXFP4 screen,
experiment `gptoss20b-mac-development-001`. Chad requested another Mac runbook;
this is a proposed screening candidate, not a replacement owner-selected or
qualified assessed judge. Its distinct model family, local availability and
[documented reasoning/structured-output capabilities](https://openai.com/index/introducing-gpt-oss/)
provide a test rationale, not evidence of stronger engineering judgment.

The NAS file's full SHA-256 was verified against the
[publisher's pinned GGUF](https://huggingface.co/ggml-org/gpt-oss-20b-GGUF/blob/b97cbb20d1995efd41dce8c4dd1ddf86e8db375b/gpt-oss-20b-MXFP4.gguf):
`27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901`,
12,109,566,624 bytes. No weight conversion or fresh model download was needed.

The new portable package is `qualification/MP1-GPTOSS-MAC/`, also provided as
`MP1-GPTOSS-MAC.zip` on the private handoff share. It reuses the exact ten-case
v2 inputs and frozen reviews, and includes the audited Mac Llama/Qwen return as
historical comparators. Only GPT-OSS may issue new completions. The existing
Mac/server build, one slot and context are checked; each run records its model
template and default runtime settings. The model's native reasoning/template
behavior differs, and this is not a randomized or repeated-seed comparison.

The separate operator-activated allowance is at most twenty new starts after
43 earlier starts, for a cumulative ceiling of 63. Attempts remain capped at two
per item, 300 seconds and 4,096 tokens. Two consecutive unsuccessful completions
stop the run; unknown outcomes require inspection. No live candidate request was
made during preparation. At that checkpoint native model/client compatibility and
judge quality were unmeasured; the return above now supplies development evidence.
Fresh blind confirmation and assessed calibration remain later gates.

## Mac v2 returned results

The November 13 return passed bundle/policy/input/attempt validation. All twenty
raw judgments match their saved parsed records and the independently recomputed
report; both models completed ten first attempts without retries, errors,
truncation or unknown outcomes. The source ZIP is retained with SHA-256
`cf8be0a1c700ef568fc16bd3bf543f2e5febfd7511fd254bb4124947840d3fc2`.

| Dimension | Llama Mac v2 | Qwen Mac v2 |
| --- | ---: | ---: |
| D1 — Completeness | 7/10 | 9/10 |
| D2 — Safety | 7/10 | 7/10 |
| D3 — API realism | 8/10 | 8/10 |
| D4 — Scope | 10/10 | 10/10 |
| D5 — Context | 9/10 | 8/10 |
| D6 — Tips | 9/10 | 9/10 |
| Total, descriptive only | 50/60 (83.3%) | 51/60 (85%) |

Llama's false approvals fell from fourteen to nine and false rejections from four
to one. Qwen's false approvals fell from ten to three, while false rejections rose
from two to six. Llama gained eight matching decisions without losing any; Qwen
gained ten and lost seven. Matching scores sometimes still have weak reasons.
These changes do not isolate a prompt effect because the platform/runtime also
changed, and the cases were already used to develop v2.

Both Mac phases record native arm64 macOS, Python 3.12.13, llama.cpp
`b12110-cd959bae9`, one slot and context 16,384, with the original GGUF pins and
client generation settings. Startup logs establish loading/serving but do not
explicitly record Metal offload layers. Mean request time was 38.1 seconds for
Llama and 9.6 seconds for Qwen (totals 381.1 and 96.3 seconds). This is operational
evidence, not a controlled hardware benchmark or a Herd-repair result.

Llama still approves critical procedural defects. Qwen detects more of them but
introduces dimension-boundary disagreements and a new false approval of a flawed
tip. Qwen remains the baseline generator, so its pooled 85% cannot supply the
required distinct stronger judge. Neither aggregate score establishes assessed
calibration; both models have D2 agreement of 7/10 on this development set.

Keep v2 as measured development evidence. Prepare another distinct candidate's
identity and rationale for a bounded same-Mac comparison before launching it;
do not silently change prompts, enter labels, reuse unused slots for new work or
advance to assessed judging. Any promising candidate still needs fresh blind
confirmation. The original twenty assessed reviews stay frozen.

## Earlier Fedora v1 results

Both models produced ten valid first-attempt judgments, with no retries, transport
failures, truncated responses or unknown outcomes in the Fedora comparison.
The returned bundle, policy, weight-hash records, input hashes and attempt lineage
passed validation. Each raw completion matched its parsed judgment, and independent
metric recomputation matched the returned report.

| Dimension | Llama 3.3 70B | Qwen3 30B-A3B |
| --- | ---: | ---: |
| D1 — Answer Completeness | 6/10 | 7/10 |
| D2 — Safety Specificity | 7/10 | 8/10 |
| D3 — API Realism | 5/10 | 8/10 |
| D4 — Scope Appropriateness | 10/10 | 8/10 |
| D5 — Context Clarity | 8/10 | 9/10 |
| D6 — Tip Usefulness | 6/10 | 8/10 |
| Total, descriptive only | 42/60 (70%) | 48/60 (80%) |

Llama incorrectly passed 14 of the 18 human-failing criterion decisions and
incorrectly rejected four human-passing criteria. Qwen incorrectly passed ten
human-failing decisions and rejected two human-passing decisions. Higher pooled
agreement does not establish per-dimension calibration; Qwen is also the baseline
generator and cannot satisfy the distinct-judge requirement.

Mean request duration was 213.0 seconds for Llama (202.4–241.5 seconds) and 74.0
seconds for Qwen (46.0–116.1 seconds). All Llama requests exceeded the earlier
120-second deadline but completed within the new 300-second budget. This shows
that the larger client timeout accommodated these requests, not that Herd was
repaired or that a controlled hardware speed improvement was demonstrated.

Both phases used the pinned Q4_K_M weights, temperature 0.1, max output 4096 and
16,384 context on the same recorded Fedora host/server build. Model-specific chat
templates and reasoning behavior differ. Ten authored examples, with AI-assisted
reviews personally verified and adopted by Chad, do not establish general model
superiority or assessed calibration.

The earlier Windows phase remains retained: two 120-second timeouts plus one
started request with unknown outcome. Together with the twenty Fedora requests,
23 qualification requests have started. Completed cases cannot be rerun using an
old run's unused budget after changing the prompt.

## Observed failure patterns and intervention

Both judges accepted candidate claims without adequately checking the actual
procedure. Errors included approving the removal of needed guards, accepting
incorrect API ownership/interface claims, and confusing plausible step lists
with successful completion. Llama additionally missed changed task specifications.
Qwen sometimes agreed with a failing label while giving an incomplete or
unsupported reason. Llama inconsistently treated supplied environment/version
requirements as unverifiable installation claims.

`judge-v2` requests evidence tied to the exact task, checks for contradictions
across all candidate fields, distinguishes API existence from misuse, and requires
accurate tips and effective precautions. It retains the existing rubric and output
schema and does not contain the ten reference labels, comments, item identifiers
or item-specific correction keys. Its hypothesis is that these instructions will
reduce false approvals without creating blanket failures or expanding D4's
professional-review requirement.

## V2 experiment protocol and stopping conditions

Chad instructed, "Document these findings and go on next steps." Prepare one
bounded development comparison of `judge-v2` against the original ten cases,
using the same frozen input/reference content, model pins and client generation
settings. The initial Fedora plan changed only the judge instruction; the later
Mac direction below additionally changes platform/runtime. Use new artifact identities and retain both
models' raw attempts; at most two attempts per case/model, forty new requests
total. Stop a phase after two consecutive timeouts. Unknown outcomes consume their
attempt and require inspection before resuming. Record authorization in the new
experiment policy; neither this experiment nor its unused budget authorizes a
further prompt version or the assessed judge run.

### Execution moved to the Mac

Chad subsequently reserved Linux for necessary Herd updates and directed this
evaluation to the Mac. Use `MP1-JUDGE-V2-MAC`, replacing the unstarted Fedora v2
handoff within the same forty-request allocation. If any Fedora v2 requests have
already started, reconcile those records before starting Mac requests; the move
does not grant an additional budget.

The checked-in Herd Mac backend uses MLX. The Mac handoff therefore uses a separate
local llama.cpp/Metal server with the same pinned GGUF files, native Apple Silicon
Python, port 8081, context 16,384 and one request slot. It does not change Herd
services or silently substitute converted weights. The handoff records the actual
Mac runtime/build and preserves the original Fedora evidence.

Both models must use the same Mac, server build and launch flags. Comparisons with
Fedora v1 now vary platform/runtime as well as prompt, so apparent improvement
cannot be attributed solely to `judge-v2`. The within-Mac model comparison and
agreement with the fixed reference remain development diagnostics. Native Mac
execution is now recorded in the returned results above; qualification is still
pending. Twenty Mac requests bring the retained history to 43 total starts.

These cases have informed the prompt change, so the new results are **development
diagnostics**, not an independent qualification result. Compare first-attempt
validity, per-dimension agreement, false approvals, false rejections, substantive
justifications and latency with v1. Preserve regressions. No new numerical
qualification threshold is introduced, and matching labels with incorrect
justifications do not establish reliable judgment.

After the development comparison, freeze any promising protocol before preparing
fresh blind confirmation cases across all five categories. Obtain authentic human
reviews before either model sees those cases. If the intervention does not help,
record that result before proposing another model or protocol. Do not tune on or
amend the frozen 20-item assessed reference to improve scores.

Assessed judging remains gated on a defensible distinct stronger-model basis and
the existing workflow: fifty cohort items, twenty frozen human reviews, complete
coverage and at least 80% agreement in every dimension. No qualification receipt
asserting readiness has been issued.

## Evidence locations

Raw evidence is excluded from Git under workspace `artifacts/evidence/P1-03/`:

- Returned data: `qualification/MP1-results-2026-11-13T050434763053+0000/`.
- Review, reproducible audit and file hashes: `qualification/return-review-20261113/`.
- Mac return: `qualification/MP1-results-2026-11-13T150132266655+0000/`.
- Mac review, audit and hashes: `qualification/mac-return-review-20261113/`.
- Frozen original packet/adoption: `qualification/llama-vs-qwen-v1/`.
- Portable original code and packet: `qualification/MP1-LINUX-HANDOFF/`.
- Current development handoff: `qualification/MP1-JUDGE-V2-MAC/HANDOFF.md`;
  its ZIP is also in the private NAS `AIA/MP1-handoff/` folder.
- Superseded, preserved Fedora development handoff: `qualification/MP1-JUDGE-V2-DEVELOPMENT/`.

The ten-review reference remains
`b86a7b139c1077a527f9e29a189aae41821add29e28b58f534e971e2ca81c65b`;
the separate assessed reference remains
`1e555ed74a0417120ac4d16052c3082e02e8e03550c3e2e09a64eda89856e4a8`.
