# Judge qualification — November 13 checkpoint

The Fedora comparison completed successfully, but **does not support qualifying
Llama-3.3-70B-Instruct Q4_K_M as the stronger judge**. The next action is a separately
versioned development comparison using [judge-v2.md](../prompts/judge-v2.md).
Its effect is unmeasured. The generator, original judge prompt, frozen rubric,
cohort and human references remain unchanged.

## Observed results

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

## Next experiment and stopping conditions

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
execution and model-quality outcomes are unmeasured until returned evidence exists.

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
- Frozen original packet/adoption: `qualification/llama-vs-qwen-v1/`.
- Portable original code and packet: `qualification/MP1-LINUX-HANDOFF/`.
- Current development handoff: `qualification/MP1-JUDGE-V2-MAC/HANDOFF.md`;
  its ZIP is also in the private NAS `AIA/MP1-handoff/` folder.
- Superseded, preserved Fedora development handoff: `qualification/MP1-JUDGE-V2-DEVELOPMENT/`.

The ten-review reference remains
`b86a7b139c1077a527f9e29a189aae41821add29e28b58f534e971e2ca81c65b`;
the separate assessed reference remains
`1e555ed74a0417120ac4d16052c3082e02e8e03550c3e2e09a64eda89856e4a8`.
